"""Decision Signals API endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from typing import List, Optional

import structlog

from app.schemas.decision_signals import (
    DecisionAction,
    DecisionSignal,
    DecisionSignalListResponse,
)
from app.services.decision_signals import (
    available_strategies,
    invalidate_signals_cache,
    list_signals,
    signals_cache_age_seconds,
)

logger = structlog.get_logger()
router = APIRouter()

# Signals are derived from synthetic OHLC; mark them as "synthetic" so the UI
# never presents them as live market data.
_SIGNAL_SOURCE = "synthetic"
# Consider cached signals stale once they're older than this (matches cache TTL).
_STALE_AFTER = timedelta(minutes=30)


@router.get("/strategies", response_model=List[str], summary="List available strategies")
async def list_strategies() -> List[str]:
    return available_strategies()


@router.get(
    "/signals",
    response_model=DecisionSignalListResponse,
    summary="List decision signals",
)
async def get_signals(
    action: Optional[DecisionAction] = Query(None, description="Filter by action"),
    strategy: Optional[str] = Query(None, description="Filter by strategy slug"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum score"),
    limit: int = Query(50, ge=1, le=200),
    refresh: bool = Query(False, description="Bypass the cache and regenerate"),
) -> DecisionSignalListResponse:
    if refresh:
        invalidate_signals_cache()
    signals = list_signals(action=action, strategy=strategy, min_score=min_score, limit=limit)
    age = signals_cache_age_seconds()
    now = datetime.utcnow()
    is_stale = age is not None and age > _STALE_AFTER.total_seconds()
    return DecisionSignalListResponse(
        total=len(signals),
        buy_count=sum(1 for s in signals if s.action == DecisionAction.BUY),
        hold_count=sum(1 for s in signals if s.action == DecisionAction.HOLD),
        avoid_count=sum(1 for s in signals if s.action == DecisionAction.AVOID),
        signals=signals,
        generated_at=now,
        data_timestamp=now,
        source=_SIGNAL_SOURCE,
        is_stale=is_stale,
    )


@router.get(
    "/signals/{signal_id}",
    response_model=DecisionSignal,
    summary="Get a single decision signal",
)
async def get_signal(signal_id: str):
    from app.services.decision_signals import get_signal as _get_signal
    from fastapi import HTTPException

    signal = _get_signal(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Decision signal not found")
    return signal
