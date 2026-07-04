# MSME Financial Health Card

> **IDBI Hackathon — Stage 1: GCP | Stage 2: AWS-portable**  
> A unified, explainable, multidimensional Financial Health Score (0–100) for MSMEs, built on alternate data sources.

---

## Problem Statement

New-to-Bank / New-to-Credit MSMEs are systematically underserved by traditional scoring models that rely on balance sheets and bureau data. This platform ingests **alternate data** (GST returns, UPI transactions, EPFO contributions, utility consumption, digital footprint) to produce a **7-dimension Financial Health Score** with a **4-tier decision label** — directly answering the IDBI Deputy Manager's requirements.

---

## Architecture (Stage 1: GCP)

```
┌──────────────────┐     HTTPS     ┌────────────────────────────────────┐
│  Frontend (React) │◄─────────────►│  Backend (FastAPI, containerized)   │
│  Cloud Run        │               │  Cloud Run                          │
└──────────────────┘               └──────────────┬─────────────────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Unified Data Layer  │
                                        │  GCS · BigQuery      │
                                        │  Cloud SQL · Pub/Sub │
                                        └──────────┬──────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Scoring & ML Engine │
                                        │  Rule Engine + SHAP  │
                                        │  XGBoost + Isolation │
                                        └─────────────────────┘
```

Cross-cutting: Secret Manager · Cloud IAM · Cloud Armor · Cloud Logging/Monitoring

---

## Alternate Data Sources

| Category | Sources |
|---|---|
| Tax & Regulatory | GST Returns, E-Way Bills, Udyam Registration, ITR/Form 26AS |
| Banking & Payments | AA Bank Statements, UPI Transactions, POS/Payment Gateway |
| Labour | EPFO Contributions, ESIC, Wage Disbursals |
| Utility | DISCOM Electricity, Water/Gas, Commercial Rent |
| Digital | ONDC, E-commerce (Amazon/Flipkart), Google Business Profile |
| Supply Chain | Commodity Price Index, DGFT/ICEGATE, Trade References |
| Ecosystem Rails | ULI (RBI), OCEN, Account Aggregator (Sahamati) |

---

## Scoring Model

### 7 Dimensions (each 0–100)
1. Revenue & Cash Flow Health
2. Compliance & Formalization
3. Workforce Stability
4. Operational Footprint
5. Digital Adoption & Market Reach
6. Credit Behavior
7. Resilience & Volatility

### 4-Tier Decision Labels
| Tier | Score | Action |
|---|---|---|
| **Disciplined ("Yes-Go")** | 75–100 | Fast-track approval |
| **Moderately Disciplined** | 55–74 | Approve with conditions |
| **Non-Disciplined ("Review")** | 35–54 | Manual underwriter review |
| **No-Go** | 0–34 | High risk, explain which dimensions |

### Two-Layer Design
- **Layer 1 — Rule Engine:** transparent, auditable, bank-configurable weight profiles
- **Layer 2 — ML Model:** XGBoost/LightGBM + SHAP explainability + Isolation Forest anomaly detection

---

## GCP → AWS Portability Map

| Function | GCP (Stage 1) | AWS (Stage 2) |
|---|---|---|
| Compute | Cloud Run | App Runner / ECS Fargate |
| Object Storage | GCS | Amazon S3 |
| Relational DB | Cloud SQL (Postgres) | RDS (Postgres) |
| NoSQL/Cache | Firestore | DynamoDB |
| Analytics | BigQuery | Redshift / Athena |
| Event Bus | Pub/Sub | SNS + SQS |
| Secrets | Secret Manager | AWS Secrets Manager |
| WAF | Cloud Armor | AWS WAF |

> **Design principle:** No business logic directly imports a cloud SDK. All cloud access goes through adapter interfaces in `backend/app/adapters/`. Swapping providers = swapping adapter + one config value.

---

## Repository Structure

```
msme-financial-health-card/
├── frontend/                    # React + TypeScript + Vite + Tailwind
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routers
│   │   ├── services/            # Business logic
│   │   ├── scoring/
│   │   │   ├── dimensions/      # 7 dimension scorers
│   │   │   └── models/          # ML model artifacts
│   │   ├── adapters/
│   │   │   ├── base.py          # Abstract interfaces (cloud-agnostic)
│   │   │   ├── gcp/             # GCP implementations
│   │   │   └── aws/             # AWS implementations (Stage 2)
│   │   ├── models/              # Pydantic + SQLAlchemy ORM
│   │   ├── repositories/        # DB access layer
│   │   └── synthetic/           # Data generator (Phase 1)
│   ├── config/
│   │   └── scoring_weights.yaml
│   └── tests/
├── infra/
│   └── terraform/               # GCP infrastructure as code
├── docs/
│   ├── ADR/                     # Architecture Decision Records
│   ├── DEMO.md
│   └── SECURITY.md
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Quick Start (Local Dev)

```bash
# Prerequisites: Docker, Docker Compose, Python 3.11+, Node 20+, Make

# 1. Copy and configure environment
cp .env.example .env

# 2. Start all services (backend + postgres + frontend)
make dev

# 3. Access services
# Backend API:  http://localhost:8000
# API Docs:     http://localhost:8000/docs
# Frontend:     http://localhost:5173
# Health check: http://localhost:8000/healthz
```

---

## Development Commands

```bash
make dev      # Start all local services (docker-compose up)
make test     # Run all tests (pytest + vitest)
make lint     # Run all linters (ruff, black, mypy, eslint)
make build    # Build production Docker images
```

---

## Synthetic Data Disclosure

> **⚠️ Important for Judges:** All MSME data in this system is **100% synthetic**, generated by a deterministic, seeded Python generator in `backend/app/synthetic/`. No real MSME, bank, or individual data is used anywhere. The two personas ("Sakhi Mahila Papad Udyog" and "Annapurna Fresh Snacks Co.") are fictional entities modeled to represent opposite risk profiles. The ML model is trained exclusively on this synthetic data with simulated default outcomes — it is a **methodology demonstration**, not a production credit model.

---

## DPDP Act 2023 Alignment

| DPDP Requirement | Implementation |
|---|---|
| Consent before data processing | `CONSENT_RECORD` gating on every alt-data endpoint |
| Purpose limitation | `purpose` field on consent records; enforced at middleware |
| Data minimization | PII tokenized in logs; only necessary fields returned per role |
| Right to access/erasure | Consent revocation endpoint; deletion hooks in repositories |
| Retention limits | `expiry` field on consent records; automated cleanup job |

---

## Security

See [`docs/SECURITY.md`](docs/SECURITY.md) for full security specification, hardening checklist, and DPDP alignment documentation.

---

## License

MIT — Built for IDBI Hackathon demonstration purposes only.
