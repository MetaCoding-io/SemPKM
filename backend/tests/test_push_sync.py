"""Unit tests for push sync building blocks.

Covers reverse field mapping (bpkm → Linear), build_issue_update_input(),
LinearClient mutation methods, externalUuid storage in pull sync,
push_sync() orchestration, and loop prevention in pull_sync().

Loads app modules from apps directory via importlib (same pattern as
test_sync_engine.py).
"""

from __future__ import annotations

import importlib.util
import json
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
_person_matcher = _load_module("person_matcher", _SERVICES_DIR / "person_matcher.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

# Import the items we need
BPKM = _field_mapper.BPKM
REVERSE_STATUS_MAP = _field_mapper.REVERSE_STATUS_MAP
REVERSE_PRIORITY_MAP = _field_mapper.REVERSE_PRIORITY_MAP
reverse_status = _field_mapper.reverse_status
reverse_priority = _field_mapper.reverse_priority
build_issue_update_input = _field_mapper.build_issue_update_input
build_task_properties = _field_mapper.build_task_properties
compute_issue_slug = _field_mapper.compute_issue_slug
LinearClient = _linear_client.LinearClient

# Push sync + helpers from sync_engine
push_sync = _sync_engine.push_sync
pull_sync = _sync_engine.pull_sync
_find_changed_tasks = _sync_engine._find_changed_tasks
_resolve_workflow_states = _sync_engine._resolve_workflow_states
_find_existing_task = _sync_engine._find_existing_task


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

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


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


# ===================================================================
# Mock helpers for push sync / loop prevention tests
# ===================================================================


class MockStateClient:
    """In-memory key-value store mirroring SDK StateClient."""

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data or {})

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class MockGraphClient:
    """Stub for GraphClient.query() — returns canned SPARQL results.

    For push sync tests, ``changed_tasks`` provides the bindings that
    ``_find_changed_tasks`` will parse.  For pull sync loop prevention tests,
    ``slug_map`` provides the bindings that ``_find_existing_task`` will parse.
    """

    def __init__(
        self,
        changed_tasks: list[dict] | None = None,
        slug_map: dict[str, dict] | None = None,
    ):
        self._changed_tasks = changed_tasks or []
        self._slug_map = slug_map or {}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)

        # _find_changed_tasks query — contains externalUuid in SELECT
        if "externalUuid" in sparql and "STRENDS" not in sparql:
            bindings = []
            for t in self._changed_tasks:
                row: dict = {
                    "task": {"type": "uri", "value": t["iri"]},
                    "uuid": {"type": "literal", "value": t["externalUuid"]},
                }
                if t.get("status"):
                    row["status"] = {"type": "literal", "value": t["status"]}
                if t.get("priority"):
                    row["priority"] = {"type": "literal", "value": t["priority"]}
                if t.get("title"):
                    row["title"] = {"type": "literal", "value": t["title"]}
                if t.get("dueDate"):
                    row["dueDate"] = {"type": "literal", "value": t["dueDate"]}
                if t.get("lastSyncedAt"):
                    row["lastSynced"] = {"type": "literal", "value": t["lastSyncedAt"]}
                bindings.append(row)
            return {"results": {"bindings": bindings}}

        # _find_existing_task query — contains STRENDS
        if "STRENDS" in sparql:
            for slug, info in self._slug_map.items():
                if slug in sparql:
                    row = {
                        "task": {"type": "uri", "value": info["iri"]},
                    }
                    if info.get("status"):
                        row["status"] = {"type": "literal", "value": info["status"]}
                    if info.get("externalId"):
                        row["extId"] = {"type": "literal", "value": info["externalId"]}
                    if info.get("lastSyncedAt"):
                        row["lastSynced"] = {"type": "literal", "value": info["lastSyncedAt"]}
                    return {"results": {"bindings": [row]}}
            return {"results": {"bindings": []}}

        # Person matcher or other queries
        return {"results": {"bindings": []}}


class MockHttpClientPush:
    """Stub for httpx.AsyncClient — records POST calls for push sync tests.

    Supports separate response queues for GraphQL and bulk command calls.
    """

    def __init__(
        self,
        graphql_responses: list[dict] | None = None,
    ):
        self.posts: list[dict] = []
        self._graphql_responses = list(graphql_responses or [])
        self._gql_index = 0

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.posts.append({"url": url, "json": json, **kwargs})
        # GraphQL requests go to linear.app
        if url.startswith("https://"):
            resp_data = {}
            if self._gql_index < len(self._graphql_responses):
                resp_data = self._graphql_responses[self._gql_index]
                self._gql_index += 1
            return MockResponse(200, resp_data)
        # Bulk command response
        return MockResponse(200, {"ok": True})


class MockCommandClientPush:
    """Stub for CommandClient used in push sync tests."""

    def __init__(self, http_client: MockHttpClientPush | None = None):
        self._client = http_client or MockHttpClientPush()
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        return {"iri": f"https://example.org/data/Task/t1"}


class MockAppContextPush:
    """AppContext for push sync tests."""

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClientPush | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClientPush()
        self.http = _http
        self.commands = MockCommandClientPush(_http)
        self.app_id = "linear-sync"


def _make_push_state(
    teams: list[str] | None = None,
    sync_direction: str | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account configured for push."""
    data: dict[str, str] = {
        "auth_method": "api_key",
        "api_key": "lin_test_key",
        "workspace_name": "TestCo",
        "workspace_id": "ws-123",
        "sync_teams": json.dumps(teams or ["team-1"]),
    }
    if sync_direction:
        data["sync_direction"] = sync_direction
    return data


def _workflow_states_response(team_id: str = "team-1") -> dict:
    """Standard GraphQL response for get_workflow_states."""
    return {
        "data": {
            "team": {
                "states": {
                    "nodes": [
                        {"id": "state-backlog-uuid", "name": "Backlog", "type": "backlog"},
                        {"id": "state-started-uuid", "name": "In Progress", "type": "started"},
                        {"id": "state-completed-uuid", "name": "Done", "type": "completed"},
                        {"id": "state-cancelled-uuid", "name": "Cancelled", "type": "cancelled"},
                    ]
                }
            }
        }
    }


def _issue_update_success(issue_id: str = "issue-uuid") -> dict:
    """Standard GraphQL response for issueUpdate mutation."""
    return {
        "data": {
            "issueUpdate": {
                "success": True,
                "issue": {"id": issue_id, "updatedAt": "2026-03-18T15:00:00Z"},
            }
        }
    }


# ===================================================================
# Tests — push_sync() orchestration
# ===================================================================


class TestPushSyncSkips:
    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        """Returns skipped status when no auth is configured."""
        ctx = MockAppContextPush(state_data={"auth_method": ""})
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    @pytest.mark.asyncio
    async def test_skips_when_pull_only(self):
        """Returns skipped when sync_direction is pull-only."""
        ctx = MockAppContextPush(
            state_data=_make_push_state(sync_direction="pull-only")
        )
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "sync direction is pull-only"

    @pytest.mark.asyncio
    async def test_skips_when_no_teams(self):
        """Returns skipped when no sync_teams configured."""
        state = {
            "auth_method": "api_key",
            "api_key": "key",
            "workspace_name": "Co",
            "workspace_id": "ws-1",
        }
        ctx = MockAppContextPush(state_data=state)
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "no teams selected"

    @pytest.mark.asyncio
    async def test_skips_when_no_changed_tasks(self):
        """Returns ok with pushed=0 when SPARQL finds no changed tasks."""
        graph = MockGraphClient(changed_tasks=[])
        http = MockHttpClientPush(graphql_responses=[_workflow_states_response()])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )
        result = await push_sync(ctx)
        assert result["status"] == "ok"
        assert result["pushed"] == 0
        assert result["skipped"] == 0


class TestPushSyncExecution:
    @pytest.mark.asyncio
    async def test_pushes_changed_task(self):
        """Changed task triggers issueUpdate mutation."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "linear-uuid-1",
            "status": "in-progress",
            "priority": "high",
            "title": "Fix bug",
            "dueDate": None,
            "lastSyncedAt": "2026-03-18T10:00:00Z",
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
            _issue_update_success("linear-uuid-1"),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await push_sync(ctx)

        assert result["status"] == "ok"
        assert result["pushed"] == 1

    @pytest.mark.asyncio
    async def test_calls_update_issue_with_correct_uuid(self):
        """issueUpdate mutation receives the task's externalUuid."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-abc",
            "status": "done",
            "priority": None,
            "title": "Complete task",
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
            _issue_update_success("uuid-abc"),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        await push_sync(ctx)

        # Find the issueUpdate GraphQL call (second one after workflow states)
        gql_posts = [p for p in http.posts if "linear.app" in p["url"]]
        assert len(gql_posts) >= 2
        mutation_vars = gql_posts[1]["json"]["variables"]
        assert mutation_vars["id"] == "uuid-abc"

    @pytest.mark.asyncio
    async def test_updates_last_synced_at_on_pushed_task(self):
        """After push, submits object.patch with updated lastSyncedAt."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-1",
            "status": "todo",
            "priority": None,
            "title": "Task",
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
            _issue_update_success(),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        await push_sync(ctx)

        bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
        assert len(bulk_posts) >= 1
        patch_cmd = bulk_posts[0]["json"]["commands"][0]
        assert patch_cmd["command"] == "object.patch"
        assert f"{BPKM}lastSyncedAt" in patch_cmd["params"]["properties"]

    @pytest.mark.asyncio
    async def test_stores_last_push_result_in_state(self):
        """push_sync stores last_push_result JSON in state."""
        graph = MockGraphClient(changed_tasks=[])
        http = MockHttpClientPush(graphql_responses=[_workflow_states_response()])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        await push_sync(ctx)

        raw = await ctx.state.get("last_push_result")
        assert raw is not None
        parsed = json.loads(raw)
        assert "pushed" in parsed
        assert "skipped" in parsed
        assert "errors" in parsed

    @pytest.mark.asyncio
    async def test_isolates_per_task_errors(self):
        """One task failure doesn't abort processing of subsequent tasks."""
        changed = [
            {
                "iri": "https://example.org/data/Task/t1",
                "externalUuid": "uuid-fail",
                "status": "in-progress",
                "priority": None,
                "title": "Will fail",
                "dueDate": None,
                "lastSyncedAt": None,
            },
            {
                "iri": "https://example.org/data/Task/t2",
                "externalUuid": "uuid-ok",
                "status": "done",
                "priority": None,
                "title": "Will succeed",
                "dueDate": None,
                "lastSyncedAt": None,
            },
        ]
        graph = MockGraphClient(changed_tasks=changed)
        # First issue update fails (GraphQL error), second succeeds
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
            {"errors": [{"message": "Something went wrong"}]},
            _issue_update_success("uuid-ok"),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await push_sync(ctx)

        assert result["status"] == "ok"
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["iri"] == "https://example.org/data/Task/t1"

    @pytest.mark.asyncio
    async def test_result_contains_counts(self):
        """Result dict has status, pushed, skipped, and errors fields."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-1",
            "status": "in-progress",
            "priority": None,
            "title": "Task",
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
            _issue_update_success(),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await push_sync(ctx)

        assert "status" in result
        assert "pushed" in result
        assert "skipped" in result
        assert "errors" in result
        assert isinstance(result["errors"], list)

    @pytest.mark.asyncio
    async def test_fetches_workflow_states_for_each_team(self):
        """Workflow states are fetched for all synced teams."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-1",
            "status": "in-progress",
            "priority": None,
            "title": "Task",
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response("team-1"),
            _workflow_states_response("team-2"),
            _issue_update_success(),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(teams=["team-1", "team-2"]),
            graph_client=graph,
            http_client=http,
        )

        await push_sync(ctx)

        # Should have two GraphQL calls for workflow states
        gql_posts = [p for p in http.posts if "linear.app" in p["url"]]
        assert len(gql_posts) >= 2
        # First two should be workflow state queries
        for i in range(2):
            assert "states" in gql_posts[i]["json"]["query"]

    @pytest.mark.asyncio
    async def test_skips_task_with_empty_update_input(self):
        """Task with no pushable properties produces empty input and is skipped."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-1",
            "status": None,
            "priority": None,
            "title": None,
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response(),
        ])
        ctx = MockAppContextPush(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert result["skipped"] == 1
        # No issueUpdate mutation call
        gql_posts = [p for p in http.posts if "linear.app" in p["url"]]
        assert len(gql_posts) == 1  # Only workflow states


# ===================================================================
# Tests — _find_changed_tasks()
# ===================================================================


class TestFindChangedTasks:
    @pytest.mark.asyncio
    async def test_returns_correct_dict_shape(self):
        """SPARQL bindings are parsed into the expected dict shape."""
        changed = [{
            "iri": "https://example.org/data/Task/t1",
            "externalUuid": "uuid-abc",
            "status": "in-progress",
            "priority": "high",
            "title": "Fix bug",
            "dueDate": "2026-04-01",
            "lastSyncedAt": "2026-03-18T10:00:00Z",
        }]
        graph = MockGraphClient(changed_tasks=changed)

        tasks = await _find_changed_tasks(graph)

        assert len(tasks) == 1
        t = tasks[0]
        assert t["iri"] == "https://example.org/data/Task/t1"
        assert t["externalUuid"] == "uuid-abc"
        assert t["status"] == "in-progress"
        assert t["priority"] == "high"
        assert t["title"] == "Fix bug"
        assert t["dueDate"] == "2026-04-01"
        assert t["lastSyncedAt"] == "2026-03-18T10:00:00Z"

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_results(self):
        """Empty SPARQL results return empty list."""
        graph = MockGraphClient(changed_tasks=[])
        tasks = await _find_changed_tasks(graph)
        assert tasks == []

    @pytest.mark.asyncio
    async def test_handles_optional_fields_as_none(self):
        """Missing optional fields are returned as None."""
        changed = [{
            "iri": "https://example.org/data/Task/t2",
            "externalUuid": "uuid-xyz",
            "status": None,
            "priority": None,
            "title": None,
            "dueDate": None,
            "lastSyncedAt": None,
        }]
        graph = MockGraphClient(changed_tasks=changed)
        tasks = await _find_changed_tasks(graph)

        assert len(tasks) == 1
        t = tasks[0]
        assert t["status"] is None
        assert t["priority"] is None
        assert t["title"] is None
        assert t["dueDate"] is None
        assert t["lastSyncedAt"] is None


# ===================================================================
# Tests — _resolve_workflow_states()
# ===================================================================


class TestResolveWorkflowStates:
    @pytest.mark.asyncio
    async def test_builds_correct_lookup_dict(self):
        """Workflow states from LinearClient are keyed by (team_id, type)."""
        http = MockHttpClientPush(graphql_responses=[
            _workflow_states_response("team-1"),
        ])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        lookup = await _resolve_workflow_states(client, ["team-1"])

        assert ("team-1", "backlog") in lookup
        assert lookup[("team-1", "backlog")] == "state-backlog-uuid"
        assert ("team-1", "started") in lookup
        assert lookup[("team-1", "started")] == "state-started-uuid"
        assert ("team-1", "completed") in lookup
        assert lookup[("team-1", "completed")] == "state-completed-uuid"

    @pytest.mark.asyncio
    async def test_first_match_wins_for_same_type(self):
        """If a team has multiple states of the same type, first wins."""
        http = MockHttpClientPush(graphql_responses=[{
            "data": {
                "team": {
                    "states": {
                        "nodes": [
                            {"id": "first-backlog", "name": "Backlog", "type": "backlog"},
                            {"id": "second-backlog", "name": "Triage", "type": "backlog"},
                        ]
                    }
                }
            }
        }])
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        lookup = await _resolve_workflow_states(client, ["team-1"])

        assert lookup[("team-1", "backlog")] == "first-backlog"

    @pytest.mark.asyncio
    async def test_empty_team_list(self):
        """No teams produces empty lookup."""
        http = MockHttpClientPush()
        state = MockStateClient({"api_key": "test-key"})
        client = LinearClient(http, state)

        lookup = await _resolve_workflow_states(client, [])
        assert lookup == {}


# ===================================================================
# Tests — Loop prevention in pull_sync()
# ===================================================================


def _make_pull_state(
    teams: list[str] | None = None,
    last_sync_at: str | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account for pull sync tests."""
    data: dict[str, str] = {
        "auth_method": "api_key",
        "api_key": "lin_test_key",
        "workspace_name": "TestCo",
        "workspace_id": "ws-123",
        "sync_teams": json.dumps(teams or ["team-1"]),
    }
    if last_sync_at:
        data["last_sync_at"] = last_sync_at
    return data


def _make_issue(
    id: str = "issue-1",
    title: str = "Fix bug",
    state_type: str = "started",
    **overrides,
) -> dict:
    """Build a realistic Linear issue dict."""
    base = {
        "id": id,
        "identifier": "ENG-1",
        "title": title,
        "description": "Bug description",
        "url": "https://linear.app/team/ENG-1",
        "state": {"type": state_type},
        "priority": 2,
        "dueDate": "2026-04-01",
        "completedAt": None,
        "labels": {"nodes": [{"name": "bug"}]},
        "estimate": 3,
        "trashed": False,
        "assignee": {
            "id": "user-1",
            "displayName": "Alice",
            "email": "alice@example.com",
        },
        "updatedAt": "2026-03-18T12:00:00.000Z",
        "createdAt": "2026-03-17T10:00:00.000Z",
    }
    base.update(overrides)
    return base


def _graphql_issues_response(issues: list[dict]) -> dict:
    """Wrap issues in a GraphQL paginated response shape."""
    return {
        "data": {
            "issues": {
                "nodes": issues,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }


class TestLoopPrevention:
    @pytest.mark.asyncio
    async def test_skips_issue_when_updated_at_lte_last_synced(self):
        """Issue with updatedAt <= lastSyncedAt is skipped (change came from us)."""
        issue = _make_issue(
            id="issue-loop",
            updatedAt="2026-03-18T14:00:00.000Z",
        )
        slug = compute_issue_slug("ws-123", "issue-loop")
        task_iri = f"https://example.org/data/Task/{slug}"

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": task_iri,
                "status": "in-progress",
                "externalId": "ENG-1",
                "lastSyncedAt": "2026-03-18T15:00:00.000Z",  # after updatedAt
            }
        })
        http = MockHttpClientPush(graphql_responses=[
            _graphql_issues_response([issue]),
        ])
        ctx = MockAppContextPush(
            state_data=_make_pull_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await pull_sync(ctx)

        assert result["unchanged"] == 1
        assert result["updated"] == 0
        # No bulk commands should be submitted
        bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
        assert len(bulk_posts) == 0

    @pytest.mark.asyncio
    async def test_processes_issue_when_updated_at_gt_last_synced(self):
        """Issue with updatedAt > lastSyncedAt is processed (change from Linear)."""
        issue = _make_issue(
            id="issue-newer",
            updatedAt="2026-03-18T16:00:00.000Z",
        )
        slug = compute_issue_slug("ws-123", "issue-newer")
        task_iri = f"https://example.org/data/Task/{slug}"

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": task_iri,
                "status": "in-progress",
                "externalId": "ENG-1",
                "lastSyncedAt": "2026-03-18T14:00:00.000Z",  # before updatedAt
            }
        })
        http = MockHttpClientPush(graphql_responses=[
            _graphql_issues_response([issue]),
        ])
        ctx = MockAppContextPush(
            state_data=_make_pull_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["unchanged"] == 0

    @pytest.mark.asyncio
    async def test_processes_issue_when_no_last_synced_at(self):
        """Issue with no lastSyncedAt on existing task is always processed."""
        issue = _make_issue(
            id="issue-nosync",
            updatedAt="2026-03-18T12:00:00.000Z",
        )
        slug = compute_issue_slug("ws-123", "issue-nosync")
        task_iri = f"https://example.org/data/Task/{slug}"

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": task_iri,
                "status": "in-progress",
                "externalId": "ENG-1",
                # No lastSyncedAt — should proceed
            }
        })
        http = MockHttpClientPush(graphql_responses=[
            _graphql_issues_response([issue]),
        ])
        ctx = MockAppContextPush(
            state_data=_make_pull_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["unchanged"] == 0

    @pytest.mark.asyncio
    async def test_skips_issue_when_updated_at_equals_last_synced(self):
        """Exact match on timestamps is also skipped (no external change)."""
        ts = "2026-03-18T14:00:00.000Z"
        issue = _make_issue(id="issue-equal", updatedAt=ts)
        slug = compute_issue_slug("ws-123", "issue-equal")
        task_iri = f"https://example.org/data/Task/{slug}"

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": task_iri,
                "status": "in-progress",
                "externalId": "ENG-1",
                "lastSyncedAt": ts,  # equal to updatedAt
            }
        })
        http = MockHttpClientPush(graphql_responses=[
            _graphql_issues_response([issue]),
        ])
        ctx = MockAppContextPush(
            state_data=_make_pull_state(),
            graph_client=graph,
            http_client=http,
        )

        result = await pull_sync(ctx)

        assert result["unchanged"] == 1
        assert result["updated"] == 0


# ===================================================================
# Tests — _find_existing_task() now returns lastSyncedAt
# ===================================================================


class TestFindExistingTaskLastSynced:
    @pytest.mark.asyncio
    async def test_returns_last_synced_at(self):
        """_find_existing_task includes lastSyncedAt in the result."""
        slug = "test-slug"
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://example.org/data/Task/test-slug",
                "status": "todo",
                "externalId": "ENG-99",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }
        })

        result = await _find_existing_task(graph, slug)

        assert result is not None
        assert result["lastSyncedAt"] == "2026-03-18T10:00:00Z"

    @pytest.mark.asyncio
    async def test_returns_none_last_synced_when_absent(self):
        """lastSyncedAt is None when not present in SPARQL result."""
        slug = "test-slug-no-sync"
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://example.org/data/Task/test-slug-no-sync",
                "status": "todo",
                "externalId": "ENG-100",
                # No lastSyncedAt
            }
        })

        result = await _find_existing_task(graph, slug)

        assert result is not None
        assert result["lastSyncedAt"] is None


# ===================================================================
# Tests — pull_sync() stores last_pull_result
# ===================================================================


class TestPullSyncStoresResult:
    @pytest.mark.asyncio
    async def test_stores_last_pull_result_in_state(self):
        """pull_sync stores last_pull_result JSON in state."""
        issue = _make_issue()
        http = MockHttpClientPush(graphql_responses=[
            _graphql_issues_response([issue]),
        ])
        ctx = MockAppContextPush(
            state_data=_make_pull_state(),
            http_client=http,
        )

        await pull_sync(ctx)

        raw = await ctx.state.get("last_pull_result")
        assert raw is not None
        parsed = json.loads(raw)
        assert "created" in parsed
        assert "updated" in parsed
        assert "unchanged" in parsed
        assert "errors" in parsed
