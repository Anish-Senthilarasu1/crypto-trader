"""
SQLite database storage for orders, fills, and trades.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from loguru import logger

from backend.engine.utils.types import Fill, Order, OrderStatus, Trade


class SQLiteStore:
    """
    SQLite database store for trading data.

    Stores orders, fills, trades, and account snapshots.
    """

    def __init__(self, db_path: str = "./data/aurora_trader.db"):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()
        logger.info(f"Initialized SQLiteStore: {db_path}")

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                client_order_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity TEXT NOT NULL,
                price TEXT,
                stop_price TEXT,
                status TEXT NOT NULL,
                filled_quantity TEXT DEFAULT '0',
                avg_fill_price TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                fees TEXT DEFAULT '0'
            )
        """)

        # Fills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fills (
                fill_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity TEXT NOT NULL,
                price TEXT NOT NULL,
                fee TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)

        # Trades table (closed positions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price TEXT NOT NULL,
                exit_price TEXT,
                quantity TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                pnl TEXT,
                pnl_percent TEXT,
                fees TEXT DEFAULT '0',
                strategy TEXT,
                tags TEXT
            )
        """)

        # Account snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                equity TEXT NOT NULL,
                cash TEXT NOT NULL,
                positions_value TEXT NOT NULL,
                unrealized_pnl TEXT NOT NULL,
                realized_pnl TEXT NOT NULL
            )
        """)

        # Metrics table (daily aggregates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                date TEXT PRIMARY KEY,
                starting_equity TEXT NOT NULL,
                ending_equity TEXT NOT NULL,
                daily_pnl TEXT NOT NULL,
                daily_pnl_pct TEXT NOT NULL,
                num_trades INTEGER DEFAULT 0,
                num_wins INTEGER DEFAULT 0,
                num_losses INTEGER DEFAULT 0,
                max_drawdown TEXT DEFAULT '0'
            )
        """)

        self.conn.commit()

    def save_order(self, order: Order) -> None:
        """
        Save or update an order.

        Args:
            order: Order object to save
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO orders (
                order_id, client_order_id, symbol, side, order_type,
                quantity, price, stop_price, status, filled_quantity,
                avg_fill_price, created_at, updated_at, fees
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                order.order_id,
                order.client_order_id,
                order.symbol,
                order.side.value,
                order.order_type.value,
                str(order.quantity),
                str(order.price) if order.price else None,
                str(order.stop_price) if order.stop_price else None,
                order.status.value,
                str(order.filled_quantity),
                str(order.avg_fill_price) if order.avg_fill_price else None,
                order.created_at.isoformat(),
                order.updated_at.isoformat() if order.updated_at else None,
                str(order.fees),
            ),
        )

        self.conn.commit()
        logger.debug(f"Saved order: {order.order_id}")

    def save_fill(self, fill: Fill) -> None:
        """
        Save a fill.

        Args:
            fill: Fill object to save
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO fills (
                fill_id, order_id, symbol, side, quantity, price, fee, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                fill.fill_id,
                fill.order_id,
                fill.symbol,
                fill.side.value,
                str(fill.quantity),
                str(fill.price),
                str(fill.fee),
                fill.timestamp.isoformat(),
            ),
        )

        self.conn.commit()
        logger.debug(f"Saved fill: {fill.fill_id}")

    def save_trade(self, trade: Trade) -> None:
        """
        Save a closed trade.

        Args:
            trade: Trade object to save
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO trades (
                trade_id, symbol, side, entry_price, exit_price, quantity,
                entry_time, exit_time, pnl, pnl_percent, fees, strategy, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                trade.trade_id,
                trade.symbol,
                trade.side.value,
                str(trade.entry_price),
                str(trade.exit_price) if trade.exit_price else None,
                str(trade.quantity),
                trade.entry_time.isoformat(),
                trade.exit_time.isoformat() if trade.exit_time else None,
                str(trade.pnl) if trade.pnl else None,
                str(trade.pnl_percent) if trade.pnl_percent else None,
                str(trade.fees),
                trade.strategy,
                str(trade.tags),
            ),
        )

        self.conn.commit()
        logger.debug(f"Saved trade: {trade.trade_id}")

    def get_orders(
        self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None, limit: int = 100
    ) -> List[Order]:
        """
        Get orders with optional filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status
            limit: Maximum number of orders

        Returns:
            List of Order objects
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM orders WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            orders.append(self._row_to_order(dict(row)))

        return orders

    def get_trades(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Trade]:
        """
        Get closed trades.

        Args:
            symbol: Filter by symbol
            limit: Maximum number of trades

        Returns:
            List of Trade objects
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY entry_time DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        trades = []
        for row in rows:
            trades.append(self._row_to_trade(dict(row)))

        return trades

    def save_account_snapshot(
        self, equity: Decimal, cash: Decimal, positions_value: Decimal,
        unrealized_pnl: Decimal, realized_pnl: Decimal
    ) -> None:
        """
        Save account snapshot.

        Args:
            equity: Total equity
            cash: Available cash
            positions_value: Value of all positions
            unrealized_pnl: Unrealized P&L
            realized_pnl: Realized P&L
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO account_snapshots (
                timestamp, equity, cash, positions_value, unrealized_pnl, realized_pnl
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.utcnow().isoformat(),
                str(equity),
                str(cash),
                str(positions_value),
                str(unrealized_pnl),
                str(realized_pnl),
            ),
        )

        self.conn.commit()

    def get_metrics(self, days: int = 30) -> dict:
        """
        Get trading metrics.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with metrics
        """
        cursor = self.conn.cursor()

        # Get recent account snapshots
        cursor.execute(
            """
            SELECT * FROM account_snapshots
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (days * 24,),  # Hourly snapshots
        )

        snapshots = [dict(row) for row in cursor.fetchall()]

        if not snapshots:
            return self._empty_metrics()

        # Calculate metrics
        latest = snapshots[0]
        oldest = snapshots[-1]

        starting_equity = Decimal(oldest["equity"])
        ending_equity = Decimal(latest["equity"])
        total_pnl = ending_equity - starting_equity
        total_pnl_pct = (total_pnl / starting_equity * 100) if starting_equity > 0 else Decimal("0")

        # Get trades
        cursor.execute("SELECT * FROM trades WHERE exit_time IS NOT NULL")
        trades = [dict(row) for row in cursor.fetchall()]

        num_trades = len(trades)
        num_wins = sum(1 for t in trades if Decimal(t["pnl"] or "0") > 0)
        num_losses = sum(1 for t in trades if Decimal(t["pnl"] or "0") < 0)
        win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0

        # Calculate drawdown
        equity_curve = [Decimal(s["equity"]) for s in reversed(snapshots)]
        max_drawdown = self._calculate_max_drawdown(equity_curve)

        return {
            "starting_equity": float(starting_equity),
            "ending_equity": float(ending_equity),
            "total_pnl": float(total_pnl),
            "total_pnl_pct": float(total_pnl_pct),
            "num_trades": num_trades,
            "num_wins": num_wins,
            "num_losses": num_losses,
            "win_rate": win_rate,
            "max_drawdown_pct": float(max_drawdown),
        }

    def _calculate_max_drawdown(self, equity_curve: List[Decimal]) -> Decimal:
        """Calculate maximum drawdown from equity curve."""
        if not equity_curve:
            return Decimal("0")

        peak = equity_curve[0]
        max_dd = Decimal("0")

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else Decimal("0")
            max_dd = max(max_dd, dd)

        return max_dd

    def _empty_metrics(self) -> dict:
        """Return empty metrics dict."""
        return {
            "starting_equity": 100000.0,
            "ending_equity": 100000.0,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "num_trades": 0,
            "num_wins": 0,
            "num_losses": 0,
            "win_rate": 0.0,
            "max_drawdown_pct": 0.0,
        }

    def _row_to_order(self, row: dict) -> Order:
        """Convert database row to Order object."""
        from backend.engine.utils.types import OrderSide, OrderType

        return Order(
            order_id=row["order_id"],
            client_order_id=row["client_order_id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            order_type=OrderType(row["order_type"]),
            quantity=Decimal(row["quantity"]),
            price=Decimal(row["price"]) if row["price"] else None,
            stop_price=Decimal(row["stop_price"]) if row["stop_price"] else None,
            status=OrderStatus(row["status"]),
            filled_quantity=Decimal(row["filled_quantity"]),
            avg_fill_price=Decimal(row["avg_fill_price"]) if row["avg_fill_price"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            fees=Decimal(row["fees"]),
        )

    def _row_to_trade(self, row: dict) -> Trade:
        """Convert database row to Trade object."""
        from backend.engine.utils.types import OrderSide

        return Trade(
            trade_id=row["trade_id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            entry_price=Decimal(row["entry_price"]),
            exit_price=Decimal(row["exit_price"]) if row["exit_price"] else None,
            quantity=Decimal(row["quantity"]),
            entry_time=datetime.fromisoformat(row["entry_time"]),
            exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
            pnl=Decimal(row["pnl"]) if row["pnl"] else None,
            pnl_percent=Decimal(row["pnl_percent"]) if row["pnl_percent"] else None,
            fees=Decimal(row["fees"]),
            strategy=row["strategy"],
            tags=eval(row["tags"]) if row["tags"] else {},
        )

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
        logger.info("Closed SQLiteStore connection")
