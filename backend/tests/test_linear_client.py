"""Unit tests for the Linear API client.

Loads ``linear_client.py`` from the apps directory using importlib to avoid
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
# Load linear_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "linear-sync"
    / "services"
    / "linear_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("linear_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["linear_client"] = mod
    spec.loader.exec_module(mod)
    return mod


lc = _load_module()
LinearClient = lc.LinearClient
LinearAPIError = lc.LinearAPIError
LinearAuthError = lc.LinearAuthError
LinearRateLimitError = lc.LinearRateLimitError
LinearQueryError = lc.LinearQueryError
LINEAR_GRAPHQL_URL = lc.LINEAR_GRAPHQL_URL
LINEAR_TOKEN_URL = lc.LINEAR_TOKEN_URL


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
# Fixtures
# ---------------------------------------------------------------------------

def _graphql_ok(data: dict) -> MockResponse:
    return MockResponse(200, {"data": data})


def _graphql_error(message: str) -> MockResponse:
    return MockResponse(200, {"data": None, "errors": [{"message": message}]})


# ---------------------------------------------------------------------------
# Tests: Query construction
# ---------------------------------------------------------------------------

class TestQueryConstruction:
    """Verify correct URL, payload, and headers on outgoing requests."""

    @pytest.mark.asyncio
    async def test_sends_to_graphql_endpoint(self):
        http = MockHttpClient([_graphql_ok({"viewer": {"id": "1"}})])
        state = MockStateClient({"access_token": "tok_abc"})
        client = LinearClient(http, state)

        await client.query("{ viewer { id } }")

        assert len(http.calls) == 1
        assert http.calls[0]["url"] == LINEAR_GRAPHQL_URL

    @pytest.mark.asyncio
    async def test_sends_json_payload_with_query_and_variables(self):
        http = MockHttpClient([_graphql_ok({"x": 1})])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        await client.query("query($id: ID!) { issue(id: $id) { id } }", {"id": "123"})

        payload = http.calls[0]["json"]
        assert payload["query"] == "query($id: ID!) { issue(id: $id) { id } }"
        assert payload["variables"] == {"id": "123"}

    @pytest.mark.asyncio
    async def test_sends_authorization_header(self):
        http = MockHttpClient([_graphql_ok({"v": 1})])
        state = MockStateClient({"access_token": "my_token"})
        client = LinearClient(http, state)

        await client.query("{ viewer { id } }")

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer my_token"


# ---------------------------------------------------------------------------
# Tests: Auth header
# ---------------------------------------------------------------------------

class TestAuthHeader:
    """Verify OAuth token priority and API key fallback."""

    @pytest.mark.asyncio
    async def test_api_key_fallback_when_no_access_token(self):
        http = MockHttpClient([_graphql_ok({"v": 1})])
        state = MockStateClient({"api_key": "lin_api_key123"})
        client = LinearClient(http, state)

        await client.query("{ viewer { id } }")

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer lin_api_key123"

    @pytest.mark.asyncio
    async def test_access_token_takes_priority_over_api_key(self):
        http = MockHttpClient([_graphql_ok({"v": 1})])
        state = MockStateClient({"access_token": "oauth_tok", "api_key": "api_key"})
        client = LinearClient(http, state)

        await client.query("{ viewer { id } }")

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer oauth_tok"

    @pytest.mark.asyncio
    async def test_error_when_no_credentials(self):
        http = MockHttpClient()
        state = MockStateClient()
        client = LinearClient(http, state)

        with pytest.raises(LinearAuthError, match="Not authenticated"):
            await client.query("{ viewer { id } }")


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_401_raises_auth_error_with_api_key(self):
        """401 with API key auth (no refresh token) raises LinearAuthError."""
        http = MockHttpClient([MockResponse(401, "Unauthorized")])
        state = MockStateClient({"api_key": "key123"})
        client = LinearClient(http, state)

        with pytest.raises(LinearAuthError, match="Token refresh not available"):
            await client.query("{ viewer { id } }")

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error_with_retry_after(self):
        http = MockHttpClient([
            MockResponse(429, "Too many requests", {"Retry-After": "30"})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        with pytest.raises(LinearRateLimitError) as exc_info:
            await client.query("{ viewer { id } }")
        assert exc_info.value.retry_after == 30
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_defaults_retry_after_to_60(self):
        http = MockHttpClient([MockResponse(429, "Too many requests")])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        with pytest.raises(LinearRateLimitError) as exc_info:
            await client.query("{ viewer { id } }")
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self):
        http = MockHttpClient([MockResponse(500, "Server error")])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        with pytest.raises(LinearAPIError) as exc_info:
            await client.query("{ viewer { id } }")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        http = MockHttpClient([MockResponse(403, "Forbidden")])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        with pytest.raises(LinearAuthError) as exc_info:
            await client.query("{ viewer { id } }")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_graphql_errors_raise_query_error(self):
        http = MockHttpClient([_graphql_error("Field 'xyz' not found")])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        with pytest.raises(LinearQueryError, match="Field 'xyz' not found"):
            await client.query("{ xyz }")


# ---------------------------------------------------------------------------
# Tests: Token refresh
# ---------------------------------------------------------------------------

class TestTokenRefresh:

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retry(self):
        """On 401 with OAuth tokens, refresh then retry the query."""
        http = MockHttpClient([
            # First attempt: 401
            MockResponse(401, "Unauthorized"),
            # Refresh token request: success
            MockResponse(200, {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
            }),
            # Retry attempt: success
            _graphql_ok({"viewer": {"id": "42"}}),
        ])
        state = MockStateClient({
            "access_token": "old_access",
            "refresh_token": "old_refresh",
        })
        client = LinearClient(http, state, client_id="cid", client_secret="csecret")

        result = await client.query("{ viewer { id } }")

        assert result == {"viewer": {"id": "42"}}
        # Verify refresh call was made
        refresh_call = http.calls[1]
        assert refresh_call["url"] == LINEAR_TOKEN_URL
        assert refresh_call["data"]["grant_type"] == "refresh_token"
        assert refresh_call["data"]["client_id"] == "cid"
        assert refresh_call["data"]["client_secret"] == "csecret"
        # Verify new tokens were stored
        assert ("access_token", "new_access") in state.set_calls
        assert ("refresh_token", "new_refresh") in state.set_calls

    @pytest.mark.asyncio
    async def test_refresh_failure_propagates(self):
        """If the refresh token endpoint fails, error propagates."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),
            MockResponse(400, "Invalid grant"),
        ])
        state = MockStateClient({
            "access_token": "old",
            "refresh_token": "bad_refresh",
        })
        client = LinearClient(http, state, client_id="c", client_secret="s")

        with pytest.raises(LinearAuthError, match="Token refresh failed"):
            await client.query("{ viewer { id } }")

    @pytest.mark.asyncio
    async def test_refresh_skipped_for_api_key_auth(self):
        """401 with API key auth raises immediately, no refresh attempt."""
        http = MockHttpClient([MockResponse(401, "Unauthorized")])
        state = MockStateClient({"api_key": "key"})
        client = LinearClient(http, state)

        with pytest.raises(LinearAuthError, match="Token refresh not available"):
            await client.query("{ viewer { id } }")

        # Only one HTTP call (the query), no refresh attempt
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_no_infinite_refresh_loop(self):
        """If retry after refresh also returns 401, stop — don't loop."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),  # first attempt
            MockResponse(200, {"access_token": "new", "refresh_token": "new_r"}),  # refresh OK
            MockResponse(401, "Still unauthorized"),  # retry also 401
        ])
        state = MockStateClient({
            "access_token": "old",
            "refresh_token": "rr",
        })
        client = LinearClient(http, state, client_id="c", client_secret="s")

        # The second 401 should raise, NOT trigger another refresh
        with pytest.raises(LinearAuthError):
            await client.query("{ viewer { id } }")

        # Should have exactly 3 HTTP calls: query, refresh, retry
        assert len(http.calls) == 3


# ---------------------------------------------------------------------------
# Tests: Pagination
# ---------------------------------------------------------------------------

class TestPagination:

    @pytest.mark.asyncio
    async def test_single_page(self):
        http = MockHttpClient([
            _graphql_ok({
                "issues": {
                    "nodes": [{"id": "1"}, {"id": "2"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }),
        ])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.query_paginated(
            "query($after: String) { issues(after: $after) { nodes { id } pageInfo { hasNextPage endCursor } } }",
            None,
            "issues.nodes",
            "issues.pageInfo",
        )

        assert result == [{"id": "1"}, {"id": "2"}]
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_multi_page_cursor_chaining(self):
        http = MockHttpClient([
            _graphql_ok({
                "issues": {
                    "nodes": [{"id": "1"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_1"},
                }
            }),
            _graphql_ok({
                "issues": {
                    "nodes": [{"id": "2"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_2"},
                }
            }),
            _graphql_ok({
                "issues": {
                    "nodes": [{"id": "3"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }),
        ])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.query_paginated(
            "query($after: String) { issues(after: $after) { nodes { id } pageInfo { hasNextPage endCursor } } }",
            None,
            "issues.nodes",
            "issues.pageInfo",
        )

        assert result == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        assert len(http.calls) == 3
        # Second call should have cursor
        assert http.calls[1]["json"]["variables"]["after"] == "cursor_1"
        # Third call should have cursor_2
        assert http.calls[2]["json"]["variables"]["after"] == "cursor_2"

    @pytest.mark.asyncio
    async def test_safety_limit_at_50_pages(self):
        """Pagination stops at 50 pages even if hasNextPage is True."""
        responses = []
        for i in range(55):
            responses.append(_graphql_ok({
                "items": {
                    "nodes": [{"id": str(i)}],
                    "pageInfo": {"hasNextPage": True, "endCursor": f"c{i}"},
                }
            }))
        http = MockHttpClient(responses)
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.query_paginated(
            "query($after: String) { items(after: $after) { nodes { id } pageInfo { hasNextPage endCursor } } }",
            None,
            "items.nodes",
            "items.pageInfo",
        )

        assert len(result) == 50
        assert len(http.calls) == 50


# ---------------------------------------------------------------------------
# Tests: Convenience methods
# ---------------------------------------------------------------------------

class TestConvenienceMethods:

    @pytest.mark.asyncio
    async def test_get_viewer(self):
        http = MockHttpClient([
            _graphql_ok({"viewer": {"id": "u1", "name": "Alice", "email": "a@b.com"}})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.get_viewer()

        assert result == {"id": "u1", "name": "Alice", "email": "a@b.com"}

    @pytest.mark.asyncio
    async def test_get_teams(self):
        teams = [
            {"id": "t1", "name": "Eng", "key": "ENG", "description": "Engineering"},
            {"id": "t2", "name": "Design", "key": "DES", "description": "Design team"},
        ]
        http = MockHttpClient([_graphql_ok({"teams": {"nodes": teams}})])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.get_teams()

        assert result == teams

    @pytest.mark.asyncio
    async def test_get_organization(self):
        org = {"id": "org1", "name": "Acme", "urlKey": "acme"}
        http = MockHttpClient([_graphql_ok({"organization": org})])
        state = MockStateClient({"access_token": "tok"})
        client = LinearClient(http, state)

        result = await client.get_organization()

        assert result == org
