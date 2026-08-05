from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class StrategyType(str, Enum):
    ORB = "ORB"
    VWAP = "VWAP"
    EMA_CROSSOVER = "EMA_CROSSOVER"
    MOMENTUM = "MOMENTUM"
    SCALPING = "SCALPING"
    OPTION_BUYING = "OPTION_BUYING"
    OPTION_SELLING = "OPTION_SELLING"
    CUSTOM = "CUSTOM"


class StrategyRule(BaseModel):
    id: str
    type: str  # "indicator", "price", "volume", "time", "custom"
    indicator: Optional[str] = None
    condition: str  # ">", "<", "==", ">=", "<=", "crosses_above", "crosses_below"
    value: Any
    operator: Optional[str] = None  # "AND", "OR"


class Strategy(BaseModel):
    id: str
    user_id: str
    name: str
    type: StrategyType
    description: Optional[str] = None
    parameters: Dict[str, Any] = {}
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StrategyCreate(BaseModel):
    name: str
    type: StrategyType
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class BacktestPeriod(BaseModel):
    start_date: datetime
    end_date: datetime


class BacktestMetrics(BaseModel):
    total_return: float
    annualized_return: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    total_trades: int
    avg_trade_duration: int
    recovery_factor: float


class BacktestTrade(BaseModel):
    id: str
    entry_date: datetime
    exit_date: datetime
    symbol: str
    type: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float


class EquityPoint(BaseModel):
    date: datetime
    equity: float
    drawdown: float


class BacktestResult(BaseModel):
    strategy_id: str
    period: BacktestPeriod
    metrics: BacktestMetrics
    equity_curve: List[EquityPoint]
    trades: List[BacktestTrade]


class BacktestParams(BaseModel):
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    symbols: Optional[List[str]] = None
