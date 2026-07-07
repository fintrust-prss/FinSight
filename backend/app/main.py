"""
MSME Financial Health Card — FastAPI Application Factory.

This module wires together all application components:
  - FastAPI app with lifespan (startup/shutdown hooks)
  - Structured JSON logging via structlog
  - CORS middleware (frontend ↔ backend)
  - Rate limiting via SlowAPI
  - Health check endpoint (/healthz)
  - API v1 router (routers added in Phase 5)

Design decisions:
  - create_app() is a factory function (not a module-level app) to support
    uvicorn --factory mode and to make testing easier (each test gets a fresh app).
  - No cloud SDK is imported here — all cloud access goes through adapters.
  - The app is intentionally thin: no business logic lives here.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.logging_config import configure_logging

logger = structlog.get_logger(__name__)


# ==============================================================
# Application Lifespan (startup / shutdown)
# ==============================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Async context manager for application lifespan events.

    Startup:
      - Configure structured logging
      - Log configuration summary (no secrets)
      - (Phase 2) Initialize DB connection pool
      - (Phase 2) Initialize adapter factory

    Shutdown:
      - Gracefully close DB connection pool
      - Flush any async log buffers
    """
    settings = get_settings()
    configure_logging(log_level=settings.app_log_level)

    logger.info(
        "application_startup",
        app_name="msme-healthcard-backend",
        environment=settings.app_env,
        cloud_provider=settings.cloud_provider,
        api_version="v1",
    )

    # TODO (Phase 2): Initialize DB engine + connection pool
    # TODO (Phase 2): Initialize adapter factory from CLOUD_PROVIDER env var
    # TODO (Phase 2): Run Alembic migrations on startup (dev only)

    yield  # Application is running

    logger.info("application_shutdown", app_name="msme-healthcard-backend")
    # TODO (Phase 2): Close DB connection pool


# ==============================================================
# Rate Limiter
# ==============================================================

limiter = Limiter(key_func=get_remote_address)


# ==============================================================
# Application Factory
# ==============================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns a fully-wired FastAPI app ready to serve requests.
    This function is called by uvicorn via --factory mode.
    """
    settings = get_settings()

    app = FastAPI(
        title="MSME Financial Health Card API",
        description=(
            "Unified, explainable, multidimensional Financial Health Score for MSMEs. "
            "Powered by alternate data (GST, UPI, EPFO, DISCOM, digital footprint). "
            "Built for IDBI Hackathon — Stage 1: GCP | Stage 2: AWS-portable."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- Rate Limiting ----
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins_list,
        allow_origin_regex=r"https://.*\.run\.app|http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # ---- Request timing + correlation ID middleware ----
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next: object) -> Response:
        """Attach X-Process-Time and X-Request-ID headers to every response."""
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Bind request context to structlog for this request
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)  # type: ignore[operator]

        process_time = (time.perf_counter() - start_time) * 1000  # ms
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=round(process_time, 2),
        )

        structlog.contextvars.clear_contextvars()
        return response

    # ---- Health Check ----
    @app.get(
        "/healthz",
        tags=["Health"],
        summary="Liveness & readiness probe",
        response_description="Service health status",
    )
    @limiter.exempt
    async def health_check() -> JSONResponse:
        """
        Liveness and readiness endpoint.

        Returns 200 OK when the service is ready to accept traffic.
        Used by Cloud Run health probes and docker-compose healthcheck.
        """
        return JSONResponse(
            content={
                "data": {
                    "status": "ok",
                    "service": "msme-healthcard-backend",
                    "version": "1.0.0",
                    "environment": settings.app_env,
                },
                "meta": {"api_version": "v1"},
                "error": None,
            }
        )

    # ---- API v1 Routers (registered in Phase 5) ----
    from app.api.v1.router import router as api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    # ---- Global Exception Handler ----
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler — returns standard error envelope, never leaks stack traces."""
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            exc_msg=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "meta": {"api_version": "v1"},
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact support.",
                },
            },
        )

    return app
