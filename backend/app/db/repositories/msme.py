"""
MSME Repository — domain queries for the core MSME profile.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import MSME
from app.db.repositories.base import BaseRepository


class MSMERepository(BaseRepository[MSME]):
    """
    MSME-specific queries.

    Usage::
        async with async_session_factory() as session:
            repo = MSMERepository(session)
            msme = await repo.get_by_msme_id("msme_sakhi_001")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MSME)

    # ------------------------------------------------------------------ #
    # Lookups
    # ------------------------------------------------------------------ #

    async def get_by_msme_id(self, msme_id: str) -> MSME | None:
        """Fetch MSME by its business-level ID (e.g. Udyam number prefix)."""
        result = await self._session.execute(
            select(MSME).where(MSME.msme_id == msme_id)
        )
        return result.scalars().first()

    async def get_by_udyam(self, udyam_number: str) -> MSME | None:
        """Fetch MSME by Udyam registration number."""
        result = await self._session.execute(
            select(MSME).where(MSME.udyam_number == udyam_number)
        )
        return result.scalars().first()

    async def get_with_all_relations(self, msme_id: str) -> MSME | None:
        """
        Fetch MSME with all child relations eagerly loaded.

        Suitable for the health-card score computation pipeline which
        needs all alternate data in a single round-trip.
        """
        result = await self._session.execute(
            select(MSME)
            .where(MSME.msme_id == msme_id)
            .options(
                selectinload(MSME.gst_returns),
                selectinload(MSME.upi_summaries),
                selectinload(MSME.bank_summaries),
                selectinload(MSME.epfo_records),
                selectinload(MSME.utility_records),
                selectinload(MSME.bureau_record),
                selectinload(MSME.digital_footprints),
            )
        )
        return result.scalars().first()

    async def list_by_state(self, state: str, limit: int = 50) -> list[MSME]:
        """Fetch MSMEs filtered by state — for portfolio dashboards."""
        result = await self._session.execute(
            select(MSME).where(MSME.state == state).limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_sector(self, sector: str, limit: int = 50) -> list[MSME]:
        """Fetch MSMEs filtered by sector."""
        result = await self._session.execute(
            select(MSME).where(MSME.sector == sector).limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Upsert
    # ------------------------------------------------------------------ #

    async def upsert(self, msme_id: str, data: dict) -> MSME:
        """
        Create-or-update MSME profile by msme_id.

        Used by the synthetic data loader and the AA consent flow.
        """
        existing = await self.get_by_msme_id(msme_id)
        if existing:
            return await self.update(existing, data)
        create_data = data.copy()
        create_data["msme_id"] = msme_id
        instance = MSME(**create_data)
        return await self.create(instance)
