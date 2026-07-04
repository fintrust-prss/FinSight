"""
Dimension 5: Digital Adoption & Market Reach Scorer.

Calculates score from:
  1. UPI HHI (concentration calculated from unique counterparties count)
  2. UPI P2M ratio (business-to-merchant share of total UPI)
  3. Digital commerce order volume (ONDC + e-commerce)
  4. Google Business Profile rating (GMB)
"""

from __future__ import annotations

import pandas as pd
from app.scoring.config_loader import get_dimension_config
from app.scoring.types import DimensionScore, MSMEData, threshold_score


def score_digital_adoption(data: MSMEData) -> DimensionScore:
    """
    Score the Digital Adoption & Market Reach dimension (0-100).
    """
    reasons = []
    cfg = get_dimension_config("digital_adoption")

    sub_scores = []
    sub_weights = []

    # 1. UPI metrics (HHI and P2M ratio)
    has_upi = data.upi_summaries is not None and not data.upi_summaries.empty
    if has_upi:
        upi_df = data.upi_summaries
        
        # 1a. UPI HHI (Proxy: 1.0 / unique_counterparties)
        mean_parties = float(upi_df["unique_counterparties"].mean())
        # Prevent division by zero
        hhi = 1.0 / mean_parties if mean_parties > 0 else 1.0
        hhi_score = threshold_score(hhi, cfg["upi_hhi"]["thresholds"])
        sub_scores.append(hhi_score)
        sub_weights.append(cfg["upi_hhi"]["weight"])
        reasons.append(
            f"UPI Counterparty Concentration (HHI): {hhi:.2f} (Avg unique counterparties: {mean_parties:.1f}) (Score: {hhi_score:.0f})"
        )

        # 1b. P2M Ratio = p2m_value / (p2m_value + p2p_value)
        total_p2m = float(upi_df["p2m_value"].sum())
        total_p2p = float(upi_df["p2p_value"].sum())
        total_upi = total_p2m + total_p2p
        p2m_ratio = total_p2m / total_upi if total_upi > 0 else 0.0
        
        p2m_score = threshold_score(p2m_ratio, cfg["upi_p2m_ratio"]["thresholds"])
        sub_scores.append(p2m_score)
        sub_weights.append(cfg["upi_p2m_ratio"]["weight"])
        reasons.append(
            f"UPI Merchant (P2M) Transaction Ratio: {p2m_ratio*100:.1f}% (INR {total_p2m:,.0f} of INR {total_upi:,.0f}) (Score: {p2m_score:.0f})"
        )
    else:
        # Default thin file / cash-only penalty
        hhi_score = float(cfg["upi_hhi"]["thresholds"]["critical"]["score"])
        sub_scores.append(hhi_score)
        sub_weights.append(cfg["upi_hhi"]["weight"])
        
        p2m_score = float(cfg["upi_p2m_ratio"]["thresholds"]["poor"]["score"])
        sub_scores.append(p2m_score)
        sub_weights.append(cfg["upi_p2m_ratio"]["weight"])
        
        reasons.append(f"UPI Transactions: No UPI transactional data available (HHI Score: {hhi_score:.0f}, P2M Score: {p2m_score:.0f})")

    # 2. Digital Platform Presence (ONDC + e-commerce orders per month average)
    has_digital = data.digital_footprints is not None and not data.digital_footprints.empty
    if has_digital:
        df = data.digital_footprints
        avg_ondc = df["ondc_orders"].mean()
        avg_ecom = df["ecommerce_orders"].mean()
        avg_orders = float(avg_ondc + avg_ecom)
        
        orders_score = threshold_score(avg_orders, cfg["digital_orders_per_month"]["thresholds"])
        sub_scores.append(orders_score)
        sub_weights.append(cfg["digital_orders_per_month"]["weight"])
        reasons.append(
            f"Avg Digital Orders: {avg_orders:.1f}/month (ONDC: {avg_ondc:.1f}, E-comm seller: {avg_ecom:.1f}) (Score: {orders_score:.0f})"
        )

        # 3. Online presence (GMB Rating)
        # Rating is static or dynamic
        rating = float(df["gmb_rating"].iloc[-1]) if "gmb_rating" in df.columns else 0.0
        gmb_score = threshold_score(rating, cfg["gmb_rating"]["thresholds"])
        sub_scores.append(gmb_score)
        sub_weights.append(cfg["gmb_rating"]["weight"])
        reasons.append(f"Google Business Profile Rating: {rating:.1f} (Score: {gmb_score:.0f})")
    else:
        # Conservative defaults if no marketplace / GMB presence found
        orders_score = float(cfg["digital_orders_per_month"]["thresholds"]["none"]["score"])
        sub_scores.append(orders_score)
        sub_weights.append(cfg["digital_orders_per_month"]["weight"])
        
        gmb_score = float(cfg["gmb_rating"]["thresholds"]["none"]["score"])
        sub_scores.append(gmb_score)
        sub_weights.append(cfg["gmb_rating"]["weight"])
        
        reasons.append(
            f"Digital Commerce & GBP: No e-commerce or Google Business Profile data (Orders Score: {orders_score:.0f}, GMB Score: {gmb_score:.0f})"
        )

    # Normalize weights of present sub-metrics
    total_w = sum(sub_weights)
    final_score = sum(s * (w / total_w) for s, w in zip(sub_scores, sub_weights))

    return DimensionScore(
        dimension="digital_adoption",
        score=final_score,
        reasons=reasons,
        data_available=True
    )
