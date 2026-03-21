"""Unit tests for the Outlook Calendar API client (Microsoft Graph).

Loads ``outlook_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package.  All HTTP and state
interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Load outlook_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "outlook-calendar"
    / "services"
    / "outlook_client.py"
)


_AUTH_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "outlook-calendar"
    / "services"
    / "auth.py"
)


def _load_auth_module():
    """Load auth module first so outlook_client can import from it."""
    spec = importlib.util.spec_from_file_location("auth", _AUTH_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auth"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_module():
    # Auth module must be importable before loading the client
    _load_auth_module()
    spec = importlib.util.spec_from_file_location("outlook_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["outlook_client"] = mod
    spec.loader.exec_module(mod)
    return mod


oc = _load_module()
OutlookClient = oc.OutlookClient
OutlookAPIError = oc.OutlookAPIError
OutlookAuthError = oc.OutlookAuthError
OutlookRateLimitError = oc.OutlookRateLimitError
OUTLOOK_API_URL = oc.OUTLOOK_API_URL


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

    def _next_response(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        return self._next_response("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> MockResponse:
        return self._next_response("POST", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> MockResponse:
        return self._next_response("PATCH", url, **kwargs)


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
# Tests: Auth header injection
# ---------------------------------------------------------------------------

class TestAuthHeaderInjection:

    @pytest.mark.asyncio
    async def test_sends_bearer_token_header(self):
        http = MockHttpClient([
            MockResponse(200, {"value": []})
        ])
        state = MockStateClient({"access_token": "eyJ.valid_token"})
        client = OutlookClient(http, state)

        await client.get_calendar_list()

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer eyJ.valid_token"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_no_token_raises_auth_error(self):
        http = MockHttpClient()
        state = MockStateClient()
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAuthError, match="Not authenticated"):
            await client.get_calendar_list()


# ---------------------------------------------------------------------------
# Tests: Calendar list fetch
# ---------------------------------------------------------------------------

class TestGetCalendarList:

    @pytest.mark.asyncio
    async def test_single_page_returns_calendars(self):
        http = MockHttpClient([
            MockResponse(200, {
                "value": [
                    {
                        "id": "AAMkAGI2TGuLAAA=",
                        "name": "Calendar",
                        "isDefaultCalendar": True,
                        "canEdit": True,
                    },
                    {
                        "id": "AAMkAGI2TGuLBBB=",
                        "name": "Work",
                        "isDefaultCalendar": False,
                        "canEdit": True,
                    },
                ],
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        result = await client.get_calendar_list()

        assert len(result) == 2
        assert result[0]["id"] == "AAMkAGI2TGuLAAA="
        assert result[0]["name"] == "Calendar"
        assert result[0]["isDefaultCalendar"] is True
        assert result[0]["canEdit"] is True
        assert result[1]["id"] == "AAMkAGI2TGuLBBB="

    @pytest.mark.asyncio
    async def test_paginated_calendar_list(self):
        http = MockHttpClient([
            MockResponse(200, {
                "value": [
                    {"id": "cal1", "name": "Cal 1",
                     "isDefaultCalendar": True, "canEdit": True},
                ],
                "@odata.nextLink": f"{OUTLOOK_API_URL}/me/calendars?$skip=10",
            }),
            MockResponse(200, {
                "value": [
                    {"id": "cal2", "name": "Cal 2",
                     "isDefaultCalendar": False, "canEdit": False},
                ],
            }),
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        result = await client.get_calendar_list()

        assert len(result) == 2
        assert result[0]["id"] == "cal1"
        assert result[1]["id"] == "cal2"
        # Second request should use the @odata.nextLink URL
        assert "$skip=10" in http.calls[1]["url"]

    @pytest.mark.asyncio
    async def test_empty_calendar_list(self):
        http = MockHttpClient([MockResponse(200, {"value": []})])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        result = await client.get_calendar_list()

        assert result == []

    @pytest.mark.asyncio
    async def test_calendar_list_url(self):
        """Verify the correct Graph API URL is called."""
        http = MockHttpClient([MockResponse(200, {"value": []})])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        await client.get_calendar_list()

        assert http.calls[0]["url"] == f"{OUTLOOK_API_URL}/me/calendars"


# ---------------------------------------------------------------------------
# Tests: Delta query (events)
# ---------------------------------------------------------------------------

class TestGetEventsDelta:

    @pytest.mark.asyncio
    async def test_initial_full_sync(self):
        """First call without delta_link fetches all events."""
        http = MockHttpClient([
            MockResponse(200, {
                "value": [
                    {"id": "evt1", "subject": "Meeting"},
                    {"id": "evt2", "subject": "Lunch"},
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?token=abc",
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        events, delta_link = await client.get_events_delta("cal123")

        assert len(events) == 2
        assert events[0]["id"] == "evt1"
        assert events[1]["subject"] == "Lunch"
        assert delta_link == "https://graph.microsoft.com/v1.0/delta?token=abc"
        # Initial URL should target the specific calendar
        assert "/me/calendars/cal123/events/delta" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_incremental_sync_with_delta_link(self):
        """Subsequent call with delta_link returns only changes."""
        saved_delta = "https://graph.microsoft.com/v1.0/delta?token=prev"
        http = MockHttpClient([
            MockResponse(200, {
                "value": [
                    {"id": "evt3", "subject": "New Event"},
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?token=next",
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        events, delta_link = await client.get_events_delta("cal123", delta_link=saved_delta)

        assert len(events) == 1
        assert events[0]["id"] == "evt3"
        assert delta_link == "https://graph.microsoft.com/v1.0/delta?token=next"
        # Should use the provided delta link URL directly
        assert http.calls[0]["url"] == saved_delta

    @pytest.mark.asyncio
    async def test_delta_pagination_via_next_link(self):
        """Multiple pages linked via @odata.nextLink, deltaLink on last page."""
        http = MockHttpClient([
            MockResponse(200, {
                "value": [{"id": "evt1"}],
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/delta?page2",
            }),
            MockResponse(200, {
                "value": [{"id": "evt2"}],
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/delta?page3",
            }),
            MockResponse(200, {
                "value": [{"id": "evt3"}],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?token=final",
            }),
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        events, delta_link = await client.get_events_delta("cal123")

        assert len(events) == 3
        assert [e["id"] for e in events] == ["evt1", "evt2", "evt3"]
        assert delta_link == "https://graph.microsoft.com/v1.0/delta?token=final"
        assert len(http.calls) == 3

    @pytest.mark.asyncio
    async def test_delta_handles_deleted_events(self):
        """Deleted events have @removed key in the response."""
        http = MockHttpClient([
            MockResponse(200, {
                "value": [
                    {"id": "evt1", "subject": "Updated"},
                    {"id": "evt2", "@removed": {"reason": "deleted"}},
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?token=d",
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        events, delta_link = await client.get_events_delta("cal123")

        assert len(events) == 2
        assert events[1].get("@removed") == {"reason": "deleted"}

    @pytest.mark.asyncio
    async def test_delta_empty_result(self):
        """Delta query with no changes returns empty list and delta link."""
        http = MockHttpClient([
            MockResponse(200, {
                "value": [],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?token=same",
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        events, delta_link = await client.get_events_delta("cal123")

        assert events == []
        assert delta_link == "https://graph.microsoft.com/v1.0/delta?token=same"


# ---------------------------------------------------------------------------
# Tests: Patch event
# ---------------------------------------------------------------------------

class TestPatchEvent:

    @pytest.mark.asyncio
    async def test_patch_event_sends_correct_url_and_body(self):
        updated_event = {
            "id": "evt1",
            "responseStatus": {"response": "accepted", "time": "2026-03-19T12:00:00Z"},
        }
        http = MockHttpClient([MockResponse(200, updated_event)])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        result = await client.patch_event(
            "cal123", "evt1",
            {"responseStatus": {"response": "accepted"}},
        )

        assert result["responseStatus"]["response"] == "accepted"
        call = http.calls[0]
        assert call["method"] == "PATCH"
        assert "/me/calendars/cal123/events/evt1" in call["url"]
        assert call["json"] == {"responseStatus": {"response": "accepted"}}

    @pytest.mark.asyncio
    async def test_patch_event_error(self):
        http = MockHttpClient([MockResponse(404, {"error": {"message": "Not found"}})])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAPIError) as exc_info:
            await client.patch_event("cal123", "evt999", {"subject": "x"})
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: 401 → refresh → retry
# ---------------------------------------------------------------------------

class TestTokenRefreshOnUnauthorized:

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retry(self):
        """On 401 with valid refresh, refresh then retry the request."""
        http = MockHttpClient([
            # First attempt: 401
            MockResponse(401, "Unauthorized"),
            # Token refresh call (from auth.refresh_if_expired)
            MockResponse(200, {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            }),
            # Retry attempt: success
            MockResponse(200, {
                "value": [
                    {"id": "cal1", "name": "My Calendar",
                     "isDefaultCalendar": True, "canEdit": True},
                ],
            }),
        ])
        state = MockStateClient({
            "access_token": "old_access_token",
            "refresh_token": "old_refresh_token",
        })
        client = OutlookClient(http, state, client_id="cid", client_secret="csecret")

        result = await client.get_calendar_list()

        assert len(result) == 1
        assert result[0]["id"] == "cal1"
        # Verify 3 HTTP calls: original request, token refresh, retry
        assert len(http.calls) == 3

    @pytest.mark.asyncio
    async def test_401_no_refresh_token_raises(self):
        """401 without a refresh token raises immediately."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),
        ])
        state = MockStateClient({"access_token": "expired_tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAuthError):
            await client.get_calendar_list()

    @pytest.mark.asyncio
    async def test_no_infinite_refresh_loop(self):
        """If retry after refresh also returns 401, stop — don't loop."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),  # first attempt
            # Token refresh succeeds
            MockResponse(200, {
                "access_token": "new_tok",
                "expires_in": 3600,
            }),
            MockResponse(401, "Still unauthorized"),  # retry also 401
        ])
        state = MockStateClient({
            "access_token": "old",
            "refresh_token": "ref",
        })
        client = OutlookClient(http, state, client_id="c", client_secret="s")

        with pytest.raises(OutlookAuthError, match="Unauthorized after token refresh"):
            await client.get_calendar_list()

        # 3 HTTP calls: original, refresh, retry
        assert len(http.calls) == 3


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        http = MockHttpClient([MockResponse(403, "Forbidden")])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAuthError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_with_retry_after(self):
        http = MockHttpClient([
            MockResponse(429, "Too many requests", {"Retry-After": "30"})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookRateLimitError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.retry_after == 30
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_defaults_retry_after_to_60(self):
        http = MockHttpClient([MockResponse(429, "Too many requests")])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookRateLimitError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self):
        http = MockHttpClient([MockResponse(500, "Server error")])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAPIError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_400_raises_api_error(self):
        http = MockHttpClient([MockResponse(400, {"error": {"message": "Bad request"}})])
        state = MockStateClient({"access_token": "tok"})
        client = OutlookClient(http, state)

        with pytest.raises(OutlookAPIError) as exc_info:
            await client.get_calendar_list()
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:

    def test_auth_error_is_api_error(self):
        err = OutlookAuthError("auth failed", status_code=401)
        assert isinstance(err, OutlookAPIError)

    def test_rate_limit_error_is_api_error(self):
        err = OutlookRateLimitError("limited", retry_after=30)
        assert isinstance(err, OutlookAPIError)

    def test_api_error_has_fields(self):
        err = OutlookAPIError("msg", status_code=500, response_body="body")
        assert err.message == "msg"
        assert err.status_code == 500
        assert err.response_body == "body"
