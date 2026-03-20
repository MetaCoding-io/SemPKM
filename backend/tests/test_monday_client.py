"""Unit tests for the Monday.com GraphQL client.

Loads ``monday_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package.  All HTTP and state
interactions are mocked — no network calls are made.

Uses ``asyncio.run()`` to execute async tests without requiring pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load monday_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "monday-sync"
    / "services"
    / "monday_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("monday_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["monday_client"] = mod
    spec.loader.exec_module(mod)
    return mod


mc = _load_module()
MondayClient = mc.MondayClient
MondayApiError = mc.MondayApiError
MondayAuthError = mc.MondayAuthError
MondayRateLimitError = mc.MondayRateLimitError
MondayComplexityError = mc.MondayComplexityError


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: dict | list | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        # K002: use `is not None` to avoid falsy empty-list bug
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

    async def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})


class MockStateClient:
    """In-memory state store."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_TOKEN = "eyJhbGciOiJIUzI1NiJ9.test_token_value.signature"
_DEFAULT_CREDS = {"monday_api_token": _DEFAULT_TOKEN}


def _gql_ok(data: Any, complexity: dict | None = None) -> MockResponse:
    """200 OK GraphQL response wrapping data in ``{"data": ...}``."""
    body: dict[str, Any] = {"data": data}
    if complexity:
        body["complexity"] = complexity
    return MockResponse(200, body)


def _gql_error(
    message: str,
    extensions: dict | None = None,
    complexity: dict | None = None,
) -> MockResponse:
    """200 OK GraphQL response with errors array."""
    error: dict[str, Any] = {"message": message}
    if extensions:
        error["extensions"] = extensions
    body: dict[str, Any] = {"errors": [error], "data": None}
    if complexity:
        body["complexity"] = complexity
    return MockResponse(200, body)


def _make_client(
    responses: list[MockResponse],
    creds: dict[str, str] | None = None,
) -> tuple[MondayClient, MockHttpClient, MockStateClient]:
    """Create a client with mocked HTTP and state."""
    http = MockHttpClient(responses)
    state = MockStateClient(creds if creds is not None else _DEFAULT_CREDS)
    client = MondayClient(http, state)
    return client, http, state


# ===========================================================================
# Tests: Error hierarchy structure
# ===========================================================================

class TestErrorHierarchy:

    def test_monday_auth_error_is_subclass(self):
        assert issubclass(MondayAuthError, MondayApiError)

    def test_monday_rate_limit_error_is_subclass(self):
        assert issubclass(MondayRateLimitError, MondayApiError)

    def test_monday_complexity_error_is_subclass(self):
        assert issubclass(MondayComplexityError, MondayApiError)

    def test_base_error_is_exception(self):
        assert issubclass(MondayApiError, Exception)

    def test_base_error_attributes(self):
        err = MondayApiError("oops", status_code=400, response_body='{"err": true}')
        assert err.message == "oops"
        assert err.status_code == 400
        assert err.response_body == '{"err": true}'

    def test_rate_limit_error_retry_after(self):
        err = MondayRateLimitError("slow down", retry_after=30)
        assert err.retry_after == 30

    def test_complexity_error_reset_in_seconds(self):
        err = MondayComplexityError("too complex", reset_in_seconds=25)
        assert err.reset_in_seconds == 25


# ===========================================================================
# Tests: Auth header
# ===========================================================================

class TestAuthHeader:

    def test_auth_header_uses_raw_token(self):
        """Auth header is raw token — no Bearer prefix."""
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == _DEFAULT_TOKEN
        assert "Bearer" not in headers["Authorization"]

    def test_content_type_json(self):
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        assert http.calls[0]["headers"]["Content-Type"] == "application/json"

    def test_missing_token_raises_auth_error(self):
        """No token in state raises MondayAuthError before any HTTP call."""
        client, http, _ = _make_client([], creds={})
        with pytest.raises(MondayAuthError, match="Not authenticated"):
            _run(client.get_me())
        assert len(http.calls) == 0

    def test_empty_token_raises_auth_error(self):
        """Empty string token raises MondayAuthError."""
        client, http, _ = _make_client([], creds={"monday_api_token": ""})
        with pytest.raises(MondayAuthError, match="Not authenticated"):
            _run(client.get_me())
        assert len(http.calls) == 0


# ===========================================================================
# Tests: HTTP error handling
# ===========================================================================

class TestHttpErrors:

    def test_401_raises_auth_error(self):
        client, _, _ = _make_client([MockResponse(401, "Unauthorized")])
        with pytest.raises(MondayAuthError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.status_code == 401

    def test_429_raises_rate_limit_with_retry_after(self):
        client, _, _ = _make_client([
            MockResponse(429, "Rate limited", {"Retry-After": "30"}),
        ])
        with pytest.raises(MondayRateLimitError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 30

    def test_429_without_retry_after_defaults_60(self):
        client, _, _ = _make_client([MockResponse(429, "Rate limited")])
        with pytest.raises(MondayRateLimitError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.retry_after == 60

    def test_429_invalid_retry_after_defaults_60(self):
        client, _, _ = _make_client([
            MockResponse(429, "Rate limited", {"Retry-After": "not-a-number"}),
        ])
        with pytest.raises(MondayRateLimitError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.retry_after == 60

    def test_500_raises_api_error(self):
        client, _, _ = _make_client([MockResponse(500, "Internal Server Error")])
        with pytest.raises(MondayApiError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.status_code == 500
        assert not isinstance(exc_info.value, MondayAuthError)

    def test_403_raises_api_error(self):
        client, _, _ = _make_client([MockResponse(403, "Forbidden")])
        with pytest.raises(MondayApiError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.status_code == 403

    def test_error_carries_response_body(self):
        client, _, _ = _make_client([
            MockResponse(400, {"error": "bad request"}),
        ])
        with pytest.raises(MondayApiError) as exc_info:
            _run(client.get_me())
        assert "bad request" in exc_info.value.response_body


# ===========================================================================
# Tests: GraphQL error handling
# ===========================================================================

class TestGraphQLErrors:

    def test_generic_graphql_error_raises_api_error(self):
        client, _, _ = _make_client([
            _gql_error("Field 'nonexistent' doesn't exist"),
        ])
        with pytest.raises(MondayApiError) as exc_info:
            _run(client.get_me())
        assert "nonexistent" in str(exc_info.value)
        assert not isinstance(exc_info.value, MondayComplexityError)

    def test_complexity_error_by_extensions_code(self):
        """Complexity error detected via extensions.code == COMPLEXITY."""
        client, _, _ = _make_client([
            _gql_error(
                "Budget exhausted",
                extensions={"code": "COMPLEXITY", "reset_in_x_seconds": 42},
            ),
        ])
        with pytest.raises(MondayComplexityError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.reset_in_seconds == 42

    def test_complexity_error_by_message_keyword(self):
        """Complexity error detected via message containing 'complexity'."""
        client, _, _ = _make_client([
            _gql_error("Complexity budget exceeded, retry later"),
        ])
        with pytest.raises(MondayComplexityError):
            _run(client.get_me())

    def test_complexity_error_uses_top_level_complexity_field(self):
        """reset_in_seconds prefers top-level complexity field."""
        client, _, _ = _make_client([
            _gql_error(
                "Complexity budget exceeded",
                extensions={"code": "COMPLEXITY", "reset_in_x_seconds": 10},
                complexity={"after": 0, "reset_in_x_seconds": 55},
            ),
        ])
        with pytest.raises(MondayComplexityError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.reset_in_seconds == 55

    def test_complexity_error_without_reset_defaults_60(self):
        """When no reset_in_x_seconds is provided, default to 60."""
        client, _, _ = _make_client([
            _gql_error(
                "Complexity budget exceeded",
                extensions={"code": "COMPLEXITY"},
            ),
        ])
        with pytest.raises(MondayComplexityError) as exc_info:
            _run(client.get_me())
        assert exc_info.value.reset_in_seconds == 60


# ===========================================================================
# Tests: get_me
# ===========================================================================

class TestGetMe:

    def test_get_me_success(self):
        user = {"id": "12345", "name": "Test User", "email": "test@example.com"}
        client, http, _ = _make_client([_gql_ok({"me": user})])
        result = _run(client.get_me())
        assert result == user
        assert http.calls[0]["method"] == "POST"

    def test_get_me_query_shape(self):
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        payload = http.calls[0]["json"]
        assert "me" in payload["query"]
        assert "id" in payload["query"]
        assert "name" in payload["query"]
        assert "email" in payload["query"]


# ===========================================================================
# Tests: get_boards
# ===========================================================================

class TestGetBoards:

    def test_get_boards_success(self):
        boards = [
            {"id": "100", "name": "Sprint Board", "state": "active"},
            {"id": "101", "name": "Backlog", "state": "active"},
        ]
        client, _, _ = _make_client([_gql_ok({"boards": boards})])
        result = _run(client.get_boards())
        assert len(result) == 2
        assert result[0]["name"] == "Sprint Board"

    def test_get_boards_empty(self):
        client, _, _ = _make_client([_gql_ok({"boards": []})])
        result = _run(client.get_boards())
        assert result == []

    def test_get_boards_query_filters_active(self):
        client, http, _ = _make_client([_gql_ok({"boards": []})])
        _run(client.get_boards())
        query = http.calls[0]["json"]["query"]
        assert "active" in query.lower() or "state" in query.lower()


# ===========================================================================
# Tests: get_board_columns
# ===========================================================================

class TestGetBoardColumns:

    def test_get_board_columns_success(self):
        columns = [
            {"id": "status", "title": "Status", "type": "status", "settings_str": "{}"},
            {"id": "text0", "title": "Notes", "type": "text", "settings_str": "{}"},
        ]
        client, _, _ = _make_client([
            _gql_ok({"boards": [{"columns": columns}]}),
        ])
        result = _run(client.get_board_columns(100))
        assert len(result) == 2
        assert result[0]["id"] == "status"
        assert result[1]["type"] == "text"

    def test_get_board_columns_empty_board(self):
        client, _, _ = _make_client([_gql_ok({"boards": []})])
        result = _run(client.get_board_columns(999))
        assert result == []

    def test_get_board_columns_includes_settings(self):
        settings = '{"labels": {"1": "Done"}}'
        columns = [{"id": "s", "title": "S", "type": "status", "settings_str": settings}]
        client, _, _ = _make_client([_gql_ok({"boards": [{"columns": columns}]})])
        result = _run(client.get_board_columns(100))
        assert result[0]["settings_str"] == settings


# ===========================================================================
# Tests: get_board_groups
# ===========================================================================

class TestGetBoardGroups:

    def test_get_board_groups_success(self):
        groups = [
            {"id": "new_group", "title": "New"},
            {"id": "top_group", "title": "Done"},
        ]
        client, _, _ = _make_client([_gql_ok({"boards": [{"groups": groups}]})])
        result = _run(client.get_board_groups(100))
        assert len(result) == 2
        assert result[0]["id"] == "new_group"

    def test_get_board_groups_empty_board(self):
        client, _, _ = _make_client([_gql_ok({"boards": []})])
        result = _run(client.get_board_groups(999))
        assert result == []


# ===========================================================================
# Tests: get_board_items
# ===========================================================================

class TestGetBoardItems:

    def test_single_page_items(self):
        items_page = {
            "cursor": None,
            "items": [
                {"id": "1", "name": "Task A", "column_values": []},
                {"id": "2", "name": "Task B", "column_values": []},
            ],
        }
        client, _, _ = _make_client([
            _gql_ok({"boards": [{"items_page": items_page}]}),
        ])
        result = _run(client.get_board_items(100))
        assert len(result["items"]) == 2
        assert result["cursor"] is None

    def test_items_with_cursor(self):
        items_page = {
            "cursor": "abc123cursor",
            "items": [{"id": "1", "name": "Task A", "column_values": []}],
        }
        client, _, _ = _make_client([
            _gql_ok({"boards": [{"items_page": items_page}]}),
        ])
        result = _run(client.get_board_items(100))
        assert result["cursor"] == "abc123cursor"
        assert len(result["items"]) == 1

    def test_items_with_cursor_parameter(self):
        """When cursor is passed, it's included in the query."""
        items_page = {"cursor": None, "items": []}
        client, http, _ = _make_client([
            _gql_ok({"boards": [{"items_page": items_page}]}),
        ])
        _run(client.get_board_items(100, cursor="prev_cursor"))
        query = http.calls[0]["json"]["query"]
        assert "prev_cursor" in query

    def test_empty_items(self):
        items_page = {"cursor": None, "items": []}
        client, _, _ = _make_client([
            _gql_ok({"boards": [{"items_page": items_page}]}),
        ])
        result = _run(client.get_board_items(100))
        assert result["items"] == []
        assert result["cursor"] is None

    def test_empty_boards_returns_empty(self):
        client, _, _ = _make_client([_gql_ok({"boards": []})])
        result = _run(client.get_board_items(999))
        assert result["items"] == []
        assert result["cursor"] is None


# ===========================================================================
# Tests: get_all_board_items (paginated)
# ===========================================================================

class TestGetAllBoardItems:

    def test_single_page_all_items(self):
        items_page = {
            "cursor": None,
            "items": [{"id": "1"}, {"id": "2"}],
        }
        client, http, _ = _make_client([
            _gql_ok({"boards": [{"items_page": items_page}]}),
        ])
        result = _run(client.get_all_board_items(100))
        assert len(result) == 2
        assert len(http.calls) == 1

    def test_multi_page_aggregation(self):
        """Collects items across 3 pages."""
        client, http, _ = _make_client([
            _gql_ok({"boards": [{"items_page": {
                "cursor": "cursor_page2",
                "items": [{"id": "1"}, {"id": "2"}],
            }}]}),
            _gql_ok({"boards": [{"items_page": {
                "cursor": "cursor_page3",
                "items": [{"id": "3"}, {"id": "4"}],
            }}]}),
            _gql_ok({"boards": [{"items_page": {
                "cursor": None,
                "items": [{"id": "5"}],
            }}]}),
        ])
        result = _run(client.get_all_board_items(100))
        assert len(result) == 5
        assert len(http.calls) == 3

    def test_safety_limit_stops_pagination(self):
        """Stops at MAX_PAGINATION_PAGES even if cursor keeps returning."""
        responses = []
        for i in range(55):
            responses.append(_gql_ok({"boards": [{"items_page": {
                "cursor": f"cursor_{i+1}",
                "items": [{"id": str(i)}],
            }}]}))
        client, http, _ = _make_client(responses)
        result = _run(client.get_all_board_items(100))
        assert len(result) == 50
        assert len(http.calls) == 50

    def test_empty_board_returns_empty(self):
        client, _, _ = _make_client([
            _gql_ok({"boards": [{"items_page": {
                "cursor": None,
                "items": [],
            }}]}),
        ])
        result = _run(client.get_all_board_items(100))
        assert result == []


# ===========================================================================
# Tests: get_users
# ===========================================================================

class TestGetUsers:

    def test_get_users_single(self):
        users = [{"id": "100", "name": "Alice", "email": "alice@test.com"}]
        client, _, _ = _make_client([_gql_ok({"users": users})])
        result = _run(client.get_users([100]))
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_get_users_multiple(self):
        users = [
            {"id": "100", "name": "Alice", "email": "alice@test.com"},
            {"id": "200", "name": "Bob", "email": "bob@test.com"},
        ]
        client, _, _ = _make_client([_gql_ok({"users": users})])
        result = _run(client.get_users([100, 200]))
        assert len(result) == 2

    def test_get_users_empty(self):
        client, _, _ = _make_client([_gql_ok({"users": []})])
        result = _run(client.get_users([999]))
        assert result == []

    def test_get_users_ids_in_query(self):
        client, http, _ = _make_client([_gql_ok({"users": []})])
        _run(client.get_users([42, 99]))
        query = http.calls[0]["json"]["query"]
        assert "42" in query
        assert "99" in query


# ===========================================================================
# Tests: get_tags
# ===========================================================================

class TestGetTags:

    def test_get_tags_single(self):
        tags = [{"id": "10", "name": "urgent"}]
        client, _, _ = _make_client([_gql_ok({"tags": tags})])
        result = _run(client.get_tags([10]))
        assert len(result) == 1
        assert result[0]["name"] == "urgent"

    def test_get_tags_multiple(self):
        tags = [
            {"id": "10", "name": "urgent"},
            {"id": "20", "name": "backend"},
        ]
        client, _, _ = _make_client([_gql_ok({"tags": tags})])
        result = _run(client.get_tags([10, 20]))
        assert len(result) == 2

    def test_get_tags_empty(self):
        client, _, _ = _make_client([_gql_ok({"tags": []})])
        result = _run(client.get_tags([999]))
        assert result == []


# ===========================================================================
# Tests: change_multiple_column_values (mutation)
# ===========================================================================

class TestChangeColumnValues:

    def test_change_column_values_success(self):
        client, http, _ = _make_client([
            _gql_ok({"change_multiple_column_values": {"id": "1", "name": "Item"}}),
        ])
        col_json = '{"status": {"label": "Done"}}'
        result = _run(client.change_multiple_column_values(100, 1, col_json))
        assert result["id"] == "1"
        query = http.calls[0]["json"]["query"]
        assert "change_multiple_column_values" in query
        assert "mutation" in query

    def test_change_column_values_includes_board_and_item(self):
        client, http, _ = _make_client([
            _gql_ok({"change_multiple_column_values": {"id": "42", "name": "X"}}),
        ])
        _run(client.change_multiple_column_values(200, 42, '{}'))
        query = http.calls[0]["json"]["query"]
        assert "200" in query
        assert "42" in query


# ===========================================================================
# Tests: create_item (mutation)
# ===========================================================================

class TestCreateItem:

    def test_create_item_success(self):
        client, http, _ = _make_client([
            _gql_ok({"create_item": {"id": "99", "name": "New Task"}}),
        ])
        result = _run(client.create_item(100, "group1", "New Task", '{"status": {"label": "Working"}}'))
        assert result["id"] == "99"
        assert result["name"] == "New Task"
        query = http.calls[0]["json"]["query"]
        assert "create_item" in query
        assert "mutation" in query

    def test_create_item_without_column_values(self):
        client, http, _ = _make_client([
            _gql_ok({"create_item": {"id": "100", "name": "Simple"}}),
        ])
        result = _run(client.create_item(100, "group1", "Simple"))
        assert result["id"] == "100"
        query = http.calls[0]["json"]["query"]
        assert "column_values" not in query

    def test_create_item_includes_group_and_name(self):
        client, http, _ = _make_client([
            _gql_ok({"create_item": {"id": "1", "name": "T"}}),
        ])
        _run(client.create_item(200, "my_group", "My Task"))
        query = http.calls[0]["json"]["query"]
        assert "my_group" in query
        assert "My Task" in query


# ===========================================================================
# Tests: MONDAY_API_URL env override
# ===========================================================================

class TestApiUrlOverride:

    def test_default_url(self):
        """Default URL is Monday.com production."""
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        url = http.calls[0]["url"]
        # URL is what the module constant evaluates to at import time
        assert url == mc.MONDAY_API_URL

    def test_env_override(self, monkeypatch):
        """MONDAY_API_URL env var overrides the API endpoint."""
        monkeypatch.setattr(mc, "MONDAY_API_URL", "http://localhost:9999/graphql")
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        assert http.calls[0]["url"] == "http://localhost:9999/graphql"


# ===========================================================================
# Tests: Complexity tracking (logged at DEBUG)
# ===========================================================================

class TestComplexityTracking:

    def test_complexity_logged_from_response(self, caplog):
        """Complexity info is logged at DEBUG level when present."""
        import logging
        with caplog.at_level(logging.DEBUG, logger="monday_sync.client"):
            client, _, _ = _make_client([
                _gql_ok(
                    {"me": {"id": "1"}},
                    complexity={"after": 9500000, "reset_in_x_seconds": 30},
                ),
            ])
            _run(client.get_me())
        assert any("9500000" in r.message for r in caplog.records)
        assert any("30" in r.message for r in caplog.records)

    def test_no_complexity_field_is_fine(self):
        """Responses without complexity field don't error."""
        client, _, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        result = _run(client.get_me())
        assert result["id"] == "1"


# ===========================================================================
# Tests: Request payload structure
# ===========================================================================

class TestRequestPayload:

    def test_posts_to_api_url(self):
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        assert http.calls[0]["method"] == "POST"

    def test_payload_has_query_key(self):
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        payload = http.calls[0]["json"]
        assert "query" in payload

    def test_variables_omitted_when_none(self):
        """Variables key is not sent when there are no variables."""
        client, http, _ = _make_client([_gql_ok({"me": {"id": "1"}})])
        _run(client.get_me())
        payload = http.calls[0]["json"]
        # Our convenience methods don't pass variables, so it shouldn't be in the payload
        assert "variables" not in payload


# ===========================================================================
# Tests: Mock helpers correctness (K002)
# ===========================================================================

class TestMockHelpers:

    def test_mock_response_empty_list_preserved(self):
        """K002: empty list body is preserved, not replaced with {}."""
        resp = MockResponse(200, [])
        assert resp.json() == []

    def test_mock_response_none_body_defaults_to_dict(self):
        resp = MockResponse(200)
        assert resp.json() == {}

    def test_mock_response_zero_body_preserved(self):
        resp = MockResponse(200, {"count": 0})
        assert resp.json()["count"] == 0
