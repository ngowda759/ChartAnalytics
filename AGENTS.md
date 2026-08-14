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
```

## Conventions

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
