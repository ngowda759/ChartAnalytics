from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class OptionData(BaseModel):
    strike: float
    oi: int
    change_oi: int
    volume: int
    iv: float
    ltp: float
    bid: float
    ask: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


class OptionChain(BaseModel):
    symbol: str
    expiry: str
    spot_price: float
    timestamp: datetime
    underlying_change: float
    calls: List[OptionData]
    puts: List[OptionData]
    pcr: float
    max_pain: float
    total_call_oi: int
    total_put_oi: int
    source: str = "unavailable"
    status: str = "unavailable"


class PCRAnalysis(BaseModel):
    value: float
    interpretation: str  # "bullish", "bearish", "neutral"
    trend: str  # "rising", "falling", "stable"
    historical_values: List[float]
    source: str = "unavailable"
    timestamp: Optional[datetime] = None


class OIAnalysis(BaseModel):
    type: str  # "buildup", "unwinding", "short_covering", "long_unwinding"
    call_oi: int
    put_oi: int
    change_call_oi: int
    change_put_oi: int
    interpretation: str
    source: str = "unavailable"
    timestamp: Optional[datetime] = None


class MaxPainAnalysis(BaseModel):
    max_pain: float
    distance_from_spot: float
    call_pain_points: Dict[str, int]
    put_pain_points: Dict[str, int]
    source: str = "unavailable"


class OptionSignal(BaseModel):
    type: str
    strike: float
    side: OptionType
    confidence: float
    interpretation: str
