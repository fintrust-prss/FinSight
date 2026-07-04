# Phase 5 Tasks
[x] Create API directory scaffolding and router init backend/app/api/v1/router.py
[x] Implement deps.py for JWT validation, role checking, and dynamic consent verification
[x] Implement authentication endpoint auth.py
[x] Implement consent simulation endpoint consent.py
[x] Implement MSME profile endpoint msme.py
[x] Implement health card scoring & rescoring endpoints score.py
[x] Implement portfolio aggregation endpoint portfolio.py
[x] Integrate routing into main.py
[x] Write complete integration tests in tests/test_api.py



# Phase 5 — Backend API Service Implementation Plan

Implement the complete FastAPI endpoints, JWT authentication, dynamic consent gating, RBAC guards, and async background rescoring.

## Proposed Changes

### [API Layer]

#### [NEW] [deps.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/deps.py)
Declares FastAPI dependencies:
- `get_db_session` dependency for database sessions.
- `get_current_user` dependency for checking JWT token validity.
- `check_consent` dependency to ensure active consent exists before accessing alternate data.
- `require_role` dependency for role-based access control (RBAC).

#### [NEW] [auth.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/auth.py)
Auth endpoints:
- `POST /api/v1/auth/token` - Issues a JWT access and refresh token.

#### [NEW] [msme.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/msme.py)
MSME profile endpoints:
- `GET /api/v1/msme/{msme_id}` - Profiles, sector, state, and registration info.
- `GET /api/v1/msme/{msme_id}/data-sources` - Consented data source catalog.

#### [NEW] [score.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/score.py)
Scoring and explainability endpoints:
- `GET /api/v1/msme/{msme_id}/score` - Health score, tier, and breakdown. Gated by active consent.
- `GET /api/v1/msme/{msme_id}/score/history` - Historical scores list. Gated by active consent.
- `GET /api/v1/msme/{msme_id}/explain` - SHAP explanation details. Gated by active consent.
- `POST /api/v1/msme/{msme_id}/rescore` - Trigger async background score recalculation. Gated by active consent.
- `GET /api/v1/msme/{msme_id}/anomalies` - Isolation Forest flags. Gated by active consent.

#### [NEW] [consent.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/consent.py)
Consent simulator:
- `POST /api/v1/consent` - Dynamically grant or revoke AA consents.

#### [NEW] [ecosystem.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/ecosystem.py)
Ecosystem connection mocks:
- `GET /api/v1/ecosystem/uli/status`
- `GET /api/v1/ecosystem/ocen/status`

#### [NEW] [portfolio.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/portfolio.py)
Portfolio dashboards:
- `GET /api/v1/portfolio/summary` - Aggregates counts by risk tiers for bank officers.

#### [NEW] [router.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/router.py)
A v1 master API router grouping all endpoint sub-routers.

#### [MODIFY] [main.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/main.py)
Integrate the v1 router and initialize database session middleware.

#### [NEW] [test_api.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/tests/test_api.py)
Integration tests validating:
- JWT Token issuance.
- Gated endpoints returning 403 on missing/expired consent.
- RBAC boundary checks.
- Async rescore timing.

## Verification Plan

### Automated Tests
- Running `pytest tests/test_api.py` to ensure route responses conform to OpenAPI specification.

## Phase 5 Summary — Backend API Service (What has been do so far)

Here's what was built and verified:

### Endpoints Created
| File | Routes |
|------|--------|
| [auth.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/auth.py) | `POST /auth/token` — JWT issuance |
| [consent.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/consent.py) | `POST /consent` — AA consent simulation |
| [msme.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/msme.py) | `GET /msme/{id}`, `GET /msme/{id}/data-sources` |
| [score.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/score.py) | `GET /score`, `/score/history`, `/explain`, `POST /rescore`, `GET /anomalies` |
| [portfolio.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/portfolio.py) | `GET /portfolio/summary` |
| [ecosystem.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/endpoints/ecosystem.py) | `GET /ecosystem/uli/status`, `/ocen/status` |

### Security & Middleware
- **JWT auth** gating via `deps.py` — 401 on missing/invalid tokens
- **RBAC** role checks (`bank_officer`, `underwriter`, `admin`)
- **Dynamic consent gating** — 403 if no active `ConsentRecord` exists for the MSME

### Integration
- [router.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/api/v1/router.py) — master v1 router combining all sub-routers
- [main.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/app/main.py) — registered under `/api/v1`

### Tests
- [test_api.py](file:///c:/Users/kumar/Documents/IDBI/FinSight/backend/tests/test_api.py) — 10 integration tests covering auth, RBAC, consent gating, scoring, explainability, anomalies, rescoring, and portfolio

**Final result: ✅ 64/64 tests passing**

---

Next up is **Phase 6 — Frontend** (React + Tailwind + Recharts dashboards). Ready to proceed when you are!