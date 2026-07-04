"""
Unit Tests for the Synthetic MSME Data Generator.
"""

from __future__ import annotations

import os
from datetime import date
import pytest
import pandas as pd

from app.synthetic.generator import SyntheticDataGenerator


def _get_persona_path(persona_name: str) -> str:
    """Resolve full path to persona configuration."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "app", "synthetic", "personas", f"{persona_name}.yaml")


class TestSyntheticDataGenerator:
    """Test suite for deterministic synthetic data generation."""

    def test_reproducibility(self) -> None:
        """Verify that running generator twice with the same config path yields identical dataframes."""
        path = _get_persona_path("sakhi_mahila")
        gen1 = SyntheticDataGenerator(path, ref_date=date(2026, 6, 1))
        gen2 = SyntheticDataGenerator(path, ref_date=date(2026, 6, 1))

        res1 = gen1.generate()
        res2 = gen2.generate()

        for table in res1:
            pd.testing.assert_frame_equal(res1[table], res2[table])

    def test_referential_integrity(self) -> None:
        """Verify that all generated child tables correctly link to the parent MSME via msme_id."""
        for name in ["sakhi_mahila", "annapurna_fresh"]:
            path = _get_persona_path(name)
            gen = SyntheticDataGenerator(path)
            res = gen.generate()

            msme_id = res["msme"].iloc[0]["msme_id"]

            for table_name, df in res.items():
                if table_name in ["msme", "bureau_records"]:
                    continue
                # Each row in other tables must match msme_id
                assert (df["msme_id"] == msme_id).all(), f"MSME ID mismatch in {table_name}"

    def test_date_monotonicity_and_alignment(self) -> None:
        """Verify that all generated time-series data is ordered chronologically."""
        for name in ["sakhi_mahila", "annapurna_fresh"]:
            path = _get_persona_path(name)
            gen = SyntheticDataGenerator(path)
            res = gen.generate()

            for table_name in [
                "gst_returns",
                "upi_transaction_summaries",
                "bank_statement_summaries",
                "epfo_records",
                "utility_consumption",
                "digital_footprints",
            ]:
                df = res[table_name]
                date_col = "period" if table_name == "gst_returns" else "month"

                # Check that dates are strictly increasing
                dates = pd.to_datetime(df[date_col])
                assert dates.is_monotonic_increasing, f"Dates not monotonic in {table_name}"

                # Ensure length is exactly matching the configuration
                history_months = gen.config["history_months"]
                assert len(df) == history_months, f"Length mismatch in {table_name}"

    def test_non_negative_invariants(self) -> None:
        """Verify that monetary amounts, counts, and metrics are non-negative."""
        for name in ["sakhi_mahila", "annapurna_fresh"]:
            path = _get_persona_path(name)
            gen = SyntheticDataGenerator(path)
            res = gen.generate()

            # GST
            assert (res["gst_returns"]["turnover"] >= 0).all()
            assert (res["gst_returns"]["tax_paid"] >= 0).all()
            assert (res["gst_returns"]["late_days"] >= 0).all()

            # UPI
            assert (res["upi_transaction_summaries"]["p2m_count"] >= 0).all()
            assert (res["upi_transaction_summaries"]["p2p_count"] >= 0).all()
            assert (res["upi_transaction_summaries"]["p2m_value"] >= 0).all()
            assert (res["upi_transaction_summaries"]["p2p_value"] >= 0).all()
            assert (res["upi_transaction_summaries"]["unique_counterparties"] >= 0).all()

            # Bank
            assert (res["bank_statement_summaries"]["avg_balance"] >= 0).all()
            assert (res["bank_statement_summaries"]["inflow"] >= 0).all()
            assert (res["bank_statement_summaries"]["outflow"] >= 0).all()
            assert (res["bank_statement_summaries"]["bounce_count"] >= 0).all()
            assert (res["bank_statement_summaries"]["overdraft_days"] >= 0).all()

            # EPFO
            assert (res["epfo_records"]["employee_count"] >= 1).all()
            assert (res["epfo_records"]["wage_bill"] >= 0).all()

            # Utility
            assert (res["utility_consumption"]["units_consumed"] >= 0).all()
            assert (res["utility_consumption"]["payment_delay_days"] >= 0).all()

    def test_persona_specific_characteristics(self) -> None:
        """Verify that the generated profiles represent the distinct configurations for both personas."""
        # 1. Sakhi Mahila Udyog (disciplined cooperative)
        sakhi_gen = SyntheticDataGenerator(_get_persona_path("sakhi_mahila"))
        sakhi = sakhi_gen.generate()

        assert bool(sakhi["bureau_records"].iloc[0]["has_file"]) is True
        assert sakhi["bureau_records"].iloc[0]["score"] > 700
        # Should have zero cheque bounces
        assert (sakhi["bank_statement_summaries"]["bounce_count"] == 0).all()
        # Should have zero missed EPFO payments
        assert (sakhi["epfo_records"]["contribution_paid"] == True).all()

        # 2. Annapurna Fresh Snacks (New-to-Bank, inconsistent)
        anna_gen = SyntheticDataGenerator(_get_persona_path("annapurna_fresh"))
        anna = anna_gen.generate()

        assert bool(anna["bureau_records"].iloc[0]["has_file"]) is False
        assert anna["bureau_records"].iloc[0]["score"] is None or pd.isna(anna["bureau_records"].iloc[0]["score"])
        # Should have cheque bounces
        assert (anna["bank_statement_summaries"]["bounce_count"] > 0).any()
        # Should have exactly one missed EPFO contribution (month index 6)
        assert not anna["epfo_records"].iloc[6]["contribution_paid"]
        assert anna["epfo_records"]["contribution_paid"].sum() == len(anna["epfo_records"]) - 1
        # Should have electricity disconnection (month index 15)
        assert anna["utility_consumption"].iloc[15]["units_consumed"] == 0.0
        assert anna["utility_consumption"].iloc[15]["payment_delay_days"] == 45
