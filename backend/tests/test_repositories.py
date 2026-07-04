"""
Phase 2 Repository Integration Tests.

Tests all three repository classes (MSMERepository, AlternateDataRepository,
HealthScoreRepository) against an in-memory SQLite database.

Coverage targets:
  - MSME CRUD: create, read by msme_id, upsert (idempotent), list filters
  - AlternateData: upsert & read for all 7 data types; date filtering
  - HealthScore: create snapshot, get_latest, get_history, list_by_tier
  - Edge cases: missing data, empty date ranges, duplicate upserts
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.db.repositories.alternate_data import AlternateDataRepository
from app.db.repositories.health_score import HealthScoreRepository
from app.db.repositories.msme import MSMERepository


# ===========================================================================
# MSME Repository Tests
# ===========================================================================

class TestMSMERepository:
    """Tests for MSMERepository — core MSME profile CRUD."""

    @pytest.mark.asyncio
    async def test_create_and_get_by_msme_id(self, msme_repo: MSMERepository, seeded_msmes):
        """get_by_msme_id returns the correct MSME by business ID."""
        sakhi = await msme_repo.get_by_msme_id("msme_sakhi_001")
        assert sakhi is not None
        assert sakhi.legal_name == "Sakhi Mahila Papad Udyog"
        assert sakhi.state == "Gujarat"
        assert sakhi.vintage_years == 12.0

    @pytest.mark.asyncio
    async def test_get_by_msme_id_not_found(self, msme_repo: MSMERepository):
        """get_by_msme_id returns None for unknown ID."""
        result = await msme_repo.get_by_msme_id("nonexistent_000")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_udyam(self, msme_repo: MSMERepository, seeded_msmes):
        """get_by_udyam resolves the Udyam registration number."""
        anna = await msme_repo.get_by_udyam("UDYAM-UP-27-0067890")
        assert anna is not None
        assert anna.msme_id == "msme_anna_002"
        assert anna.sector == "manufacturing"

    @pytest.mark.asyncio
    async def test_upsert_idempotent(self, msme_repo: MSMERepository, seeded_msmes):
        """Upserting the same msme_id twice updates the record, not duplicates it."""
        # Update Sakhi's vintage_years
        updated = await msme_repo.upsert("msme_sakhi_001", {"vintage_years": 13.0})
        assert updated.vintage_years == 13.0
        # Confirm only one row exists
        count = await msme_repo.count()
        assert count == 2  # Still just 2 MSMEs

    @pytest.mark.asyncio
    async def test_list_by_state(self, msme_repo: MSMERepository, seeded_msmes):
        """list_by_state filters MSMEs correctly."""
        gujarat_msmes = await msme_repo.list_by_state("Gujarat")
        assert len(gujarat_msmes) == 1
        assert gujarat_msmes[0].msme_id == "msme_sakhi_001"

        up_msmes = await msme_repo.list_by_state("Uttar Pradesh")
        assert len(up_msmes) == 1
        assert up_msmes[0].msme_id == "msme_anna_002"

    @pytest.mark.asyncio
    async def test_list_by_sector(self, msme_repo: MSMERepository, seeded_msmes):
        """list_by_sector filters correctly."""
        mfg_msmes = await msme_repo.list_by_sector("manufacturing")
        assert len(mfg_msmes) == 2

        service_msmes = await msme_repo.list_by_sector("services")
        assert len(service_msmes) == 0

    @pytest.mark.asyncio
    async def test_count(self, msme_repo: MSMERepository, seeded_msmes):
        """count() returns correct row count."""
        assert await msme_repo.count() == 2


# ===========================================================================
# AlternateData Repository Tests
# ===========================================================================

class TestAlternateDataRepository:
    """Tests for AlternateDataRepository — all 7 alternate-data table types."""

    @pytest.fixture
    def base_date(self) -> date:
        return date(2025, 1, 1)

    @pytest.fixture
    def gst_records(self, base_date: date) -> list[dict]:
        """12 months of GST return records for Sakhi."""
        records = []
        for i in range(12):
            period = date(base_date.year, base_date.month + i if base_date.month + i <= 12
                          else base_date.month + i - 12,
                          1) if base_date.month + i <= 12 else date(
                base_date.year + 1, base_date.month + i - 12, 1)
            records.append({
                "msme_id": "msme_sakhi_001",
                "period": period,
                "return_type": "GSTR-3B",
                "turnover": 500_000.0 + i * 10_000,
                "tax_paid": 45_000.0 + i * 900,
                "filed_on_time": True,
                "late_days": 0,
            })
        return records

    @pytest.mark.asyncio
    async def test_upsert_and_get_gst_returns(
        self,
        alt_data_repo: AlternateDataRepository,
        seeded_msmes,
        gst_records: list[dict],
    ):
        """upsert_gst_returns inserts records; get_gst_returns retrieves them."""
        count = await alt_data_repo.upsert_gst_returns(gst_records)
        assert count == 12

        returns = await alt_data_repo.get_gst_returns("msme_sakhi_001")
        assert len(returns) == 12
        # Chronological order
        for i in range(len(returns) - 1):
            assert returns[i].period <= returns[i + 1].period
        # No negative turnover
        assert all(r.turnover >= 0 for r in returns)

    @pytest.mark.asyncio
    async def test_gst_upsert_is_idempotent(
        self,
        alt_data_repo: AlternateDataRepository,
        seeded_msmes,
        gst_records: list[dict],
    ):
        """Upserting the same GST records twice does not duplicate them."""
        await alt_data_repo.upsert_gst_returns(gst_records)
        count2 = await alt_data_repo.upsert_gst_returns(gst_records)
        assert count2 == 0  # 0 new inserts (all updated)
        returns = await alt_data_repo.get_gst_returns("msme_sakhi_001")
        assert len(returns) == 12  # Still 12

    @pytest.mark.asyncio
    async def test_gst_date_filter(
        self,
        alt_data_repo: AlternateDataRepository,
        seeded_msmes,
        gst_records: list[dict],
    ):
        """get_gst_returns respects from_date/to_date filters."""
        await alt_data_repo.upsert_gst_returns(gst_records)
        # Request only records from April 2025 onwards
        from_date = date(2025, 4, 1)
        returns = await alt_data_repo.get_gst_returns(
            "msme_sakhi_001", from_date=from_date
        )
        assert all(r.period >= from_date for r in returns)

    @pytest.mark.asyncio
    async def test_upsert_and_get_upi_summaries(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """UPI summaries: upsert, read, correct ordering."""
        records = [
            {
                "msme_id": "msme_sakhi_001",
                "month": date(2025, m, 1),
                "p2m_count": 120 + m * 5,
                "p2m_value": 80_000.0 + m * 2000,
                "p2p_count": 10,
                "p2p_value": 5_000.0,
                "unique_counterparties": 45 + m,
            }
            for m in range(1, 7)
        ]
        count = await alt_data_repo.upsert_upi_summaries(records)
        assert count == 6
        summaries = await alt_data_repo.get_upi_summaries("msme_sakhi_001", months=6)
        assert len(summaries) == 6
        assert all(s.p2m_count >= 0 for s in summaries)

    @pytest.mark.asyncio
    async def test_upsert_and_get_bank_summaries(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """Bank statement summaries for Annapurna (inconsistent — 3 bounces)."""
        records = []
        for m in range(1, 7):
            bounce_count = 1 if m in (2, 4, 6) else 0  # Simulate MSME B's bounces
            records.append({
                "msme_id": "msme_anna_002",
                "month": date(2025, m, 1),
                "avg_balance": 25_000.0 if bounce_count == 0 else 5_000.0,
                "inflow": 150_000.0,
                "outflow": 145_000.0,
                "bounce_count": bounce_count,
                "overdraft_days": 2 if bounce_count > 0 else 0,
            })
        count = await alt_data_repo.upsert_bank_summaries(records)
        assert count == 6
        summaries = await alt_data_repo.get_bank_summaries("msme_anna_002", months=6)
        assert len(summaries) == 6
        total_bounces = sum(s.bounce_count for s in summaries)
        assert total_bounces == 3  # MSME B has exactly 3 bounces

    @pytest.mark.asyncio
    async def test_upsert_and_get_epfo_records(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """EPFO records: Annapurna has one missing contribution month."""
        records = [
            {
                "msme_id": "msme_anna_002",
                "month": date(2025, m, 1),
                "employee_count": 8,
                "wage_bill": 120_000.0,
                "contribution_paid": m != 4,  # Month 4: EPFO gap (MSME B's flaw)
            }
            for m in range(1, 7)
        ]
        count = await alt_data_repo.upsert_epfo_records(records)
        assert count == 6
        epfo = await alt_data_repo.get_epfo_records("msme_anna_002", months=6)
        assert len(epfo) == 6
        missed = [r for r in epfo if not r.contribution_paid]
        assert len(missed) == 1  # Exactly one missed month

    @pytest.mark.asyncio
    async def test_upsert_and_get_utility_records(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """Utility consumption: Annapurna has one disconnection month (0 units)."""
        records = [
            {
                "msme_id": "msme_anna_002",
                "month": date(2025, m, 1),
                "utility_type": "electricity",
                "units_consumed": 0.0 if m == 3 else 2500.0,  # Disconnection in month 3
                "sanctioned_load": 10.0,
                "payment_delay_days": 30 if m == 3 else 0,
            }
            for m in range(1, 7)
        ]
        count = await alt_data_repo.upsert_utility_records(records)
        assert count == 6
        utility = await alt_data_repo.get_utility_records("msme_anna_002", months=6)
        assert len(utility) == 6
        disconnections = [r for r in utility if r.units_consumed == 0.0]
        assert len(disconnections) == 1

    @pytest.mark.asyncio
    async def test_upsert_and_get_bureau_record(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """Bureau record: Sakhi has a file (thin) with score 720."""
        record = {
            "msme_id": "msme_sakhi_001",
            "has_file": True,
            "score": 720,
            "enquiries_last_6m": 1,
            "existing_loans": 1,
        }
        bureau = await alt_data_repo.upsert_bureau_record(record)
        assert bureau.has_file is True
        assert bureau.score == 720

        # Verify read-back
        fetched = await alt_data_repo.get_bureau_record("msme_sakhi_001")
        assert fetched is not None
        assert fetched.score == 720

    @pytest.mark.asyncio
    async def test_bureau_record_no_file(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """Annapurna is credit-invisible (no bureau file)."""
        record = {
            "msme_id": "msme_anna_002",
            "has_file": False,
            "score": None,
            "enquiries_last_6m": 0,
            "existing_loans": 0,
        }
        bureau = await alt_data_repo.upsert_bureau_record(record)
        assert bool(bureau.has_file) is False
        assert bureau.score is None

    @pytest.mark.asyncio
    async def test_upsert_and_get_digital_footprints(
        self, alt_data_repo: AlternateDataRepository, seeded_msmes
    ):
        """Digital footprint: Sakhi has ONDC + e-commerce orders and a GMB rating."""
        records = [
            {
                "msme_id": "msme_sakhi_001",
                "month": date(2025, m, 1),
                "ondc_orders": 80 + m * 5,
                "ecommerce_orders": 40 + m * 3,
                "gmb_rating": 4.3,
                "gmb_review_count": 120,
            }
            for m in range(1, 7)
        ]
        count = await alt_data_repo.upsert_digital_footprints(records)
        assert count == 6
        footprints = await alt_data_repo.get_digital_footprints("msme_sakhi_001", months=6)
        assert len(footprints) == 6
        assert all(f.gmb_rating >= 4.0 for f in footprints)


# ===========================================================================
# HealthScore Repository Tests
# ===========================================================================

class TestHealthScoreRepository:
    """Tests for HealthScoreRepository — score snapshot management."""

    @pytest.mark.asyncio
    async def test_create_and_get_latest_score(
        self, score_repo: HealthScoreRepository, seeded_msmes
    ):
        """create_score + get_latest return the most recent score snapshot."""
        dimension_scores = {
            "revenue_cashflow": 82.0,
            "compliance_formalization": 91.0,
            "workforce_stability": 88.0,
            "operational_footprint": 79.0,
            "digital_adoption": 73.0,
            "credit_behavior": 71.0,
            "resilience_volatility": 65.0,
        }
        score = await score_repo.create_score(
            msme_id="msme_sakhi_001",
            as_of_date=date(2025, 6, 1),
            overall_score=80.5,
            tier="Disciplined",
            dimension_scores=dimension_scores,
            shap_summary={"top_contributor": "compliance_formalization"},
        )
        assert score.overall_score == 80.5
        assert score.tier == "Disciplined"

        latest = await score_repo.get_latest("msme_sakhi_001")
        assert latest is not None
        assert latest.overall_score == 80.5

        # Verify JSON round-trip
        decoded = score_repo.decode_dimension_scores(latest)
        assert decoded["revenue_cashflow"] == 82.0
        assert decoded["compliance_formalization"] == 91.0

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(
        self, score_repo: HealthScoreRepository, seeded_msmes
    ):
        """get_latest returns the newest snapshot when multiple exist."""
        for month in [1, 3, 6]:
            await score_repo.create_score(
                msme_id="msme_sakhi_001",
                as_of_date=date(2025, month, 1),
                overall_score=70.0 + month,
                tier="Disciplined",
                dimension_scores={},
                shap_summary={},
            )
        latest = await score_repo.get_latest("msme_sakhi_001")
        assert latest is not None
        assert latest.as_of_date == date(2025, 6, 1)
        assert latest.overall_score == 76.0

    @pytest.mark.asyncio
    async def test_get_history_ordering(
        self, score_repo: HealthScoreRepository, seeded_msmes
    ):
        """get_history returns snapshots in descending date order."""
        for month in [1, 2, 3, 4, 5, 6]:
            await score_repo.create_score(
                msme_id="msme_sakhi_001",
                as_of_date=date(2025, month, 1),
                overall_score=75.0 + month,
                tier="Disciplined",
                dimension_scores={},
                shap_summary={},
            )
        history = await score_repo.get_history("msme_sakhi_001", limit=6)
        assert len(history) == 6
        # Most recent first
        assert history[0].as_of_date == date(2025, 6, 1)
        assert history[-1].as_of_date == date(2025, 1, 1)

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_for_unknown_msme(
        self, score_repo: HealthScoreRepository
    ):
        """get_latest returns None when no score exists for an MSME."""
        result = await score_repo.get_latest("nonexistent_999")
        assert result is None

    @pytest.mark.asyncio
    async def test_persona_b_scores_lower_than_persona_a(
        self, score_repo: HealthScoreRepository, seeded_msmes
    ):
        """Annapurna (MSME B) should score lower than Sakhi (MSME A)."""
        await score_repo.create_score(
            msme_id="msme_sakhi_001",
            as_of_date=date(2025, 6, 1),
            overall_score=80.0,
            tier="Disciplined",
            dimension_scores={},
            shap_summary={},
        )
        await score_repo.create_score(
            msme_id="msme_anna_002",
            as_of_date=date(2025, 6, 1),
            overall_score=42.0,
            tier="Non-Disciplined",
            dimension_scores={},
            shap_summary={},
        )
        sakhi_score = await score_repo.get_latest("msme_sakhi_001")
        anna_score = await score_repo.get_latest("msme_anna_002")

        assert sakhi_score is not None
        assert anna_score is not None
        assert sakhi_score.overall_score > anna_score.overall_score
        assert sakhi_score.tier == "Disciplined"
        assert anna_score.tier == "Non-Disciplined"

    @pytest.mark.asyncio
    async def test_list_by_tier(
        self, score_repo: HealthScoreRepository, seeded_msmes
    ):
        """list_by_tier returns only scores matching the specified tier."""
        await score_repo.create_score(
            msme_id="msme_sakhi_001",
            as_of_date=date(2025, 6, 1),
            overall_score=80.0,
            tier="Disciplined",
            dimension_scores={},
            shap_summary={},
        )
        await score_repo.create_score(
            msme_id="msme_anna_002",
            as_of_date=date(2025, 6, 1),
            overall_score=42.0,
            tier="Non-Disciplined",
            dimension_scores={},
            shap_summary={},
        )
        disciplined = await score_repo.list_by_tier("Disciplined")
        assert len(disciplined) == 1
        assert disciplined[0].msme_id == "msme_sakhi_001"

        non_disciplined = await score_repo.list_by_tier("Non-Disciplined")
        assert len(non_disciplined) == 1
        assert non_disciplined[0].msme_id == "msme_anna_002"
