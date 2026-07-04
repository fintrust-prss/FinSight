"""
GCP Secret Manager Adapter — Stage 1 implementation.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

import structlog
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound

from app.adapters.base import SecretsAdapter
from app.adapters.exceptions import SecretNotFoundError, SecretsError

logger = structlog.get_logger(__name__)


class GCPSecretsAdapter(SecretsAdapter):
    """
    Google Cloud Secret Manager implementation of SecretsAdapter.

    Args:
        project_id: GCP project ID.
        secret_prefix: Prefix prepended to all secret names
                       (e.g. ``"msme-healthcard-dev"``).
    """

    def __init__(self, project_id: str, secret_prefix: str) -> None:
        self._project_id = project_id
        self._secret_prefix = secret_prefix
        self._client: secretmanager.SecretManagerServiceClient | None = None

    def _get_client(self) -> secretmanager.SecretManagerServiceClient:
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def _full_name(self, name: str, version: str) -> str:
        """Build the full Secret Manager resource name."""
        return (
            f"projects/{self._project_id}/secrets/"
            f"{self._secret_prefix}-{name}/versions/{version}"
        )

    async def _run_in_executor(self, fn: Any, *args: Any) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args))

    async def get_secret(self, name: str, version: str = "latest") -> str:
        full_name = self._full_name(name, version)

        def _access() -> str:
            try:
                response = self._get_client().access_secret_version(
                    request={"name": full_name}
                )
                payload: str = response.payload.data.decode("utf-8")
                logger.debug("secret_accessed", name=name, version=version)
                return payload
            except NotFound as exc:
                raise SecretNotFoundError(
                    f"Secret {name!r} (version={version}) not found in Secret Manager"
                ) from exc

        try:
            return await self._run_in_executor(_access)
        except SecretNotFoundError:
            raise
        except Exception as exc:
            raise SecretsError(f"Failed to access secret {name!r}: {exc}", cause=exc) from exc

    async def create_or_update_secret(self, name: str, value: str) -> None:
        secret_id = f"{self._secret_prefix}-{name}"
        parent = f"projects/{self._project_id}"

        def _create_version() -> None:
            client = self._get_client()
            secret_path = f"{parent}/secrets/{secret_id}"

            # Try to add a version; if secret doesn't exist, create it first
            try:
                client.add_secret_version(
                    request={
                        "parent": secret_path,
                        "payload": {"data": value.encode("utf-8")},
                    }
                )
            except NotFound:
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
                client.add_secret_version(
                    request={
                        "parent": secret_path,
                        "payload": {"data": value.encode("utf-8")},
                    }
                )
            logger.info("secret_updated", name=name)

        try:
            await self._run_in_executor(_create_version)
        except Exception as exc:
            raise SecretsError(f"Failed to create/update secret {name!r}: {exc}", cause=exc) from exc
