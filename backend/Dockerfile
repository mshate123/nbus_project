# Multi-stage backend Dockerfile.
# Targets:
#   app  — production server (uvicorn)
#   test — pytest runner with coverage

FROM python:3.12-slim AS base

WORKDIR /app

# Make top-level backend modules (models, engine, api) importable in every target.
ENV PYTHONPATH=/app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install all Python dependencies (app + test)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[test]"

# Copy source
COPY . .

# Make code importable as both top-level (`import seed`) and qualified
# (`from backend import seed`) so tests/factories can use either style.
RUN ln -s /app /app/backend

# ── App target ───────────────────────────────────────────────────────────────
FROM base AS app

EXPOSE 8000

# Run migrations then start production server
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2"]

# ── Test target ──────────────────────────────────────────────────────────────
FROM base AS test

# Run full test suite with coverage
CMD ["sh", "-c", "alembic upgrade head && pytest --cov=engine --cov-report=term-missing --cov-fail-under=20 -v"]
