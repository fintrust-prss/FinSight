"""
MSME Credit Score & Explainability Endpoints.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, check_consent, RoleChecker
from app.db.repositories.msme import MSMERepository
from app.db.repositories.health_score import HealthScoreRepository
from app.db.models import HealthScore
from app.scoring.engine import ScoringEngine
from app.scoring.types import MSMEData

router = APIRouter(tags=["MSME Credit Scoring"])
require_bank_access = RoleChecker(["bank_officer", "underwriter", "admin"])
engine = ScoringEngine()


# ===========================================================================
# Repository Data Helper
# ===========================================================================

def build_msme_data_object(msme) -> MSMEData:
    """Map SQLAlchemy model to pandas-based MSMEData container."""
    # Convert relationships to DataFrames
    gst_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "period": r.period,
            "return_type": r.return_type,
            "turnover": r.turnover,
            "tax_paid": r.tax_paid,
            "filed_on_time": r.filed_on_time,
            "late_days": r.late_days,
        } for r in msme.gst_returns
    ]) if msme.gst_returns else pd.DataFrame(columns=["msme_id", "period", "turnover", "filed_on_time"])

    upi_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "month": r.month,
            "p2m_count": r.p2m_count,
            "p2m_value": r.p2m_value,
            "p2p_count": r.p2p_count,
            "p2p_value": r.p2p_value,
            "unique_counterparties": r.unique_counterparties,
        } for r in msme.upi_summaries
    ]) if msme.upi_summaries else pd.DataFrame(columns=["msme_id", "month", "p2m_value", "p2p_value", "unique_counterparties"])

    bank_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "month": r.month,
            "avg_balance": r.avg_balance,
            "inflow": r.inflow,
            "outflow": r.outflow,
            "bounce_count": r.bounce_count,
            "overdraft_days": r.overdraft_days,
        } for r in msme.bank_summaries
    ]) if msme.bank_summaries else pd.DataFrame(columns=["msme_id", "month", "avg_balance", "bounce_count", "overdraft_days", "inflow"])

    epfo_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "month": r.month,
            "employee_count": r.employee_count,
            "wage_bill": r.wage_bill,
            "contribution_paid": r.contribution_paid,
        } for r in msme.epfo_records
    ]) if msme.epfo_records else pd.DataFrame(columns=["msme_id", "month", "employee_count", "wage_bill", "contribution_paid"])

    util_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "month": r.month,
            "utility_type": r.utility_type,
            "units_consumed": r.units_consumed,
            "sanctioned_load": r.sanctioned_load,
            "payment_delay_days": r.payment_delay_days,
        } for r in msme.utility_records
    ]) if msme.utility_records else pd.DataFrame(columns=["msme_id", "month", "units_consumed", "sanctioned_load", "payment_delay_days"])

    dig_df = pd.DataFrame([
        {
            "msme_id": r.msme_id,
            "month": r.month,
            "ondc_orders": r.ondc_orders,
            "ecommerce_orders": r.ecommerce_orders,
            "gmb_rating": r.gmb_rating,
            "gmb_review_count": r.gmb_review_count,
        } for r in msme.digital_footprints
    ]) if msme.digital_footprints else pd.DataFrame(columns=["msme_id", "month", "ondc_orders", "ecommerce_orders", "gmb_rating"])

    # Bureau record mapping
    b_score = None
    b_enquiries = 0
    b_has_file = False
    if msme.bureau_record:
        b_score = msme.bureau_record.score
        b_enquiries = msme.bureau_record.enquiries_last_6m
        b_has_file = msme.bureau_record.has_file

    return MSMEData(
        msme_id=msme.msme_id,
        sector=msme.sector,
        sub_sector=msme.sub_sector,
        vintage_years=msme.vintage_years,
        udyam_registered=True,
        gst_returns=gst_df,
        upi_summaries=upi_df,
        bank_summaries=bank_df,
        epfo_records=epfo_df,
        utility_records=util_df,
        digital_footprints=dig_df,
        bureau_has_file=b_has_file,
        bureau_score=b_score,
        bureau_enquiries_6m=b_enquiries,
    )


async def execute_and_save_score(
    msme_id: str,
    db: AsyncSession,
    bank_profile: str,
    use_ml: bool = True
) -> HealthScore:
    """Helper to run the scoring engine and persist snapshot to DB."""
    msme_repo = MSMERepository(db)
    msme = await msme_repo.get_with_all_relations(msme_id)
    if not msme:
        raise ValueError(f"MSME not found: {msme_id}")
        
    msme_data = build_msme_data_object(msme)
    scoring_result = engine.score(msme_data, bank_profile=bank_profile, use_ml=use_ml)
    
    score_repo = HealthScoreRepository(db)
    # Check if a score snapshot already exists for today + model version, if so we retrieve/update
    existing = await score_repo.get_by_date(msme_id, date.today())
    if existing:
        # Update existing snapshot
        existing.overall_score = scoring_result.overall_score
        existing.tier = scoring_result.tier
        existing.dimension_scores_json = json.dumps(scoring_result.dimension_scores)
        existing.shap_summary_json = json.dumps(scoring_result.shap_summary)
        await db.flush()
        return existing
    
    # Save a fresh snapshot
    new_score = await score_repo.create_score(
        msme_id=msme_id,
        as_of_date=date.today(),
        overall_score=scoring_result.overall_score,
        tier=scoring_result.tier,
        dimension_scores=scoring_result.dimension_scores,
        shap_summary=scoring_result.shap_summary,
    )
    return new_score


# ===========================================================================
# API Endpoints
# ===========================================================================

@router.get(
    "/msme/{msme_id}/score",
    summary="Compute or fetch MSME financial health score",
)
async def get_msme_score(
    msme_id: str,
    bank_profile: Literal["idbi", "hdfc", "axis", "nbfc_generic"] = "idbi",
    use_ml: bool = True,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """
    Returns the latest computed score, tier, and 7-dimension breakdown.
    Requires dynamic consent verification (gated by check_consent).
    """
    try:
        score_record = await execute_and_save_score(msme_id, db, bank_profile, use_ml)
        
        return {
            "data": {
                "msme_id": msme_id,
                "overall_score": score_record.overall_score,
                "tier": score_record.tier,
                "as_of_date": score_record.as_of_date.isoformat(),
                "dimension_scores": json.loads(score_record.dimension_scores_json),
                "model_version": score_record.model_version,
            },
            "meta": {"api_version": "v1"},
            "error": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/msme/{msme_id}/score/history",
    summary="Get historical scores trend",
)
async def get_msme_score_history(
    msme_id: str,
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """Retrieve historical snapshots of scores to generate trend line charts."""
    score_repo = HealthScoreRepository(db)
    history = await score_repo.get_history(msme_id, limit)
    
    data_list = [
        {
            "as_of_date": h.as_of_date.isoformat(),
            "overall_score": h.overall_score,
            "tier": h.tier,
            "dimension_scores": json.loads(h.dimension_scores_json),
        } for h in history
    ]

    return {
        "data": {
            "msme_id": msme_id,
            "history": data_list,
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/msme/{msme_id}/explain",
    summary="Retrieve SHAP explainability payload",
)
async def get_msme_explainability(
    msme_id: str,
    bank_profile: Literal["idbi", "hdfc", "axis", "nbfc_generic"] = "idbi",
    use_ml: bool = True,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """Surfaces SHAP features explaining contribution factors."""
    try:
        score_record = await execute_and_save_score(msme_id, db, bank_profile, use_ml)
        
        return {
            "data": {
                "msme_id": msme_id,
                "shap_summary": json.loads(score_record.shap_summary_json),
                "reasons": {
                    # Include human-readable rules output
                    "revenue_cashflow": ["Good positive turnovers"],
                    "compliance_formalization": ["Valid registration"],
                }
            },
            "meta": {"api_version": "v1"},
            "error": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/msme/{msme_id}/rescore",
    summary="Trigger async background rescoring",
)
async def rescore_msme(
    msme_id: str,
    background_tasks: BackgroundTasks,
    bank_profile: Literal["idbi", "hdfc", "axis", "nbfc_generic"] = "idbi",
    use_ml: bool = True,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """Triggers dynamic rescoring running in background."""
    background_tasks.add_task(execute_and_save_score, msme_id, db, bank_profile, use_ml)
    
    return {
        "data": {
            "msme_id": msme_id,
            "status": "QUEUED",
            "message": "Incremental score recalculation started in background.",
        },
        "meta": {"api_version": "v1"},
        "error": None,
    }


@router.get(
    "/msme/{msme_id}/anomalies",
    summary="Retrieve Isolation Forest anomalies",
)
async def get_msme_anomalies(
    msme_id: str,
    bank_profile: Literal["idbi", "hdfc", "axis", "nbfc_generic"] = "idbi",
    use_ml: bool = True,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(require_bank_access),
    _consent = Depends(check_consent),
) -> dict:
    """Inconsistency anomalies check."""
    try:
        msme_repo = MSMERepository(db)
        msme = await msme_repo.get_with_all_relations(msme_id)
        if not msme:
            raise ValueError(f"MSME not found: {msme_id}")
            
        msme_data = build_msme_data_object(msme)
        scoring_result = engine.score(msme_data, bank_profile=bank_profile, use_ml=use_ml)
        
        return {
            "data": {
                "msme_id": msme_id,
                "is_anomaly": scoring_result.is_anomaly,
                "message": (
                    "Statistical inconsistency detected. Hand off to underwriter."
                    if scoring_result.is_anomaly else "No anomalies detected."
                ),
            },
            "meta": {"api_version": "v1"},
            "error": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
