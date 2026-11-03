"""TimesFM 2.5 forecasting endpoints."""
from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.timesfm_forecast import TimesFMUnavailable, forecast_symbol

router = APIRouter()


@router.get("/{symbol}", summary="Forecast daily closing prices with TimesFM 2.5")
async def get_timesfm_forecast(
    symbol: str,
    horizon: int = Query(10, ge=1, le=30, description="Future daily steps"),
    context: int = Query(512, ge=60, le=1024, description="Historical daily observations"),
    refresh: bool = Query(False, description="Bypass the forecast cache"),
):
    """Return median, P10 and P90 daily-close forecasts.

    Requires TIMESFM_ENABLED=true and the optional TimesFM model dependencies.
    """
    if not settings.TIMESFM_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="TimesFM forecasting is disabled. Set TIMESFM_ENABLED=true to enable it.",
        )
    try:
        return await run_in_threadpool(
            forecast_symbol, symbol, horizon, context, refresh
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TimesFMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
