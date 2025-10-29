"""
Momentum Breakout Strategy.

Entry: Price breaks above N-period high
Stop Loss: ATR-based stop (k * ATR below entry)
Exit: Trailing stop (ATR-based) or stop hit
"""

from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from backend.engine.signals.indicators import atr, rolling_high
from backend.engine.utils.types import Candle, OrderSide


class MomentumConfig(BaseModel):
    """Configuration for momentum breakout strategy."""

    lookback_period: int = Field(default=20, description="Period for breakout detection")
    atr_period: int = Field(default=14, description="ATR calculation period")
    atr_multiplier: float = Field(default=2.0, description="ATR multiplier for stop loss")
    trail_atr_multiplier: float = Field(default=1.5, description="ATR multiplier for trailing stop")
    min_atr: float = Field(default=0.0001, description="Minimum ATR to avoid division by zero")


class MomentumSignal(BaseModel):
    """Momentum strategy signal."""

    symbol: str
    side: OrderSide
    entry_price: Decimal
    stop_loss: Decimal
    trailing_stop: Optional[Decimal] = None
    atr_value: Decimal
    breakout_level: Decimal
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class MomentumStrategy:
    """
    Momentum Breakout Strategy.

    Detects when price breaks above recent highs and enters long positions
    with ATR-based stops.
    """

    def __init__(self, config: Optional[MomentumConfig] = None):
        """
        Initialize momentum strategy.

        Args:
            config: Strategy configuration (uses defaults if None)
        """
        self.config = config or MomentumConfig()
        logger.info(f"Initialized MomentumStrategy: {self.config.model_dump()}")

    def analyze(self, candles: List[Candle]) -> Optional[MomentumSignal]:
        """
        Analyze candles and generate signal if breakout detected.

        Args:
            candles: List of historical candles (must have at least lookback_period + atr_period)

        Returns:
            MomentumSignal if entry condition met, None otherwise
        """
        if len(candles) < max(self.config.lookback_period, self.config.atr_period) + 1:
            logger.debug(
                f"Insufficient candles: {len(candles)} < "
                f"{max(self.config.lookback_period, self.config.atr_period) + 1}"
            )
            return None

        # Convert to DataFrame
        df = self._candles_to_df(candles)

        # Calculate indicators
        df["atr"] = atr(
            df["high"], df["low"], df["close"], period=self.config.atr_period
        )
        df["breakout_level"] = rolling_high(
            df["high"], period=self.config.lookback_period
        ).shift(1)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Check for breakout
        # Entry: Current close > previous N-period high
        if latest["close"] > prev["breakout_level"] and prev["close"] <= prev["breakout_level"]:
            atr_val = max(float(latest["atr"]), self.config.min_atr)

            entry_price = Decimal(str(latest["close"]))
            stop_loss = Decimal(str(float(entry_price) - (atr_val * self.config.atr_multiplier)))
            trailing_stop = Decimal(
                str(float(entry_price) - (atr_val * self.config.trail_atr_multiplier))
            )

            # Calculate confidence based on how far above breakout
            breakout_distance = float(latest["close"] - prev["breakout_level"])
            confidence = min(1.0, breakout_distance / atr_val)

            signal = MomentumSignal(
                symbol=candles[-1].symbol,
                side=OrderSide.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                trailing_stop=trailing_stop,
                atr_value=Decimal(str(atr_val)),
                breakout_level=Decimal(str(prev["breakout_level"])),
                confidence=confidence,
                reason=f"Breakout above {self.config.lookback_period}-period high",
            )

            logger.info(
                f"Momentum signal: {signal.symbol} @ ${entry_price} "
                f"(stop: ${stop_loss}, confidence: {confidence:.2%})"
            )

            return signal

        return None

    def update_trailing_stop(
        self, entry_price: Decimal, current_price: Decimal, current_stop: Decimal, atr_val: Decimal
    ) -> Decimal:
        """
        Update trailing stop based on current price.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            current_stop: Current stop loss price
            atr_val: Current ATR value

        Returns:
            Updated stop loss price (will only move up, never down)
        """
        # Calculate new stop based on current price
        new_stop = Decimal(
            str(float(current_price) - (float(atr_val) * self.config.trail_atr_multiplier))
        )

        # Only update if new stop is higher (for long positions)
        if new_stop > current_stop:
            logger.debug(f"Trailing stop updated: ${current_stop} -> ${new_stop}")
            return new_stop

        return current_stop

    def should_exit(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        stop_loss: Decimal,
    ) -> bool:
        """
        Check if position should be exited.

        Args:
            entry_price: Entry price
            current_price: Current market price
            stop_loss: Stop loss price

        Returns:
            True if stop hit, False otherwise
        """
        # Exit if stop loss hit
        if current_price <= stop_loss:
            logger.info(f"Stop loss hit: ${current_price} <= ${stop_loss}")
            return True

        return False

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
