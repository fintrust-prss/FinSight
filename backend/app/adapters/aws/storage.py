"""
AWS S3 Storage Adapter — Stage 2 stub.

TODO (Stage 2): Implement using aioboto3 or boto3 behind asyncio.
  pip install aioboto3
  Conform to the StorageAdapter interface in adapters/base.py.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from app.adapters.base import StorageAdapter


class S3StorageAdapter(StorageAdapter):
    """
    Amazon S3 implementation of StorageAdapter.

    Stage 2 task: implement all methods using aioboto3.
    The interface is identical to GCSStorageAdapter — the only change
    is the underlying SDK calls.
    """

    def __init__(self) -> None:
        # Stage 2: initialize aioboto3 session + S3 client here
        raise NotImplementedError(
            "S3StorageAdapter is not yet implemented. "
            "This is a Stage 2 (AWS migration) task. "
            "Set CLOUD_PROVIDER=gcp to use the GCS adapter."
        )

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream", metadata: dict[str, str] | None = None) -> None:
        raise NotImplementedError("Stage 2 task — see adapters/aws/storage.py")

    async def get(self, key: str) -> bytes:
        raise NotImplementedError("Stage 2 task — see adapters/aws/storage.py")

    async def list(self, prefix: str = "") -> list[str]:
        raise NotImplementedError("Stage 2 task — see adapters/aws/storage.py")

    async def delete(self, key: str) -> None:
        raise NotImplementedError("Stage 2 task — see adapters/aws/storage.py")

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("Stage 2 task — see adapters/aws/storage.py")
