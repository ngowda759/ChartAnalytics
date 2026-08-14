"""Debate agents — ported/inspired by TradingAgents (Apache-2.0).

Deterministic bull/bear researchers and aggressive/conservative/neutral risk
debators. Each side builds an evidence-based argument from the analyst reports
and the composite score; the framework's "winner" is decided by which side's
score carries the debate.
"""

from dataclasses import dataclass
from typing import List

from app.services.trading_agents.analysts import RawAnalyst
from app.services.trading_agents.rating import rating_for_score


@dataclass
class DebateTurnRaw:
    speaker: str
    stance: str
    argument: str
    score: int


@dataclass
class DebateResultRaw:
    turns: List[DebateTurnRaw]
    winner: str
    summary: str
    score: int


def _bull_points(analysts: List[RawAnalyst]) -> List[str]:
    return [p for a in analysts for p in a.key_points if a.score >= 55]


def _bear_points(analysts: List[RawAnalyst]) -> List[str]:
    return [p for a in analysts for p in a.key_points if a.score <= 45]


def investment_debate(analysts: List[RawAnalyst], composite: int) -> DebateResultRaw:
    """Bull vs Bear researchers debating the analyst reports."""
    bull_pts = _bull_points(analysts) or ["No strongly bullish points surfaced."]
    bear_pts = _bear_points(analysts) or ["No strongly bearish points surfaced."]

    bull_score = max(0, composite)
    bear_score = max(0, 100 - composite)

    bull_arg = (
        "Bull case: " + "; ".join(bull_pts[:3])
        + f". Composite bullishness {composite}/100 supports accumulation."
    )
    bear_arg = (
        "Bear case: " + "; ".join(bear_pts[:3])
        + f". Downside risk weighs against {composite}/100 bullishness."
    )

    turns = [
        DebateTurnRaw("Bull Researcher", "bull", bull_arg, bull_score),
        DebateTurnRaw("Bear Researcher", "bear", bear_arg, bear_score),
    ]
    winner = "bull" if bull_score >= bear_score else "bear"
    rating = rating_for_score(composite)
    summary = f"Debate favours {winner}; provisional rating {rating}."
    return DebateResultRaw(turns, winner, summary, composite)


def risk_debate(
    analysts: List[RawAnalyst],
    composite: int,
    trader_action: str,
) -> DebateResultRaw:
    """Aggressive / Conservative / Neutral risk analysts debate the trader call."""
    rating = rating_for_score(composite)

    aggressive = (
        f"Aggressive: rating {rating} justifies full-sized entry; momentum and "
        f"analyst composite ({composite}) favour taking risk for upside."
    )
    conservative = (
        f"Conservative: protect capital first; the {rating} rating and "
        f"composite ({composite}) argue for trimmed size and a tight stop."
    )
    neutral = (
        f"Neutral: balance the two — a partial position with defined risk "
        f"fits the {rating} view without overcommitting."
    )

    turns = [
        DebateTurnRaw("Aggressive Risk Analyst", "aggressive", aggressive, min(100, composite + 5)),
        DebateTurnRaw("Conservative Risk Analyst", "conservative", conservative, max(0, 100 - composite)),
        DebateTurnRaw("Neutral Risk Analyst", "neutral", neutral, composite),
    ]
    # The conservative stance wins when evidence is weak; aggressive wins when strong.
    if composite >= 60:
        winner = "aggressive"
    elif composite <= 40:
        winner = "conservative"
    else:
        winner = "neutral"
    summary = f"Risk debate leans {winner} for a {trader_action} action ({rating})."
    return DebateResultRaw(turns, winner, summary, composite)
