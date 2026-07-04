"""
Pydantic Schemas for Core Entities.

These schemas define the properties of the core objects used in the
MSME Financial Health Card platform (Section 7 of the spec).
They are used for validation, data generation, and API responses.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class MSMESchema(BaseModel):
    """Core MSME Profile information."""
    msme_id: str = Field(..., description="Unique ID for the MSME")
    legal_name: str = Field(..., description="Registered legal name")
    udyam_number: str = Field(..., description="Udyam Registration Number")
    sector: Literal["manufacturing", "services", "trade"] = Field(..., description="Broad sector classification")
    sub_sector: str = Field(..., description="Specific sub-sector, e.g., food_processing")
    vintage_years: float = Field(..., description="Years since company establishment")
    state: str = Field(..., description="State of operations, e.g., Gujarat")
    registration_type: str = Field(..., description="Registration type, e.g., cooperative, sole_proprietorship")


class GSTReturnSchema(BaseModel):
    """Monthly or Quarterly GST Return filing record."""
    msme_id: str
    period: date = Field(..., description="Filing month (e.g., 2024-01-01)")
    return_type: Literal["GSTR-1", "GSTR-3B", "GSTR-9"] = Field(..., description="Type of GST return")
    turnover: float = Field(..., description="Declared turnover/sales in INR")
    tax_paid: float = Field(..., description="Tax paid in INR")
    filed_on_time: bool = Field(..., description="Whether return was filed on or before due date")
    late_days: int = Field(..., description="Number of days delayed in filing")


class UPITransactionSummarySchema(BaseModel):
    """Monthly UPI transaction volume and velocity summary."""
    msme_id: str
    month: date = Field(..., description="Calendar month")
    p2m_count: int = Field(..., description="Number of Peer-to-Merchant (business inflow) transactions")
    p2m_value: float = Field(..., description="Total value of P2M transactions in INR")
    p2p_count: int = Field(..., description="Number of Peer-to-Peer transactions")
    p2p_value: float = Field(..., description="Total value of P2P transactions in INR")
    unique_counterparties: int = Field(..., description="Number of unique counterparties interacting with the MSME")


class AABankStatementSummarySchema(BaseModel):
    """Monthly bank statement summary from Account Aggregator consent flow."""
    msme_id: str
    month: date = Field(..., description="Calendar month")
    avg_balance: float = Field(..., description="Average daily balance in INR")
    inflow: float = Field(..., description="Total credit/inflows in INR")
    outflow: float = Field(..., description="Total debit/outflows in INR")
    bounce_count: int = Field(..., description="Count of cheque or ECS/NACH payment bounces")
    overdraft_days: int = Field(..., description="Number of days the account utilized overdraft/limit")


class EPFORecordSchema(BaseModel):
    """Monthly EPFO contribution and headcount filing."""
    msme_id: str
    month: date = Field(..., description="Filing month")
    employee_count: int = Field(..., description="Total employees registered for PF")
    wage_bill: float = Field(..., description="Total wage bill reported in INR")
    contribution_paid: bool = Field(..., description="Whether the monthly employer contribution was paid")


class UtilityConsumptionSchema(BaseModel):
    """Monthly utility bills and operational footprint indicators."""
    msme_id: str
    month: date = Field(..., description="Billing month")
    utility_type: Literal["electricity", "water", "gas"] = Field(..., description="Utility type")
    units_consumed: float = Field(..., description="Consumption in physical units (e.g., kWh for electricity)")
    sanctioned_load: float = Field(..., description="Sanctioned capacity/load (e.g., kW)")
    payment_delay_days: int = Field(..., description="Days delayed beyond due date")


class BureauRecordSchema(BaseModel):
    """Credit bureau profile (CIBIL/CRIF Highmark summary)."""
    msme_id: str
    has_file: bool = Field(..., description="Whether bureau records exist")
    score: int | None = Field(None, description="Bureau score (300-900), null if credit-invisible")
    enquiries_last_6m: int = Field(..., description="Number of hard credit enquiries in the last 6 months")
    existing_loans: int = Field(..., description="Number of active loan accounts")


class DigitalFootprintSchema(BaseModel):
    """Digital marketplace footprint summary (ONDC, E-commerce, GMB)."""
    msme_id: str
    month: date = Field(..., description="Calendar month")
    ondc_orders: int = Field(..., description="ONDC digital orders fulfilled")
    ecommerce_orders: int = Field(..., description="Orders from Amazon, Flipkart, etc.")
    gmb_rating: float = Field(..., description="Google Business Profile average rating (0.0 to 5.0)")
    gmb_review_count: int = Field(..., description="Google Business Profile review count")


class HealthScoreSchema(BaseModel):
    """Complete multi-dimensional health score and decision tier."""
    msme_id: str
    as_of_date: date = Field(..., description="Computation date")
    dimension_scores: dict[str, float] = Field(..., description="0-100 score for all 7 dimensions")
    overall_score: float = Field(..., description="Composite health score (0-100)")
    tier: Literal["Disciplined", "Moderately Disciplined", "Non-Disciplined", "No-Go"] = Field(..., description="Decision tier label")
    model_version: str = Field(..., description="Scoring config or ML model version used")
    shap_summary: dict[str, Any] = Field(..., description="SHAP feature importances and explanations")


class ConsentRecordSchema(BaseModel):
    """Account Aggregator dynamic consent record gating alternate data access."""
    consent_id: str = Field(..., description="Unique consent identifier")
    msme_id: str
    data_types: list[str] = Field(..., description="Authorized alternate data sources (e.g. ['GST', 'EPFO'])")
    purpose: str = Field(..., description="Explicit purpose for data access, e.g. Credit Assessment")
    status: Literal["PENDING", "ACTIVE", "REVOKED", "EXPIRED"] = Field("PENDING", description="Consent status")
    expiry: datetime = Field(..., description="Expiry timestamp after which access is revoked")
