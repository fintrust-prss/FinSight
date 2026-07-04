"""
HealthScore Repository — queries for score snapshots and trend history.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HealthScore
from app.db.repositories.base import BaseRepository


class HealthScoreRepository(BaseRepository[HealthScore]):
    """
    HealthScore-specific queries.

    HealthScore rows are append-only snapshots — never updated in place.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HealthScore)

    async def get_latest(self, msme_id: str) -> HealthScore | None:
        """Fetch the most recent score for an MSME."""
        result = await self._session.execute(
            select(HealthScore)
            .where(HealthScore.msme_id == msme_id)
            .order_by(desc(HealthScore.as_of_date), desc(HealthScore.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def get_history(self, msme_id: str, limit: int = 12) -> list[HealthScore]:
        """Fetch the N most recent score snapshots for trend charts."""
        result = await self._session.execute(
            select(HealthScore)
            .where(HealthScore.msme_id == msme_id)
            .order_by(desc(HealthScore.as_of_date))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_date(self, msme_id: str, as_of_date: date) -> HealthScore | None:
        """Fetch the score for a specific computation date."""
        result = await self._session.execute(
            select(HealthScore)
            .where(
                HealthScore.msme_id == msme_id,
                HealthScore.as_of_date == as_of_date,
            )
            .order_by(desc(HealthScore.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def create_score(
        self,
        msme_id: str,
        as_of_date: date,
        overall_score: float,
        tier: str,
        dimension_scores: dict,
        shap_summary: dict,
        model_version: str = "1.0.0",
    ) -> HealthScore:
        """Append a new score snapshot (scores are never mutated)."""
        instance = HealthScore(
            msme_id=msme_id,
            as_of_date=as_of_date,
            overall_score=overall_score,
            tier=tier,
            model_version=model_version,
            dimension_scores_json=json.dumps(dimension_scores),
            shap_summary_json=json.dumps(shap_summary),
        )
        return await self.create(instance)

    def decode_dimension_scores(self, score: HealthScore) -> dict:
        """Deserialize dimension_scores_json to a Python dict."""
        return json.loads(score.dimension_scores_json)

    def decode_shap_summary(self, score: HealthScore) -> dict:
        """Deserialize shap_summary_json to a Python dict."""
        return json.loads(score.shap_summary_json)

    async def list_by_tier(self, tier: str, limit: int = 50) -> list[HealthScore]:
        """
        Fetch the latest scores filtered by tier.

        Used by portfolio dashboard to segment MSMEs into risk buckets.
        NOTE: This is a subquery approach — returns one row per MSME only
        for the latest score.
        """
        # Subquery: latest as_of_date per msme_id
        from sqlalchemy import func
        latest_dates = (
            select(
                HealthScore.msme_id,
                func.max(HealthScore.as_of_date).label("max_date"),
            )
            .group_by(HealthScore.msme_id)
            .subquery()
        )

        result = await self._session.execute(
            select(HealthScore)
            .join(
                latest_dates,
                (HealthScore.msme_id == latest_dates.c.msme_id)
                & (HealthScore.as_of_date == latest_dates.c.max_date),
            )
            .where(HealthScore.tier == tier)
            .limit(limit)
        )
        return list(result.scalars().all())
