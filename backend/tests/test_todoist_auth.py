"""Unit tests for Todoist Sync auth helpers.

Loads ``auth.py`` from the apps directory using importlib. All state and
API interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "todoist-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"
_AUTH_PATH = _SERVICES_DIR / "auth.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


auth = _load_module("todoist_auth", _AUTH_PATH)


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


class MockResponse:
    """Mock HTTP response with status_code and json()."""

    def __init__(self, status_code: int, data: Any = None):
        self.status_code = status_code
        self._data = data if data is not None else []

    def json(self) -> Any:
        return self._data


class MockHttpClient:
    """Mock HTTP client for auth tests.

    ``get()`` returns the configured response or raises the configured error.
    """

    def __init__(
        self,
        response: MockResponse | None = None,
        error: Exception | None = None,
    ):
        self._response = response or MockResponse(200, [])
        self._error = error
        self.last_url: str | None = None
        self.last_headers: dict | None = None

    async def get(self, url: str, headers: dict | None = None) -> MockResponse:
        self.last_url = url
        self.last_headers = headers
        if self._error:
            raise self._error
        return self._response


# ===================================================================
# store_token / get_stored_token tests
# ===================================================================

class TestStoreToken:
    @pytest.mark.asyncio
    async def test_store_token_writes_to_state(self):
        state = MockStateClient()
        await auth.store_token(state, "abc123xyz")
        assert state._store["todoist_pat"] == "abc123xyz"

    @pytest.mark.asyncio
    async def test_get_stored_token_reads_from_state(self):
        state = MockStateClient({"todoist_pat": "my_secret_token"})
        result = await auth.get_stored_token(state)
        assert result == "my_secret_token"

    @pytest.mark.asyncio
    async def test_get_stored_token_returns_none_when_missing(self):
        state = MockStateClient()
        result = await auth.get_stored_token(state)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stored_token_returns_none_for_empty_string(self):
        state = MockStateClient({"todoist_pat": ""})
        result = await auth.get_stored_token(state)
        assert result is None


# ===================================================================
# verify_token tests
# ===================================================================

class TestVerifyToken:
    @pytest.mark.asyncio
    async def test_verify_success_returns_projects_count(self):
        projects = [{"id": "1", "name": "Inbox"}, {"id": "2", "name": "Work"}]
        http = MockHttpClient(MockResponse(200, projects))
        result = await auth.verify_token(http, "valid_token_abc")
        assert result["valid"] is True
        assert result["projects_count"] == 2

    @pytest.mark.asyncio
    async def test_verify_sends_bearer_header(self):
        http = MockHttpClient(MockResponse(200, []))
        await auth.verify_token(http, "my_token")
        assert http.last_headers == {"Authorization": "Bearer my_token"}

    @pytest.mark.asyncio
    async def test_verify_calls_correct_endpoint(self):
        http = MockHttpClient(MockResponse(200, []))
        await auth.verify_token(http, "my_token")
        assert http.last_url == "https://api.todoist.com/rest/v2/projects"

    @pytest.mark.asyncio
    async def test_verify_401_raises_auth_error(self):
        http = MockHttpClient(MockResponse(401))
        with pytest.raises(auth.TodoistAuthError) as exc_info:
            await auth.verify_token(http, "bad_token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_403_raises_auth_error(self):
        http = MockHttpClient(MockResponse(403))
        with pytest.raises(auth.TodoistAuthError) as exc_info:
            await auth.verify_token(http, "bad_token")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_verify_500_raises_api_error(self):
        http = MockHttpClient(MockResponse(500))
        with pytest.raises(auth.TodoistAPIError) as exc_info:
            await auth.verify_token(http, "any_token")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_verify_empty_projects_still_valid(self):
        http = MockHttpClient(MockResponse(200, []))
        result = await auth.verify_token(http, "valid_token")
        assert result["valid"] is True
        assert result["projects_count"] == 0


# ===================================================================
# token masking tests
# ===================================================================

class TestTokenMasking:
    def test_standard_token(self):
        assert auth._mask_token("abcdefghijklmnop") == "abcd****mnop"

    def test_short_token(self):
        """Tokens <= 8 chars show first 4 + ****."""
        assert auth._mask_token("abcd1234") == "abcd****"

    def test_very_short_token(self):
        assert auth._mask_token("abc") == "abc****"

    def test_long_token(self):
        masked = auth._mask_token("0123456789abcdef0123456789abcdef")
        assert masked.startswith("0123")
        assert masked.endswith("cdef")
        assert "****" in masked


# ===================================================================
# get_connection_status tests
# ===================================================================

class TestGetConnectionStatus:
    @pytest.mark.asyncio
    async def test_connected_status(self):
        state = MockStateClient({"todoist_pat": "abcdefghijklmnop"})
        projects = [{"id": "1", "name": "Inbox"}]
        http = MockHttpClient(MockResponse(200, projects))
        result = await auth.get_connection_status(state, http)
        assert result["connected"] is True
        assert result["auth_method"] == "api_token"
        assert result["projects_count"] == 1
        assert result["token_preview"] == "abcd****mnop"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_disconnected_status_no_token(self):
        state = MockStateClient()
        http = MockHttpClient()
        result = await auth.get_connection_status(state, http)
        assert result["connected"] is False
        assert result["auth_method"] is None
        assert result["projects_count"] is None
        assert result["token_preview"] is None

    @pytest.mark.asyncio
    async def test_error_status_bad_token(self):
        state = MockStateClient({"todoist_pat": "bad_token_here12"})
        http = MockHttpClient(MockResponse(401))
        result = await auth.get_connection_status(state, http)
        assert result["connected"] is False
        assert result["token_preview"] == "bad_****re12"
        assert "error" in result
        assert "401" in result["error"]

    @pytest.mark.asyncio
    async def test_error_status_network_failure(self):
        state = MockStateClient({"todoist_pat": "good_token_abcd"})
        http = MockHttpClient(error=ConnectionError("network down"))
        result = await auth.get_connection_status(state, http)
        assert result["connected"] is False
        assert result["token_preview"] is not None
        assert "error" in result
        assert "network down" in result["error"]


# ===================================================================
# clear_credentials tests
# ===================================================================

class TestClearCredentials:
    @pytest.mark.asyncio
    async def test_clear_sets_empty_string(self):
        state = MockStateClient({"todoist_pat": "secret_token"})
        await auth.clear_credentials(state)
        assert state._store["todoist_pat"] == ""

    @pytest.mark.asyncio
    async def test_clear_makes_get_stored_token_return_none(self):
        state = MockStateClient({"todoist_pat": "secret_token"})
        await auth.clear_credentials(state)
        result = await auth.get_stored_token(state)
        assert result is None


# ===================================================================
# Exception classes tests
# ===================================================================

class TestExceptionClasses:
    def test_auth_error_has_status_code(self):
        err = auth.TodoistAuthError("bad token", status_code=401)
        assert str(err) == "bad token"
        assert err.status_code == 401

    def test_auth_error_default_status_code(self):
        err = auth.TodoistAuthError("unauthorized")
        assert err.status_code == 401

    def test_api_error_has_status_code(self):
        err = auth.TodoistAPIError("server error", status_code=503)
        assert str(err) == "server error"
        assert err.status_code == 503

    def test_api_error_default_status_code(self):
        err = auth.TodoistAPIError("unknown error")
        assert err.status_code == 500
