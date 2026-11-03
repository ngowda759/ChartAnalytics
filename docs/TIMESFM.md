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

## Installation and configuration

The core backend does not install PyTorch or TimesFM. This keeps normal API
startup lightweight and avoids breaking deployments that do not use the model.

The inference runtime is intentionally isolated from the main backend. Its
dependencies are in `backend/timesfm_service/requirements.txt`; the main
backend does not install PyTorch or TimesFM.

The repository includes an optional paid Render blueprint at
`render.timesfm.yaml`. It is deliberately separate from the existing
`render.yaml`, so syncing the current free API blueprint cannot create a paid
service unexpectedly. The optional blueprint creates a dedicated 1 CPU / 2 GB
RAM service with a 2 GB persistent Hugging Face cache disk.

Configure the dedicated service with:
```dotenv
TIMESFM_MODEL_ID=google/timesfm-2.5-200m-pytorch
TIMESFM_SERVICE_TOKEN=<a long random secret>
HF_HOME=/var/cache/huggingface
```

Configure the existing ChartAnalytics backend with:
```dotenv
TIMESFM_ENABLED=true
TIMESFM_SERVICE_URL=https://<dedicated-service-host>
TIMESFM_SERVICE_TOKEN=<the same secret>
TIMESFM_MODEL_ID=google/timesfm-2.5-200m-pytorch
TIMESFM_CACHE_TTL_SECONDS=900
```

The main backend sends only validated daily close values to the inference
service over an authenticated HTTPS request. The model service does not access
the app database or market-data providers. Inference is serialized to avoid
concurrent requests multiplying memory use.

The model checkpoint is downloaded from Hugging Face on first forecast and
cached on the dedicated service's persistent disk. Keep outbound Hugging Face
access enabled. The first model load can be slow. Keep
`TIMESFM_ENABLED=false` until the service is provisioned, its health check
passes, and a real forecast has been verified. The rest of the application
continues to work without TimesFM.

### Current Render deployment constraint

The repository's current `render.yaml` declares the main backend as a Render
Free web service with 512 MB RAM. TimesFM 2.5's upstream system-requirements
guide estimates roughly 1.5 GB RAM for a small CPU inference workload; the
checkpoint is approximately 925 MB. The free service also has an ephemeral
filesystem and can spin down when idle. Therefore the model must **not** be
installed or enabled inside the existing API service.

The isolated blueprint uses Render's 1 CPU / 2 GB RAM Standard service as a
minimum starting point. Actual latency and memory must be measured before
production traffic is enabled. The persistent cache disk avoids downloading
the model weights on every restart. Do not upgrade compute or incur recurring
costs without explicit owner approval.

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
