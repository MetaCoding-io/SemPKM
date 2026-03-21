"""Unit tests for the Todoist pull sync engine.

Loads ``sync_engine.py`` (and its dependencies) from the apps directory
via importlib so the app does not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "todoist-sync"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load in dependency order so that sync_engine's try/except imports resolve.
_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_person_matcher = _load_module("person_matcher", _SERVICES_DIR / "person_matcher.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_todoist_client = _load_module("todoist_client", _SERVICES_DIR / "todoist_client.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
_find_existing_task = _sync_engine._find_existing_task
_find_task_by_slug = _sync_engine._find_task_by_slug
_submit_commands_batched = _sync_engine._submit_commands_batched
_build_create_command = _sync_engine._build_create_command
_build_update_commands = _sync_engine._build_update_commands
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
compute_task_slug = _field_mapper.compute_task_slug


# ===================================================================
# Mock clients
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
    """Stub for GraphClient.query() — returns results based on query content.

    Supports:
    - externalId match: if the query contains an externalId that exists
      in ``id_map``, returns a binding with that task IRI.
    - Slug match: if the query uses STRENDS and a slug from ``slug_map``.
    """

    def __init__(
        self,
        id_map: dict[str, str | dict] | None = None,
        slug_map: dict[str, str | dict] | None = None,
    ):
        self.id_map = id_map or {}      # externalId → IRI or dict
        self.slug_map = slug_map or {}   # slug → IRI or dict
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)

        # Check externalId lookups
        if "externalId" in sparql and "externalProvider" in sparql:
            for ext_id, info in self.id_map.items():
                if f'"{ext_id}"' in sparql:
                    if isinstance(info, str):
                        info = {"iri": info}
                    binding: dict = {
                        "task": {"type": "uri", "value": info["iri"]},
                    }
                    if info.get("title"):
                        binding["title"] = {"type": "literal", "value": info["title"]}
                    if info.get("status"):
                        binding["status"] = {"type": "literal", "value": info["status"]}
                    if info.get("lastSyncedAt"):
                        binding["lastSynced"] = {"type": "literal", "value": info["lastSyncedAt"]}
                    return {"results": {"bindings": [binding]}}

        # Check STRENDS slug lookups
        if "STRENDS" in sparql:
            for slug, info in self.slug_map.items():
                if slug in sparql:
                    if isinstance(info, str):
                        info = {"iri": info}
                    return {
                        "results": {
                            "bindings": [
                                {"task": {"type": "uri", "value": info["iri"]}}
                            ]
                        }
                    }

        # Person matcher queries (foaf/email/externalId without externalProvider)
        if "foaf" in sparql or "crm:email" in sparql:
            return {"results": {"bindings": []}}
        if "externalId" in sparql and "externalProvider" not in sparql:
            return {"results": {"bindings": []}}

        return {"results": {"bindings": []}}


class MockCommandClient:
    """Stub for CommandClient.

    Provides ``._client`` (MockHttpClient) for direct bulk POSTs and
    ``execute()`` for person matcher's object.create calls.
    """

    def __init__(self, http_client=None):
        self._client = http_client or MockHttpClient()
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        type_name = params["type"].split(":")[-1]
        return {"iri": f"https://example.org/data/{type_name}/{slug}"}


class MockResponse:
    """Minimal httpx.Response stub."""

    def __init__(self, status_code: int = 200, data=None,
                 headers: dict | None = None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.headers = headers or {}
        self.text = json.dumps(self._data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHttpClient:
    """Stub for httpx.AsyncClient — records POST calls."""

    def __init__(self):
        self.posts: list[dict] = []

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.posts.append({"url": url, "json": json, **kwargs})
        return MockResponse(200, {"ok": True})


class MockExternalHttpClient:
    """Stub for SDK's HttpClient (external requests to Todoist API).

    Records all requests and returns pre-configured responses.
    """

    def __init__(self, responses: list[MockResponse] | None = None):
        self.requests: list[dict] = []
        self._responses = list(responses or [])
        self._index = 0

    async def request(self, method: str, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        # Default: return empty list for projects (verify_token)
        return MockResponse(200, [{"id": "1", "name": "Project"}])

    async def get(self, url: str, **kwargs) -> MockResponse:
        return await self.request("GET", url, **kwargs)


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes."""

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
        ext_http_client: MockExternalHttpClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.commands = MockCommandClient(_http)
        self.http = ext_http_client or MockExternalHttpClient()
        self.app_id = "todoist-sync"


# ===================================================================
# Task fixtures
# ===================================================================


def make_task(
    task_id: str = "12345",
    content: str = "Fix bug",
    is_completed: bool = False,
    priority: int = 1,
    **overrides,
) -> dict:
    """Build a realistic Todoist task dict."""
    base = {
        "id": task_id,
        "content": content,
        "description": "Task description in markdown",
        "is_completed": is_completed,
        "priority": priority,
        "labels": ["bug"],
        "due": {"date": "2026-04-01", "datetime": None, "string": "Apr 1"},
        "project_id": "proj_001",
        "url": f"https://app.todoist.com/app/task/{task_id}",
        "assignee_id": None,
        "created_at": "2026-03-17T10:00:00Z",
    }
    base.update(overrides)
    return base


def _make_connected_state(
    selected_projects: list[str] | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account with token stored."""
    data: dict[str, str] = {
        "todoist_pat": "test_token_1234567890",
    }
    if selected_projects is not None:
        data["selected_projects"] = json.dumps(selected_projects)
    return data


def _make_todoist_responses(
    tasks: list[dict] | None = None,
    labels: list[dict] | None = None,
    projects: list[dict] | None = None,
) -> list[MockResponse]:
    """Build MockExternalHttpClient responses for Todoist API calls.

    Order of calls in pull_sync:
    1. verify_token: GET /rest/v2/projects (from get_connection_status)
    2. get_labels: GET /rest/v2/labels
    3. get_projects: GET /rest/v2/projects (for name lookup)
    4. get_tasks: GET /rest/v2/tasks?project_id=... (per project)
    """
    if tasks is None:
        tasks = []
    if labels is None:
        labels = []
    if projects is None:
        projects = [{"id": "proj_001", "name": "Test Project"}]

    return [
        # 1. verify_token (get_connection_status)
        MockResponse(200, projects),
        # 2. get_labels
        MockResponse(200, labels),
        # 3. get_projects (name lookup)
        MockResponse(200, projects),
        # 4. get_tasks for first project
        MockResponse(200, tasks),
    ]


# ===================================================================
# Tests: _find_existing_task
# ===================================================================


class TestFindExistingTask:

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self):
        graph = MockGraphClient()
        result = await _find_existing_task(graph, "99999")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_task_when_found(self):
        graph = MockGraphClient(id_map={
            "12345": {
                "iri": "urn:sempkm:task:td-abc123",
                "title": "Fix bug",
                "status": "todo",
            }
        })
        result = await _find_existing_task(graph, "12345")
        assert result is not None
        assert result["iri"] == "urn:sempkm:task:td-abc123"
        assert result["title"] == "Fix bug"

    @pytest.mark.asyncio
    async def test_sparql_contains_external_id(self):
        graph = MockGraphClient()
        await _find_existing_task(graph, "12345")
        assert len(graph.queries) == 1
        assert '"12345"' in graph.queries[0]
        assert "todoist" in graph.queries[0]


# ===================================================================
# Tests: _find_task_by_slug
# ===================================================================


class TestFindTaskBySlug:

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self):
        graph = MockGraphClient()
        result = await _find_task_by_slug(graph, "td-deadbeef")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_iri_when_found(self):
        graph = MockGraphClient(slug_map={
            "td-abc123": "urn:sempkm:task:td-abc123"
        })
        result = await _find_task_by_slug(graph, "td-abc123")
        assert result is not None
        assert result["iri"] == "urn:sempkm:task:td-abc123"


# ===================================================================
# Tests: _build_create_command
# ===================================================================


class TestBuildCreateCommand:

    def test_creates_task_command(self):
        props = {"dcterms:title": "Test task", f"{BPKM}priority": "high"}
        cmd = _build_create_command("td-abc123", props)
        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Task"
        assert cmd["params"]["slug"] == "td-abc123"
        assert cmd["params"]["properties"]["dcterms:title"] == "Test task"


# ===================================================================
# Tests: _build_update_commands
# ===================================================================


class TestBuildUpdateCommands:

    def test_patch_only_without_body(self):
        props = {"dcterms:title": "Updated task"}
        cmds = _build_update_commands("urn:task:1", props, None)
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"
        assert cmds[0]["params"]["iri"] == "urn:task:1"

    def test_patch_and_body_set(self):
        props = {"dcterms:title": "Updated task"}
        cmds = _build_update_commands("urn:task:1", props, "New description")
        assert len(cmds) == 2
        assert cmds[0]["command"] == "object.patch"
        assert cmds[1]["command"] == "body.set"
        assert cmds[1]["params"]["body"] == "New description"


# ===================================================================
# Tests: _submit_commands_batched
# ===================================================================


class TestSubmitCommandsBatched:

    @pytest.mark.asyncio
    async def test_empty_commands_does_nothing(self):
        http = MockHttpClient()
        result = await _submit_commands_batched(http, [])
        assert result == []
        assert len(http.posts) == 0

    @pytest.mark.asyncio
    async def test_single_batch(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {"slug": "a"}}]
        await _submit_commands_batched(http, cmds)
        assert len(http.posts) == 1
        assert http.posts[0]["json"]["source"] == "todoist-sync"

    @pytest.mark.asyncio
    async def test_includes_request_id_header(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {"slug": "a"}}]
        await _submit_commands_batched(http, cmds, request_id="req-123")
        assert http.posts[0]["headers"]["X-Request-Id"] == "req-123"


# ===================================================================
# Tests: pull_sync — skipped scenarios
# ===================================================================


class TestPullSyncSkipped:

    @pytest.mark.asyncio
    async def test_skipped_when_not_connected(self):
        ctx = MockAppContext(state_data={})
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    @pytest.mark.asyncio
    async def test_skipped_when_no_projects_selected(self):
        """Connected but no projects → skipped."""
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=None),
            ext_http_client=MockExternalHttpClient([
                MockResponse(200, [{"id": "1", "name": "P"}]),
            ]),
        )
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "no projects selected"

    @pytest.mark.asyncio
    async def test_skipped_when_empty_projects_list(self):
        """Connected but empty projects list → skipped."""
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=[]),
            ext_http_client=MockExternalHttpClient([
                MockResponse(200, [{"id": "1", "name": "P"}]),
            ]),
        )
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "no projects selected"


# ===================================================================
# Tests: pull_sync — creates new tasks
# ===================================================================


class TestPullSyncCreates:

    @pytest.mark.asyncio
    async def test_creates_single_task(self):
        task = make_task(task_id="111")
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["status"] == "success"
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["errors"] == 0

        # Verify create command was submitted
        posts = ctx.commands._client.posts
        assert len(posts) >= 1
        create_batch = posts[0]["json"]["commands"]
        assert create_batch[0]["command"] == "object.create"
        assert create_batch[0]["params"]["properties"]["dcterms:title"] == "Fix bug"

    @pytest.mark.asyncio
    async def test_creates_multiple_tasks(self):
        tasks = [
            make_task(task_id="111", content="Task A"),
            make_task(task_id="222", content="Task B"),
            make_task(task_id="333", content="Task C"),
        ]
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=tasks)
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 3
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_task_properties_include_external_provider(self):
        task = make_task(task_id="111")
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        create_batch = ctx.commands._client.posts[0]["json"]["commands"]
        props = create_batch[0]["params"]["properties"]
        assert props[f"{BPKM}externalProvider"] == "todoist"
        assert props[f"{BPKM}externalId"] == "111"

    @pytest.mark.asyncio
    async def test_task_slug_is_deterministic(self):
        task = make_task(task_id="111")
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        create_batch = ctx.commands._client.posts[0]["json"]["commands"]
        slug = create_batch[0]["params"]["slug"]
        expected_slug = compute_task_slug("111")
        assert slug == expected_slug

    @pytest.mark.asyncio
    async def test_task_with_description_gets_body_set(self):
        task = make_task(task_id="111", description="Some notes")

        # After create, we need the slug lookup to find the new IRI
        slug = compute_task_slug("111")
        graph = MockGraphClient(
            slug_map={slug: f"urn:sempkm:task:{slug}"},
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1

        # Phase 2 should include a body.set command
        all_posts = ctx.commands._client.posts
        # Find the body.set command across all batches
        all_commands = []
        for p in all_posts:
            all_commands.extend(p["json"]["commands"])
        body_cmds = [c for c in all_commands if c["command"] == "body.set"]
        assert len(body_cmds) == 1
        assert body_cmds[0]["params"]["body"] == "Some notes"

    @pytest.mark.asyncio
    async def test_task_without_description_no_body_set(self):
        task = make_task(task_id="111", description="")
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1

        # No phase 2 body.set
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        body_cmds = [c for c in all_commands if c["command"] == "body.set"]
        assert len(body_cmds) == 0


# ===================================================================
# Tests: pull_sync — updates existing tasks
# ===================================================================


class TestPullSyncUpdates:

    @pytest.mark.asyncio
    async def test_updates_existing_task(self):
        task = make_task(task_id="111", content="Updated title")
        graph = MockGraphClient(id_map={
            "111": {
                "iri": "urn:sempkm:task:td-abc",
                "title": "Old title",
                "status": "todo",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["updated"] == 1
        assert result["created"] == 0

        # Verify patch command
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        patch_cmds = [c for c in all_commands if c["command"] == "object.patch"]
        assert len(patch_cmds) >= 1
        assert patch_cmds[0]["params"]["iri"] == "urn:sempkm:task:td-abc"

    @pytest.mark.asyncio
    async def test_update_includes_body_set(self):
        task = make_task(task_id="111", description="New notes")
        graph = MockGraphClient(id_map={
            "111": {"iri": "urn:sempkm:task:td-abc"}
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        body_cmds = [c for c in all_commands if c["command"] == "body.set"]
        assert len(body_cmds) == 1
        assert body_cmds[0]["params"]["body"] == "New notes"

    @pytest.mark.asyncio
    async def test_mix_of_creates_and_updates(self):
        tasks = [
            make_task(task_id="111", content="Existing"),
            make_task(task_id="222", content="New task"),
        ]
        graph = MockGraphClient(id_map={
            "111": {"iri": "urn:sempkm:task:td-existing"}
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=tasks)
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1
        assert result["updated"] == 1


# ===================================================================
# Tests: pull_sync — assignee resolution
# ===================================================================


class TestPullSyncAssignees:

    @pytest.mark.asyncio
    async def test_task_with_assignee_creates_edge(self):
        task = make_task(task_id="111", assignee_id="user_abc")
        slug = compute_task_slug("111")
        graph = MockGraphClient(
            slug_map={slug: f"urn:sempkm:task:{slug}"},
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1

        # Should have edge.create in phase 2
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        edge_cmds = [c for c in all_commands if c["command"] == "edge.create"]
        assert len(edge_cmds) >= 1
        assert edge_cmds[0]["params"]["predicate"] == f"{BPKM}assignedTo"

    @pytest.mark.asyncio
    async def test_task_without_assignee_no_edge(self):
        task = make_task(task_id="111", assignee_id=None)
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        result = await pull_sync(ctx)
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        edge_cmds = [c for c in all_commands if c["command"] == "edge.create"]
        assert len(edge_cmds) == 0

    @pytest.mark.asyncio
    async def test_existing_task_with_assignee_gets_edge(self):
        task = make_task(task_id="111", assignee_id="user_abc")
        graph = MockGraphClient(id_map={
            "111": {"iri": "urn:sempkm:task:td-existing"}
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        all_commands = []
        for p in ctx.commands._client.posts:
            all_commands.extend(p["json"]["commands"])
        edge_cmds = [c for c in all_commands if c["command"] == "edge.create"]
        assert len(edge_cmds) >= 1


# ===================================================================
# Tests: pull_sync — per-task error isolation
# ===================================================================


class TestPullSyncErrorIsolation:

    @pytest.mark.asyncio
    async def test_one_bad_task_doesnt_kill_batch(self):
        """If one task fails processing, others still get created."""
        good_task = make_task(task_id="111", content="Good task")
        # Task with an ID that triggers no errors, but we'll make the
        # graph fail on the second lookup
        bad_task = make_task(task_id="222", content="Bad task")

        class FailOnSecondGraphClient(MockGraphClient):
            def __init__(self):
                super().__init__()
                self._call_count = 0

            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                self._call_count += 1
                # Fail on the externalId check for "222"
                if '"222"' in sparql and "externalProvider" in sparql:
                    raise RuntimeError("SPARQL timeout")
                return {"results": {"bindings": []}}

        graph = FailOnSecondGraphClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=graph,
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[good_task, bad_task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1  # good_task created
        assert result["errors"] == 1   # bad_task errored
        assert result["status"] == "partial"
        assert len(result["error_details"]) == 1
        assert result["error_details"][0]["task_id"] == "222"

    @pytest.mark.asyncio
    async def test_project_fetch_failure_isolated(self):
        """If fetching tasks from one project fails, others still process."""
        task = make_task(task_id="111")

        class FailOnSecondProject(MockExternalHttpClient):
            def __init__(self, responses):
                super().__init__(responses)

            async def request(self, method, url, **kwargs):
                self.requests.append({"method": method, "url": url, **kwargs})
                if self._index < len(self._responses):
                    resp = self._responses[self._index]
                    self._index += 1
                    return resp
                return MockResponse(200, [])

        responses = [
            # verify_token
            MockResponse(200, [{"id": "1", "name": "P"}]),
            # get_labels
            MockResponse(200, []),
            # get_projects
            MockResponse(200, []),
            # get_tasks for first project — success
            MockResponse(200, [task]),
            # get_tasks for second project — failure
            MockResponse(500, {"error": "server error"}),
        ]

        ctx = MockAppContext(
            state_data=_make_connected_state(
                selected_projects=["proj_001", "proj_002"]
            ),
            ext_http_client=FailOnSecondProject(responses),
        )

        result = await pull_sync(ctx)
        # First project's task created successfully
        assert result["created"] == 1
        # Second project fetch failed
        assert result["errors"] == 1
        assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_all_tasks_error_gives_error_status(self):
        """If all tasks fail, status is 'error'."""
        bad_task = make_task(task_id="111")

        class AlwaysFailGraph(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "externalProvider" in sparql:
                    raise RuntimeError("DB down")
                return {"results": {"bindings": []}}

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=AlwaysFailGraph(),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[bad_task])
            ),
        )

        result = await pull_sync(ctx)
        assert result["errors"] == 1
        assert result["created"] == 0
        assert result["status"] == "error"


# ===================================================================
# Tests: pull_sync — result structure
# ===================================================================


class TestPullSyncResultStructure:

    @pytest.mark.asyncio
    async def test_result_has_all_required_keys(self):
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[])
            ),
        )

        result = await pull_sync(ctx)
        assert "status" in result
        assert "created" in result
        assert "updated" in result
        assert "unchanged" in result
        assert "errors" in result
        assert "error_details" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_result_saved_to_state(self):
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[])
            ),
        )

        await pull_sync(ctx)
        stored = await ctx.state.get("last_pull_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "success"

    @pytest.mark.asyncio
    async def test_duration_ms_is_positive(self):
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[make_task()])
            ),
        )

        result = await pull_sync(ctx)
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_skipped_result_has_reason(self):
        ctx = MockAppContext(state_data={})
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_error_details_contain_task_ids(self):
        """error_details entries include the task_id that failed."""
        bad_task = make_task(task_id="999")

        class FailGraph(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "externalProvider" in sparql:
                    raise RuntimeError("fail")
                return {"results": {"bindings": []}}

        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            graph_client=FailGraph(),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[bad_task])
            ),
        )

        result = await pull_sync(ctx)
        assert len(result["error_details"]) == 1
        assert result["error_details"][0]["task_id"] == "999"


# ===================================================================
# Tests: pull_sync — labels integration
# ===================================================================


class TestPullSyncLabels:

    @pytest.mark.asyncio
    async def test_labels_included_in_properties(self):
        task = make_task(task_id="111", labels=["bug", "urgent"])
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(
                    tasks=[task],
                    labels=[{"id": "L1", "name": "bug"}, {"id": "L2", "name": "urgent"}],
                )
            ),
        )

        await pull_sync(ctx)
        create_batch = ctx.commands._client.posts[0]["json"]["commands"]
        props = create_batch[0]["params"]["properties"]
        tags = props.get(f"{BPKM}tags", [])
        assert "bug" in tags
        assert "urgent" in tags


# ===================================================================
# Tests: pull_sync — priority mapping
# ===================================================================


class TestPullSyncPriority:

    @pytest.mark.asyncio
    async def test_priority_1_maps_to_low(self):
        task = make_task(task_id="111", priority=1)
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        props = ctx.commands._client.posts[0]["json"]["commands"][0]["params"]["properties"]
        assert props[f"{BPKM}priority"] == "low"

    @pytest.mark.asyncio
    async def test_priority_4_maps_to_critical(self):
        task = make_task(task_id="111", priority=4)
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        props = ctx.commands._client.posts[0]["json"]["commands"][0]["params"]["properties"]
        assert props[f"{BPKM}priority"] == "critical"


# ===================================================================
# Tests: pull_sync — idempotency
# ===================================================================


class TestPullSyncIdempotency:

    @pytest.mark.asyncio
    async def test_create_batch_has_request_id(self):
        task = make_task(task_id="111")
        ctx = MockAppContext(
            state_data=_make_connected_state(selected_projects=["proj_001"]),
            ext_http_client=MockExternalHttpClient(
                _make_todoist_responses(tasks=[task])
            ),
        )

        await pull_sync(ctx)
        # The first bulk post (creates) should have X-Request-Id
        posts = ctx.commands._client.posts
        assert len(posts) >= 1
        headers = posts[0].get("headers", {})
        assert "X-Request-Id" in headers
        assert len(headers["X-Request-Id"]) > 0
