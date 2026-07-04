"""
Scoring Config Loader.

Loads config/scoring_weights.yaml once (cached) and provides typed accessors
for dimension weights and threshold configs.

Never import raw YAML values in dimension modules — always go through this loader
so the config path is swappable via environment variable (useful for A/B testing
different weight profiles).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Default config path — resolved relative to backend/ root
# ---------------------------------------------------------------------------
_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "scoring_weights.yaml"


@lru_cache(maxsize=1)
def load_scoring_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load and cache the scoring weights YAML.

    Args:
        config_path: Optional override path. If None, uses the path from
                     SCORING_WEIGHTS_PATH env var, or the default location.

    Returns:
        Parsed YAML as a nested dict.
    """
    path = Path(
        config_path
        or os.getenv("SCORING_WEIGHTS_PATH", str(_DEFAULT_CONFIG_PATH))
    )
    if not path.exists():
        raise FileNotFoundError(f"Scoring config not found at: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_bank_profile_weights(bank_profile: str) -> dict[str, float]:
    """
    Return the dimension weights for a specific bank profile.

    Args:
        bank_profile: One of "idbi", "hdfc", "axis", "nbfc_generic".

    Returns:
        Dict mapping dimension name → float weight (should sum to ~1.0).

    Raises:
        KeyError: If the bank_profile is not found in the YAML config.
    """
    config = load_scoring_config()
    profiles: dict[str, dict[str, float]] = config["bank_profiles"]
    if bank_profile not in profiles:
        available = list(profiles.keys())
        raise KeyError(
            f"Unknown bank_profile '{bank_profile}'. Available: {available}"
        )
    return profiles[bank_profile]


def get_dimension_config(dimension_name: str) -> dict[str, Any]:
    """
    Return the threshold/weight sub-config for a named dimension.

    Args:
        dimension_name: e.g. "revenue_cashflow", "workforce_stability".

    Returns:
        The nested config dict for that dimension.
    """
    config = load_scoring_config()
    return config[dimension_name]


def get_decision_tiers() -> dict[str, Any]:
    """Return the decision tier thresholds from config."""
    return load_scoring_config()["decision_tiers"]
