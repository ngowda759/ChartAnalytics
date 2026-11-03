"""TimesFM 2.5 inference endpoint for Hugging Face ZeroGPU Spaces.

The Space is private. ChartAnalytics calls its Gradio API using a Hugging Face
read token stored only in the Render backend environment.
"""
from __future__ import annotations

import numpy as np
import spaces
import torch
import gradio as gr
import timesfm

MODEL_ID = "google/timesfm-2.5-200m-pytorch"

# ZeroGPU requires importing `spaces` before torch and placing the model on
# CUDA at module scope. The package emulates CUDA during startup and streams
# weights into the allocated GPU when the decorated endpoint is invoked.
torch.set_float32_matmul_precision("high")
MODEL = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
    MODEL_ID,
    torch_compile=False,
)
MODEL.compile(
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


@spaces.GPU(duration=60)
def forecast(symbol: str, closes: list[float], horizon: int) -> dict:
    """Return TimesFM median and 10th/90th percentile forecasts."""
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 40:
        raise gr.Error("A valid market symbol is required.")
    if not 1 <= int(horizon) <= 30:
        raise gr.Error("Horizon must be between 1 and 30.")
    values = np.asarray(closes, dtype=np.float32)
    if values.ndim != 1 or not 60 <= values.size <= 1024:
        raise gr.Error("Provide between 60 and 1024 daily closing prices.")
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise gr.Error("Closing prices must be finite positive numbers.")

    point, quantiles = MODEL.forecast(
        horizon=int(horizon),
        inputs=[values],
    )
    forecast_points = []
    for index in range(int(horizon)):
        lower = float(quantiles[0, index, 1])
        upper = float(quantiles[0, index, 9])
        forecast_points.append({
            "step": index + 1,
            "median": round(float(point[0, index]), 4),
            "lower": round(min(lower, upper), 4),
            "upper": round(max(lower, upper), 4),
        })
    return {
        "symbol": normalized,
        "model": "TimesFM 2.5 200M",
        "model_id": MODEL_ID,
        "forecast": forecast_points,
    }


with gr.Blocks(title="ChartAnalytics TimesFM 2.5") as demo:
    gr.Markdown(
        "# ChartAnalytics · TimesFM 2.5\n"
        "Private inference endpoint for daily closing-price forecasts."
    )
    gr.api(
        forecast,
        api_name="forecast",
        api_description="Forecast daily closes using Google TimesFM 2.5.",
    )

demo.queue(default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch()
