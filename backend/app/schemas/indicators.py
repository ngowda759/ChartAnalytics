from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class IndicatorType(str, Enum):
    EMA = "ema"
    SMA = "sma"
    RSI = "rsi"
    MACD = "macd"
    VWAP = "vwap"
    SUPERTREND = "supertrend"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR = "atr"
    ADX = "adx"
    STOCHASTIC = "stochastic"
    OBV = "obv"


class TrendDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class EMAData(BaseModel):
    ema_9: float
    ema_20: float
    ema_50: float
    ema_100: Optional[float] = None
    ema_200: float
    trend: TrendDirection
    crossover: Optional[str] = None


class MACDData(BaseModel):
    macd: float
    signal: float
    histogram: float
    crossover: str  # "bullish", "bearish", "none"
    crossover_strength: Optional[float] = None


class SupertrendData(BaseModel):
    value: float
    direction: str  # "up", "down"
    is_breakout: bool
    previous_direction: Optional[str] = None


class BollingerBandsData(BaseModel):
    upper: float
    middle: float
    lower: float
    bandwidth: float
    position: float  # 0-100 percentage position within bands


class RSIData(BaseModel):
    value: float
    signal: str  # "overbought", "oversold", "neutral"
    divergence: Optional[str] = None


class ATRData(BaseModel):
    value: float
    percent: float
    signal: str  # "high", "medium", "low"


class ADXData(BaseModel):
    value: float
    trend_strength: str  # "strong", "moderate", "weak"
    plus_di: float
    minus_di: float


class VWAPData(BaseModel):
    value: float
    distance_from_vwap: float  # percentage
    signal: str  # "above", "below"


class TechnicalIndicators(BaseModel):
    symbol: str
    timestamp: datetime
    price: float
    ema: EMAData
    rsi: RSIData
    macd: MACDData
    vwap: VWAPData
    supertrend: SupertrendData
    bollinger_bands: BollingerBandsData
    atr: ATRData
    adx: ADXData
    overall_signal: str
    confidence: float


class IndicatorHistory(BaseModel):
    timestamp: datetime
    value: float


class IndicatorHistoryResponse(BaseModel):
    indicator: str
    symbol: str
    period: str
    data: List[IndicatorHistory]


class IndicatorComparison(BaseModel):
    symbol: str
    indicators: Dict[str, float]
    correlation: Optional[float] = None
