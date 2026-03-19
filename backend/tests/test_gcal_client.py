"""Unit tests for the Google Calendar API client.

Loads ``gcal_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All HTTP and state interactions
are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load gcal_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "google-calendar"
    / "services"
    / "gcal_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("gcal_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gcal_client"] = mod
    spec.loader.exec_module(mod)
    return mod


gc = _load_module()
GCalClient = gc.GCalClient
GCalAPIError = gc.GCalAPIError
GCalAuthError = gc.GCalAuthError
GCalRateLimitError = gc.GCalRateLimitError
GCAL_BASE_URL = gc.GCAL_BASE_URL


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
    """In-memory state store."""

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
# Tests: Calendar list fetch
# ---------------------------------------------------------------------------

class TestGetCalendarList:

    @pytest.mark.asyncio
    async def test_single_page_returns_calendars(self):
        http = MockHttpClient([
            MockResponse(200, {
                "kind": "calendar#calendarList",
                "items": [
                    {"id": "primary@gmail.com", "summary": "My Calendar",
                     "primary": True, "accessRole": "owner"},
                    {"id": "work@group.calendar.google.com", "summary": "Work",
                     "primary": False, "accessRole": "writer"},
                ],
            })
        ])
        state = MockStateClient({"access_token": "ya29.valid"})
        client = GCalClient(http, state)

        result = await client.get_calendar_list()

        assert len(result) == 2
        assert result[0]["id"] == "primary@gmail.com"
        assert result[0]["summary"] == "My Calendar"
        assert result[0]["primary"] is True
        assert result[0]["accessRole"] == "owner"
        assert result[1]["id"] == "work@group.calendar.google.com"

    @pytest.mark.asyncio
    async def test_paginated_calendar_list(self):
        http = MockHttpClient([
            MockResponse(200, {
                "items": [
                    {"id": "cal1", "summary": "Cal 1",
                     "primary": True, "accessRole": "owner"},
                ],
                "nextPageToken": "page2_token",
            }),
            MockResponse(200, {
                "items": [
                    {"id": "cal2", "summary": "Cal 2",
                     "primary": False, "accessRole": "reader"},
                ],
            }),
        ])
        state = MockStateClient({"access_token": "ya29.valid"})
        client = GCalClient(http, state)

        result = await client.get_calendar_list()

        assert len(result) == 2
        assert result[0]["id"] == "cal1"
        assert result[1]["id"] == "cal2"
        # Second request should include pageToken in URL
        assert "pageToken=page2_token" in http.calls[1]["url"]

    @pytest.mark.asyncio
    async def test_empty_calendar_list(self):
        http = MockHttpClient([
            MockResponse(200, {"items": []})
        ])
        state = MockStateClient({"access_token": "ya29.valid"})
        client = GCalClient(http, state)

        result = await client.get_calendar_list()

        assert result == []


# ---------------------------------------------------------------------------
# Tests: Auth header injection
# ---------------------------------------------------------------------------

class TestAuthHeaderInjection:

    @pytest.mark.asyncio
    async def test_sends_bearer_token_header(self):
        http = MockHttpClient([
            MockResponse(200, {"items": []})
        ])
        state = MockStateClient({"access_token": "ya29.my_token"})
        client = GCalClient(http, state)

        await client.get_calendar_list()

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer ya29.my_token"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_no_token_raises_auth_error(self):
        http = MockHttpClient()
        state = MockStateClient()
        client = GCalClient(http, state)

        with pytest.raises(GCalAuthError, match="Not authenticated"):
            await client.get_calendar_list()


# ---------------------------------------------------------------------------
# Tests: 401 → refresh → retry
# ---------------------------------------------------------------------------

class TestTokenRefreshOnUnauthorized:

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retry(self):
        """On 401 with refresh token, refresh then retry the request."""
        http = MockHttpClient([
            # First attempt: 401
            MockResponse(401, "Unauthorized"),
            # Refresh token request: success
            MockResponse(200, {
                "access_token": "ya29.new_access",
            }),
            # Retry attempt: success
            MockResponse(200, {
                "items": [
                    {"id": "cal1", "summary": "My Cal",
                     "primary": True, "accessRole": "owner"},
                ],
            }),
        ])
        state = MockStateClient({
            "access_token": "ya29.old_access",
            "refresh_token": "1//old_refresh",
        })
        client = GCalClient(http, state, client_id="cid", client_secret="csecret")

        result = await client.get_calendar_list()

        assert len(result) == 1
        assert result[0]["id"] == "cal1"
        # Verify refresh call was made
        refresh_call = http.calls[1]
        assert refresh_call["method"] == "POST"
        assert refresh_call["data"]["grant_type"] == "refresh_token"
        assert refresh_call["data"]["client_id"] == "cid"
        # Verify new token was stored
        assert ("access_token", "ya29.new_access") in state.set_calls

    @pytest.mark.asyncio
    async def test_401_no_refresh_token_raises(self):
        """401 without a refresh token raises immediately."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),
        ])
        state = MockStateClient({"access_token": "ya29.expired"})
        client = GCalClient(http, state)

        with pytest.raises(GCalAuthError, match="no refresh token"):
            await client.get_calendar_list()

    @pytest.mark.asyncio
    async def test_no_infinite_refresh_loop(self):
        """If retry after refresh also returns 401, stop — don't loop."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),  # first attempt
            MockResponse(200, {"access_token": "new_tok"}),  # refresh OK
            MockResponse(401, "Still unauthorized"),  # retry also 401
        ])
        state = MockStateClient({
            "access_token": "old",
            "refresh_token": "ref",
        })
        client = GCalClient(http, state, client_id="c", client_secret="s")

        with pytest.raises(GCalAuthError, match="Unauthorized after token refresh"):
            await client.get_calendar_list()

        # Should have exactly 3 HTTP calls: request, refresh, retry
        assert len(http.calls) == 3


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        http = MockHttpClient([MockResponse(403, "Forbidden")])
        state = MockStateClient({"access_token": "tok"})
        client = GCalClient(http, state)

        with pytest.raises(GCalAuthError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_with_retry_after(self):
        http = MockHttpClient([
            MockResponse(429, "Too many requests", {"Retry-After": "30"})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = GCalClient(http, state)

        with pytest.raises(GCalRateLimitError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.retry_after == 30
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_defaults_retry_after_to_60(self):
        http = MockHttpClient([MockResponse(429, "Too many requests")])
        state = MockStateClient({"access_token": "tok"})
        client = GCalClient(http, state)

        with pytest.raises(GCalRateLimitError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self):
        http = MockHttpClient([MockResponse(500, "Server error")])
        state = MockStateClient({"access_token": "tok"})
        client = GCalClient(http, state)

        with pytest.raises(GCalAPIError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.status_code == 500
