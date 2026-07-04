"""
Dimension 2: Compliance & Formalization Scorer.

Calculates score from:
  1. GST filing timeliness rate (last 18 months)
  2. Udyam registration status
  3. EPFO payment timeliness / contribution rate
  4. Business licensing compliance
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, threshold_score


def score_compliance_formalization(data: MSMEData) -> DimensionScore:
    """
    Score the Compliance & Formalization dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("compliance_formalization")

    sub_scores = []
    sub_weights = []

    # 1. GST Filing Rate
    has_gst = data.gst_returns is not None and not data.gst_returns.empty
    if has_gst:
        gst_df = data.gst_returns
        total_gst_months = len(gst_df)
        if total_gst_months > 0:
            # Check how many filed on time
            on_time_count = int(gst_df["filed_on_time"].sum())
            filing_rate = on_time_count / total_gst_months
            gst_score = threshold_score(filing_rate, cfg["gst_filing_rate"]["thresholds"])
            sub_scores.append(gst_score)
            sub_weights.append(cfg["gst_filing_rate"]["weight"])
            reasons.append(
                f"GST Filing Timeliness: {filing_rate*100:.0f}% ({on_time_count}/{total_gst_months} on time) (Score: {gst_score:.0f})"
            )
        else:
            has_gst = False

    # 2. Udyam Registered
    udyam_val = "registered" if data.udyam_registered else "not_registered"
    udyam_score = float(cfg["udyam_registered"]["scores"][udyam_val])
    sub_scores.append(udyam_score)
    sub_weights.append(cfg["udyam_registered"]["weight"])
    reasons.append(f"Udyam Registered: {data.udyam_registered} (Score: {udyam_score:.0f})")

    # 3. EPFO Filing Rate
    has_epfo = data.epfo_records is not None and not data.epfo_records.empty
    if has_epfo:
        epfo_df = data.epfo_records
        total_epfo_months = len(epfo_df)
        if total_epfo_months > 0:
            paid_count = int(epfo_df["contribution_paid"].sum())
            epfo_rate = paid_count / total_epfo_months
            epfo_score = threshold_score(epfo_rate, cfg["epfo_filing_rate"]["thresholds"])
            sub_scores.append(epfo_score)
            sub_weights.append(cfg["epfo_filing_rate"]["weight"])
            reasons.append(
                f"EPFO Contribution Regularity: {epfo_rate*100:.0f}% ({paid_count}/{total_epfo_months} paid) (Score: {epfo_score:.0f})"
            )
        else:
            has_epfo = False
    else:
        # If thin file/no workers, penalize conservatively but keep score
        epfo_score = float(cfg["epfo_filing_rate"]["thresholds"]["critical"]["score"])
        sub_scores.append(epfo_score)
        sub_weights.append(cfg["epfo_filing_rate"]["weight"])
        reasons.append(f"EPFO Contribution: No EPFO records found (Score: {epfo_score:.0f})")

    # 4. License Validity
    # Since license_valid is dynamic but not in core models, we default to valid (100) or check if udyam registration exists
    license_status = "valid" if data.udyam_registered else "missing"
    lic_score = float(cfg["license_valid"]["scores"][license_status])
    sub_scores.append(lic_score)
    sub_weights.append(cfg["license_valid"]["weight"])
    reasons.append(f"Regulatory Licenses Status: {license_status.capitalize()} (Score: {lic_score:.0f})")

    # Normalize weights of present sub-metrics
    total_w = sum(sub_weights)
    final_score = sum(s * (w / total_w) for s, w in zip(sub_scores, sub_weights))

    return DimensionScore(
        dimension="compliance_formalization",
        score=final_score,
        reasons=reasons,
        data_available=True
    )
