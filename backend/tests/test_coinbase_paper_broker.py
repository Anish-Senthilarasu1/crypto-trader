"""
Tests for Coinbase paper trading broker.
"""

from decimal import Decimal

import pytest

from backend.engine.broker.coinbase_paper import CoinbasePaperBroker
from backend.engine.utils.config import Settings
from backend.engine.utils.types import OrderSide, OrderStatus, OrderType


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(coinbase_sandbox=True)


@pytest.fixture
def broker(settings: Settings) -> CoinbasePaperBroker:
    """Create broker instance with $100,000 starting balance."""
    return CoinbasePaperBroker(settings, initial_balance=Decimal("100000"))


def test_initialization(broker: CoinbasePaperBroker) -> None:
    """Test broker initialization."""
    assert broker.cash == Decimal("100000")
    assert broker.initial_balance == Decimal("100000")
    assert len(broker.orders) == 0
    assert len(broker.fills) == 0
    assert len(broker.positions) == 0


def test_get_account_initial(broker: CoinbasePaperBroker) -> None:
    """Test getting account info initially."""
    account = broker.get_account()

    assert account.equity == Decimal("100000")
    assert account.cash == Decimal("100000")
    assert account.buying_power == Decimal("100000")
    assert account.portfolio_value == Decimal("100000")
    assert account.positions_value == Decimal("0")


def test_place_market_order_buy(broker: CoinbasePaperBroker) -> None:
    """Test placing a market buy order."""
    order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )

    assert order.symbol == "BTC-USD"
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal("0.5")
    assert order.order_type == OrderType.MARKET
    assert order.status == OrderStatus.PENDING
    assert order.order_id in broker.orders


def test_place_limit_order(broker: CoinbasePaperBroker) -> None:
    """Test placing a limit order."""
    order = broker.place_order(
        symbol="ETH-USD",
        side=OrderSide.SELL,
        quantity=Decimal("2.0"),
        order_type=OrderType.LIMIT,
        price=Decimal("2500"),
    )

    assert order.order_type == OrderType.LIMIT
    assert order.price == Decimal("2500")
    assert order.status == OrderStatus.PENDING


def test_place_order_validation(broker: CoinbasePaperBroker) -> None:
    """Test order validation."""
    # Zero quantity should raise error
    with pytest.raises(ValueError, match="Quantity must be positive"):
        broker.place_order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            quantity=Decimal("0"),
            order_type=OrderType.MARKET,
        )

    # Limit order without price should raise error
    with pytest.raises(ValueError, match="Limit orders require a price"):
        broker.place_order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            order_type=OrderType.LIMIT,
        )


def test_fill_buy_order(broker: CoinbasePaperBroker) -> None:
    """Test filling a buy order."""
    # Place order
    order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )

    initial_cash = broker.cash

    # Fill at $45,000
    fill = broker.fill_order(order.order_id, Decimal("45000"))

    assert fill is not None
    assert fill.price == Decimal("45000")
    assert fill.quantity == Decimal("0.5")
    assert fill.fee > 0  # Should have fee

    # Check order updated
    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == Decimal("0.5")
    assert order.avg_fill_price == Decimal("45000")

    # Check cash decreased
    notional = Decimal("0.5") * Decimal("45000")
    assert broker.cash < initial_cash
    assert broker.cash == initial_cash - notional - fill.fee

    # Check position created
    position = broker.get_position("BTC-USD")
    assert position is not None
    assert position.quantity == Decimal("0.5")
    assert position.entry_price == Decimal("45000")


def test_fill_sell_order(broker: CoinbasePaperBroker) -> None:
    """Test filling a sell order."""
    # First buy to establish position
    buy_order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        order_type=OrderType.MARKET,
    )
    broker.fill_order(buy_order.order_id, Decimal("45000"))

    # Now sell
    sell_order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.SELL,
        quantity=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )

    cash_before_sell = broker.cash
    fill = broker.fill_order(sell_order.order_id, Decimal("46000"))

    assert fill is not None

    # Cash should increase
    notional = Decimal("0.5") * Decimal("46000")
    assert broker.cash > cash_before_sell
    assert broker.cash == cash_before_sell + notional - fill.fee

    # Position should be reduced
    position = broker.get_position("BTC-USD")
    assert position.quantity == Decimal("0.5")


def test_insufficient_funds(broker: CoinbasePaperBroker) -> None:
    """Test order rejection due to insufficient funds."""
    # Try to buy more than we can afford
    order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("10.0"),  # $450,000 at $45,000
        order_type=OrderType.MARKET,
    )

    fill = broker.fill_order(order.order_id, Decimal("45000"))

    # Should be rejected
    assert fill is None
    assert order.status == OrderStatus.REJECTED


def test_cancel_order(broker: CoinbasePaperBroker) -> None:
    """Test cancelling an order."""
    order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        order_type=OrderType.LIMIT,
        price=Decimal("44000"),
    )

    success = broker.cancel_order(order.order_id)

    assert success is True
    assert order.status == OrderStatus.CANCELLED


def test_cannot_cancel_filled_order(broker: CoinbasePaperBroker) -> None:
    """Test that filled orders cannot be cancelled."""
    order = broker.place_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )
    broker.fill_order(order.order_id, Decimal("45000"))

    success = broker.cancel_order(order.order_id)

    assert success is False
    assert order.status == OrderStatus.FILLED


def test_get_orders_filtering(broker: CoinbasePaperBroker) -> None:
    """Test getting orders with filters."""
    # Place multiple orders
    broker.place_order("BTC-USD", OrderSide.BUY, Decimal("0.5"), OrderType.MARKET)
    broker.place_order("ETH-USD", OrderSide.BUY, Decimal("1.0"), OrderType.MARKET)
    broker.place_order("BTC-USD", OrderSide.SELL, Decimal("0.2"), OrderType.LIMIT, Decimal("50000"))

    # All orders
    all_orders = broker.get_orders()
    assert len(all_orders) == 3

    # Filter by symbol
    btc_orders = broker.get_orders(symbol="BTC-USD")
    assert len(btc_orders) == 2
    assert all(o.symbol == "BTC-USD" for o in btc_orders)

    # Filter by status
    pending_orders = broker.get_orders(status=OrderStatus.PENDING)
    assert len(pending_orders) == 3


def test_position_averaging(broker: CoinbasePaperBroker) -> None:
    """Test that multiple buys average the entry price."""
    # First buy
    order1 = broker.place_order("BTC-USD", OrderSide.BUY, Decimal("1.0"), OrderType.MARKET)
    broker.fill_order(order1.order_id, Decimal("45000"))

    # Second buy at different price
    order2 = broker.place_order("BTC-USD", OrderSide.BUY, Decimal("1.0"), OrderType.MARKET)
    broker.fill_order(order2.order_id, Decimal("47000"))

    # Position should be averaged
    position = broker.get_position("BTC-USD")
    assert position.quantity == Decimal("2.0")
    # Average: (45000 + 47000) / 2 = 46000
    assert position.entry_price == Decimal("46000")


def test_update_position_prices(broker: CoinbasePaperBroker) -> None:
    """Test updating position prices and unrealized P&L."""
    # Establish position
    order = broker.place_order("BTC-USD", OrderSide.BUY, Decimal("1.0"), OrderType.MARKET)
    broker.fill_order(order.order_id, Decimal("45000"))

    # Update price
    broker.update_position_prices({"BTC-USD": Decimal("47000")})

    position = broker.get_position("BTC-USD")
    assert position.current_price == Decimal("47000")
    assert position.unrealized_pnl == Decimal("2000")  # $47k - $45k
    assert position.unrealized_pnl_percent > 0


def test_account_after_trades(broker: CoinbasePaperBroker) -> None:
    """Test account state after multiple trades."""
    # Buy BTC
    order1 = broker.place_order("BTC-USD", OrderSide.BUY, Decimal("1.0"), OrderType.MARKET)
    broker.fill_order(order1.order_id, Decimal("45000"))

    # Buy ETH
    order2 = broker.place_order("ETH-USD", OrderSide.BUY, Decimal("10.0"), OrderType.MARKET)
    broker.fill_order(order2.order_id, Decimal("2500"))

    # Update prices
    broker.update_position_prices({
        "BTC-USD": Decimal("46000"),
        "ETH-USD": Decimal("2600"),
    })

    account = broker.get_account()

    # Should have two positions
    assert len(broker.get_positions()) == 2

    # Positions value
    expected_positions_value = Decimal("1.0") * Decimal("46000") + Decimal("10.0") * Decimal(
        "2600"
    )
    assert account.positions_value == expected_positions_value

    # Unrealized P&L
    btc_pnl = Decimal("1000")  # $46k - $45k
    eth_pnl = Decimal("1000")  # ($2600 - $2500) * 10
    assert account.unrealized_pnl == btc_pnl + eth_pnl

    # Total equity
    assert account.equity == account.cash + account.positions_value
