"""Tests for Asana pull sync engine — all sync paths and edge cases.

Runs with ``pytest --noconftest`` — no fixtures or conftest required.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path setup — import the apps/asana-sync/services package
# ---------------------------------------------------------------------------
_apps_dir = str(Path(__file__).resolve().parent.parent.parent / "apps" / "asana-sync")
if _apps_dir not in sys.path:
    sys.path.insert(0, _apps_dir)

from services.sync_engine import (
    BATCH_SIZE,
    MAX_SUBTASK_DEPTH,
    TASK_OPT_FIELDS,
    _find_existing_task,
    _submit_commands_batched,
    _read_field_config,
    _fetch_subtasks_recursive,
    _build_create_command,
    _build_update_commands,
    _make_result,
    pull_sync,
    _find_changed_tasks,
    push_sync,
)
from services.field_mapper import BPKM


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------


class MockStateClient:
    """Dict-backed state client with get/set."""

    def __init__(self, data: dict | None = None):
        self._data = data if data is not None else {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class MockGraphClient:
    """Mock graph client with configurable query responses.

    ``responses`` is a list of results returned in order — each call
    pops from the front.  If only one response is provided, it's reused
    for all subsequent calls.
    """

    def __init__(self, responses: list[dict] | None = None):
        self._responses = list(responses) if responses else [
            {"results": {"bindings": []}}
        ]
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


class MockResponse:
    """Mock HTTP response with status_code and json()."""

    def __init__(self, status_code: int = 200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHttpClient:
    """Mock HTTP client recording POST calls and returning responses."""

    def __init__(self, responses: list[MockResponse] | None = None):
        self._responses = list(responses) if responses else [
            MockResponse(200, {"ok": True})
        ]
        self.posts: list[tuple[str, dict]] = []

    async def post(self, url: str, **kwargs) -> MockResponse:
        self.posts.append((url, kwargs))
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]

    async def get(self, url: str, **kwargs) -> MockResponse:
        return MockResponse(200, {"data": []})


class MockCommandClient:
    """Mock command client with _client attribute for D204 bypass."""

    def __init__(self, http_client: MockHttpClient | None = None):
        self._client = http_client or MockHttpClient()
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, cmd_type: str, params: dict) -> dict:
        self.calls.append((cmd_type, params))
        return {"iri": f"urn:test:created:{params.get('slug', 'unknown')}"}


class MockAsanaClient:
    """Mock AsanaClient with configurable get_tasks / get_subtasks."""

    def __init__(
        self,
        tasks_by_project: dict[str, list[dict]] | None = None,
        subtasks_by_task: dict[str, list[dict]] | None = None,
    ):
        self._tasks = tasks_by_project or {}
        self._subtasks = subtasks_by_task or {}
        self.get_tasks_calls: list[tuple] = []
        self.get_subtasks_calls: list[tuple] = []

    async def get_tasks(
        self, project_gid: str, opt_fields: str,
        modified_since: str | None = None,
    ) -> list[dict]:
        self.get_tasks_calls.append((project_gid, opt_fields, modified_since))
        return list(self._tasks.get(project_gid, []))

    async def get_subtasks(self, task_gid: str, opt_fields: str) -> list[dict]:
        self.get_subtasks_calls.append((task_gid, opt_fields))
        return list(self._subtasks.get(task_gid, []))


class MockContext:
    """Assemble mock clients into a ctx-like object."""

    def __init__(
        self,
        state_data: dict | None = None,
        graph_responses: list[dict] | None = None,
        http_responses: list[MockResponse] | None = None,
    ):
        self.state = MockStateClient(state_data or {})
        self.graph = MockGraphClient(graph_responses)
        bulk_http = MockHttpClient(http_responses)
        self.commands = MockCommandClient(bulk_http)
        self.http = MockHttpClient()  # for AsanaClient

    @property
    def bulk_http(self) -> MockHttpClient:
        return self.commands._client


# ---------------------------------------------------------------------------
# Task factory
# ---------------------------------------------------------------------------


def _make_task(
    gid: str = "1234567890",
    name: str = "Test Task",
    completed: bool = False,
    notes: str | None = None,
    modified_at: str = "2025-06-01T12:00:00Z",
    resource_subtype: str = "default_task",
    assignee: dict | None = None,
    followers: list[dict] | None = None,
    memberships: list[dict] | None = None,
    custom_fields: list[dict] | None = None,
    tags: list[dict] | None = None,
    permalink_url: str = "https://app.asana.com/0/proj/task",
    **extra,
) -> dict:
    """Build a realistic Asana task dict."""
    task: dict = {
        "gid": gid,
        "name": name,
        "completed": completed,
        "modified_at": modified_at,
        "resource_subtype": resource_subtype,
        "permalink_url": permalink_url,
    }
    if notes is not None:
        task["notes"] = notes
    if assignee is not None:
        task["assignee"] = assignee
    if followers is not None:
        task["followers"] = followers
    if memberships is not None:
        task["memberships"] = memberships
    if custom_fields is not None:
        task["custom_fields"] = custom_fields
    if tags is not None:
        task["tags"] = tags
    task.update(extra)
    return task


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestFindExistingTask:
    """SPARQL lookup for existing tasks by slug."""

    def test_not_found_returns_none(self):
        graph = MockGraphClient()
        result = _run(_find_existing_task(graph, "asana-999"))
        assert result is None
        assert len(graph.queries) == 1
        assert "STRENDS" in graph.queries[0]
        assert '"asana"' in graph.queries[0]

    def test_found_returns_dict(self):
        iri = "urn:sempkm:object:Task/asana-123"
        graph = MockGraphClient([{
            "results": {"bindings": [{
                "task": {"value": iri},
                "status": {"value": "todo"},
                "extId": {"value": "123"},
                "lastSynced": {"value": "2025-01-01T00:00:00Z"},
            }]}
        }])
        result = _run(_find_existing_task(graph, "asana-123"))
        assert result is not None
        assert result["iri"] == iri
        assert result["status"] == "todo"
        assert result["externalId"] == "123"
        assert result["lastSyncedAt"] == "2025-01-01T00:00:00Z"

    def test_found_minimal_fields(self):
        """Only iri is required; status/extId/lastSynced may be absent."""
        graph = MockGraphClient([{
            "results": {"bindings": [{
                "task": {"value": "urn:test:task"},
            }]}
        }])
        result = _run(_find_existing_task(graph, "asana-456"))
        assert result is not None
        assert result["iri"] == "urn:test:task"
        assert result["status"] is None
        assert result["lastSyncedAt"] is None


class TestSubmitCommandsBatched:
    """Bulk command submission."""

    def test_empty_commands_returns_empty(self):
        http = MockHttpClient()
        result = _run(_submit_commands_batched(http, []))
        assert result == []
        assert len(http.posts) == 0

    def test_single_batch(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {}}]
        _run(_submit_commands_batched(http, cmds))
        assert len(http.posts) == 1
        url, kwargs = http.posts[0]
        assert url == "/api/commands/bulk"
        payload = kwargs["json"]
        assert payload["source"] == "asana-sync"
        assert len(payload["commands"]) == 1

    def test_error_raised_on_http_error(self):
        http = MockHttpClient([MockResponse(500)])
        cmds = [{"command": "test", "params": {}}]
        with pytest.raises(Exception, match="HTTP 500"):
            _run(_submit_commands_batched(http, cmds))


class TestReadFieldConfig:
    """StateClient → field config dict."""

    def test_defaults_when_empty(self):
        state = MockStateClient({})
        config = _run(_read_field_config(state))
        assert config["status_source"] == "completed_only"
        assert config["status_mapping"] == {}
        assert config["priority_mapping"] == {}
        assert config["story_points_field_gid"] == ""

    def test_reads_all_keys(self):
        state = MockStateClient({
            "status_source": "custom_field",
            "status_field_gid": "cf-123",
            "status_mapping": '{"Todo": "todo", "Done": "done"}',
            "priority_field_gid": "cf-456",
            "priority_mapping": '{"High": "high", "Low": "low"}',
            "story_points_field_gid": "cf-789",
        })
        config = _run(_read_field_config(state))
        assert config["status_source"] == "custom_field"
        assert config["status_field_gid"] == "cf-123"
        assert config["status_mapping"] == {"Todo": "todo", "Done": "done"}
        assert config["priority_field_gid"] == "cf-456"
        assert config["priority_mapping"] == {"High": "high", "Low": "low"}
        assert config["story_points_field_gid"] == "cf-789"


class TestFetchSubtasksRecursive:
    """Subtask recursion with depth enforcement."""

    def test_no_subtasks(self):
        client = MockAsanaClient()
        result = _run(_fetch_subtasks_recursive(client, "t1", "name"))
        assert result == []
        assert len(client.get_subtasks_calls) == 1

    def test_one_level(self):
        client = MockAsanaClient(subtasks_by_task={
            "t1": [
                {"gid": "s1", "name": "Sub 1"},
                {"gid": "s2", "name": "Sub 2"},
            ],
        })
        result = _run(_fetch_subtasks_recursive(client, "t1", "name"))
        assert len(result) == 2
        assert result[0]["_parent_gid"] == "t1"
        assert result[1]["_parent_gid"] == "t1"

    def test_three_levels(self):
        client = MockAsanaClient(subtasks_by_task={
            "t1": [{"gid": "s1", "name": "Level 1"}],
            "s1": [{"gid": "s2", "name": "Level 2"}],
            "s2": [{"gid": "s3", "name": "Level 3"}],
        })
        result = _run(_fetch_subtasks_recursive(client, "t1", "name"))
        assert len(result) == 3
        gids = [r["gid"] for r in result]
        assert gids == ["s1", "s2", "s3"]
        # Check parent linkage
        assert result[0]["_parent_gid"] == "t1"
        assert result[1]["_parent_gid"] == "s1"
        assert result[2]["_parent_gid"] == "s2"

    def test_max_depth_enforcement(self):
        """Tasks at depth=max_depth are NOT fetched."""
        client = MockAsanaClient(subtasks_by_task={
            "t1": [{"gid": "s1", "name": "Depth 1"}],
            "s1": [{"gid": "s2", "name": "Depth 2"}],
            "s2": [{"gid": "s3", "name": "Depth 3"}],
            "s3": [{"gid": "s4", "name": "Depth 4"}],
            "s4": [{"gid": "s5", "name": "Depth 5"}],
            "s5": [{"gid": "s6", "name": "Should NOT appear"}],
        })
        result = _run(_fetch_subtasks_recursive(
            client, "t1", "name", depth=0, max_depth=5,
        ))
        gids = [r["gid"] for r in result]
        assert "s5" in gids  # depth 5 — fetched at depth=4
        assert "s6" not in gids  # would be depth 6 — blocked

    def test_at_max_depth_returns_empty(self):
        """When depth == max_depth, return immediately."""
        client = MockAsanaClient(subtasks_by_task={
            "t1": [{"gid": "s1", "name": "Nope"}],
        })
        result = _run(_fetch_subtasks_recursive(
            client, "t1", "name", depth=5, max_depth=5,
        ))
        assert result == []
        assert len(client.get_subtasks_calls) == 0


class TestBuildCreateCommand:
    """object.create command building."""

    def test_task_type(self):
        cmd = _build_create_command("asana-123", f"{BPKM}Task", {"dcterms:title": "T"})
        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Task"
        assert cmd["params"]["slug"] == "asana-123"

    def test_milestone_type(self):
        cmd = _build_create_command("asana-456", f"{BPKM}Milestone", {})
        assert cmd["params"]["type"] == f"{BPKM}Milestone"


class TestBuildUpdateCommands:
    """object.patch / body.set / edge.create for existing tasks."""

    def test_patch_only(self):
        cmds = _build_update_commands("urn:t", {"a": "1"}, None, None)
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"
        assert cmds[0]["params"]["iri"] == "urn:t"

    def test_with_body(self):
        cmds = _build_update_commands("urn:t", {}, "Hello", None)
        assert len(cmds) == 2
        assert cmds[1]["command"] == "body.set"
        assert cmds[1]["params"]["body"] == "Hello"

    def test_with_assignee(self):
        cmds = _build_update_commands("urn:t", {}, None, "urn:person")
        assert len(cmds) == 2
        assert cmds[1]["command"] == "edge.create"
        assert cmds[1]["params"]["predicate"] == f"{BPKM}assignedTo"

    def test_with_followers(self):
        cmds = _build_update_commands(
            "urn:t", {}, None, None,
            follower_iris=["urn:f1", "urn:f2"],
        )
        assert len(cmds) == 3  # patch + 2 follower edges
        assert cmds[1]["params"]["predicate"] == f"{BPKM}followedBy"
        assert cmds[2]["params"]["predicate"] == f"{BPKM}followedBy"

    def test_all_together(self):
        cmds = _build_update_commands(
            "urn:t", {"a": "1"}, "Body", "urn:p",
            follower_iris=["urn:f1"],
        )
        assert len(cmds) == 4  # patch + body + assignee + follower


class TestMakeResult:
    """Structured result dict."""

    def test_basic(self):
        start = time.monotonic()
        result = _make_result("success", start, "2025-06-01T00:00:00Z")
        assert result["status"] == "success"
        assert result["created"] == 0
        assert result["duration_ms"] >= 0
        assert result["timestamp"] == "2025-06-01T00:00:00Z"
        assert result["error_details"] == []

    def test_with_reason(self):
        result = _make_result(
            "skipped", time.monotonic(), "ts",
            reason="not connected",
        )
        assert result["reason"] == "not connected"

    def test_with_counts(self):
        result = _make_result(
            "partial", time.monotonic(), "ts",
            created=5, updated=3, errors=1,
            error_details=[{"task_gid": "x", "error": "fail"}],
        )
        assert result["created"] == 5
        assert result["updated"] == 3
        assert result["errors"] == 1
        assert len(result["error_details"]) == 1


# ---------------------------------------------------------------------------
# Pull sync — guard tests
# ---------------------------------------------------------------------------


class TestPullSyncGuards:
    """Early-exit conditions before any real work."""

    def test_not_connected_skips(self):
        ctx = MockContext(state_data={})
        result = _run(pull_sync(ctx))
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    def test_no_selected_projects_key_skips(self):
        ctx = MockContext(state_data={"auth_method": "pat"})
        result = _run(pull_sync(ctx))
        assert result["status"] == "skipped"
        assert result["reason"] == "no projects selected"

    def test_empty_selected_projects_skips(self):
        ctx = MockContext(state_data={
            "auth_method": "pat",
            "selected_projects": "[]",
        })
        result = _run(pull_sync(ctx))
        assert result["status"] == "skipped"
        assert result["reason"] == "no projects selected"

    def test_skipped_result_stored_in_state(self):
        ctx = MockContext(state_data={})
        _run(pull_sync(ctx))
        stored = _run(ctx.state.get("last_pull_result"))
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"


# ---------------------------------------------------------------------------
# Pull sync — create flow tests
# ---------------------------------------------------------------------------


def _connected_state(extra: dict | None = None) -> dict:
    """Build state data for a connected app with one project selected."""
    data = {
        "auth_method": "pat",
        "access_token": "test-token",
        "selected_projects": '["proj-1"]',
        "status_source": "completed_only",
    }
    if extra:
        data.update(extra)
    return data


def _make_ctx_with_tasks(
    tasks: list[dict],
    graph_responses: list[dict] | None = None,
    state_extra: dict | None = None,
    subtasks_by_task: dict[str, list[dict]] | None = None,
) -> MockContext:
    """Build a MockContext that returns the given tasks for project proj-1.

    Monkey-patches AsanaClient construction in pull_sync by replacing
    ctx.http with a mock that AsanaClient wraps. Since AsanaClient uses
    _paginated_get which calls _raw_request, we need the Asana mock at
    the HTTP level. Instead, we patch the sync_engine module to use a
    fake client.

    For simplicity we monkeypatch the module globals after import.
    """
    ctx = MockContext(
        state_data=_connected_state(state_extra),
        graph_responses=graph_responses,
    )
    return ctx


class _PatchedPullSync:
    """Context manager that patches AsanaClient in sync_engine for testing.

    Instead of fighting the HTTP layer, we directly replace the
    AsanaClient class used by pull_sync with our mock.
    """

    def __init__(
        self,
        tasks_by_project: dict[str, list[dict]],
        subtasks_by_task: dict[str, list[dict]] | None = None,
    ):
        self._mock_client = MockAsanaClient(tasks_by_project, subtasks_by_task)

    def __enter__(self):
        import services.sync_engine as mod
        self._orig_asana_client = mod.AsanaClient
        # Replace AsanaClient constructor with a factory returning our mock
        mod.AsanaClient = lambda **kw: self._mock_client
        return self

    def __exit__(self, *args):
        import services.sync_engine as mod
        mod.AsanaClient = self._orig_asana_client

    @property
    def client(self):
        return self._mock_client


class TestPullSyncCreateFlow:
    """New tasks → object.create + phase 2."""

    def test_new_task_creates_object(self):
        task = _make_task(gid="aaa111")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["status"] == "success"
        assert result["created"] == 1
        assert result["updated"] == 0
        # Verify bulk POST was made
        assert len(ctx.bulk_http.posts) >= 1
        # First bulk post should contain object.create
        first_payload = ctx.bulk_http.posts[0][1]["json"]
        cmds = first_payload["commands"]
        create_cmds = [c for c in cmds if c["command"] == "object.create"]
        assert len(create_cmds) == 1
        assert create_cmds[0]["params"]["slug"] == "asana-aaa111"
        assert create_cmds[0]["params"]["type"] == f"{BPKM}Task"

    def test_milestone_task_uses_milestone_type(self):
        task = _make_task(gid="m001", resource_subtype="milestone")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        first_payload = ctx.bulk_http.posts[0][1]["json"]
        cmds = first_payload["commands"]
        create_cmds = [c for c in cmds if c["command"] == "object.create"]
        assert create_cmds[0]["params"]["type"] == f"{BPKM}Milestone"

    def test_multiple_tasks_creates_all(self):
        tasks = [
            _make_task(gid="t1", name="Task 1"),
            _make_task(gid="t2", name="Task 2"),
            _make_task(gid="t3", name="Task 3"),
        ]
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": tasks}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 3

    def test_body_set_in_phase2(self):
        """Task with notes → body.set command after IRI discovery."""
        task = _make_task(gid="b1", notes="Body text here")
        iri = "urn:sempkm:object:Task/asana-b1"
        # Response sequence: first call (in task loop) returns empty,
        # second call (phase 2 IRI discovery) returns the created task
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[
                {"results": {"bindings": []}},  # _find_existing_task during classify
                {"results": {"bindings": [{"task": {"value": iri}}]}},  # phase 2 lookup
            ],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        # Check for body.set in follow-up batch
        all_cmds = []
        for _, kwargs in ctx.bulk_http.posts:
            payload = kwargs.get("json", {})
            all_cmds.extend(payload.get("commands", []))
        body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
        assert len(body_cmds) == 1
        assert body_cmds[0]["params"]["iri"] == iri
        assert body_cmds[0]["params"]["body"] == "Body text here"

    def test_assignee_edge_in_phase2(self):
        """Task with assignee → edge.create for assignedTo."""
        task = _make_task(
            gid="a1",
            assignee={"email": "alice@example.com", "name": "Alice"},
        )
        iri = "urn:sempkm:object:Task/asana-a1"
        person_iri = "urn:test:created:alice"
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[
                {"results": {"bindings": []}},  # existing task lookup
                {"results": {"bindings": []}},  # person lookup (no match)
                {"results": {"bindings": [{"task": {"value": iri}}]}},  # phase 2
            ],
        )
        # PersonMatcher will call commands.execute to create the person
        ctx.commands = MockCommandClient(ctx.bulk_http)
        ctx.commands._response_iri = person_iri

        # Override execute to return desired IRI
        original_execute = ctx.commands.execute
        async def mock_execute(cmd_type, params):
            ctx.commands.calls.append((cmd_type, params))
            return {"iri": person_iri}
        ctx.commands.execute = mock_execute

        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        all_cmds = []
        for _, kwargs in ctx.bulk_http.posts:
            payload = kwargs.get("json", {})
            all_cmds.extend(payload.get("commands", []))
        edge_cmds = [
            c for c in all_cmds
            if c["command"] == "edge.create"
            and c["params"].get("predicate") == f"{BPKM}assignedTo"
        ]
        assert len(edge_cmds) >= 1

    def test_follower_edges_in_phase2(self):
        """Task with followers → edge.create for followedBy."""
        task = _make_task(
            gid="f1",
            followers=[
                {"email": "bob@example.com", "name": "Bob"},
                {"email": "carol@example.com", "name": "Carol"},
            ],
        )
        iri = "urn:sempkm:object:Task/asana-f1"
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[
                {"results": {"bindings": []}},  # existing task lookup
                {"results": {"bindings": []}},  # person lookup bob
                {"results": {"bindings": []}},  # person lookup carol
                {"results": {"bindings": [{"task": {"value": iri}}]}},  # phase 2
            ],
        )
        ctx.commands = MockCommandClient(ctx.bulk_http)
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        all_cmds = []
        for _, kwargs in ctx.bulk_http.posts:
            payload = kwargs.get("json", {})
            all_cmds.extend(payload.get("commands", []))
        follow_cmds = [
            c for c in all_cmds
            if c["command"] == "edge.create"
            and c["params"].get("predicate") == f"{BPKM}followedBy"
        ]
        assert len(follow_cmds) >= 2


# ---------------------------------------------------------------------------
# Pull sync — update flow tests
# ---------------------------------------------------------------------------


class TestPullSyncUpdateFlow:
    """Existing tasks → object.patch + body.set + edge.create."""

    def test_existing_task_patches(self):
        task = _make_task(gid="e1", modified_at="2025-06-10T00:00:00Z")
        existing_iri = "urn:sempkm:object:Task/asana-e1"
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{
                "results": {"bindings": [{
                    "task": {"value": existing_iri},
                    "status": {"value": "todo"},
                    "lastSynced": {"value": "2025-06-01T00:00:00Z"},
                }]}
            }],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["updated"] == 1
        assert result["created"] == 0
        # Verify patch command
        all_cmds = []
        for _, kwargs in ctx.bulk_http.posts:
            payload = kwargs.get("json", {})
            all_cmds.extend(payload.get("commands", []))
        patch_cmds = [c for c in all_cmds if c["command"] == "object.patch"]
        assert len(patch_cmds) >= 1
        assert patch_cmds[0]["params"]["iri"] == existing_iri

    def test_loop_prevention_skips_unchanged(self):
        """Task not modified since lastSyncedAt → counted as unchanged."""
        task = _make_task(gid="lp1", modified_at="2025-06-01T00:00:00Z")
        existing_iri = "urn:sempkm:object:Task/asana-lp1"
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{
                "results": {"bindings": [{
                    "task": {"value": existing_iri},
                    "status": {"value": "todo"},
                    "lastSynced": {"value": "2025-06-05T00:00:00Z"},
                }]}
            }],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["unchanged"] == 1
        assert result["updated"] == 0
        # No bulk commands should be submitted (no create/update)
        assert len(ctx.bulk_http.posts) == 0

    def test_modified_since_last_sync_updates(self):
        """Task modified after lastSyncedAt → updated."""
        task = _make_task(gid="ms1", modified_at="2025-06-10T00:00:00Z")
        existing_iri = "urn:sempkm:object:Task/asana-ms1"
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{
                "results": {"bindings": [{
                    "task": {"value": existing_iri},
                    "status": {"value": "todo"},
                    "lastSynced": {"value": "2025-06-05T00:00:00Z"},
                }]}
            }],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["updated"] == 1


# ---------------------------------------------------------------------------
# Pull sync — subtask recursion tests
# ---------------------------------------------------------------------------


class TestPullSyncSubtasks:
    """Subtask recursion and parent linkage."""

    def test_one_level_subtasks(self):
        """Parent with 2 subtasks → 3 total tasks processed."""
        parent = _make_task(gid="p1", name="Parent")
        sub1 = _make_task(gid="s1", name="Sub 1")
        sub2 = _make_task(gid="s2", name="Sub 2")

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync(
            {"proj-1": [parent]},
            subtasks_by_task={"p1": [sub1, sub2]},
        ):
            result = _run(pull_sync(ctx))

        assert result["created"] == 3

    def test_three_levels_deep(self):
        """Grandparent → parent → child → 3 tasks with parent linkage."""
        gp = _make_task(gid="gp", name="Grandparent")
        parent = _make_task(gid="pa", name="Parent")
        child = _make_task(gid="ch", name="Child")

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync(
            {"proj-1": [gp]},
            subtasks_by_task={"gp": [parent], "pa": [child]},
        ):
            result = _run(pull_sync(ctx))

        assert result["created"] == 3

    def test_max_depth_enforced(self):
        """Tasks at depth 5 processed, depth 6 not fetched."""
        root = _make_task(gid="r0", name="Root")
        # Build chain: r0 → d1 → d2 → d3 → d4 → d5 → d6
        subtasks = {}
        for i in range(6):
            parent_gid = f"d{i}" if i > 0 else "r0"
            child_gid = f"d{i+1}"
            subtasks[parent_gid] = [_make_task(gid=child_gid, name=f"Depth {i+1}")]

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [root]}, subtasks_by_task=subtasks) as p:
            result = _run(pull_sync(ctx))

        # root + d1...d5 = 6 tasks (d6 blocked by MAX_SUBTASK_DEPTH=5)
        assert result["created"] == 6
        # Verify d6 was never fetched
        fetched_gids = [call[0] for call in p.client.get_subtasks_calls]
        assert "d5" not in fetched_gids  # d5 is at depth=5, so its subtasks aren't fetched

    def test_subtask_parent_edge(self):
        """Subtask→parent creates dcterms:isPartOf edge."""
        parent = _make_task(gid="ep", name="Parent")
        child = _make_task(gid="ec", name="Child")
        parent_iri = "urn:sempkm:object:Task/asana-ep"
        child_iri = "urn:sempkm:object:Task/asana-ec"

        # Both tasks are new; phase 2 discovers their IRIs
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[
                {"results": {"bindings": []}},  # parent classify
                {"results": {"bindings": []}},  # child classify
                # phase 2: child slug lookup → return child IRI
                {"results": {"bindings": [{"task": {"value": child_iri}}]}},
                # phase 2: parent slug lookup → return parent IRI
                {"results": {"bindings": [{"task": {"value": parent_iri}}]}},
            ],
        )
        with _PatchedPullSync(
            {"proj-1": [parent]},
            subtasks_by_task={"ep": [child]},
        ):
            result = _run(pull_sync(ctx))

        assert result["created"] == 2
        all_cmds = []
        for _, kwargs in ctx.bulk_http.posts:
            payload = kwargs.get("json", {})
            all_cmds.extend(payload.get("commands", []))
        part_of_cmds = [
            c for c in all_cmds
            if c["command"] == "edge.create"
            and c["params"].get("predicate") == "dcterms:isPartOf"
        ]
        assert len(part_of_cmds) >= 1


# ---------------------------------------------------------------------------
# Pull sync — error isolation tests
# ---------------------------------------------------------------------------


class TestPullSyncErrorIsolation:
    """Per-task error isolation — one failing task doesn't stop others."""

    def test_one_task_fails_others_continue(self):
        """Exception on task 1 → task 2 still processed."""
        good_task = _make_task(gid="good1", name="Good Task")
        bad_task = _make_task(gid="bad1", name="Bad Task")
        # Remove 'gid' from bad_task to trigger KeyError in compute_task_slug
        del bad_task["gid"]

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [bad_task, good_task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        assert result["errors"] == 1
        assert len(result["error_details"]) == 1
        assert result["status"] == "partial"

    def test_api_error_on_project(self):
        """Fetch failure on one project → error logged, other projects work."""
        task = _make_task(gid="p2t1", name="Project 2 Task")
        ctx = MockContext(
            state_data=_connected_state({
                "selected_projects": '["proj-err", "proj-ok"]',
            }),
            graph_responses=[{"results": {"bindings": []}}],
        )

        class FailFirstClient(MockAsanaClient):
            async def get_tasks(self, project_gid, opt_fields, modified_since=None):
                if project_gid == "proj-err":
                    raise Exception("API rate limit")
                return [task]

        with _PatchedPullSync({}) as p:
            import services.sync_engine as mod
            mod.AsanaClient = lambda **kw: FailFirstClient()
            result = _run(pull_sync(ctx))

        assert result["errors"] >= 1
        assert result["created"] == 1  # proj-ok's task

    def test_error_details_contain_gid(self):
        """Error details include task_gid and project_gid."""
        bad_task = _make_task(gid="fail1", name="Fail")
        del bad_task["gid"]

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [bad_task]}):
            result = _run(pull_sync(ctx))

        assert result["errors"] == 1
        detail = result["error_details"][0]
        assert "project_gid" in detail
        assert "error" in detail


# ---------------------------------------------------------------------------
# Pull sync — incremental sync tests
# ---------------------------------------------------------------------------


class TestPullSyncIncremental:
    """Incremental sync: modified_since from last_sync_at."""

    def test_modified_since_passed(self):
        task = _make_task(gid="inc1")
        last_sync = "2025-05-01T00:00:00Z"
        ctx = MockContext(
            state_data=_connected_state({"last_sync_at": last_sync}),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}) as p:
            _run(pull_sync(ctx))

        # Verify modified_since was passed to get_tasks
        calls = p.client.get_tasks_calls
        assert len(calls) == 1
        assert calls[0][2] == last_sync  # modified_since arg

    def test_no_last_sync_sends_none(self):
        task = _make_task(gid="inc2")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}) as p:
            _run(pull_sync(ctx))

        calls = p.client.get_tasks_calls
        assert calls[0][2] is None  # no modified_since


# ---------------------------------------------------------------------------
# Pull sync — status mode tests
# ---------------------------------------------------------------------------


class TestPullSyncFieldConfig:
    """Field config integration — custom_field and section modes."""

    def test_custom_field_status_mode(self):
        task = _make_task(
            gid="cf1",
            custom_fields=[{
                "gid": "cf-status",
                "name": "Status",
                "enum_value": {"name": "In Progress"},
            }],
        )
        ctx = MockContext(
            state_data=_connected_state({
                "status_source": "custom_field",
                "status_field_gid": "cf-status",
                "status_mapping": '{"In Progress": "in_progress", "Done": "done"}',
            }),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        # Check properties in create command
        payload = ctx.bulk_http.posts[0][1]["json"]
        create_cmd = [c for c in payload["commands"] if c["command"] == "object.create"][0]
        props = create_cmd["params"]["properties"]
        assert props[f"{BPKM}taskStatus"] == "in_progress"

    def test_section_status_mode(self):
        task = _make_task(
            gid="sec1",
            memberships=[{"section": {"name": "In Review", "gid": "s1"}}],
        )
        ctx = MockContext(
            state_data=_connected_state({
                "status_source": "section",
                "status_mapping": '{"In Review": "in_review", "Done": "done"}',
            }),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        payload = ctx.bulk_http.posts[0][1]["json"]
        create_cmd = [c for c in payload["commands"] if c["command"] == "object.create"][0]
        props = create_cmd["params"]["properties"]
        assert props[f"{BPKM}taskStatus"] == "in_review"


# ---------------------------------------------------------------------------
# Pull sync — result storage tests
# ---------------------------------------------------------------------------


class TestPullSyncResultStorage:
    """State persistence: last_pull_result and last_sync_at."""

    def test_last_pull_result_stored(self):
        task = _make_task(gid="res1")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        stored_json = _run(ctx.state.get("last_pull_result"))
        assert stored_json is not None
        stored = json.loads(stored_json)
        assert "created" in stored
        assert "errors" in stored
        assert "duration_ms" in stored
        assert "timestamp" in stored
        assert stored["created"] == 1

    def test_last_sync_at_updated(self):
        task = _make_task(gid="sync1")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            _run(pull_sync(ctx))

        last_sync = _run(ctx.state.get("last_sync_at"))
        assert last_sync is not None
        # Should be an ISO timestamp
        assert "T" in last_sync

    def test_success_status_when_no_errors(self):
        task = _make_task(gid="suc1")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))
        assert result["status"] == "success"

    def test_partial_status_when_some_errors(self):
        good = _make_task(gid="pg1")
        bad = _make_task(gid="pb1")
        del bad["gid"]

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [bad, good]}):
            result = _run(pull_sync(ctx))
        assert result["status"] == "partial"

    def test_error_status_when_all_fail(self):
        bad = _make_task(gid="ab1")
        del bad["gid"]

        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [bad]}):
            result = _run(pull_sync(ctx))
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Constants verification
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify module-level constants."""

    def test_batch_size(self):
        assert BATCH_SIZE == 1000

    def test_max_subtask_depth(self):
        assert MAX_SUBTASK_DEPTH == 5

    def test_opt_fields_complete(self):
        """TASK_OPT_FIELDS includes all critical fields."""
        assert "custom_fields.gid" in TASK_OPT_FIELDS
        assert "custom_fields.enum_value.name" in TASK_OPT_FIELDS
        assert "memberships.section.name" in TASK_OPT_FIELDS
        assert "assignee.email" in TASK_OPT_FIELDS
        assert "followers.email" in TASK_OPT_FIELDS
        assert "resource_subtype" in TASK_OPT_FIELDS
        assert "modified_at" in TASK_OPT_FIELDS
        assert "custom_fields.number_value" in TASK_OPT_FIELDS
        assert "tags.name" in TASK_OPT_FIELDS
        assert "html_notes" in TASK_OPT_FIELDS
        assert "permalink_url" in TASK_OPT_FIELDS


# ---------------------------------------------------------------------------
# Completed task handling
# ---------------------------------------------------------------------------


class TestPullSyncCompletedTasks:
    """Completed tasks → status = done."""

    def test_completed_task_maps_to_done(self):
        task = _make_task(gid="ct1", completed=True)
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            result = _run(pull_sync(ctx))

        assert result["created"] == 1
        payload = ctx.bulk_http.posts[0][1]["json"]
        create_cmd = [c for c in payload["commands"] if c["command"] == "object.create"][0]
        props = create_cmd["params"]["properties"]
        assert props[f"{BPKM}taskStatus"] == "done"


# ---------------------------------------------------------------------------
# D204 bypass verification
# ---------------------------------------------------------------------------


class TestD204Bypass:
    """Commands use ctx.commands._client for bulk API bypass."""

    def test_bulk_posts_use_commands_client(self):
        task = _make_task(gid="d204")
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": [task]}):
            _run(pull_sync(ctx))

        # Bulk commands go through ctx.commands._client, not ctx.http
        assert len(ctx.bulk_http.posts) >= 1
        assert len(ctx.http.posts) == 0  # ctx.http not used for bulk


# ---------------------------------------------------------------------------
# Edge case: empty project
# ---------------------------------------------------------------------------


class TestPullSyncEmptyProject:
    """Project with no tasks → success with zero counts."""

    def test_empty_project(self):
        ctx = MockContext(
            state_data=_connected_state(),
            graph_responses=[{"results": {"bindings": []}}],
        )
        with _PatchedPullSync({"proj-1": []}):
            result = _run(pull_sync(ctx))

        assert result["status"] == "success"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["errors"] == 0


# ===========================================================================
# Push sync tests
# ===========================================================================


class MockPushAsanaClient:
    """Mock AsanaClient with patch_task and add_task_to_section for push tests."""

    def __init__(self):
        self.patch_task_calls: list[tuple[str, dict]] = []
        self.add_task_to_section_calls: list[tuple[str, str]] = []
        self.patch_task_error: Exception | None = None
        self.section_move_error: Exception | None = None

    async def patch_task(self, task_gid: str, data: dict) -> dict:
        if self.patch_task_error:
            raise self.patch_task_error
        self.patch_task_calls.append((task_gid, data))
        return {"gid": task_gid}

    async def add_task_to_section(self, section_gid: str, task_gid: str) -> None:
        if self.section_move_error:
            raise self.section_move_error
        self.add_task_to_section_calls.append((section_gid, task_gid))


class _PatchedPushSync:
    """Context manager that patches AsanaClient + _find_changed_tasks for push tests."""

    def __init__(
        self,
        changed_tasks: list[dict],
        mock_client: MockPushAsanaClient | None = None,
    ):
        self._changed_tasks = changed_tasks
        self._mock_client = mock_client or MockPushAsanaClient()

    def __enter__(self):
        import services.sync_engine as mod
        self._orig_asana_client = mod.AsanaClient
        self._orig_find_changed = mod._find_changed_tasks
        mod.AsanaClient = lambda **kw: self._mock_client
        mod._find_changed_tasks = self._fake_find_changed
        return self

    def __exit__(self, *args):
        import services.sync_engine as mod
        mod.AsanaClient = self._orig_asana_client
        mod._find_changed_tasks = self._orig_find_changed

    async def _fake_find_changed(self, graph_client):
        return list(self._changed_tasks)

    @property
    def client(self):
        return self._mock_client


def _push_state(extra: dict | None = None) -> dict:
    """Build state data for a connected app ready for push sync."""
    data = {
        "auth_method": "pat",
        "access_token": "test-token",
        "selected_projects": '["proj-1"]',
        "sync_direction": "bidirectional",
        "status_source": "custom_field",
        "status_field_gid": "cf-status-gid",
        "status_mapping": json.dumps({"In Progress": "in_progress", "Done": "done", "To Do": "todo"}),
        "priority_field_gid": "cf-priority-gid",
        "priority_mapping": json.dumps({"High": "high", "Medium": "medium", "Low": "low"}),
        "discovered_enum_fields": json.dumps([
            {
                "gid": "cf-status-gid",
                "name": "Status",
                "enum_options": [
                    {"gid": "opt-todo", "name": "To Do"},
                    {"gid": "opt-in-progress", "name": "In Progress"},
                    {"gid": "opt-done", "name": "Done"},
                ],
            },
            {
                "gid": "cf-priority-gid",
                "name": "Priority",
                "enum_options": [
                    {"gid": "opt-high", "name": "High"},
                    {"gid": "opt-medium", "name": "Medium"},
                    {"gid": "opt-low", "name": "Low"},
                ],
            },
        ]),
        "discovered_sections": json.dumps([
            {"gid": "sec-todo", "name": "To Do"},
            {"gid": "sec-doing", "name": "Doing"},
            {"gid": "sec-done", "name": "Done"},
        ]),
    }
    if extra:
        data.update(extra)
    return data


def _changed_task(
    gid: str = "12345",
    iri: str = "urn:sempkm:object:Task/asana-12345",
    status: str | None = "in_progress",
    priority: str | None = "high",
    title: str | None = "Test Task",
    due_date: str | None = None,
) -> dict:
    """Build a dict matching _find_changed_tasks output."""
    return {
        "iri": iri,
        "externalUuid": gid,
        "status": status,
        "priority": priority,
        "title": title,
        "dueDate": due_date,
        "lastSyncedAt": None,
    }


# ---------------------------------------------------------------------------
# _find_changed_tasks unit tests
# ---------------------------------------------------------------------------


class TestFindChangedTasks:
    """SPARQL query for locally-changed Asana tasks."""

    def test_filters_asana_provider(self):
        graph = MockGraphClient([{"results": {"bindings": [
            {
                "task": {"value": "urn:test:task-1"},
                "uuid": {"value": "gid-1"},
                "status": {"value": "todo"},
            }
        ]}}])
        result = _run(_find_changed_tasks(graph))
        assert len(result) == 1
        assert result[0]["iri"] == "urn:test:task-1"
        assert result[0]["externalUuid"] == "gid-1"
        # Verify query filters for "asana" provider
        assert '"asana"' in graph.queries[0]

    def test_excludes_pull_only(self):
        """SPARQL includes FILTER to exclude pull-only tasks."""
        graph = MockGraphClient([{"results": {"bindings": []}}])
        _run(_find_changed_tasks(graph))
        assert 'pull-only' in graph.queries[0]
        assert 'FILTER' in graph.queries[0]

    def test_empty_result(self):
        graph = MockGraphClient([{"results": {"bindings": []}}])
        result = _run(_find_changed_tasks(graph))
        assert result == []

    def test_extracts_all_fields(self):
        """Verify all optional fields are extracted."""
        graph = MockGraphClient([{"results": {"bindings": [
            {
                "task": {"value": "urn:t:1"},
                "uuid": {"value": "gid-abc"},
                "status": {"value": "in_progress"},
                "priority": {"value": "high"},
                "title": {"value": "My Task"},
                "dueDate": {"value": "2025-12-31"},
                "lastSynced": {"value": "2025-01-01T00:00:00Z"},
            }
        ]}}])
        tasks = _run(_find_changed_tasks(graph))
        t = tasks[0]
        assert t["status"] == "in_progress"
        assert t["priority"] == "high"
        assert t["title"] == "My Task"
        assert t["dueDate"] == "2025-12-31"
        assert t["lastSyncedAt"] == "2025-01-01T00:00:00Z"

    def test_optional_fields_default_to_none(self):
        """Missing optional fields should be None, not KeyError."""
        graph = MockGraphClient([{"results": {"bindings": [
            {
                "task": {"value": "urn:t:2"},
                "uuid": {"value": "gid-xyz"},
            }
        ]}}])
        tasks = _run(_find_changed_tasks(graph))
        t = tasks[0]
        assert t["status"] is None
        assert t["priority"] is None
        assert t["title"] is None
        assert t["dueDate"] is None
        assert t["lastSyncedAt"] is None


# ---------------------------------------------------------------------------
# push_sync integration tests
# ---------------------------------------------------------------------------


class TestPushSync:
    """Push sync pipeline — custom field PATCH, section moves, error isolation."""

    # -- Guard tests --------------------------------------------------------

    def test_push_sync_not_connected(self):
        """Skip push when not connected."""
        ctx = MockContext(state_data={})  # no auth keys
        with _PatchedPushSync([]):
            result = _run(push_sync(ctx))
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"
        assert result["pushed"] == 0

    def test_push_sync_pull_only(self):
        """Skip push when sync direction is pull-only."""
        ctx = MockContext(state_data=_push_state({"sync_direction": "pull-only"}))
        with _PatchedPushSync([]):
            result = _run(push_sync(ctx))
        assert result["status"] == "skipped"
        assert result["reason"] == "sync direction is pull-only"

    def test_push_sync_no_changed_tasks(self):
        """No changed tasks → ok with pushed=0."""
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([]):
            result = _run(push_sync(ctx))
        assert result["status"] == "ok"
        assert result["pushed"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    # -- Custom field push --------------------------------------------------

    def test_push_sync_custom_field_status(self):
        """Status change pushes via custom field PATCH."""
        task = _changed_task(status="in_progress", priority=None, title=None)
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["status"] == "ok"
        assert result["pushed"] == 1
        # Verify patch_task was called with correct custom field
        assert len(patcher.client.patch_task_calls) == 1
        gid, patch = patcher.client.patch_task_calls[0]
        assert gid == "12345"
        assert "custom_fields" in patch
        assert patch["custom_fields"]["cf-status-gid"] == "opt-in-progress"

    def test_push_sync_priority_change(self):
        """Priority change includes priority custom field in PATCH."""
        task = _changed_task(status=None, priority="high", title=None)
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        _, patch = patcher.client.patch_task_calls[0]
        assert patch["custom_fields"]["cf-priority-gid"] == "opt-high"

    def test_push_sync_title_change(self):
        """Title change includes name in PATCH."""
        task = _changed_task(status=None, priority=None, title="New Title")
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        _, patch = patcher.client.patch_task_calls[0]
        assert patch["name"] == "New Title"

    def test_push_sync_multiple_fields(self):
        """Status + priority + title all pushed in one PATCH."""
        task = _changed_task(status="done", priority="low", title="Updated")
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        _, patch = patcher.client.patch_task_calls[0]
        assert patch["name"] == "Updated"
        assert patch["custom_fields"]["cf-status-gid"] == "opt-done"
        assert patch["custom_fields"]["cf-priority-gid"] == "opt-low"

    # -- Section-based push -------------------------------------------------

    def test_push_sync_section_status(self):
        """Section-based status calls add_task_to_section."""
        task = _changed_task(status="in_progress", priority=None, title=None)
        state = _push_state({
            "status_source": "section",
            "status_mapping": json.dumps({
                "To Do": "todo",
                "Doing": "in_progress",
                "Done": "done",
            }),
        })
        ctx = MockContext(state_data=state)
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        # Section move should have happened
        assert len(patcher.client.add_task_to_section_calls) == 1
        sec_gid, task_gid = patcher.client.add_task_to_section_calls[0]
        assert sec_gid == "sec-doing"
        assert task_gid == "12345"
        # No PATCH for custom field (section mode doesn't produce cf patch for status)
        assert len(patcher.client.patch_task_calls) == 0

    def test_push_sync_section_status_plus_priority(self):
        """Section move for status AND PATCH for priority in same push."""
        task = _changed_task(status="done", priority="medium", title=None)
        state = _push_state({
            "status_source": "section",
            "status_mapping": json.dumps({
                "To Do": "todo",
                "Doing": "in_progress",
                "Done": "done",
            }),
        })
        ctx = MockContext(state_data=state)
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        # Both paths fired
        assert len(patcher.client.add_task_to_section_calls) == 1
        assert patcher.client.add_task_to_section_calls[0][0] == "sec-done"
        assert len(patcher.client.patch_task_calls) == 1
        _, patch = patcher.client.patch_task_calls[0]
        assert patch["custom_fields"]["cf-priority-gid"] == "opt-medium"

    # -- Error isolation ----------------------------------------------------

    def test_push_sync_partial_failure(self):
        """One task fails, others still push successfully."""
        task_ok = _changed_task(gid="111", iri="urn:t:ok", title="OK Task")
        task_fail = _changed_task(gid="222", iri="urn:t:fail", title="Fail Task")

        mock_client = MockPushAsanaClient()
        call_count = 0
        _orig_patch = mock_client.patch_task

        async def _flaky_patch(task_gid, data):
            nonlocal call_count
            call_count += 1
            if task_gid == "222":
                raise Exception("Asana API error")
            return await _orig_patch(task_gid, data)

        mock_client.patch_task = _flaky_patch

        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task_ok, task_fail], mock_client):
            result = _run(push_sync(ctx))

        assert result["status"] == "partial"
        assert result["pushed"] == 1
        assert result["errors"] == 1
        assert len(result["error_details"]) == 1
        assert result["error_details"][0]["task_gid"] == "222"

    # -- lastSyncedAt update ------------------------------------------------

    def test_push_sync_updates_last_synced_at(self):
        """Verify lastSyncedAt timestamp update command is submitted."""
        task = _changed_task(title="Push Me")
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]):
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        # Bulk HTTP should have received a command with lastSyncedAt patch
        assert len(ctx.bulk_http.posts) >= 1
        bulk_payload = ctx.bulk_http.posts[0][1]["json"]
        cmds = bulk_payload["commands"]
        assert any(
            c["command"] == "object.patch"
            and f"{BPKM}lastSyncedAt" in c["params"]["properties"]
            for c in cmds
        )

    # -- Result storage -----------------------------------------------------

    def test_push_sync_stores_result(self):
        """last_push_result stored in StateClient with required keys."""
        task = _changed_task()
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]):
            _run(push_sync(ctx))

        stored = _run(ctx.state.get("last_push_result"))
        assert stored is not None
        parsed = json.loads(stored)
        assert "pushed" in parsed
        assert "errors" in parsed
        assert "status" in parsed
        assert "skipped" in parsed
        assert "error_details" in parsed

    def test_push_sync_stores_result_on_skip(self):
        """last_push_result stored even when push is skipped (guard path)."""
        ctx = MockContext(state_data={})  # not connected
        with _PatchedPushSync([]):
            _run(push_sync(ctx))
        stored = _run(ctx.state.get("last_push_result"))
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"

    # -- Section GID not found ----------------------------------------------

    def test_push_sync_section_gid_not_found(self):
        """Status mapped but section GID missing → skipped, not fatal."""
        task = _changed_task(status="archived", priority=None, title=None)
        state = _push_state({
            "status_source": "section",
            "status_mapping": json.dumps({
                "Archive": "archived",
            }),
            # discovered_sections doesn't have an "Archive" section
        })
        ctx = MockContext(state_data=state)
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        # No section move happened, no PATCH either → skipped
        assert result["skipped"] == 1
        assert result["pushed"] == 0
        assert len(patcher.client.add_task_to_section_calls) == 0

    # -- No pushable changes ------------------------------------------------

    def test_push_sync_no_pushable_changes(self):
        """Task detected as changed but nothing reverse-maps → skipped."""
        # Status has no mapping entry, no priority, no title
        task = _changed_task(status="unmapped_status", priority=None, title=None)
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["skipped"] == 1
        assert result["pushed"] == 0
        assert len(patcher.client.patch_task_calls) == 0

    # -- Due date in PATCH --------------------------------------------------

    def test_push_sync_due_date_in_patch(self):
        """Due date change is included in the bpkm properties for patch.

        Note: build_asana_patch currently handles title/status/priority.
        Due date is in bpkm_props but doesn't produce a patch entry
        unless field_mapper is extended. This tests that the pipeline
        doesn't crash with dueDate present.
        """
        task = _changed_task(status="todo", due_date="2025-12-31")
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1

    # -- Completed-only status mode -----------------------------------------

    def test_push_sync_completed_only_status(self):
        """completed_only mode: status 'done' → completed: true in PATCH."""
        task = _changed_task(status="done", priority=None, title=None)
        state = _push_state({
            "status_source": "completed_only",
            "status_mapping": "{}",
        })
        ctx = MockContext(state_data=state)
        with _PatchedPushSync([task]) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 1
        _, patch = patcher.client.patch_task_calls[0]
        assert patch["completed"] is True

    # -- Multiple tasks -----------------------------------------------------

    def test_push_sync_multiple_tasks(self):
        """Multiple tasks are pushed independently."""
        tasks = [
            _changed_task(gid="aaa", iri="urn:t:aaa", title="Task A"),
            _changed_task(gid="bbb", iri="urn:t:bbb", title="Task B"),
            _changed_task(gid="ccc", iri="urn:t:ccc", title="Task C"),
        ]
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync(tasks) as patcher:
            result = _run(push_sync(ctx))

        assert result["pushed"] == 3
        assert result["errors"] == 0
        pushed_gids = [gid for gid, _ in patcher.client.patch_task_calls]
        assert set(pushed_gids) == {"aaa", "bbb", "ccc"}

    # -- Overall status logic -----------------------------------------------

    def test_push_sync_all_errors_status(self):
        """All tasks fail → status is 'error'."""
        task = _changed_task(title="Will Fail")
        mock_client = MockPushAsanaClient()
        mock_client.patch_task_error = Exception("API down")

        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task], mock_client):
            result = _run(push_sync(ctx))

        assert result["status"] == "error"
        assert result["pushed"] == 0
        assert result["errors"] == 1

    def test_push_sync_ok_status_on_success(self):
        """All tasks succeed → status is 'ok'."""
        task = _changed_task(title="Will Succeed")
        ctx = MockContext(state_data=_push_state())
        with _PatchedPushSync([task]):
            result = _run(push_sync(ctx))
        assert result["status"] == "ok"

    # -- Guard: result stored on pull-only ----------------------------------

    def test_push_sync_pull_only_stores_result(self):
        """Pull-only guard still stores last_push_result."""
        ctx = MockContext(state_data=_push_state({"sync_direction": "pull-only"}))
        with _PatchedPushSync([]):
            _run(push_sync(ctx))
        stored = _run(ctx.state.get("last_push_result"))
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"
        assert parsed["pushed"] == 0
