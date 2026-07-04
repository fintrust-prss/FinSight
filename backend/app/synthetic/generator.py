"""
Deterministic, Seeded, Config-Driven Synthetic MSME Data Generator.

This module generates realistic 18–24 months of historical alternate data for:
  - GST returns (turnover, tax, filing delays)
  - UPI transaction summaries (inflows, outflows, counterparties)
  - Account Aggregator bank statement summaries (average balances, bounces, overdraft)
  - EPFO records (headcount, wage bills, contribution gaps)
  - Utility consumption (electricity units, loads, delays, disconnections)
  - Credit Bureau records (thin file or score, enquiries)
  - Digital footprint (ONDC, e-commerce, GMB ratings)

All data is generated deterministically from seeded random distributions
defined in persona YAML files.
"""

from __future__ import annotations

import argparse
import os
import random
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import yaml
import structlog
from dateutil.relativedelta import relativedelta

from app.logging_config import configure_logging

from app.models.schemas import (
    AABankStatementSummarySchema,
    BureauRecordSchema,
    DigitalFootprintSchema,
    EPFORecordSchema,
    GSTReturnSchema,
    MSMESchema,
    UPITransactionSummarySchema,
    UtilityConsumptionSchema,
)

logger = structlog.get_logger(__name__)


class SyntheticDataGenerator:
    """
    Core synthetic data generator class.

    Attributes:
        config: Loaded persona configuration dict.
        ref_date: Starting end date for generation, moving backwards.
    """

    def __init__(self, config_path: str, ref_date: date | None = None) -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Set default reference date to June 2026 (spec benchmark time)
        self.ref_date = ref_date or date(2026, 6, 1)

        # Set seed for reproducibility
        self.seed = self.config.get("seed", 42)
        random.seed(self.seed)
        np.random.seed(self.seed)

    def generate(self) -> dict[str, pd.DataFrame]:
        """
        Generate all entity tables for the configured persona.

        Returns:
            Dictionary mapping table/schema name to pandas DataFrame.
        """
        # Reset seeds at generator execution time to ensure absolute reproducibility and isolation
        random.seed(self.seed)
        np.random.seed(self.seed)

        msme_id = self.config["msme_id"]
        history_months = self.config.get("history_months", 24)

        logger.info(
            "generating_synthetic_data",
            msme_id=msme_id,
            persona=self.config["legal_name"],
            months=history_months,
            seed=self.seed,
        )

        # 1. Generate core MSME profile
        msme_profile = self._generate_msme_profile()

        # Generate month list going back from ref_date
        month_list = []
        for i in range(history_months):
            # Calculate date for the 1st of each month
            m_date = self.ref_date - relativedelta(months=i)
            # Normalize to 1st day of month
            month_list.append(date(m_date.year, m_date.month, 1))

        # Reverse so dates are chronologically ascending
        month_list.reverse()

        # 2. Generate alternate datasets
        gst_returns = self._generate_gst_returns(month_list)
        upi_summaries = self._generate_upi_summaries(month_list, gst_returns)
        bank_summaries = self._generate_bank_summaries(month_list, gst_returns, upi_summaries)
        epfo_records = self._generate_epfo_records(month_list)
        utility_consumption = self._generate_utility_consumption(month_list)
        bureau_record = self._generate_bureau_record()
        digital_footprint = self._generate_digital_footprint(month_list)

        return {
            "msme": pd.DataFrame([msme_profile]),
            "gst_returns": pd.DataFrame(gst_returns),
            "upi_transaction_summaries": pd.DataFrame(upi_summaries),
            "bank_statement_summaries": pd.DataFrame(bank_summaries),
            "epfo_records": pd.DataFrame(epfo_records),
            "utility_consumption": pd.DataFrame(utility_consumption),
            "bureau_records": pd.DataFrame([bureau_record]),
            "digital_footprints": pd.DataFrame(digital_footprint),
        }

    def _generate_msme_profile(self) -> dict[str, Any]:
        profile = {
            "msme_id": self.config["msme_id"],
            "legal_name": self.config["legal_name"],
            "udyam_number": self.config["udyam_number"],
            "sector": self.config["sector"],
            "sub_sector": self.config["sub_sector"],
            "vintage_years": self.config["vintage_years"],
            "state": self.config["state"],
            "registration_type": self.config["registration_type"],
        }
        # Validate schema
        MSMESchema(**profile)
        return profile

    def _generate_gst_returns(self, month_list: list[date]) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        fin = self.config["financials"]
        comp = self.config["compliance"]

        base_turnover = fin["base_turnover"]
        growth_trend = fin["growth_trend_mom"]
        peak_month = fin["seasonality_peak_month"]
        amplitude = fin["seasonality_amplitude"]
        volatility = fin["cashflow_volatility_std"]

        for idx, month in enumerate(month_list):
            # 1. Base trend growth
            trend_turnover = base_turnover * ((1 + growth_trend) ** idx)

            # 2. Seasonality (festive spike, e.g. Diwali)
            # Model as Gaussian-like peak around peak_month (with wrap-around for calendar months)
            month_dist = min(abs(month.month - peak_month), 12 - abs(month.month - peak_month))
            seasonality_multiplier = 1.0 + amplitude * np.exp(-(month_dist**2) / 2.0)

            # 3. Volatility noise
            noise = np.random.normal(0, volatility)
            turnover = max(10000.0, trend_turnover * seasonality_multiplier * (1 + noise))

            # 4. Tax calculated at 12% average GST rate
            tax_rate = 0.12
            tax_paid = turnover * tax_rate

            # 5. Filing delays
            filed_on_time = np.random.random() >= comp["gst_filing_delay_prob"]
            late_days = 0 if filed_on_time else int(np.random.geometric(0.1)) # mean 10 days delay

            record = {
                "msme_id": msme_id,
                "period": month,
                "return_type": "GSTR-3B",
                "turnover": round(float(turnover), 2),
                "tax_paid": round(float(tax_paid), 2),
                "filed_on_time": filed_on_time,
                "late_days": late_days,
            }
            # Schema validation
            GSTReturnSchema(**record)
            records.append(record)

        return records

    def _generate_upi_summaries(self, month_list: list[date], gst_returns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        fin = self.config["financials"]

        upi_ratio = fin["upi_ratio"]
        upi_p2m_ratio = fin["upi_p2m_ratio"]
        counterparty_count = fin["upi_counterparty_count"]

        for idx, month in enumerate(month_list):
            turnover = gst_returns[idx]["turnover"]

            # Calculate UPI values
            upi_total_value = turnover * upi_ratio
            p2m_value = upi_total_value * upi_p2m_ratio
            p2p_value = upi_total_value * (1.0 - upi_p2m_ratio)

            # Count of transactions matches value logically (average transaction size ~1,200 INR)
            avg_txn_size = 1200.0
            p2m_count = max(1, int(p2m_value / avg_txn_size))
            p2p_count = max(0, int(p2p_value / avg_txn_size))

            # Variance in counterparties depending on business
            # If diverse, more counterparties; if concentration risk, very few
            unique_parties = max(1, int(np.random.normal(counterparty_count, counterparty_count * 0.15)))

            record = {
                "msme_id": msme_id,
                "month": month,
                "p2m_count": p2m_count,
                "p2m_value": round(float(p2m_value), 2),
                "p2p_count": p2p_count,
                "p2p_value": round(float(p2p_value), 2),
                "unique_counterparties": unique_parties,
            }
            # Schema validation
            UPITransactionSummarySchema(**record)
            records.append(record)

        return records

    def _generate_bank_summaries(
        self,
        month_list: list[date],
        gst_returns: list[dict[str, Any]],
        upi_summaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        fin = self.config["financials"]

        bank_inflow_ratio = fin["bank_inflow_ratio"]
        avg_balance_ratio = fin["avg_balance_ratio"]
        bounce_prob = fin["cheque_bounce_probability"]
        max_overdraft_days = fin["overdraft_days"]

        for idx, month in enumerate(month_list):
            turnover = gst_returns[idx]["turnover"]

            # Inflow tracks GST turnover with some cash offset
            inflow = turnover * bank_inflow_ratio * np.random.normal(1.0, 0.02)
            # Outflow matches inflow closely but fluctuates slightly (e.g. inventory seasons)
            outflow_ratio = np.random.normal(0.97, 0.05)
            outflow = inflow * outflow_ratio

            # Average daily balance matches average daily cash flows
            avg_balance = turnover * avg_balance_ratio * np.random.normal(1.0, 0.08)
            avg_balance = max(2000.0, avg_balance) # minimum buffer

            # Bounces
            bounce_count = 0
            if bounce_prob > 0:
                # Geometric/Poisson distribution for bounces if persona has bounce probability
                bounce_count = np.random.poisson(bounce_prob * 10)

            # Overdraft usage
            overdraft_days = 0
            if max_overdraft_days > 0:
                # Bounded daily overdraft duration based on cash flow adequacy
                if outflow_ratio > 1.02:
                    overdraft_days = min(30, int(np.random.normal(max_overdraft_days * 1.5, 3)))
                else:
                    overdraft_days = min(30, int(np.random.normal(max_overdraft_days, 2)))
                overdraft_days = max(0, overdraft_days)

            record = {
                "msme_id": msme_id,
                "month": month,
                "avg_balance": round(float(avg_balance), 2),
                "inflow": round(float(inflow), 2),
                "outflow": round(float(outflow), 2),
                "bounce_count": int(bounce_count),
                "overdraft_days": int(overdraft_days),
            }
            # Schema validation
            AABankStatementSummarySchema(**record)
            records.append(record)

        return records

    def _generate_epfo_records(self, month_list: list[date]) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        comp = self.config["compliance"]

        headcount_base = comp["epfo_headcount_base"]
        headcount_growth = comp["epfo_headcount_growth_mom"]
        wage_bill_per_employee = comp["wage_bill_per_employee"]
        missed_months = comp["epfo_missed_months"]

        current_headcount = headcount_base

        for idx, month in enumerate(month_list):
            # Headcount growth MoM
            if headcount_growth > 0:
                current_headcount = headcount_base * ((1 + headcount_growth) ** idx)

            employee_count = max(1, int(round(current_headcount)))

            # Total monthly wage bill + small random variance
            wage_bill = employee_count * wage_bill_per_employee * np.random.normal(1.0, 0.01)

            # Check if this month is configured as a missed contribution
            contribution_paid = True
            if idx in missed_months:
                contribution_paid = False

            record = {
                "msme_id": msme_id,
                "month": month,
                "employee_count": employee_count,
                "wage_bill": round(float(wage_bill), 2),
                "contribution_paid": contribution_paid,
            }
            # Schema validation
            EPFORecordSchema(**record)
            records.append(record)

        return records

    def _generate_utility_consumption(self, month_list: list[date]) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        util = self.config["utility"]

        utility_type = util["utility_type"]
        sanctioned_load = util["sanctioned_load_kwh"]
        base_units = util["base_units_consumed"]
        delay_prob = util["payment_delay_days_prob"]
        disconnections = util["disconnection_events"]

        for idx, month in enumerate(month_list):
            # Model utility units consumed.
            # Manufacturing utility is correlated with business volume.
            # Add seasonal variation (e.g. heating/cooling and peak festive production)
            seasonality = 1.0 + 0.15 * np.sin(2 * np.pi * month.month / 12.0)
            units = base_units * seasonality * np.random.normal(1.0, 0.05)

            # Payment delays
            payment_delay = 0
            if np.random.random() < delay_prob:
                payment_delay = int(np.random.geometric(0.08)) # mean 12 days delay

            # Adjust units consumed to 0 if a disconnection event occurred
            if idx in disconnections:
                units = 0.0
                payment_delay = 45 # severe delinquency

            record = {
                "msme_id": msme_id,
                "month": month,
                "utility_type": utility_type,
                "units_consumed": round(float(units), 2),
                "sanctioned_load": float(sanctioned_load),
                "payment_delay_days": payment_delay,
            }
            # Schema validation
            UtilityConsumptionSchema(**record)
            records.append(record)

        return records

    def _generate_bureau_record(self) -> dict[str, Any]:
        bur = self.config["bureau"]
        record = {
            "msme_id": self.config["msme_id"],
            "has_file": bur["has_file"],
            "score": bur["score"],
            "enquiries_last_6m": bur["enquiries_last_6m"],
            "existing_loans": bur["existing_loans"],
        }
        # Schema validation
        BureauRecordSchema(**record)
        return record

    def _generate_digital_footprint(self, month_list: list[date]) -> list[dict[str, Any]]:
        records = []
        msme_id = self.config["msme_id"]
        dig = self.config["digital"]

        ondc_base = dig["ondc_orders_base"]
        ecom_base = dig["ecommerce_orders_base"]
        gmb_rating = dig["gmb_rating"]
        review_base = dig["gmb_review_count_base"]

        for idx, month in enumerate(month_list):
            # Growth in digital footprint over time
            growth = 1.0 + 0.02 * idx # 2% growth monthly
            ondc_orders = int(np.random.poisson(ondc_base * growth))
            ecommerce_orders = int(np.random.poisson(ecom_base * growth))

            # Cumulative review count increases
            review_count = int(review_base + np.random.normal(5 * idx, 2))
            review_count = max(review_base, review_count)

            record = {
                "msme_id": msme_id,
                "month": month,
                "ondc_orders": ondc_orders,
                "ecommerce_orders": ecommerce_orders,
                "gmb_rating": float(gmb_rating),
                "gmb_review_count": review_count,
            }
            # Schema validation
            DigitalFootprintSchema(**record)
            records.append(record)

        return records


def main() -> None:
    """Execute generators for all personas and write outcomes to output directory."""
    parser = argparse.ArgumentParser(description="Synthetic MSME Data Generator")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.getenv("SYNTHETIC_DATA_OUTPUT_DIR", "data/synthetic"),
        help="Target folder for Parquet/CSV files",
    )
    args = parser.parse_args()

    # Locate persona config files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    personas_dir = os.path.join(base_dir, "synthetic", "personas")

    if not os.path.exists(personas_dir):
        logger.error("personas_directory_missing", path=personas_dir)
        return

    os.makedirs(args.output_dir, exist_ok=True)

    # Dictionary containing accumulated lists of DataFrames for export
    full_dataset: dict[str, list[pd.DataFrame]] = {
        "msme": [],
        "gst_returns": [],
        "upi_transaction_summaries": [],
        "bank_statement_summaries": [],
        "epfo_records": [],
        "utility_consumption": [],
        "bureau_records": [],
        "digital_footprints": [],
    }

    # Generate data for all persona files in the directory
    for file_name in os.listdir(personas_dir):
        if not file_name.endswith(".yaml"):
            continue

        config_path = os.path.join(personas_dir, file_name)
        generator = SyntheticDataGenerator(config_path)
        persona_dfs = generator.generate()

        for table, df in persona_dfs.items():
            full_dataset[table].append(df)

    # Merge individual dataframes and write to output folder
    for table, df_list in full_dataset.items():
        if not df_list:
            continue

        # Concatenate records from all personas
        merged_df = pd.concat(df_list, ignore_index=True)

        # Write Parquet and CSV versions
        parquet_path = os.path.join(args.output_dir, f"{table}.parquet")
        csv_path = os.path.join(args.output_dir, f"{table}.csv")

        merged_df.to_parquet(parquet_path, index=False)
        merged_df.to_csv(csv_path, index=False)

        logger.info(
            "dataset_written",
            table=table,
            rows=len(merged_df),
            parquet=parquet_path,
            csv=csv_path,
        )

    print("\nDeterministic seeded synthetic data generation completed successfully.\n")


if __name__ == "__main__":
    configure_logging()
    main()
