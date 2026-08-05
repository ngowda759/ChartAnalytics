from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MarketQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    previous_close: float
    volume: int
    timestamp: datetime


class IndexQuote(MarketQuote):
    is_index: bool = True


class OHLC(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalData(BaseModel):
    symbol: str
    interval: str
    data: List[OHLC]
    from_date: datetime
    to_date: datetime


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    price: float
    change_percent: float


class WatchlistCreate(BaseModel):
    symbol: str
