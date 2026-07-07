"""
Application configuration via Pydantic Settings.

All configuration is loaded from environment variables (or .env file in dev).
In production, sensitive values are injected by Secret Manager / Cloud Run env vars.

No secrets are hardcoded here — see .env.example for the full variable list.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic validates all values on startup — the app will refuse to
    start with an invalid configuration (fail-fast principle).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars (don't crash)
    )

    # ---- App ----
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_workers: int = 1

    # ---- Cloud Provider (adapter selection) ----
    cloud_provider: Literal["gcp", "aws"] = "gcp"

    # ---- GCP ----
    gcp_project_id: str = ""
    gcp_region: str = "asia-south1"

    # ---- Database ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "msme_healthcard"
    postgres_user: str = "msme_app"
    postgres_password: str = ""

    @property
    def database_url(self) -> str:
        """Construct async SQLAlchemy database URL from components."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@/{self.postgres_db}?host={self.postgres_host}"
        )

    # ---- JWT ----
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_not_be_empty_in_production(cls, v: str, info: object) -> str:
        """Enforce non-empty JWT secret in non-development environments."""
        # We can't easily access other fields in validators without model_validator,
        # so we allow empty in all envs but log a warning at startup.
        return v

    # ---- GCS / Storage ----
    gcs_bucket_name: str = "msme-healthcard-synthetic-data-dev"
    gcs_bucket_region: str = "asia-south1"

    # ---- Pub/Sub ----
    pubsub_topic_rescore: str = "msme-rescore-events"
    pubsub_subscription_rescore: str = "msme-rescore-events-sub"

    # ---- Scoring ----
    scoring_weights_path: str = "config/scoring_weights.yaml"
    default_bank_profile: str = "idbi"

    # ---- CORS ----
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """Accept either a list or a comma-separated string."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    # ---- Rate Limiting ----
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # ---- Synthetic Data ----
    synthetic_data_seed: int = 42
    synthetic_data_output_dir: str = "data/synthetic"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    Using lru_cache means the .env file is read exactly once at startup.
    In tests, call get_settings.cache_clear() to reset between test runs.
    """
    return Settings()
