"""Unit tests for Outlook Calendar auth helpers.

Loads ``auth.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All HTTP and state
interactions are mocked — no network calls are made.
"""

from __future__ import annotations

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
    Path(__file__).resolve().parent.parent.parent / "apps" / "outlook-calendar"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load auth module (it defines OutlookAuthError as a local fallback
# when outlook_client isn't available yet — that's fine for T01)
auth = _load_module("outlook_auth", _SERVICES_DIR / "auth.py")

build_authorize_url = auth.build_authorize_url
exchange_code = auth.exchange_code
refresh_access_token = auth.refresh_access_token
refresh_if_expired = auth.refresh_if_expired
store_auth_tokens = auth.store_auth_tokens
get_connection_status = auth.get_connection_status
clear_auth_state = auth.clear_auth_state
OutlookAuthError = auth.OutlookAuthError
OUTLOOK_AUTHORIZE_URL = auth.OUTLOOK_AUTHORIZE_URL
OUTLOOK_TOKEN_URL = auth.OUTLOOK_TOKEN_URL
OUTLOOK_SCOPES = auth.OUTLOOK_SCOPES
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
# Tests: build_authorize_url
# ---------------------------------------------------------------------------


class TestBuildAuthorizeUrl:

    def test_basic_url_construction(self):
        url = build_authorize_url(
            client_id="app-id-123",
            redirect_uri="http://localhost:8000/callback",
            state="csrf_token_abc",
        )
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert "login.microsoftonline.com" in parsed.netloc
        assert "/oauth2/v2.0/authorize" in parsed.path

        params = parse_qs(parsed.query)
        assert params["client_id"] == ["app-id-123"]
        assert params["redirect_uri"] == ["http://localhost:8000/callback"]
        assert params["response_type"] == ["code"]
        assert params["state"] == ["csrf_token_abc"]

    def test_scope_includes_calendars_and_offline(self):
        url = build_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        scopes = params["scope"][0].split()
        assert "Calendars.ReadWrite" in scopes
        assert "offline_access" in scopes

    def test_response_mode_is_query(self):
        url = build_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert params["response_mode"] == ["query"]

    def test_url_encodes_redirect_uri(self):
        url = build_authorize_url(
            client_id="cid",
            redirect_uri="http://example.com/path?foo=bar&baz=1",
            state="s",
        )
        params = parse_qs(urlparse(url).query)
        assert params["redirect_uri"] == [
            "http://example.com/path?foo=bar&baz=1"
        ]

    def test_no_prompt_or_access_type_params(self):
        """Microsoft uses different params than Google — no prompt/access_type by default."""
        url = build_authorize_url("cid", "http://cb", "s")
        params = parse_qs(urlparse(url).query)
        assert "prompt" not in params
        assert "access_type" not in params


# ---------------------------------------------------------------------------
# Tests: exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:

    @pytest.mark.asyncio
    async def test_success_returns_token_dict(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "eyJ0eXAi.access_token",
                "refresh_token": "0.AVYA.refresh_token",
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

        assert result["access_token"] == "eyJ0eXAi.access_token"
        assert result["refresh_token"] == "0.AVYA.refresh_token"
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
        assert call["url"] == OUTLOOK_TOKEN_URL
        assert call["data"]["grant_type"] == "authorization_code"
        assert call["data"]["code"] == "code123"
        assert call["data"]["client_id"] == "cid"
        assert call["data"]["client_secret"] == "csecret"
        assert call["data"]["redirect_uri"] == "http://cb"

    @pytest.mark.asyncio
    async def test_sends_scope_in_token_request(self):
        """Microsoft requires scope in the token exchange, unlike Google."""
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 3600,
            })
        ])

        await exchange_code(http, "code", "cid", "cs", "http://cb")

        call = http.calls[0]
        assert call["data"]["scope"] == OUTLOOK_SCOPES

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(400, {"error": "invalid_grant"})
        ])

        with pytest.raises(OutlookAuthError, match="OAuth token exchange failed: 400"):
            await exchange_code(http, "bad_code", "cid", "csecret", "http://cb")

    @pytest.mark.asyncio
    async def test_failure_error_has_status_and_body(self):
        http = MockHttpClient([
            MockResponse(400, {"error": "invalid_grant", "error_description": "expired"})
        ])

        with pytest.raises(OutlookAuthError) as exc_info:
            await exchange_code(http, "bad_code", "cid", "cs", "http://cb")

        assert exc_info.value.status_code == 400
        assert "invalid_grant" in exc_info.value.response_body

    @pytest.mark.asyncio
    async def test_missing_fields_returns_empty_strings(self):
        """Response without some fields should return empty strings."""
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
                "access_token": "eyJ0eXAi.new_access",
                "expires_in": 3600,
            })
        ])

        result = await refresh_access_token(
            http, "0.AVYA.refresh_tok", "cid", "csecret"
        )

        assert result["access_token"] == "eyJ0eXAi.new_access"
        assert result["expires_in"] == 3600

        call = http.calls[0]
        assert call["data"]["grant_type"] == "refresh_token"
        assert call["data"]["refresh_token"] == "0.AVYA.refresh_tok"

    @pytest.mark.asyncio
    async def test_sends_scope_in_refresh_request(self):
        """Microsoft requires scope in the refresh request."""
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "tok",
                "expires_in": 3600,
            })
        ])

        await refresh_access_token(http, "ref", "cid", "cs")

        call = http.calls[0]
        assert call["data"]["scope"] == OUTLOOK_SCOPES

    @pytest.mark.asyncio
    async def test_returns_rotated_refresh_token(self):
        """Microsoft may return a new refresh token — should be captured."""
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
            })
        ])

        result = await refresh_access_token(http, "old_refresh", "cid", "cs")

        assert result["refresh_token"] == "new_refresh"

    @pytest.mark.asyncio
    async def test_preserves_original_refresh_when_not_rotated(self):
        """If Microsoft doesn't return a new refresh token, keep the old one."""
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_access",
                "expires_in": 3600,
            })
        ])

        result = await refresh_access_token(http, "old_refresh", "cid", "cs")

        assert result["refresh_token"] == "old_refresh"

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(401, {"error": "invalid_grant"})
        ])

        with pytest.raises(OutlookAuthError, match="Token refresh failed: 401"):
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
        assert len(http.calls) == 0

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
        expiry_calls = [c for c in state.set_calls if c[0] == "token_expiry"]
        assert len(expiry_calls) == 1

    @pytest.mark.asyncio
    async def test_no_refresh_token_raises(self):
        """If no refresh token available, raises OutlookAuthError."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
        })
        http = MockHttpClient()

        with pytest.raises(OutlookAuthError, match="No refresh token"):
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
    async def test_stores_rotated_refresh_token(self):
        """If refresh returns a new refresh_token, it should be stored."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
            "refresh_token": "old_refresh",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_access",
                "refresh_token": "rotated_refresh",
                "expires_in": 3600,
            })
        ])

        await refresh_if_expired(http, state, "cid", "csecret")

        assert ("refresh_token", "rotated_refresh") in state.set_calls

    @pytest.mark.asyncio
    async def test_skips_refresh_token_store_when_unchanged(self):
        """If refresh token is same as before, don't re-store it."""
        past_expiry = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        state = MockStateClient({
            "access_token": "old_token",
            "token_expiry": past_expiry,
            "refresh_token": "same_refresh",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_access",
                "refresh_token": "same_refresh",
                "expires_in": 3600,
            })
        ])

        await refresh_if_expired(http, state, "cid", "csecret")

        refresh_sets = [c for c in state.set_calls if c[0] == "refresh_token"]
        assert len(refresh_sets) == 0

    @pytest.mark.asyncio
    async def test_invalid_expiry_format_triggers_refresh(self):
        """Malformed token_expiry should be treated as expired."""
        state = MockStateClient({
            "access_token": "tok",
            "token_expiry": "not-a-date",
            "refresh_token": "ref",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_tok",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "cs")

        assert token == "new_tok"
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_no_token_expiry_triggers_refresh(self):
        """If no token_expiry is stored at all, should refresh."""
        state = MockStateClient({
            "access_token": "tok",
            "refresh_token": "ref",
        })
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "new_tok",
                "expires_in": 3600,
            })
        ])

        token = await refresh_if_expired(http, state, "cid", "cs")

        assert token == "new_tok"


# ---------------------------------------------------------------------------
# Tests: store_auth_tokens
# ---------------------------------------------------------------------------


class TestStoreAuthTokens:

    @pytest.mark.asyncio
    async def test_stores_all_fields(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="eyJ0eXAi.access",
            refresh_token="0.AVYA.refresh",
            expires_in=3600,
            microsoft_email="user@outlook.com",
        )

        assert state._store["access_token"] == "eyJ0eXAi.access"
        assert state._store["refresh_token"] == "0.AVYA.refresh"
        assert state._store["auth_method"] == "oauth"
        assert state._store["microsoft_email"] == "user@outlook.com"

    @pytest.mark.asyncio
    async def test_computes_token_expiry_as_iso8601(self):
        state = MockStateClient()

        before = datetime.now(timezone.utc)
        await store_auth_tokens(state, "tok", "ref", 3600, "u@outlook.com")
        after = datetime.now(timezone.utc)

        stored_expiry = state._store["token_expiry"]
        expiry_dt = datetime.fromisoformat(stored_expiry)
        assert before + timedelta(seconds=3599) <= expiry_dt
        assert expiry_dt <= after + timedelta(seconds=3601)

    @pytest.mark.asyncio
    async def test_none_expires_in_skips_expiry(self):
        state = MockStateClient()

        await store_auth_tokens(state, "tok", "ref", None, "u@outlook.com")

        assert "token_expiry" not in state._store


# ---------------------------------------------------------------------------
# Tests: get_connection_status
# ---------------------------------------------------------------------------


class TestGetConnectionStatus:

    @pytest.mark.asyncio
    async def test_connected_with_full_info(self):
        state = MockStateClient({
            "auth_method": "oauth",
            "microsoft_email": "user@outlook.com",
            "token_expiry": "2026-03-19T12:00:00+00:00",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.something",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "oauth"
        assert status["microsoft_email"] == "user@outlook.com"
        assert status["token_expiry"] == "2026-03-19T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_token_preview_masked(self):
        """token_preview shows first 8 chars + ellipsis, never full token."""
        state = MockStateClient({
            "auth_method": "oauth",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9",
        })

        status = await get_connection_status(state)

        assert status["token_preview"] == "eyJ0eXAi..."
        assert "JKV1Q" not in status["token_preview"]

    @pytest.mark.asyncio
    async def test_token_preview_short_token(self):
        """Very short tokens get masked to *** instead of partial."""
        state = MockStateClient({
            "auth_method": "oauth",
            "access_token": "short",
        })

        status = await get_connection_status(state)

        assert status["token_preview"] == "***"

    @pytest.mark.asyncio
    async def test_token_preview_none_when_no_token(self):
        state = MockStateClient({
            "auth_method": "oauth",
        })

        status = await get_connection_status(state)

        assert status["token_preview"] is None

    @pytest.mark.asyncio
    async def test_disconnected_when_no_auth(self):
        state = MockStateClient()

        status = await get_connection_status(state)

        assert status["connected"] is False
        assert status["auth_method"] is None
        assert status["microsoft_email"] is None
        assert status["token_preview"] is None

    @pytest.mark.asyncio
    async def test_disconnected_after_clear(self):
        """After clear_auth_state, connection shows as disconnected."""
        state = MockStateClient({
            "auth_method": "oauth",
            "microsoft_email": "user@outlook.com",
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
            "microsoft_email": "user@outlook.com",
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


# ---------------------------------------------------------------------------
# Tests: OutlookAuthError
# ---------------------------------------------------------------------------


class TestOutlookAuthError:

    def test_error_carries_status_and_body(self):
        err = OutlookAuthError(
            "token exchange failed",
            status_code=400,
            response_body='{"error":"invalid_grant"}',
        )
        assert err.status_code == 400
        assert err.response_body == '{"error":"invalid_grant"}'
        assert str(err) == "token exchange failed"

    def test_error_with_none_fields(self):
        err = OutlookAuthError("generic error")
        assert err.status_code is None
        assert err.response_body is None


# ---------------------------------------------------------------------------
# Tests: constants / env overrides
# ---------------------------------------------------------------------------


class TestConstants:

    def test_default_authorize_url(self):
        assert "login.microsoftonline.com" in OUTLOOK_AUTHORIZE_URL
        assert "/common/oauth2/v2.0/authorize" in OUTLOOK_AUTHORIZE_URL

    def test_default_token_url(self):
        assert "login.microsoftonline.com" in OUTLOOK_TOKEN_URL
        assert "/common/oauth2/v2.0/token" in OUTLOOK_TOKEN_URL

    def test_scopes_include_calendars_and_offline(self):
        assert "Calendars.ReadWrite" in OUTLOOK_SCOPES
        assert "offline_access" in OUTLOOK_SCOPES

    def test_auth_state_keys_complete(self):
        expected = {"access_token", "refresh_token", "auth_method",
                    "microsoft_email", "token_expiry"}
        assert set(AUTH_STATE_KEYS) == expected
