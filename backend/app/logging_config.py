"""
Structured logging configuration using structlog.

Emits JSON logs in production (parseable by Cloud Logging / CloudWatch)
and pretty-printed colored logs in development.

Usage:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("event_name", key="value", another_key=42)
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for the application.

    In development (non-JSON): colorized, human-readable output.
    In production: JSON output compatible with Cloud Logging.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    # Standard library logging configuration
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_int,
    )

    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Formatter: JSON in production, colored console in dev
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()
        if _is_development()
        else structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level_int)

    # Silence noisy third-party loggers
    for noisy_logger in ["uvicorn.access", "sqlalchemy.engine"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _is_development() -> bool:
    """Check if running in development mode (affects log format)."""
    import os
    return os.getenv("APP_ENV", "development").lower() in ("development", "testing")
