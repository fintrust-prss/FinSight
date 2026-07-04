"""
Shared types and utilities for the scoring engine.

All dimension scorers return a DimensionScore; the aggregator collects them
into a ScoringInput and produces a ScoringResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class DimensionScore:
    """
    Output of a single dimension scorer.

    Attributes:
        dimension: Canonical name matching the bank_profile weight key.
        score: 0–100 float (raw, before bank-profile weighting).
        reasons: List of human-readable strings explaining contributing factors.
                 Each string names the sub-signal and its value direction.
                 These are surfaced verbatim in the Health Card UI.
        data_available: False when required data was missing / insufficient.
                        Dimension is scored with a conservative penalty if False.
    """
    dimension: str
    score: float
    reasons: list[str]
    data_available: bool = True


@dataclass
class MSMEData:
    """
    All alternate-data inputs required by the scoring engine.

    Each field holds a pandas DataFrame with the schema from Section 7 of the spec.
    A field is None if the data source is not consented / unavailable — the
    engine handles missing data gracefully (conservative penalty, flagged in reasons).
    """
    msme_id: str
    sector: str
    sub_sector: str
    vintage_years: float
    udyam_registered: bool = True

    # Time-series tables (each a DataFrame with msme_id + month columns)
    gst_returns: pd.DataFrame | None = None           # Dim 1, 2, 4
    upi_summaries: pd.DataFrame | None = None         # Dim 1, 5
    bank_summaries: pd.DataFrame | None = None        # Dim 1, 6
    epfo_records: pd.DataFrame | None = None          # Dim 2, 3
    utility_records: pd.DataFrame | None = None       # Dim 4
    digital_footprints: pd.DataFrame | None = None    # Dim 5

    # Single-row tables
    bureau_score: int | None = None                   # Dim 6 (None = no file)
    bureau_enquiries_6m: int = 0                      # Dim 6
    bureau_has_file: bool = False                     # Dim 6


def threshold_score(value: float, thresholds: dict[str, Any], default: float = 20.0) -> float:
    """
    Map a continuous value to a discrete score using the YAML threshold config.

    The threshold config is a dict of named tiers, each with a ``score`` key
    and one of: ``min_*``, ``max_*``, ``above``, ``below``, ``value``.

    Tiers are checked in ascending order of their ``score`` (best match wins).

    Example YAML structure this function reads::

        excellent: { max_cov: 0.15, score: 90 }
        good:      { max_cov: 0.30, score: 70 }
        fair:      { max_cov: 0.50, score: 50 }
        poor:      { max_cov: 0.75, score: 25 }
        critical:  { above: 0.75,  score: 10 }

    Args:
        value: The numeric signal value (e.g. CoV = 0.22).
        thresholds: Parsed YAML dict of tier name → condition + score.
        default: Fallback score if no tier matches.

    Returns:
        Score (0–100 float).
    """
    # Filter out non-dict items (like disconnection_penalty or scale values)
    dict_thresholds = {k: v for k, v in thresholds.items() if isinstance(v, dict)}
    
    # Sort tiers by descending score so we match the best tier first
    sorted_tiers = sorted(
        dict_thresholds.items(),
        key=lambda kv: kv[1].get("score", 0),
        reverse=True,
    )
    for _tier_name, cfg in sorted_tiers:
        score = float(cfg.get("score", default))
        # Range match: min + max
        if "min_growth_pct" in cfg and "max_util" not in cfg:
            if value >= cfg["min_growth_pct"]:
                return score
        elif "max_cov" in cfg:
            if value <= cfg["max_cov"]:
                return score
        elif "max_hhi" in cfg:
            if value <= cfg["max_hhi"]:
                return score
        elif "max_corr" in cfg:
            if value <= cfg["max_corr"]:
                return score
        elif "min_rate" in cfg:
            if value >= cfg["min_rate"]:
                return score
        elif "min_ratio" in cfg:
            if value >= cfg["min_ratio"]:
                return score
        elif "min_inr" in cfg:
            if value >= cfg["min_inr"]:
                return score
        elif "min_rate" in cfg:
            if value >= cfg["min_rate"]:
                return score
        elif "min_score" in cfg:
            if value >= cfg["min_score"]:
                return score
        elif "min_orders" in cfg:
            if value >= cfg["min_orders"]:
                return score
        elif "min_rating" in cfg:
            if value >= cfg["min_rating"]:
                return score
        elif "min_corr" in cfg:
            if value >= cfg["min_corr"]:
                return score
        elif "min_regularity" in cfg:
            if value >= cfg["min_regularity"]:
                return score
        elif "min_growth_pct" in cfg and "max_util" in cfg:
            # Utility utilization range match
            util = value
            min_u = cfg.get("min_util", 0.0)
            max_u = cfg.get("max_util", float("inf"))
            if min_u <= util <= max_u:
                return score
        elif "min_util" in cfg:
            if value >= cfg["min_util"]:
                return score
        elif "max_enquiries" in cfg:
            if value <= cfg["max_enquiries"]:
                return score
        elif "max_rate" in cfg:
            if value <= cfg["max_rate"]:
                return score
        elif "below" in cfg:
            if value < cfg["below"]:
                return score
        elif "above" in cfg:
            if value > cfg["above"]:
                return score
        elif "value" in cfg and cfg["value"] == 0:
            if value == 0:
                return score
    return default


def compute_cov(series: pd.Series) -> float:
    """
    Compute the Coefficient of Variation (std / mean) for a numeric series.

    Returns 1.0 (max volatility) if the mean is zero to avoid division by zero.
    Vectorized — operates on the full series at once.
    """
    mean_val = series.mean()
    if mean_val == 0:
        return 1.0
    return float(series.std(ddof=1) / mean_val)


def compute_hhi(counts: pd.Series) -> float:
    """
    Compute the Herfindahl-Hirschman Index (concentration measure).

    HHI = Σ (share_i)^2 where share_i = count_i / total_count.
    Range: 0 (perfectly diversified) → 1 (pure monopoly).

    Args:
        counts: Series of counterparty transaction counts (one per counterparty).

    Returns:
        HHI float (0–1).
    """
    total = counts.sum()
    if total == 0:
        return 1.0  # No transactions = maximum concentration (conservative)
    shares = counts / total
    return float((shares ** 2).sum())


def growth_rate_pct(series: pd.Series) -> float:
    """
    Compute average month-over-month growth rate (%) across a time series.

    Uses vectorized pct_change(). Returns 0.0 if series has fewer than 2 points.
    """
    if len(series) < 2:
        return 0.0
    pct = series.pct_change().dropna()
    if pct.empty:
        return 0.0
    return float(pct.mean() * 100)
