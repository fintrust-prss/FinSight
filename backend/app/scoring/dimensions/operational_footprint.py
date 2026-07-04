"""
Dimension 4: Operational Footprint Scorer.

Calculates score from:
  1. Electricity utilization (units_consumed vs sanctioned_load)
  2. Utility bill payment timeliness rate
  3. Seasonality alignment (correlation with GST turnover)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, threshold_score


def score_operational_footprint(data: MSMEData) -> DimensionScore:
    """
    Score the Operational Footprint dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("operational_footprint")

    has_utility = data.utility_records is not None and not data.utility_records.empty
    if not has_utility:
        return DimensionScore(
            dimension="operational_footprint",
            score=20.0,  # Conservatively low if utility data is completely absent
            reasons=["No utility consumption records available"],
            data_available=False,
        )

    util_df = data.utility_records.sort_values("month")
    
    # 1. Electricity utilization: units_consumed / (sanctioned_load * 100)
    # optimal range 60–90% (0.60–0.90)
    mean_units = float(util_df["units_consumed"].mean())
    mean_load = float(util_df["sanctioned_load"].mean())
    
    if mean_load > 0:
        util_ratio = mean_units / (mean_load * 100.0)
    else:
        util_ratio = 0.0

    util_score = threshold_score(util_ratio, cfg["electricity_utilization"]["thresholds"])
    reasons.append(
        f"Electricity Load Utilization: {util_ratio*100:.1f}% (Avg consumed: {mean_units:.0f} kWh, load: {mean_load:.0f} kW) (Score: {util_score:.0f})"
    )

    # 2. Payment regularity for utility bills (% months paid on time - delay == 0)
    total_months = len(util_df)
    on_time_months = int((util_df["payment_delay_days"] == 0).sum())
    payment_rate = on_time_months / total_months if total_months > 0 else 0.0
    
    payment_score = threshold_score(payment_rate, cfg["utility_payment_rate"]["thresholds"])
    
    # Check for disconnection event: units_consumed == 0.0 or severe delay
    # Applied as a subtraction penalty
    has_disconnection = bool((util_df["units_consumed"] == 0.0).any())
    penalty = 0.0
    if has_disconnection:
        penalty = float(cfg["utility_payment_rate"].get("disconnection_penalty", -40))
        payment_score = max(0.0, payment_score + penalty)
        reasons.append(
            f"Utility Bill Payment Regularity: {payment_rate*100:.0f}% (Disconnection event detected! Penalty: {penalty:.0f}) (Score: {payment_score:.0f})"
        )
    else:
        reasons.append(
            f"Utility Bill Payment Regularity: {payment_rate*100:.0f}% ({on_time_months}/{total_months} on time) (Score: {payment_score:.0f})"
        )

    # 3. Seasonality alignment (correlation between electricity units and GST turnovers)
    align_score = 50.0  # default neutral
    has_gst = data.gst_returns is not None and not data.gst_returns.empty
    if has_gst:
        gst_df = data.gst_returns[["period", "turnover"]].rename(columns={"period": "date"})
        elec_df = util_df[["month", "units_consumed"]].rename(columns={"month": "date"})
        # Merge on date
        merged = pd.merge(gst_df, elec_df, on="date")
        if len(merged) >= 3:
            # Check standard deviation of both, if zero, corr is undef
            if merged["turnover"].std() > 0 and merged["units_consumed"].std() > 0:
                corr = float(merged["turnover"].corr(merged["units_consumed"]))
                if not np.isnan(corr):
                    align_score = threshold_score(corr, cfg["seasonality_alignment"]["thresholds"])
                    reasons.append(f"Electricity & GST Correlation: {corr:.2f} (Score: {align_score:.0f})")
                else:
                    reasons.append("Electricity & GST Correlation: Undefined (no variance) (Score: 50)")
            else:
                reasons.append("Electricity & GST Correlation: No variance in series (Score: 50)")
        else:
            reasons.append("Electricity & GST Correlation: Insufficient overlapping data (Score: 50)")
    else:
        reasons.append("Electricity & GST Correlation: No GST data to correlate (Score: 50)")

    # Aggregate weighted score
    w_util = cfg["electricity_utilization"]["weight"]
    w_pay = cfg["utility_payment_rate"]["weight"]
    w_align = cfg["seasonality_alignment"]["weight"]

    final_score = (util_score * w_util) + (payment_score * w_pay) + (align_score * w_align)

    return DimensionScore(
        dimension="operational_footprint",
        score=final_score,
        reasons=reasons,
        data_available=True,
    )
