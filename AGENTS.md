# ChartAnalytics — Agent Notes

Repository for the AI Trading Assistant / Chart Analytics app (FastAPI backend + Next.js frontend).

## Git push credentials

A GitHub Personal Access Token (classic, `repo` scope) is saved locally for committing
and pushing from this environment:

- **Location:** `backend/.env` → `GITHUB_TOKEN=ghp_...`
- **Status:** `backend/.env` is gitignored (confirmed via `git check-ignore backend/.env`),
  so the token is NOT tracked and will not be committed. Do not remove it from `.gitignore`.
- **Repository:** `ngowda759/ChartAnalytics` (remote `origin`).

### How an agent should push to git

The `GITHUB_TOKEN` env var is usually empty-scoped in this environment and cannot push
directly. To push, read the token from `backend/.env` and set the remote URL with it:

```bash
TOKEN=$(grep '^GITHUB_TOKEN=' backend/.env | cut -d= -f2)
git remote set-url origin "https://${TOKEN}@github.com/ngowda759/ChartAnalytics.git"
git push -u origin <branch>
# Always clean the token out of the remote URL afterwards:
git remote set-url origin https://github.com/ngowda759/ChartAnalytics.git
```

If a PR is needed, create it via the GitHub REST API with the same token (POST to
`/repos/ngowda759/ChartAnalytics/pulls`).

### Security

- Never paste the token into tracked files, commits, PR descriptions, or chat logs.
- The token has full `repo` scope — treat it as a secret. If it was shared in chat,
  consider it exposed and rotate it at https://github.com/settings/tokens when work is done.
- Do not commit `backend/.env`. Before pushing, verify with `git status` that it does not appear.

## Current branch

- `feature/chartink-nse-screener-dashboard` → open PR #17 targeting `main`.
  Adds the Chartink-style screener dashboard backed by live NSE data (nsetools).

## Build / test commands

Backend (run from `backend/`):

```bash
pip install -r requirements.txt
flake8 app --count --show-source --statistics   # CI lint step
pytest --cov=app                                 # CI test step
python -m uvicorn app.main:app --port 8000       # run locally
```

Frontend (run from `frontend/`):

```bash
npm install
npm run lint
npm run type-check   # tsc --noEmit
npm run build
npm test             # jest (next/jest); __tests__/*.test.tsx
```

## Conventions

- Frontend tests use `next/jest` (`jest.config.js`) with jsdom. The `@/*` path
  alias is mapped via `moduleNameMapper`. Test files live in
  `frontend/__tests__/*.test.tsx`; shared render helpers in
  `frontend/__tests__/helpers/` are excluded from the test runner. `tsconfig.json`
  excludes `__tests__`/`jest.*` so the production `tsc`/build type-check is not
  polluted by `@types/jest` globals (jest uses babel, no type-check at runtime).
- Dashboard tiles use the unified tile-state contract `useTileQuery`
  (`frontend/lib/useTileQuery.ts`) over React Query: `{data, loading, error,
  updatedAt, source, stale, refetch}`. Every rewritten tile renders Loading →
  Success(real data) → Cached(stale indicator) → Fallback(labelled) → Error(retry).
  Never fabricate metrics: if the backend does not provide a value, show "N/A".
- API base URL is centralized in `frontend/lib/api.ts::getApiBaseUrl()`
  (env `NEXT_PUBLIC_API_URL`, else relative `/api/v1`, else localhost for SSR).
  Never hardcode `localhost:8000` in components or construct `/api/options/...`
  double-prefixed paths — `fetchApi` already prepends `/api/v1`.

- Python: PEP 8 enforced via `flake8 app` in CI. Keep blank lines to PEP 8 (2 between
  top-level defs, 1 inside, no trailing blank line at EOF).
- Git commits: prefix with type (`feat:`, `fix:`, `chore:`). Add
  `Co-authored-by: openhands <openhands@all-hands.dev>` to commit messages.

## Scan dashboard (NSE) notes

- The scan dashboard page (`frontend/app/(dashboard)/scan-dashboard/page.tsx`)
  calls `GET /api/v1/scanner/nse-dashboard`, backed by
  `app/services/nse_service.py::build_nse_dashboard()`.
- `nsetools` is declared in `backend/requirements.txt` but is NOT preinstalled in
  this environment — run `pip install -r requirements.txt` before any live NSE
  call, or `_get_nse()` returns `None` and every `get_*` yields `[]`.
- Every widget in `build_nse_dashboard()` must fall back to synthetic rows when
  the live NSE source returns nothing (market closed / NSE blocks the request /
  nsetools missing) so the dashboard is never empty. Fallback rows are tagged
  `extra.source = "synthetic_fallback"` so the UI can distinguish them from live.
- Tests live in `backend/tests/services/test_nse_service.py`; monkeypatch the
  `get_*` getters to `[]` to simulate NSE being down.

## Decision Signals / Strategy Templates (ported from daily_stock_analysis)

A YAML-driven strategy-template engine + Decision Signals feature, adapted
from the `daily_stock_analysis` fork (MIT). Self-contained — no AI/DB deps.

- Strategy YAMLs: `backend/app/data/strategy_templates/*.yaml` (one per
  strategy: ma_golden_cross, volume_breakout, bull_trend, rsi_oversold_reversal,
  bollinger_squeeze_breakout, supertrend_flip). Add a new YAML to ship a new
  strategy; no code changes needed.
- Engine: `app/services/strategy_templates.py` loads YAMLs and evaluates each
  strategy's weighted `rules` against the screener_engine's synthetic OHLC +
  the existing `app.services.indicators` functions, producing a 0-100 score,
  a buy/hold/avoid action, and entry/stop/target levels. Rule kinds are
  registered in `_RULE_EVALUATORS`.
- Signals: `app/services/decision_signals.py` wraps evals into
  `DecisionSignal` objects (action, score, confidence, entry/stop/target,
  risk:reward, horizon, status lifecycle) — never empty (synthetic fallback).
- API: `app/api/decision_signals.py` mounted at `/api/v1/decision-signals`
  (`GET /strategies`, `GET /signals?action=&strategy=&min_score=&limit=`,
  `GET /signals/{id}`). Registered in `app/main.py`.
- Schemas: `app/schemas/decision_signals.py`.
- Tests: `backend/tests/services/test_strategy_templates.py` and
  `test_decision_signals.py`.
- Frontend: `frontend/app/(dashboard)/decision-signals/page.tsx` +
  `decisionSignalsApi` in `frontend/lib/api.ts` + sidebar nav entry.
- Dep: `pyyaml>=6.0.1` added to `backend/requirements.txt`.

## Agent Analysis (TradingAgents-style pipeline)

A deterministic, offline port of the TradingAgents framework (Apache-2.0,
github.com/TauricResearch/TradingAgents) — the multi-agent graph:
analysts → bull/bear investment debate → Research Manager → Trader →
aggressive/conservative/neutral risk debate → Portfolio Manager.

- No LLM/DB deps: every agent is a deterministic function of the
  screener-engine synthetic OHLC + `app.services.indicators`, so the
  pipeline always returns a complete result and is CI-testable. An LLM
  can be wired in later behind a key; the deterministic path stays the
  default + fallback.
- Schemas: `app/schemas/agent_analysis.py` — `PortfolioRating` (5-tier
  Buy/Overweight/Hold/Underweight/Sell), `TraderAction` (3-tier
  Buy/Hold/Sell), `AnalystReport`, `DebateResult`, `ResearchPlan`,
  `TraderProposal`, `PortfolioDecision`, `AgentAnalysisResult`.
- Service package: `app/services/trading_agents/`
  (`rating.py`, `analysts.py`, `debate.py`, `pipeline.py`).
- API: `app/api/agent_analysis.py` mounted at
  `/api/v1/agent-analysis` (`GET /?limit=`, `GET /{symbol}`). Registered
  in `app/main.py`.
- Tests: `backend/tests/services/test_agent_analysis.py`.
- Frontend: `frontend/app/(dashboard)/agent-analysis/page.tsx` (summary
  cards + watchlist table + detail modal showing every pipeline stage) +
  `agentAnalysisApi` in `frontend/lib/api.ts` + sidebar nav entry.

## MiroFish swarm predictions

A deterministic, offline port of the MiroFish swarm-intelligence prediction
engine (AGPL-3.0, github.com/666ghj/MiroFish). The same conceptual pipeline
as the original — seed extraction → swarm generation (persona agents) →
simulation rounds (social influence / herding) → consensus aggregation →
prediction report — with no LLM/DB/graph dependencies, so predictions are
always complete, deterministic (seeded per symbol + hour), and CI-testable.

- Engine: `app/services/mirofish/engine.py` — `extract_seed()` normalizes
  OHLCV + indicators into a SeedSnapshot (trend/momentum/volume_flow/
  price_position/drift in [-1,1] + ATR volatility); `build_swarm()` creates
  24 agents across 6 persona archetypes (momentum, trend, mean-reversion,
  value, breakout, contrarian); `simulate()` runs 4 opinion-dynamics rounds;
  aggregation maps consensus → direction/conviction/predicted % change/
  target price band. NaN/missing closes are dropped; <30 valid candles →
  truthful `unavailable` prediction.
- Schemas: `app/schemas/predictions.py` — `SwarmPrediction`,
  `SwarmPredictionSummary` (compact embed), `SwarmRoundSnapshot`,
  `PredictionListResponse`.
- API: `app/api/predictions.py` mounted at `/api/v1/predictions`
  (`GET /?limit=&refresh=`, `GET /{symbol}`). Registered in `app/main.py`.
- Cache: per-symbol TTLCache (30 min), reset by the conftest autouse fixture
  via `mirofish.invalidate_prediction_cache()`.
- Integrations (every surface carries a prediction):
  - Decision signals: `DecisionSignal.prediction` (summary) attached in
    `decision_signals._eval_to_signal()`.
  - Agent analysis: `AgentAnalysisResult.prediction` attached in
    `trading_agents/pipeline.py` (also on the unavailable result).
  - Scanners: `ScanResult.prediction` attached in
    `scanner_engine.scan_market()`.
  - Screener widgets: `screener_engine._to_row()` merges
    `extra.prediction_direction / predicted_change_pct /
    prediction_conviction / prediction_target` into every row; screener
    widget columns include them.
  - Scan dashboard: `nse_service._swarm_forecast_rows()` adds the
    `mirofish-swarm-forecast` widget (9 widgets total). NOTE: widget
    status/source vocab now includes `mock` (test
    `test_widget_status_source_fields_present` + frontend badge map updated).
- Frontend: `frontend/app/(dashboard)/predictions/page.tsx` (cards + detail
  modal with per-round swarm bars) + `predictionsApi` in `lib/api.ts` +
  sidebar entry (Fish icon). `screener-widget.tsx` renders string extras
  (`STRING_EXTRA_FIELDS`) — `extra.prediction_direction` is a string column.
  Decision-signal cards and the agent-analysis table/modal show the swarm
  badge.
- Tests: `backend/tests/services/test_mirofish.py` (engine determinism,
  API, NaN regression, all integration surfaces).

## Live market-data provider (yfinance default)

The app MUST use a real market-data provider in production; the Mock
provider is development-only and never silently activated (Phase 5/22).

- **Provider matrix:** `app/services/market_data.py` — sources:
  `SOURCE_YFINANCE` (default, credential-free, working in this env),
  `SOURCE_ANGEL_ONE`, `SOURCE_KITE`, `SOURCE_NSE`, `SOURCE_MOCK`,
  `SOURCE_UNAVAILABLE`.
- **Selection:** `settings.MARKET_DATA_PROVIDER` (`auto` default →
  broker if configured, else `yfinance`; `mock` only when explicit or
  `ALLOW_MOCK_IN_PRODUCTION=true`). `get_market_data_provider()`
  resolves the active source; `get_market_service()` uses it with NO
  silent mock fallback.
- **Unified resolver:** `candles_for(symbol) -> Tuple[List[Candle], str]`
  in `app/services/market_data.py` returns OHLCV + source string. All
  scanners/signals/agent-analysis consume this — they never know whether
  the source is NSE/Angel/Kite/Yahoo/Mock (Phase 6 architecture:
  Provider → Adapter → Normalized MarketData → Scanner Engine).
- **Startup log:** `app/main.py` prints
  `"MARKET DATA PROVIDER = <NAME>"` so the active provider is visible.
- **Diagnostic endpoints:** `GET /api/v1/system/data-provider`
  (`app/api/system.py`) and `GET /api/v1/market/status`
  (`app/api/market.py`) return provider/configured/connected/quote/
  historical_ohlcv/options/last_success. NEVER return secrets.
- **Frontend badge:** `components/dashboard/MarketStatusBadge.tsx`
  polls `/market/status` and shows ● LIVE/CACHED/UNAVAILABLE/MOCK with
  provider + last-updated IST. Wired into the dashboard header.
- **Source propagation:** every scan result, decision signal, and
  agent-analysis result carries `source` (provider name) + `status`
  (`live`/`cached`/`unavailable`/`mock`). Tests assert `source == "mock"`
  under the conftest autouse mock-mode fixture.
- **OI buildup:** truthfully `unavailable` when no real option feed is
  configured — NO synthetic OI deltas (Phase 12).
- **Bounded concurrency:** `fetch_universe_candles()` in
  `market_data.py` respects `settings.SCANNER_CONCURRENCY` (default 5)
  so the scanner universe fetch does not overwhelm the provider.
- **Live verified (this env):** startup `YFINANCE`; `/market/status`
  provider=yfinance connected=true; `/system/data-provider`
  quote=true historical_ohlcv=true; scanner results source="yfinance"
  status="live" with real prices; decision signals real entries;
  agent analysis source="yfinance"; indices NIFTY 50=24208.15.
  Options chain returns 503 (truthful unavailable — no broker).
