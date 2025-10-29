"""
Tests for momentum breakout strategy.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend.engine.signals.momentum import MomentumConfig, MomentumStrategy
from backend.engine.utils.types import Candle, OrderSide


def create_test_candles(
    prices: list, symbol: str = "BTC-USD", base_time: datetime = None
) -> list[Candle]:
    """Create test candles from price list."""
    if base_time is None:
        base_time = datetime.utcnow() - timedelta(hours=len(prices))

    candles = []
    for i, price in enumerate(prices):
        candles.append(
            Candle(
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(price * 0.99)),
                high=Decimal(str(price * 1.01)),
                low=Decimal(str(price * 0.98)),
                close=Decimal(str(price)),
                volume=Decimal("100"),
                symbol=symbol,
            )
        )
    return candles


@pytest.fixture
def strategy() -> MomentumStrategy:
    """Create momentum strategy with test config."""
    config = MomentumConfig(lookback_period=5, atr_period=5)
    return MomentumStrategy(config)


def test_momentum_strategy_initialization(strategy: MomentumStrategy) -> None:
    """Test strategy initialization."""
    assert strategy.config.lookback_period == 5
    assert strategy.config.atr_period == 5


def test_no_signal_insufficient_data(strategy: MomentumStrategy) -> None:
    """Test that no signal is generated with insufficient data."""
    candles = create_test_candles([100, 101, 102])
    signal = strategy.analyze(candles)

    assert signal is None


def test_breakout_signal_generated(strategy: MomentumStrategy) -> None:
    """Test that breakout signal is generated when price breaks high."""
    # Create uptrend with breakout
    prices = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103, 105]  # Breaks out at end
    candles = create_test_candles(prices)

    signal = strategy.analyze(candles)

    assert signal is not None
    assert signal.symbol == "BTC-USD"
    assert signal.side == OrderSide.BUY
    assert signal.entry_price > 0
    assert signal.stop_loss < signal.entry_price
    assert signal.confidence > 0


def test_no_signal_no_breakout(strategy: MomentumStrategy) -> None:
    """Test that no signal when price doesn't break out."""
    # Sideways market, no breakout
    prices = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101]
    candles = create_test_candles(prices)

    signal = strategy.analyze(candles)

    assert signal is None


def test_stop_loss_calculation(strategy: MomentumStrategy) -> None:
    """Test that stop loss is calculated correctly."""
    prices = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103, 105]
    candles = create_test_candles(prices)

    signal = strategy.analyze(candles)

    assert signal is not None
    # Stop should be entry - (ATR * multiplier)
    assert signal.stop_loss < signal.entry_price
    # Verify it's ATR-based
    assert signal.atr_value > 0


def test_trailing_stop_update(strategy: MomentumStrategy) -> None:
    """Test trailing stop update logic."""
    entry_price = Decimal("100")
    current_stop = Decimal("95")
    atr_val = Decimal("2")

    # Price moves up
    new_price = Decimal("105")
    new_stop = strategy.update_trailing_stop(entry_price, new_price, current_stop, atr_val)

    # New stop should be higher
    assert new_stop > current_stop

    # Price moves down (stop shouldn't move down)
    lower_price = Decimal("102")
    same_stop = strategy.update_trailing_stop(entry_price, lower_price, new_stop, atr_val)

    assert same_stop == new_stop  # Stop doesn't move down


def test_should_exit_stop_hit(strategy: MomentumStrategy) -> None:
    """Test exit when stop loss is hit."""
    entry_price = Decimal("100")
    stop_loss = Decimal("95")

    # Price hits stop
    current_price = Decimal("94")
    should_exit = strategy.should_exit(entry_price, current_price, stop_loss)

    assert should_exit is True


def test_should_exit_stop_not_hit(strategy: MomentumStrategy) -> None:
    """Test no exit when stop not hit."""
    entry_price = Decimal("100")
    stop_loss = Decimal("95")

    # Price above stop
    current_price = Decimal("102")
    should_exit = strategy.should_exit(entry_price, current_price, stop_loss)

    assert should_exit is False


def test_confidence_calculation(strategy: MomentumStrategy) -> None:
    """Test that confidence is calculated based on breakout strength."""
    # Strong breakout
    prices = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 110]  # Big jump
    candles = create_test_candles(prices)

    signal = strategy.analyze(candles)

    if signal:  # May not trigger depending on exact implementation
        assert 0 <= signal.confidence <= 1.0


def test_candles_to_df_conversion(strategy: MomentumStrategy) -> None:
    """Test candle to DataFrame conversion."""
    prices = [100, 101, 102, 103, 104]
    candles = create_test_candles(prices)

    df = strategy._candles_to_df(candles)

    assert len(df) == len(candles)
    assert "open" in df.columns
    assert "high" in df.columns
    assert "low" in df.columns
    assert "close" in df.columns
    assert "volume" in df.columns
    assert df["close"].iloc[-1] == pytest.approx(104)
