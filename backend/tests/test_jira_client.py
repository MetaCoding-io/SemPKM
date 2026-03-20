"""Unit tests for the Jira REST API client.

Loads ``jira_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All HTTP and state interactions
are mocked — no network calls are made.

Uses ``asyncio.run()`` to execute async tests without requiring pytest-asyncio.
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
# Load jira_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "jira-sync"
    / "services"
    / "jira_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("jira_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jira_client"] = mod
    spec.loader.exec_module(mod)
    return mod


jc = _load_module()
JiraClient = jc.JiraClient
JiraAPIError = jc.JiraAPIError
JiraAuthError = jc.JiraAuthError
JiraRateLimitError = jc.JiraRateLimitError


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

_DEFAULT_CREDS = {
    "jira_email": "user@example.com",
    "jira_token": "my-api-token",
    "jira_site_url": "https://mysite.atlassian.net",
}


def _ok(body: Any, headers: dict[str, str] | None = None) -> MockResponse:
    """200 OK response with optional headers."""
    return MockResponse(200, body, headers)


def _no_content() -> MockResponse:
    """204 No Content response."""
    return MockResponse(204)


def _make_client(
    responses: list[MockResponse],
    creds: dict[str, str] | None = None,
) -> tuple[JiraClient, MockHttpClient, MockStateClient]:
    """Create a client with mocked HTTP and state."""
    http = MockHttpClient(responses)
    state = MockStateClient(creds if creds is not None else _DEFAULT_CREDS)
    client = JiraClient(http, state)
    return client, http, state


def _expected_auth_header() -> str:
    """Compute expected Basic auth header for default creds."""
    encoded = base64.b64encode(b"user@example.com:my-api-token").decode()
    return f"Basic {encoded}"


# ===========================================================================
# Tests: Auth header construction
# ===========================================================================

class TestAuthHeader:

    def test_basic_auth_header_correct(self):
        """Auth header is Base64(email:token)."""
        client, http, _ = _make_client([_ok({"accountId": "123"})])
        _run(client.get_myself())
        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == _expected_auth_header()

    def test_auth_header_contains_email_colon_token(self):
        """Verify the decoded header matches email:token."""
        client, http, _ = _make_client([_ok({"accountId": "123"})])
        _run(client.get_myself())
        auth = http.calls[0]["headers"]["Authorization"]
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth.split(" ", 1)[1]).decode()
        assert decoded == "user@example.com:my-api-token"

    def test_missing_email_raises_auth_error(self):
        """Missing email in state raises JiraAuthError."""
        client, http, _ = _make_client([], creds={
            "jira_token": "token",
            "jira_site_url": "https://site.atlassian.net",
        })
        with pytest.raises(JiraAuthError, match="Not authenticated"):
            _run(client.get_myself())
        assert len(http.calls) == 0

    def test_missing_token_raises_auth_error(self):
        """Missing token in state raises JiraAuthError."""
        client, http, _ = _make_client([], creds={
            "jira_email": "user@example.com",
            "jira_site_url": "https://site.atlassian.net",
        })
        with pytest.raises(JiraAuthError, match="Not authenticated"):
            _run(client.get_myself())
        assert len(http.calls) == 0

    def test_empty_email_raises_auth_error(self):
        """Empty string email in state raises JiraAuthError."""
        client, http, _ = _make_client([], creds={
            "jira_email": "",
            "jira_token": "token",
            "jira_site_url": "https://site.atlassian.net",
        })
        with pytest.raises(JiraAuthError, match="Not authenticated"):
            _run(client.get_myself())

    def test_no_credentials_at_all_raises_auth_error(self):
        """No credentials in state raises JiraAuthError."""
        client, http, _ = _make_client([], creds={})
        with pytest.raises(JiraAuthError, match="Not authenticated"):
            _run(client.get_myself())
        assert len(http.calls) == 0


# ===========================================================================
# Tests: Request construction
# ===========================================================================

class TestRequestConstruction:

    def test_sends_correct_headers(self):
        client, http, _ = _make_client([_ok({"accountId": "123"})])
        _run(client.get_myself())
        headers = http.calls[0]["headers"]
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"

    def test_url_uses_site_url(self):
        """Request URL uses the site URL from state."""
        client, http, _ = _make_client([_ok({"accountId": "123"})])
        _run(client.get_myself())
        assert http.calls[0]["url"] == "https://mysite.atlassian.net/rest/api/3/myself"

    def test_absolute_url_preserved(self):
        """Absolute URLs bypass site URL prefix."""
        client, http, _ = _make_client([_ok([])])
        _run(client._request("GET", "https://custom.jira.com/endpoint"))
        assert http.calls[0]["url"] == "https://custom.jira.com/endpoint"


# ===========================================================================
# Tests: Error handling
# ===========================================================================

class TestErrorHandling:

    def test_401_raises_auth_error(self):
        client, _, _ = _make_client([MockResponse(401, "Unauthorized")])
        with pytest.raises(JiraAuthError) as exc_info:
            _run(client._request("GET", "/rest/api/3/myself"))
        assert exc_info.value.status_code == 401
        assert exc_info.value.response_body == "Unauthorized"

    def test_429_raises_rate_limit_error_with_retry_after(self):
        client, _, _ = _make_client([
            MockResponse(429, "Rate limited", {"Retry-After": "45"}),
        ])
        with pytest.raises(JiraRateLimitError) as exc_info:
            _run(client._request("GET", "/rest/api/3/search"))
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 45

    def test_429_without_retry_after_defaults_60(self):
        client, _, _ = _make_client([MockResponse(429, "Rate limited")])
        with pytest.raises(JiraRateLimitError) as exc_info:
            _run(client._request("GET", "/rest/api/3/search"))
        assert exc_info.value.retry_after == 60

    def test_404_raises_api_error(self):
        client, _, _ = _make_client([MockResponse(404, "Not Found")])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client._request("GET", "/rest/api/3/issue/NOPE-999"))
        assert exc_info.value.status_code == 404
        assert not isinstance(exc_info.value, JiraAuthError)
        assert not isinstance(exc_info.value, JiraRateLimitError)

    def test_500_raises_api_error(self):
        client, _, _ = _make_client([MockResponse(500, "Internal Server Error")])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client._request("GET", "/rest/api/3/search"))
        assert exc_info.value.status_code == 500

    def test_error_hierarchy(self):
        """JiraAuthError and JiraRateLimitError are subclasses of JiraAPIError."""
        assert issubclass(JiraAuthError, JiraAPIError)
        assert issubclass(JiraRateLimitError, JiraAPIError)

    def test_error_carries_response_body(self):
        """Error exceptions carry the response body for debugging."""
        client, _, _ = _make_client([
            MockResponse(422, {"errorMessages": ["Field X is required"]}),
        ])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client._request("PUT", "/rest/api/3/issue/PROJ-1"))
        assert "Field X is required" in exc_info.value.response_body


# ===========================================================================
# Tests: JQL search (single page)
# ===========================================================================

class TestSearchIssues:

    def test_search_issues_basic(self):
        """Single-page search returns issues with pagination metadata."""
        response_data = {
            "issues": [{"key": "PROJ-1"}, {"key": "PROJ-2"}],
            "startAt": 0,
            "maxResults": 100,
            "total": 2,
        }
        client, http, _ = _make_client([_ok(response_data)])
        result = _run(client.search_issues("project = PROJ"))
        assert len(result["issues"]) == 2
        assert result["total"] == 2
        assert http.calls[0]["method"] == "POST"
        assert "/rest/api/3/search" in http.calls[0]["url"]
        body = http.calls[0]["json"]
        assert body["jql"] == "project = PROJ"
        assert body["startAt"] == 0
        assert body["maxResults"] == 100
        assert body["fields"] == ["*all"]
        assert body["expand"] == ["names"]

    def test_search_issues_custom_pagination(self):
        """Custom startAt and maxResults are passed through."""
        response_data = {
            "issues": [{"key": "PROJ-3"}],
            "startAt": 50,
            "maxResults": 25,
            "total": 51,
        }
        client, http, _ = _make_client([_ok(response_data)])
        _run(client.search_issues("project = PROJ", start_at=50, max_results=25))
        body = http.calls[0]["json"]
        assert body["startAt"] == 50
        assert body["maxResults"] == 25

    def test_search_issues_empty(self):
        """Empty search returns zero issues."""
        response_data = {
            "issues": [],
            "startAt": 0,
            "maxResults": 100,
            "total": 0,
        }
        client, _, _ = _make_client([_ok(response_data)])
        result = _run(client.search_issues("project = EMPTY"))
        assert result["issues"] == []
        assert result["total"] == 0


# ===========================================================================
# Tests: Paginated search (multi-page)
# ===========================================================================

class TestSearchAllIssues:

    def test_single_page_returns_all(self):
        """When total <= page size, one page is enough."""
        client, http, _ = _make_client([
            _ok({
                "issues": [{"key": "P-1"}, {"key": "P-2"}],
                "startAt": 0,
                "maxResults": 100,
                "total": 2,
            }),
        ])
        result = _run(client.search_all_issues("project = P"))
        assert len(result) == 2
        assert len(http.calls) == 1

    def test_multi_page_collects_all(self):
        """Fetches 3 pages when total exceeds page size."""
        client, http, _ = _make_client([
            _ok({
                "issues": [{"key": f"P-{i}"} for i in range(100)],
                "startAt": 0,
                "maxResults": 100,
                "total": 250,
            }),
            _ok({
                "issues": [{"key": f"P-{i}"} for i in range(100, 200)],
                "startAt": 100,
                "maxResults": 100,
                "total": 250,
            }),
            _ok({
                "issues": [{"key": f"P-{i}"} for i in range(200, 250)],
                "startAt": 200,
                "maxResults": 100,
                "total": 250,
            }),
        ])
        result = _run(client.search_all_issues("project = P"))
        assert len(result) == 250
        assert len(http.calls) == 3
        assert http.calls[0]["json"]["startAt"] == 0
        assert http.calls[1]["json"]["startAt"] == 100
        assert http.calls[2]["json"]["startAt"] == 200

    def test_max_pages_safety_limit(self):
        """Stops at MAX_PAGINATION_PAGES even if more pages exist."""
        responses = []
        for i in range(55):
            responses.append(_ok({
                "issues": [{"key": f"P-{i}"}],
                "startAt": i,
                "maxResults": 1,
                "total": 9999,
            }))
        client, http, _ = _make_client(responses)
        result = _run(client.search_all_issues("project = P"))
        assert len(result) == 50
        assert len(http.calls) == 50

    def test_empty_issues_stops(self):
        """Stops when issues list is empty (even if total > startAt)."""
        client, http, _ = _make_client([
            _ok({
                "issues": [],
                "startAt": 0,
                "maxResults": 100,
                "total": 0,
            }),
        ])
        result = _run(client.search_all_issues("project = EMPTY"))
        assert result == []
        assert len(http.calls) == 1


# ===========================================================================
# Tests: get_issue
# ===========================================================================

class TestGetIssue:

    def test_get_issue_success(self):
        issue_data = {"key": "PROJ-42", "fields": {"summary": "Fix bug"}}
        client, http, _ = _make_client([_ok(issue_data)])
        result = _run(client.get_issue("PROJ-42"))
        assert result == issue_data
        assert http.calls[0]["method"] == "GET"
        assert "/rest/api/3/issue/PROJ-42" in http.calls[0]["url"]

    def test_get_issue_not_found(self):
        client, _, _ = _make_client([MockResponse(404, "Not Found")])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client.get_issue("NOPE-999"))
        assert exc_info.value.status_code == 404


# ===========================================================================
# Tests: update_issue
# ===========================================================================

class TestUpdateIssue:

    def test_update_issue_success(self):
        """update_issue sends PUT with fields and returns None."""
        client, http, _ = _make_client([_no_content()])
        result = _run(client.update_issue("PROJ-1", {"summary": "Updated"}))
        assert result is None
        assert http.calls[0]["method"] == "PUT"
        assert "/rest/api/3/issue/PROJ-1" in http.calls[0]["url"]
        assert http.calls[0]["json"] == {"fields": {"summary": "Updated"}}

    def test_update_issue_error(self):
        client, _, _ = _make_client([
            MockResponse(400, {"errorMessages": ["Invalid field"]}),
        ])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client.update_issue("PROJ-1", {"bad_field": "value"}))
        assert exc_info.value.status_code == 400


# ===========================================================================
# Tests: get_projects
# ===========================================================================

class TestGetProjects:

    def test_get_projects_success(self):
        projects = [
            {"id": "10000", "key": "PROJ", "name": "My Project"},
            {"id": "10001", "key": "OPS", "name": "Operations"},
        ]
        client, http, _ = _make_client([_ok(projects)])
        result = _run(client.get_projects())
        assert result == projects
        assert http.calls[0]["method"] == "GET"
        assert "/rest/api/3/project" in http.calls[0]["url"]

    def test_get_projects_empty(self):
        client, _, _ = _make_client([_ok([])])
        result = _run(client.get_projects())
        assert result == []


# ===========================================================================
# Tests: get_user
# ===========================================================================

class TestGetUser:

    def test_get_user_success(self):
        user_data = {
            "accountId": "abc123",
            "emailAddress": "user@example.com",
            "displayName": "Test User",
        }
        client, http, _ = _make_client([_ok(user_data)])
        result = _run(client.get_user("abc123"))
        assert result == user_data
        assert http.calls[0]["method"] == "GET"
        assert "accountId=abc123" in http.calls[0]["url"]

    def test_get_user_not_found(self):
        client, _, _ = _make_client([MockResponse(404, "User not found")])
        with pytest.raises(JiraAPIError) as exc_info:
            _run(client.get_user("nonexistent"))
        assert exc_info.value.status_code == 404


# ===========================================================================
# Tests: get_myself
# ===========================================================================

class TestGetMyself:

    def test_get_myself_success(self):
        myself_data = {
            "accountId": "me123",
            "emailAddress": "me@example.com",
            "displayName": "Me",
        }
        client, http, _ = _make_client([_ok(myself_data)])
        result = _run(client.get_myself())
        assert result == myself_data
        assert http.calls[0]["method"] == "GET"
        assert "/rest/api/3/myself" in http.calls[0]["url"]

    def test_get_myself_auth_error(self):
        client, _, _ = _make_client([MockResponse(401, "Unauthorized")])
        with pytest.raises(JiraAuthError):
            _run(client.get_myself())
