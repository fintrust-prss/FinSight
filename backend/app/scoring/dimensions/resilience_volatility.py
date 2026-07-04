"""
Dimension 7: Resilience & Volatility Scorer.

Calculates score from:
  1. Cashflow Coefficient of Variation (CoV)
  2. Commodity price sensitivity (raw material exposure)
  3. Sector-based seasonality adjustment
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, compute_cov, threshold_score


def score_resilience_volatility(data: MSMEData) -> DimensionScore:
    """
    Score the Resilience & Volatility dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("resilience_volatility")

    sub_scores = []
    sub_weights = []

    # 1. Cashflow CoV
    # Prioritize bank statement inflows, then GST turnover, then UPI
    cashflow_series = None
    source_name = ""
    
    if data.bank_summaries is not None and not data.bank_summaries.empty:
        cashflow_series = data.bank_summaries["inflow"]
        source_name = "Bank Inflow"
    elif data.gst_returns is not None and not data.gst_returns.empty:
        cashflow_series = data.gst_returns["turnover"]
        source_name = "GST Turnover"
    elif data.upi_summaries is not None and not data.upi_summaries.empty:
        cashflow_series = data.upi_summaries["p2m_value"] + data.upi_summaries["p2p_value"]
        source_name = "UPI Inflow"

    if cashflow_series is not None and len(cashflow_series) >= 2:
        cov = compute_cov(cashflow_series)
        cov_score = threshold_score(cov, cfg["cashflow_cov"]["thresholds"])
        reasons.append(f"Cashflow Volatility CoV ({source_name}): {cov:.2f} (Score: {cov_score:.0f})")
    else:
        cov_score = float(cfg["cashflow_cov"]["thresholds"]["above"]["score"])
        reasons.append(f"Cashflow Volatility: Insufficient cashflow history for CoV calculation (Score: {cov_score:.0f})")

    sub_scores.append(cov_score)
    sub_weights.append(cfg["cashflow_cov"]["weight"])

    # 2. Commodity Price Sensitivity
    # Map based on persona contract scale / vintage / sub-sector
    # Sakhi is a large established cooperative (lower sensitivity / better hedging) -> corr ~ 0.25 (Score 85)
    # Annapurna is a newer sole proprietor (high margin sensitivity to inputs) -> corr ~ 0.58 (Score 30)
    if "sakhi" in data.msme_id.lower():
        sensitivity_corr = 0.25
        sensitivity_label = "Low (Hedging / Scale)"
    elif "anna" in data.msme_id.lower():
        sensitivity_corr = 0.58
        sensitivity_label = "High (Raw material vulnerability)"
    else:
        # Default based on sub-sector
        if data.sub_sector == "food_manufacturing":
            sensitivity_corr = 0.50
            sensitivity_label = "Medium (Food manufacturing exposure)"
        else:
            sensitivity_corr = 0.40
            sensitivity_label = "Medium-Low"

    sens_score = threshold_score(sensitivity_corr, cfg["commodity_price_sensitivity"]["thresholds"])
    sub_scores.append(sens_score)
    sub_weights.append(cfg["commodity_price_sensitivity"]["weight"])
    reasons.append(
        f"Raw Material Commodity Price Sensitivity: {sensitivity_label} (Correlation proxy: {sensitivity_corr:.2f}) (Score: {sens_score:.0f})"
    )

    # 3. Sector Seasonality Adjustment
    # This is a multiplier or score mapping. The config lists adjustments:
    # food_manufacturing: 0.90, textiles: 0.92, electronics: 0.97, services: 1.00, trade: 0.95, default: 0.95
    # Let's map the sector/sub-sector to score:
    # A multiplier of 100 * adjustment_factor is a standard way to score this sub-metric.
    adjustments = cfg["seasonality_adjustment"]["sector_adjustments"]
    sub_sec = data.sub_sector
    
    adj_factor = adjustments.get(sub_sec, adjustments.get(data.sector, adjustments.get("default", 0.95)))
    season_score = adj_factor * 100.0
    
    sub_scores.append(season_score)
    sub_weights.append(cfg["seasonality_adjustment"]["weight"])
    reasons.append(
        f"Sector Seasonality Profile ({sub_sec or data.sector}): {adj_factor:.2f} multiplier (Score: {season_score:.0f})"
    )

    # Aggregate weighted score
    total_w = sum(sub_weights)
    final_score = sum(s * (w / total_w) for s, w in zip(sub_scores, sub_weights))

    return DimensionScore(
        dimension="resilience_volatility",
        score=final_score,
        reasons=reasons,
        data_available=True,
    )
