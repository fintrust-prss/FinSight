"""
Ecosystem rails simulator endpoints (ULI / OCEN / AA mock connectors).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, RoleChecker, check_consent
from app.db.models import ConsentRecord, MSME
from app.ecosystem.aa import AASimulator
from app.ecosystem.uli import ULISimulator
from app.ecosystem.ocen import OCENSimulator
from app.api.v1.endpoints.score import execute_and_save_score

router = APIRouter(tags=["Ecosystem Simulators"])
require_bank_access = RoleChecker(["bank_officer", "underwriter", "admin"])


class InitiateAARequest(BaseModel):
    msme_id: str = Field(..., example="msme_sakhi_001")
    data_types: List[str] = Field(
        default_factory=lambda: ["gst", "upi", "bank_statement", "epfo", "utility", "digital_footprint"]
    )
    purpose: str = Field("Credit Scoring Assessment", example="Credit Assessment")
    valid_hours: int = Field(24, description="Hours before consent expires")


@router.get(
    "/ecosystem/uli/status",
    summary="Mock Unified Lending Interface (ULI) connector status",
)
def get_uli_status(_current_user: dict = Depends(require_bank_access)) -> dict:
    """Returns mock connectivity and status metrics for ULI integrations."""
    return {
        "data": {
            "connector_id": "uli_conn_idbi_prod_01",
            "status": "ONLINE",
            "ping_latency_ms": 14.5,
            "connected_since": "2026-07-01T00:00:00Z",
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/ecosystem/ocen/status",
    summary="Mock Open Credit Enablement Network (OCEN) connector status",
)
def get_ocen_status(_current_user: dict = Depends(require_bank_access)) -> dict:
    """Returns mock connectivity and status metrics for OCEN integrations."""
    return {
        "data": {
            "connector_id": "ocen_lsp_connector_02",
            "status": "ONLINE",
            "ping_latency_ms": 22.1,
            "connected_since": "2026-07-01T00:00:00Z",
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.post(
    "/ecosystem/aa/request",
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Account Aggregator Consent Flow",
)
async def initiate_aa_consent(
    payload: InitiateAARequest,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Initiate the AA consent flow. Creates a PENDING consent record in the database.
    """
    # Verify MSME exists
    stmt = select(MSME).where(MSME.msme_id == payload.msme_id)
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MSME profile not found for ID: {payload.msme_id}"
        )

    sim_res = AASimulator.initiate_consent_request(
        payload.msme_id, payload.data_types, payload.purpose, payload.valid_hours
    )
    
    consent_id = f"consent_sim_{uuid.uuid4().hex[:12]}"
    expiry_time = datetime.now(timezone.utc) + timedelta(hours=payload.valid_hours)
    
    new_consent = ConsentRecord(
        consent_id=consent_id,
        msme_id=payload.msme_id,
        data_types_json=json.dumps(payload.data_types),
        purpose=payload.purpose,
        status="PENDING",
        expiry=expiry_time,
    )
    
    db.add(new_consent)
    await db.flush()
    
    sim_res["consent_id"] = consent_id
    
    return {
        "data": sim_res,
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/ecosystem/aa/pending",
    summary="Fetch all pending AA consent requests",
)
async def get_pending_consents(
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Lists all PENDING consent records in the database.
    """
    stmt = select(ConsentRecord).where(ConsentRecord.status == "PENDING")
    res = await db.execute(stmt)
    records = res.scalars().all()
    
    return {
        "data": [
            {
                "consent_id": r.consent_id,
                "msme_id": r.msme_id,
                "data_types": json.loads(r.data_types_json),
                "purpose": r.purpose,
                "status": r.status,
                "expiry": r.expiry.isoformat(),
            }
            for r in records
        ],
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.post(
    "/ecosystem/aa/approve/{consent_id}",
    summary="Approve a pending AA consent request",
)
async def approve_aa_consent(
    consent_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Transition a PENDING consent request to ACTIVE.
    """
    stmt = select(ConsentRecord).where(ConsentRecord.consent_id == consent_id)
    res = await db.execute(stmt)
    record = res.scalars().first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent record not found: {consent_id}"
        )
        
    if record.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consent record is not in PENDING status. Current: {record.status}"
        )
        
    record.status = "ACTIVE"
    await db.flush()
    
    return {
        "data": {
            "consent_id": record.consent_id,
            "msme_id": record.msme_id,
            "status": record.status,
            "expiry": record.expiry.isoformat(),
            "msg": "Consent granted successfully. Scoring unlock authorized."
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.post(
    "/ecosystem/aa/revoke/{consent_id}",
    summary="Revoke an active AA consent",
)
async def revoke_aa_consent(
    consent_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Revoke a consent request (forces status to REVOKED).
    """
    stmt = select(ConsentRecord).where(ConsentRecord.consent_id == consent_id)
    res = await db.execute(stmt)
    record = res.scalars().first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent record not found: {consent_id}"
        )
        
    record.status = "REVOKED"
    await db.flush()
    
    return {
        "data": {
            "consent_id": record.consent_id,
            "msme_id": record.msme_id,
            "status": record.status,
            "msg": "Consent revoked successfully."
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/ecosystem/uli/fetch/{msme_id}",
    summary="Fetch standardized data package via ULI simulator",
)
async def fetch_uli_data(
    msme_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """
    Returns ULI-standardized data package. Requires an active consent record.
    """
    data = ULISimulator.fetch_standardized_profile(msme_id)
    return {
        "data": data,
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/ecosystem/ocen/lsp-signal/{msme_id}",
    summary="Fetch loan-eligibility signal exchange stub via OCEN simulator",
)
async def fetch_ocen_signal(
    msme_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """
    Calculates/fetches score and outputs OCEN-compliant loan-eligibility signal exchange.
    Requires active consent record.
    """
    try:
        score_record = await execute_and_save_score(msme_id, db, "idbi", use_ml=False)
        score = score_record.overall_score
    except Exception:
        score = 0.0

    signal = OCENSimulator.generate_loan_offer_signal(msme_id, score)
    return {
        "data": signal,
        "meta": {"api_version": "v1"},
        "error": None,
    }
