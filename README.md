# Enterprise Opportunity Copilot

FastAPI analysis pipeline (extraction → gap/feasibility → deterministic pricing →
win-probability model → narrative agents → synthesis → pitch deck) with a React +
Vite frontend. See `VISION.md` for product direction and `Plan_v2.md` for the
delivery roadmap.

## Backend — local development (uv)

The backend uses [uv](https://docs.astral.sh/uv/) with a committed `uv.lock` for
reproducible environments. Everything is driven from the repo root.

```bash
# Install the pinned toolchain (runtime + dev extras)
uv sync --extra dev

# Run the API (loads secrets from .env; copy .env.example first)
uv run uvicorn backend.main:app --reload --env-file .env

# Quality gates (these are exactly what CI runs)
uv run ruff check backend           # lint
uv run ruff format --check backend  # format
uv run mypy backend                 # types (strict on schemas/, pricing.py, ml/)
uv run pytest --cov=backend         # tests + coverage
```

Optional local git hooks mirroring CI:

```bash
uv run pre-commit install
```

### Configuration

All environment-driven settings are declared in `backend/config.py` (`Settings`)
and documented in `.env.example`. Nothing reads `os.environ` directly. Config is
loaded from the process environment only — pass `--env-file .env` locally.

## Frontend — local development

```bash
cd frontend
npm ci
npm run dev        # dev server
npm run lint       # oxlint
npm run typecheck  # tsc -b (no emit)
npm run build      # production bundle
```

## Full stack via Docker

```bash
docker compose up --build
# backend  → http://localhost:8000  (health: /health)
# frontend → http://localhost:5173
# postgres → localhost:5432
```

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `master`:
lint → typecheck → test → build images. On push to `master` it triggers a Render
deploy via the `RENDER_DEPLOY_HOOK_URL` repo secret (`render.yaml` defines the
services). A red suite blocks the deploy.
