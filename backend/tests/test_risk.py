"""
Tests for risk management modules.
"""

from decimal import Decimal

import pytest

from backend.engine.risk.limits import RiskLimits, RiskLimitsConfig
from backend.engine.risk.position import PositionSizeConfig, PositionSizer


# Position Sizer Tests
@pytest.fixture
def position_sizer() -> PositionSizer:
    """Create position sizer with default config."""
    return PositionSizer()


def test_position_sizer_initialization(position_sizer: PositionSizer) -> None:
    """Test position sizer initialization."""
    assert position_sizer.config.risk_per_trade == 0.005


def test_calculate_basic_position_size(position_sizer: PositionSizer) -> None:
    """Test basic position size calculation."""
    equity = Decimal("100000")
    entry_price = Decimal("45000")
    stop_loss = Decimal("44000")

    size = position_sizer.calculate_size(equity, entry_price, stop_loss)

    # Risk amount = 100000 * 0.005 = 500
    # Risk per unit = 45000 - 44000 = 1000
    # Position size = 500 / 1000 = 0.5
    assert size > 0
    assert size == pytest.approx(Decimal("0.5"), abs=Decimal("0.01"))


def test_position_size_with_atr(position_sizer: PositionSizer) -> None:
    """Test position size with ATR adjustment."""
    equity = Decimal("100000")
    entry_price = Decimal("45000")
    stop_loss = Decimal("44000")
    atr = Decimal("900")  # High volatility

    size = position_sizer.calculate_size(equity, entry_price, stop_loss, atr)

    # With high ATR, position size should be adjusted
    assert size > 0


def test_position_size_respects_minimum(position_sizer: PositionSizer) -> None:
    """Test that minimum position value is respected."""
    equity = Decimal("1000")  # Small equity
    entry_price = Decimal("45000")
    stop_loss = Decimal("44999")  # Very tight stop

    size = position_sizer.calculate_size(equity, entry_price, stop_loss)

    # Should be at least min_position_value / entry_price
    min_size = Decimal("10") / entry_price
    assert size >= min_size


def test_position_size_invalid_stop(position_sizer: PositionSizer) -> None:
    """Test position size with invalid stop loss."""
    equity = Decimal("100000")
    entry_price = Decimal("45000")
    stop_loss = Decimal("45000")  # Same as entry (invalid)

    size = position_sizer.calculate_size(equity, entry_price, stop_loss)

    assert size == Decimal("0")


def test_risk_reward_calculation(position_sizer: PositionSizer) -> None:
    """Test risk-reward ratio calculation."""
    entry = Decimal("100")
    stop = Decimal("95")
    target = Decimal("115")

    rr = position_sizer.calculate_risk_reward(entry, stop, target)

    # Risk = 5, Reward = 15, RR = 3
    assert rr == Decimal("3")


def test_correlation_adjustment(position_sizer: PositionSizer) -> None:
    """Test position size adjustment for correlated positions."""
    base_size = Decimal("1.0")

    # No correlated positions
    size = position_sizer.adjust_size_for_correlation(base_size, 0)
    assert size == base_size

    # One correlated position
    size = position_sizer.adjust_size_for_correlation(base_size, 1, 0.5)
    assert size < base_size
    assert size == Decimal("0.5")

    # Two correlated positions
    size = position_sizer.adjust_size_for_correlation(base_size, 2, 0.5)
    assert size == Decimal("0.25")


# Risk Limits Tests
@pytest.fixture
def risk_limits() -> RiskLimits:
    """Create risk limits with test config."""
    config = RiskLimitsConfig(
        max_daily_loss=0.02,
        max_portfolio_exposure=0.4,
        max_position_size=0.1,
        max_positions=5,
        symbol_whitelist=["BTC-USD", "ETH-USD"],
    )
    return RiskLimits(config)


def test_risk_limits_initialization(risk_limits: RiskLimits) -> None:
    """Test risk limits initialization."""
    assert risk_limits.config.max_daily_loss == 0.02
    assert not risk_limits.kill_switch_active


def test_check_order_within_limits(risk_limits: RiskLimits) -> None:
    """Test order check when within limits."""
    allowed, reason = risk_limits.check_order(
        symbol="BTC-USD",
        order_value=Decimal("5000"),
        current_positions_value=Decimal("10000"),
        account_equity=Decimal("100000"),
        num_positions=2,
    )

    assert allowed is True


def test_check_order_symbol_not_whitelisted(risk_limits: RiskLimits) -> None:
    """Test order rejection for non-whitelisted symbol."""
    allowed, reason = risk_limits.check_order(
        symbol="DOGE-USD",  # Not in whitelist
        order_value=Decimal("5000"),
        current_positions_value=Decimal("0"),
        account_equity=Decimal("100000"),
        num_positions=0,
    )

    assert allowed is False
    assert "whitelist" in reason.lower()


def test_check_order_max_positions_exceeded(risk_limits: RiskLimits) -> None:
    """Test order rejection when max positions reached."""
    allowed, reason = risk_limits.check_order(
        symbol="BTC-USD",
        order_value=Decimal("5000"),
        current_positions_value=Decimal("20000"),
        account_equity=Decimal("100000"),
        num_positions=5,  # At max
    )

    assert allowed is False
    assert "max positions" in reason.lower()


def test_check_order_exposure_limit(risk_limits: RiskLimits) -> None:
    """Test order rejection for exposure limit."""
    allowed, reason = risk_limits.check_order(
        symbol="BTC-USD",
        order_value=Decimal("30000"),
        current_positions_value=Decimal("20000"),  # Total would be 50k / 100k = 50% > 40%
        account_equity=Decimal("100000"),
        num_positions=2,
    )

    assert allowed is False
    assert "exposure" in reason.lower()


def test_check_order_position_size_limit(risk_limits: RiskLimits) -> None:
    """Test order rejection for single position size limit."""
    allowed, reason = risk_limits.check_order(
        symbol="BTC-USD",
        order_value=Decimal("15000"),  # 15% > 10% max
        current_positions_value=Decimal("0"),
        account_equity=Decimal("100000"),
        num_positions=0,
    )

    assert allowed is False
    assert "position size" in reason.lower()


def test_daily_loss_tracking(risk_limits: RiskLimits) -> None:
    """Test daily loss tracking."""
    risk_limits.update_daily_equity(Decimal("100000"))

    # Record some losses
    risk_limits.record_trade_pnl(Decimal("-500"))
    risk_limits.record_trade_pnl(Decimal("-300"))

    daily_pnl = risk_limits.daily_tracker.get_daily_pnl()
    assert daily_pnl == Decimal("-800")


def test_kill_switch_on_daily_loss(risk_limits: RiskLimits) -> None:
    """Test kill switch activation on daily loss limit."""
    risk_limits.update_daily_equity(Decimal("100000"))

    # Record 2% loss
    risk_limits.record_trade_pnl(Decimal("-2000"))

    # Kill switch should activate
    assert risk_limits.kill_switch_active

    # New orders should be blocked
    allowed, reason = risk_limits.check_order(
        symbol="BTC-USD",
        order_value=Decimal("1000"),
        current_positions_value=Decimal("0"),
        account_equity=Decimal("98000"),
        num_positions=0,
    )

    assert allowed is False
    assert "kill switch" in reason.lower()


def test_kill_switch_manual_activation(risk_limits: RiskLimits) -> None:
    """Test manual kill switch activation."""
    risk_limits.activate_kill_switch("Manual halt")

    assert risk_limits.kill_switch_active


def test_kill_switch_deactivation(risk_limits: RiskLimits) -> None:
    """Test kill switch deactivation."""
    risk_limits.activate_kill_switch("Test")
    assert risk_limits.kill_switch_active

    risk_limits.deactivate_kill_switch()
    assert not risk_limits.kill_switch_active


def test_get_status(risk_limits: RiskLimits) -> None:
    """Test getting risk limits status."""
    risk_limits.update_daily_equity(Decimal("100000"))
    risk_limits.record_trade_pnl(Decimal("500"))

    status = risk_limits.get_status()

    assert "kill_switch_active" in status
    assert "trading_enabled" in status
    assert "daily_pnl" in status
    assert status["daily_pnl"] == 500.0
    assert "max_daily_loss_pct" in status
    assert "symbol_whitelist" in status
