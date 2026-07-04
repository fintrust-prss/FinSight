"""
MSME Financial Health Card — Scoring Engine.

Runs the 7-dimension rule-based scoring algorithm, aggregates using
bank weight profiles, and maps to decision tiers.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.scoring.config_loader import get_bank_profile_weights, get_decision_tiers
from app.scoring.types import DimensionScore, MSMEData
from app.scoring.ml_scorer import MLScorer
from app.scoring.dimensions import (
    score_revenue_cashflow,
    score_compliance_formalization,
    score_workforce_stability,
    score_operational_footprint,
    score_digital_adoption,
    score_credit_behavior,
    score_resilience_volatility,
)

logger = structlog.get_logger(__name__)


@dataclass
class ScoringResult:
    """Unified score output from the scoring engine."""
    msme_id: str
    overall_score: float
    tier: str
    action: str
    dimension_scores: dict[str, float]
    reasons: dict[str, list[str]]
    bank_profile: str
    as_of_date: date
    is_anomaly: bool = False
    shap_summary: dict[str, float] = field(default_factory=dict)
    model_version: str = "1.0.0"


class ScoringEngine:
    """
    Main orchestrator for alternate-data credit scoring.

    Loads weights from config and aggregates scores from the 7 dimensions.
    """

    def __init__(self) -> None:
        self._scorers = {
            "revenue_cashflow": score_revenue_cashflow,
            "compliance_formalization": score_compliance_formalization,
            "workforce_stability": score_workforce_stability,
            "operational_footprint": score_operational_footprint,
            "digital_adoption": score_digital_adoption,
            "credit_behavior": score_credit_behavior,
            "resilience_volatility": score_resilience_volatility,
        }
        self.ml_scorer = MLScorer()

    def score(
        self,
        data: MSMEData,
        bank_profile: str = "idbi",
        as_of_date: date | None = None,
        use_ml: bool = True,
    ) -> ScoringResult:
        """
        Compute financial health score and decision tier for an MSME.

        Args:
            data: Loaded Alternate Data and profile metrics.
            bank_profile: Active bank weighting profile (idbi, hdfc, axis, nbfc_generic).
            as_of_date: Score snapshot calculation date (defaults to today).
            use_ml: Toggle to blend Layer-2 ML scoring with Layer-1 rule-based score.

        Returns:
            ScoringResult containing overall score, tier, and dimension breakdown.
        """
        calc_date = as_of_date or date.today()
        logger.info("Computing health score", msme_id=data.msme_id, bank_profile=bank_profile, as_of_date=calc_date)

        # 1. Run all dimension scorers
        dim_results: dict[str, DimensionScore] = {}
        for name, scorer_fn in self._scorers.items():
            try:
                dim_results[name] = scorer_fn(data)
            except Exception as e:
                logger.error(f"Error scoring dimension {name}", exc_info=True)
                dim_results[name] = DimensionScore(
                    dimension=name,
                    score=20.0,  # conservative default penalty on crash
                    reasons=[f"Error calculating score: {str(e)}"],
                    data_available=False
                )

        # 2. Retrieve weights for the selected profile
        weights = get_bank_profile_weights(bank_profile)

        # 3. Aggregate overall rule-based score
        rule_score = 0.0
        dimension_scores: dict[str, float] = {}
        reasons: dict[str, list[str]] = {}

        for name, dim_res in dim_results.items():
            weight = weights.get(name, 0.0)
            rule_score += dim_res.score * weight
            dimension_scores[name] = round(dim_res.score, 2)
            reasons[name] = dim_res.reasons

        # Bound overall rule score to [0, 100]
        rule_score = max(0.0, min(100.0, rule_score))
        overall_score = rule_score

        # 4. Integrate Layer-2 ML scoring
        is_anomaly = False
        shap_summary: dict[str, float] = {}

        if use_ml and self.ml_scorer.is_loaded:
            # Predict default probability (PD)
            pd_val = self.ml_scorer.predict_default_prob(dimension_scores)
            
            # Blend score: 50% Rule-based score + 50% ML-derived score (100 * (1 - PD))
            ml_score = 100.0 * (1.0 - pd_val)
            overall_score = 0.5 * rule_score + 0.5 * ml_score
            
            # Anomaly detection
            is_anomaly = self.ml_scorer.detect_anomaly(dimension_scores)
            
            # SHAP Explainability
            shap_summary = self.ml_scorer.explain(dimension_scores)
        else:
            # Generate rule-based SHAP-like values for explainability fallback
            # Represents how much each dimension pulled the score up or down from a neutral baseline of 50.0
            for name, score in dimension_scores.items():
                weight = weights.get(name, 0.0)
                shap_summary[name] = (score - 50.0) * weight

        # 5. Map overall score to decision tier
        decision_tiers = get_decision_tiers()
        tier_label = "No-Go"
        tier_action = "Decline"

        # Tiers are sorted by min_score descending so first matches highest tier
        sorted_tiers = sorted(
            decision_tiers.items(),
            key=lambda kv: kv[1].get("min_score", 0),
            reverse=True,
        )

        for _key, tier_cfg in sorted_tiers:
            if overall_score >= tier_cfg["min_score"]:
                tier_label = tier_cfg["label"]
                tier_action = tier_cfg["action"]
                break

        return ScoringResult(
            msme_id=data.msme_id,
            overall_score=round(overall_score, 2),
            tier=tier_label,
            action=tier_action,
            dimension_scores=dimension_scores,
            reasons=reasons,
            bank_profile=bank_profile,
            as_of_date=calc_date,
            is_anomaly=is_anomaly,
            shap_summary=shap_summary,
        )
