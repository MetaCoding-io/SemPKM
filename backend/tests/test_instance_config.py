"""Tests for instance configuration module, setup endpoint, and config priority chain.

Covers:
- InstanceConfig model creation and serialization
- generate_instance_id() UUID validity
- save/load round-trip and atomic write behaviour
- load_instance_config() graceful handling of missing/malformed files
- Config priority chain (env var > instance config > default)
- POST /api/setup/configure-instance endpoint (all three modes)
- Domain validation (protocol prefix rejection, empty string, valid hostname)
- 409 Conflict when user data exists
- StatusResponse includes instance_configured field
"""

import json
import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.instance_config import (
    DEFAULT_CONFIG_PATH,
    InstanceConfig,
    generate_instance_id,
    load_instance_config,
    save_instance_config,
)


# ---------------------------------------------------------------------------
# InstanceConfig model tests
# ---------------------------------------------------------------------------


class TestInstanceConfigModel:
    """Tests for the InstanceConfig Pydantic model."""

    def test_create_local_config(self):
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="local",
            base_namespace="urn:sempkm:test-uuid/",
            app_base_url="http://localhost:3000",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        assert config.instance_id == "test-uuid"
        assert config.deployment_mode == "local"
        assert config.base_namespace == "urn:sempkm:test-uuid/"
        assert config.app_base_url == "http://localhost:3000"

    def test_create_domain_config(self):
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="domain",
            base_namespace="https://sempkm.example.com/data/",
            app_base_url="https://sempkm.example.com",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        assert config.deployment_mode == "domain"
        assert config.base_namespace == "https://sempkm.example.com/data/"

    def test_create_later_config(self):
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="later",
            base_namespace="urn:sempkm:test-uuid/",
            app_base_url="",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        assert config.deployment_mode == "later"
        assert config.app_base_url == ""

    def test_invalid_deployment_mode_rejected(self):
        with pytest.raises(ValueError):
            InstanceConfig(
                instance_id="test-uuid",
                deployment_mode="invalid",
                base_namespace="urn:sempkm:test/",
                app_base_url="",
                configured_at="2026-03-22T00:00:00+00:00",
            )

    def test_serialization_round_trip(self):
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="local",
            base_namespace="urn:sempkm:test-uuid/",
            app_base_url="http://localhost:3000",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        json_str = config.model_dump_json()
        restored = InstanceConfig.model_validate_json(json_str)
        assert restored == config


# ---------------------------------------------------------------------------
# generate_instance_id tests
# ---------------------------------------------------------------------------


class TestGenerateInstanceId:
    """Tests for the generate_instance_id function."""

    def test_returns_valid_uuid_string(self):
        instance_id = generate_instance_id()
        # Should not raise
        parsed = uuid.UUID(instance_id)
        assert str(parsed) == instance_id

    def test_returns_unique_ids(self):
        ids = {generate_instance_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# save/load round-trip tests
# ---------------------------------------------------------------------------


class TestSaveLoadConfig:
    """Tests for save_instance_config and load_instance_config."""

    def _make_config(self, instance_id: str = "test-uuid") -> InstanceConfig:
        return InstanceConfig(
            instance_id=instance_id,
            deployment_mode="local",
            base_namespace=f"urn:sempkm:{instance_id}/",
            app_base_url="http://localhost:3000",
            configured_at="2026-03-22T00:00:00+00:00",
        )

    def test_round_trip(self, tmp_path):
        config = self._make_config()
        path = tmp_path / ".instance-config.json"
        save_instance_config(config, path=path)
        loaded = load_instance_config(path=path)
        assert loaded is not None
        assert loaded == config

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "config.json"
        config = self._make_config()
        save_instance_config(config, path=path)
        assert path.exists()
        loaded = load_instance_config(path=path)
        assert loaded == config

    def test_load_returns_none_for_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        result = load_instance_config(path=path)
        assert result is None

    def test_load_returns_none_for_malformed_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("this is not json {{{{", encoding="utf-8")
        result = load_instance_config(path=path)
        assert result is None

    def test_load_returns_none_for_invalid_schema(self, tmp_path):
        path = tmp_path / "wrong-schema.json"
        path.write_text('{"foo": "bar"}', encoding="utf-8")
        result = load_instance_config(path=path)
        assert result is None

    def test_atomic_write_no_tmp_leftover(self, tmp_path):
        """After a successful save, no .tmp file should remain."""
        config = self._make_config()
        path = tmp_path / "config.json"
        save_instance_config(config, path=path)
        tmp_file = path.with_suffix(".tmp")
        assert not tmp_file.exists()
        assert path.exists()

    def test_file_is_valid_json(self, tmp_path):
        """The saved file should be parseable JSON with expected keys."""
        config = self._make_config()
        path = tmp_path / "config.json"
        save_instance_config(config, path=path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["instance_id"] == "test-uuid"
        assert data["deployment_mode"] == "local"

    def test_overwrite_existing_config(self, tmp_path):
        """Saving twice should overwrite cleanly."""
        path = tmp_path / "config.json"
        config1 = self._make_config("uuid-1")
        config2 = self._make_config("uuid-2")
        save_instance_config(config1, path=path)
        save_instance_config(config2, path=path)
        loaded = load_instance_config(path=path)
        assert loaded is not None
        assert loaded.instance_id == "uuid-2"


# ---------------------------------------------------------------------------
# Config priority chain tests
# ---------------------------------------------------------------------------


class TestConfigPriorityChain:
    """Tests for the config priority chain in config.py.

    Priority: explicit env var > instance config > Pydantic default.
    """

    def test_default_when_no_env_no_config(self):
        """With no env var and no instance config, the Pydantic default wins."""
        from app.config import Settings
        s = Settings(secret_key="test")
        assert s.base_namespace == "https://example.org/data/"
        assert s.app_base_url == ""

    def test_instance_config_overrides_default(self, tmp_path, monkeypatch):
        """Instance config wins over Pydantic default when env var is absent."""
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="local",
            base_namespace="urn:sempkm:test-uuid/",
            app_base_url="http://localhost:3000",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        config_path = tmp_path / ".instance-config.json"
        save_instance_config(config, path=config_path)

        # Remove env vars so they don't win
        monkeypatch.delenv("BASE_NAMESPACE", raising=False)
        monkeypatch.delenv("APP_BASE_URL", raising=False)

        from app.config import Settings, _apply_instance_config_overrides

        s = Settings(secret_key="test")
        # Patch load_instance_config to use our tmp path
        with patch(
            "app.instance_config.load_instance_config",
            return_value=load_instance_config(config_path),
        ):
            # Reset settings values to defaults first
            object.__setattr__(s, "base_namespace", "https://example.org/data/")
            object.__setattr__(s, "app_base_url", "")
            with patch("app.config.settings", s):
                _apply_instance_config_overrides()
        assert s.base_namespace == "urn:sempkm:test-uuid/"
        assert s.app_base_url == "http://localhost:3000"

    def test_env_var_overrides_instance_config(self, tmp_path, monkeypatch):
        """Explicit env var wins over instance config."""
        config = InstanceConfig(
            instance_id="test-uuid",
            deployment_mode="local",
            base_namespace="urn:sempkm:test-uuid/",
            app_base_url="http://localhost:3000",
            configured_at="2026-03-22T00:00:00+00:00",
        )
        config_path = tmp_path / ".instance-config.json"
        save_instance_config(config, path=config_path)

        monkeypatch.setenv("BASE_NAMESPACE", "https://override.example.com/data/")
        monkeypatch.setenv("APP_BASE_URL", "https://override.example.com")

        from app.config import Settings, _apply_instance_config_overrides

        s = Settings(secret_key="test")
        with patch(
            "app.instance_config.load_instance_config",
            return_value=load_instance_config(config_path),
        ):
            object.__setattr__(s, "base_namespace", "https://override.example.com/data/")
            object.__setattr__(s, "app_base_url", "https://override.example.com")
            with patch("app.config.settings", s):
                _apply_instance_config_overrides()
        # Env var should win
        assert s.base_namespace == "https://override.example.com/data/"
        assert s.app_base_url == "https://override.example.com"


# ---------------------------------------------------------------------------
# Setup endpoint tests
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with the setup router for testing."""
    from app.api.setup_routes import setup_router

    test_app = FastAPI()
    test_app.include_router(setup_router)

    # Fake triplestore client on app state
    mock_client = MagicMock()
    mock_client.query = AsyncMock(return_value={"boolean": False})
    test_app.state.triplestore_client = mock_client

    # Setup mode must be active for configure-instance to succeed
    test_app.state.setup_mode = True

    return test_app


class TestConfigureInstanceEndpoint:
    """Tests for POST /api/setup/configure-instance."""

    @pytest_asyncio.fixture
    async def client(self, tmp_path, monkeypatch):
        """Provide an async test client with instance config path overridden."""
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        app = _make_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_local_mode(self, client, tmp_path, monkeypatch):
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_namespace"].startswith("urn:sempkm:")
        assert data["base_namespace"].endswith("/")
        assert data["app_base_url"] == "http://localhost:3000"
        assert data["instance_id"]
        # Verify config was persisted
        loaded = load_instance_config(path=config_path)
        assert loaded is not None
        assert loaded.deployment_mode == "local"

    @pytest.mark.asyncio
    async def test_domain_mode(self, client, tmp_path, monkeypatch):
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": "sempkm.example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_namespace"] == "https://sempkm.example.com/data/"
        assert data["app_base_url"] == "https://sempkm.example.com"

    @pytest.mark.asyncio
    async def test_later_mode(self, client, tmp_path, monkeypatch):
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "later"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_namespace"].startswith("urn:sempkm:")
        assert data["app_base_url"] == ""

    @pytest.mark.asyncio
    async def test_domain_mode_requires_domain(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain"},
        )
        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_domain_rejects_protocol_prefix(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": "https://example.com"},
        )
        assert resp.status_code == 400
        assert "protocol" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_domain_rejects_http_prefix(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": "http://example.com"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_domain_rejects_empty_string(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": ""},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_domain_rejects_invalid_hostname(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": "-invalid-.com"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_mode_rejected(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "invalid"},
        )
        assert resp.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_409_when_user_data_exists(self, tmp_path, monkeypatch):
        """Endpoint returns 409 when triplestore has user data."""
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )

        app = _make_test_app()
        # Override mock to return True (user data exists)
        app.state.triplestore_client.query = AsyncMock(
            return_value={"boolean": True}
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/setup/configure-instance",
                json={"mode": "local"},
            )
        assert resp.status_code == 409
        assert "user data" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_preserves_existing_instance_id(self, client, tmp_path, monkeypatch):
        """If config already exists, the existing instance_id is preserved."""
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )

        # First call — creates config
        resp1 = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "local"},
        )
        first_id = resp1.json()["instance_id"]

        # Second call — should preserve the same instance_id
        resp2 = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "later"},
        )
        assert resp2.json()["instance_id"] == first_id

    @pytest.mark.asyncio
    async def test_domain_accepts_subdomain(self, client):
        resp = await client.post(
            "/api/setup/configure-instance",
            json={"mode": "domain", "domain": "my.sempkm.example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["base_namespace"] == "https://my.sempkm.example.com/data/"

    @pytest.mark.asyncio
    async def test_403_when_setup_mode_inactive(self, tmp_path, monkeypatch):
        """Return 403 when setup_mode is not active (post-setup)."""
        config_path = tmp_path / ".instance-config.json"
        monkeypatch.setattr(
            "app.instance_config.DEFAULT_CONFIG_PATH", config_path
        )
        # Create app with setup_mode OFF
        from app.api.setup_routes import setup_router
        test_app = FastAPI()
        test_app.include_router(setup_router)
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={"boolean": False})
        test_app.state.triplestore_client = mock_client
        test_app.state.setup_mode = False

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/setup/configure-instance",
                json={"mode": "local"},
            )
            assert resp.status_code == 403
            assert "setup mode" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# StatusResponse instance_configured field tests
# ---------------------------------------------------------------------------


class TestStatusResponseInstanceConfigured:
    """Tests that GET /api/auth/status includes instance_configured."""

    def test_status_response_has_instance_configured_field(self):
        from app.auth.schemas import StatusResponse
        resp = StatusResponse(
            setup_complete=True,
            setup_mode=False,
            instance_configured=True,
        )
        assert resp.instance_configured is True

    def test_status_response_instance_configured_false(self):
        from app.auth.schemas import StatusResponse
        resp = StatusResponse(
            setup_complete=False,
            setup_mode=True,
            instance_configured=False,
        )
        assert resp.instance_configured is False
