"""
Run Alembic migrations and load synthetic Parquet data into Postgres.

Usage (from repo root):
  python backend/scripts/seed_db.py --data-dir data/synthetic

The script will:
  1. Read application settings (env/.env) via `app.config.get_settings()`
  2. Optionally run `alembic upgrade head` using the repo's Alembic config
  3. Call the existing `app.db.loader.load_data` to ingest Parquet files

Note: Ensure your Cloud SQL Proxy (or DB host) is running and env vars
      (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)
      are set so `get_settings()` can construct the correct DB URL.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import sys

from app.config import get_settings
from app.logging_config import configure_logging


def run_alembic_upgrade(backend_dir: Path, settings) -> None:
    """Programmatically run `alembic upgrade head` using the project's config."""
    from alembic.config import Config
    from alembic import command

    alembic_ini = backend_dir / "alembic.ini"
    if not alembic_ini.exists():
        raise SystemExit(f"alembic.ini not found at {alembic_ini}")

    cfg = Config(str(alembic_ini))
    # Ensure alembic uses the same DB URL as the app
    # Escape percent signs to avoid ConfigParser interpolation errors
    # Log masked URL for debugging (don't print the raw password)
    raw_url = settings.database_url
    try:
        # naive masking of password segment
        masked = raw_url.split("//", 1)[1]
        userinfo, hostpart = masked.split("@", 1)
        user, pwd = userinfo.split(":", 1)
        masked_url = f"{user}:<redacted>@{hostpart}"
    except Exception:
        masked_url = "<could not mask>"
    logging.info("Alembic will use DB URL: %s", masked_url)

    # Escape % for ConfigParser
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace('%', '%%'))
    # Make script_location absolute so Alembic can locate the migrations
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    logging.info("Running alembic upgrade head")
    command.upgrade(cfg, "head")


async def run_loader(data_dir: str) -> None:
    """Call the existing loader to push Parquet files into the DB."""
    from app.db.loader import load_data

    await load_data(data_dir)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Run migrations and seed synthetic data")
    parser.add_argument("--data-dir", default=str(Path("data") / "synthetic"), help="Directory containing parquet files")
    parser.add_argument("--no-migrate", action="store_true", help="Skip running alembic migrations")
    args = parser.parse_args()

    # Determine backend directory (this file is under backend/scripts)
    backend_dir = Path(__file__).resolve().parents[1]

    settings = get_settings()

    # Run migrations unless disabled
    if not args.no_migrate:
        try:
            run_alembic_upgrade(backend_dir, settings)
        except Exception as exc:
            logging.exception("Alembic migration failed")
            raise SystemExit("Migration failed — aborting") from exc

    # Load data
    data_dir = args.data_dir
    logging.info("Loading synthetic data from %s", data_dir)
    try:
        asyncio.run(run_loader(data_dir))
    except Exception as exc:
        logging.exception("Data loader failed")
        raise SystemExit("Data load failed") from exc

    logging.info("Seeding completed successfully")


if __name__ == "__main__":
    main()
