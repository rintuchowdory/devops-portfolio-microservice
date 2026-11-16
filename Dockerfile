# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── Dependencies (cached layer) ───────────────────────────────────────────────
FROM base AS deps
COPY requirements.txt ./
RUN pip install -r requirements.txt

# ── Test stage: `docker build --target test .` runs pytest inside the image ───
FROM deps AS test
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY app ./app
COPY tests ./tests
COPY pyproject.toml ./
RUN PYTHONPATH=. pytest -q

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM deps AS prod
COPY app ./app

# Run unprivileged: a compromised process should not own the app directory
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen(f\"http://127.0.0.1:{os.getenv('PORT','8000')}/health\", timeout=2)"

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
