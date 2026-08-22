"""MiroFish swarm-prediction API endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Query

import structlog

from app.schemas.predictions import (
    PredictionListResponse,
    SwarmDirection,
    SwarmPrediction,
)
from app.services.mirofish import (
    invalidate_prediction_cache,
    predict_symbol,
    predict_universe,
    prediction_cache_age_seconds,
)

logger = structlog.get_logger()
router = APIRouter()

_STALE_AFTER = timedelta(minutes=30)


def _prediction_source() -> str:
    """Active market-data source for predictions."""
    from app.services import market_data

    p = market_data.get_market_data_provider()
    return p if p != market_data.SOURCE_UNAVAILABLE else "unavailable"


@router.get(
    "",
    response_model=PredictionListResponse,
    summary="Run the swarm-prediction engine across the watchlist universe",
)
async def list_predictions(
    limit: int = Query(25, ge=1, le=100),
    refresh: bool = Query(False, description="Bypass the cache and regenerate"),
) -> PredictionListResponse:
    if refresh:
        invalidate_prediction_cache()
    results = predict_universe(limit=limit)
    age = prediction_cache_age_seconds()
    is_stale = age is not None and age > _STALE_AFTER.total_seconds()
    now = datetime.utcnow()
    logger.info("mirofish_predictions_built", count=len(results))
    return PredictionListResponse(
        total=len(results),
        bullish_count=sum(1 for p in results if p.direction == SwarmDirection.BULLISH),
        bearish_count=sum(1 for p in results if p.direction == SwarmDirection.BEARISH),
        neutral_count=sum(1 for p in results if p.direction == SwarmDirection.NEUTRAL),
        results=results,
        generated_at=now,
        data_timestamp=now,
        source=_prediction_source(),
        is_stale=is_stale,
    )


@router.get(
    "/{symbol}",
    response_model=SwarmPrediction,
    summary="Run the swarm-prediction engine for a single symbol",
)
async def get_prediction(
    symbol: str, refresh: bool = Query(False)
) -> SwarmPrediction:
    if refresh:
        invalidate_prediction_cache()
    prediction = predict_symbol(symbol)
    logger.info(
        "mirofish_prediction_completed",
        symbol=symbol,
        direction=prediction.direction.value,
        conviction=prediction.conviction,
    )
    return prediction
