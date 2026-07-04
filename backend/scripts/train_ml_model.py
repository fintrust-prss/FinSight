"""
Phase 4 Model Training Script.

Generates training samples from the 2 personas' synthetic histories with noise
augmentation, computes Layer-1 dimension scores as features, generates synthetic
default labels, and trains/saves:
  1. XGBoost Classifier (Layer-2 Default Probability)
  2. Isolation Forest (Anomaly/Inconsistency Detector)
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from xgboost import XGBClassifier

from app.scoring.engine import ScoringEngine
from app.scoring.types import MSMEData


def load_parquet_data(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all Parquet files from synthetic data directory."""
    tables = [
        "msme",
        "gst_returns",
        "upi_transaction_summaries",
        "bank_statement_summaries",
        "epfo_records",
        "utility_consumption",
        "digital_footprints",
    ]
    data = {}
    for t in tables:
        path = data_dir / f"{t}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Missing synthetic Parquet table: {path}")
        data[t] = pd.read_parquet(path)
    return data


def build_msme_data_object(msme_row: pd.Series, tables: dict[str, pd.DataFrame]) -> MSMEData:
    """Build a typed MSMEData container for a given MSME row."""
    msme_id = msme_row["msme_id"]
    
    # Filter time-series DataFrames
    gst = tables["gst_returns"][tables["gst_returns"]["msme_id"] == msme_id]
    upi = tables["upi_transaction_summaries"][tables["upi_transaction_summaries"]["msme_id"] == msme_id]
    bank = tables["bank_statement_summaries"][tables["bank_statement_summaries"]["msme_id"] == msme_id]
    epfo = tables["epfo_records"][tables["epfo_records"]["msme_id"] == msme_id]
    util = tables["utility_consumption"][tables["utility_consumption"]["msme_id"] == msme_id]
    dig = tables["digital_footprints"][tables["digital_footprints"]["msme_id"] == msme_id]

    # Bureau record is 1-to-1 with msme_id
    # We can fetch enquiries and score or mock them if not present
    bureau_records = pd.read_parquet(data_dir_path / "bureau_records.parquet")
    b_rec = bureau_records[bureau_records["msme_id"] == msme_id]
    
    bureau_score = None
    bureau_enquiries = 0
    has_file = False
    
    if not b_rec.empty:
        row = b_rec.iloc[0]
        has_file = bool(row["has_file"])
        bureau_enquiries = int(row["enquiries_last_6m"])
        bureau_score = int(row["score"]) if pd.notna(row["score"]) else None

    return MSMEData(
        msme_id=msme_id,
        sector=msme_row["sector"],
        sub_sector=msme_row["sub_sector"],
        vintage_years=float(msme_row["vintage_years"]),
        udyam_registered=True,
        gst_returns=gst,
        upi_summaries=upi,
        bank_summaries=bank,
        epfo_records=epfo,
        utility_records=util,
        digital_footprints=dig,
        bureau_has_file=has_file,
        bureau_score=bureau_score,
        bureau_enquiries_6m=bureau_enquiries,
    )


def generate_ml_training_set(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate feature matrix and target labels.
    Uses the 2 personas' baseline dimension scores, adding noise jitter
    to simulate a balanced dataset of 1000 observations.
    """
    tables = load_parquet_data(data_dir)
    msmes = tables["msme"]
    engine = ScoringEngine()

    base_features = []
    
    # 1. Compute baseline features for both personas
    for _, msme_row in msmes.iterrows():
        msme_id = msme_row["msme_id"]
        msme_data = build_msme_data_object(msme_row, tables)
        
        # Calculate dimension scores using ScoringEngine
        res = engine.score(msme_data, bank_profile="idbi")
        feats = [
            res.dimension_scores["revenue_cashflow"],
            res.dimension_scores["compliance_formalization"],
            res.dimension_scores["workforce_stability"],
            res.dimension_scores["operational_footprint"],
            res.dimension_scores["digital_adoption"],
            res.dimension_scores["credit_behavior"],
            res.dimension_scores["resilience_volatility"],
        ]
        base_features.append(feats)

    # 2. Augment dataset using random seed
    np.random.seed(42)
    augmented_features = []
    
    # Generate 1000 samples
    for _ in range(1000):
        # Randomly choose one of the baseline profiles (Sakhi or Annapurna)
        base = base_features[np.random.choice(len(base_features))]
        # Add normal noise jitter (mean=0, std=8.0) bounded between 0 and 100
        jittered = [max(0.0, min(100.0, float(val + np.random.normal(0, 8.0)))) for val in base]
        augmented_features.append(jittered)

    X = np.array(augmented_features)

    # 3. Generate synthetic labels: Probability of Default (PD)
    # Average score across dimensions
    mean_scores = X.mean(axis=1)
    
    # Sigmoid function centered around score 55
    # If mean score is < 35, high probability of default. If > 75, low probability.
    logits = (55.0 - mean_scores) / 10.0
    probs = 1.0 / (1.0 + np.exp(-logits))
    
    # Binary classification labels
    y = np.where(probs + np.random.normal(0, 0.05, size=len(probs)) > 0.5, 1, 0)
    
    return X, y


if __name__ == "__main__":
    # Setup paths
    workspace_root = Path(__file__).parent.parent.parent
    data_dir_path = workspace_root / "data" / "synthetic"
    models_dir = Path(__file__).parent.parent / "app" / "scoring" / "models"
    
    # Create models directory if it doesn't exist
    models_dir.mkdir(parents=True, exist_ok=True)

    print("Generating training dataset from synthetic Parquet files...")
    X, y = generate_ml_training_set(data_dir_path)

    # Train XGBoost Classifier
    print("Training XGBoost Classifier...")
    xgb = XGBClassifier(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss"
    )
    xgb.fit(X, y)

    # Train Isolation Forest (Anomaly Detector)
    # Contamination = 5% anomalies expected
    print("Training Isolation Forest Anomaly Detector...")
    iso = IsolationForest(
        contamination=0.05,
        random_state=42
    )
    iso.fit(X)

    # Save models
    xgb_path = models_dir / "xgb_model.joblib"
    iso_path = models_dir / "isolation_forest.joblib"
    
    joblib.dump(xgb, xgb_path)
    joblib.dump(iso, iso_path)

    print(f"Successfully trained and saved model artifacts:")
    print(f"  - XGBoost Model: {xgb_path}")
    print(f"  - Isolation Forest: {iso_path}")
