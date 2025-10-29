"""
Mean Reversion Strategy with VWAP and Bollinger Bands.

Entry: Price < VWAP AND price near lower Bollinger Band
Exit: Price > VWAP OR stop loss hit
"""

from decimal import Decimal
from typing import List, Optional

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from backend.engine.signals.indicators import atr, bollinger_bands, vwap
from backend.engine.utils.types import Candle, OrderSide


class MeanRevConfig(BaseModel):
    """Configuration for mean reversion strategy."""

    bb_period: int = Field(default=20, description="Bollinger Bands period")
    bb_std: float = Field(default=2.0, description="Bollinger Bands standard deviations")
    atr_period: int = Field(default=14, description="ATR calculation period")
    atr_stop_multiplier: float = Field(default=2.0, description="ATR multiplier for stop loss")
    bb_entry_threshold: float = Field(
        default=0.2, description="How close to lower BB (0=at BB, 1=at middle)"
    )
    min_atr: float = Field(default=0.0001, description="Minimum ATR")


class MeanRevSignal(BaseModel):
    """Mean reversion strategy signal."""

    symbol: str
    side: OrderSide
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal  # VWAP
    atr_value: Decimal
    vwap_value: Decimal
    bb_lower: Decimal
    bb_middle: Decimal
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class MeanRevStrategy:
    """
    Mean Reversion Strategy.

    Buys when price drops below VWAP and approaches lower Bollinger Band,
    expecting reversion to mean. Exits when price returns to VWAP or stop hit.
    """

    def __init__(self, config: Optional[MeanRevConfig] = None):
        """
        Initialize mean reversion strategy.

        Args:
            config: Strategy configuration (uses defaults if None)
        """
        self.config = config or MeanRevConfig()
        logger.info(f"Initialized MeanRevStrategy: {self.config.model_dump()}")

    def analyze(self, candles: List[Candle]) -> Optional[MeanRevSignal]:
        """
        Analyze candles and generate signal if mean reversion setup detected.

        Args:
            candles: List of historical candles

        Returns:
            MeanRevSignal if entry condition met, None otherwise
        """
        min_candles = max(self.config.bb_period, self.config.atr_period) + 1
        if len(candles) < min_candles:
            logger.debug(f"Insufficient candles: {len(candles)} < {min_candles}")
            return None

        # Convert to DataFrame
        df = self._candles_to_df(candles)

        # Calculate indicators
        df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
        df["bb_middle"], df["bb_upper"], df["bb_lower"] = bollinger_bands(
            df["close"], period=self.config.bb_period, num_std=self.config.bb_std
        )
        df["atr"] = atr(df["high"], df["low"], df["close"], period=self.config.atr_period)

        # Get latest values
        latest = df.iloc[-1]

        # Entry conditions:
        # 1. Price < VWAP (oversold relative to volume-weighted average)
        # 2. Price near lower Bollinger Band
        if latest["close"] >= latest["vwap"]:
            return None

        # Check proximity to lower BB
        bb_range = latest["bb_middle"] - latest["bb_lower"]
        if bb_range <= 0:
            return None

        price_to_bb_lower = latest["close"] - latest["bb_lower"]
        bb_position = price_to_bb_lower / bb_range  # 0 = at lower BB, 1 = at middle

        if bb_position > self.config.bb_entry_threshold:
            return None

        # Signal conditions met
        atr_val = max(float(latest["atr"]), self.config.min_atr)

        entry_price = Decimal(str(latest["close"]))
        stop_loss = Decimal(str(float(entry_price) - (atr_val * self.config.atr_stop_multiplier)))
        target_price = Decimal(str(latest["vwap"]))  # Target is reversion to VWAP

        # Confidence based on how oversold (lower BB position)
        confidence = 1.0 - bb_position  # Closer to lower BB = higher confidence

        # Additional confidence boost if far below VWAP
        vwap_distance_pct = (latest["vwap"] - latest["close"]) / latest["vwap"]
        confidence = min(1.0, confidence + vwap_distance_pct * 2)

        signal = MeanRevSignal(
            symbol=candles[-1].symbol,
            side=OrderSide.BUY,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            atr_value=Decimal(str(atr_val)),
            vwap_value=Decimal(str(latest["vwap"])),
            bb_lower=Decimal(str(latest["bb_lower"])),
            bb_middle=Decimal(str(latest["bb_middle"])),
            confidence=confidence,
            reason=f"Price below VWAP, near lower BB (position: {bb_position:.2f})",
        )

        logger.info(
            f"Mean reversion signal: {signal.symbol} @ ${entry_price} "
            f"(target: ${target_price}, confidence: {confidence:.2%})"
        )

        return signal

    def should_exit(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        stop_loss: Decimal,
        vwap_value: Decimal,
    ) -> tuple[bool, str]:
        """
        Check if position should be exited.

        Args:
            entry_price: Entry price
            current_price: Current market price
            stop_loss: Stop loss price
            vwap_value: Current VWAP value

        Returns:
            Tuple of (should_exit, reason)
        """
        # Exit if stop loss hit
        if current_price <= stop_loss:
            return True, f"Stop loss hit: ${current_price} <= ${stop_loss}"

        # Exit if price reverted above VWAP (target reached)
        if current_price >= vwap_value:
            pnl_pct = (float(current_price) - float(entry_price)) / float(entry_price) * 100
            return True, f"Target reached: price above VWAP (P&L: {pnl_pct:.2f}%)"

        return False, ""

    def update_target(
        self, candles: List[Candle]
    ) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Update VWAP and Bollinger Band values for exit monitoring.

        Args:
            candles: Recent candles

        Returns:
            Tuple of (vwap_value, bb_middle) or (None, None) if insufficient data
        """
        min_candles = max(self.config.bb_period, self.config.atr_period)
        if len(candles) < min_candles:
            return None, None

        df = self._candles_to_df(candles)
        df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
        df["bb_middle"], _, _ = bollinger_bands(
            df["close"], period=self.config.bb_period, num_std=self.config.bb_std
        )

        latest = df.iloc[-1]
        return Decimal(str(latest["vwap"])), Decimal(str(latest["bb_middle"]))

    def _candles_to_df(self, candles: List[Candle]) -> pd.DataFrame:
        """
        Convert candles to pandas DataFrame.

        Args:
            candles: List of Candle objects

        Returns:
            DataFrame with OHLCV columns
        """
        data = []
        for c in candles:
            data.append(
                {
                    "timestamp": c.timestamp,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "volume": float(c.volume),
                }
            )

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
