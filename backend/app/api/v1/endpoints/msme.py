"""
MSME Profiles Endpoint.
"""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, RoleChecker
from app.db.repositories.msme import MSMERepository
from app.db.repositories.alternate_data import AlternateDataRepository
from app.db.models import ConsentRecord
from sqlalchemy import select

router = APIRouter(tags=["MSME Profiles"])
require_bank_access = RoleChecker(["bank_officer", "underwriter", "admin"])


@router.get(
    "/msme/{msme_id}",
    summary="Retrieve MSME Profile Information",
)
async def get_msme_profile(
    msme_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
) -> dict:
    """
    Fetch static demographic information, registration details,
    vintage, and industry sector classification for a specified MSME.
    """
    repo = MSMERepository(db)
    msme = await repo.get_by_msme_id(msme_id)
    if not msme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MSME profile not found for id: {msme_id}"
        )

    return {
        "data": {
            "id": msme.id,
            "msme_id": msme.msme_id,
            "legal_name": msme.legal_name,
            "udyam_number": msme.udyam_number,
            "sector": msme.sector,
            "sub_sector": msme.sub_sector,
            "vintage_years": msme.vintage_years,
            "state": msme.state,
            "registration_type": msme.registration_type,
            "created_at": msme.created_at.isoformat() if msme.created_at else None,
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/msme/{msme_id}/data-sources",
    summary="Get connected data sources catalog",
)
async def get_msme_data_sources(
    msme_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
) -> dict:
    """
    Returns lists of alternate data sources that have been connected
    under existing active or expired consent objects.
    """
    # Look up consents in database
    stmt = select(ConsentRecord).where(ConsentRecord.msme_id == msme_id)
    result = await db.execute(stmt)
    consents = result.scalars().all()
    
    connected_sources = set()
    for c in consents:
        try:
            sources = json.loads(c.data_types_json)
            connected_sources.update(sources)
        except Exception:
            pass

    return {
        "data": {
            "msme_id": msme_id,
            "connected_sources": list(connected_sources),
            "consent_count": len(consents),
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }
