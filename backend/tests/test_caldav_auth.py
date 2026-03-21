"""Unit tests for CalDAV auth helpers.

Loads ``caldav_client.py`` and ``auth.py`` from the apps directory using
importlib to avoid requiring the app to be installed as a package.
All HTTP and state interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "caldav-calendar"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# caldav_client must be in sys.modules before auth imports it
cc = _load_module("caldav_client", _SERVICES_DIR / "caldav_client.py")
CalDAVAuthError = cc.CalDAVAuthError
CalDAVError = cc.CalDAVError

# Now load auth module
auth = _load_module("auth", _SERVICES_DIR / "auth.py")

get_auth_headers = auth.get_auth_headers
store_credentials = auth.store_credentials
check_connection = auth.check_connection
get_connection_status = auth.get_connection_status
clear_auth_state = auth.clear_auth_state
AUTH_STATE_KEYS = auth.AUTH_STATE_KEYS


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: str | dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else ""
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return self._body


class MockHttpClient:
    """Records calls and returns preset responses."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self._idx = 0

    async def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, "No mock response configured")


class MockStateClient:
    """In-memory state store with async get/set."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str]] = []

    async def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.set_calls.append((key, value))
        self._store[key] = value


# ---------------------------------------------------------------------------
# Tests: get_auth_headers
# ---------------------------------------------------------------------------


class TestGetAuthHeaders:

    def test_basic_encoding(self):
        """Correct base64 encoding of username:password."""
        headers = get_auth_headers("alice", "secret123")
        expected = base64.b64encode(b"alice:secret123").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_special_chars_in_username(self):
        """Handles special characters in username."""
        headers = get_auth_headers("user@example.com", "p@ss:w0rd!")
        expected = base64.b64encode(b"user@example.com:p@ss:w0rd!").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_unicode_password(self):
        """Handles unicode characters in credentials."""
        headers = get_auth_headers("user", "pässwörd")
        credentials = "user:pässwörd"
        expected = base64.b64encode(credentials.encode()).decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_empty_password(self):
        """Handles empty password (some servers allow this)."""
        headers = get_auth_headers("user", "")
        expected = base64.b64encode(b"user:").decode()
        assert headers["Authorization"] == f"Basic {expected}"


# ---------------------------------------------------------------------------
# Tests: store_credentials
# ---------------------------------------------------------------------------


class TestStoreCredentials:

    @pytest.mark.asyncio
    async def test_stores_all_fields(self):
        state = MockStateClient()

        await store_credentials(
            state,
            server_url="https://caldav.example.com/dav",
            username="alice",
            password="secret",
        )

        assert state._store["server_url"] == "https://caldav.example.com/dav"
        assert state._store["username"] == "alice"
        assert state._store["password"] == "secret"
        assert state._store["auth_method"] == "basic"

    @pytest.mark.asyncio
    async def test_trims_trailing_slash(self):
        state = MockStateClient()

        await store_credentials(
            state,
            server_url="https://caldav.example.com/dav/",
            username="alice",
            password="secret",
        )

        assert state._store["server_url"] == "https://caldav.example.com/dav"

    @pytest.mark.asyncio
    async def test_trims_multiple_trailing_slashes(self):
        state = MockStateClient()

        await store_credentials(
            state,
            server_url="https://caldav.example.com///",
            username="alice",
            password="secret",
        )

        assert state._store["server_url"] == "https://caldav.example.com"


# ---------------------------------------------------------------------------
# Tests: check_connection
# ---------------------------------------------------------------------------


class TestTestConnection:

    @pytest.mark.asyncio
    async def test_success_207(self):
        """207 Multi-Status means CalDAV is working."""
        multistatus_xml = """<?xml version="1.0" encoding="utf-8"?>
        <d:multistatus xmlns:d="DAV:">
          <d:response>
            <d:href>/</d:href>
            <d:propstat>
              <d:prop>
                <d:current-user-principal>
                  <d:href>/principals/users/alice/</d:href>
                </d:current-user-principal>
              </d:prop>
              <d:status>HTTP/1.1 200 OK</d:status>
            </d:propstat>
          </d:response>
        </d:multistatus>"""
        http = MockHttpClient([MockResponse(207, multistatus_xml)])

        result = await check_connection(
            http, "https://caldav.example.com/", "alice", "secret"
        )

        assert result["success"] is True
        assert result["status_code"] == 207

    @pytest.mark.asyncio
    async def test_auth_failure_401(self):
        http = MockHttpClient([MockResponse(401, "Unauthorized")])

        result = await check_connection(
            http, "https://caldav.example.com/", "alice", "wrong"
        )

        assert result["success"] is False
        assert result["status_code"] == 401
        assert "Authentication failed" in result["message"]

    @pytest.mark.asyncio
    async def test_not_found_404(self):
        http = MockHttpClient([MockResponse(404, "Not Found")])

        result = await check_connection(
            http, "https://example.com/nonexistent", "alice", "secret"
        )

        assert result["success"] is False
        assert result["status_code"] == 404
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        http = MockHttpClient([MockResponse(500, "Internal Server Error")])

        result = await check_connection(
            http, "https://caldav.example.com/", "alice", "secret"
        )

        assert result["success"] is False
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    async def test_sends_propfind_method(self):
        """Verifies PROPFIND method and XML body are sent."""
        http = MockHttpClient([MockResponse(207, "<multistatus/>")])

        await check_connection(
            http, "https://caldav.example.com/", "alice", "secret"
        )

        call = http.calls[0]
        assert call["method"] == "PROPFIND"
        assert call["url"] == "https://caldav.example.com/"
        assert "current-user-principal" in call["content"]
        assert call["headers"]["Depth"] == "0"
        assert "Basic " in call["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_connection_exception_handled(self):
        """Network errors are caught and returned as failure."""

        class FailingHttpClient:
            async def request(self, *args, **kwargs):
                raise ConnectionError("DNS resolution failed")

        result = await check_connection(
            FailingHttpClient(), "https://unreachable.example.com/", "alice", "secret"
        )

        assert result["success"] is False
        assert result["status_code"] == 0
        assert "Connection error" in result["message"]


# ---------------------------------------------------------------------------
# Tests: get_connection_status
# ---------------------------------------------------------------------------


class TestGetConnectionStatus:

    @pytest.mark.asyncio
    async def test_connected_with_credentials(self):
        state = MockStateClient({
            "auth_method": "basic",
            "server_url": "https://caldav.example.com",
            "username": "alice",
            "password": "secret",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "basic"
        assert status["server_url"] == "https://caldav.example.com"
        assert status["username"] == "alice"

    @pytest.mark.asyncio
    async def test_disconnected_when_no_auth(self):
        state = MockStateClient()

        status = await get_connection_status(state)

        assert status["connected"] is False
        assert status["auth_method"] is None

    @pytest.mark.asyncio
    async def test_never_returns_password(self):
        """Password must never appear in connection status."""
        state = MockStateClient({
            "auth_method": "basic",
            "server_url": "https://caldav.example.com",
            "username": "alice",
            "password": "super_secret_password",
        })

        status = await get_connection_status(state)

        assert "password" not in status
        # Also verify the password value doesn't appear in any field
        for value in status.values():
            if isinstance(value, str):
                assert "super_secret_password" not in value

    @pytest.mark.asyncio
    async def test_disconnected_after_clear(self):
        """After clear_auth_state, connection shows as disconnected."""
        state = MockStateClient({
            "auth_method": "basic",
            "server_url": "https://caldav.example.com",
            "username": "alice",
            "password": "secret",
        })

        await clear_auth_state(state)
        status = await get_connection_status(state)

        assert status["connected"] is False


# ---------------------------------------------------------------------------
# Tests: clear_auth_state
# ---------------------------------------------------------------------------


class TestClearAuthState:

    @pytest.mark.asyncio
    async def test_clears_all_keys(self):
        state = MockStateClient({
            "server_url": "https://caldav.example.com",
            "username": "alice",
            "password": "secret",
            "auth_method": "basic",
        })

        await clear_auth_state(state)

        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""

    @pytest.mark.asyncio
    async def test_clears_each_key_individually(self):
        """Verify each AUTH_STATE_KEY gets a set("", ...) call."""
        state = MockStateClient({
            "server_url": "https://caldav.example.com",
            "username": "alice",
            "password": "secret",
            "auth_method": "basic",
        })

        await clear_auth_state(state)

        cleared_keys = {call[0] for call in state.set_calls}
        for key in AUTH_STATE_KEYS:
            assert key in cleared_keys

    @pytest.mark.asyncio
    async def test_clear_on_empty_state(self):
        """Clearing when already empty should not raise."""
        state = MockStateClient()

        await clear_auth_state(state)

        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""
