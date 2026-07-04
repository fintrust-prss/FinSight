"""
Phase 0 Test Suite — Adapter Interface Smoke Tests.

These tests verify:
1. The abstract adapter interfaces cannot be instantiated directly.
2. The factory correctly selects adapters based on CLOUD_PROVIDER.
3. The AWS stub adapters raise NotImplementedError (not silently pass).
4. Settings load correctly from environment.
5. The FastAPI app starts and /healthz returns 200.

Note: Phase 2 will add integration tests against real adapter implementations
(GCS, Firestore, Pub/Sub, Secret Manager) using a local emulator or test containers.
"""

from __future__ import annotations

import os
import pytest

from unittest.mock import patch


# ==============================================================
# 1. Adapter interfaces are abstract (cannot instantiate directly)
# ==============================================================

class TestAdapterAbstractInterfaces:
    """Verify abstract base classes cannot be instantiated."""

    def test_storage_adapter_is_abstract(self) -> None:
        from app.adapters.base import StorageAdapter
        with pytest.raises(TypeError, match="abstract"):
            StorageAdapter()  # type: ignore[abstract]

    def test_kv_store_is_abstract(self) -> None:
        from app.adapters.base import KeyValueStore
        with pytest.raises(TypeError, match="abstract"):
            KeyValueStore()  # type: ignore[abstract]

    def test_secrets_adapter_is_abstract(self) -> None:
        from app.adapters.base import SecretsAdapter
        with pytest.raises(TypeError, match="abstract"):
            SecretsAdapter()  # type: ignore[abstract]

    def test_event_publisher_is_abstract(self) -> None:
        from app.adapters.base import EventPublisher
        with pytest.raises(TypeError, match="abstract"):
            EventPublisher()  # type: ignore[abstract]

    def test_event_subscriber_is_abstract(self) -> None:
        from app.adapters.base import EventSubscriber
        with pytest.raises(TypeError, match="abstract"):
            EventSubscriber()  # type: ignore[abstract]


# ==============================================================
# 2. AWS stub adapters raise NotImplementedError
# ==============================================================

class TestAWSStubAdapters:
    """Verify AWS stubs raise NotImplementedError (not silently fail)."""

    def test_s3_storage_adapter_raises_not_implemented(self) -> None:
        from app.adapters.aws.storage import S3StorageAdapter
        with pytest.raises(NotImplementedError, match="Stage 2"):
            S3StorageAdapter()


# ==============================================================
# 3. Adapter factory — provider selection logic
# ==============================================================

class TestAdapterFactory:
    """Verify the factory returns the correct adapter type."""

    @patch.dict(os.environ, {"CLOUD_PROVIDER": "aws"}, clear=False)
    def test_factory_raises_on_aws_storage(self) -> None:
        """AWS factory call raises NotImplementedError (stubs not implemented)."""
        from app.config import get_settings
        get_settings.cache_clear()

        from app.adapters.factory import get_storage_adapter
        with pytest.raises(NotImplementedError):
            get_storage_adapter()

    @patch.dict(os.environ, {"CLOUD_PROVIDER": "invalid_provider"}, clear=False)
    def test_factory_raises_on_unknown_provider(self) -> None:
        """Factory raises ValueError for unrecognized cloud provider."""
        from app.config import get_settings
        get_settings.cache_clear()

        # We need to bypass pydantic validation which would also reject "invalid_provider"
        # So we mock settings directly
        from unittest.mock import MagicMock
        mock_settings = MagicMock()
        mock_settings.cloud_provider = "invalid_provider"

        with patch("app.adapters.factory.get_settings", return_value=mock_settings):
            from app.adapters.factory import get_storage_adapter
            with pytest.raises(ValueError, match="Unsupported CLOUD_PROVIDER"):
                get_storage_adapter()


# ==============================================================
# 4. Settings load correctly
# ==============================================================

class TestSettings:
    """Verify Pydantic settings load and validate correctly."""

    def setup_method(self) -> None:
        from app.config import get_settings
        get_settings.cache_clear()

    def test_default_cloud_provider_is_gcp(self) -> None:
        with patch.dict(os.environ, {
            "CLOUD_PROVIDER": "gcp",
            "JWT_SECRET_KEY": "test_secret",
        }, clear=False):
            from app.config import get_settings
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.cloud_provider == "gcp"

    def test_database_url_construction(self) -> None:
        with patch.dict(os.environ, {
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
        }, clear=False):
            from app.config import get_settings
            get_settings.cache_clear()
            settings = get_settings()
            assert "testuser" in settings.database_url
            assert "testdb" in settings.database_url
            assert "asyncpg" in settings.database_url

    def test_cors_origins_parsed_from_comma_string(self) -> None:
        with patch.dict(os.environ, {
            "CORS_ALLOWED_ORIGINS": "http://localhost:5173,http://localhost:3000",
        }, clear=False):
            from app.config import get_settings
            get_settings.cache_clear()
            settings = get_settings()
            assert "http://localhost:5173" in settings.cors_allowed_origins_list
            assert "http://localhost:3000" in settings.cors_allowed_origins_list


# ==============================================================
# 5. FastAPI application health check
# ==============================================================

class TestHealthEndpoint:
    """Verify the FastAPI app starts and /healthz responds correctly."""

    def test_healthz_returns_200(self) -> None:
        """GET /healthz should return 200 with status: ok."""
        from starlette.testclient import TestClient
        from app.main import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/healthz")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "ok"
        assert body["error"] is None
        assert "version" in body["data"]

    def test_healthz_response_has_correct_envelope(self) -> None:
        """All API responses must follow the standard envelope format."""
        from starlette.testclient import TestClient
        from app.main import create_app

        app = create_app()
        with TestClient(app) as client:
            response = client.get("/healthz")

        body = response.json()
        # Standard envelope: { data, meta, error }
        assert "data" in body
        assert "meta" in body
        assert "error" in body

    def test_openapi_docs_accessible(self) -> None:
        """OpenAPI spec should be accessible at /openapi.json."""
        from starlette.testclient import TestClient
        from app.main import create_app

        app = create_app()
        with TestClient(app) as client:
            response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "MSME Financial Health Card API"

    def test_cors_headers_present(self) -> None:
        """CORS response headers should be present on cross-origin GET requests."""
        from starlette.testclient import TestClient
        from app.main import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/healthz",
                headers={"Origin": "http://localhost:5173"},
            )
        # The response should succeed and carry CORS allow-origin header
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


# ==============================================================
# 6. Adapter exception hierarchy
# ==============================================================

class TestAdapterExceptions:
    """Verify the exception hierarchy is correct."""

    def test_storage_not_found_is_storage_error(self) -> None:
        from app.adapters.exceptions import StorageNotFoundError, StorageError, AdapterError
        exc = StorageNotFoundError("not found")
        assert isinstance(exc, StorageError)
        assert isinstance(exc, AdapterError)

    def test_secret_not_found_is_secrets_error(self) -> None:
        from app.adapters.exceptions import SecretNotFoundError, SecretsError, AdapterError
        exc = SecretNotFoundError("not found")
        assert isinstance(exc, SecretsError)
        assert isinstance(exc, AdapterError)

    def test_adapter_error_stores_cause(self) -> None:
        from app.adapters.exceptions import StorageError
        cause = ValueError("original error")
        exc = StorageError("wrapped", cause=cause)
        assert exc.cause is cause
