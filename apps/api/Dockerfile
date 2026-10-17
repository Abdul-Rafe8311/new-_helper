# syntax=docker/dockerfile:1
# NewsHelper API image (Render). Build context: apps/api.

ARG PYTHON_IMAGE=python:3.12-slim

# ---------- builder: resolve the locked runtime deps into /app/.venv ----------
FROM ${PYTHON_IMAGE} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# ---------- runtime: slim image, non-root, no build tools ----------
FROM ${PYTHON_IMAGE} AS runtime

ARG GIT_SHA=dev
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV=prod \
    GIT_SHA=${GIT_SHA} \
    PORT=8000

# WeasyPrint (PDF editions) needs Pango/HarfBuzz and a font at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/health\", timeout=3)"]

# Render injects PORT; shell form is needed to expand it, exec keeps uvicorn as PID 1.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips='*'"]
