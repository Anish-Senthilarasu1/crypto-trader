"""
Coinbase Advanced Trade paper trading broker adapter.

Simulates order placement and execution in sandbox mode.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from loguru import logger

from backend.engine.utils.config import Settings
from backend.engine.utils.types import (
    Account,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class CoinbasePaperBroker:
    """
    Paper trading broker for Coinbase Advanced Trade.

    Simulates order placement and fills without real capital.
    """

    def __init__(self, settings: Settings, initial_balance: Decimal = Decimal("100000")):
        """
        Initialize paper trading broker.

        Args:
            settings: Application settings
            initial_balance: Starting cash balance
        """
        self.settings = settings
        self.sandbox = settings.coinbase_sandbox

        # Paper trading state
        self.cash = initial_balance
        self.initial_balance = initial_balance
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.positions: Dict[str, Position] = {}

        logger.info(
            f"Initialized CoinbasePaperBroker (sandbox={self.sandbox}, "
            f"balance=${initial_balance})"
        )

    def get_account(self) -> Account:
        """
        Get current account information.

        Returns:
            Account object with current state
        """
        positions_value = sum(
            pos.quantity * (pos.current_price or pos.entry_price)
            for pos in self.positions.values()
        )

        unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.positions.values() if pos.unrealized_pnl
        )

        equity = self.cash + positions_value
        realized_pnl = equity - self.initial_balance - unrealized_pnl

        return Account(
            account_id="paper_account",
            equity=equity,
            cash=self.cash,
            buying_power=self.cash,  # Simplified: no margin for paper trading
            portfolio_value=equity,
            positions_value=positions_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            timestamp=datetime.utcnow(),
        )

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
    ) -> Order:
        """
        Place an order (simulated).

        Args:
            symbol: Trading pair (e.g., 'BTC-USD')
            side: Buy or sell
            quantity: Order quantity
            order_type: Market, limit, stop, etc.
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            client_order_id: Optional client-provided order ID

        Returns:
            Order object

        Raises:
            ValueError: If order parameters are invalid
        """
        # Validate order
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders require a price")

        # Generate order ID
        order_id = f"paper_{uuid.uuid4().hex[:16]}"
        if client_order_id is None:
            client_order_id = f"client_{uuid.uuid4().hex[:8]}"

        # Create order
        order = Order(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self.orders[order_id] = order
        logger.info(
            f"Placed {side.value} order: {order_id} for {quantity} {symbol} "
            f"({order_type.value})"
        )

        return order

    def fill_order(
        self, order_id: str, fill_price: Decimal, fee_rate: Decimal = Decimal("0.001")
    ) -> Optional[Fill]:
        """
        Simulate order fill (called by backtester or live worker).

        Args:
            order_id: Order ID to fill
            fill_price: Execution price
            fee_rate: Fee as a fraction (default: 0.1%)

        Returns:
            Fill object if successful, None if order not found
        """
        order = self.orders.get(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found")
            return None

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            logger.warning(f"Order {order_id} already {order.status.value}")
            return None

        # Calculate fee
        notional = order.quantity * fill_price
        fee = notional * fee_rate

        # Check if we have enough cash (for buys)
        if order.side == OrderSide.BUY:
            total_cost = notional + fee
            if self.cash < total_cost:
                logger.error(f"Insufficient cash for order {order_id}: need ${total_cost}")
                order.status = OrderStatus.REJECTED
                return None

        # Create fill
        fill = Fill(
            fill_id=f"fill_{uuid.uuid4().hex[:16]}",
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=fee,
            timestamp=datetime.utcnow(),
        )

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.fees = fee
        order.updated_at = datetime.utcnow()

        # Update cash and positions
        if order.side == OrderSide.BUY:
            self.cash -= notional + fee
            self._add_position(order.symbol, order.quantity, fill_price)
        else:  # SELL
            self.cash += notional - fee
            self._reduce_position(order.symbol, order.quantity, fill_price)

        self.fills.append(fill)
        logger.info(
            f"Filled order {order_id}: {order.quantity} {order.symbol} @ ${fill_price} "
            f"(fee: ${fee:.2f})"
        )

        return fill

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        order = self.orders.get(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found")
            return False

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            logger.warning(f"Order {order_id} cannot be cancelled (status: {order.status.value})")
            return False

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        logger.info(f"Cancelled order {order_id}")

        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order object or None if not found
        """
        return self.orders.get(order_id)

    def get_orders(
        self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """
        Get orders with optional filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status

        Returns:
            List of Order objects
        """
        orders = list(self.orders.values())

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        if status:
            orders = [o for o in orders if o.status == status]

        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Position object or None if no position
        """
        return self.positions.get(symbol)

    def get_positions(self) -> List[Position]:
        """
        Get all current positions.

        Returns:
            List of Position objects
        """
        return list(self.positions.values())

    def update_position_prices(self, prices: Dict[str, Decimal]) -> None:
        """
        Update current prices for positions.

        Args:
            prices: Dictionary mapping symbol to current price
        """
        for symbol, position in self.positions.items():
            if symbol in prices:
                current_price = prices[symbol]
                position.current_price = current_price

                # Calculate unrealized P&L
                if position.side == OrderSide.BUY:
                    position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
                else:  # Short position
                    position.unrealized_pnl = (position.entry_price - current_price) * position.quantity

                position.unrealized_pnl_percent = (
                    position.unrealized_pnl / (position.entry_price * position.quantity) * Decimal("100")
                )

    def _add_position(self, symbol: str, quantity: Decimal, price: Decimal) -> None:
        """
        Add or increase a position.

        Args:
            symbol: Trading pair
            quantity: Quantity to add
            price: Entry price
        """
        if symbol in self.positions:
            # Average up existing position
            pos = self.positions[symbol]
            total_cost = (pos.entry_price * pos.quantity) + (price * quantity)
            pos.quantity += quantity
            pos.entry_price = total_cost / pos.quantity
        else:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                entry_price=price,
                current_price=price,
            )

    def _reduce_position(self, symbol: str, quantity: Decimal, price: Decimal) -> None:
        """
        Reduce or close a position.

        Args:
            symbol: Trading pair
            quantity: Quantity to reduce
            price: Exit price
        """
        if symbol not in self.positions:
            logger.warning(f"Attempting to reduce non-existent position: {symbol}")
            return

        pos = self.positions[symbol]
        if quantity >= pos.quantity:
            # Close entire position
            del self.positions[symbol]
        else:
            # Partial reduction
            pos.quantity -= quantity
