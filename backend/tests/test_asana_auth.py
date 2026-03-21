"""Unit tests for Asana Sync auth helpers.

Loads ``auth.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. Defines a minimal
``AsanaAuthError`` stub since ``asana_client.py`` doesn't exist yet (T02).
All HTTP and state interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "asana-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Provide a minimal asana_client stub so auth.py can import AsanaAuthError.
# T02 will create the real asana_client.py with the canonical exception hierarchy.
_asana_client_stub = type(sys)("asana_client")


class AsanaAPIError(Exception):
    """Base exception for Asana API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class AsanaAuthError(AsanaAPIError):
    """Authentication/authorization error (401/403)."""


_asana_client_stub.AsanaAPIError = AsanaAPIError  # type: ignore[attr-defined]
_asana_client_stub.AsanaAuthError = AsanaAuthError  # type: ignore[attr-defined]
sys.modules["asana_client"] = _asana_client_stub

# Now load auth module (will find AsanaAuthError via the stub)
auth = _load_module("auth", _SERVICES_DIR / "auth.py")

build_asana_authorize_url = auth.build_asana_authorize_url
exchange_code = auth.exchange_code
refresh_access_token = auth.refresh_access_token
refresh_if_expired = auth.refresh_if_expired
verify_pat = auth.verify_pat
store_auth_tokens = auth.store_auth_tokens
get_connection_status = auth.get_connection_status
clear_auth_state = auth.clear_auth_state
ASANA_AUTHORIZE_URL = auth.ASANA_AUTHORIZE_URL
ASANA_TOKEN_URL = auth.ASANA_TOKEN_URL
ASANA_API_URL = auth.ASANA_API_URL
AUTH_STATE_KEYS = auth.AUTH_STATE_KEYS


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: dict | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)

    def json(self) -> Any:
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class MockHttpClient:
    """Records calls and returns preset responses."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self._idx = 0

    async def post(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})


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
# Tests: build_asana_authorize_url
# ---------------------------------------------------------------------------

class TestBuildAsanaAuthorizeUrl:

    def test_basic_url_construction(self):
        url = build_asana_authorize_url(
            client_id="client123",
            redirect_uri="http://localhost:8000/callback",
            state="csrf_token_abc",
        )
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "app.asana.com"
        assert parsed.path == "/-/oauth_authorize"

        params = parse_qs(parsed.query)
        assert params["client_id"] == ["client123"]
        assert params["redirect_uri"] == ["http://localhost:8000/callback"]
        assert params["response_type"] == ["code"]
        assert params["state"] == ["csrf_token_abc"]

    def test_no_scope_parameter(self):
        """Asana OAuth uses implicit scopes — no scope param in URL."""
        url = build_asana_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert "scope" not in params

    def test_url_encodes_redirect_uri(self):
        url = build_asana_authorize_url(
            client_id="cid",
            redirect_uri="http://example.com/path?foo=bar&baz=1",
            state="s",
        )
        params = parse_qs(urlparse(url).query)
        assert params["redirect_uri"] == ["http://example.com/path?foo=bar&baz=1"]

    def test_state_preserved_exactly(self):
        url = build_asana_authorize_url("cid", "http://cb", "complex-state_123")
        params = parse_qs(urlparse(url).query)
        assert params["state"] == ["complex-state_123"]


# ---------------------------------------------------------------------------
# Tests: exchange_code
# ---------------------------------------------------------------------------

class TestExchangeCode:

    @pytest.mark.asyncio
    async def test_success_returns_token_dict(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "asana_access_token",
                "refresh_token": "asana_refresh_token",
                "expires_in": 3600,
            })
        ])

        result = await exchange_code(
            http,
            code="auth_code_abc",
            client_id="cid",
            client_secret="csecret",
            redirect_uri="http://localhost/cb",
        )

        assert result["access_token"] == "asana_access_token"
        assert result["refresh_token"] == "asana_refresh_token"
        assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_sends_correct_post_body(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 3600,
            })
        ])

        await exchange_code(http, "code123", "cid", "csecret", "http://cb")

        call = http.calls[0]
        assert call["url"] == ASANA_TOKEN_URL
        assert call["data"]["grant_type"] == "authorization_code"
        assert call["data"]["code"] == "code123"
        assert call["data"]["client_id"] == "cid"
        assert call["data"]["client_secret"] == "csecret"
        assert call["data"]["redirect_uri"] == "http://cb"

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(400, {"error": "invalid_grant"})
        ])

        with pytest.raises(AsanaAuthError, match="OAuth token exchange failed: 400"):
            await exchange_code(http, "bad_code", "cid", "csecret", "http://cb")

    @pytest.mark.asyncio
    async def test_missing_fields_returns_empty_strings(self):
        """Response without some fields returns empty strings / None."""
        http = MockHttpClient([
            MockResponse(200, {"access_token": "tok"})
        ])

        result = await exchange_code(http, "code", "cid", "cs", "http://cb")

        assert result["access_token"] == "tok"
        assert result["refresh_token"] == ""
        assert result["expires_in"] is None


# ---------------------------------------------------------------------------
# Tests: refresh_access_token
# ---------------------------------------------------------------------------

class TestRefreshAccessToken:

    @pytest.mark.asyncio
    async def test_success_returns_new_token(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_asana_access",
                "expires_in": 3600,
            })
        ])

        result = await refresh_access_token(
            http, "refresh_tok", "cid", "csecret"
        )

        assert result["access_token"] == "new_asana_access"
        assert result["expires_in"] == 3600

        call = http.calls[0]
        assert call["data"]["grant_type"] == "refresh_token"
        assert call["data"]["refresh_token"] == "refresh_tok"

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(401, {"error": "invalid_grant"})
        ])

        with pytest.raises(AsanaAuthError, match="Token refresh failed: 401"):
            await refresh_access_token(http, "bad_ref", "cid", "csecret")


# ---------------------------------------------------------------------------
# Tests: refresh_if_expired
# ---------------------------------------------------------------------------

class TestRefreshIfExpired:

    @pytest.mark.asyncio
    async def test_not_expired_skips_refresh(self):
        """If token is valid for more than 5 minutes, just return it."""
        future_expiry = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        state = MockStateClient({
            "access_token": "still_valid",
            "token_expiry": future_expiry,
            "refresh_token": "ref_tok",
        })
        http = MockHttpClient()

        token = await refresh_if_expired(http, state, "cid", "csecret")

        assert token == "still_valid"
        assert len(http.calls) == 0  # No HTTP calls made

    @pytest.mark.asyncio
    async def test_expired_triggers_refresh(self):
        """If token is expired, refresh and store new token."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
            "refresh_token": "ref_tok",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_access",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "csecret")

        assert token == "new_access"
        assert ("access_token", "new_access") in state.set_calls
        # Should also store the new expiry
        expiry_calls = [c for c in state.set_calls if c[0] == "token_expiry"]
        assert len(expiry_calls) == 1

    @pytest.mark.asyncio
    async def test_no_refresh_token_raises(self):
        """If no refresh token available, raises AsanaAuthError."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
        })
        http = MockHttpClient()

        with pytest.raises(AsanaAuthError, match="No refresh token"):
            await refresh_if_expired(http, state, "cid", "csecret")

    @pytest.mark.asyncio
    async def test_within_buffer_triggers_refresh(self):
        """Token expiring in less than 5 minutes should trigger refresh."""
        near_expiry = (
            datetime.now(timezone.utc) + timedelta(minutes=3)
        ).isoformat()
        state = MockStateClient({
            "access_token": "expiring_soon",
            "token_expiry": near_expiry,
            "refresh_token": "ref_tok",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "refreshed",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "csecret")

        assert token == "refreshed"
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_no_expiry_recorded_triggers_refresh(self):
        """If no token_expiry in state, assume expired and refresh."""
        state = MockStateClient({
            "access_token": "token_no_expiry",
            "refresh_token": "ref_tok",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "refreshed_token",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "csecret")

        assert token == "refreshed_token"
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_invalid_expiry_format_triggers_refresh(self):
        """Malformed token_expiry should trigger refresh, not crash."""
        state = MockStateClient({
            "access_token": "token_bad_expiry",
            "token_expiry": "not-a-date",
            "refresh_token": "ref_tok",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "refreshed_after_bad",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "csecret")

        assert token == "refreshed_after_bad"
        assert len(http.calls) == 1


# ---------------------------------------------------------------------------
# Tests: verify_pat
# ---------------------------------------------------------------------------

class TestVerifyPat:

    @pytest.mark.asyncio
    async def test_success_returns_user_data(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": {
                    "email": "user@company.com",
                    "name": "Test User",
                    "gid": "12345",
                }
            })
        ])

        result = await verify_pat(http, "pat_0/abc123")

        assert result["email"] == "user@company.com"
        assert result["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_sends_bearer_header(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": {"email": "u@c.com", "name": "U"}
            })
        ])

        await verify_pat(http, "my_pat_token")

        call = http.calls[0]
        assert call["headers"]["Authorization"] == "Bearer my_pat_token"
        assert ASANA_API_URL in call["url"]
        assert call["url"].endswith("/users/me")

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(401, {"errors": [{"message": "Not Authorized"}]})
        ])

        with pytest.raises(AsanaAuthError, match="PAT verification failed: 401"):
            await verify_pat(http, "invalid_pat")

    @pytest.mark.asyncio
    async def test_missing_data_wrapper(self):
        """Response without 'data' wrapper still extracts user info."""
        http = MockHttpClient([
            MockResponse(200, {
                "email": "direct@example.com",
                "name": "Direct User",
            })
        ])

        result = await verify_pat(http, "pat_token")

        assert result["email"] == "direct@example.com"
        assert result["name"] == "Direct User"


# ---------------------------------------------------------------------------
# Tests: store_auth_tokens
# ---------------------------------------------------------------------------

class TestStoreAuthTokens:

    @pytest.mark.asyncio
    async def test_stores_all_fields_oauth(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="asana_access",
            refresh_token="asana_refresh",
            expires_in=3600,
            asana_email="user@asana.com",
            auth_method="oauth",
        )

        assert state._store["access_token"] == "asana_access"
        assert state._store["refresh_token"] == "asana_refresh"
        assert state._store["auth_method"] == "oauth"
        assert state._store["asana_email"] == "user@asana.com"

    @pytest.mark.asyncio
    async def test_stores_pat_auth_method(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="pat_token",
            refresh_token="",
            expires_in=None,
            asana_email="user@asana.com",
            auth_method="pat",
        )

        assert state._store["auth_method"] == "pat"
        assert state._store["refresh_token"] == ""
        assert "token_expiry" not in state._store

    @pytest.mark.asyncio
    async def test_computes_token_expiry_as_iso8601(self):
        state = MockStateClient()

        before = datetime.now(timezone.utc)
        await store_auth_tokens(state, "tok", "ref", 3600, "u@a.com")
        after = datetime.now(timezone.utc)

        stored_expiry = state._store["token_expiry"]
        expiry_dt = datetime.fromisoformat(stored_expiry)
        # The expiry should be ~1 hour from now
        assert before + timedelta(seconds=3599) <= expiry_dt
        assert expiry_dt <= after + timedelta(seconds=3601)

    @pytest.mark.asyncio
    async def test_none_expires_in_skips_expiry(self):
        state = MockStateClient()

        await store_auth_tokens(state, "tok", "ref", None, "u@a.com")

        assert "token_expiry" not in state._store


# ---------------------------------------------------------------------------
# Tests: get_connection_status
# ---------------------------------------------------------------------------

class TestGetConnectionStatus:

    @pytest.mark.asyncio
    async def test_connected_with_full_info(self):
        state = MockStateClient({
            "auth_method": "oauth",
            "asana_email": "user@asana.com",
            "token_expiry": "2026-03-19T12:00:00+00:00",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "oauth"
        assert status["asana_email"] == "user@asana.com"
        assert status["token_expiry"] == "2026-03-19T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_connected_with_pat(self):
        state = MockStateClient({
            "auth_method": "pat",
            "asana_email": "user@asana.com",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "pat"

    @pytest.mark.asyncio
    async def test_disconnected_when_no_auth(self):
        state = MockStateClient()

        status = await get_connection_status(state)

        assert status["connected"] is False
        assert status["auth_method"] is None
        assert status["asana_email"] is None

    @pytest.mark.asyncio
    async def test_disconnected_after_clear(self):
        """After clear_auth_state, connection shows as disconnected."""
        state = MockStateClient({
            "auth_method": "oauth",
            "asana_email": "user@asana.com",
            "access_token": "tok",
            "refresh_token": "ref",
            "token_expiry": "2026-03-19T12:00:00+00:00",
        })

        await clear_auth_state(state)
        status = await get_connection_status(state)

        assert status["connected"] is False


# ---------------------------------------------------------------------------
# Tests: clear_auth_state
# ---------------------------------------------------------------------------

class TestClearAuthState:

    @pytest.mark.asyncio
    async def test_clears_all_auth_keys(self):
        state = MockStateClient({
            "access_token": "tok",
            "refresh_token": "ref",
            "auth_method": "oauth",
            "asana_email": "user@asana.com",
            "token_expiry": "2026-03-19T12:00:00+00:00",
        })

        await clear_auth_state(state)

        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""

    @pytest.mark.asyncio
    async def test_clear_on_empty_state(self):
        """Clearing when already empty should not raise."""
        state = MockStateClient()

        await clear_auth_state(state)

        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""
