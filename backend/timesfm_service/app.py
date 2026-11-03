"""Optional isolated TimesFM 2.5 inference service.

This service accepts a validated daily-close series from the main ChartAnalytics
API. It does not fetch market data or access the application's database.
"""
from __future__ import annotations

import os
import secrets
import threading
from typing import Any

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

MODEL_ID = os.getenv("TIMESFM_MODEL_ID", "google/timesfm-2.5-200m-pytorch")
SERVICE_TOKEN = os.getenv("TIMESFM_SERVICE_TOKEN", "")
MODEL: Any = None
MODEL_LOCK = threading.Lock()
INFERENCE_LOCK = threading.Lock()

app = FastAPI(title="ChartAnalytics TimesFM Inference", version="1.0.0")


class ForecastRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    closes: list[float] = Field(min_length=60, max_length=1024)
    horizon: int = Field(default=10, ge=1, le=30)


def _authorize(authorization: str | None) -> None:
    if not SERVICE_TOKEN:
        raise HTTPException(status_code=503, detail="Inference service token is not configured.")
    expected = f"Bearer {SERVICE_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized inference request.")


def _load_model():
    global MODEL
    if MODEL is not None:
        return MODEL
    with MODEL_LOCK:
        if MODEL is not None:
            return MODEL
        try:
            import timesfm
            model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                MODEL_ID, torch_compile=False
            )
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
            raise HTTPException(
                status_code=503, detail="TimesFM model could not be loaded."
            ) from exc
        MODEL = model
        return MODEL


@app.get("/health")
def health():
    """Lightweight health check; deliberately does not load model weights."""
    return {
        "status": "ok",
        "model": "TimesFM 2.5 200M",
        "model_id": MODEL_ID,
        "model_loaded": MODEL is not None,
    }


@app.post("/forecast")
def forecast(
    request: ForecastRequest,
    authorization: str | None = Header(default=None),
):
    """Forecast daily closes and return P10/P50/P90 values."""
    _authorize(authorization)
    values = np.asarray(request.closes, dtype=np.float32)
    if not np.isfinite(values).all():
        raise HTTPException(status_code=422, detail="Closing prices must all be finite numbers.")
    if np.any(values <= 0):
        raise HTTPException(status_code=422, detail="Closing prices must be positive.")

    model = _load_model()
    try:
        # Keep inference serial on the small dedicated CPU worker. This avoids
        # concurrent requests multiplying activation memory.
        with INFERENCE_LOCK:
            point, quantiles = model.forecast(
                horizon=request.horizon,
                inputs=[values],
            )
        point = np.asarray(point)[0]
        quantiles = np.asarray(quantiles)[0]
        if (
            point.shape[0] < request.horizon
            or quantiles.shape[0] < request.horizon
            or quantiles.shape[1] < 10
        ):
            raise ValueError("Unexpected TimesFM forecast output shape.")
        forecast_points = []
        for index in range(request.horizon):
            lower = float(quantiles[index, 1])
            upper = float(quantiles[index, 9])
            forecast_points.append({
                "step": index + 1,
                "median": round(float(point[index]), 4),
                "lower": round(min(lower, upper), 4),
                "upper": round(max(lower, upper), 4),
            })
        return {
            "symbol": request.symbol.upper(),
            "model": "TimesFM 2.5 200M",
            "model_id": MODEL_ID,
            "forecast": forecast_points,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="TimesFM inference failed.") from exc
