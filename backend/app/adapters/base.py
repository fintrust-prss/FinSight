"""
Cloud-Agnostic Adapter Interfaces — the portability seam.

ADR-001: Every module that touches a cloud SDK must live under
``adapters/gcp/`` or ``adapters/aws/`` and implement the abstract
interfaces defined here.  No business logic, service, or router
module may import a cloud SDK directly.

Stage 2 AWS migration = implement ``adapters/aws/*`` + flip
``CLOUD_PROVIDER=gcp`` → ``CLOUD_PROVIDER=aws``.  Zero changes
to any service/route code.

Interfaces defined here:
  - StorageAdapter   — object storage (GCS ↔ S3)
  - KeyValueStore    — document/cache store (Firestore ↔ DynamoDB)
  - SecretsAdapter   — secrets management (Secret Manager ↔ AWS SM)
  - EventPublisher   — event publishing (Pub/Sub ↔ SNS/SQS)
  - EventSubscriber  — event consuming  (Pub/Sub ↔ SQS)

All methods are async-first to avoid blocking the FastAPI event loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


# ==============================================================
# StorageAdapter — Object Storage
# GCP: google-cloud-storage (GCS)
# AWS: boto3 S3
# ==============================================================

class StorageAdapter(ABC):
    """
    Abstract interface for object (blob) storage operations.

    Implementations:
      - ``adapters.gcp.storage.GCSStorageAdapter``
      - ``adapters.aws.storage.S3StorageAdapter``  [Stage 2]

    Design notes:
      - ``key`` is always a forward-slash path (e.g. ``raw/gst/2024-01.parquet``).
      - ``signed_url`` returns a pre-signed URL valid for ``expires_in`` seconds,
        usable from the frontend without credentials.
      - All methods raise ``StorageError`` on failure (see exceptions.py).
    """

    @abstractmethod
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """
        Upload bytes to object storage.

        Args:
            key: Object path/key within the bucket.
            data: Raw bytes to upload.
            content_type: MIME type of the object.
            metadata: Optional key-value metadata attached to the object.

        Raises:
            StorageError: If the upload fails.
        """
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """
        Download an object by key.

        Args:
            key: Object path/key within the bucket.

        Returns:
            Raw bytes of the object.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If the download fails.
        """
        ...

    @abstractmethod
    async def list(self, prefix: str = "") -> list[str]:
        """
        List object keys under a given prefix.

        Args:
            prefix: Key prefix to filter by (e.g. ``"raw/gst/"``).

        Returns:
            List of full object keys matching the prefix.

        Raises:
            StorageError: If the list operation fails.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete an object by key.

        Args:
            key: Object path/key to delete.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If the delete fails.
        """
        ...

    @abstractmethod
    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for temporary direct access to an object.

        Args:
            key: Object path/key.
            expires_in: URL validity duration in seconds (default: 1 hour).

        Returns:
            Pre-signed HTTPS URL string.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If URL generation fails.
        """
        ...


# ==============================================================
# KeyValueStore — Document / Cache Store
# GCP: Firestore
# AWS: DynamoDB [Stage 2]
# ==============================================================

class KeyValueStore(ABC):
    """
    Abstract interface for a key-value / document store.

    Used for:
      - Session/cache data (e.g., cached score objects)
      - Consent records (when low-latency lookup matters)
      - Feature store hot-path cache

    Implementations:
      - ``adapters.gcp.firestore.FirestoreKVStore``
      - ``adapters.aws.dynamodb.DynamoDBKVStore``  [Stage 2]

    Design constraint:
      Avoid Firestore-specific query features (e.g., complex composite
      indexes, ``array-contains-any``) — only use:
        - ``get``, ``put``, ``delete`` by primary key
        - Simple equality filters on one field (maps to DynamoDB scan)
      This ensures clean portability to DynamoDB.
    """

    @abstractmethod
    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """
        Retrieve a document by collection and key.

        Args:
            collection: Logical collection/table name.
            key: Document primary key.

        Returns:
            Document as a dict, or None if not found.

        Raises:
            KVStoreError: If the read fails unexpectedly.
        """
        ...

    @abstractmethod
    async def put(
        self,
        collection: str,
        key: str,
        document: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Write or overwrite a document.

        Args:
            collection: Logical collection/table name.
            key: Document primary key.
            document: Data to store.
            ttl_seconds: Optional TTL for automatic expiry (supported by both
                Firestore TTL policies and DynamoDB TTL attribute).

        Raises:
            KVStoreError: If the write fails.
        """
        ...

    @abstractmethod
    async def delete(self, collection: str, key: str) -> None:
        """
        Delete a document by collection and key.

        Args:
            collection: Logical collection/table name.
            key: Document primary key.

        Raises:
            KVStoreError: If the delete fails.
        """
        ...

    @abstractmethod
    async def query_by_field(
        self,
        collection: str,
        field: str,
        value: Any,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query documents where a single field equals a value.

        **Portability constraint:** single-field equality only.
        Complex multi-field queries should go through the relational DB
        (repositories layer), not this adapter.

        Args:
            collection: Logical collection/table name.
            field: Field name to filter on.
            value: Value to match.
            limit: Maximum number of documents to return.

        Returns:
            List of matching documents (may be empty).

        Raises:
            KVStoreError: If the query fails.
        """
        ...


# ==============================================================
# SecretsAdapter — Secrets Management
# GCP: Secret Manager
# AWS: AWS Secrets Manager [Stage 2]
# ==============================================================

class SecretsAdapter(ABC):
    """
    Abstract interface for secrets management.

    All secrets must be fetched through this adapter —
    never from environment variables directly in business logic,
    and never hardcoded.

    Implementations:
      - ``adapters.gcp.secrets.GCPSecretsAdapter``
      - ``adapters.aws.secrets.AWSSecretsAdapter``  [Stage 2]
    """

    @abstractmethod
    async def get_secret(self, name: str, version: str = "latest") -> str:
        """
        Retrieve a secret value by name.

        Args:
            name: Secret name (without project/environment prefix —
                the adapter implementation adds the prefix).
            version: Secret version (default: ``"latest"``).

        Returns:
            Secret value as a string (decode bytes if needed in implementation).

        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretsError: If the retrieval fails.
        """
        ...

    @abstractmethod
    async def create_or_update_secret(self, name: str, value: str) -> None:
        """
        Create a new secret or add a new version to an existing one.

        Args:
            name: Secret name (without prefix).
            value: Secret value to store.

        Raises:
            SecretsError: If the operation fails.
        """
        ...


# ==============================================================
# EventPublisher — Event / Message Bus (publish side)
# GCP: Pub/Sub
# AWS: SNS + SQS / EventBridge [Stage 2]
# ==============================================================

class EventPublisher(ABC):
    """
    Abstract interface for publishing events to a message bus.

    Used for:
      - Triggering incremental MSME re-scoring (rescore-events topic)
      - Publishing audit events (audit-events topic)

    Implementations:
      - ``adapters.gcp.pubsub.GCPEventPublisher``
      - ``adapters.aws.sns.SNSEventPublisher``  [Stage 2]
    """

    @abstractmethod
    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        attributes: dict[str, str] | None = None,
    ) -> str:
        """
        Publish an event message to a topic.

        Args:
            topic: Logical topic name (e.g., ``"rescore-events"``).
                The adapter implementation resolves this to the full
                provider-specific topic path.
            payload: JSON-serializable event payload.
            attributes: Optional string key-value metadata attached to the message
                (used for filtering in subscriptions).

        Returns:
            Message ID assigned by the broker.

        Raises:
            EventPublisherError: If publishing fails.
        """
        ...


# ==============================================================
# EventSubscriber — Event / Message Bus (consume side)
# GCP: Pub/Sub pull subscription
# AWS: SQS [Stage 2]
# ==============================================================

class EventSubscriber(ABC):
    """
    Abstract interface for consuming events from a message bus.

    The consuming side is typically a background worker task
    (async loop or Cloud Run Job), not the request-handling path.

    Implementations:
      - ``adapters.gcp.pubsub.GCPEventSubscriber``
      - ``adapters.aws.sqs.SQSEventSubscriber``  [Stage 2]
    """

    @abstractmethod
    async def subscribe(
        self,
        subscription: str,
        batch_size: int = 10,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """
        Pull messages from a subscription as an async iterator.

        Each iteration yields a (message_id, payload) tuple.
        The caller is responsible for calling ``acknowledge`` after
        successfully processing each message.

        Args:
            subscription: Logical subscription name.
            batch_size: Number of messages to pull per batch.

        Yields:
            (message_id, payload) tuples.

        Raises:
            EventSubscriberError: If the pull operation fails.
        """
        ...

    @abstractmethod
    async def acknowledge(self, subscription: str, message_id: str) -> None:
        """
        Acknowledge a successfully processed message (removes it from the queue).

        Args:
            subscription: Logical subscription name.
            message_id: ID of the message to acknowledge.

        Raises:
            EventSubscriberError: If the acknowledge fails.
        """
        ...

    @abstractmethod
    async def nack(self, subscription: str, message_id: str) -> None:
        """
        Negative-acknowledge a message (returns it to the queue for retry).

        Args:
            subscription: Logical subscription name.
            message_id: ID of the message to nack.

        Raises:
            EventSubscriberError: If the nack fails.
        """
        ...
