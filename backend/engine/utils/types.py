"""
Common type definitions and models for the trading engine.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TimeFrame(str, Enum):
    """Supported timeframes for candles."""

    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


class Candle(BaseModel):
    """OHLCV candle data."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    symbol: str

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: float | Decimal | str) -> Decimal:
        """Convert numeric values to Decimal for precision."""
        return Decimal(str(v))


class Order(BaseModel):
    """Order model."""

    order_id: str
    client_order_id: Optional[str] = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    fees: Decimal = Decimal("0")

    @field_validator("quantity", "price", "stop_price", "filled_quantity", "fees", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: Optional[float | Decimal | str]) -> Optional[Decimal]:
        """Convert numeric values to Decimal for precision."""
        if v is None:
            return None
        return Decimal(str(v))


class Fill(BaseModel):
    """Order fill/execution model."""

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    fee: Decimal
    timestamp: datetime

    @field_validator("quantity", "price", "fee", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: float | Decimal | str) -> Decimal:
        """Convert numeric values to Decimal for precision."""
        return Decimal(str(v))


class Trade(BaseModel):
    """Completed trade model (entry + exit)."""

    trade_id: str
    symbol: str
    side: OrderSide
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: Decimal
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    fees: Decimal = Decimal("0")
    strategy: Optional[str] = None
    tags: dict = Field(default_factory=dict)

    @field_validator(
        "entry_price", "exit_price", "quantity", "pnl", "pnl_percent", "fees", mode="before"
    )
    @classmethod
    def convert_to_decimal(cls, v: Optional[float | Decimal | str]) -> Optional[Decimal]:
        """Convert numeric values to Decimal for precision."""
        if v is None:
            return None
        return Decimal(str(v))


class Position(BaseModel):
    """Current position model."""

    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percent: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

    @field_validator(
        "quantity",
        "entry_price",
        "current_price",
        "unrealized_pnl",
        "unrealized_pnl_percent",
        "stop_loss",
        "take_profit",
        mode="before",
    )
    @classmethod
    def convert_to_decimal(cls, v: Optional[float | Decimal | str]) -> Optional[Decimal]:
        """Convert numeric values to Decimal for precision."""
        if v is None:
            return None
        return Decimal(str(v))


class Account(BaseModel):
    """Account information model."""

    account_id: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    portfolio_value: Decimal
    positions_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    timestamp: datetime

    @field_validator(
        "equity",
        "cash",
        "buying_power",
        "portfolio_value",
        "positions_value",
        "unrealized_pnl",
        "realized_pnl",
        mode="before",
    )
    @classmethod
    def convert_to_decimal(cls, v: float | Decimal | str) -> Decimal:
        """Convert numeric values to Decimal for precision."""
        return Decimal(str(v))
