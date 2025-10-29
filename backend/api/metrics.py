"""
Metrics endpoints for monitoring trading performance.
"""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from backend.engine.store.sqlite import SQLiteStore
from backend.engine.utils.config import get_settings

router = APIRouter()
settings = get_settings()
store = SQLiteStore(settings.database_url.replace("sqlite:///", ""))


class MetricsResponse(BaseModel):
    """Trading metrics response."""

    starting_equity: float
    ending_equity: float
    total_pnl: float
    total_pnl_pct: float
    num_trades: int
    num_wins: int
    num_losses: int
    win_rate: float
    max_drawdown_pct: float


class PositionResponse(BaseModel):
    """Position response."""

    symbol: str
    side: str
    quantity: str
    entry_price: str
    current_price: str
    unrealized_pnl: str
    unrealized_pnl_pct: str


class TradeResponse(BaseModel):
    """Trade response."""

    trade_id: str
    symbol: str
    side: str
    entry_price: str
    exit_price: str
    quantity: str
    pnl: str
    pnl_percent: str
    entry_time: str
    exit_time: str


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(days: int = 30) -> Dict:
    """
    Get trading performance metrics.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        Trading metrics including P&L, win rate, drawdown
    """
    metrics = store.get_metrics(days=days)
    return metrics


@router.get("/metrics/positions", response_model=List[PositionResponse])
async def get_positions() -> List[Dict]:
    """
    Get current open positions.

    Returns:
        List of current positions
    """
    # Import here to avoid circular dependency
    from backend.engine.broker.coinbase_paper import CoinbasePaperBroker

    broker = CoinbasePaperBroker(settings)
    positions = broker.get_positions()

    return [
        {
            "symbol": pos.symbol,
            "side": pos.side.value,
            "quantity": str(pos.quantity),
            "entry_price": str(pos.entry_price),
            "current_price": str(pos.current_price) if pos.current_price else str(pos.entry_price),
            "unrealized_pnl": str(pos.unrealized_pnl) if pos.unrealized_pnl else "0",
            "unrealized_pnl_pct": str(pos.unrealized_pnl_percent) if pos.unrealized_pnl_percent else "0",
        }
        for pos in positions
    ]


@router.get("/metrics/trades", response_model=List[TradeResponse])
async def get_trades(symbol: str = None, limit: int = 50) -> List[Dict]:
    """
    Get recent closed trades.

    Args:
        symbol: Filter by symbol (optional)
        limit: Maximum number of trades (default: 50)

    Returns:
        List of closed trades
    """
    trades = store.get_trades(symbol=symbol, limit=limit)

    return [
        {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "entry_price": str(trade.entry_price),
            "exit_price": str(trade.exit_price) if trade.exit_price else "0",
            "quantity": str(trade.quantity),
            "pnl": str(trade.pnl) if trade.pnl else "0",
            "pnl_percent": str(trade.pnl_percent) if trade.pnl_percent else "0",
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
        }
        for trade in trades
    ]


@router.get("/metrics/equity")
async def get_equity_curve(hours: int = 168) -> Dict:
    """
    Get equity curve data for charting.

    Args:
        hours: Number of hours to look back (default: 168 = 1 week)

    Returns:
        Equity curve data points
    """
    import sqlite3

    conn = sqlite3.connect(settings.database_url.replace("sqlite:///", ""))
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp, equity, unrealized_pnl, realized_pnl
        FROM account_snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (hours * 2,),  # Get more points for smoother curve
    )

    rows = cursor.fetchall()
    conn.close()

    data_points = [
        {
            "timestamp": row[0],
            "equity": float(row[1]),
            "unrealized_pnl": float(row[2]),
            "realized_pnl": float(row[3]),
        }
        for row in reversed(rows)  # Reverse to get chronological order
    ]

    return {"data": data_points}
