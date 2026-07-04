"""
SQLAlchemy ORM Models — Phase 2.

All models mirror the Pydantic schemas defined in app/models/schemas.py.
Schema validation → API layer.  ORM models → persistence layer.

Portability note: We use standard SQL types (no PostgreSQL-specific types
in column definitions) to support SQLite for testing without changes.
The only Postgres-specific feature used is UUID primary keys via
sqlalchemy.dialects.postgresql.UUID, which gracefully falls back to
String(36) in SQLite via the `native_uuid=False` pattern handled in session.py.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


def _uuid() -> str:
    """Generate a new UUID string (used as default PK for new rows)."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# MSME
# ---------------------------------------------------------------------------

class MSME(Base):
    """
    Core MSME profile. Parent to all time-series alternate-data tables.

    msme_id is the canonical business key — sourced from Udyam/AA/GST systems.
    The ``id`` surrogate key is used for FK relationships within this DB.
    """
    __tablename__ = "msme"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    udyam_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(64), nullable=False)          # manufacturing/services/trade
    sub_sector: Mapped[str] = mapped_column(String(128), nullable=False)
    vintage_years: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    registration_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    gst_returns: Mapped[list[GSTReturn]] = relationship("GSTReturn", back_populates="msme", lazy="select")
    upi_summaries: Mapped[list[UPITransactionSummary]] = relationship("UPITransactionSummary", back_populates="msme", lazy="select")
    bank_summaries: Mapped[list[BankStatementSummary]] = relationship("BankStatementSummary", back_populates="msme", lazy="select")
    epfo_records: Mapped[list[EPFORecord]] = relationship("EPFORecord", back_populates="msme", lazy="select")
    utility_records: Mapped[list[UtilityConsumption]] = relationship("UtilityConsumption", back_populates="msme", lazy="select")
    bureau_record: Mapped[BureauRecord | None] = relationship("BureauRecord", back_populates="msme", uselist=False, lazy="select")
    digital_footprints: Mapped[list[DigitalFootprint]] = relationship("DigitalFootprint", back_populates="msme", lazy="select")
    health_scores: Mapped[list[HealthScore]] = relationship("HealthScore", back_populates="msme", lazy="select")
    consents: Mapped[list[ConsentRecord]] = relationship("ConsentRecord", back_populates="msme", lazy="select")

    def __repr__(self) -> str:
        return f"<MSME msme_id={self.msme_id!r} name={self.legal_name!r}>"


# ---------------------------------------------------------------------------
# GST Returns
# ---------------------------------------------------------------------------

class GSTReturn(Base):
    """Monthly GST-3B filing record."""
    __tablename__ = "gst_returns"
    __table_args__ = (
        UniqueConstraint("msme_id", "period", "return_type", name="uq_gst_msme_period_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    return_type: Mapped[str] = mapped_column(String(16), nullable=False, default="GSTR-3B")
    turnover: Mapped[float] = mapped_column(Float, nullable=False)
    tax_paid: Mapped[float] = mapped_column(Float, nullable=False)
    filed_on_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    late_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="gst_returns")

    def __repr__(self) -> str:
        return f"<GSTReturn msme_id={self.msme_id!r} period={self.period} turnover={self.turnover}>"


# ---------------------------------------------------------------------------
# UPI Transaction Summary
# ---------------------------------------------------------------------------

class UPITransactionSummary(Base):
    """Monthly UPI inflow/outflow summary."""
    __tablename__ = "upi_transaction_summaries"
    __table_args__ = (
        UniqueConstraint("msme_id", "month", name="uq_upi_msme_month"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    p2m_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p2m_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p2p_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p2p_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_counterparties: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="upi_summaries")


# ---------------------------------------------------------------------------
# Bank Statement Summary
# ---------------------------------------------------------------------------

class BankStatementSummary(Base):
    """Monthly AA bank statement summary (from Account Aggregator)."""
    __tablename__ = "bank_statement_summaries"
    __table_args__ = (
        UniqueConstraint("msme_id", "month", name="uq_bank_msme_month"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    avg_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inflow: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    outflow: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overdraft_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="bank_summaries")


# ---------------------------------------------------------------------------
# EPFO Record
# ---------------------------------------------------------------------------

class EPFORecord(Base):
    """Monthly EPFO contribution and headcount filing."""
    __tablename__ = "epfo_records"
    __table_args__ = (
        UniqueConstraint("msme_id", "month", name="uq_epfo_msme_month"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wage_bill: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contribution_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="epfo_records")


# ---------------------------------------------------------------------------
# Utility Consumption
# ---------------------------------------------------------------------------

class UtilityConsumption(Base):
    """Monthly electricity/water/gas consumption and payment record."""
    __tablename__ = "utility_consumption"
    __table_args__ = (
        UniqueConstraint("msme_id", "month", "utility_type", name="uq_utility_msme_month_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    utility_type: Mapped[str] = mapped_column(String(32), nullable=False, default="electricity")
    units_consumed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sanctioned_load: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payment_delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="utility_records")


# ---------------------------------------------------------------------------
# Bureau Record
# ---------------------------------------------------------------------------

class BureauRecord(Base):
    """Credit bureau profile (CIBIL/CRIF). One record per MSME."""
    __tablename__ = "bureau_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    has_file: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enquiries_last_6m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    existing_loans: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="bureau_record")


# ---------------------------------------------------------------------------
# Digital Footprint
# ---------------------------------------------------------------------------

class DigitalFootprint(Base):
    """Monthly ONDC / e-commerce / Google Business Profile metrics."""
    __tablename__ = "digital_footprints"
    __table_args__ = (
        UniqueConstraint("msme_id", "month", name="uq_digital_msme_month"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    ondc_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ecommerce_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gmb_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gmb_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="digital_footprints")


# ---------------------------------------------------------------------------
# Health Score
# ---------------------------------------------------------------------------

class HealthScore(Base):
    """
    Computed multi-dimensional financial health score.

    One record per MSME per computation date — keeps historical score snapshots.
    ``dimension_scores`` and ``shap_summary`` are stored as JSON (JSONB on Postgres,
    JSON text on SQLite for tests).
    """
    __tablename__ = "health_scores"
    __table_args__ = (
        UniqueConstraint("msme_id", "as_of_date", "model_version", name="uq_score_msme_date_model"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)   # Disciplined / Moderately Disciplined / Non-Disciplined / No-Go
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    # JSON column — dimension_scores dict + shap_summary dict stored as TEXT in tests/SQLite
    dimension_scores_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    shap_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="health_scores")

    def __repr__(self) -> str:
        return f"<HealthScore msme_id={self.msme_id!r} score={self.overall_score} tier={self.tier!r}>"


# ---------------------------------------------------------------------------
# Consent Record
# ---------------------------------------------------------------------------

class ConsentRecord(Base):
    """
    Account Aggregator dynamic consent record.

    Controls which data sources the system may access for a given MSME.
    Status lifecycle: PENDING → ACTIVE → REVOKED / EXPIRED.
    """
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    consent_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    msme_id: Mapped[str] = mapped_column(String(64), ForeignKey("msme.msme_id", ondelete="CASCADE"), nullable=False, index=True)
    data_types_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list of authorized sources
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    msme: Mapped[MSME] = relationship("MSME", back_populates="consents")

    def __repr__(self) -> str:
        return f"<ConsentRecord consent_id={self.consent_id!r} msme_id={self.msme_id!r} status={self.status!r}>"
