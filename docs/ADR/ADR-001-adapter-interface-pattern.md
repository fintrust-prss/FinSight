# ADR-001: Adapter Interface Pattern for Cloud Portability

**Status:** Accepted  
**Date:** 2026-07-04  
**Author:** Hackathon Build Team  

---

## Context

The MSME Financial Health Card must be deployable on **GCP in Stage 1** and **AWS in Stage 2** with minimal code changes. A naïve implementation would import cloud SDKs (`google-cloud-storage`, `boto3`) directly in service and route modules, making the AWS migration a large-scale refactor of business logic.

We need a design that makes the cloud provider a configuration decision, not an architectural one.

---

## Decision

**All cloud SDK usage is encapsulated behind abstract Python interfaces** defined in `backend/app/adapters/base.py`:

| Interface | GCP Implementation | AWS Implementation |
|---|---|---|
| `StorageAdapter` | `GCSStorageAdapter` | `S3StorageAdapter` (Stage 2) |
| `KeyValueStore` | `FirestoreKVStore` | `DynamoDBKVStore` (Stage 2) |
| `SecretsAdapter` | `GCPSecretsAdapter` | `AWSSecretsAdapter` (Stage 2) |
| `EventPublisher` | `GCPEventPublisher` | `SNSEventPublisher` (Stage 2) |
| `EventSubscriber` | `GCPEventSubscriber` | `SQSEventSubscriber` (Stage 2) |

The **adapter factory** (`adapters/factory.py`) reads the `CLOUD_PROVIDER` environment variable and returns the correct implementation using lazy imports — GCP SDK is not loaded in AWS deployments and vice versa.

**Services never import cloud SDKs directly.** This is enforced by:
1. A ruff lint rule (`no-direct-cloud-sdk-import`) — Phase 8
2. Code review checklist in SECURITY.md
3. The directory structure itself: cloud SDK code physically lives in `adapters/gcp/` or `adapters/aws/`

---

## Consequences

**Positive:**
- Stage 2 AWS migration = implement `adapters/aws/*` + set `CLOUD_PROVIDER=aws`. Zero service/route code changes.
- Adapters can be mocked in tests without any cloud dependencies (just implement the abstract interface).
- CI pipeline doesn't need GCP credentials to run tests (mocked adapters).
- Forces a clean separation between business logic and infrastructure.

**Negative:**
- Additional boilerplate per cloud operation (factory call instead of direct SDK call).
- AWS stub adapters must be kept in sync with the interface as new methods are added.
- Interface evolution requires updating both GCP and AWS implementations simultaneously.

**Neutral:**
- GCP SDK calls use `asyncio.run_in_executor()` since the GCP Python SDK is synchronous. This adds minor overhead but is correct for FastAPI async contexts.

---

## Alternatives Considered

1. **Direct SDK imports in services:** Rejected — makes AWS migration a full rewrite.
2. **Abstract only at the service layer (not method level):** Rejected — too coarse-grained, doesn't enforce portability at the call-site level.
3. **Use a universal cloud abstraction library (e.g., libcloud):** Rejected — insufficient coverage for GCP-specific services (Pub/Sub, Secret Manager, Firestore) and adds a dependency we don't control.

---

## Reference

- Spec Section 5: GCP → AWS Service Portability Map
- Spec Section 4.3: Two Independent Services requirement
- [`adapters/base.py`](../../backend/app/adapters/base.py)
- [`adapters/factory.py`](../../backend/app/adapters/factory.py)
