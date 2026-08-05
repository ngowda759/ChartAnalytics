from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class InsightType(str, Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    SUPPORT_RESISTANCE = "support_resistance"
    BREAKOUT = "breakout"
    GENERAL = "general"


class BiasDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class AIInsight(BaseModel):
    id: str
    symbol: str
    type: InsightType
    title: str
    description: str
    confidence: float  # 0-100
    bias: BiasDirection
    reasoning: str
    indicators: List[str]
    timestamp: datetime


class ChartPattern(BaseModel):
    type: str
    confidence: float
    description: str


class TradingLevels(BaseModel):
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    risk_reward: float


class ChartAnalysis(BaseModel):
    id: str
    symbol: str
    patterns: List[ChartPattern]
    levels: TradingLevels
    bias: BiasDirection
    confidence: float
    reasoning: str
    timestamp: datetime


class ChatMessage(BaseModel):
    id: Optional[str] = None
    role: str = "user"  # "user", "assistant", "system"
    content: str
    timestamp: Optional[datetime] = None


class ChatResponse(BaseModel):
    message: ChatMessage
    sources: Optional[List[str]] = None


class TradeReview(BaseModel):
    id: str
    trade_id: str
    entry_timing: int  # 1-10 rating
    exit_timing: int  # 1-10 rating
    risk_management: int  # 1-10 rating
    overall_quality: int  # 1-10 rating
    strengths: List[str]
    improvements: List[str]
    psychology_notes: str
    timestamp: datetime
