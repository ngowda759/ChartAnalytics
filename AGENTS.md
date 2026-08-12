# ChartAnalytics — Agent Notes

Repository for the AI Trading Assistant / Chart Analytics app (FastAPI backend + Next.js frontend).

## Git push credentials

A GitHub Personal Access Token (classic, `repo` scope) is saved locally for committing
and pushing from this environment:

- **Location:** `backend/.env` → `GITHUB_TOKEN=ghp_...`
- **Status:** `backend/.env` is gitignored (confirmed via `git check-ignore backend/.env`),
  so the token is NOT tracked and will not be committed. Do not remove it from `.gitignore`.
- **Repository:** `ngowda759/ChartAnalytics` (remote `origin`).
- **Documented:** `backend/.env.example` has a clearly documented `GITHUB_TOKEN` section
  (placeholder only — no real value) describing where the real token goes and the agent
  push flow. Check there first if you need to find the token.

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

- `fix/scan-dashboard-nse-data` → open PR #20 targeting `main`.
  Fixes the scan dashboard failing to load (frontend→backend proxy gap in
  next.config.mjs) and switches the dashboard's market indices to live NSE
  data (nsetools) with a graceful mock fallback.

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
