"""
AlternateData Repository — bulk insert and query helpers for all 7 alternate-data tables.

Used by:
  1. The synthetic data loader (Phase 1 output → Postgres)
  2. The scoring engine (reads 24 months of data per MSME)
  3. The API data-explorer endpoint (Phase 5)
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import (
    BankStatementSummary,
    BureauRecord,
    DigitalFootprint,
    EPFORecord,
    GSTReturn,
    UPITransactionSummary,
    UtilityConsumption,
)
from app.db.repositories.base import BaseRepository


class AlternateDataRepository:
    """
    Compound repository for all alternate-data tables.

    Wraps a single session and exposes sub-repository-like methods
    for each data type. Designed for batch ingest and bulk reads.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    # GST Returns
    # ------------------------------------------------------------------ #

    async def upsert_gst_returns(self, records: list[dict]) -> int:
        """Bulk upsert GST return records (ON CONFLICT DO UPDATE)."""
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(GSTReturn).where(
                    and_(
                        GSTReturn.msme_id == rec["msme_id"],
                        GSTReturn.period == rec["period"],
                        GSTReturn.return_type == rec.get("return_type", "GSTR-3B"),
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(GSTReturn(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_gst_returns(
        self, msme_id: str, from_date: date | None = None, to_date: date | None = None
    ) -> list[GSTReturn]:
        """Fetch GST returns for an MSME within an optional date range."""
        stmt = select(GSTReturn).where(GSTReturn.msme_id == msme_id)
        if from_date:
            stmt = stmt.where(GSTReturn.period >= from_date)
        if to_date:
            stmt = stmt.where(GSTReturn.period <= to_date)
        stmt = stmt.order_by(GSTReturn.period)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # UPI Transaction Summaries
    # ------------------------------------------------------------------ #

    async def upsert_upi_summaries(self, records: list[dict]) -> int:
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(UPITransactionSummary).where(
                    and_(
                        UPITransactionSummary.msme_id == rec["msme_id"],
                        UPITransactionSummary.month == rec["month"],
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(UPITransactionSummary(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_upi_summaries(self, msme_id: str, months: int = 24) -> list[UPITransactionSummary]:
        result = await self._session.execute(
            select(UPITransactionSummary)
            .where(UPITransactionSummary.msme_id == msme_id)
            .order_by(UPITransactionSummary.month.desc())
            .limit(months)
        )
        return list(reversed(result.scalars().all()))  # Return chronologically

    # ------------------------------------------------------------------ #
    # Bank Statement Summaries
    # ------------------------------------------------------------------ #

    async def upsert_bank_summaries(self, records: list[dict]) -> int:
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(BankStatementSummary).where(
                    and_(
                        BankStatementSummary.msme_id == rec["msme_id"],
                        BankStatementSummary.month == rec["month"],
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(BankStatementSummary(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_bank_summaries(self, msme_id: str, months: int = 24) -> list[BankStatementSummary]:
        result = await self._session.execute(
            select(BankStatementSummary)
            .where(BankStatementSummary.msme_id == msme_id)
            .order_by(BankStatementSummary.month.desc())
            .limit(months)
        )
        return list(reversed(result.scalars().all()))

    # ------------------------------------------------------------------ #
    # EPFO Records
    # ------------------------------------------------------------------ #

    async def upsert_epfo_records(self, records: list[dict]) -> int:
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(EPFORecord).where(
                    and_(
                        EPFORecord.msme_id == rec["msme_id"],
                        EPFORecord.month == rec["month"],
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(EPFORecord(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_epfo_records(self, msme_id: str, months: int = 24) -> list[EPFORecord]:
        result = await self._session.execute(
            select(EPFORecord)
            .where(EPFORecord.msme_id == msme_id)
            .order_by(EPFORecord.month.desc())
            .limit(months)
        )
        return list(reversed(result.scalars().all()))

    # ------------------------------------------------------------------ #
    # Utility Consumption
    # ------------------------------------------------------------------ #

    async def upsert_utility_records(self, records: list[dict]) -> int:
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(UtilityConsumption).where(
                    and_(
                        UtilityConsumption.msme_id == rec["msme_id"],
                        UtilityConsumption.month == rec["month"],
                        UtilityConsumption.utility_type == rec.get("utility_type", "electricity"),
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(UtilityConsumption(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_utility_records(self, msme_id: str, months: int = 24) -> list[UtilityConsumption]:
        result = await self._session.execute(
            select(UtilityConsumption)
            .where(UtilityConsumption.msme_id == msme_id)
            .order_by(UtilityConsumption.month.desc())
            .limit(months)
        )
        return list(reversed(result.scalars().all()))

    # ------------------------------------------------------------------ #
    # Bureau Record
    # ------------------------------------------------------------------ #

    async def upsert_bureau_record(self, record: dict) -> BureauRecord:
        existing = await self._session.execute(
            select(BureauRecord).where(BureauRecord.msme_id == record["msme_id"])
        )
        row = existing.scalars().first()
        if row:
            for k, v in record.items():
                setattr(row, k, v)
            await self._session.flush()
            return row
        instance = BureauRecord(**record)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_bureau_record(self, msme_id: str) -> BureauRecord | None:
        result = await self._session.execute(
            select(BureauRecord).where(BureauRecord.msme_id == msme_id)
        )
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Digital Footprint
    # ------------------------------------------------------------------ #

    async def upsert_digital_footprints(self, records: list[dict]) -> int:
        count = 0
        for rec in records:
            existing = await self._session.execute(
                select(DigitalFootprint).where(
                    and_(
                        DigitalFootprint.msme_id == rec["msme_id"],
                        DigitalFootprint.month == rec["month"],
                    )
                )
            )
            row = existing.scalars().first()
            if row:
                for k, v in rec.items():
                    setattr(row, k, v)
            else:
                self._session.add(DigitalFootprint(**rec))
                count += 1
        await self._session.flush()
        return count

    async def get_digital_footprints(self, msme_id: str, months: int = 24) -> list[DigitalFootprint]:
        result = await self._session.execute(
            select(DigitalFootprint)
            .where(DigitalFootprint.msme_id == msme_id)
            .order_by(DigitalFootprint.month.desc())
            .limit(months)
        )
        return list(reversed(result.scalars().all()))
