"""
Portfolio aggregation dashboard endpoints for bank officers and underwriters.
"""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, RoleChecker
from app.db.models import MSME, HealthScore
from app.db.repositories.msme import MSMERepository
from app.db.repositories.health_score import HealthScoreRepository

router = APIRouter(tags=["Portfolio Dashboard"])
require_bank_access = RoleChecker(["bank_officer", "underwriter", "admin"])


@router.get(
    "/portfolio/summary",
    summary="Bank-level aggregate portfolio dashboard summary",
)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
) -> dict:
    """
    Returns counts by decision tiers and the list of onboarded MSMEs
    with their latest health score cards. Used by the dashboard index screen.
    """
    try:
        msme_repo = MSMERepository(db)
        score_repo = HealthScoreRepository(db)

        msmes = await msme_repo.get_all(limit=100)

        tier_counts = {
            "Disciplined": 0,
            "Moderately Disciplined": 0,
            "Non-Disciplined": 0,
            "No-Go": 0,
        }

        msme_list = []

        for m in msmes:
            latest_score = await score_repo.get_latest(m.msme_id)

            score_val = None
            tier_val = "Non-Disciplined"

            if latest_score:
                score_val = latest_score.overall_score
                tier_val = latest_score.tier
                if tier_val in tier_counts:
                    tier_counts[tier_val] += 1
            else:
                tier_counts["Non-Disciplined"] += 1

            msme_list.append({
                "msme_id": m.msme_id,
                "legal_name": m.legal_name,
                "udyam_number": m.udyam_number,
                "sector": m.sector,
                "state": m.state,
                "latest_score": score_val,
                "tier": tier_val,
            })

        return {
            "data": {
                "total_msmes": len(msmes),
                "tier_distribution": tier_counts,
                "msmes": msme_list,
            },
            "meta": {"api_version": "v1"},
            "error": None,
        }
    except Exception:
        return {
            "data": {
                "total_msmes": 0,
                "tier_distribution": {
                    "Disciplined": 0,
                    "Moderately Disciplined": 0,
                    "Non-Disciplined": 0,
                    "No-Go": 0,
                },
                "msmes": [],
            },
            "meta": {"api_version": "v1"},
            "error": None,
        }
