from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class InstrumentType(str, Enum):
    FUTURES = "futures"
    OPTIONS = "options"
    EQUITY = "equity"


class TradeType(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeEntry(BaseModel):
    price: float
    quantity: int
    timestamp: datetime


class TradeExit(BaseModel):
    price: float
    quantity: int
    timestamp: datetime


class Trade(BaseModel):
    id: str
    user_id: str
    symbol: str
    instrument: InstrumentType
    type: TradeType
    entry: TradeEntry
    exit: Optional[TradeExit] = None
    status: TradeStatus
    strategy: str
    tags: List[str] = []
    notes: Optional[str] = None
    screenshots: List[str] = []
    pnl: Optional[float] = None
    fees: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class TradeCreate(BaseModel):
    symbol: str
    instrument: InstrumentType
    type: TradeType
    entry_price: float
    quantity: int
    strategy: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    exit_quantity: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    screenshots: Optional[List[str]] = None


class TradeFilters(BaseModel):
    symbol: Optional[str] = None
    instrument: Optional[InstrumentType] = None
    type: Optional[TradeType] = None
    status: Optional[TradeStatus] = None
    strategy: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class MonthlyReturn(BaseModel):
    month: str
    return_value: float
    trades: int


class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    total_pnl: float
    expectancy: float
    avg_rr: float
    monthly_returns: List[MonthlyReturn]
