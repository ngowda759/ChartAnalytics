"""TradingAgents-style agent analysis schemas.

Adapted from the TradingAgents framework (Apache-2.0,
github.com/TauricResearch/TradingAgents): the 5-tier portfolio rating,
3-tier trader action, and the structured decision artifacts produced by the
analyst → debate → research-manager → trader → risk-debate →
portfolio-manager pipeline. Kept self-contained (no LLM/DB dependencies).
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PortfolioRating(str, Enum):
    """5-tier rating used by the Research Manager and Portfolio Manager."""

    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


class TraderAction(str, Enum):
    """3-tier transaction direction used by the Trader."""

    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


class SentimentBand(str, Enum):
    """Discrete sentiment direction produced by the Sentiment Analyst."""

    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


class AnalystReport(BaseModel):
    """A single analyst's report (market / fundamentals / news / sentiment)."""

    role: str
    summary: str
    score: int = Field(..., ge=0, le=100, description="Bullishness score, 0-100")
    key_points: List[str] = Field(default_factory=list)


class DebateTurn(BaseModel):
    """One turn in the bull/bear or risk debate."""

    speaker: str
    stance: str
    argument: str
    score: int = Field(..., ge=0, le=100)


class DebateResult(BaseModel):
    """Outcome of a debate round."""

    turns: List[DebateTurn] = Field(default_factory=list)
    winner: str
    summary: str


class ResearchPlan(BaseModel):
    """Structured investment plan produced by the Research Manager."""

    recommendation: PortfolioRating
    rationale: str
    strategic_actions: str


class TraderProposal(BaseModel):
    """Structured transaction proposal produced by the Trader."""

    action: TraderAction
    reasoning: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_sizing: Optional[str] = None


class PortfolioDecision(BaseModel):
    """Structured final decision produced by the Portfolio Manager."""

    rating: PortfolioRating
    executive_summary: str
    investment_thesis: str
    price_target: Optional[float] = None
    time_horizon: Optional[str] = None


class AgentAnalysisResult(BaseModel):
    """Full TradingAgents-style pipeline output for one symbol."""

    symbol: str
    name: Optional[str] = None
    timestamp: datetime
    analysts: List[AnalystReport]
    investment_debate: DebateResult
    research_plan: ResearchPlan
    trader_proposal: TraderProposal
    risk_debate: DebateResult
    final_decision: PortfolioDecision
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = "synthetic"
    is_stale: bool = False


class AgentAnalysisListResponse(BaseModel):
    total: int
    buy_count: int
    sell_count: int
    hold_count: int
    results: List[AgentAnalysisResult]
    generated_at: datetime
    data_timestamp: Optional[datetime] = None
    source: str = "synthetic"
    is_stale: bool = False
