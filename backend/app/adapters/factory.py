"""
Adapter Factory — provider-agnostic adapter instantiation.

Reads ``CLOUD_PROVIDER`` env var and returns the correct adapter implementation.
All service code calls ``get_storage_adapter()`` etc. — never imports GCP/AWS directly.

Usage:
    from app.adapters.factory import get_storage_adapter, get_secrets_adapter

    storage = await get_storage_adapter()
    data = await storage.get("raw/gst/2024-01.parquet")

Stage 2 migration:
    Set ``CLOUD_PROVIDER=aws`` → AWS adapters load automatically.
    Zero changes to service/route code.
"""

from __future__ import annotations

import structlog

from app.adapters.base import (
    EventPublisher,
    EventSubscriber,
    KeyValueStore,
    SecretsAdapter,
    StorageAdapter,
)
from app.config import get_settings

logger = structlog.get_logger(__name__)


def get_storage_adapter() -> StorageAdapter:
    """
    Return the appropriate StorageAdapter implementation for the configured cloud provider.

    GCP  → ``adapters.gcp.storage.GCSStorageAdapter``
    AWS  → ``adapters.aws.storage.S3StorageAdapter``  [Stage 2]
    """
    settings = get_settings()
    provider = settings.cloud_provider

    if provider == "gcp":
        # Lazy import — avoids loading GCP SDK in AWS deployments
        from app.adapters.gcp.storage import GCSStorageAdapter  # type: ignore[import]
        logger.debug("adapter_selected", adapter="GCSStorageAdapter", provider="gcp")
        return GCSStorageAdapter(
            bucket_name=settings.gcs_bucket_name,
            project_id=settings.gcp_project_id,
        )

    if provider == "aws":
        # Stage 2: implement adapters/aws/storage.py
        from app.adapters.aws.storage import S3StorageAdapter  # type: ignore[import]
        logger.debug("adapter_selected", adapter="S3StorageAdapter", provider="aws")
        return S3StorageAdapter()

    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider!r}. Must be 'gcp' or 'aws'.")


def get_kv_store() -> KeyValueStore:
    """
    Return the appropriate KeyValueStore implementation.

    GCP  → ``adapters.gcp.firestore.FirestoreKVStore``
    AWS  → ``adapters.aws.dynamodb.DynamoDBKVStore``  [Stage 2]
    """
    settings = get_settings()
    provider = settings.cloud_provider

    if provider == "gcp":
        from app.adapters.gcp.firestore import FirestoreKVStore  # type: ignore[import]
        logger.debug("adapter_selected", adapter="FirestoreKVStore", provider="gcp")
        return FirestoreKVStore(project_id=settings.gcp_project_id)

    if provider == "aws":
        from app.adapters.aws.dynamodb import DynamoDBKVStore  # type: ignore[import]
        logger.debug("adapter_selected", adapter="DynamoDBKVStore", provider="aws")
        return DynamoDBKVStore()

    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider!r}.")


def get_secrets_adapter() -> SecretsAdapter:
    """
    Return the appropriate SecretsAdapter implementation.

    GCP  → ``adapters.gcp.secrets.GCPSecretsAdapter``
    AWS  → ``adapters.aws.secrets.AWSSecretsAdapter``  [Stage 2]
    """
    settings = get_settings()
    provider = settings.cloud_provider

    if provider == "gcp":
        from app.adapters.gcp.secrets import GCPSecretsAdapter  # type: ignore[import]
        logger.debug("adapter_selected", adapter="GCPSecretsAdapter", provider="gcp")
        return GCPSecretsAdapter(
            project_id=settings.gcp_project_id,
            secret_prefix=f"msme-healthcard-{settings.app_env}",
        )

    if provider == "aws":
        from app.adapters.aws.secrets import AWSSecretsAdapter  # type: ignore[import]
        logger.debug("adapter_selected", adapter="AWSSecretsAdapter", provider="aws")
        return AWSSecretsAdapter()

    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider!r}.")


def get_event_publisher() -> EventPublisher:
    """
    Return the appropriate EventPublisher implementation.

    GCP  → ``adapters.gcp.pubsub.GCPEventPublisher``
    AWS  → ``adapters.aws.sns.SNSEventPublisher``  [Stage 2]
    """
    settings = get_settings()
    provider = settings.cloud_provider

    if provider == "gcp":
        from app.adapters.gcp.pubsub import GCPEventPublisher  # type: ignore[import]
        logger.debug("adapter_selected", adapter="GCPEventPublisher", provider="gcp")
        return GCPEventPublisher(project_id=settings.gcp_project_id)

    if provider == "aws":
        from app.adapters.aws.sns import SNSEventPublisher  # type: ignore[import]
        logger.debug("adapter_selected", adapter="SNSEventPublisher", provider="aws")
        return SNSEventPublisher()

    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider!r}.")


def get_event_subscriber() -> EventSubscriber:
    """
    Return the appropriate EventSubscriber implementation.

    GCP  → ``adapters.gcp.pubsub.GCPEventSubscriber``
    AWS  → ``adapters.aws.sqs.SQSEventSubscriber``  [Stage 2]
    """
    settings = get_settings()
    provider = settings.cloud_provider

    if provider == "gcp":
        from app.adapters.gcp.pubsub import GCPEventSubscriber  # type: ignore[import]
        logger.debug("adapter_selected", adapter="GCPEventSubscriber", provider="gcp")
        return GCPEventSubscriber(project_id=settings.gcp_project_id)

    if provider == "aws":
        from app.adapters.aws.sqs import SQSEventSubscriber  # type: ignore[import]
        logger.debug("adapter_selected", adapter="SQSEventSubscriber", provider="aws")
        return SQSEventSubscriber()

    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider!r}.")
