"""Unit tests for GitHub Sync auth helpers.

Loads ``auth.py`` from the apps directory using importlib. All state and
API interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "github-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"

# Load github_client first (auth.py depends on it for GitHubAuthError)
_GC_PATH = _SERVICES_DIR / "github_client.py"
_AUTH_PATH = _SERVICES_DIR / "auth.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gc = _load_module("github_client", _GC_PATH)
auth = _load_module("github_auth", _AUTH_PATH)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockStateClient:
    """In-memory state client that mimics the SDK StateClient interface."""

    def __init__(self, initial: dict[str, str] | None = None):
        self._store: dict[str, str] = initial or {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


class MockGitHubClient:
    """Mock GitHubClient for auth tests."""

    def __init__(self, verify_result: dict | None = None, verify_error: Exception | None = None):
        self._verify_result = verify_result
        self._verify_error = verify_error

    async def verify_token(self) -> dict:
        if self._verify_error:
            raise self._verify_error
        return self._verify_result or {}


# ===================================================================
# store_pat / get_pat tests
# ===================================================================

class TestStorePat:
    @pytest.mark.asyncio
    async def test_store_pat_writes_to_state(self):
        state = MockStateClient()
        await auth.store_pat(state, "ghp_abc123")
        assert state._store["github_pat"] == "ghp_abc123"

    @pytest.mark.asyncio
    async def test_get_pat_reads_from_state(self):
        state = MockStateClient({"github_pat": "ghp_xyz789"})
        result = await auth.get_pat(state)
        assert result == "ghp_xyz789"

    @pytest.mark.asyncio
    async def test_get_pat_returns_none_when_missing(self):
        state = MockStateClient()
        result = await auth.get_pat(state)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pat_returns_none_for_empty_string(self):
        state = MockStateClient({"github_pat": ""})
        result = await auth.get_pat(state)
        assert result is None


# ===================================================================
# verify_pat tests
# ===================================================================

class TestVerifyPat:
    @pytest.mark.asyncio
    async def test_verify_success_returns_user(self):
        client = MockGitHubClient(verify_result={
            "login": "octocat",
            "name": "Octo Cat",
            "email": "octo@github.com",
        })
        result = await auth.verify_pat(client)
        assert result["login"] == "octocat"
        assert result["name"] == "Octo Cat"

    @pytest.mark.asyncio
    async def test_verify_failure_raises(self):
        client = MockGitHubClient(
            verify_error=gc.GitHubAuthError("bad token", status_code=401)
        )
        with pytest.raises(gc.GitHubAuthError):
            await auth.verify_pat(client)


# ===================================================================
# get_connection_status tests
# ===================================================================

class TestGetConnectionStatus:
    @pytest.mark.asyncio
    async def test_connected_status(self):
        state = MockStateClient({"github_pat": "ghp_abcdefghijklmnop"})
        client = MockGitHubClient(verify_result={"login": "octocat"})
        result = await auth.get_connection_status(state, client)
        assert result["connected"] is True
        assert result["username"] == "octocat"
        assert result["pat_preview"] == "ghp_****mnop"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_disconnected_status_no_pat(self):
        state = MockStateClient()
        client = MockGitHubClient()
        result = await auth.get_connection_status(state, client)
        assert result["connected"] is False
        assert result["username"] is None
        assert result["pat_preview"] is None

    @pytest.mark.asyncio
    async def test_error_status_bad_pat(self):
        state = MockStateClient({"github_pat": "ghp_invalidtoken123"})
        client = MockGitHubClient(
            verify_error=gc.GitHubAuthError("bad token", status_code=401)
        )
        result = await auth.get_connection_status(state, client)
        assert result["connected"] is False
        assert result["pat_preview"] == "ghp_****n123"
        assert "error" in result
        assert "bad token" in result["error"]


# ===================================================================
# PAT masking tests
# ===================================================================

class TestPatMasking:
    def test_standard_pat(self):
        assert auth._mask_pat("ghp_abcdefghijklmnop") == "ghp_****mnop"

    def test_short_pat(self):
        """PATs <= 8 chars show first 4 + ****."""
        assert auth._mask_pat("abcd1234") == "abcd****"

    def test_very_short_pat(self):
        assert auth._mask_pat("abc") == "abc****"

    def test_fine_grained_pat(self):
        """Fine-grained PATs start with github_pat_..."""
        masked = auth._mask_pat("github_pat_abc123def456")
        assert masked.startswith("gith")
        assert masked.endswith("f456")
        assert "****" in masked


# ===================================================================
# disconnect tests
# ===================================================================

class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_clears_key(self):
        state = MockStateClient({"github_pat": "ghp_secret"})
        await auth.disconnect(state)
        assert state._store["github_pat"] == ""

    @pytest.mark.asyncio
    async def test_disconnect_makes_get_pat_return_none(self):
        state = MockStateClient({"github_pat": "ghp_secret"})
        await auth.disconnect(state)
        result = await auth.get_pat(state)
        assert result is None
