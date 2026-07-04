"""
Account Aggregator Consent Simulator Endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.db.models import ConsentRecord

router = APIRouter(tags=["Ecosystem Simulators"])


class CreateConsentRequest(BaseModel):
    """Parameters to create/simulate consent."""
    msme_id: str = Field(..., example="msme_sakhi_001")
    data_types: list[str] = Field(
        default_factory=lambda: ["gst", "upi", "bank_statement", "epfo", "utility", "digital_footprint"],
        example=["gst", "upi", "bank_statement"]
    )
    purpose: str = Field("Credit Scoring Assessment", example="Credit Assessment")
    valid_hours: int = Field(24, description="Hours before consent expires")


class ConsentResponse(BaseModel):
    """Consent record details."""
    consent_id: str
    msme_id: str
    data_types: list[str]
    purpose: str
    status: str
    expiry: datetime


@router.post(
    "/consent",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate AA Consent Grant",
)
async def create_consent_simulation(
    payload: CreateConsentRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Simulate Account Aggregator consent authorization.
    Inserts a ConsentRecord into the database that acts as the gating
    token for alternate credit scoring.
    """
    import json
    
    consent_id = f"consent_sim_{uuid.uuid4().hex[:12]}"
    expiry_time = datetime.now(timezone.utc) + timedelta(hours=payload.valid_hours)
    
    # Store standard JSON fields
    new_consent = ConsentRecord(
        consent_id=consent_id,
        msme_id=payload.msme_id,
        data_types_json=json.dumps(payload.data_types),
        purpose=payload.purpose,
        status="ACTIVE",
        expiry=expiry_time,
    )
    
    db.add(new_consent)
    await db.flush()
    
    return {
        "data": {
            "consent_id": consent_id,
            "msme_id": payload.msme_id,
            "data_types": payload.data_types,
            "purpose": payload.purpose,
            "status": "ACTIVE",
            "expiry": expiry_time.isoformat(),
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }
