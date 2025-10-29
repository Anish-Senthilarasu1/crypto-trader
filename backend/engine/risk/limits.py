"""
Risk limits and controls.

Enforces daily loss limits, exposure caps, and symbol whitelists.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set

from loguru import logger
from pydantic import BaseModel, Field


class RiskLimitsConfig(BaseModel):
    """Configuration for risk limits."""

    max_daily_loss: float = Field(
        default=0.02, description="Maximum daily loss as fraction of equity (2% default)"
    )
    max_portfolio_exposure: float = Field(
        default=0.4, description="Maximum portfolio exposure as fraction (40% default)"
    )
    max_position_size: float = Field(
        default=0.1, description="Maximum single position as fraction of equity (10% default)"
    )
    max_positions: int = Field(default=10, description="Maximum number of concurrent positions")
    symbol_whitelist: List[str] = Field(
        default_factory=lambda: ["BTC-USD", "ETH-USD"],
        description="Allowed trading symbols",
    )
    trading_enabled: bool = Field(default=True, description="Master trading on/off switch")


class DailyLossTracker:
    """Track daily profit/loss for loss limit enforcement."""

    def __init__(self) -> None:
        """Initialize daily loss tracker."""
        self.daily_pnl: Dict[str, Decimal] = {}  # date -> pnl
        self.starting_equity: Dict[str, Decimal] = {}  # date -> equity

    def reset_day(self, date: str, equity: Decimal) -> None:
        """
        Reset tracker for a new trading day.

        Args:
            date: Date string (YYYY-MM-DD)
            equity: Starting equity for the day
        """
        self.daily_pnl[date] = Decimal("0")
        self.starting_equity[date] = equity
        logger.info(f"Reset daily loss tracker for {date} (equity: ${equity})")

    def record_pnl(self, pnl: Decimal, date: Optional[str] = None) -> None:
        """
        Record profit/loss for today.

        Args:
            pnl: P&L amount
            date: Date string (default: today)
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        if date not in self.daily_pnl:
            logger.warning(f"Date {date} not initialized in tracker")
            self.daily_pnl[date] = Decimal("0")

        self.daily_pnl[date] += pnl

    def get_daily_pnl(self, date: Optional[str] = None) -> Decimal:
        """
        Get total P&L for a date.

        Args:
            date: Date string (default: today)

        Returns:
            Daily P&L
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        return self.daily_pnl.get(date, Decimal("0"))

    def get_daily_pnl_pct(self, date: Optional[str] = None) -> Decimal:
        """
        Get daily P&L as percentage of starting equity.

        Args:
            date: Date string (default: today)

        Returns:
            Daily P&L percentage
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        pnl = self.get_daily_pnl(date)
        starting = self.starting_equity.get(date, Decimal("100000"))

        if starting <= 0:
            return Decimal("0")

        return (pnl / starting) * Decimal("100")


class RiskLimits:
    """
    Risk limits enforcer.

    Checks orders against risk limits before execution.
    """

    def __init__(self, config: Optional[RiskLimitsConfig] = None):
        """
        Initialize risk limits.

        Args:
            config: Risk limits configuration
        """
        self.config = config or RiskLimitsConfig()
        self.daily_tracker = DailyLossTracker()
        self.kill_switch_active = False

        # Initialize today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        self.daily_tracker.reset_day(today, Decimal("100000"))  # Will be updated with real equity

        logger.info(f"Initialized RiskLimits: {self.config.model_dump()}")

    def update_daily_equity(self, equity: Decimal, date: Optional[str] = None) -> None:
        """
        Update starting equity for the day.

        Args:
            equity: Current equity
            date: Date string (default: today)
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        if date not in self.daily_tracker.starting_equity:
            self.daily_tracker.reset_day(date, equity)
        else:
            self.daily_tracker.starting_equity[date] = equity

    def check_order(
        self,
        symbol: str,
        order_value: Decimal,
        current_positions_value: Decimal,
        account_equity: Decimal,
        num_positions: int,
    ) -> tuple[bool, str]:
        """
        Check if order passes all risk limits.

        Args:
            symbol: Trading symbol
            order_value: Value of proposed order
            current_positions_value: Total value of current positions
            account_equity: Account equity
            num_positions: Current number of positions

        Returns:
            Tuple of (allowed, reason)
        """
        # Check kill switch
        if self.kill_switch_active:
            return False, "Kill switch activated - no new orders allowed"

        # Check if trading enabled
        if not self.config.trading_enabled:
            return False, "Trading is disabled"

        # Check symbol whitelist
        if symbol not in self.config.symbol_whitelist:
            return False, f"Symbol {symbol} not in whitelist"

        # Check max positions
        if num_positions >= self.config.max_positions:
            return False, f"Max positions reached ({self.config.max_positions})"

        # Check daily loss limit
        daily_pnl_pct = self.daily_tracker.get_daily_pnl_pct()
        max_loss_pct = Decimal(str(self.config.max_daily_loss * -100))

        if daily_pnl_pct <= max_loss_pct:
            self.activate_kill_switch(f"Daily loss limit breached: {daily_pnl_pct:.2f}%")
            return False, f"Daily loss limit breached: {daily_pnl_pct:.2f}%"

        # Check portfolio exposure
        new_exposure = (current_positions_value + order_value) / account_equity
        max_exposure = Decimal(str(self.config.max_portfolio_exposure))

        if new_exposure > max_exposure:
            return (
                False,
                f"Portfolio exposure limit exceeded: {new_exposure:.2%} > {max_exposure:.2%}",
            )

        # Check single position size
        position_size_pct = order_value / account_equity
        max_position_pct = Decimal(str(self.config.max_position_size))

        if position_size_pct > max_position_pct:
            return (
                False,
                f"Position size limit exceeded: {position_size_pct:.2%} > {max_position_pct:.2%}",
            )

        return True, "Order approved"

    def record_trade_pnl(self, pnl: Decimal) -> None:
        """
        Record profit/loss from a closed trade.

        Args:
            pnl: Trade P&L
        """
        self.daily_tracker.record_pnl(pnl)

        # Check if daily loss limit breached
        daily_pnl_pct = self.daily_tracker.get_daily_pnl_pct()
        max_loss_pct = Decimal(str(self.config.max_daily_loss * -100))

        if daily_pnl_pct <= max_loss_pct:
            self.activate_kill_switch(f"Daily loss limit breached: {daily_pnl_pct:.2f}%")

    def activate_kill_switch(self, reason: str) -> None:
        """
        Activate kill switch - stops all trading.

        Args:
            reason: Reason for activation
        """
        if not self.kill_switch_active:
            self.kill_switch_active = True
            logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")

    def deactivate_kill_switch(self) -> None:
        """Deactivate kill switch - resume trading."""
        if self.kill_switch_active:
            self.kill_switch_active = False
            logger.warning("Kill switch deactivated - trading resumed")

    def get_status(self) -> Dict[str, any]:
        """
        Get current risk limits status.

        Returns:
            Dictionary with status information
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_pnl = self.daily_tracker.get_daily_pnl(today)
        daily_pnl_pct = self.daily_tracker.get_daily_pnl_pct(today)

        return {
            "kill_switch_active": self.kill_switch_active,
            "trading_enabled": self.config.trading_enabled,
            "daily_pnl": float(daily_pnl),
            "daily_pnl_pct": float(daily_pnl_pct),
            "max_daily_loss_pct": self.config.max_daily_loss * 100,
            "max_portfolio_exposure_pct": self.config.max_portfolio_exposure * 100,
            "max_position_size_pct": self.config.max_position_size * 100,
            "max_positions": self.config.max_positions,
            "symbol_whitelist": self.config.symbol_whitelist,
        }
