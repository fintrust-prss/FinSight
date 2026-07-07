# ==============================================================
# Backend Dockerfile — Multi-stage build
# Stage 1: base      — Python 3.11-slim base image
# Stage 2: builder   — Install dependencies
# Stage 3: development — Hot-reload dev server (mounted source)
# Stage 4: production  — Final minimal image (no dev deps)
# ==============================================================

# ---- Base ----
FROM python:3.11-slim AS base

# Security: run as non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# System deps required by psycopg2 / asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Builder: install dependencies ----
FROM base AS builder

COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# ---- Development: hot-reload via uvicorn ----
FROM builder AS development

# Dev deps already installed in builder
COPY . .

USER root

EXPOSE 8080

# Use --reload for hot-reload; source mounted via docker-compose volume
CMD ["uvicorn", "app.main:create_app", \
     "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--reload", \
     "--log-level", "info"]

# ---- Production: minimal image ----
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (no dev deps, no test files)
COPY app/ ./app/
COPY config/ ./config/

RUN chown -R appuser:appuser /app
USER root

EXPOSE 8080

# Production: multiple workers, no reload
CMD ["uvicorn", "app.main:create_app", \
     "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log"]
