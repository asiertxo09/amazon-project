# syntax=docker/dockerfile:1.9
# Multi-stage, uv-based, non-root backend image (Plan_v2 P1-A4).
# Build context is the repo ROOT (pyproject.toml + uv.lock live there):
#   docker build -f backend/Dockerfile -t opportunity-copilot-backend .

# ── Builder: resolve the locked environment into /app/.venv ──────────────────
FROM python:3.12-slim-bookworm AS builder

# Pinned uv, copied from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:0.11.27 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy just the dependency manifests first so this layer caches on the lockfile
# (plain COPY keeps the image buildable with or without BuildKit/buildx).
COPY pyproject.toml uv.lock ./

# Install *only* runtime dependencies from the lockfile — no dev extras, no
# project.
RUN uv sync --frozen --no-dev --no-install-project

# ── Runtime: slim image, non-root, just the venv + app code ──────────────────
FROM python:3.12-slim-bookworm AS runtime

RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# The resolved virtualenv (absolute paths match because both stages use /app).
COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Application code (data CSVs included so the win model can self-train on first
# prediction if the joblib artifact isn't baked in).
COPY --chown=app:app backend ./backend

USER app
EXPOSE 8000

# Honor Render's $PORT when present; default to 8000 for local runs.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
