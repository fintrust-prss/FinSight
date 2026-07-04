"""
MSME Financial Health Card — Scoring Engine Package.

This package implements the two-layer scoring architecture from the spec (Section 6.2):

  Layer 1: Rule-based/expert scoring engine (this package)
    - 7 pure-function dimension scorers in scoring/dimensions/
    - Config-driven thresholds from config/scoring_weights.yaml
    - Per-institution bank_profile weight support (idbi, hdfc, axis, nbfc_generic)
    - Aggregator: produces overall 0-100 score + 4-tier decision label

  Layer 2: ML Risk Model (Phase 4 — scoring/models/)
    - Gradient Boosting trained on Layer-1 engineered features
    - SHAP explainability
    - Isolation Forest anomaly detection

Public interface:
    from app.scoring import ScoringEngine

    engine = ScoringEngine()
    result = engine.score(msme_data, bank_profile="idbi")
"""

from app.scoring.engine import ScoringEngine, ScoringResult

__all__ = ["ScoringEngine", "ScoringResult"]
