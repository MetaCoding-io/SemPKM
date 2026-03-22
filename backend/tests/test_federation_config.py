"""Unit tests for federation_config.py — load/save/merge with atomic writes."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.sparql.federation_config import (
    FederationEndpoints,
    add_endpoint,
    get_merged_endpoints,
    load_federation_endpoints,
    remove_endpoint,
    save_federation_endpoints,
)


@pytest.fixture
def tmp_federation_path(tmp_path):
    """Return a temporary path for federation config."""
    return tmp_path / ".federation-endpoints.json"


def _patch_env_endpoints(endpoints: list[str]):
    """Return a context manager that patches settings.get_allowed_endpoints()."""
    mock_settings = type("MockSettings", (), {"get_allowed_endpoints": lambda self: endpoints})()
    return patch("app.sparql.federation_config.settings", mock_settings)


class TestLoadFederationEndpoints:
    def test_absent_file_returns_empty(self, tmp_federation_path):
        result = load_federation_endpoints(tmp_federation_path)
        assert result.endpoints == []
        assert result.updated_at == ""

    def test_valid_file_loads(self, tmp_federation_path):
        data = {
            "endpoints": ["https://dbpedia.org/sparql", "https://wikidata.org/sparql"],
            "updated_at": "2026-03-22T00:00:00+00:00",
        }
        tmp_federation_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_federation_endpoints(tmp_federation_path)
        assert len(result.endpoints) == 2
        assert "https://dbpedia.org/sparql" in result.endpoints

    def test_malformed_json_returns_empty(self, tmp_federation_path):
        tmp_federation_path.write_text("{bad json", encoding="utf-8")
        result = load_federation_endpoints(tmp_federation_path)
        assert result.endpoints == []

    def test_empty_file_returns_empty(self, tmp_federation_path):
        tmp_federation_path.write_text("", encoding="utf-8")
        result = load_federation_endpoints(tmp_federation_path)
        assert result.endpoints == []

    def test_invalid_schema_returns_empty(self, tmp_federation_path):
        # Valid JSON but wrong shape
        tmp_federation_path.write_text('{"foo": "bar"}', encoding="utf-8")
        result = load_federation_endpoints(tmp_federation_path)
        # Pydantic will use defaults for missing fields
        assert result.endpoints == []


class TestSaveFederationEndpoints:
    def test_save_creates_file(self, tmp_federation_path):
        config = FederationEndpoints(
            endpoints=["https://example.org/sparql"],
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        save_federation_endpoints(config, tmp_federation_path)
        assert tmp_federation_path.is_file()
        loaded = json.loads(tmp_federation_path.read_text(encoding="utf-8"))
        assert loaded["endpoints"] == ["https://example.org/sparql"]

    def test_save_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / ".federation-endpoints.json"
        config = FederationEndpoints(endpoints=[], updated_at="")
        save_federation_endpoints(config, deep_path)
        assert deep_path.is_file()

    def test_round_trip(self, tmp_federation_path):
        original = FederationEndpoints(
            endpoints=["https://a.org/sparql", "https://b.org/sparql"],
            updated_at="2026-01-01T00:00:00+00:00",
        )
        save_federation_endpoints(original, tmp_federation_path)
        loaded = load_federation_endpoints(tmp_federation_path)
        assert loaded.endpoints == original.endpoints
        assert loaded.updated_at == original.updated_at

    def test_atomic_write_no_tmp_left(self, tmp_federation_path):
        config = FederationEndpoints(endpoints=["https://x.org/sparql"], updated_at="")
        save_federation_endpoints(config, tmp_federation_path)
        # Temp file should not linger
        assert not tmp_federation_path.with_suffix(".tmp").exists()


class TestGetMergedEndpoints:
    def test_env_only(self, tmp_federation_path):
        with _patch_env_endpoints(["https://env.org/sparql"]):
            result = get_merged_endpoints(tmp_federation_path)
            assert len(result) == 1
            assert result[0]["url"] == "https://env.org/sparql"
            assert result[0]["source"] == "env"
            assert result[0]["removable"] is False

    def test_admin_only(self, tmp_federation_path):
        config = FederationEndpoints(
            endpoints=["https://admin.org/sparql"],
            updated_at="2026-01-01T00:00:00+00:00",
        )
        save_federation_endpoints(config, tmp_federation_path)

        with _patch_env_endpoints([]):
            result = get_merged_endpoints(tmp_federation_path)
            assert len(result) == 1
            assert result[0]["source"] == "admin"
            assert result[0]["removable"] is True

    def test_merge_deduplicates_env_wins(self, tmp_federation_path):
        config = FederationEndpoints(
            endpoints=["https://shared.org/sparql", "https://admin-only.org/sparql"],
            updated_at="",
        )
        save_federation_endpoints(config, tmp_federation_path)

        with _patch_env_endpoints(["https://shared.org/sparql"]):
            result = get_merged_endpoints(tmp_federation_path)
            urls = {r["url"] for r in result}
            assert urls == {"https://shared.org/sparql", "https://admin-only.org/sparql"}
            # The shared URL should be env-sourced (env wins)
            shared = next(r for r in result if r["url"] == "https://shared.org/sparql")
            assert shared["source"] == "env"
            assert shared["removable"] is False

    def test_empty_when_nothing_configured(self, tmp_federation_path):
        with _patch_env_endpoints([]):
            result = get_merged_endpoints(tmp_federation_path)
            assert result == []


class TestAddEndpoint:
    def test_add_new_endpoint(self, tmp_federation_path):
        with _patch_env_endpoints([]):
            result = add_endpoint("https://new.org/sparql", tmp_federation_path)
            assert any(e["url"] == "https://new.org/sparql" for e in result)

    def test_add_duplicate_is_idempotent(self, tmp_federation_path):
        with _patch_env_endpoints([]):
            add_endpoint("https://dup.org/sparql", tmp_federation_path)
            result = add_endpoint("https://dup.org/sparql", tmp_federation_path)
            count = sum(1 for e in result if e["url"] == "https://dup.org/sparql")
            assert count == 1


class TestRemoveEndpoint:
    def test_remove_admin_endpoint(self, tmp_federation_path):
        with _patch_env_endpoints([]):
            add_endpoint("https://removeme.org/sparql", tmp_federation_path)
            result = remove_endpoint("https://removeme.org/sparql", tmp_federation_path)
            assert not any(e["url"] == "https://removeme.org/sparql" for e in result)

    def test_remove_env_endpoint_raises(self, tmp_federation_path):
        with _patch_env_endpoints(["https://env-locked.org/sparql"]):
            with pytest.raises(ValueError, match="Cannot remove env-var endpoint"):
                remove_endpoint("https://env-locked.org/sparql", tmp_federation_path)

    def test_remove_nonexistent_raises(self, tmp_federation_path):
        with _patch_env_endpoints([]):
            with pytest.raises(ValueError, match="Endpoint not found"):
                remove_endpoint("https://ghost.org/sparql", tmp_federation_path)
