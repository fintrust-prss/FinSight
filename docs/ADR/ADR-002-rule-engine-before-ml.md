# ADR-002: Rule Engine First, ML Second (Two-Layer Scoring Design)

**Status:** Accepted  
**Date:** 2026-07-04  
**Author:** Hackathon Build Team  

---

## Context

The IDBI Deputy Manager explicitly asked for **explainable** credit decisions — not a black box. The spec requires a 4-tier label (Disciplined / Moderately Disciplined / Non-Disciplined / No-Go) that a bank examiner can audit. There are two broad scoring approaches:

1. **Pure ML model**: Train an XGBoost/LightGBM model directly on alternate-data features → high predictive power, but hard to explain to a regulator.
2. **Pure rule engine**: Expert-designed thresholds → fully transparent, but rigid and potentially biased toward the designer's priors.
3. **Two-layer hybrid (our choice)**: Rule engine first (Layer 1) → ML model trained *on top of* Layer-1 features (Layer 2).

---

## Decision

**Implement Layer 1 (Rule Engine) completely before Layer 2 (ML)**, and keep both independently operable via a feature flag.

**Layer 1 — Deterministic/Expert Rule Engine:**
- Computes 0–100 scores for each of the 7 dimensions using domain thresholds
- All thresholds live in `config/scoring_weights.yaml` — never hardcoded
- Returns a human-readable "reason string" per contributing factor
- This is the **explainability anchor** — SHAP maps back to these dimensions

**Layer 2 — Gradient Boosting ML Model:**
- Trained on Layer-1 engineered features as inputs
- Labels from a documented, seeded synthetic default simulation (clearly marked as synthetic)
- Outputs: probability of default + tier recommendation
- Adds SHAP-based per-prediction explanations
- Adds Isolation Forest anomaly detection

**Feature flag:** `SCORING_MODE=rule_engine_only | blended` controls which layer is active.

---

## Consequences

**Positive:**
- **Regulator/bank examiner auditability:** Layer 1 produces an exact, traceable explanation for every score — which factors drove it, which thresholds were crossed.
- **Incremental development:** Phase 3 (Layer 1) is fully functional and demo-able before Phase 4 (Layer 2) is built. The hackathon is protected against ML training/debugging time overruns.
- **Ground truth for ML:** By training Layer 2 on Layer-1 features, the ML model is forced to learn from the same signal space — it can refine the weights but cannot contradict the domain logic entirely.
- **Real-data readiness:** When IDBI provides real loan outcome data, Layer 2 can be retrained without touching Layer 1 or any business logic.
- **Fairness monitoring:** Layer 1's dimension-level breakdown makes it easy to spot if a dimension is systematically penalizing a demographic (e.g., geography-correlated utility patterns).

**Negative:**
- Two layers to maintain instead of one.
- Layer 1 weight calibration is manual (YAML) — requires domain expert input for production deployment.
- Feature flag adds a configuration dimension that must be documented and tested.

**Neutral:**
- SHAP explanations computed against Layer-2 model are mapped back to Layer-1 dimensions — this requires a translation step but produces more human-interpretable explanations than raw feature importances.

---

## Alternatives Considered

1. **ML-only (end-to-end):** Rejected — fails the explainability requirement; regulators and bank examiners cannot accept a black-box score.
2. **Rule engine only (no ML):** Rejected — loses the ability to learn non-linear interactions between dimensions (e.g., high UPI volume + missed EPFO is riskier than either alone).
3. **Logistic regression as Layer 2:** Considered — more interpretable than GBM, but lower predictive power. Decision: use GBM + SHAP, which matches GBM's power with logistic regression's interpretability.

---

## Reference

- Spec Section 6.2: Two-Layer Scoring Design
- Spec Section 6.1: Seven Scoring Dimensions
- Spec Section 9: Explainability requirement
- [`config/scoring_weights.yaml`](../../backend/config/scoring_weights.yaml)
- Phase 3 (Rule Engine): `backend/app/scoring/dimensions/`
- Phase 4 (ML Layer): `backend/app/scoring/models/`
