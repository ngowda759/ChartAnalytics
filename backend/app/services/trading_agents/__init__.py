"""TradingAgents-style multi-agent analysis pipeline.

Adapted from the TradingAgents framework (Apache-2.0,
github.com/TauricResearch/TradingAgents). Deterministic, offline port of the
analyst → debate → manager → trader → risk-debate → portfolio-manager graph.
"""

from app.services.trading_agents.pipeline import analyze_symbol, analyze_universe
from app.services.trading_agents.rating import (
    RATINGS_5_TIER,
    action_for_rating,
    rating_for_score,
    rating_sign,
)

__all__ = [
    "analyze_symbol",
    "analyze_universe",
    "RATINGS_5_TIER",
    "action_for_rating",
    "rating_for_score",
    "rating_sign",
]
