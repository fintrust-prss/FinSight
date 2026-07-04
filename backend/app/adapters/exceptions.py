"""
Adapter Exceptions — standardized error types for all adapter implementations.

Services catch these exceptions, not provider-specific SDK exceptions,
ensuring business logic remains cloud-agnostic.
"""

from __future__ import annotations


class AdapterError(Exception):
    """Base class for all adapter errors."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


# ---- Storage ----

class StorageError(AdapterError):
    """Raised when a storage operation fails."""


class StorageNotFoundError(StorageError):
    """Raised when a requested object does not exist in storage."""


# ---- KeyValue Store ----

class KVStoreError(AdapterError):
    """Raised when a key-value store operation fails."""


# ---- Secrets ----

class SecretsError(AdapterError):
    """Raised when a secrets management operation fails."""


class SecretNotFoundError(SecretsError):
    """Raised when a requested secret does not exist."""


# ---- Events ----

class EventPublisherError(AdapterError):
    """Raised when publishing an event fails."""


class EventSubscriberError(AdapterError):
    """Raised when consuming an event fails."""
