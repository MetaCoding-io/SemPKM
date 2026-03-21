"""Unit tests for the Asana REST API client.

Loads ``asana_client.py`` from the apps directory using importlib to avoid
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
# Load asana_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "asana-sync"
    / "services"
    / "asana_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("asana_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["asana_client"] = mod
    spec.loader.exec_module(mod)
    return mod


ac = _load_module()
AsanaClient = ac.AsanaClient
AsanaAPIError = ac.AsanaAPIError
AsanaAuthError = ac.AsanaAuthError
AsanaRateLimitError = ac.AsanaRateLimitError
ASANA_BASE_URL = ac.ASANA_BASE_URL


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

    def _next_response(self) -> MockResponse:
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._next_response()

    async def post(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._next_response()

    async def patch(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "PATCH", "url": url, **kwargs})
        return self._next_response()


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

class TestGetHeaders:

    @pytest.mark.asyncio
    async def test_returns_bearer_token(self):
        http = MockHttpClient()
        state = MockStateClient({"access_token": "xoxp-asana-token"})
        client = AsanaClient(http, state)

        headers = await client._get_headers()

        assert headers["Authorization"] == "Bearer xoxp-asana-token"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_no_token_raises_auth_error(self):
        http = MockHttpClient()
        state = MockStateClient()
        client = AsanaClient(http, state)

        with pytest.raises(AsanaAuthError, match="Not authenticated"):
            await client._get_headers()


# ---------------------------------------------------------------------------
# Tests: _request / _raw_request
# ---------------------------------------------------------------------------

class TestRequest:

    @pytest.mark.asyncio
    async def test_200_extracts_data_wrapper(self):
        """_request unwraps the {"data": ...} envelope."""
        http = MockHttpClient([
            MockResponse(200, {"data": {"gid": "123", "name": "Test"}})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client._request("GET", f"{ASANA_BASE_URL}/test")

        assert result == {"gid": "123", "name": "Test"}

    @pytest.mark.asyncio
    async def test_200_list_data_wrapper(self):
        """_request unwraps list data too."""
        http = MockHttpClient([
            MockResponse(200, {"data": [{"gid": "1"}, {"gid": "2"}]})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client._request("GET", f"{ASANA_BASE_URL}/test")

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retry(self):
        http = MockHttpClient([
            # First attempt: 401
            MockResponse(401, "Unauthorized"),
            # Refresh token request: success
            MockResponse(200, {"access_token": "new_token"}),
            # Retry: success
            MockResponse(200, {"data": {"gid": "456"}}),
        ])
        state = MockStateClient({
            "access_token": "old_token",
            "refresh_token": "ref_tok",
        })
        client = AsanaClient(http, state, client_id="cid", client_secret="cs")

        result = await client._request("GET", f"{ASANA_BASE_URL}/test")

        assert result == {"gid": "456"}
        # Verify refresh call was made
        refresh_call = http.calls[1]
        assert refresh_call["method"] == "POST"
        assert refresh_call["data"]["grant_type"] == "refresh_token"
        assert ("access_token", "new_token") in state.set_calls

    @pytest.mark.asyncio
    async def test_401_no_refresh_token_raises(self):
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),
        ])
        state = MockStateClient({"access_token": "expired"})
        client = AsanaClient(http, state)

        with pytest.raises(AsanaAuthError, match="no refresh token"):
            await client._request("GET", f"{ASANA_BASE_URL}/test")

    @pytest.mark.asyncio
    async def test_401_no_infinite_refresh_loop(self):
        """If retry after refresh also returns 401, stop."""
        http = MockHttpClient([
            MockResponse(401, "Unauthorized"),        # first attempt
            MockResponse(200, {"access_token": "n"}), # refresh OK
            MockResponse(401, "Still unauthorized"),   # retry also 401
        ])
        state = MockStateClient({
            "access_token": "old",
            "refresh_token": "ref",
        })
        client = AsanaClient(http, state, client_id="c", client_secret="s")

        with pytest.raises(AsanaAuthError, match="Unauthorized after token refresh"):
            await client._request("GET", f"{ASANA_BASE_URL}/test")

        assert len(http.calls) == 3

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        http = MockHttpClient([MockResponse(403, "Forbidden")])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        with pytest.raises(AsanaAuthError) as exc_info:
            await client._request("GET", f"{ASANA_BASE_URL}/test")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_with_retry_after(self):
        http = MockHttpClient([
            MockResponse(429, "Too many requests", {"Retry-After": "30"})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        with pytest.raises(AsanaRateLimitError) as exc_info:
            await client._request("GET", f"{ASANA_BASE_URL}/test")
        assert exc_info.value.retry_after == 30
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_defaults_retry_after_to_60(self):
        http = MockHttpClient([MockResponse(429, "Too many requests")])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        with pytest.raises(AsanaRateLimitError) as exc_info:
            await client._request("GET", f"{ASANA_BASE_URL}/test")
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self):
        http = MockHttpClient([MockResponse(500, "Server error")])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        with pytest.raises(AsanaAPIError) as exc_info:
            await client._request("GET", f"{ASANA_BASE_URL}/test")
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Tests: Pagination
# ---------------------------------------------------------------------------

class TestPaginatedGet:

    @pytest.mark.asyncio
    async def test_single_page(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [{"gid": "1"}, {"gid": "2"}],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client._paginated_get(
            f"{ASANA_BASE_URL}/test", opt_fields="name"
        )

        assert len(result) == 2
        assert result[0]["gid"] == "1"
        # Verify opt_fields in URL
        assert "opt_fields=name" in http.calls[0]["url"]
        assert "limit=100" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_multi_page_with_offset(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [{"gid": "1"}],
                "next_page": {"offset": "eyJ0eXAi", "path": "/test", "uri": "..."},
            }),
            MockResponse(200, {
                "data": [{"gid": "2"}],
                "next_page": None,
            }),
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client._paginated_get(
            f"{ASANA_BASE_URL}/test", opt_fields="name"
        )

        assert len(result) == 2
        assert result[0]["gid"] == "1"
        assert result[1]["gid"] == "2"
        # Second request should include offset
        assert "offset=eyJ0eXAi" in http.calls[1]["url"]

    @pytest.mark.asyncio
    async def test_empty_results(self):
        http = MockHttpClient([
            MockResponse(200, {"data": [], "next_page": None})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client._paginated_get(f"{ASANA_BASE_URL}/test")

        assert result == []


# ---------------------------------------------------------------------------
# Tests: get_workspaces
# ---------------------------------------------------------------------------

class TestGetWorkspaces:

    @pytest.mark.asyncio
    async def test_returns_workspace_list(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {"gid": "ws1", "name": "My Workspace"},
                    {"gid": "ws2", "name": "Other Workspace"},
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_workspaces()

        assert len(result) == 2
        assert result[0]["gid"] == "ws1"
        assert result[0]["name"] == "My Workspace"
        assert "opt_fields=name" in http.calls[0]["url"]
        assert "/workspaces?" in http.calls[0]["url"]


# ---------------------------------------------------------------------------
# Tests: get_projects
# ---------------------------------------------------------------------------

class TestGetProjects:

    @pytest.mark.asyncio
    async def test_returns_non_archived_projects(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {"gid": "p1", "name": "Active", "archived": False},
                    {"gid": "p2", "name": "Archived", "archived": True},
                    {"gid": "p3", "name": "Also Active", "archived": False},
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_projects("ws1")

        assert len(result) == 2
        assert result[0]["gid"] == "p1"
        assert result[1]["gid"] == "p3"
        assert "opt_fields=name,archived" in http.calls[0]["url"]
        assert "/workspaces/ws1/projects?" in http.calls[0]["url"]


# ---------------------------------------------------------------------------
# Tests: get_sections
# ---------------------------------------------------------------------------

class TestGetSections:

    @pytest.mark.asyncio
    async def test_returns_section_list(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {"gid": "s1", "name": "To Do"},
                    {"gid": "s2", "name": "In Progress"},
                    {"gid": "s3", "name": "Done"},
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_sections("p1")

        assert len(result) == 3
        assert result[0]["name"] == "To Do"
        assert "opt_fields=name" in http.calls[0]["url"]
        assert "/projects/p1/sections?" in http.calls[0]["url"]


# ---------------------------------------------------------------------------
# Tests: get_custom_fields
# ---------------------------------------------------------------------------

class TestGetCustomFields:

    @pytest.mark.asyncio
    async def test_extracts_custom_field_from_settings(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {
                        "gid": "setting1",
                        "custom_field": {
                            "gid": "cf1",
                            "name": "Priority",
                            "resource_subtype": "enum",
                            "enum_options": [
                                {"gid": "e1", "name": "High"},
                                {"gid": "e2", "name": "Low"},
                            ],
                        },
                    },
                    {
                        "gid": "setting2",
                        "custom_field": {
                            "gid": "cf2",
                            "name": "Story Points",
                            "resource_subtype": "number",
                        },
                    },
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_custom_fields("p1")

        assert len(result) == 2
        assert result[0]["gid"] == "cf1"
        assert result[0]["name"] == "Priority"
        assert result[0]["resource_subtype"] == "enum"
        assert len(result[0]["enum_options"]) == 2
        assert result[1]["name"] == "Story Points"
        assert "custom_field.name" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_skips_settings_without_custom_field(self):
        """Settings that lack a custom_field key are skipped."""
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {"gid": "s1"},  # No custom_field key
                    {"gid": "s2", "custom_field": {"gid": "cf1", "name": "X"}},
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_custom_fields("p1")

        assert len(result) == 1
        assert result[0]["gid"] == "cf1"


# ---------------------------------------------------------------------------
# Tests: get_tasks
# ---------------------------------------------------------------------------

class TestGetTasks:

    @pytest.mark.asyncio
    async def test_returns_tasks_with_opt_fields(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [
                    {"gid": "t1", "name": "Task 1", "completed": False},
                    {"gid": "t2", "name": "Task 2", "completed": True},
                ],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_tasks("p1", "name,completed")

        assert len(result) == 2
        assert "opt_fields=name,completed" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_modified_since_param(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": [{"gid": "t1"}],
                "next_page": None,
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_tasks(
            "p1", "name", modified_since="2025-01-01T00:00:00Z"
        )

        assert len(result) == 1
        assert "modified_since=2025-01-01T00:00:00Z" in http.calls[0]["url"]


# ---------------------------------------------------------------------------
# Tests: get_user_me
# ---------------------------------------------------------------------------

class TestGetUserMe:

    @pytest.mark.asyncio
    async def test_returns_user_data(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": {
                    "gid": "u1",
                    "name": "Test User",
                    "email": "test@example.com",
                },
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.get_user_me()

        assert result["gid"] == "u1"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert "opt_fields=name,email" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_sends_auth_header(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": {"gid": "u1", "name": "User", "email": "u@x.com"},
            })
        ])
        state = MockStateClient({"access_token": "my_bearer_tok"})
        client = AsanaClient(http, state)

        await client.get_user_me()

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer my_bearer_tok"


# ---------------------------------------------------------------------------
# Tests: patch_task
# ---------------------------------------------------------------------------

class TestPatchTask:

    @pytest.mark.asyncio
    async def test_sends_correct_json_body(self):
        http = MockHttpClient([
            MockResponse(200, {
                "data": {"gid": "t1", "name": "Updated", "completed": True},
            })
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        result = await client.patch_task("t1", {"completed": True})

        assert result["completed"] is True
        patch_call = http.calls[0]
        assert patch_call["method"] == "PATCH"
        assert patch_call["json"] == {"data": {"completed": True}}
        assert "/tasks/t1" in patch_call["url"]


# ---------------------------------------------------------------------------
# Tests: add_task_to_section
# ---------------------------------------------------------------------------

class TestAddTaskToSection:

    @pytest.mark.asyncio
    async def test_sends_correct_nested_data(self):
        http = MockHttpClient([
            MockResponse(200, {"data": {}})
        ])
        state = MockStateClient({"access_token": "tok"})
        client = AsanaClient(http, state)

        await client.add_task_to_section("sec1", "task1")

        post_call = http.calls[0]
        assert post_call["method"] == "POST"
        assert post_call["json"] == {"data": {"task": "task1"}}
        assert "/sections/sec1/addTask" in post_call["url"]


# ---------------------------------------------------------------------------
# Tests: Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:

    def test_auth_error_is_api_error(self):
        err = AsanaAuthError("auth fail", status_code=401)
        assert isinstance(err, AsanaAPIError)
        assert err.status_code == 401

    def test_rate_limit_error_is_api_error(self):
        err = AsanaRateLimitError("rate limit", retry_after=45)
        assert isinstance(err, AsanaAPIError)
        assert err.retry_after == 45
        assert err.status_code == 429

    def test_api_error_attributes(self):
        err = AsanaAPIError("fail", status_code=500, response_body="oops")
        assert err.message == "fail"
        assert err.status_code == 500
        assert err.response_body == "oops"
