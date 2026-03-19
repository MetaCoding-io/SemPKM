"""Unit tests for Google Calendar auth helpers.

Loads ``auth.py`` and ``gcal_client.py`` from the apps directory using
importlib to avoid requiring the app to be installed as a package.
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
    Path(__file__).resolve().parent.parent.parent / "apps" / "google-calendar"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# gcal_client must be in sys.modules before auth imports it
gc = _load_module("gcal_client", _SERVICES_DIR / "gcal_client.py")
GCalAuthError = gc.GCalAuthError
GCalAPIError = gc.GCalAPIError

# Now load auth module
auth = _load_module("auth", _SERVICES_DIR / "auth.py")

build_google_authorize_url = auth.build_google_authorize_url
exchange_code = auth.exchange_code
refresh_access_token = auth.refresh_access_token
refresh_if_expired = auth.refresh_if_expired
store_auth_tokens = auth.store_auth_tokens
get_connection_status = auth.get_connection_status
clear_auth_state = auth.clear_auth_state
GOOGLE_AUTHORIZE_URL = auth.GOOGLE_AUTHORIZE_URL
GOOGLE_TOKEN_URL = auth.GOOGLE_TOKEN_URL
GOOGLE_SCOPES = auth.GOOGLE_SCOPES
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
# Tests: build_google_authorize_url
# ---------------------------------------------------------------------------

class TestBuildGoogleAuthorizeUrl:

    def test_basic_url_construction(self):
        url = build_google_authorize_url(
            client_id="client123",
            redirect_uri="http://localhost:8000/callback",
            state="csrf_token_abc",
        )
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert parsed.path == "/o/oauth2/v2/auth"

        params = parse_qs(parsed.query)
        assert params["client_id"] == ["client123"]
        assert params["redirect_uri"] == ["http://localhost:8000/callback"]
        assert params["response_type"] == ["code"]
        assert params["state"] == ["csrf_token_abc"]

    def test_scope_is_calendar_events(self):
        url = build_google_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert params["scope"] == [GOOGLE_SCOPES]

    def test_access_type_is_offline(self):
        url = build_google_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert params["access_type"] == ["offline"]

    def test_prompt_is_consent(self):
        url = build_google_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert params["prompt"] == ["consent"]

    def test_url_encodes_redirect_uri(self):
        url = build_google_authorize_url(
            client_id="cid",
            redirect_uri="http://example.com/path?foo=bar&baz=1",
            state="s",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["redirect_uri"] == ["http://example.com/path?foo=bar&baz=1"]


# ---------------------------------------------------------------------------
# Tests: exchange_code
# ---------------------------------------------------------------------------

class TestExchangeCode:

    @pytest.mark.asyncio
    async def test_success_returns_token_dict(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "ya29.access_token",
                "refresh_token": "1//refresh_token",
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

        assert result["access_token"] == "ya29.access_token"
        assert result["refresh_token"] == "1//refresh_token"
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
        assert call["url"] == GOOGLE_TOKEN_URL
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

        with pytest.raises(GCalAuthError, match="OAuth token exchange failed: 400"):
            await exchange_code(http, "bad_code", "cid", "csecret", "http://cb")

    @pytest.mark.asyncio
    async def test_missing_fields_returns_empty_strings(self):
        """Google response without some fields should return empty strings."""
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
                "access_token": "ya29.new_access",
                "expires_in": 3600,
            })
        ])

        result = await refresh_access_token(
            http, "1//refresh_tok", "cid", "csecret"
        )

        assert result["access_token"] == "ya29.new_access"
        assert result["expires_in"] == 3600

        call = http.calls[0]
        assert call["data"]["grant_type"] == "refresh_token"
        assert call["data"]["refresh_token"] == "1//refresh_tok"

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(401, {"error": "invalid_grant"})
        ])

        with pytest.raises(GCalAuthError, match="Token refresh failed: 401"):
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
        """If no refresh token available, raises GCalAuthError."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
        })
        http = MockHttpClient()

        with pytest.raises(GCalAuthError, match="No refresh token"):
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


# ---------------------------------------------------------------------------
# Tests: store_auth_tokens
# ---------------------------------------------------------------------------

class TestStoreAuthTokens:

    @pytest.mark.asyncio
    async def test_stores_all_fields(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="ya29.access",
            refresh_token="1//refresh",
            expires_in=3600,
            google_email="user@gmail.com",
        )

        assert state._store["access_token"] == "ya29.access"
        assert state._store["refresh_token"] == "1//refresh"
        assert state._store["auth_method"] == "oauth"
        assert state._store["google_email"] == "user@gmail.com"

    @pytest.mark.asyncio
    async def test_computes_token_expiry_as_iso8601(self):
        state = MockStateClient()

        before = datetime.now(timezone.utc)
        await store_auth_tokens(state, "tok", "ref", 3600, "u@g.com")
        after = datetime.now(timezone.utc)

        stored_expiry = state._store["token_expiry"]
        expiry_dt = datetime.fromisoformat(stored_expiry)
        # The expiry should be ~1 hour from now
        assert before + timedelta(seconds=3599) <= expiry_dt
        assert expiry_dt <= after + timedelta(seconds=3601)

    @pytest.mark.asyncio
    async def test_none_expires_in_skips_expiry(self):
        state = MockStateClient()

        await store_auth_tokens(state, "tok", "ref", None, "u@g.com")

        assert "token_expiry" not in state._store


# ---------------------------------------------------------------------------
# Tests: get_connection_status
# ---------------------------------------------------------------------------

class TestGetConnectionStatus:

    @pytest.mark.asyncio
    async def test_connected_with_full_info(self):
        state = MockStateClient({
            "auth_method": "oauth",
            "google_email": "user@gmail.com",
            "token_expiry": "2026-03-19T12:00:00+00:00",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "oauth"
        assert status["google_email"] == "user@gmail.com"
        assert status["token_expiry"] == "2026-03-19T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_disconnected_when_no_auth(self):
        state = MockStateClient()

        status = await get_connection_status(state)

        assert status["connected"] is False
        assert status["auth_method"] is None
        assert status["google_email"] is None

    @pytest.mark.asyncio
    async def test_disconnected_after_clear(self):
        """After clear_auth_state, connection shows as disconnected."""
        state = MockStateClient({
            "auth_method": "oauth",
            "google_email": "user@gmail.com",
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
            "google_email": "user@gmail.com",
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
