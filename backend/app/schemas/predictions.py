"""MiroFish swarm-prediction schemas.

Adapted from the MiroFish swarm-intelligence prediction engine (AGPL-3.0,
github.com/666ghj/MiroFish): a population of agents with distinct personas
reacts to a seed snapshot extracted from real market data, interacts over
several simulation rounds (social influence / herding), and the emergent
consensus is aggregated into a direction, conviction, and price forecast.

Kept self-contained and deterministic (no LLM/DB/graph dependencies) so the
prediction pipeline always returns a complete, CI-testable result. An LLM
can be wired in later behind a key; the deterministic path stays the default
and the fallback.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SwarmDirection(str, Enum):
    """Emergent consensus direction of the agent swarm."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SwarmRoundSnapshot(BaseModel):
    """Opinion distribution of the swarm after one simulation round."""

    round: int
    bullish_pct: float = Field(..., ge=0.0, le=100.0)
    bearish_pct: float = Field(..., ge=0.0, le=100.0)
    neutral_pct: float = Field(..., ge=0.0, le=100.0)
    consensus: float = Field(..., ge=-1.0, le=1.0)


class SwarmPredictionSummary(BaseModel):
    """Compact prediction embedded in signals, scans, and agent analysis."""

    direction: SwarmDirection
    conviction: int = Field(..., ge=0, le=100)
    predicted_change_percent: float
    target_price: Optional[float] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class SwarmPrediction(BaseModel):
    """Full MiroFish-style swarm prediction for one symbol."""

    symbol: str
    name: Optional[str] = None
    direction: SwarmDirection
    conviction: int = Field(..., ge=0, le=100)
    predicted_change_percent: float
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    target_low: Optional[float] = None
    target_high: Optional[float] = None
    horizon: str = "5 sessions (swing)"
    confidence: float = Field(..., ge=0.0, le=1.0)
    agents_total: int = 0
    agents_bullish: int = 0
    agents_bearish: int = 0
    agents_neutral: int = 0
    rounds: List[SwarmRoundSnapshot] = Field(default_factory=list)
    key_drivers: List[str] = Field(default_factory=list)
    report: str = ""
    timestamp: datetime
    source: str = "unavailable"  # yfinance | angel_one | kite | mock | unavailable
    status: str = "unavailable"  # live | mock | unavailable


class PredictionListResponse(BaseModel):
    total: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    results: List[SwarmPrediction]
    generated_at: datetime
    data_timestamp: Optional[datetime] = None
    source: str = "unavailable"
    is_stale: bool = False
