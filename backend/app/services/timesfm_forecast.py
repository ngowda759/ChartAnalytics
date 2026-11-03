"""Optional TimesFM 2.5 daily-close forecasting service.

The model is loaded lazily and only when TIMESFM_ENABLED=true. It consumes
real OHLCV from the unified market-data resolver; mock candles are rejected.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import structlog

from app.core.config import settings
from app.services import market_data

logger = structlog.get_logger()

_MODEL_ID = "google/timesfm-2.5-200m-pytorch"
_MODEL: Any = None
_MODEL_LOCK = threading.Lock()
_CACHE: dict[tuple[str, int, int], tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()


class TimesFMUnavailable(RuntimeError):
    """Raised when TimesFM cannot serve a forecast."""


def _load_model():
    """Load and compile the pinned TimesFM 2.5 checkpoint once per process."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        try:
            import timesfm
        except ImportError as exc:
            raise TimesFMUnavailable(
                "TimesFM is not installed. Install backend/timesfm-requirements.txt."
            ) from exc

        model_id = getattr(settings, "TIMESFM_MODEL_ID", _MODEL_ID) or _MODEL_ID
        try:
            model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(model_id)
            model.compile(
                timesfm.ForecastConfig(
                    max_context=1024,
                    max_horizon=30,
                    normalize_inputs=True,
                    per_core_batch_size=1,
                    use_continuous_quantile_head=True,
                    force_flip_invariance=True,
                    infer_is_positive=True,
                    fix_quantile_crossing=True,
                )
            )
        except Exception as exc:
            logger.exception("timesfm_model_load_failed", model_id=model_id)
            raise TimesFMUnavailable("TimesFM model could not be loaded.") from exc
        _MODEL = model
        logger.info("timesfm_model_loaded", model_id=model_id)
        return _MODEL


def _next_weekday(last_date: datetime, offset: int) -> datetime:
    """Advance by trading weekdays (weekends skipped; exchange holidays unknown)."""
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
    point: np.ndarray,
    quantiles: np.ndarray,
) -> dict:
    """Convert TimesFM arrays into a stable API payload."""
    last_date = candles[-1].date
    forecasts = []
    for index in range(horizon):
        median = float(point[index])
        lower = float(quantiles[index, 1])  # q10
        upper = float(quantiles[index, 9])  # q90
        forecasts.append({
            "step": index + 1,
            "timestamp": _next_weekday(last_date, index + 1).isoformat(),
            "median": round(median, 4),
            "lower": round(min(lower, upper), 4),
            "upper": round(max(lower, upper), 4),
        })
    return {
        "symbol": symbol.upper(),
        "model": "TimesFM 2.5 200M",
        "model_id": getattr(settings, "TIMESFM_MODEL_ID", _MODEL_ID) or _MODEL_ID,
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


def forecast_symbol(symbol: str, horizon: int = 10, context: int = 512, refresh: bool = False) -> dict:
    """Generate a daily closing-price forecast from real historical candles."""
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    if not 1 <= horizon <= 30:
        raise ValueError("horizon must be between 1 and 30")
    if not 60 <= context <= 1024:
        raise ValueError("context must be between 60 and 1024")

    cache_key = (normalized, horizon, context)
    ttl = max(0, int(getattr(settings, "TIMESFM_CACHE_TTL_SECONDS", 900)))
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if not refresh and cached and time.time() - cached[0] < ttl:
            return cached[1]

    candles, source = market_data.get_real_candles(normalized, interval="1d", limit=context)
    if not candles or source in (market_data.SOURCE_UNAVAILABLE, market_data.SOURCE_MOCK):
        raise TimesFMUnavailable("Real daily OHLCV data is unavailable for this symbol.")
    closes = np.asarray([c.close for c in candles if np.isfinite(c.close)], dtype=np.float32)
    if closes.size < 60:
        raise TimesFMUnavailable("At least 60 valid daily closing prices are required.")

    model = _load_model()
    try:
        point_forecast, quantile_forecast = model.forecast(
            horizon=horizon,
            inputs=[closes[-context:]],
        )
        point = np.asarray(point_forecast)[0]
        quantiles = np.asarray(quantile_forecast)[0]
        if point.shape[0] < horizon or quantiles.shape[0] < horizon or quantiles.shape[1] < 10:
            raise ValueError("Unexpected TimesFM forecast output shape.")
        payload = _build_forecast_payload(
            normalized, candles, source, horizon, point[:horizon], quantiles[:horizon]
        )
    except Exception as exc:
        logger.exception("timesfm_inference_failed", symbol=normalized)
        raise TimesFMUnavailable("TimesFM inference failed.") from exc

    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.time(), payload)
    return payload


def clear_forecast_cache() -> None:
    """Clear the in-process forecast cache (primarily for tests)."""
    with _CACHE_LOCK:
        _CACHE.clear()
