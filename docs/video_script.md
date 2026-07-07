# MSME Financial Health Card — Video Script

Duration: ~3–4 minutes

Presenter: [Your Name]

---

## Opening (15–20s)

Hello — I’m [Your Name]. Today I’ll give a concise overview of the MSME Financial Health Card product: the problem it solves, how it works, key business benefits, and a short demo walkthrough.

## Problem Statement (20–30s)

Small and micro businesses often lack a consolidated, objective view of their financial health. Lenders and service providers face information gaps, longer decision cycles, and higher underwriting costs. This reduces credit access for MSMEs and increases operational risk for financial institutions.

## What We Built (20–30s)

The MSME Financial Health Card aggregates alternate data — GST returns, bank statement summaries, UPI transactions, EPFO records, utility consumption, bureau data, and digital footprint — into a single, scored healthcard. It converts distributed signals into a transparent, auditable health score and a set of diagnostic indicators that lenders can act on immediately.

## Value Proposition (25–35s)

- Faster underwriting: reduce manual verification time by up to 60% through automated data ingestion and standardized scoring.
- Better risk selection: enrich credit decisions with longitudinal behavioral signals to improve loss-rate prediction.
- Scalable sourcing: ingest multiple alternate-data streams without building custom connectors per partner.
- Improved conversion: provide MSMEs with clear, actionable guidance to improve their score and credit access.

## How It Works (30–40s)

- Data ingestion: bulk Parquet/CSV ingest of alternate datasets which are upserted into the system.
- Schema & persistence: Alembic migrations create normalized tables; repository layer performs safe upserts and maintains time-series integrity.
- Scoring engine: consumes 18–24 months of alternate data to compute a composite health score and per-dimension subscores.
- APIs & UI: a fast API serves the score and diagnostic insights to frontend dashboards, partner integrations, or batch exports.

## Security & Compliance (15–20s)

- Secrets stored in environment or managed secret stores, not in source.
- Persistent data in Postgres with role-based access controls.
- Structured logging and audit trails for ingestion and scoring to support compliance and dispute resolution.

## Key Metrics to Highlight (15–20s)

- Supported data sources: GST, AA bank summaries, UPI, EPFO, utility, bureau, digital footprint.
- Typical data horizon: 18–24 months per MSME.
- Integration time for a new partner: days (configuration + API onboarding).
- Business impact: lower default rates through improved selection; higher funded volume for verified MSMEs.

## Demo Walkthrough (40–60s)

1. Show the product splash with a one-line value proposition: "Transparent scoring. Faster decisions. More MSME access."
2. Switch to the dashboard and show a sample MSME health card — highlight the composite score and three subscores (cashflow, compliance, credit history). Briefly explain each.
3. Open the ingestion logs and show recent Parquet files loaded; mention the loader upsert and commit messages.
4. Run a quick API request (or show the API client) to fetch a health card for an MSME; highlight latency and key payload fields used for underwriting.
5. Show a short "before vs after" slide illustrating reduced verification time and improved approval rates.

## Closing / Call to Action (15–20s)

If you’re evaluating new sources of credit intelligence, we can run a pilot with a small portfolio within weeks. Share sample data and we’ll produce a baseline healthcard and uplift analysis. Thank you — I’m happy to take questions or walk through a live integration next.

---

## Optional: 60-second Elevator Version

Hello — I’m [Your Name]. The MSME Financial Health Card consolidates alternate-data signals — GST, bank summaries, UPI, EPFO, utilities, bureau and digital footprint — into a single, auditable score. It shortens underwriting time, improves risk selection, and scales across partners. We load historical data, compute a composite score and dimension subscores, and expose the result via APIs and dashboards. Request a pilot and we’ll deliver a baseline healthcard and uplift analysis in weeks.

---

## Short Taglines

- Transparent scoring. Faster decisions. More MSME access.
- Turn alternate data into confident lending.

End of Script
