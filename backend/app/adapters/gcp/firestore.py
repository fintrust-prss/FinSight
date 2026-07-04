"""
GCP Firestore Key-Value Store Adapter — Stage 1 implementation.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

import structlog
from google.cloud import firestore

from app.adapters.base import KeyValueStore
from app.adapters.exceptions import KVStoreError

logger = structlog.get_logger(__name__)


class FirestoreKVStore(KeyValueStore):
    """
    Google Cloud Firestore implementation of KeyValueStore.

    Portability constraint: Only uses single-field equality queries
    to ensure clean DynamoDB portability in Stage 2.

    Args:
        project_id: GCP project ID.
    """

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._client: firestore.AsyncClient | None = None

    def _get_client(self) -> firestore.AsyncClient:
        if self._client is None:
            self._client = firestore.AsyncClient(project=self._project_id)
        return self._client

    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        try:
            doc_ref = self._get_client().collection(collection).document(key)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as exc:
            raise KVStoreError(f"Firestore get failed for {collection}/{key}: {exc}", cause=exc) from exc

    async def put(
        self,
        collection: str,
        key: str,
        document: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        try:
            doc_ref = self._get_client().collection(collection).document(key)
            data = dict(document)
            if ttl_seconds is not None:
                import datetime
                data["_ttl"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl_seconds)
            await doc_ref.set(data)
            logger.debug("firestore_put", collection=collection, key=key)
        except Exception as exc:
            raise KVStoreError(f"Firestore put failed for {collection}/{key}: {exc}", cause=exc) from exc

    async def delete(self, collection: str, key: str) -> None:
        try:
            doc_ref = self._get_client().collection(collection).document(key)
            await doc_ref.delete()
            logger.debug("firestore_delete", collection=collection, key=key)
        except Exception as exc:
            raise KVStoreError(f"Firestore delete failed for {collection}/{key}: {exc}", cause=exc) from exc

    async def query_by_field(
        self,
        collection: str,
        field: str,
        value: Any,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Single-field equality query only (portability constraint)."""
        try:
            query = (
                self._get_client()
                .collection(collection)
                .where(field, "==", value)
                .limit(limit)
            )
            docs = query.stream()
            results = []
            async for doc in docs:
                results.append(doc.to_dict())
            return results
        except Exception as exc:
            raise KVStoreError(
                f"Firestore query failed for {collection} where {field}=={value}: {exc}",
                cause=exc,
            ) from exc
