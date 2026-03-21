"""Unit tests for Todoist REST client.

Loads ``todoist_client.py`` from the apps directory using importlib. All
HTTP interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "todoist-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"
_AUTH_PATH = _SERVICES_DIR / "auth.py"
_CLIENT_PATH = _SERVICES_DIR / "todoist_client.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Auth must be loaded first (client imports from it)
# The _load_client function handles this.


def _load_client():
    """Load todoist_client.py with auth module pre-registered.

    The client uses try/except imports:
      try: from services.auth import ...
      except: from auth import ...
    We register the auth module under both names so either resolves.
    """
    auth_mod = _load_module("auth", _AUTH_PATH)
    sys.modules["auth"] = auth_mod
    sys.modules["services.auth"] = auth_mod
    return _load_module("todoist_client", _CLIENT_PATH)


client_mod = _load_client()
TodoistClient = client_mod.TodoistClient

# Use exception classes from the SAME module namespace the client imports from
_client_auth = sys.modules["auth"]
TodoistAuthError = _client_auth.TodoistAuthError
TodoistAPIError = _client_auth.TodoistAPIError


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockStateClient:
    """In-memory state client that mimics the SDK StateClient interface."""

    def __init__(self, initial: dict[str, str] | None = None):
        self._store: dict[str, str] = initial or {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


class MockResponse:
    """Mock HTTP response with status_code, json(), and text."""

    def __init__(self, status_code: int, data: Any = None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = json.dumps(self._data) if self._data else ""
        self.headers = {}

    def json(self) -> Any:
        return self._data


class MockHttpClient:
    """Mock HTTP client that records calls and returns preset responses."""

    def __init__(self, responses: list[MockResponse] | None = None):
        self._responses = list(responses) if responses else []
        self._call_index = 0
        self.calls: list[dict] = []

    async def request(self, method: str, url: str, **kwargs) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        return MockResponse(200, [])

    async def get(self, url: str, **kwargs) -> MockResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> MockResponse:
        return await self.request("POST", url, **kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOKEN = "test_todoist_token_abc123"
SAMPLE_TASKS = [
    {"id": "100", "content": "Buy milk", "project_id": "200", "priority": 1},
    {"id": "101", "content": "Write report", "project_id": "201", "priority": 4},
]
SAMPLE_PROJECTS = [
    {"id": "200", "name": "Personal"},
    {"id": "201", "name": "Work"},
]
SAMPLE_LABELS = [
    {"id": "300", "name": "urgent"},
    {"id": "301", "name": "home"},
]


@pytest.fixture
def state_client():
    return MockStateClient({"todoist_pat": TOKEN})


@pytest.fixture
def empty_state_client():
    return MockStateClient()


# ---------------------------------------------------------------------------
# Tests: Authentication
# ---------------------------------------------------------------------------


class TestAuth:
    """Tests for token retrieval and auth header."""

    @pytest.mark.asyncio
    async def test_auth_header_uses_bearer_token(self, state_client):
        """Client sends Bearer token in Authorization header."""
        http = MockHttpClient([MockResponse(200, SAMPLE_TASKS)])
        client = TodoistClient(http, state_client)

        await client.get_tasks()

        assert len(http.calls) == 1
        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == f"Bearer {TOKEN}"

    @pytest.mark.asyncio
    async def test_no_token_raises_auth_error(self, empty_state_client):
        """Raises TodoistAuthError when no token is stored."""
        http = MockHttpClient()
        client = TodoistClient(http, empty_state_client)

        with pytest.raises(TodoistAuthError, match="Not authenticated"):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_empty_token_raises_auth_error(self):
        """Empty string token is treated as absent."""
        state = MockStateClient({"todoist_pat": ""})
        http = MockHttpClient()
        client = TodoistClient(http, state)

        with pytest.raises(TodoistAuthError, match="Not authenticated"):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, state_client):
        """401 from Todoist raises TodoistAuthError."""
        http = MockHttpClient([MockResponse(401)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAuthError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self, state_client):
        """403 from Todoist raises TodoistAuthError."""
        http = MockHttpClient([MockResponse(403)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAuthError):
            await client.get_tasks()


# ---------------------------------------------------------------------------
# Tests: Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for API error responses."""

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self, state_client):
        """500 from Todoist raises TodoistAPIError."""
        http = MockHttpClient([MockResponse(500)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAPIError, match="500"):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_404_raises_api_error(self, state_client):
        """404 from Todoist raises TodoistAPIError."""
        http = MockHttpClient([MockResponse(404)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAPIError, match="404"):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_429_raises_api_error(self, state_client):
        """429 (rate limit) from Todoist raises TodoistAPIError."""
        http = MockHttpClient([MockResponse(429)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAPIError, match="429"):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_error_includes_status_code(self, state_client):
        """TodoistAPIError carries the HTTP status code."""
        http = MockHttpClient([MockResponse(502)])
        client = TodoistClient(http, state_client)

        with pytest.raises(TodoistAPIError) as exc_info:
            await client.get_tasks()
        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Tests: get_tasks
# ---------------------------------------------------------------------------


class TestGetTasks:
    """Tests for the get_tasks method."""

    @pytest.mark.asyncio
    async def test_get_tasks_returns_list(self, state_client):
        """get_tasks returns the task list from the API."""
        http = MockHttpClient([MockResponse(200, SAMPLE_TASKS)])
        client = TodoistClient(http, state_client)

        tasks = await client.get_tasks()
        assert tasks == SAMPLE_TASKS

    @pytest.mark.asyncio
    async def test_get_tasks_url(self, state_client):
        """get_tasks calls the correct URL."""
        http = MockHttpClient([MockResponse(200, [])])
        client = TodoistClient(http, state_client)

        await client.get_tasks()

        assert http.calls[0]["url"] == "https://api.todoist.com/rest/v2/tasks"

    @pytest.mark.asyncio
    async def test_get_tasks_no_params_when_no_project(self, state_client):
        """get_tasks sends no params when project_id is None."""
        http = MockHttpClient([MockResponse(200, [])])
        client = TodoistClient(http, state_client)

        await client.get_tasks()

        # No params key or params is None
        call = http.calls[0]
        assert call.get("params") is None

    @pytest.mark.asyncio
    async def test_get_tasks_with_project_id(self, state_client):
        """get_tasks filters by project_id when provided."""
        http = MockHttpClient([MockResponse(200, SAMPLE_TASKS[:1])])
        client = TodoistClient(http, state_client)

        tasks = await client.get_tasks(project_id="200")

        assert http.calls[0]["params"] == {"project_id": "200"}
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_get_tasks_empty_list(self, state_client):
        """get_tasks returns empty list when no tasks."""
        http = MockHttpClient([MockResponse(200, [])])
        client = TodoistClient(http, state_client)

        tasks = await client.get_tasks()
        assert tasks == []


# ---------------------------------------------------------------------------
# Tests: get_projects
# ---------------------------------------------------------------------------


class TestGetProjects:
    """Tests for the get_projects method."""

    @pytest.mark.asyncio
    async def test_get_projects_returns_list(self, state_client):
        """get_projects returns the project list."""
        http = MockHttpClient([MockResponse(200, SAMPLE_PROJECTS)])
        client = TodoistClient(http, state_client)

        projects = await client.get_projects()
        assert projects == SAMPLE_PROJECTS

    @pytest.mark.asyncio
    async def test_get_projects_url(self, state_client):
        """get_projects calls the correct URL."""
        http = MockHttpClient([MockResponse(200, [])])
        client = TodoistClient(http, state_client)

        await client.get_projects()

        assert http.calls[0]["url"] == "https://api.todoist.com/rest/v2/projects"


# ---------------------------------------------------------------------------
# Tests: get_labels
# ---------------------------------------------------------------------------


class TestGetLabels:
    """Tests for the get_labels method."""

    @pytest.mark.asyncio
    async def test_get_labels_returns_list(self, state_client):
        """get_labels returns the label list."""
        http = MockHttpClient([MockResponse(200, SAMPLE_LABELS)])
        client = TodoistClient(http, state_client)

        labels = await client.get_labels()
        assert labels == SAMPLE_LABELS

    @pytest.mark.asyncio
    async def test_get_labels_url(self, state_client):
        """get_labels calls the correct URL."""
        http = MockHttpClient([MockResponse(200, [])])
        client = TodoistClient(http, state_client)

        await client.get_labels()

        assert http.calls[0]["url"] == "https://api.todoist.com/rest/v2/labels"


# ---------------------------------------------------------------------------
# Tests: Task operations (close, reopen, create, update)
# ---------------------------------------------------------------------------


class TestTaskOperations:
    """Tests for task mutation methods."""

    @pytest.mark.asyncio
    async def test_close_task(self, state_client):
        """close_task sends POST to /tasks/{id}/close."""
        http = MockHttpClient([MockResponse(204)])
        client = TodoistClient(http, state_client)

        await client.close_task("100")

        assert http.calls[0]["method"] == "POST"
        assert "/tasks/100/close" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_reopen_task(self, state_client):
        """reopen_task sends POST to /tasks/{id}/reopen."""
        http = MockHttpClient([MockResponse(204)])
        client = TodoistClient(http, state_client)

        await client.reopen_task("100")

        assert http.calls[0]["method"] == "POST"
        assert "/tasks/100/reopen" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_create_task(self, state_client):
        """create_task sends POST to /tasks with JSON body."""
        created = {"id": "999", "content": "New task"}
        http = MockHttpClient([MockResponse(200, created)])
        client = TodoistClient(http, state_client)

        result = await client.create_task({"content": "New task", "priority": 3})

        assert http.calls[0]["method"] == "POST"
        assert "/tasks" in http.calls[0]["url"]
        assert http.calls[0]["json"] == {"content": "New task", "priority": 3}
        assert result == created

    @pytest.mark.asyncio
    async def test_update_task(self, state_client):
        """update_task sends POST to /tasks/{id} with JSON body."""
        updated = {"id": "100", "content": "Updated"}
        http = MockHttpClient([MockResponse(200, updated)])
        client = TodoistClient(http, state_client)

        result = await client.update_task("100", {"content": "Updated"})

        assert http.calls[0]["method"] == "POST"
        assert "/tasks/100" in http.calls[0]["url"]
        assert result == updated
