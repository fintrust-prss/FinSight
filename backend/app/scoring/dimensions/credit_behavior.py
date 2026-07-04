"""
Dimension 6: Credit Behavior Scorer.

Calculates score from:
  1. Credit bureau score (CIBIL/CRIF) or a conservative "no-file" fallback
  2. Bureau enquiries volume in the last 6 months
  3. Bank statement repayment proxy (bounces & overdraft patterns)
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, threshold_score


def score_credit_behavior(data: MSMEData) -> DimensionScore:
    """
    Score the Credit Behavior dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("credit_behavior")

    sub_scores = []
    sub_weights = []

    # 1. Bureau Score
    if data.bureau_has_file and data.bureau_score is not None:
        score_val = float(data.bureau_score)
        bureau_score = threshold_score(score_val, cfg["bureau_score"]["thresholds"])
        reasons.append(f"Credit Bureau Score: {score_val:.0f} (Score: {bureau_score:.0f})")
    else:
        # Credit Invisible / Thin File
        bureau_score = float(cfg["bureau_score"]["thresholds"]["no_file"]["score"])
        reasons.append(f"Credit Bureau: Credit Invisible / Thin File fallback (Score: {bureau_score:.0f})")
    
    sub_scores.append(bureau_score)
    sub_weights.append(cfg["bureau_score"]["weight"])

    # 2. Bureau Enquiries (Last 6 Months)
    enq_val = float(data.bureau_enquiries_6m)
    enq_score = threshold_score(enq_val, cfg["bureau_enquiries_6m"]["thresholds"])
    sub_scores.append(enq_score)
    sub_weights.append(cfg["bureau_enquiries_6m"]["weight"])
    reasons.append(f"Credit Bureau Enquiries (last 6m): {enq_val:.0f} (Score: {enq_score:.0f})")

    # 3. AA-based Repayment Proxy (computed from bank statement bounces & overdrafts)
    has_bank = data.bank_summaries is not None and not data.bank_summaries.empty
    if has_bank:
        bank_df = data.bank_summaries
        total_bounces = int(bank_df["bounce_count"].sum())
        avg_overdraft = float(bank_df["overdraft_days"].mean())

        # Formula: penalize bounces heavily (-15% each) and overdraft days moderately (-2% per day avg)
        regularity = 1.0 - (total_bounces * 0.15) - (avg_overdraft * 0.02)
        regularity = max(0.0, min(1.0, regularity))

        repay_score = threshold_score(regularity, cfg["aa_repayment_proxy"]["thresholds"])
        reasons.append(
            f"Account Aggregator Repayment Proxy: {regularity*100:.0f}% regularity ({total_bounces} bounces, {avg_overdraft:.1f} avg overdraft days) (Score: {repay_score:.0f})"
        )
    else:
        # Default thin file / cash-only penalty
        repay_score = float(cfg["aa_repayment_proxy"]["thresholds"]["poor"]["score"])
        reasons.append(f"Account Aggregator Repayment: No bank summaries to evaluate (Score: {repay_score:.0f})")

    sub_scores.append(repay_score)
    sub_weights.append(cfg["aa_repayment_proxy"]["weight"])

    # Aggregate weighted score
    total_w = sum(sub_weights)
    final_score = sum(s * (w / total_w) for s, w in zip(sub_scores, sub_weights))

    return DimensionScore(
        dimension="credit_behavior",
        score=final_score,
        reasons=reasons,
        data_available=True,
    )
