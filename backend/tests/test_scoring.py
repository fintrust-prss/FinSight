"""
Unit Tests for the Phase 3 Scoring Engine.

Validates:
  1. Config loading and weight profiles
  2. Mathematical scoring utilities (HHI, CoV, growth)
  3. Single-dimension scorers (edge cases, missing data, thresholds)
  4. ScoringEngine end-to-end (overall score, decision tiers, profiles)
"""

from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd
import pytest

from app.scoring.config_loader import get_bank_profile_weights, get_dimension_config, get_decision_tiers
from app.scoring.types import MSMEData, threshold_score, compute_cov, compute_hhi, growth_rate_pct
from app.scoring.engine import ScoringEngine
from app.scoring.dimensions.revenue_cashflow import score_revenue_cashflow
from app.scoring.dimensions.compliance_formalization import score_compliance_formalization
from app.scoring.dimensions.workforce_stability import score_workforce_stability
from app.scoring.dimensions.operational_footprint import score_operational_footprint
from app.scoring.dimensions.digital_adoption import score_digital_adoption
from app.scoring.dimensions.credit_behavior import score_credit_behavior
from app.scoring.dimensions.resilience_volatility import score_resilience_volatility


# ===========================================================================
# 1. Config Loader Tests
# ===========================================================================

def test_config_loader():
    """Verify profile weights and configurations load correctly."""
    # Test bank profiles load and have weights summing to 1.0
    for profile in ["idbi", "hdfc", "nbfc_generic"]:
        weights = get_bank_profile_weights(profile)
        assert len(weights) == 7
        assert abs(sum(weights.values()) - 1.0) < 1e-5

    # Test unknown profile raises KeyError
    with pytest.raises(KeyError):
        get_bank_profile_weights("invalid_bank")

    # Test dimension configs exist
    rev_cfg = get_dimension_config("revenue_cashflow")
    assert "gst_turnover" in rev_cfg
    assert "avg_balance" in rev_cfg

    # Test decision tiers exist
    tiers = get_decision_tiers()
    assert "disciplined" in tiers
    assert "no_go" in tiers


# ===========================================================================
# 2. Math Utility Tests
# ===========================================================================

def test_math_utilities():
    """Test standard scoring math calculations."""
    # CoV (std / mean)
    s1 = pd.Series([100.0, 100.0, 100.0])
    assert compute_cov(s1) == 0.0
    s2 = pd.Series([10.0, 20.0, 30.0])  # mean=20, std=10 (ddof=1)
    assert abs(compute_cov(s2) - 0.5) < 1e-5
    s_zero = pd.Series([0.0, 0.0])
    assert compute_cov(s_zero) == 1.0

    # HHI (Herfindahl-Hirschman Index)
    # 1 unique counterparty -> max concentration -> HHI = 1.0
    assert compute_hhi(pd.Series([10])) == 1.0
    # Equal distribution -> HHI = sum((1/N)^2) = N * (1/N^2) = 1/N
    assert abs(compute_hhi(pd.Series([5, 5, 5, 5])) - 0.25) < 1e-5

    # Growth rate MoM
    assert growth_rate_pct(pd.Series([100])) == 0.0
    # MoM changes: 100 -> 110 (10%), 110 -> 121 (10%). Average should be 10%
    assert abs(growth_rate_pct(pd.Series([100.0, 110.0, 121.0])) - 10.0) < 1e-5


def test_threshold_score():
    """Test mapping continuous values to discrete scores based on thresholds."""
    # Sample threshold structure:
    thresholds = {
        "excellent": {"min_score": 750, "score": 95},
        "good": {"min_score": 700, "score": 80},
        "fair": {"min_score": 650, "score": 60},
        "poor": {"min_score": 600, "score": 35},
        "critical": {"below": 600, "score": 15},
    }
    assert threshold_score(770, thresholds) == 95.0
    assert threshold_score(710, thresholds) == 80.0
    assert threshold_score(670, thresholds) == 60.0
    assert threshold_score(610, thresholds) == 35.0
    assert threshold_score(550, thresholds) == 15.0


# ===========================================================================
# 3. Dimension Scorers & Orchestrator end-to-end
# ===========================================================================

@pytest.fixture
def disciplined_msme_data() -> MSMEData:
    """Mock a strong, disciplined MSME (Sakhi-like profile)."""
    # 12 months history
    months = [date(2025, i, 1) for i in range(1, 13)]
    
    # 1. Steady GST turnovers with ~5% MoM growth
    gst = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "period": months,
        "return_type": ["GSTR-3B"] * 12,
        "turnover": [100000.0 * (1.05**i) for i in range(12)],
        "tax_paid": [18000.0] * 12,
        "filed_on_time": [True] * 12,
        "late_days": [0] * 12
    })

    # 2. Stable UPI inflow (CoV ~0.0)
    upi = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "month": months,
        "p2m_count": [100] * 12,
        "p2m_value": [50000.0] * 12,
        "p2p_count": [10] * 12,
        "p2p_value": [5000.0] * 12,
        "unique_counterparties": [15] * 12  # HHI = 1/15 = 0.067 (Excellent)
    })

    # 3. High average bank balance, 0 bounces, 0 overdraft
    bank = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "month": months,
        "avg_balance": [600000.0] * 12,  # >5L (Excellent)
        "inflow": [100000.0] * 12,
        "outflow": [90000.0] * 12,
        "bounce_count": [0] * 12,        # 0 bounces (Excellent)
        "overdraft_days": [0] * 12
    })

    # 4. EPFO contribution is 100% on time, employee headcount growing
    epfo = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "month": months,
        "employee_count": [40 + i for i in range(12)],  # growth from 40 to 52 (>10%, Excellent)
        "wage_bill": [480000.0 + i*12000 for i in range(12)],
        "contribution_paid": [True] * 12
    })

    # 5. Ideal utility utilization (70% load) and 100% on time
    utility = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "month": months,
        "utility_type": ["electricity"] * 12,
        "units_consumed": [3500.0] * 12,
        "sanctioned_load": [50.0] * 12,  # 3500/(50*100) = 70% (Excellent)
        "payment_delay_days": [0] * 12
    })

    # 6. E-commerce digital presence (GMB 4.5, many orders)
    digital = pd.DataFrame({
        "msme_id": ["msme_sakhi"] * 12,
        "month": months,
        "ondc_orders": [40] * 12,
        "ecommerce_orders": [80] * 12,  # 120 total orders (Excellent)
        "gmb_rating": [4.5] * 12,       # Excellent GBP rating
        "gmb_review_count": [120] * 12
    })

    return MSMEData(
        msme_id="msme_sakhi_001",
        sector="manufacturing",
        sub_sector="food_manufacturing",
        vintage_years=12.0,
        udyam_registered=True,
        gst_returns=gst,
        upi_summaries=upi,
        bank_summaries=bank,
        epfo_records=epfo,
        utility_records=utility,
        digital_footprints=digital,
        bureau_has_file=True,
        bureau_score=780,  # Excellent (CIBIL 780)
        bureau_enquiries_6m=0,
    )


@pytest.fixture
def erratic_msme_data() -> MSMEData:
    """Mock a high-risk, erratic MSME (Annapurna-like profile)."""
    months = [date(2025, i, 1) for i in range(1, 13)]
    
    # 1. Volatile GST turnovers with negative MoM growth
    gst = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "period": months,
        "return_type": ["GSTR-3B"] * 12,
        "turnover": [100000.0 * (0.95**i) for i in range(12)], # Decline
        "tax_paid": [18000.0] * 12,
        "filed_on_time": [True] * 10 + [False] * 2, # 2 late filings (83% on time)
        "late_days": [0] * 10 + [15, 20]
    })

    # 2. Concentrated UPI (HHI = 1/2 = 0.5, Concentrated)
    upi = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "month": months,
        "p2m_count": [50] * 12,
        "p2m_value": [30000.0] * 12,
        "p2p_count": [50] * 12,
        "p2p_value": [30000.0] * 12, # 50% P2M ratio
        "unique_counterparties": [2] * 12  
    })

    # 3. Low balance, 3 bounces, some overdraft days
    bank = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "month": months,
        "avg_balance": [5000.0] * 12,  # <10K (Critical)
        "inflow": [60000.0] * 12,
        "outflow": [59000.0] * 12,
        "bounce_count": [0] * 9 + [1, 1, 1], # 3 bounces total
        "overdraft_days": [0] * 9 + [5, 10, 8]  # overdraft stress
    })

    # 4. EPFO missed contribution month
    epfo = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "month": months,
        "employee_count": [8] * 12,  # headcount flat (No growth)
        "wage_bill": [96000.0] * 12,
        "contribution_paid": [True] * 11 + [False]  # Missed 1 month
    })

    # 5. Low utility utilization, 1 payment delay, 1 disconnection event
    utility = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "month": months,
        "utility_type": ["electricity"] * 12,
        "units_consumed": [1600.0] * 11 + [0.0],  # Disconnection at month 12!
        "sanctioned_load": [20.0] * 12,  # 1600 / (20*100) = 80% utilization
        "payment_delay_days": [0] * 10 + [15, 45]
    })

    # 6. Poor digital orders, GMB rating 3.2
    digital = pd.DataFrame({
        "msme_id": ["msme_anna"] * 12,
        "month": months,
        "ondc_orders": [2] * 12,
        "ecommerce_orders": [3] * 12,  # 5 total orders (Fair)
        "gmb_rating": [3.2] * 12,
        "gmb_review_count": [5] * 12
    })

    return MSMEData(
        msme_id="msme_anna_002",
        sector="manufacturing",
        sub_sector="food_manufacturing",
        vintage_years=2.5,
        udyam_registered=True,
        gst_returns=gst,
        upi_summaries=upi,
        bank_summaries=bank,
        epfo_records=epfo,
        utility_records=utility,
        digital_footprints=digital,
        bureau_has_file=False,  # Credit invisible / fallback (no file)
        bureau_score=None,
        bureau_enquiries_6m=4,
    )


def test_scoring_dimensions(disciplined_msme_data, erratic_msme_data):
    """Verify each dimension scorer works correctly for both profiles."""
    
    # --- Revenue & Cash Flow ---
    score_a = score_revenue_cashflow(disciplined_msme_data)
    score_b = score_revenue_cashflow(erratic_msme_data)
    assert score_a.score > score_b.score
    assert score_a.data_available is True
    assert score_b.data_available is True

    # --- Compliance ---
    score_a = score_compliance_formalization(disciplined_msme_data)
    score_b = score_compliance_formalization(erratic_msme_data)
    assert score_a.score > score_b.score

    # --- Workforce Stability ---
    score_a = score_workforce_stability(disciplined_msme_data)
    score_b = score_workforce_stability(erratic_msme_data)
    assert score_a.score > score_b.score

    # --- Operational Footprint ---
    score_a = score_operational_footprint(disciplined_msme_data)
    score_b = score_operational_footprint(erratic_msme_data)
    assert score_a.score > score_b.score

    # --- Digital Adoption ---
    score_a = score_digital_adoption(disciplined_msme_data)
    score_b = score_digital_adoption(erratic_msme_data)
    assert score_a.score > score_b.score

    # --- Credit Behavior ---
    score_a = score_credit_behavior(disciplined_msme_data)
    score_b = score_credit_behavior(erratic_msme_data)
    assert score_a.score > score_b.score

    # --- Resilience & Volatility ---
    score_a = score_resilience_volatility(disciplined_msme_data)
    score_b = score_resilience_volatility(erratic_msme_data)
    assert score_a.score > score_b.score


def test_scoring_engine_end_to_end(disciplined_msme_data, erratic_msme_data):
    """Verify unified aggregation and decision tier assignment in ScoringEngine."""
    engine = ScoringEngine()

    # Score Disciplined MSME
    res_a = engine.score(disciplined_msme_data, bank_profile="idbi", use_ml=False)
    assert res_a.overall_score >= 75.0
    assert res_a.tier == "Disciplined"
    assert res_a.action == "Yes-Go"

    # Score Erratic MSME
    res_b = engine.score(erratic_msme_data, bank_profile="idbi", use_ml=False)
    assert res_b.overall_score < res_a.overall_score
    assert res_b.overall_score < 65.0
    assert res_b.tier in ("Non-Disciplined", "No-Go", "Moderately Disciplined")

    # Verify score variation under different profiles
    res_a_idbi = engine.score(disciplined_msme_data, bank_profile="idbi", use_ml=False)
    res_a_nbfc = engine.score(disciplined_msme_data, bank_profile="nbfc_generic", use_ml=False)
    
    # Scores should be slightly different due to weight profiles, but both high
    assert abs(res_a_idbi.overall_score - res_a_nbfc.overall_score) > 0.01
    assert res_a_idbi.overall_score >= 70.0
    assert res_a_nbfc.overall_score >= 70.0
