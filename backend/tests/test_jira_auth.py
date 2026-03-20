"""Unit tests for Jira Sync auth helpers.

Loads ``auth.py`` from the apps directory using importlib. All state and
API interactions are mocked — no network calls are made.

Uses ``asyncio.run()`` to execute async tests without requiring pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "jira-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"

# Load jira_client first (auth.py depends on it for JiraAuthError)
_JC_PATH = _SERVICES_DIR / "jira_client.py"
_AUTH_PATH = _SERVICES_DIR / "auth.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


jc = _load_module("jira_client", _JC_PATH)
auth = _load_module("jira_auth", _AUTH_PATH)


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


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


class MockJiraClient:
    """Mock JiraClient for auth tests."""

    def __init__(
        self,
        myself_result: dict | None = None,
        myself_error: Exception | None = None,
    ):
        self._myself_result = myself_result
        self._myself_error = myself_error

    async def get_myself(self) -> dict:
        if self._myself_error:
            raise self._myself_error
        return self._myself_result or {}


# ===================================================================
# store_credentials tests
# ===================================================================

class TestStoreCredentials:

    def test_store_credentials_writes_all_keys(self):
        state = MockStateClient()
        _run(auth.store_credentials(
            state, "user@example.com", "my-token", "https://site.atlassian.net"
        ))
        assert state._store["jira_email"] == "user@example.com"
        assert state._store["jira_token"] == "my-token"
        assert state._store["jira_site_url"] == "https://site.atlassian.net"

    def test_store_credentials_overwrites_existing(self):
        state = MockStateClient({
            "jira_email": "old@example.com",
            "jira_token": "old-token",
            "jira_site_url": "https://old.atlassian.net",
        })
        _run(auth.store_credentials(
            state, "new@example.com", "new-token", "https://new.atlassian.net"
        ))
        assert state._store["jira_email"] == "new@example.com"
        assert state._store["jira_token"] == "new-token"
        assert state._store["jira_site_url"] == "https://new.atlassian.net"


# ===================================================================
# get_credentials tests
# ===================================================================

class TestGetCredentials:

    def test_get_credentials_returns_dict(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "my-token",
            "jira_site_url": "https://site.atlassian.net",
        })
        result = _run(auth.get_credentials(state))
        assert result == {
            "email": "user@example.com",
            "token": "my-token",
            "site_url": "https://site.atlassian.net",
        }

    def test_get_credentials_returns_none_when_missing(self):
        state = MockStateClient()
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_get_credentials_returns_none_when_email_empty(self):
        state = MockStateClient({
            "jira_email": "",
            "jira_token": "token",
            "jira_site_url": "https://site.atlassian.net",
        })
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_get_credentials_returns_none_when_token_empty(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "",
            "jira_site_url": "https://site.atlassian.net",
        })
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_get_credentials_returns_none_when_site_url_empty(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "token",
            "jira_site_url": "",
        })
        result = _run(auth.get_credentials(state))
        assert result is None


# ===================================================================
# clear_credentials tests
# ===================================================================

class TestClearCredentials:

    def test_clear_credentials_sets_empty(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "my-token",
            "jira_site_url": "https://site.atlassian.net",
        })
        _run(auth.clear_credentials(state))
        assert state._store["jira_email"] == ""
        assert state._store["jira_token"] == ""
        assert state._store["jira_site_url"] == ""

    def test_clear_credentials_makes_get_return_none(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "my-token",
            "jira_site_url": "https://site.atlassian.net",
        })
        _run(auth.clear_credentials(state))
        result = _run(auth.get_credentials(state))
        assert result is None


# ===================================================================
# _mask_token tests
# ===================================================================

class TestMaskToken:

    def test_standard_token(self):
        assert auth._mask_token("abcdefghijklmnop") == "abcd****mnop"

    def test_short_token(self):
        """Tokens <= 8 chars show first 4 + ****."""
        assert auth._mask_token("abcd1234") == "abcd****"

    def test_very_short_token(self):
        assert auth._mask_token("abc") == "abc****"

    def test_exactly_nine_chars(self):
        """Token of 9 chars shows first 4 + **** + last 4."""
        assert auth._mask_token("123456789") == "1234****6789"

    def test_long_api_token(self):
        """Long Atlassian API tokens are properly masked."""
        token = "ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234"
        masked = auth._mask_token(token)
        assert masked.startswith("ATAT")
        assert masked.endswith("1234")
        assert "****" in masked


# ===================================================================
# build_auth_header tests
# ===================================================================

class TestBuildAuthHeader:

    def test_correct_base64(self):
        result = auth.build_auth_header("user@example.com", "my-token")
        expected = base64.b64encode(b"user@example.com:my-token").decode()
        assert result == f"Basic {expected}"

    def test_decoded_value_matches(self):
        result = auth.build_auth_header("admin@corp.com", "secret123")
        encoded = result.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "admin@corp.com:secret123"

    def test_starts_with_basic(self):
        result = auth.build_auth_header("a@b.com", "t")
        assert result.startswith("Basic ")


# ===================================================================
# get_connection_status tests
# ===================================================================

class TestGetConnectionStatus:

    def test_connected_status(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "abcdefghijklmnop",
            "jira_site_url": "https://site.atlassian.net",
        })
        client = MockJiraClient(myself_result={
            "displayName": "Test User",
            "accountId": "abc123",
        })
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is True
        assert result["email"] == "user@example.com"
        assert result["display_name"] == "Test User"
        assert result["token_preview"] == "abcd****mnop"
        assert result["site_url"] == "https://site.atlassian.net"
        assert "error" not in result

    def test_disconnected_status_no_creds(self):
        state = MockStateClient()
        client = MockJiraClient()
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert result["email"] is None
        assert result["display_name"] is None
        assert result["token_preview"] is None
        assert result["site_url"] is None

    def test_error_status_bad_credentials(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "invalid-token-value",
            "jira_site_url": "https://site.atlassian.net",
        })
        client = MockJiraClient(
            myself_error=jc.JiraAuthError("bad credentials", status_code=401)
        )
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert result["email"] == "user@example.com"
        assert result["token_preview"] == "inva****alue"
        assert result["site_url"] == "https://site.atlassian.net"
        assert "error" in result
        assert "bad credentials" in result["error"]

    def test_error_status_network_failure(self):
        state = MockStateClient({
            "jira_email": "user@example.com",
            "jira_token": "abcdefghijklmnop",
            "jira_site_url": "https://site.atlassian.net",
        })
        client = MockJiraClient(
            myself_error=ConnectionError("Network unreachable")
        )
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert "error" in result
        assert "Network unreachable" in result["error"]
