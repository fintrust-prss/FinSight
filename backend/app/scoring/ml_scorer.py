"""
Layer-2 ML Scorer & Explainability Service.

Loads the trained XGBoost default predictor and Isolation Forest anomaly detector,
performs real-time predictions, computes SHAP values for explainability, and flags anomalies.
"""

from __future__ import annotations

import os
from pathlib import Path
import joblib
import numpy as np
import shap
import structlog

logger = structlog.get_logger(__name__)

# Feature columns in exact training order
FEATURE_ORDER = [
    "revenue_cashflow",
    "compliance_formalization",
    "workforce_stability",
    "operational_footprint",
    "digital_adoption",
    "credit_behavior",
    "resilience_volatility",
]


class MLScorer:
    """
    Wraps the trained machine learning models for inference, SHAP explanations,
    and anomaly detection.
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        if models_dir is None:
            models_dir = Path(__file__).parent / "models"
        
        self.xgb_model_path = models_dir / "xgb_model.joblib"
        self.iso_model_path = models_dir / "isolation_forest.joblib"
        
        self.xgb_model = None
        self.iso_model = None
        self.explainer = None
        self.is_loaded = False

        self.load_models()

    def load_models(self) -> None:
        """Load joblib serialized models and initialize SHAP explainer."""
        try:
            if self.xgb_model_path.exists() and self.iso_model_path.exists():
                self.xgb_model = joblib.load(self.xgb_model_path)
                self.iso_model = joblib.load(self.iso_model_path)
                
                # Pre-initialize SHAP TreeExplainer for fast on-the-fly calculations
                self.explainer = shap.TreeExplainer(self.xgb_model)
                self.is_loaded = True
                logger.info("ML Models successfully loaded for scoring")
            else:
                logger.warning(
                    "ML Model files not found. Scoring engine will fallback to Layer-1 only.",
                    xgb_path=str(self.xgb_model_path),
                    iso_path=str(self.iso_model_path),
                )
        except Exception as e:
            logger.error("Failed to load ML models, falling back to Layer-1", error=str(e))
            self.is_loaded = False

    def predict_default_prob(self, dimension_scores: dict[str, float]) -> float:
        """
        Predict probability of default (0.0 to 1.0) using XGBoost.
        """
        if not self.is_loaded or self.xgb_model is None:
            return 0.5  # Neutral default

        features = [dimension_scores.get(col, 50.0) for col in FEATURE_ORDER]
        X = np.array([features])
        probs = self.xgb_model.predict_proba(X)
        return float(probs[0][1])

    def detect_anomaly(self, dimension_scores: dict[str, float]) -> bool:
        """
        Run Isolation Forest to check if the feature vector represents a statistical anomaly.
        """
        if not self.is_loaded or self.iso_model is None:
            return False

        features = [dimension_scores.get(col, 50.0) for col in FEATURE_ORDER]
        X = np.array([features])
        prediction = self.iso_model.predict(X)[0]
        return bool(prediction == -1)

    def explain(self, dimension_scores: dict[str, float]) -> dict[str, float]:
        """
        Calculate SHAP values for the current prediction.
        Maps the raw contribution values back to the 7 dimensions.
        """
        if not self.is_loaded or self.explainer is None:
            return {col: 0.0 for col in FEATURE_ORDER}

        features = [dimension_scores.get(col, 50.0) for col in FEATURE_ORDER]
        X = np.array([features])
        
        # Calculate raw SHAP values (log-odds impact for binary classifier)
        shap_vals = self.explainer.shap_values(X)[0]
        
        # XGBoost SHAP output format check (binary classification can yield a 2D or 1D array)
        if isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) > 1:
            shap_vals = shap_vals[:, 1]  # positive class (default)
            
        # Map values to corresponding features
        explanation = {
            FEATURE_ORDER[i]: float(shap_vals[i]) for i in range(len(FEATURE_ORDER))
        }
        return explanation
