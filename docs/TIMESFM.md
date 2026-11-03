# TimesFM 2.5 Forecasting

ChartAnalytics includes an optional TimesFM 2.5 forecasting endpoint. It is
separate from MiroFish: MiroFish remains the existing deterministic
multi-agent/signal pipeline, while TimesFM forecasts the future **daily close**
from historical daily closing prices.

## Architecture

```text
Frontend / API client
       |
GET /api/v1/timesfm/{symbol}
       |
FastAPI timesfm router
       |
Main API forecast orchestrator
  |-- unified market_data.get_real_candles(symbol, "1d", context)
  |-- validate real OHLCV; reject mock/unavailable data
  |-- authenticated request to isolated inference service
       |
Dedicated TimesFM inference service
  |-- lazy-load TimesFM 2.5 PyTorch checkpoint once per process
  |-- serialize inference to bound memory use
  |-- return median (P50), P10 and P90 per future step
       |
Main API in-process TTL cache
```

Only the close series is forecast. The API does not invent future open, high,
low or volume values. The P10/P90 values are model quantiles, not guaranteed
price bounds. This is a research/decision-support feature, not investment
advice.

## Deployment on the existing free Render service

The existing Render service remains the **main ChartAnalytics API** and stays
on its Free plan. Do not install PyTorch or TimesFM in that service: its
512 MB memory limit is insufficient for reliable model inference and adding
the model would risk the existing APIs.

The recommended no-additional-Render-cost inference target is a **private
Hugging Face ZeroGPU Gradio Space**:

- ZeroGPU provides dynamically allocated GPU inference without a dedicated
  always-on model server.
- Eligible free personal accounts can host up to two ZeroGPU Spaces.
- Free accounts currently receive 5 minutes of GPU execution quota per day;
  authenticated calls consume the token owner's quota.
- Spaces can sleep or queue when GPU capacity is busy. It is suitable for
  personal/on-demand use, not a guaranteed production SLA.
- A private Space protects the inference API. The backend uses a Hugging Face
  read token; keep it only in Render environment variables.

Space source is in `backend/timesfm_zerogpu/`. Create a private Gradio Space,
select ZeroGPU hardware, and publish the contents of that directory to its
root. The Space uses the Apache-2.0 TimesFM 2.5 200M checkpoint.

Configure the existing Render backend:

```dotenv
TIMESFM_ENABLED=true
TIMESFM_SERVICE_PROTOCOL=gradio
TIMESFM_SERVICE_URL=https://<your-space-subdomain>.hf.space
TIMESFM_SERVICE_TOKEN=<hugging-face-read-token>
TIMESFM_MODEL_ID=google/timesfm-2.5-200m-pytorch
TIMESFM_CACHE_TTL_SECONDS=900
```

Do not put the Hugging Face token in Vercel or browser code. The Render backend
sends only validated daily closing prices to the private Space. The Space does
not access ChartAnalytics databases or market-data providers.

The original isolated FastAPI inference service remains available for a
separately provisioned environment using
`TIMESFM_SERVICE_PROTOCOL=fastapi`, but it is not required for the free
ZeroGPU deployment.

Keep `TIMESFM_ENABLED=false` and
`NEXT_PUBLIC_TIMESFM_ENABLED` unset until the Space has been deployed and a
real forecast has passed the smoke test. If ZeroGPU quota is exhausted, the
Space is sleeping, or the GPU queue is unavailable, TimesFM returns a
controlled unavailable response. Existing MiroFish, market-data, screener and
chart functionality remains independent.

## API

```http
GET /api/v1/timesfm/{symbol}?horizon=10&context=512
```

- `symbol`: market symbol supported by the configured market-data provider.
- `horizon`: future daily steps, 1–30 (default 10).
- `context`: trailing daily observations, 60–1024 (default 512).
- `refresh=true`: bypass the in-process forecast cache.

Response fields include `last_observation`, `historical_points`, and
`forecast[]` with `timestamp`, `median`, `lower` (P10), and `upper`
(P90). The forecast timestamps skip weekends but do not include an exchange
holiday calendar; they are weekday estimates, not guaranteed trading dates.

The endpoint returns HTTP 503 when disabled, when TimesFM is not installed,
when model loading/inference fails, or when real historical candles are
unavailable. It returns HTTP 422 for invalid parameters.

## Model and licensing

This integration explicitly uses the TimesFM 2.5 200M PyTorch checkpoint
(`google/timesfm-2.5-200m-pytorch`). TimesFM source and 2.5 model weights are
published under Apache-2.0 according to the upstream project. Do not silently
replace this checkpoint with TimesFM 3.0: upstream currently documents a
separate non-commercial license for 3.0 weights. Review upstream terms before
changing the checkpoint or redistributing model assets.

Upstream references:
- https://github.com/google-research/timesfm
- https://huggingface.co/google/timesfm-2.5-200m-pytorch
- https://pypi.org/project/timesfm/

## Operational notes

- The model is loaded lazily, once per Python process, on the first forecast.
- Forecast results are cached in process (default 15 minutes); each worker has
  its own cache and model instance.
- The model is run in FastAPI's thread pool so inference does not block the
  event loop.
- Forecasts are based on daily close only; intraday forecasting is not enabled.
- Validate forecasts against walk-forward backtests and paper trading before
  using them in any trading workflow.
