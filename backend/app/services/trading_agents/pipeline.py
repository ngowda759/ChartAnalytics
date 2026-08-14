"""TradingAgents-style pipeline — orchestrates the deterministic agent team.

Adapted from TradingAgents (Apache-2.0). Sequence mirrors the framework:

  analysts → bull/bear investment debate → Research Manager → Trader →
  aggressive/conservative/neutral risk debate → Portfolio Manager.

Runs offline with no LLM: every agent is a deterministic function of the
screener-engine OHLC and the indicators package, so the pipeline always
returns a complete result (never empty) and is CI-testable.
"""

from datetime import datetime
from typing import List, Optional

from app.schemas.agent_analysis import (
    AgentAnalysisResult,
    AnalystReport,
    DebateResult,
    DebateTurn,
    PortfolioDecision,
    PortfolioRating,
    ResearchPlan,
    TraderAction,
    TraderProposal,
)
from app.services.screener_engine import Candle, _generate_ohlc, _UNIVERSE
from app.services.trading_agents.analysts import (
    RawAnalyst,
    composite_score,
    run_analysts,
)
from app.services.trading_agents.debate import investment_debate, risk_debate
from app.services.trading_agents.rating import (
    action_for_rating,
    rating_for_score,
)


def _levels(candles: List[Candle], action: str) -> tuple:
    price = candles[-1].close
    if action == "Buy":
        entry = round(price, 2)
        stop = round(price * 0.97, 2)
        target = round(price * 1.06, 2)
        return entry, stop, target
    if action == "Sell":
        entry = round(price, 2)
        stop = round(price * 1.03, 2)
        target = round(price * 0.94, 2)
        return entry, stop, target
    return round(price, 2), None, None


def _research_plan(composite: int, analysts: List[RawAnalyst]) -> ResearchPlan:
    rating = rating_for_score(composite)
    top = ", ".join(f"{a.role}={a.score}" for a in analysts)
    rationale = (
        f"Composite bullishness {composite}/100 ({top}). "
        f"The {'bull' if composite >= 50 else 'bear'} side carried the debate."
    )
    actions = {
        "Buy": "Accumulate on weakness; size up with a trailing stop.",
        "Overweight": "Gradually increase exposure; add on pullbacks.",
        "Hold": "Maintain current position; no new action warranted.",
        "Underweight": "Trim exposure; take partial profits.",
        "Sell": "Exit or avoid; stand aside until setup rebuilds.",
    }.get(rating, "Hold and monitor.")
    return ResearchPlan(
        recommendation=PortfolioRating(rating),
        rationale=rationale,
        strategic_actions=actions,
    )


def _trader_proposal(composite: int, candles: List[Candle]) -> TraderProposal:
    rating = rating_for_score(composite)
    action = action_for_rating(rating)
    entry, stop, _target = _levels(candles, action)
    sizing = {
        "Buy": "5% of portfolio; add 3% on confirmation",
        "Sell": "Reduce 5% of position",
        "Hold": "No change; observe",
    }.get(action, "No change")
    reasoning = (
        f"Translating the {rating} research plan into a {action} transaction. "
        f"Anchored in analyst composite {composite}/100."
    )
    return TraderProposal(
        action=TraderAction(action),
        reasoning=reasoning,
        entry_price=entry,
        stop_loss=stop,
        position_sizing=sizing,
    )


def _final_decision(
    composite: int,
    risk_winner: str,
    plan: ResearchPlan,
    candles: List[Candle],
) -> PortfolioDecision:
    rating = plan.recommendation
    action = action_for_rating(rating.value)
    entry, stop, target = _levels(candles, action)
    horizon = {
        "Buy": "2-6 weeks (swing)",
        "Overweight": "2-6 weeks (swing)",
        "Hold": "Watch; re-evaluate in 1 week",
        "Underweight": "1-3 weeks",
        "Sell": "Immediate; re-evaluate after setup resets",
    }.get(rating.value, "1-3 weeks")

    summary = (
        f"Rating {rating.value}: {action} with risk-debate leaning {risk_winner}. "
        f"Entry ~₹{entry}, stop ~₹{stop if stop else 'n/a'}, target ~₹{target if target else 'n/a'}."
    )
    thesis = (
        f"Analyst composite {composite}/100 resolved to {rating.value} after the "
        f"bull/bear and risk debates. Execute a {action} with the risk envelope "
        f"shaped by the {risk_winner} risk stance."
    )
    return PortfolioDecision(
        rating=rating,
        executive_summary=summary,
        investment_thesis=thesis,
        price_target=target,
        time_horizon=horizon,
    )


def analyze_symbol(symbol: str, name: Optional[str] = None, base: Optional[float] = None) -> AgentAnalysisResult:
    meta = next((m for m in _UNIVERSE if m["symbol"] == symbol), None)
    if meta is None and base is None:
        base = 1000.0
    if meta is not None:
        name = name or meta.get("name")
        base = base or meta["base"]
    elif base is None:
        base = 1000.0

    candles = _generate_ohlc(symbol, float(base))
    raw_analysts = run_analysts(candles)
    composite, _ = composite_score(raw_analysts)

    inv = investment_debate(raw_analysts, composite)
    plan = _research_plan(composite, raw_analysts)
    trader = _trader_proposal(composite, candles)
    risk = risk_debate(raw_analysts, composite, trader.action.value)
    decision = _final_decision(composite, risk.winner, plan, candles)

    analysts_out = [
        AnalystReport(
            role=a.role, summary=a.summary, score=a.score, key_points=a.key_points
        )
        for a in raw_analysts
    ]
    inv_out = DebateResult(
        turns=[DebateTurn(speaker=t.speaker, stance=t.stance, argument=t.argument, score=t.score) for t in inv.turns],
        winner=inv.winner,
        summary=inv.summary,
    )
    risk_out = DebateResult(
        turns=[DebateTurn(speaker=t.speaker, stance=t.stance, argument=t.argument, score=t.score) for t in risk.turns],
        winner=risk.winner,
        summary=risk.summary,
    )
    confidence = round(composite / 100.0, 2)

    return AgentAnalysisResult(
        symbol=symbol,
        name=name,
        timestamp=datetime.utcnow(),
        analysts=analysts_out,
        investment_debate=inv_out,
        research_plan=plan,
        trader_proposal=trader,
        risk_debate=risk_out,
        final_decision=decision,
        confidence=confidence,
    )


def analyze_universe(limit: int = 25) -> List[AgentAnalysisResult]:
    results: List[AgentAnalysisResult] = []
    for meta in _UNIVERSE:
        results.append(analyze_symbol(meta["symbol"], meta.get("name"), meta["base"]))
        if len(results) >= limit:
            break
    # Sort by final rating bullishness, then confidence.
    from app.services.trading_agents.rating import rating_sign
    results.sort(
        key=lambda r: (rating_sign(r.final_decision.rating.value), r.confidence),
        reverse=True,
    )
    return results
