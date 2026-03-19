"""Unit tests for push sync building blocks.

Covers reverse field mapping (bpkm → Linear), build_issue_update_input(),
LinearClient mutation methods, and externalUuid storage in pull sync.

Loads app modules from apps directory via importlib (same pattern as
test_sync_engine.py).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "linear-sync"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load in dependency order
_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_linear_client = _load_module("linear_client", _SERVICES_DIR / "linear_client.py")

# Import the items we need
BPKM = _field_mapper.BPKM
REVERSE_STATUS_MAP = _field_mapper.REVERSE_STATUS_MAP
REVERSE_PRIORITY_MAP = _field_mapper.REVERSE_PRIORITY_MAP
reverse_status = _field_mapper.reverse_status
reverse_priority = _field_mapper.reverse_priority
build_issue_update_input = _field_mapper.build_issue_update_input
build_task_properties = _field_mapper.build_task_properties
LinearClient = _linear_client.LinearClient


# ===================================================================
# Mock helpers
# ===================================================================


class MockStateClient:
    """In-memory key-value store mirroring SDK StateClient."""

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data or {})

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class MockResponse:
    """Minimal httpx.Response stub."""

    def __init__(self, status_code: int = 200, data: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = headers or {}
        self.text = str(self._data)

    def json(self):
        return self._data


class MockHttpClient:
    """Stub for httpx.AsyncClient — records POST calls and returns queued responses."""

    def __init__(self, responses: list[dict] | None = None):
        self.posts: list[dict] = []
        self._responses = list(responses or [])
        self._index = 0

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.posts.append({"url": url, "json": json, **kwargs})
        resp_data = {}
        if self._index < len(self._responses):
            resp_data = self._responses[self._index]
            self._index += 1
        return MockResponse(200, resp_data)


# ===================================================================
# Tests — REVERSE_STATUS_MAP constant
# ===================================================================


class TestReverseStatusMap:
    def test_todo_maps_to_backlog(self):
        assert REVERSE_STATUS_MAP["todo"] == "backlog"

    def test_in_progress_maps_to_started(self):
        assert REVERSE_STATUS_MAP["in-progress"] == "started"

    def test_done_maps_to_completed(self):
        assert REVERSE_STATUS_MAP["done"] == "completed"

    def test_blocked_maps_to_unstarted(self):
        assert REVERSE_STATUS_MAP["blocked"] == "unstarted"

    def test_cancelled_maps_to_cancelled(self):
        assert REVERSE_STATUS_MAP["cancelled"] == "cancelled"


# ===================================================================
# Tests — reverse_status()
# ===================================================================


class TestReverseStatus:
    def test_todo(self):
        assert reverse_status("todo") == "backlog"

    def test_in_progress(self):
        assert reverse_status("in-progress") == "started"

    def test_done(self):
        assert reverse_status("done") == "completed"

    def test_blocked(self):
        assert reverse_status("blocked") == "unstarted"

    def test_cancelled(self):
        assert reverse_status("cancelled") == "cancelled"

    def test_unknown_defaults_to_backlog(self):
        assert reverse_status("some-unknown-status") == "backlog"

    def test_empty_string_defaults_to_backlog(self):
        assert reverse_status("") == "backlog"


# ===================================================================
# Tests — REVERSE_PRIORITY_MAP constant
# ===================================================================


class TestReversePriorityMap:
    def test_critical_maps_to_1(self):
        assert REVERSE_PRIORITY_MAP["critical"] == 1

    def test_high_maps_to_2(self):
        assert REVERSE_PRIORITY_MAP["high"] == 2

    def test_medium_maps_to_3(self):
        assert REVERSE_PRIORITY_MAP["medium"] == 3

    def test_low_maps_to_4(self):
        assert REVERSE_PRIORITY_MAP["low"] == 4


# ===================================================================
# Tests — reverse_priority()
# ===================================================================


class TestReversePriority:
    def test_critical(self):
        assert reverse_priority("critical") == 1

    def test_high(self):
        assert reverse_priority("high") == 2

    def test_medium(self):
        assert reverse_priority("medium") == 3

    def test_low(self):
        assert reverse_priority("low") == 4

    def test_unknown_returns_none(self):
        assert reverse_priority("urgent") is None

    def test_empty_returns_none(self):
        assert reverse_priority("") is None


# ===================================================================
# Tests — build_issue_update_input()
# ===================================================================


class TestBuildIssueUpdateInput:
    """Tests for build_issue_update_input with full IRI property keys."""

    def _workflow_states(self) -> dict[tuple[str, str], str]:
        """Standard workflow states lookup for testing."""
        return {
            ("team-1", "backlog"): "state-backlog-uuid",
            ("team-1", "started"): "state-started-uuid",
            ("team-1", "completed"): "state-completed-uuid",
            ("team-1", "unstarted"): "state-unstarted-uuid",
            ("team-1", "cancelled"): "state-cancelled-uuid",
        }

    def test_title_extracted(self):
        props = {"dcterms:title": "Fix the bug"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert result["title"] == "Fix the bug"

    def test_status_resolves_state_id(self):
        props = {f"{BPKM}taskStatus": "in-progress"}
        ws = self._workflow_states()
        result = build_issue_update_input(props, ws, team_id="team-1")
        assert result["stateId"] == "state-started-uuid"

    def test_status_done_resolves_completed(self):
        props = {f"{BPKM}taskStatus": "done"}
        ws = self._workflow_states()
        result = build_issue_update_input(props, ws, team_id="team-1")
        assert result["stateId"] == "state-completed-uuid"

    def test_priority_mapped(self):
        props = {f"{BPKM}priority": "high"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert result["priority"] == 2

    def test_due_date_passed_through(self):
        props = {f"{BPKM}dueDate": "2026-04-01"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert result["dueDate"] == "2026-04-01"

    def test_missing_workflow_state_skips_state_id(self):
        """If team's state type is not in workflow_states, stateId is omitted."""
        props = {f"{BPKM}taskStatus": "in-progress"}
        # Empty workflow states — no match possible
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert "stateId" not in result

    def test_no_team_id_skips_state_id(self):
        """Without team_id, stateId cannot be resolved."""
        props = {f"{BPKM}taskStatus": "done"}
        ws = self._workflow_states()
        result = build_issue_update_input(props, ws, team_id=None)
        assert "stateId" not in result

    def test_unknown_priority_skipped(self):
        props = {f"{BPKM}priority": "urgent"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert "priority" not in result

    def test_skips_tags(self):
        """Tags are not pushed in v1."""
        props = {f"{BPKM}tags": ["bug", "feature"]}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert "labels" not in result

    def test_skips_completed_date(self):
        props = {f"{BPKM}completedDate": "2026-03-18"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert "completedDate" not in result

    def test_skips_external_url(self):
        props = {f"{BPKM}externalUrl": "https://linear.app/team/ENG-1"}
        result = build_issue_update_input(props, {}, team_id="team-1")
        assert "externalUrl" not in result
        assert "url" not in result

    def test_empty_properties_produce_empty_dict(self):
        result = build_issue_update_input({}, {}, team_id="team-1")
        assert result == {}

    def test_full_update(self):
        """All supported fields in one call."""
        props = {
            "dcterms:title": "Updated title",
            f"{BPKM}taskStatus": "todo",
            f"{BPKM}priority": "critical",
            f"{BPKM}dueDate": "2026-05-01",
        }
        ws = self._workflow_states()
        result = build_issue_update_input(props, ws, team_id="team-1")
        assert result == {
            "title": "Updated title",
            "stateId": "state-backlog-uuid",
            "priority": 1,
            "dueDate": "2026-05-01",
        }


# ===================================================================
# Tests — LinearClient.get_workflow_states()
# ===================================================================


class TestGetWorkflowStates:
    @pytest.mark.asyncio
    async def test_queries_team_states(self):
        """Sends correct GraphQL query and parses response."""
        http = MockHttpClient(responses=[{
            "data": {
                "team": {
                    "states": {
                        "nodes": [
                            {"id": "s1", "name": "Backlog", "type": "backlog"},
                            {"id": "s2", "name": "In Progress", "type": "started"},
                        ]
                    }
                }
            }
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        result = await client.get_workflow_states("team-abc")

        assert len(result) == 2
        assert result[0] == {"id": "s1", "name": "Backlog", "type": "backlog"}
        assert result[1] == {"id": "s2", "name": "In Progress", "type": "started"}

    @pytest.mark.asyncio
    async def test_query_includes_team_id_variable(self):
        """The GraphQL variables include the teamId."""
        http = MockHttpClient(responses=[{
            "data": {"team": {"states": {"nodes": []}}}
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        await client.get_workflow_states("team-xyz")

        assert len(http.posts) == 1
        variables = http.posts[0]["json"]["variables"]
        assert variables["teamId"] == "team-xyz"

    @pytest.mark.asyncio
    async def test_empty_states_returns_empty_list(self):
        """Team with no states returns empty list."""
        http = MockHttpClient(responses=[{
            "data": {"team": {"states": {"nodes": []}}}
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        result = await client.get_workflow_states("team-empty")
        assert result == []


# ===================================================================
# Tests — LinearClient.update_issue()
# ===================================================================


class TestUpdateIssue:
    @pytest.mark.asyncio
    async def test_sends_mutation(self):
        """Sends issueUpdate mutation with correct variables."""
        http = MockHttpClient(responses=[{
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {"id": "issue-uuid", "updatedAt": "2026-03-18T14:00:00Z"},
                }
            }
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        result = await client.update_issue("issue-uuid", {"title": "New title"})

        assert result["success"] is True
        assert result["issue"]["id"] == "issue-uuid"

    @pytest.mark.asyncio
    async def test_mutation_variables_structure(self):
        """Variables contain id and input dict."""
        http = MockHttpClient(responses=[{
            "data": {"issueUpdate": {"success": True, "issue": {"id": "x", "updatedAt": "t"}}}
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        await client.update_issue("issue-123", {"stateId": "state-456", "priority": 2})

        variables = http.posts[0]["json"]["variables"]
        assert variables["id"] == "issue-123"
        assert variables["input"] == {"stateId": "state-456", "priority": 2}

    @pytest.mark.asyncio
    async def test_mutation_query_string(self):
        """The GraphQL string contains issueUpdate and IssueUpdateInput."""
        http = MockHttpClient(responses=[{
            "data": {"issueUpdate": {"success": True, "issue": {"id": "x", "updatedAt": "t"}}}
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        await client.update_issue("issue-1", {"title": "T"})

        query = http.posts[0]["json"]["query"]
        assert "issueUpdate" in query
        assert "IssueUpdateInput" in query
        assert "$id" in query
        assert "$input" in query


# ===================================================================
# Tests — build_task_properties includes externalUuid
# ===================================================================


class TestExternalUuid:
    def test_external_uuid_stored(self):
        """build_task_properties includes bpkm:externalUuid from issue['id']."""
        issue = {
            "id": "linear-uuid-abc123",
            "identifier": "ENG-1",
            "title": "Test issue",
            "description": "",
            "url": "https://linear.app/ENG-1",
            "state": {"type": "started"},
            "priority": 2,
            "dueDate": None,
            "completedAt": None,
            "labels": None,
            "estimate": None,
            "trashed": False,
            "assignee": None,
            "updatedAt": "2026-03-18T12:00:00Z",
            "createdAt": "2026-03-17T10:00:00Z",
        }
        props = build_task_properties(issue, "ws-123", sync_time="2026-03-18T12:00:00Z")
        assert props[f"{BPKM}externalUuid"] == "linear-uuid-abc123"

    def test_external_uuid_omitted_when_empty(self):
        """Empty id is stripped by the empty-value filter."""
        issue = {
            "id": "",
            "identifier": "ENG-2",
            "title": "No UUID",
            "description": "",
            "url": "https://linear.app/ENG-2",
            "state": {"type": "backlog"},
            "priority": 0,
            "dueDate": None,
            "completedAt": None,
            "labels": None,
            "estimate": None,
            "trashed": False,
            "assignee": None,
            "updatedAt": "2026-03-18T12:00:00Z",
            "createdAt": "2026-03-17T10:00:00Z",
        }
        props = build_task_properties(issue, "ws-123", sync_time="2026-03-18T12:00:00Z")
        assert f"{BPKM}externalUuid" not in props

    def test_external_uuid_missing_key_omitted(self):
        """Missing 'id' key produces empty string which is stripped."""
        issue = {
            "identifier": "ENG-3",
            "title": "Missing ID key",
            "description": "",
            "url": "",
            "state": {"type": "backlog"},
            "priority": 0,
            "dueDate": None,
            "completedAt": None,
            "labels": None,
            "estimate": None,
            "trashed": False,
            "assignee": None,
            "updatedAt": "2026-03-18T12:00:00Z",
            "createdAt": "2026-03-17T10:00:00Z",
        }
        props = build_task_properties(issue, "ws-123", sync_time="2026-03-18T12:00:00Z")
        assert f"{BPKM}externalUuid" not in props
