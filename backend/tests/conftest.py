"""
Shared pytest fixtures for the MSME Health Card backend test suite.

Uses an in-memory SQLite database (via aiosqlite) so repository tests
run without a real Postgres instance. The engine is configured to mimic
Postgres semantics as closely as possible.

SQLite differences handled:
  - No JSONB → we use Text everywhere (already done in models.py)
  - No asyncpg → we use aiosqlite driver
  - No native UUID → stored as String(36) (already done in models.py)
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.db.models  # noqa: F401 — registers all ORM models on Base.metadata
from app.db.session import Base
from app.db.repositories.msme import MSMERepository
from app.db.repositories.health_score import HealthScoreRepository
from app.db.repositories.alternate_data import AlternateDataRepository


# ---------------------------------------------------------------------------
# Event loop — pytest-asyncio default scope
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for all tests."""
    return asyncio.DefaultEventLoopPolicy()


# ---------------------------------------------------------------------------
# In-memory SQLite engine (session-scoped: created once per test session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def engine():
    """
    Create a shared in-memory SQLite engine for the test session.

    All tables are created before tests run and dropped afterwards.
    Isolation between tests is achieved via per-test transactions (see `db_session`).
    """
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


# ---------------------------------------------------------------------------
# Per-test DB session (rolls back after each test → test isolation)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async session that is rolled back after each test.

    This ensures test isolation without needing to truncate tables.
    """
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Repository fixtures (convenience wrappers around db_session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def msme_repo(db_session: AsyncSession) -> MSMERepository:
    """Return an MSMERepository wired to the test session."""
    return MSMERepository(db_session)


@pytest_asyncio.fixture
async def alt_data_repo(db_session: AsyncSession) -> AlternateDataRepository:
    """Return an AlternateDataRepository wired to the test session."""
    return AlternateDataRepository(db_session)


@pytest_asyncio.fixture
async def score_repo(db_session: AsyncSession) -> HealthScoreRepository:
    """Return a HealthScoreRepository wired to the test session."""
    return HealthScoreRepository(db_session)


# ---------------------------------------------------------------------------
# Sample MSME seed data (matches synthetic generator persona A & B)
# ---------------------------------------------------------------------------

SAKHI_MSME_DATA = {
    "msme_id": "msme_sakhi_001",
    "legal_name": "Sakhi Mahila Papad Udyog",
    "udyam_number": "UDYAM-GJ-01-0012345",
    "sector": "manufacturing",
    "sub_sector": "food_manufacturing",
    "vintage_years": 12.0,
    "state": "Gujarat",
    "registration_type": "cooperative",
}

ANNA_MSME_DATA = {
    "msme_id": "msme_anna_002",
    "legal_name": "Annapurna Fresh Snacks Co.",
    "udyam_number": "UDYAM-UP-27-0067890",
    "sector": "manufacturing",
    "sub_sector": "food_manufacturing",
    "vintage_years": 2.5,
    "state": "Uttar Pradesh",
    "registration_type": "sole_proprietor",
}


@pytest_asyncio.fixture
async def seeded_msmes(msme_repo: MSMERepository) -> dict:
    """
    Seed both synthetic personas (Sakhi + Annapurna) into the test DB.

    Returns a dict with both MSME objects for use in tests.
    """
    sakhi = await msme_repo.upsert("msme_sakhi_001", SAKHI_MSME_DATA)
    anna = await msme_repo.upsert("msme_anna_002", ANNA_MSME_DATA)
    await msme_repo._session.commit()
    return {"sakhi": sakhi, "anna": anna}
