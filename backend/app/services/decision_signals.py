"""Decision Signals service.

Builds DecisionSignals from the strategy-templates engine, derives
risk/reward, applies expiry, and supports filtering. Self-contained: no
external AI or database dependencies; mirrors the DecisionSignal lifecycle
concept from daily_stock_analysis (MIT).
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog

from app.schemas.decision_signals import (
    DecisionAction,
    DecisionHorizon,
    DecisionSignal,
    DecisionStatus,
)
from app.services.strategy_templates import (
    StrategyEval,
    evaluate_all,
    evaluate_template_universe,
    load_all_templates,
    load_template,
)

logger = structlog.get_logger()

# Signals are considered stale after one trading day.
SIGNAL_TTL = timedelta(days=1)


def _risk_reward(entry: Optional[float], stop: Optional[float], target: Optional[float]) -> Optional[float]:
    if not entry or not stop or not target:
        return None
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return None
    return round(reward / risk, 2)


def _eval_to_signal(idx: int, ev: StrategyEval) -> DecisionSignal:
    rr = _risk_reward(ev.entry, ev.stop_loss, ev.target)
    status = DecisionStatus.ACTIVE if ev.action != DecisionAction.AVOID else DecisionStatus.EXPIRED
    expires_at = ev.timestamp + SIGNAL_TTL
    if datetime.utcnow() > expires_at:
        status = DecisionStatus.EXPIRED
    return DecisionSignal(
        id=f"{ev.strategy}-{ev.symbol}-{ev.timestamp.strftime('%Y%m%d%H')}-{idx}",
        symbol=ev.symbol,
        name=ev.name,
        strategy=ev.strategy,
        display_name=ev.display_name,
        category=ev.category,
        action=DecisionAction(ev.action),
        score=ev.score,
        confidence=ev.confidence,
        entry=ev.entry,
        stop_loss=ev.stop_loss,
        target=ev.target,
        horizon=DecisionHorizon(ev.horizon),
        risk_reward=rr,
        reasons=ev.reasons,
        status=status,
        timestamp=ev.timestamp,
    )


def build_signals(
    strategy: Optional[str] = None,
    limit_per_template: int = 25,
) -> List[DecisionSignal]:
    evals: List[StrategyEval] = []
    if strategy:
        tpl = load_template(strategy)
        if tpl is None:
            return []
        evals = evaluate_template_universe(tpl, limit=limit_per_template)
    else:
        evals = evaluate_all(limit_per_template=limit_per_template)

    signals = [_eval_to_signal(i, ev) for i, ev in enumerate(evals)]
    logger.info(
        "decision_signals_built",
        strategy=strategy,
        count=len(signals),
    )
    return signals


def list_signals(
    action: Optional[DecisionAction] = None,
    strategy: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
) -> List[DecisionSignal]:
    signals = build_signals(strategy=strategy, limit_per_template=25)
    if action is not None:
        signals = [s for s in signals if s.action == action]
    if min_score is not None:
        signals = [s for s in signals if s.score >= min_score]
    signals = signals[:limit]
    return signals


def get_signal(signal_id: str) -> Optional[DecisionSignal]:
    for s in build_signals():
        if s.id == signal_id:
            return s
    return None


def available_strategies() -> List[str]:
    return list(load_all_templates().keys())
