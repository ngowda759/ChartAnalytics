---
title: ChartAnalytics TimesFM 2.5
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.49.1
python_version: 3.12
suggested_hardware: zero-a10g
app_file: app.py
---

# ChartAnalytics TimesFM 2.5 inference

Private Gradio API for the ChartAnalytics application. Uses the Apache-2.0
Google TimesFM 2.5 200M checkpoint.

## Deployment

Create a **private Gradio Space** and select **ZeroGPU** hardware. Free personal
accounts in good standing may host up to two ZeroGPU Spaces; eligibility
requires a verified email and an account older than 30 days.

The repository includes a manual GitHub Actions deployment workflow:
`.github/workflows/deploy-timesfm-zerogpu.yml`. Add these repository settings:

- Actions secret `HF_TOKEN`: a Hugging Face write token for the Space.
- Actions variable `HF_SPACE_REPO_ID`: the Space repository ID
  (`owner/space-name`).

Then run **Actions → Deploy TimesFM ZeroGPU Space → Run workflow**. It uploads
only this directory to the Space root. No paid Render service or paid Hugging
Face hardware is required.

The Space should remain private. Do not publish this inference endpoint
publicly: the ChartAnalytics backend sends a Hugging Face read token when
calling its API.

## ChartAnalytics backend configuration

Set these environment variables on the existing Render backend:

```dotenv
TIMESFM_ENABLED=true
TIMESFM_SERVICE_PROTOCOL=gradio
TIMESFM_SERVICE_URL=https://<your-space-subdomain>.hf.space
TIMESFM_SERVICE_TOKEN=<hugging-face-read-token>
TIMESFM_MODEL_ID=google/timesfm-2.5-200m-pytorch
TIMESFM_CACHE_TTL_SECONDS=900
```

The Hugging Face token is stored only in Render's environment settings. Never
commit it to GitHub or expose it in the frontend.

## Limits and operational behaviour

- ZeroGPU free accounts currently receive 5 minutes of GPU time per day.
- Authenticated API calls consume the token owner's ZeroGPU quota.
- GPU availability is shared and queue delays can occur.
- Free Spaces may sleep after inactivity; the first call can take longer.
- Forecast requests are serialized to avoid concurrent model execution.
- If the quota is exhausted or the Space is unavailable, ChartAnalytics
  returns a controlled unavailable response; existing market-data,
  MiroFish, screener and chart features continue to work.
