"""
GCP Cloud Storage Adapter — Stage 1 implementation.

Wraps google-cloud-storage SDK behind the StorageAdapter interface.
No code outside this file should import google.cloud.storage directly.
"""

from __future__ import annotations

import asyncio
import datetime
from functools import partial
from typing import Any

import structlog
from google.cloud import storage
from google.cloud.exceptions import NotFound

from app.adapters.base import StorageAdapter
from app.adapters.exceptions import StorageError, StorageNotFoundError

logger = structlog.get_logger(__name__)


class GCSStorageAdapter(StorageAdapter):
    """
    Google Cloud Storage implementation of StorageAdapter.

    All GCS operations are wrapped in asyncio.get_event_loop().run_in_executor()
    to prevent blocking the FastAPI event loop (GCS SDK is synchronous).

    Args:
        bucket_name: GCS bucket name.
        project_id: GCP project ID.
    """

    def __init__(self, bucket_name: str, project_id: str) -> None:
        self._bucket_name = bucket_name
        self._project_id = project_id
        self._client: storage.Client | None = None

    def _get_client(self) -> storage.Client:
        """Lazy-initialize GCS client (singleton per adapter instance)."""
        if self._client is None:
            self._client = storage.Client(project=self._project_id)
        return self._client

    def _get_bucket(self) -> storage.Bucket:
        return self._get_client().bucket(self._bucket_name)

    async def _run_in_executor(self, fn: Any, *args: Any) -> Any:
        """Run a synchronous GCS call in a thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args))

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload bytes to GCS."""
        def _upload() -> None:
            blob = self._get_bucket().blob(key)
            blob.content_type = content_type
            if metadata:
                blob.metadata = metadata
            blob.upload_from_string(data, content_type=content_type)
            logger.debug("gcs_put", key=key, bytes=len(data))

        try:
            await self._run_in_executor(_upload)
        except Exception as exc:
            raise StorageError(f"Failed to upload {key!r} to GCS: {exc}", cause=exc) from exc

    async def get(self, key: str) -> bytes:
        """Download bytes from GCS."""
        def _download() -> bytes:
            blob = self._get_bucket().blob(key)
            try:
                data: bytes = blob.download_as_bytes()
                logger.debug("gcs_get", key=key, bytes=len(data))
                return data
            except NotFound as exc:
                raise StorageNotFoundError(f"Object {key!r} not found in GCS") from exc

        try:
            return await self._run_in_executor(_download)
        except StorageNotFoundError:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to download {key!r} from GCS: {exc}", cause=exc) from exc

    async def list(self, prefix: str = "") -> list[str]:
        """List object keys in GCS bucket under a prefix."""
        def _list() -> list[str]:
            blobs = self._get_client().list_blobs(self._bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]

        try:
            return await self._run_in_executor(_list)
        except Exception as exc:
            raise StorageError(f"Failed to list GCS objects with prefix {prefix!r}: {exc}", cause=exc) from exc

    async def delete(self, key: str) -> None:
        """Delete an object from GCS."""
        def _delete() -> None:
            blob = self._get_bucket().blob(key)
            try:
                blob.delete()
                logger.debug("gcs_delete", key=key)
            except NotFound as exc:
                raise StorageNotFoundError(f"Object {key!r} not found in GCS") from exc

        try:
            await self._run_in_executor(_delete)
        except StorageNotFoundError:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to delete {key!r} from GCS: {exc}", cause=exc) from exc

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed GCS URL for temporary direct access."""
        def _sign() -> str:
            blob = self._get_bucket().blob(key)
            url: str = blob.generate_signed_url(
                expiration=datetime.timedelta(seconds=expires_in),
                method="GET",
                version="v4",
            )
            return url

        try:
            return await self._run_in_executor(_sign)
        except Exception as exc:
            raise StorageError(f"Failed to generate signed URL for {key!r}: {exc}", cause=exc) from exc
