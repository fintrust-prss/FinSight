"""
Synthetic Data Loader Script.

Reads the generated Parquet files from data/synthetic/ and seeds
the Postgres database via the repository layer.

Usage:
    python -m app.db.loader --data-dir ../data/synthetic

Run this after:
    1. `docker compose up -d db`  (Postgres running)
    2. `alembic upgrade head`     (tables created)
    3. `python -m app.synthetic.generator` (Parquet files generated)
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date

import pandas as pd
import structlog

from app.db.session import async_session_factory
from app.db.repositories import AlternateDataRepository, MSMERepository, HealthScoreRepository
from app.logging_config import configure_logging

logger = structlog.get_logger(__name__)


def _parse_date(val: object) -> date:
    """Safely convert a value to a Python date object."""
    if isinstance(val, date):
        return val
    return pd.to_datetime(val).date()


async def load_data(data_dir: str) -> None:
    """Load all synthetic Parquet files into the database."""
    logger.info("loader_starting", data_dir=data_dir)

    async with async_session_factory() as session:
        msme_repo = MSMERepository(session)
        alt_repo = AlternateDataRepository(session)

        # ---- 1. MSME Profiles ----
        msme_path = os.path.join(data_dir, "msme.parquet")
        if os.path.exists(msme_path):
            df = pd.read_parquet(msme_path)
            for _, row in df.iterrows():
                data = row.to_dict()
                msme_id = data.pop("msme_id")
                await msme_repo.upsert(msme_id, {**data, "msme_id": msme_id})
            await session.commit()
            logger.info("msme_loaded", count=len(df))

        # ---- 2. GST Returns ----
        gst_path = os.path.join(data_dir, "gst_returns.parquet")
        if os.path.exists(gst_path):
            df = pd.read_parquet(gst_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["period"] = _parse_date(r["period"])
            count = await alt_repo.upsert_gst_returns(records)
            await session.commit()
            logger.info("gst_returns_loaded", new_rows=count, total=len(records))

        # ---- 3. UPI Transaction Summaries ----
        upi_path = os.path.join(data_dir, "upi_transaction_summaries.parquet")
        if os.path.exists(upi_path):
            df = pd.read_parquet(upi_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["month"] = _parse_date(r["month"])
            count = await alt_repo.upsert_upi_summaries(records)
            await session.commit()
            logger.info("upi_summaries_loaded", new_rows=count, total=len(records))

        # ---- 4. Bank Statement Summaries ----
        bank_path = os.path.join(data_dir, "bank_statement_summaries.parquet")
        if os.path.exists(bank_path):
            df = pd.read_parquet(bank_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["month"] = _parse_date(r["month"])
            count = await alt_repo.upsert_bank_summaries(records)
            await session.commit()
            logger.info("bank_summaries_loaded", new_rows=count, total=len(records))

        # ---- 5. EPFO Records ----
        epfo_path = os.path.join(data_dir, "epfo_records.parquet")
        if os.path.exists(epfo_path):
            df = pd.read_parquet(epfo_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["month"] = _parse_date(r["month"])
            count = await alt_repo.upsert_epfo_records(records)
            await session.commit()
            logger.info("epfo_records_loaded", new_rows=count, total=len(records))

        # ---- 6. Utility Consumption ----
        util_path = os.path.join(data_dir, "utility_consumption.parquet")
        if os.path.exists(util_path):
            df = pd.read_parquet(util_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["month"] = _parse_date(r["month"])
            count = await alt_repo.upsert_utility_records(records)
            await session.commit()
            logger.info("utility_records_loaded", new_rows=count, total=len(records))

        # ---- 7. Bureau Records ----
        bureau_path = os.path.join(data_dir, "bureau_records.parquet")
        if os.path.exists(bureau_path):
            df = pd.read_parquet(bureau_path)
            for _, row in df.iterrows():
                rec = row.to_dict()
                # Convert numpy nan to None
                if pd.isna(rec.get("score")):
                    rec["score"] = None
                await alt_repo.upsert_bureau_record(rec)
            await session.commit()
            logger.info("bureau_records_loaded", count=len(df))

        # ---- 8. Digital Footprints ----
        digital_path = os.path.join(data_dir, "digital_footprints.parquet")
        if os.path.exists(digital_path):
            df = pd.read_parquet(digital_path)
            records = df.to_dict(orient="records")
            for r in records:
                r["month"] = _parse_date(r["month"])
            count = await alt_repo.upsert_digital_footprints(records)
            await session.commit()
            logger.info("digital_footprints_loaded", new_rows=count, total=len(records))

    logger.info("loader_completed", data_dir=data_dir)
    print("\nSynthetic data loaded into database successfully.\n")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Synthetic Data DB Loader")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.getenv("SYNTHETIC_DATA_OUTPUT_DIR", "../data/synthetic"),
    )
    args = parser.parse_args()
    asyncio.run(load_data(args.data_dir))


if __name__ == "__main__":
    main()
