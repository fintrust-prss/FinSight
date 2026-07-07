"""
Phase 5 Endpoint Integration Tests.

Validates:
  1. Login / JWT access token issuance
  2. RBAC access guards (unauthorized blockages)
  3. Consent compliance gating (403 on missing consent)
  4. Scoring endpoint success once consent is simulated
  5. Trend history and rescoring background tasks
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.api.deps import get_db
from app.db.repositories.alternate_data import AlternateDataRepository


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> TestClient:
    """Provide a TestClient with overridden database dependency."""
    app = create_app()
    # Override get_db to return the in-memory SQLite test session
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Helper to request a bank_officer token and return auth headers."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "officer_test", "role": "bank_officer"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def underwriter_headers(client: TestClient) -> dict[str, str]:
    """Helper to request an underwriter token and return auth headers."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "underwriter_test", "role": "underwriter"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Auth Endpoint Tests
# ===========================================================================

def test_token_issuance(client: TestClient):
    """POST /auth/token returns a valid access token envelope."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "officer_test", "role": "bank_officer"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["role"] == "bank_officer"


def test_token_endpoint_allows_cloud_run_preflight(client: TestClient):
    """OPTIONS preflight from a Cloud Run frontend origin should be accepted."""
    resp = client.options(
        "/api/v1/auth/token",
        headers={
            "Origin": "https://msme-frontend-12345-uc.a.run.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://msme-frontend-12345-uc.a.run.app"


# ===========================================================================
# 2. RBAC & MSME Endpoint Tests
# ===========================================================================

def test_msme_profile_auth_gating(client: TestClient, seeded_msmes):
    """MSME profile returns 401 if authorization header is absent."""
    resp = client.get("/api/v1/msme/msme_sakhi_001")
    assert resp.status_code == 401


def test_msme_profile_fetch(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """GET /msme/{msme_id} returns the profile details for authenticated user."""
    resp = client.get("/api/v1/msme/msme_sakhi_001", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["msme_id"] == "msme_sakhi_001"
    assert body["data"]["legal_name"] == "Sakhi Mahila Papad Udyog"
    assert body["error"] is None


def test_msme_profile_not_found(client: TestClient, auth_headers: dict[str, str]):
    """GET /msme/{msme_id} returns 404 if profile does not exist."""
    resp = client.get("/api/v1/msme/nonexistent_999", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# 3. Consent Gating Tests
# ===========================================================================

def test_scoring_consent_gating(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """GET /score returns 403 Forbidden if no active consent is found."""
    resp = client.get("/api/v1/msme/msme_sakhi_001/score", headers=auth_headers)
    assert resp.status_code == 403
    assert "consent is required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_scoring_success_with_consent(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    seeded_msmes,
):
    """Score computes successfully once dynamic consent is simulated/granted."""
    # 1. Seed some baseline alternate data for Sakhi Mahila
    # So we don't get fallback/empty scores
    repo = AlternateDataRepository(db_session)
    await repo.upsert_gst_returns([
        {
            "msme_id": "msme_sakhi_001",
            "period": date(2025, 1, 1),
            "return_type": "GSTR-3B",
            "turnover": 450000.0,
            "tax_paid": 40500.0,
            "filed_on_time": True,
            "late_days": 0,
        }
    ])
    await db_session.flush()

    # 2. Grant dynamic consent via endpoint
    consent_resp = client.post(
        "/api/v1/consent",
        json={"msme_id": "msme_sakhi_001", "data_types": ["gst", "bank_statement"], "valid_hours": 12},
        headers=auth_headers
    )
    assert consent_resp.status_code == 201
    
    # 3. Retrieve score card
    score_resp = client.get(
        "/api/v1/msme/msme_sakhi_001/score?bank_profile=idbi&use_ml=false",
        headers=auth_headers
    )
    assert score_resp.status_code == 200
    body = score_resp.json()
    assert body["data"]["msme_id"] == "msme_sakhi_001"
    assert "overall_score" in body["data"]
    assert "dimension_scores" in body["data"]
    assert body["error"] is None


# ===========================================================================
# 4. History, Anomalies, and Rescoring Tests
# ===========================================================================

def test_explainability_endpoint(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """GET /explain returns the SHAP values / contribution payload."""
    # Grant consent
    client.post(
        "/api/v1/consent",
        json={"msme_id": "msme_sakhi_001", "valid_hours": 12},
        headers=auth_headers
    )
    
    resp = client.get("/api/v1/msme/msme_sakhi_001/explain?use_ml=false", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "shap_summary" in body["data"]
    assert "reasons" in body["data"]


def test_anomalies_endpoint(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """GET /anomalies returns anomaly flags."""
    # Grant consent
    client.post(
        "/api/v1/consent",
        json={"msme_id": "msme_sakhi_001", "valid_hours": 12},
        headers=auth_headers
    )
    
    resp = client.get("/api/v1/msme/msme_sakhi_001/anomalies?use_ml=false", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "is_anomaly" in body["data"]


def test_rescoring_background_task(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """POST /rescore queues rescoring in BackgroundTasks and returns 200."""
    # Grant consent
    client.post(
        "/api/v1/consent",
        json={"msme_id": "msme_sakhi_001", "valid_hours": 12},
        headers=auth_headers
    )
    
    resp = client.post("/api/v1/msme/msme_sakhi_001/rescore?use_ml=false", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "QUEUED"
    assert "Incremental score" in body["data"]["message"]


def test_portfolio_summary_aggregates(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """GET /portfolio/summary aggregates count distributions."""
    resp = client.get("/api/v1/portfolio/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_msmes" in body["data"]
    assert "tier_distribution" in body["data"]
    assert len(body["data"]["msmes"]) == 2  # Sakhi and Annapurna


# ===========================================================================
# 5. Phase 7 Ecosystem Simulator Tests
# ===========================================================================

def test_ecosystem_status_endpoints(client: TestClient, auth_headers: dict[str, str]):
    """GET /ecosystem/uli/status and /ecosystem/ocen/status return mock status."""
    resp_uli = client.get("/api/v1/ecosystem/uli/status", headers=auth_headers)
    assert resp_uli.status_code == 200
    assert resp_uli.json()["data"]["status"] == "ONLINE"

    resp_ocen = client.get("/api/v1/ecosystem/ocen/status", headers=auth_headers)
    assert resp_ocen.status_code == 200
    assert resp_ocen.json()["data"]["status"] == "ONLINE"


def test_aa_consent_handshake_flow(client: TestClient, auth_headers: dict[str, str], seeded_msmes):
    """Verifies consent request -> pending list -> approve -> active status flow."""
    # 1. Request consent (initiating flow)
    req_resp = client.post(
        "/api/v1/ecosystem/aa/request",
        json={"msme_id": "msme_sakhi_001", "valid_hours": 12},
        headers=auth_headers
    )
    assert req_resp.status_code == 201
    consent_id = req_resp.json()["data"]["consent_id"]
    assert req_resp.json()["data"]["status"] == "PENDING"

    # 2. Verify it is in the pending list
    list_resp = client.get("/api/v1/ecosystem/aa/pending", headers=auth_headers)
    assert list_resp.status_code == 200
    pending_ids = [c["consent_id"] for c in list_resp.json()["data"]]
    assert consent_id in pending_ids

    # 3. Try ULI data fetch (should fail since status is PENDING, i.e. no active consent)
    uli_resp = client.get("/api/v1/ecosystem/uli/fetch/msme_sakhi_001", headers=auth_headers)
    assert uli_resp.status_code == 403

    # 4. Approve consent
    approve_resp = client.post(f"/api/v1/ecosystem/aa/approve/{consent_id}", headers=auth_headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["data"]["status"] == "ACTIVE"

    # 5. Fetch ULI data (should succeed now)
    uli_resp2 = client.get("/api/v1/ecosystem/uli/fetch/msme_sakhi_001", headers=auth_headers)
    assert uli_resp2.status_code == 200
    assert uli_resp2.json()["data"]["msme_profile"]["msme_id"] == "msme_sakhi_001"

    # 6. Fetch OCEN LSP signal (should succeed)
    ocen_resp = client.get("/api/v1/ecosystem/ocen/lsp-signal/msme_sakhi_001", headers=auth_headers)
    assert ocen_resp.status_code == 200
    assert ocen_resp.json()["data"]["msme_id"] == "msme_sakhi_001"

    # 7. Revoke consent
    revoke_resp = client.post(f"/api/v1/ecosystem/aa/revoke/{consent_id}", headers=auth_headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["data"]["status"] == "REVOKED"

    # 8. Fetch should fail again
    uli_resp3 = client.get("/api/v1/ecosystem/uli/fetch/msme_sakhi_001", headers=auth_headers)
    assert uli_resp3.status_code == 403

