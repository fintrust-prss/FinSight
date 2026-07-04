"""
Dimension 3: Workforce Stability Scorer.

Calculates score from:
  1. EPFO employee headcount growth trend (last 12 months)
  2. Wage bill growth trend (MoM average)
  3. EPFO contribution payment regularity consistency
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, growth_rate_pct, threshold_score


def score_workforce_stability(data: MSMEData) -> DimensionScore:
    """
    Score the Workforce Stability dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("workforce_stability")

    has_epfo = data.epfo_records is not None and not data.epfo_records.empty
    if not has_epfo:
        return DimensionScore(
            dimension="workforce_stability",
            score=20.0,  # Conservatively low if EPFO data is completely absent
            reasons=["No EPFO registration or contribution data available"],
            data_available=False,
        )

    epfo_df = data.epfo_records.sort_values("month")
    
    # 1. Headcount Growth Trend (past 12 months)
    # Get last 12 months or whatever is available
    recent_epfo = epfo_df.tail(12)
    
    # Calculate headcount growth (percentage change first vs last or MoM avg)
    # The helper growth_rate_pct computes the average MoM growth percentage.
    # Alternatively, the spec suggests "% change last 12 months" - let's compute:
    # (final_headcount - initial_headcount) / initial_headcount * 100
    if len(recent_epfo) >= 2:
        initial_hc = float(recent_epfo.iloc[0]["employee_count"])
        final_hc = float(recent_epfo.iloc[-1]["employee_count"])
        hc_growth = ((final_hc - initial_hc) / initial_hc * 100) if initial_hc > 0 else 0.0
    else:
        hc_growth = 0.0

    hc_score = threshold_score(hc_growth, cfg["headcount_growth"]["thresholds"])
    reasons.append(f"EPFO Headcount Growth: {hc_growth:+.1f}% (Score: {hc_score:.0f})")

    # 2. Wage Bill Growth Trend (average MoM %)
    wage_growth = growth_rate_pct(epfo_df["wage_bill"])
    wage_score = threshold_score(wage_growth, cfg["wage_bill_growth"]["thresholds"])
    reasons.append(f"EPFO Wage Bill Growth (MoM avg): {wage_growth:+.1f}% (Score: {wage_score:.0f})")

    # 3. Contribution Consistency (contribution_paid rate)
    paid_count = int(epfo_df["contribution_paid"].sum())
    total_months = len(epfo_df)
    consistency_rate = paid_count / total_months if total_months > 0 else 0.0
    const_score = threshold_score(consistency_rate, cfg["contribution_consistency"]["thresholds"])
    reasons.append(
        f"EPFO Contribution Consistency: {consistency_rate*100:.0f}% ({paid_count}/{total_months} months) (Score: {const_score:.0f})"
    )

    # Aggregate weighted score
    w_hc = cfg["headcount_growth"]["weight"]
    w_wage = cfg["wage_bill_growth"]["weight"]
    w_const = cfg["contribution_consistency"]["weight"]

    final_score = (hc_score * w_hc) + (wage_score * w_wage) + (const_score * w_const)

    return DimensionScore(
        dimension="workforce_stability",
        score=final_score,
        reasons=reasons,
        data_available=True,
    )
