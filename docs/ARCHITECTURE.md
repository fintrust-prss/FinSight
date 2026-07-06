# Architecture Diagram

```mermaid
flowchart LR
    User[Bank Officer / Underwriter] --> Frontend[React + TypeScript + Vite Frontend]

    Frontend -->|HTTPS / REST| API[FastAPI Backend API]
    API --> Auth[JWT Auth + RBAC]
    API --> Consent[Consent Gate]
    API --> Scoring[Scoring Engine]
    API --> Repos[Repositories / ORM]

    Repos --> DB[(PostgreSQL)]
    Scoring --> Models[(Model Artifacts / Joblib)]
    Scoring --> Config[(scoring_weights.yaml)]

    API --> Adapters[Cloud-agnostic Adapters]
    Adapters --> GCP[Google Cloud Services]
    Adapters --> AWS[AWS Services]

    GCP --> GCS[Cloud Storage]
    GCP --> SQL[Cloud SQL]
    GCP --> PubSub[Pub/Sub]
    GCP --> Secrets[Secret Manager]

    AWS --> S3[S3]
    AWS --> RDS[RDS Postgres]
    AWS --> SNS[SNS/SQS]
    AWS --> SecretsAWS[AWS Secrets Manager]

    API --> Sim[Mock Ecosystem Connectors]
    Sim --> AA[Account Aggregator Simulator]
    Sim --> ULI[ULI Connector Stub]
    Sim --> OCEN[OCEN Connector Stub]

    Data[Synthetic Data Generator] --> Parquet[Parquet / CSV Files]
    Parquet --> Loader[Data Loader]
    Loader --> DB

    classDef core fill:#e8f1ff,stroke:#4b89dc,color:#0f172a;
    classDef data fill:#eef8ea,stroke:#4caf50,color:#0f172a;
    classDef external fill:#fff3e0,stroke:#f59e0b,color:#0f172a;

    class Frontend,API,Auth,Consent,Scoring,Repos core;
    class DB,Parquet,Loader,Config,Models data;
    class GCP,AWS,GCS,SQL,PubSub,Secrets,S3,RDS,SNS,SecretsAWS,Sim,AA,ULI,OCEN external;
```

## Notes
- The frontend is decoupled from the backend and talks only through the documented REST API.
- The backend uses adapter interfaces so the app can run on GCP or AWS with minimal change.
- Synthetic data flows from the generator into PostgreSQL for local demo and testing.
