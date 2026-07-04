# MSME Financial Health Card — Spec-Driven Development Document

**Version:** 1.0 **Prepared for:** Hackathon Build (Stage 1: GCP, Stage 2: AWS-portable) **Target Consumer:** Agentic IDE (Claude Code / Cursor / Windsurf) — each phase below is written to be pasted in as a standalone build prompt.

---

## 1\. Problem Alignment Summary

| Stakeholder Ask (Deputy Manager, IDBI) | Translated Requirement |
| :---- | :---- |
| "New-to-Bank/New-to-Credit customers should be understood beyond balance sheets" | Ingest alternate data (GST, UPI, AA, EPFO, utility) as first-class credit signals, not supplementary notes |
| "Electricity consumption for manufacturing units" | Utility/DISCOM consumption as a proxy for operating capacity & seasonality |
| "EPFO contributions" | Workforce stability & formalization signal |
| "Digital platform / digital projects / supplementary power/consumption data" | Unified digital footprint aggregation layer |
| "Categorize into disciplined / non-disciplined / no-go / yes-go" | A 4-tier decision label sitting on top of a continuous, explainable Financial Health Score |
| "Quick and easy result with most reliable methods" | Near-real-time scoring (event-driven, cached, incremental — not batch-only), explainable output (not a black box) |

**North Star:** A unified, explainable, multidimensional Financial Health Score (0–100) \+ decision tier, computed from alternate data, refreshed near-real-time, visualized as a "Health Card," and pluggable into ULI/OCEN/AA rails — built so Stage 2's AWS port is a config change, not a rewrite.

---

## 2\. Alternate Data Source Catalog (Bank/NBFC-Grade)

Use this as the master reference for what a real deployment (IDBI, SBI, HDFC, Axis, or an NBFC) would connect to. Every source below gets a synthetic generator in Phase 1\.

### 2.1 Tax & Regulatory Compliance

1. **GST Returns** (GSTR-1, GSTR-3B, GSTR-9) — turnover, ITC claims, filing timeliness, late fees  
2. **E-Way Bills** — goods movement volume/frequency (proxy for real trade activity, detects bill-trading/shell patterns)  
3. **E-Invoicing data** — B2B invoice authenticity and volume  
4. **Udyam Registration** — MSME classification (micro/small/medium), NIC industry code, registration vintage  
5. **Income Tax Returns / Form 26AS / AIS** — declared income, TDS credits  
6. **ESIC filings** — employee health insurance compliance (pairs with EPFO)  
7. **Factory/Trade/Pollution-control licenses** — regulatory standing, especially for manufacturing

### 2.2 Banking, Payments & Cash Flow (via Account Aggregator / RBI AA framework)

8. **Account Aggregator (AA) bank statements** — inflow/outflow, average balance, cheque bounces, overdraft usage  
9. **UPI transaction data** — transaction count/value, counterparty diversity, P2M vs P2P ratio, time-of-day patterns  
10. **POS / Payment Gateway data** (Razorpay, PayU, PhonePe Business, Paytm) — settlement volume, refund rate, chargeback rate  
11. **Existing loan repayment history from other lenders** (via AA-linked loan accounts)  
12. **Credit Bureau data** (CIBIL, CRIF Highmark, Experian) — even thin-file / no-file records, enquiry frequency

### 2.3 Labour & Formalization

13. **EPFO contributions** — headcount trend, monthly wage bill, employer contribution regularity  
14. **ESIC** — worker count cross-check  
15. **Wage payment consistency** (via UPI/bank salary disbursals)

### 2.4 Utility & Operational Footprint

16. **Electricity consumption (DISCOM data)** — kWh trend, load sanctioned vs used, seasonality, payment delays  
17. **Water & gas utility consumption** (relevant to food processing units)  
18. **Commercial rent / property records** — premises stability

### 2.5 Digital & Market Presence

19. **ONDC transaction data** — digital commerce participation  
20. **E-commerce marketplace data** (Amazon/Flipkart seller dashboards) — order volume, ratings, return rate  
21. **Google Business Profile / digital footprint** — reviews, ratings, years active online  
22. **Accounting/ERP software telemetry** (Tally, Zoho Books, Vyapar) — invoicing regularity, digital adoption maturity  
23. **Telecom data** — mobile bill payment regularity (alt-credit signal used by telcos/fintechs)

### 2.6 Supply Chain & Sector-Specific

23. **Raw material commodity price index** (e.g., wheat, urad dal for papad/snacks units) — margin pressure signal  
24. **DGFT/ICEGATE import-export data** — for units with trade exposure  
25. **Trade reference / supplier-buyer network data** — B2B relationship depth

### 2.7 Ecosystem Rails (integration targets, not raw data)

27. **ULI (Unified Lending Interface, RBI)** — standardized digital data flow for lenders  
28. **OCEN (Open Credit Enablement Network)** — Loan Service Provider (LSP) signal exchange  
29. **Account Aggregator ecosystem (Sahamati)** — consent artifact \+ data-fetch protocol

**Bank applicability note:** IDBI/SBI/PSU banks typically weight EPFO \+ utility \+ GST heavily (manufacturing-heavy portfolios); HDFC/Axis/private banks weight UPI \+ POS \+ bureau more (trade/services-heavy, urban); NBFCs lean hardest on UPI/telecom/digital footprint (thinnest-file segment). The scoring engine (Section 6\) must support **per-institution weight profiles** for this reason.

---

## 3\. Synthetic MSME Personas

Two food-FMCG manufacturing MSMEs, modeled loosely on a cooperative papad/snacks manufacturer (Lijjat-style), representing opposite ends of the risk spectrum. Both get 18–24 months of synthetic history across every data source in Section 2 (minus the ecosystem rails, which are integration simulators, not data).

### MSME A — "Sakhi Mahila Papad Udyog" (Established, Disciplined)

- 12 years old, Udyam-registered (Small), women's cooperative, Gujarat, papad \+ fryums manufacturing  
- Steady, seasonal GST filings (festive-season spike Oct–Dec), always filed within due date  
- EPFO: 45→60 employees over 18 months, rising wage bill, zero missed contributions  
- Electricity: strong correlation with production season, sanctioned-load utilization 70–85%  
- UPI/POS: high P2M volume from distributor network, low bounce rate on bank statement  
- Bureau: thin file but one small prior loan repaid on time  
- **Expected label:** Disciplined / "Yes-Go"

### MSME B — "Annapurna Fresh Snacks Co." (New-to-Bank, Inconsistent)

- 2.5 years old, recently Udyam-registered, sole proprietor, Uttar Pradesh, namkeen/snacks manufacturing  
- Irregular GST filing (2 late filings, 1 missed quarter), turnover volatile  
- EPFO: newly registered, only 8 employees, one contribution gap  
- Electricity: erratic consumption, one disconnection-for-non-payment event  
- UPI: high volume but concentrated in few counterparties (concentration risk), 3 cheque bounces  
- Bureau: no file (credit-invisible)  
- **Expected label:** Semi-disciplined → borderline "No-Go" unless alternate signals compensate (this is the persona that proves the tool's value — traditional scoring rejects them, alternate data may reveal a viable borrower)

Both personas are defined as structured YAML "persona configs" (Phase 1\) so the generator is parameterized — a judge/demo can add a third persona without touching code.

---

## 4\. System Architecture (Stage 1: GCP)

### 4.1 High-Level Component View

┌─────────────────────────┐        ┌──────────────────────────────────────────┐

│   FRONTEND SERVICE       │  HTTPS │   BACKEND SERVICE (FastAPI, containerized)│

│   React \+ Vite \+ TS      │◄──────►│   /api/v1/...                              │

│   Cloud Run (or Firebase │        │   Cloud Run                                │

│   Hosting)                │        └───────────────┬────────────────────────────┘

└─────────────────────────┘                        │

                                                     ▼

                          ┌───────────────────────────────────────────┐

                          │  Unified Data Layer                        │

                          │  \- Cloud Storage (raw synthetic data lake) │

                          │  \- BigQuery (feature store / analytics)    │

                          │  \- Cloud SQL / Firestore (app \+ consent DB)│

                          └───────────────┬─────────────────────────────┘

                                          ▼

                          ┌───────────────────────────────────────────┐

                          │  Scoring & ML Engine                       │

                          │  \- Feature Engineering module (Python)     │

                          │  \- Rule-based baseline scorer               │

                          │  \- Vertex AI (or local sklearn/XGBoost)     │

                          │    trained risk model \+ SHAP explainability │

                          └───────────────┬─────────────────────────────┘

                                          ▼

                          ┌───────────────────────────────────────────┐

                          │  Ecosystem Connectors (simulated)           │

                          │  \- AA consent simulator                     │

                          │  \- OCEN/ULI mock adapters                   │

                          └───────────────────────────────────────────┘

Cross-cutting: Secret Manager, Cloud IAM, Cloud Armor, Cloud Logging/Monitoring, Pub/Sub (event-driven re-scoring)

### 4.2 Why this shape supports "near real-time"

- New data event (e.g., a fresh UPI batch) → Pub/Sub message → incremental feature recompute (only affected dimensions) → cached score update → frontend polls/subscribes for delta. Avoids full re-computation on every request.

### 4.3 Two Independent Services (explicit requirement)

- **`frontend/`** — deployable and versioned independently. Talks to backend only via documented REST contract (Section 8). No backend code imported.  
- **`backend/`** — deployable and versioned independently. Stateless API layer; all state in Cloud SQL/Firestore/BigQuery/Cloud Storage. CORS-configured, never assumes a specific frontend origin in business logic.

---

## 5\. GCP → AWS Service Portability Map (Stage 2 prep)

Design constraint for every phase below: **no business logic may directly import a cloud SDK.** All cloud access goes through a thin adapter interface (`storage_adapter.py`, `db_adapter.py`, `ml_adapter.py`, `pubsub_adapter.py`) so swapping providers means swapping an adapter implementation \+ one config value, not rewriting services.

| Function | GCP (Stage 1\) | AWS (Stage 2\) | Portability Notes |
| :---- | :---- | :---- | :---- |
| Compute (frontend \+ backend containers) | Cloud Run | AWS App Runner / ECS Fargate | Both are container-native, autoscaling, HTTPS-terminating. Use a single `Dockerfile` per service — no GCP-specific base image. |
| Object storage (raw synthetic data, documents) | Cloud Storage (GCS) | Amazon S3 | Use `boto3`/`google-cloud-storage` behind one `StorageAdapter` interface (`put`, `get`, `list`, `signed_url`). |
| Relational DB (consent, users, audit) | Cloud SQL (Postgres) | Amazon RDS (Postgres) | Keep 100% vanilla Postgres SQL/ORM (SQLAlchemy) — zero Cloud SQL–specific extensions. |
| Document/NoSQL store (session, cache) | Firestore | DynamoDB | Keep access behind a `KeyValueStore` interface; avoid Firestore-specific query features (e.g. complex composite indexes) that don't map cleanly. |
| Analytical warehouse / feature store | BigQuery | Amazon Redshift / Athena \+ Glue | Keep feature engineering SQL ANSI-standard where possible; isolate BQ-specific SQL (e.g. `ML.PREDICT`) behind adapter. |
| ML training & serving | Vertex AI (or local sklearn/XGBoost container) | Amazon SageMaker | **Recommendation:** train/serve the model as a plain containerized Python service (FastAPI \+ joblib/ONNX) from day 1 — this runs unchanged on Cloud Run *or* Fargate *or* SageMaker endpoints, sidestepping vendor lock-in almost entirely. |
| Event/message bus | Pub/Sub | Amazon SNS \+ SQS, or EventBridge | Abstract behind `EventPublisher`/`EventSubscriber`; both support pub-sub semantics. |
| Secrets | Secret Manager | AWS Secrets Manager | Access via `SecretsAdapter.get_secret(name)`; both SDKs are near-identical. |
| IAM / auth | Cloud IAM \+ Identity Platform | AWS IAM \+ Cognito | App-level auth should be self-issued JWT (Section 9\) so the identity *provider* underneath is swappable. |
| WAF / edge security | Cloud Armor | AWS WAF | Config-as-code (Terraform) — same ruleset logic, different provider block. |
| Monitoring/Logging | Cloud Monitoring \+ Cloud Logging | Amazon CloudWatch | Emit structured JSON logs (provider-agnostic) so log *shipping* is the only thing that changes. |
| CDN / static hosting | Firebase Hosting / Cloud CDN | CloudFront \+ S3 | Frontend build output (`dist/`) is a static bundle either way. |
| Infra-as-code | Terraform (GCP provider) | Terraform (AWS provider) | **Use Terraform from Stage 1**, not gcloud CLI scripts/console clicks — this alone is 70% of "AWS portability." |

**Actionable rule for the IDE agent:** every module that touches a cloud SDK must live under `backend/app/adapters/gcp/*` with a matching interface in `backend/app/adapters/base.py`. Stage 2 work becomes: implement `backend/app/adapters/aws/*` \+ flip an env var.

---

## 6\. Unified Multidimensional Financial Health Score

### 6.1 Seven Scoring Dimensions (each 0–100)

1. **Revenue & Cash Flow Health** — GST turnover trend, UPI/POS inflow stability, AA bank-statement average balance & bounce rate  
2. **Compliance & Formalization** — GST filing timeliness, Udyam status, license validity, ESIC/EPFO filing regularity  
3. **Workforce Stability** — EPFO headcount trend, wage bill growth, contribution consistency  
4. **Operational Footprint** — electricity/utility consumption trend vs. declared capacity, seasonality alignment with sector norms  
5. **Digital Adoption & Market Reach** — UPI/ONDC/e-commerce diversity, counterparty concentration (Herfindahl index), digital footprint recency  
6. **Credit Behavior** — bureau data if present, else proxy from AA repayment-like patterns, cheque bounce frequency  
7. **Resilience & Volatility** — coefficient of variation across cash flow, raw-material price sensitivity, sector seasonality adjustment

### 6.2 Two-Layer Scoring Design (rule-based \+ ML, in that order)

- **Layer 1 — Deterministic/Expert Rule Engine:** transparent, auditable, weighted scoring per dimension using domain thresholds (bank-configurable weight profile per Section 2 note). This is the fallback and the explainability anchor — a bank examiner must be able to see *exactly* why a score moved.  
- **Layer 2 — ML Risk Model:** a Gradient Boosting classifier (XGBoost/LightGBM) trained on the Layer-1 engineered features against **synthetically simulated default outcomes** (labels generated via a documented, seeded rule \+ noise process — clearly marked as synthetic/for-demo in code and README, ready to be retrained on real bank outcome data later). Output: probability of default \+ the decision tier.  
- **Explainability:** SHAP values surfaced per prediction, mapped back to the 7 dimensions, shown on the Health Card UI as "why this score."  
- **Anomaly/fraud flagging:** Isolation Forest across the feature vector to flag statistically inconsistent MSMEs (e.g., GST turnover contradicting UPI volume) — surfaced as a data-integrity warning, not folded silently into the score.

### 6.3 Decision Tiers (maps directly to the Deputy Manager's ask)

| Tier | Score Range | Meaning |
| :---- | :---- | :---- |
| **Disciplined ("Yes-Go")** | 75–100 | Strong, consistent, low-risk — fast-track |
| **Moderately Disciplined ("Go with Conditions")** | 55–74 | Viable, recommend conditions (collateral-lite, lower ticket, monitoring) |
| **Non-Disciplined ("Review")** | 35–54 | Needs manual underwriter review — alternate data flagged specific weak dimensions |
| **No-Go** | 0–34 | High risk given current data; explain which dimensions drove it |

### 6.4 Efficiency Requirements

- Feature computation must be **vectorized** (pandas/numpy or Polars), no row-wise Python loops over transaction-level data.  
- Support **incremental scoring**: a new data event recomputes only the affected dimension(s), not the full 7-dimension pipeline (target: \<500ms for an incremental update, \<3s for a full recompute, on synthetic-scale data).  
- All heavy features (e.g., Herfindahl index, CoV) cached in the feature store (BigQuery table or equivalent) keyed by `(msme_id, as_of_date)`.  
- Model inference must be \<200ms p95 for a single MSME scoring call.

---

## 7\. Data Model (Core Entities)

MSME

 ├─ msme\_id (PK), legal\_name, udyam\_number, sector, sub\_sector, vintage\_years, state, registration\_type

GST\_RETURN

 ├─ msme\_id (FK), period, return\_type, turnover, tax\_paid, filed\_on\_time (bool), late\_days

UPI\_TRANSACTION\_SUMMARY

 ├─ msme\_id (FK), month, p2m\_count, p2m\_value, p2p\_count, p2p\_value, unique\_counterparties

AA\_BANK\_STATEMENT\_SUMMARY

 ├─ msme\_id (FK), month, avg\_balance, inflow, outflow, bounce\_count, overdraft\_days

EPFO\_RECORD

 ├─ msme\_id (FK), month, employee\_count, wage\_bill, contribution\_paid (bool)

UTILITY\_CONSUMPTION

 ├─ msme\_id (FK), month, utility\_type, units\_consumed, sanctioned\_load, payment\_delay\_days

BUREAU\_RECORD

 ├─ msme\_id (FK), has\_file (bool), score (nullable), enquiries\_last\_6m, existing\_loans

DIGITAL\_FOOTPRINT

 ├─ msme\_id (FK), month, ondc\_orders, ecommerce\_orders, gmb\_rating, gmb\_review\_count

HEALTH\_SCORE

 ├─ msme\_id (FK), as\_of\_date, dimension\_scores (JSON), overall\_score, tier, model\_version, shap\_summary (JSON)

CONSENT\_RECORD (AA-simulation)

 ├─ consent\_id, msme\_id (FK), data\_types\[\], purpose, status, expiry

All synthetic tables generated as CSV/Parquet in Phase 1, loaded into BigQuery (or Cloud SQL for the transactional tables) in Phase 2\.

---

## 8\. Backend API Contract (v1, indicative)

POST   /api/v1/auth/token                        \# issue JWT (demo login)

GET    /api/v1/msme/{msme\_id}                     \# profile \+ Udyam \+ sector info

GET    /api/v1/msme/{msme\_id}/data-sources        \# raw alt-data summary per source

GET    /api/v1/msme/{msme\_id}/score               \# latest health score \+ tier \+ dimension breakdown

GET    /api/v1/msme/{msme\_id}/score/history        \# score trend over time

GET    /api/v1/msme/{msme\_id}/explain              \# SHAP-based explanation payload

POST   /api/v1/msme/{msme\_id}/rescore              \# trigger recompute (simulates new data event)

GET    /api/v1/msme/{msme\_id}/anomalies            \# isolation-forest flags

POST   /api/v1/consent                            \# simulate AA consent grant

GET    /api/v1/ecosystem/uli/status                \# mock ULI connector status

GET    /api/v1/ecosystem/ocen/status               \# mock OCEN connector status

GET    /api/v1/portfolio/summary                   \# bank-level dashboard aggregate (both MSMEs \+ synthetic peers)

GET    /healthz                                    \# liveness/readiness

All responses: consistent envelope `{ "data": ..., "meta": {...}, "error": null }`. All list endpoints paginated. All endpoints versioned under `/api/v1`.

---

## 9\. Security Specification (non-negotiable, applies to every phase)

- **Auth:** JWT (short-lived access \+ refresh token), signed with a secret from Secret Manager — never hardcoded, never committed.  
- **AA-aligned consent model:** every alternate-data access is gated by a `CONSENT_RECORD` with explicit `data_types`, `purpose`, and `expiry` — mirrors real RBI AA framework; log every data access against its consent.  
- **Data minimization & tokenization:** PII fields (names, account numbers) tokenized/masked in logs and in any non-authorized API response.  
- **Transport & storage:** TLS everywhere (enforced at Cloud Run/App Runner ingress); encryption at rest (default GCS/Cloud SQL encryption \+ CMEK optional).  
- **Input validation:** Pydantic schemas on every request body; reject unknown fields; strict type/range validation (e.g., dates, monetary values).  
- **Injection defense:** parameterized queries only (SQLAlchemy ORM/params) — no string-interpolated SQL, anywhere.  
- **RBAC:** roles (`bank_officer`, `underwriter`, `admin`) enforced at route level via dependency-injection guards, not ad hoc checks scattered in handlers.  
- **Secrets:** all API keys/DB creds via Secret Manager / env-injected at deploy time; `.env.example` committed, `.env` gitignored.  
- **Audit logging:** every score computation, data access, and consent event written to an immutable audit log table with actor, timestamp, action.  
- **Rate limiting:** per-token request throttling at the API gateway/ingress layer.  
- **Dependency hygiene:** `pip-audit`/`safety` and `npm audit` run in CI; no critical/high vulnerabilities allowed to merge.  
- **DPDP Act 2023 alignment note:** document (in README) how consent, purpose limitation, and data-retention fields map to India's Digital Personal Data Protection Act — a judge-facing compliance talking point, not just an engineering nicety.

---

## 10\. Frontend Specification

- **Stack:** React \+ TypeScript \+ Vite, Tailwind for styling, Recharts/D3 for visualizations.  
- **Screens:**  
  1. **Login / Bank Officer selection** (demo auth)  
  2. **Portfolio Dashboard** — all onboarded MSMEs, tier distribution, quick filters (sector, state, tier)  
  3. **MSME Financial Health Card** (the centerpiece):  
     - Header: name, sector, vintage, Udyam status  
     - Radar/spider chart of the 7 dimensions  
     - Overall score gauge \+ tier badge (color-coded: green/yellow/orange/red)  
     - "Why this score" panel — top contributing/detracting factors (from SHAP)  
     - Data source trust panel — which alt-data sources are connected/consented, freshness timestamp  
     - Score trend over time (line chart)  
     - Anomaly/fraud flag banner if present  
  4. **Data Source Explorer** — drill into raw GST/UPI/EPFO/utility series per MSME (for underwriter due diligence)  
  5. **Ecosystem Status** — mock ULI/OCEN/AA connector health indicators  
- **Non-functional:** responsive, accessible (WCAG AA contrast on tier colors), loading/error/empty states on every data fetch, no direct cloud SDK calls from frontend (backend-mediated only).

---

## 11\. Testing Strategy

- **Unit tests (pytest, backend):** every feature-engineering function, every rule-based dimension scorer, adapter interfaces (mocked cloud clients) — target ≥85% line coverage on `app/services` and `app/scoring`.  
- **Model validation tests:** score monotonicity checks (e.g., increasing bounce\_count must not increase the score), stability under small input perturbation, basic fairness check across the two personas' sub-segments (state/sector) to catch a dimension that's accidentally penalizing a whole category.  
- **Data validation tests:** Pydantic/Great Expectations checks on every synthetic dataset generator's output (no negative turnover, monotonic dates, referential integrity to `msme_id`).  
- **Integration tests:** full API contract tests (httpx/TestClient) including auth, consent-gating (score endpoint must 403 if consent missing/expired), and error envelopes.  
- **Frontend tests:** component tests (Vitest \+ React Testing Library) for the Health Card and dashboard; at least one Cypress/Playwright e2e happy-path (login → view MSME → view score → view explanation).  
- **Performance tests:** locust/k6 script hitting `/score` and `/rescore` to validate the near-real-time latency targets in Section 6.4.  
- **CI gate:** GitHub Actions pipeline running lint (ruff/eslint) → type-check (mypy/tsc) → unit+integration tests → security scan (bandit/npm audit) → build. No merge on red.

---

## 12\. Code Quality Standards

- Layered backend structure: `api/` (routers) → `services/` (business logic) → `scoring/` (dimension \+ ML logic) → `adapters/` (cloud/base \+ gcp \+ aws) → `models/` (Pydantic \+ ORM schemas) → `repositories/` (DB access).  
- Full type hints (Python) / strict TypeScript (`strict: true`), no `any`.  
- `black` \+ `ruff` \+ `mypy` (backend), `eslint` \+ `prettier` (frontend), enforced via pre-commit hooks.  
- Docstrings on every public function/class explaining the alt-data rationale (not just the code — the domain reasoning), since this is a domain-heavy hackathon judged partly on explainability.  
- Conventional Commits; a lightweight `ADR/` folder capturing key architecture decisions (e.g., "why rule-engine-first before ML layer").  
- No secrets, no magic numbers for scoring thresholds — thresholds live in a single versioned `config/scoring_weights.yaml` (also what makes per-bank weight profiles from Section 2 possible).

---

## 13\. Phased Build Plan (Agentic-IDE Ready)

Each phase below is written so it can be pasted directly as a build instruction. Work sequentially; do not start a phase until the previous phase's Definition of Done is met.

### Phase 0 — Repo & Environment Scaffolding

**Instruction to IDE agent:**

Create a monorepo with two independent, separately-deployable services: `frontend/` (React \+ TypeScript \+ Vite \+ Tailwind) and `backend/` (Python 3.11 \+ FastAPI \+ SQLAlchemy \+ Pydantic v2). Add `docker-compose.yml` for local dev (backend, Postgres, and a synthetic-data volume). Add `Makefile` with `make dev`, `make test`, `make lint`. Set up pre-commit (black, ruff, mypy) and a GitHub Actions workflow skeleton (`lint → test → build`) that fails the pipeline on any error. Create the adapter-interface skeleton (`backend/app/adapters/base.py` with abstract `StorageAdapter`, `KeyValueStore`, `SecretsAdapter`, `EventPublisher`) and empty `adapters/gcp/` and `adapters/aws/` folders — implementations come later, but the seam must exist from day one. Add `.env.example` and `README.md` stating the GCP-first/AWS-portable design goal. **Definition of Done:** `make dev` boots both services locally; CI pipeline runs green on an empty test suite; adapter interfaces committed with docstrings.

### Phase 1 — Synthetic Data Generation Engine

**Instruction to IDE agent:**

Build `backend/app/synthetic/` — a deterministic (seeded), config-driven synthetic data generator. Define two persona YAML configs under `backend/app/synthetic/personas/` matching Section 3 of the spec (Sakhi Mahila Papad Udyog — disciplined; Annapurna Fresh Snacks Co. — new-to-bank/inconsistent). For each persona, generate 18–24 months of: GST returns, UPI transaction summaries, AA bank-statement summaries, EPFO records, utility consumption, bureau record, digital footprint (per the schemas in Section 7). Encode realistic seasonality (festive-season spike for papad/snacks), and deliberately inject the persona's known irregularities (e.g., MSME B's missed EPFO month, cheque bounces, disconnection event) so the scoring engine has real signal to react to. Output as Parquet to a local `data/synthetic/` folder and add a script to bulk-load into Postgres/BigQuery. Write unit tests validating referential integrity, date monotonicity, and no-negative-value invariants across all generated tables. **Definition of Done:** Running the generator produces reproducible (seeded) data for both personas passing all validation tests; data loads cleanly into the dev DB.

### Phase 2 — Unified Data Layer & Repositories

**Instruction to IDE agent:**

Implement SQLAlchemy models for every entity in Section 7, plus repository classes exposing typed query methods (no raw SQL in services). Implement the GCP adapter set (`adapters/gcp/storage.py` using google-cloud-storage, `adapters/gcp/db.py` for Cloud SQL connection, `adapters/gcp/secrets.py`, `adapters/gcp/pubsub.py`) conforming to the Phase 0 interfaces. Wire environment-based adapter selection (`CLOUD_PROVIDER=gcp|aws` env var choosing which adapter package loads) even though only `gcp/` has a real implementation right now — `aws/` should raise a clear `NotImplementedError` with a comment marking it as the Stage 2 task. Add integration tests (using a local Postgres test container) for every repository method. **Definition of Done:** Repositories pass tests against a real (test) Postgres instance; adapter selection is provider-agnostic at the call site.

### Phase 3 — Rule-Based Scoring Engine (Layer 1\)

**Instruction to IDE agent:**

Implement `backend/app/scoring/dimensions/` with one module per dimension from Section 6.1, each a pure function taking the relevant repository data and returning a 0–100 score plus a human-readable "reason" string per contributing factor. Read all thresholds/weights from `config/scoring_weights.yaml` (never hardcoded) and support a `bank_profile` parameter so IDBI/SBI/HDFC/Axis/NBFC weight profiles (per Section 2 note) can be swapped without code changes. Implement the aggregator producing the overall score and the 4-tier decision label from Section 6.3. Vectorize all computations (pandas/numpy — no per-row Python loops). Write unit tests per dimension covering: normal case, missing-data case, and each persona's known edge case (e.g., MSME B's EPFO gap must visibly lower the Workforce Stability score). **Definition of Done:** Both synthetic personas score plausibly differently (A lands "Disciplined," B lands "Non-Disciplined"/"Review" range); ≥85% test coverage on this module; scoring is fully explainable via the reason strings.

### Phase 4 — ML Layer (Layer 2\) & Explainability

**Instruction to IDE agent:**

Add a synthetic label generator that simulates a "default within 12 months" outcome per MSME-month using a documented, seeded rule (based on the Layer-1 dimension scores plus injected noise) — clearly commented as a stand-in for real bank outcome data. Train a gradient boosting classifier (XGBoost or LightGBM) on the Layer-1 engineered features against these labels; persist the model as a versioned artifact (joblib/ONNX) under `backend/app/scoring/models/`. Wrap inference in a `MLScorer` service returning probability-of-default and a tier recommendation, and add SHAP-based per-prediction explanations mapped back to the 7 dimensions. Add an Isolation Forest anomaly detector flagging internally-inconsistent MSMEs. Write model validation tests: monotonicity (Section 11), latency (\<200ms p95 inference on synthetic scale), and a basic cross-segment fairness check. **Definition of Done:** `/score` can return either Layer-1-only or Layer-1+Layer-2 blended output (feature-flagged); SHAP explanation payload is stable and test-covered; model card documented in README (training data caveat: synthetic).

### Phase 5 — Backend API Service

**Instruction to IDE agent:**

Implement all endpoints from Section 8 using FastAPI routers calling into the Phase 2–4 services — routers must contain no business logic. Implement JWT auth, the consent-gating middleware (Section 9 — every alt-data-backed endpoint checks an active `CONSENT_RECORD`), RBAC route guards, structured JSON logging, and the standard response envelope. Add the incremental re-scoring flow: `/rescore` publishes an event via `EventPublisher`, a background worker (or async task) recomputes only the affected dimension(s) and updates the cached `HEALTH_SCORE` row. Add full Pydantic request/response schemas and auto-generated OpenAPI docs. Write integration tests for every endpoint including the 403-on-missing-consent case and the auth/RBAC boundary cases. **Definition of Done:** Full OpenAPI spec browsable at `/docs`; all endpoints pass integration tests; incremental rescore demonstrably faster than full pipeline recompute (assert via test timing).

### Phase 6 — Frontend Application

**Instruction to IDE agent:**

Build the five screens from Section 10 against the Phase 5 API contract, using React Query (or SWR) for data fetching with proper loading/error/empty states everywhere. Build the Health Card radar chart, gauge, and "why this score" panel using Recharts. Implement tier color-coding meeting WCAG AA contrast. Add Vitest \+ React Testing Library component tests for the Health Card and Dashboard, and one Playwright e2e happy-path test. No direct cloud SDK usage in frontend code — all data via the backend API only. **Definition of Done:** Full user journey (login → dashboard → MSME health card → explanation → data source explorer) works against the live backend; component \+ e2e tests pass in CI.

### Phase 7 — Ecosystem Integration Simulators (ULI/OCEN/AA)

**Instruction to IDE agent:**

Build mock connector modules simulating: (a) an AA consent-flow handshake (issue/revoke consent, expiry handling — already partially built in Phase 5's consent gate, this phase adds the initiating "request consent" flow and a simple consent UI screen), (b) a ULI-style standardized data-fetch response format, (c) an OCEN-style loan-service-provider signal exchange stub. These should be clearly marked as simulators (mock external system, deterministic canned \+ config-driven responses) but structured so a real integration later is a matter of implementing the same interface against a real endpoint. Expose status via the `/ecosystem/*` endpoints and the "Ecosystem Status" frontend screen. **Definition of Done:** Demo can show a consent request → grant → data-gated score unlock flow end-to-end; ecosystem status screen reflects mock connector health.

### Phase 8 — Security Hardening Pass

**Instruction to IDE agent:**

Run a dedicated hardening pass across the whole codebase against every item in Section 9: confirm no secrets in code/history, confirm parameterized queries everywhere, add rate-limiting middleware, add `bandit` (Python) and `npm audit` (frontend) to CI as blocking checks, add PII masking to all logging, and add the audit-log table \+ write-path for score computations and consent events. Document DPDP Act 2023 alignment in `SECURITY.md`. **Definition of Done:** CI security scans green; a manual review checklist (attach as `SECURITY.md`) is fully checked off; audit log demonstrably captures a full score-computation trail for one MSME.

### Phase 9 — Deployment (GCP) \+ AWS-Portability Verification

**Instruction to IDE agent:**

Write Terraform for the GCP stack (Cloud Run x2, Cloud SQL, Cloud Storage, Secret Manager, Pub/Sub, Cloud Armor) per Section 5's mapping. Deploy both services. Then, as a portability smoke-test, implement a minimal `adapters/aws/storage.py` (S3) behind the same interface and prove — via a config flag and a local test — that swapping `CLOUD_PROVIDER=gcp` to `aws` for just the storage adapter requires zero changes to any service/route code. This proves the Section 5 design goal without doing the full AWS migration yet. **Definition of Done:** Live GCP URLs for both services; portability smoke-test passes; Terraform is the only path to infra (no manual console changes).

### Phase 10 — Demo Narrative & Documentation

**Instruction to IDE agent:**

Write `DEMO.md` with a scripted walkthrough: open Portfolio Dashboard → select MSME B (Annapurna, the NTB/NTC persona) → show traditional-doc gaps → show alternate-data Health Card revealing a "Go with Conditions" recommendation traditional scoring would have missed → show "why this score" explainability → show consent flow → show ecosystem status. Ensure `README.md` clearly states: problem statement addressed, architecture diagram (Section 4), data sources catalog (Section 2), GCP→AWS portability table (Section 5), and explicit synthetic-data disclosure (what's real methodology vs. synthetic stand-in data, for judge transparency). **Definition of Done:** A cold reader (judge) can follow `DEMO.md` end-to-end without additional context.

---

## 14\. Suggested Repository Structure

msme-financial-health-card/

├── frontend/

│   ├── src/

│   │   ├── pages/            \# 5 screens from Section 10

│   │   ├── components/

│   │   ├── api/               \# typed API client

│   │   └── ...

│   └── package.json

├── backend/

│   ├── app/

│   │   ├── api/                \# routers (Section 8\)

│   │   ├── services/

│   │   ├── scoring/

│   │   │   ├── dimensions/     \# Phase 3

│   │   │   └── models/         \# Phase 4 artifacts

│   │   ├── adapters/

│   │   │   ├── base.py

│   │   │   ├── gcp/

│   │   │   └── aws/

│   │   ├── models/             \# Pydantic \+ ORM (Section 7\)

│   │   ├── repositories/

│   │   └── synthetic/          \# Phase 1

│   │       └── personas/

│   ├── config/

│   │   └── scoring\_weights.yaml

│   ├── tests/

│   └── pyproject.toml

├── infra/

│   └── terraform/

├── docs/

│   ├── ADR/

│   ├── DEMO.md

│   └── SECURITY.md

└── README.md

---

## 15\. Success Criteria Mapped to Judging Parameters

| Parameter | How this spec satisfies it |
| :---- | :---- |
| **Code Quality** | Layered architecture, typed everywhere, lint/format/pre-commit gates, config-driven thresholds, ADRs |
| **Security** | Consent-gated data access, JWT+RBAC, secrets management, audit logging, DPDP alignment, CI security scans |
| **Algorithm Efficiency** | Vectorized feature engineering, incremental re-scoring, cached feature store, \<200ms inference target, documented latency tests |
| **Testing** | Unit \+ integration \+ model-validation \+ e2e \+ performance tests, ≥85% coverage target, CI-enforced |
| **Problem Statement Alignment** | Direct traceability from Deputy Manager's ask (Section 1\) → data sources (Section 2\) → 7-dimension score → 4-tier disciplined/no-go labels → ULI/OCEN/AA integration → near-real-time incremental scoring |

---

*End of specification. Build phases 0–10 sequentially in the agentic IDE; each phase's "Definition of Done" is the acceptance gate before proceeding.*  
