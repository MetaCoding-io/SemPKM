"""Unit tests for Monday.com Sync auth helpers.

Loads ``auth.py`` from the apps directory using importlib. All state and
API interactions are mocked — no network calls are made.

Uses ``asyncio.run()`` to execute async tests without requiring pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"

_AUTH_PATH = _SERVICES_DIR / "auth.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


auth = _load_module("monday_auth", _AUTH_PATH)


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


class MockMondayClient:
    """Mock MondayClient for auth tests."""

    def __init__(
        self,
        me_result: dict | None = None,
        me_error: Exception | None = None,
    ):
        self._me_result = me_result
        self._me_error = me_error

    async def get_me(self) -> dict:
        if self._me_error:
            raise self._me_error
        return self._me_result or {}


# ===================================================================
# store_credentials tests
# ===================================================================

class TestStoreCredentials:

    def test_store_credentials_writes_token(self):
        state = MockStateClient()
        _run(auth.store_credentials(state, "my-monday-api-token"))
        assert state._store["monday_api_token"] == "my-monday-api-token"

    def test_store_credentials_overwrites_existing(self):
        state = MockStateClient({
            "monday_api_token": "old-token",
        })
        _run(auth.store_credentials(state, "new-token"))
        assert state._store["monday_api_token"] == "new-token"

    def test_store_credentials_preserves_other_keys(self):
        state = MockStateClient({"some_other_key": "value123"})
        _run(auth.store_credentials(state, "my-token"))
        assert state._store["some_other_key"] == "value123"
        assert state._store["monday_api_token"] == "my-token"


# ===================================================================
# get_credentials tests
# ===================================================================

class TestGetCredentials:

    def test_get_credentials_returns_dict(self):
        state = MockStateClient({
            "monday_api_token": "my-monday-api-token",
        })
        result = _run(auth.get_credentials(state))
        assert result == {"api_token": "my-monday-api-token"}

    def test_get_credentials_returns_none_when_missing(self):
        state = MockStateClient()
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_get_credentials_returns_none_when_empty(self):
        state = MockStateClient({"monday_api_token": ""})
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_get_credentials_returns_none_when_not_set(self):
        state = MockStateClient({"other_key": "value"})
        result = _run(auth.get_credentials(state))
        assert result is None


# ===================================================================
# clear_credentials tests
# ===================================================================

class TestClearCredentials:

    def test_clear_credentials_sets_empty(self):
        state = MockStateClient({
            "monday_api_token": "my-token",
        })
        _run(auth.clear_credentials(state))
        assert state._store["monday_api_token"] == ""

    def test_clear_credentials_makes_get_return_none(self):
        state = MockStateClient({
            "monday_api_token": "my-token",
        })
        _run(auth.clear_credentials(state))
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_clear_credentials_idempotent(self):
        state = MockStateClient()
        _run(auth.clear_credentials(state))
        assert state._store["monday_api_token"] == ""
        result = _run(auth.get_credentials(state))
        assert result is None


# ===================================================================
# _mask_token tests
# ===================================================================

class TestMaskToken:

    def test_standard_token(self):
        assert auth._mask_token("abcdefghijklmnop") == "abcd****mnop"

    def test_short_token_8_chars(self):
        """Tokens <= 8 chars show first 4 + ****."""
        assert auth._mask_token("abcd1234") == "abcd****"

    def test_very_short_token(self):
        assert auth._mask_token("abc") == "abc****"

    def test_exactly_nine_chars(self):
        """Token of 9 chars shows first 4 + **** + last 4."""
        assert auth._mask_token("123456789") == "1234****6789"

    def test_long_api_token(self):
        """Long Monday.com API tokens are properly masked."""
        token = "eyJhbGciOiJIUzI1NiJ9abcdefghijklmnopqrstuvwxyz"
        masked = auth._mask_token(token)
        assert masked.startswith("eyJh")
        assert masked.endswith("wxyz")
        assert "****" in masked

    def test_single_char_token(self):
        """Single-char token still gets masked."""
        assert auth._mask_token("x") == "x****"

    def test_four_char_token(self):
        assert auth._mask_token("abcd") == "abcd****"

    def test_ten_char_token(self):
        """Token of exactly 10 chars shows first 4 + **** + last 4, with overlap."""
        assert auth._mask_token("1234567890") == "1234****7890"


# ===================================================================
# verify_connection tests
# ===================================================================

class TestVerifyConnection:

    def test_verify_connection_success(self):
        state = MockStateClient({"monday_api_token": "valid-token"})
        client = MockMondayClient(me_result={
            "id": "12345",
            "name": "Test User",
            "email": "test@example.com",
        })
        result = _run(auth.verify_connection(state, client))
        assert result["id"] == "12345"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"

    def test_verify_connection_failure(self):
        state = MockStateClient({"monday_api_token": "bad-token"})
        client = MockMondayClient(me_error=Exception("401 Unauthorized"))
        with pytest.raises(Exception, match="401 Unauthorized"):
            _run(auth.verify_connection(state, client))

    def test_verify_connection_network_error(self):
        state = MockStateClient({"monday_api_token": "token"})
        client = MockMondayClient(me_error=ConnectionError("Network unreachable"))
        with pytest.raises(ConnectionError, match="Network unreachable"):
            _run(auth.verify_connection(state, client))


# ===================================================================
# get_connection_status tests
# ===================================================================

class TestGetConnectionStatus:

    def test_connected_status(self):
        state = MockStateClient({
            "monday_api_token": "abcdefghijklmnop",
        })
        client = MockMondayClient(me_result={
            "id": "12345",
            "name": "Test User",
            "email": "test@example.com",
        })
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is True
        assert result["display_name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["token_preview"] == "abcd****mnop"
        assert "error" not in result

    def test_disconnected_status_no_creds(self):
        state = MockStateClient()
        client = MockMondayClient()
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert result["display_name"] is None
        assert result["email"] is None
        assert result["token_preview"] is None

    def test_disconnected_status_empty_token(self):
        state = MockStateClient({"monday_api_token": ""})
        client = MockMondayClient()
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert result["display_name"] is None

    def test_error_status_bad_credentials(self):
        state = MockStateClient({
            "monday_api_token": "invalid-token-value",
        })
        client = MockMondayClient(me_error=Exception("Authentication failed"))
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert result["display_name"] is None
        assert result["token_preview"] == "inva****alue"
        assert "error" in result
        assert "Authentication failed" in result["error"]

    def test_error_status_network_failure(self):
        state = MockStateClient({
            "monday_api_token": "abcdefghijklmnop",
        })
        client = MockMondayClient(
            me_error=ConnectionError("Network unreachable")
        )
        result = _run(auth.get_connection_status(state, client))
        assert result["connected"] is False
        assert "error" in result
        assert "Network unreachable" in result["error"]

    def test_connected_returns_no_error_key(self):
        """Successful connection should not include error key in result."""
        state = MockStateClient({
            "monday_api_token": "abcdefghijklmnop",
        })
        client = MockMondayClient(me_result={
            "id": "1",
            "name": "User",
            "email": "u@e.com",
        })
        result = _run(auth.get_connection_status(state, client))
        assert "error" not in result
        assert result["connected"] is True

    def test_error_preserves_token_preview(self):
        """Even on error, token_preview should be populated."""
        state = MockStateClient({
            "monday_api_token": "1234567890abcdef",
        })
        client = MockMondayClient(me_error=Exception("Server error"))
        result = _run(auth.get_connection_status(state, client))
        assert result["token_preview"] == "1234****cdef"
        assert result["connected"] is False


# ===================================================================
# Integration / round-trip tests
# ===================================================================

class TestRoundTrip:

    def test_store_then_get(self):
        state = MockStateClient()
        _run(auth.store_credentials(state, "round-trip-token"))
        result = _run(auth.get_credentials(state))
        assert result == {"api_token": "round-trip-token"}

    def test_store_clear_get(self):
        state = MockStateClient()
        _run(auth.store_credentials(state, "some-token"))
        _run(auth.clear_credentials(state))
        result = _run(auth.get_credentials(state))
        assert result is None

    def test_store_overwrite_get(self):
        state = MockStateClient()
        _run(auth.store_credentials(state, "first-token"))
        _run(auth.store_credentials(state, "second-token"))
        result = _run(auth.get_credentials(state))
        assert result == {"api_token": "second-token"}
