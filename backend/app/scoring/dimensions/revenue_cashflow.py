"""
Dimension 1: Revenue & Cash Flow Health Scorer.

Calculates score from:
  1. GST MoM growth (%)
  2. UPI inflow Coefficient of Variation (stability)
  3. Average bank balance (INR)
  4. Bank statement cheque bounce rate
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, growth_rate_pct, compute_cov, threshold_score


def score_revenue_cashflow(data: MSMEData) -> DimensionScore:
    """
    Score the Revenue & Cash Flow Health dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("revenue_cashflow")
    
    # Check if we have any cashflow data
    has_gst = data.gst_returns is not None and not data.gst_returns.empty
    has_upi = data.upi_summaries is not None and not data.upi_summaries.empty
    has_bank = data.bank_summaries is not None and not data.bank_summaries.empty

    if not (has_gst or has_upi or has_bank):
        return DimensionScore(
            dimension="revenue_cashflow",
            score=20.0,  # Penalty for zero cashflow records
            reasons=["No tax or banking transactional data available"],
            data_available=False
        )

    sub_scores = []
    sub_weights = []

    # 1. GST Turnover MoM growth
    if has_gst:
        gst_df = data.gst_returns.sort_values("period")
        growth = growth_rate_pct(gst_df["turnover"])
        gst_score = threshold_score(growth, cfg["gst_turnover"]["thresholds"])
        sub_scores.append(gst_score)
        sub_weights.append(cfg["gst_turnover"]["weight"])
        reasons.append(f"GST Turnover MoM Growth: {growth:+.1f}% (Score: {gst_score:.0f})")
    
    # 2. UPI/POS Inflow stability (CoV)
    if has_upi:
        upi_df = data.upi_summaries.sort_values("month")
        # UPI inflow is represented by p2m_value + p2p_value (or just p2m_value as commercial inflow)
        inflows = upi_df["p2m_value"] + upi_df["p2p_value"]
        cov = compute_cov(inflows)
        upi_score = threshold_score(cov, cfg["upi_inflow_cov"]["thresholds"])
        sub_scores.append(upi_score)
        sub_weights.append(cfg["upi_inflow_cov"]["weight"])
        reasons.append(f"UPI Inflow Volatility (CoV): {cov:.2f} (Score: {upi_score:.0f})")

    # 3. Average Monthly Balance & Cheque Bounce Rate (from Bank Statement)
    if has_bank:
        bank_df = data.bank_summaries.sort_values("month")
        
        # Avg Balance
        avg_bal = float(bank_df["avg_balance"].mean())
        bal_score = threshold_score(avg_bal, cfg["avg_balance"]["thresholds"])
        sub_scores.append(bal_score)
        sub_weights.append(cfg["avg_balance"]["weight"])
        reasons.append(f"Avg Monthly Bank Balance: INR {avg_bal:,.0f} (Score: {bal_score:.0f})")

        # Cheque Bounce Rate
        # Bounces vs total inflows (or count of transactions) - let's compute bounce rate as
        # bounce_count / (total transactions or bounce_count + transaction counts).
        # Alternatively, the spec threshold is:
        # excellent: <= 1% bounce_rate, good: <= 3%, etc.
        # Let's compute bounce rate as bounce_count / total inflows transaction count if available,
        # or simply treat the average monthly bounce count or a count ratio.
        # Let's check UPI transaction counts or look at bounce count directly.
        # Since we only have bounce_count and inflows/outflows, let's compute bounce rate as:
        # bounce_count / (number of months * 30) or bounce_count / estimated inflow transactions,
        # or simply average monthly bounces. The spec says: "bounce rate (bounced transactions / total)"
        # Let's check if the UPI P2M count can be a proxy for total transactions, or use a default base of 100 transactions/month.
        # Let's check if there is transaction count in bank statement summary - there is not, just bounce_count.
        # So let's divide bounce_count by total transaction count (UPI P2M count + P2P count) if available, otherwise default to 50 transactions.
        total_transactions = 1
        if has_upi:
            total_transactions = int(upi_df["p2m_count"].sum() + upi_df["p2p_count"].sum())
        total_transactions = max(total_transactions, len(bank_df) * 30)  # fallback to 30 tx per month
        
        total_bounces = int(bank_df["bounce_count"].sum())
        bounce_rate = total_bounces / total_transactions
        bounce_score = threshold_score(bounce_rate, cfg["bounce_rate"]["thresholds"])
        sub_scores.append(bounce_score)
        sub_weights.append(cfg["bounce_rate"]["weight"])
        reasons.append(f"Cheque Bounce Rate: {bounce_rate*100:.2f}% ({total_bounces} bounces) (Score: {bounce_score:.0f})")

    if not sub_scores:
        return DimensionScore(
            dimension="revenue_cashflow",
            score=30.0,
            reasons=["Incomplete transactional data to score cashflow"],
            data_available=False
        )

    # Normalize weights of present sub-metrics
    total_w = sum(sub_weights)
    final_score = sum(s * (w / total_w) for s, w in zip(sub_scores, sub_weights))

    return DimensionScore(
        dimension="revenue_cashflow",
        score=final_score,
        reasons=reasons,
        data_available=True
    )
