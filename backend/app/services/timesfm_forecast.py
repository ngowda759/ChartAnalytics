"""TimesFM forecast orchestration in the main ChartAnalytics API.

Market data remains sourced by the existing unified resolver. Inference is
forwarded to a separately provisioned TimesFM service so model memory cannot
impact the main API process.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import httpx
import numpy as np
import structlog

from app.core.config import settings
from app.services import market_data

logger = structlog.get_logger()
_CACHE: dict[tuple[str, int, int], tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()


class TimesFMUnavailable(RuntimeError):
    """Raised when the isolated TimesFM inference service cannot serve a forecast."""


def _next_weekday(last_date: datetime, offset: int) -> datetime:
    """Advance by weekdays; the exchange holiday calendar is not applied."""
    current = last_date
    remaining = offset
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _build_forecast_payload(
    symbol: str,
    candles: list,
    source: str,
    horizon: int,
    forecast_points: list[dict],
) -> dict:
    last_date = candles[-1].date
    forecasts = []
    for index, point in enumerate(forecast_points[:horizon]):
        forecasts.append({
            "step": index + 1,
            "timestamp": _next_weekday(last_date, index + 1).isoformat(),
            "median": round(float(point["median"]), 4),
            "lower": round(float(point["lower"]), 4),
            "upper": round(float(point["upper"]), 4),
        })
    if len(forecasts) != horizon:
        raise TimesFMUnavailable("Inference service returned an incomplete forecast.")
    return {
        "symbol": symbol.upper(),
        "model": "TimesFM 2.5 200M",
        "model_id": settings.TIMESFM_MODEL_ID,
        "interval": "1d",
        "target": "close",
        "source": source,
        "generated_at": datetime.utcnow().isoformat(),
        "last_observation": {
            "timestamp": last_date.isoformat(),
            "close": round(float(candles[-1].close), 4),
        },
        "historical_points": len(candles),
        "horizon": horizon,
        "quantiles": ["p10", "p50", "p90"],
        "forecast": forecasts,
        "disclaimer": (
            "Model output is an experimental statistical forecast, not a price "
            "target or investment recommendation. Weekday dates do not account "
            "for NSE/BSE exchange holidays."
        ),
    }


def forecast_symbol(
    symbol: str,
    horizon: int = 10,
    context: int = 512,
    refresh: bool = False,
) -> dict:
    """Fetch real daily candles and call the isolated TimesFM inference service."""
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    if not 1 <= horizon <= 30:
        raise ValueError("horizon must be between 1 and 30")
    if not 60 <= context <= 1024:
        raise ValueError("context must be between 60 and 1024")

    service_url = (settings.TIMESFM_SERVICE_URL or "").rstrip("/")
    service_token = settings.TIMESFM_SERVICE_TOKEN or ""
    if not service_url or not service_token:
        raise TimesFMUnavailable(
            "The dedicated TimesFM inference service is not configured."
        )

    cache_key = (normalized, horizon, context)
    ttl = max(0, int(settings.TIMESFM_CACHE_TTL_SECONDS))
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if not refresh and cached and time.time() - cached[0] < ttl:
            return cached[1]

    candles, source = market_data.get_real_candles(
        normalized, interval="1d", limit=context
    )
    if not candles or source in (
        market_data.SOURCE_UNAVAILABLE,
        market_data.SOURCE_MOCK,
    ):
        raise TimesFMUnavailable("Real daily OHLCV data is unavailable for this symbol.")

    valid_candles = [
        candle for candle in candles
        if candle.close is not None and np.isfinite(candle.close)
    ]
    closes = np.asarray([c.close for c in valid_candles], dtype=np.float32)
    if closes.size < 60:
        raise TimesFMUnavailable("At least 60 valid daily closing prices are required.")

    try:
        response = httpx.post(
            f"{service_url}/forecast",
            headers={"Authorization": f"Bearer {service_token}"},
            json={
                "symbol": normalized,
                "closes": closes[-context:].tolist(),
                "horizon": horizon,
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        response.raise_for_status()
        body = response.json()
        if body.get("symbol") != normalized or body.get("model_id") != settings.TIMESFM_MODEL_ID:
            raise ValueError("Inference service returned unexpected model metadata.")
        payload = _build_forecast_payload(
            normalized, valid_candles, source, horizon, body.get("forecast", [])
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.exception("timesfm_remote_inference_failed", symbol=normalized)
        raise TimesFMUnavailable("The dedicated TimesFM inference service is unavailable.") from exc

    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.time(), payload)
    return payload


def clear_forecast_cache() -> None:
    """Clear the in-process forecast cache (primarily for tests)."""
    with _CACHE_LOCK:
        _CACHE.clear()
