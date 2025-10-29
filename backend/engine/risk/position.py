"""
Position sizing and risk management.

ATR-based position sizing to normalize risk across different volatility regimes.
"""

from decimal import Decimal
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field


class PositionSizeConfig(BaseModel):
    """Configuration for position sizing."""

    risk_per_trade: float = Field(
        default=0.005, description="Risk per trade as fraction of equity (0.5% default)"
    )
    use_atr_sizing: bool = Field(
        default=True, description="Use ATR-based position sizing"
    )
    min_position_value: float = Field(
        default=10.0, description="Minimum position value in dollars"
    )
    max_position_value: Optional[float] = Field(
        default=None, description="Maximum position value (None = no limit)"
    )


class PositionSizer:
    """
    Position sizing calculator.

    Calculates position size based on account equity, risk tolerance, and volatility (ATR).
    """

    def __init__(self, config: Optional[PositionSizeConfig] = None):
        """
        Initialize position sizer.

        Args:
            config: Position sizing configuration
        """
        self.config = config or PositionSizeConfig()
        logger.info(f"Initialized PositionSizer: {self.config.model_dump()}")

    def calculate_size(
        self,
        account_equity: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal,
        atr: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate position size based on risk parameters.

        Args:
            account_equity: Total account equity
            entry_price: Planned entry price
            stop_loss: Stop loss price
            atr: Average True Range (optional, for ATR-based sizing)

        Returns:
            Position size (quantity to trade)
        """
        # Calculate risk amount in dollars
        risk_amount = account_equity * Decimal(str(self.config.risk_per_trade))

        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            logger.warning(f"Invalid risk per unit: {risk_per_unit}. Returning 0.")
            return Decimal("0")

        # Base position size
        position_size = risk_amount / risk_per_unit

        # ATR-based adjustment
        if self.config.use_atr_sizing and atr and atr > 0:
            # Scale position size inversely with volatility
            # Higher ATR = smaller position, lower ATR = larger position
            # This normalizes risk across different volatility regimes
            avg_atr = Decimal("0.02")  # Baseline 2% ATR
            atr_ratio = avg_atr / atr
            position_size = position_size * atr_ratio

        # Apply minimum position value constraint
        min_size = Decimal(str(self.config.min_position_value)) / entry_price
        position_size = max(position_size, min_size)

        # Apply maximum position value constraint
        if self.config.max_position_value:
            max_size = Decimal(str(self.config.max_position_value)) / entry_price
            position_size = min(position_size, max_size)

        # Round to reasonable precision
        position_size = self._round_size(position_size, entry_price)

        logger.debug(
            f"Calculated position size: {position_size} "
            f"(equity: ${account_equity}, risk: ${risk_amount}, "
            f"risk/unit: ${risk_per_unit})"
        )

        return position_size

    def calculate_risk_reward(
        self, entry_price: Decimal, stop_loss: Decimal, target_price: Decimal
    ) -> Decimal:
        """
        Calculate risk-reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            target_price: Target/take profit price

        Returns:
            Risk-reward ratio (reward / risk)
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(target_price - entry_price)

        if risk <= 0:
            return Decimal("0")

        return reward / risk

    def adjust_size_for_correlation(
        self,
        base_size: Decimal,
        num_correlated_positions: int,
        correlation_factor: float = 0.5,
    ) -> Decimal:
        """
        Adjust position size for correlated positions.

        Reduces size when multiple correlated positions are held to avoid concentration risk.

        Args:
            base_size: Base position size
            num_correlated_positions: Number of existing correlated positions
            correlation_factor: Reduction factor per correlated position (0-1)

        Returns:
            Adjusted position size
        """
        if num_correlated_positions == 0:
            return base_size

        # Reduce size by correlation factor for each correlated position
        reduction = Decimal(str(correlation_factor)) ** num_correlated_positions
        adjusted_size = base_size * reduction

        logger.debug(
            f"Adjusted size for correlation: {base_size} -> {adjusted_size} "
            f"({num_correlated_positions} correlated positions)"
        )

        return adjusted_size

    def _round_size(self, size: Decimal, price: Decimal) -> Decimal:
        """
        Round position size to reasonable precision.

        Args:
            size: Raw position size
            price: Entry price

        Returns:
            Rounded position size
        """
        # For crypto, typically 8 decimal places
        # For stocks, typically whole shares or 0.001 for fractional
        if price > Decimal("100"):
            # Expensive asset (e.g., BTC) - use more decimals
            return size.quantize(Decimal("0.00001"))
        elif price > Decimal("1"):
            # Medium price - fewer decimals needed
            return size.quantize(Decimal("0.001"))
        else:
            # Cheap asset - even fewer decimals
            return size.quantize(Decimal("0.1"))
