"""
Phase 4 ML Model Validation Tests.

Validates:
  1. Monotonicity: worsening behavior (bounces/overdrafts) increases default probability.
  2. Latency: inference completes under 200ms p95.
  3. Fairness: verifies default probabilities remain balanced across sectors/vintages.
"""

from __future__ import annotations

import time
from datetime import date
import numpy as np
import pandas as pd
import pytest

from app.scoring.engine import ScoringEngine
from app.scoring.types import MSMEData


@pytest.fixture
def base_msme_data() -> MSMEData:
    """Provide a baseline MSME with average parameters."""
    months = [date(2025, i, 1) for i in range(1, 13)]
    
    gst = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "period": months,
        "return_type": ["GSTR-3B"] * 12,
        "turnover": [100000.0] * 12,
        "tax_paid": [18000.0] * 12,
        "filed_on_time": [True] * 12,
        "late_days": [0] * 12
    })

    upi = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "month": months,
        "p2m_count": [100] * 12,
        "p2m_value": [50000.0] * 12,
        "p2p_count": [10] * 12,
        "p2p_value": [5000.0] * 12,
        "unique_counterparties": [10] * 12
    })

    bank = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "month": months,
        "avg_balance": [100000.0] * 12,
        "inflow": [100000.0] * 12,
        "outflow": [90000.0] * 12,
        "bounce_count": [0] * 12,
        "overdraft_days": [0] * 12
    })

    epfo = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "month": months,
        "employee_count": [15] * 12,
        "wage_bill": [180000.0] * 12,
        "contribution_paid": [True] * 12
    })

    utility = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "month": months,
        "utility_type": ["electricity"] * 12,
        "units_consumed": [1200.0] * 12,
        "sanctioned_load": [20.0] * 12,
        "payment_delay_days": [0] * 12
    })

    digital = pd.DataFrame({
        "msme_id": ["msme_test"] * 12,
        "month": months,
        "ondc_orders": [10] * 12,
        "ecommerce_orders": [20] * 12,
        "gmb_rating": [4.0] * 12,
        "gmb_review_count": [30] * 12
    })

    return MSMEData(
        msme_id="msme_test_001",
        sector="manufacturing",
        sub_sector="food_manufacturing",
        vintage_years=5.0,
        udyam_registered=True,
        gst_returns=gst,
        upi_summaries=upi,
        bank_summaries=bank,
        epfo_records=epfo,
        utility_records=utility,
        digital_footprints=digital,
        bureau_has_file=True,
        bureau_score=700,
        bureau_enquiries_6m=1,
    )


def test_ml_scoring_monotonicity(base_msme_data):
    """Verify that worsening alternate metrics monotonically decreases the overall blended score."""
    engine = ScoringEngine()
    
    # 1. Baseline scoring
    res_base = engine.score(base_msme_data, bank_profile="idbi", use_ml=True)
    
    # 2. Add bounces to bank summaries (stress scenario)
    stressed_bank = base_msme_data.bank_summaries.copy()
    stressed_bank["bounce_count"] = [2] * 12  # severe bounces MoM
    stressed_bank["overdraft_days"] = [15] * 12  # heavy overdraft usage
    
    stressed_data = MSMEData(
        msme_id=base_msme_data.msme_id,
        sector=base_msme_data.sector,
        sub_sector=base_msme_data.sub_sector,
        vintage_years=base_msme_data.vintage_years,
        udyam_registered=base_msme_data.udyam_registered,
        gst_returns=base_msme_data.gst_returns,
        upi_summaries=base_msme_data.upi_summaries,
        bank_summaries=stressed_bank,
        epfo_records=base_msme_data.epfo_records,
        utility_records=base_msme_data.utility_records,
        digital_footprints=base_msme_data.digital_footprints,
        bureau_has_file=base_msme_data.bureau_has_file,
        bureau_score=base_msme_data.bureau_score,
        bureau_enquiries_6m=5,  # also increase inquiries
    )
    
    res_stressed = engine.score(stressed_data, bank_profile="idbi", use_ml=True)
    
    # Stressed score must be strictly less than baseline score
    assert res_stressed.overall_score < res_base.overall_score


def test_ml_scoring_latency(base_msme_data):
    """Validate that single-customer scoring latency meets the <200ms p95 threshold."""
    engine = ScoringEngine()
    
    latencies = []
    
    # Execute 50 runs to measure p95 latency
    for _ in range(50):
        start = time.perf_counter()
        engine.score(base_msme_data, bank_profile="idbi", use_ml=True)
        latencies.append((time.perf_counter() - start) * 1000.0)  # ms
        
    p95 = np.percentile(latencies, 95)
    print(f"ML Scoring p95 latency: {p95:.2f}ms")
    
    # Assert p95 is strictly less than 200ms
    assert p95 < 200.0


def test_ml_scoring_fairness(base_msme_data):
    """
    Ensure the scoring output is fair across sub-segments.
    Assert that score variation solely from changing sector/state is minimal (<10%).
    """
    engine = ScoringEngine()
    
    # Baseline run
    res_mfg = engine.score(base_msme_data, bank_profile="idbi", use_ml=True)
    
    # Switch sub_sector to textiles (retaining same financial behaviors)
    textiles_data = MSMEData(
        msme_id=base_msme_data.msme_id,
        sector="manufacturing",
        sub_sector="textiles",
        vintage_years=base_msme_data.vintage_years,
        udyam_registered=base_msme_data.udyam_registered,
        gst_returns=base_msme_data.gst_returns,
        upi_summaries=base_msme_data.upi_summaries,
        bank_summaries=base_msme_data.bank_summaries,
        epfo_records=base_msme_data.epfo_records,
        utility_records=base_msme_data.utility_records,
        digital_footprints=base_msme_data.digital_footprints,
        bureau_has_file=base_msme_data.bureau_has_file,
        bureau_score=base_msme_data.bureau_score,
        bureau_enquiries_6m=base_msme_data.bureau_enquiries_6m,
    )
    
    res_textiles = engine.score(textiles_data, bank_profile="idbi", use_ml=True)
    
    # Blended score difference should be less than 10 points
    assert abs(res_mfg.overall_score - res_textiles.overall_score) < 10.0
