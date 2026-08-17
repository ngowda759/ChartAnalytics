from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ScanType(str, Enum):
    BREAKOUT = "breakout"
    EMA_CROSS = "ema_cross"
    VOLUME_SPIKE = "volume_spike"
    OI_BUILDUP = "oi_buildup"
    GAPPER = "gapper"
    RSI_EXTREME = "rsi_extreme"


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ScanFilters(BaseModel):
    scan_types: List[ScanType]
    min_confidence: float = 60.0
    symbols: Optional[List[str]] = None
    indices: Optional[List[str]] = None


class ScanResult(BaseModel):
    id: str
    symbol: str
    name: str
    scan_type: ScanType
    direction: SignalDirection
    confidence: float
    price: float
    change_percent: float
    volume_ratio: Optional[float] = None
    details: Dict[str, float]
    timestamp: datetime


class ScanSummary(BaseModel):
    total_results: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_signals: List[ScanResult]
    by_type: Dict[str, int]


class BreakoutSignal(BaseModel):
    symbol: str
    type: str  # "resistance", "support"
    breakout_price: float
    current_price: float
    distance_percent: float
    volume_ratio: float
    atr: float
    confidence: float


class EMACrossSignal(BaseModel):
    symbol: str
    cross_type: str  # "golden_cross", "death_cross"
    fast_ema: float
    slow_ema: float
    price: float
    distance_from_cross: float
    rsi: float
    volume_ratio: float
    confidence: float


class VolumeSignal(BaseModel):
    symbol: str
    type: str  # "spike_up", "spike_down"
    current_volume: int
    avg_volume: int
    volume_ratio: float
    price_change: float
    delivery_percent: Optional[float] = None
    confidence: float


class OISignal(BaseModel):
    symbol: str
    type: str  # "buildup", "unwinding"
    change_call_oi: int
    change_put_oi: int
    price_change: float
    pcr: float
    interpretation: str
    confidence: float


class ScreenerRow(BaseModel):
    symbol: str
    name: Optional[str] = None
    ltp: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    # `extra` carries both numeric OHLC fields (open/high/low/...) and string
    # metadata such as {"source": "synthetic_fallback"}. Typed as a free-form
    # dict so metadata is not coerced/broken by a numeric-only type contract.
    extra: Optional[Dict[str, Any]] = None


class ScreenerWidget(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    timeframe: str = "daily"
    columns: List[str] = ["symbol", "change_percent", "ltp", "volume"]
    rows: List[ScreenerRow]
    last_updated: datetime
    # Per-widget provenance so the UI can render live / cached / fallback /
    # unavailable states truthfully instead of guessing from the rows.
    status: str = "live"  # live | cached | fallback | unavailable | error
    source: str = "nse"  # nse | broker | cache | synthetic | none
    error: Optional[str] = None


class ScreenerDashboard(BaseModel):
    id: str
    name: str
    author: str
    description: Optional[str] = None
    widgets: List[ScreenerWidget]


class ScreenerDashboardResponse(BaseModel):
    """Envelope for the NSE scan dashboard.

    ``source`` is "live" when every dataset came from NSE, "cached" when
    cached real data was served because NSE was temporarily unavailable,
    "synthetic_fallback" when any widget used labelled fallback data, and
    "unavailable" when no data (live or cached) could be obtained for any
    widget. ``warnings`` lists unavailable datasets. ``generated_at`` /
    ``data_timestamp`` let the UI show freshness + staleness.
    """

    success: bool = True
    source: str = "live"
    data: ScreenerDashboard
    warnings: List[str] = []
    generated_at: datetime
    data_timestamp: Optional[datetime] = None
    is_stale: bool = False
