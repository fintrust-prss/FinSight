"""
SQLAlchemy 2.0 Async Session Factory.

Usage (in FastAPI routes):
    async with async_session_factory() as session:
        repo = MSMERepository(session)
        msme = await repo.get_by_id("msme_sakhi_001")

The session is created fresh per request via the `get_db` dependency injected
by `app/api/deps.py` (Phase 5). Direct use of `async_session_factory` here
is for services and background workers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Declarative Base — shared by all ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base class for all ORM models."""


# ---------------------------------------------------------------------------
# Async Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",  # SQL logging in dev only
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # Detect stale connections before use
    pool_recycle=1800,    # Recycle connections every 30 min
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Attributes stay accessible after commit
    autoflush=True,
    autocommit=False,
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides a DB session.

    Rolls back on exception; commits on clean exit.
    Suitable for background workers and scripts.
    FastAPI routes should use the ``Depends(get_db_dep)`` dependency from deps.py.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
