"""Unit tests for the Linear pull sync engine.

Loads ``sync_engine.py`` (and its dependencies) from the apps directory
via importlib so the app does not need to be installed as a package.
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
    sys.modules[name] = mod  # make available to dependent modules
    spec.loader.exec_module(mod)
    return mod


# Load in dependency order so that sync_engine's try/except imports resolve.
_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_person_matcher = _load_module("person_matcher", _SERVICES_DIR / "person_matcher.py")
# auth needs linear_client for LinearAuthError; load linear_client first
_linear_client = _load_module("linear_client", _SERVICES_DIR / "linear_client.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
_find_existing_task = _sync_engine._find_existing_task
_submit_commands_batched = _sync_engine._submit_commands_batched
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
compute_issue_slug = _field_mapper.compute_issue_slug


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

    Supports two modes:
    - Static: always returns ``self.default_results``
    - Dynamic: if a STRENDS slug matches an entry in ``self.slug_map``,
      returns a binding for that slug.
    """

    def __init__(
        self,
        default_results: dict | None = None,
        slug_map: dict[str, str] | None = None,
    ):
        self.default_results = default_results or {"results": {"bindings": []}}
        self.slug_map = slug_map or {}  # slug → task IRI
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        # Check if this is a _find_existing_task query with STRENDS
        if "STRENDS" in sparql:
            for slug, iri in self.slug_map.items():
                if slug in sparql:
                    return {
                        "results": {
                            "bindings": [
                                {
                                    "task": {"type": "uri", "value": iri},
                                    "status": {
                                        "type": "literal",
                                        "value": "in-progress",
                                    },
                                    "extId": {"type": "literal", "value": "ENG-1"},
                                }
                            ]
                        }
                    }
        # Check if it looks like a person matcher query (foaf mbox or crm email)
        if "foaf" in sparql or "crm:email" in sparql:
            return self.default_results
        return self.default_results


class MockCommandClient:
    """Stub for CommandClient.

    Provides ``._client`` (MockHttpClient) for direct bulk POSTs and
    ``execute()`` for person matcher's object.create calls.
    """

    def __init__(self, http_client: MockHttpClient | None = None):
        self._client = http_client or MockHttpClient()
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        type_name = params["type"].split(":")[-1]
        return {"iri": f"https://example.org/data/{type_name}/{slug}"}


class MockHttpClient:
    """Stub for httpx.AsyncClient — records POST calls.

    Used for both the sync engine's bulk command POSTs and the
    LinearClient's GraphQL requests.
    """

    def __init__(self, graphql_responses: list[dict] | None = None):
        self.posts: list[dict] = []
        self._graphql_responses = list(graphql_responses or [])
        self._gql_index = 0

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.posts.append({"url": url, "json": json, **kwargs})
        # If this is a GraphQL request, return from the queue
        if url.startswith("https://"):
            resp_data = {}
            if self._gql_index < len(self._graphql_responses):
                resp_data = self._graphql_responses[self._gql_index]
                self._gql_index += 1
            return MockResponse(200, resp_data)
        # Bulk command response
        return MockResponse(200, {"ok": True})


class MockResponse:
    """Minimal httpx.Response stub."""

    def __init__(self, status_code: int = 200, data: dict | None = None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes."""

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.http = _http
        self.commands = MockCommandClient(_http)
        self.app_id = "linear-sync"


# ===================================================================
# Issue fixtures
# ===================================================================


def make_issue(
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


def _make_connected_state(
    teams: list[str] | None = None,
    last_sync_at: str | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account with teams selected."""
    data = {
        "auth_method": "api_key",
        "api_key": "lin_test_key",
        "workspace_name": "TestCo",
        "workspace_id": "ws-123",
        "sync_teams": json.dumps(teams or ["team-1"]),
    }
    if last_sync_at:
        data["last_sync_at"] = last_sync_at
    return data


# ===================================================================
# Tests — auth / state checks
# ===================================================================


@pytest.mark.asyncio
async def test_skips_when_not_connected():
    """Returns skipped status when no auth is configured."""
    ctx = MockAppContext(state_data={"auth_method": ""})
    result = await pull_sync(ctx)
    assert result["status"] == "skipped"
    assert result["reason"] == "not connected"


@pytest.mark.asyncio
async def test_skips_when_no_teams_selected():
    """Returns skipped status when connected but no sync_teams configured."""
    ctx = MockAppContext(state_data={
        "auth_method": "api_key",
        "api_key": "key",
        "workspace_name": "Co",
        "workspace_id": "ws-1",
    })
    result = await pull_sync(ctx)
    assert result["status"] == "skipped"
    assert result["reason"] == "no teams selected"


# ===================================================================
# Tests — new issue creation
# ===================================================================


@pytest.mark.asyncio
async def test_creates_task_for_new_issue():
    """New issue (no existing task) produces object.create in bulk POST."""
    issue = make_issue()
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    result = await pull_sync(ctx)

    assert result["status"] == "ok"
    assert result["created"] == 1
    # At least one POST to /api/commands/bulk
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    assert len(bulk_posts) >= 1
    # Phase 1 should contain an object.create
    phase1 = bulk_posts[0]
    create_cmds = [
        c for c in phase1["json"]["commands"] if c["command"] == "object.create"
    ]
    assert len(create_cmds) == 1


@pytest.mark.asyncio
async def test_create_command_has_correct_properties():
    """object.create command has type, slug, and properties with expected keys."""
    issue = make_issue(id="issue-2", title="New feature")
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    create_cmd = [
        c
        for p in bulk_posts
        for c in p["json"]["commands"]
        if c["command"] == "object.create"
    ][0]
    params = create_cmd["params"]
    assert params["type"] == f"{BPKM}Task"
    assert "slug" in params
    assert "dcterms:title" in params["properties"]
    assert params["properties"]["dcterms:title"] == "New feature"


@pytest.mark.asyncio
async def test_create_command_has_deterministic_slug():
    """Slug matches compute_issue_slug output for the same workspace+issue ID."""
    issue = make_issue(id="issue-slug-test")
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    expected_slug = compute_issue_slug("ws-123", "issue-slug-test")
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    create_cmd = [
        c
        for p in bulk_posts
        for c in p["json"]["commands"]
        if c["command"] == "object.create"
    ][0]
    assert create_cmd["params"]["slug"] == expected_slug


@pytest.mark.asyncio
async def test_body_set_for_new_issue_with_description():
    """Phase 2 submits body.set after discovering the newly created task's IRI."""
    issue = make_issue(id="issue-body", description="Detailed description")
    slug = compute_issue_slug("ws-123", "issue-body")
    task_iri = f"https://example.org/data/Task/{slug}"

    # GraphClient returns empty on first lookup (new), then found on phase 2
    graph = MockGraphClient(slug_map={slug: task_iri})
    # Override default_results to return empty for STRENDS queries not in slug_map
    # The slug_map handles phase 2 discovery.  First lookup (during issue processing)
    # should return empty — we accomplish this by NOT having the slug in slug_map
    # initially, then adding it.  But MockGraphClient is simpler with a trick:
    # return empty for person-matcher queries, and use slug_map for STRENDS.

    # Actually, during issue processing _find_existing_task will also match slug_map.
    # We need the first call to return empty, the second to return the IRI.
    # Use a stateful graph client instead.

    class StatefulGraph:
        def __init__(self):
            self.queries = []
            self._call_count = 0

        async def query(self, sparql):
            self.queries.append(sparql)
            self._call_count += 1
            # First STRENDS call → not found (new issue)
            # Second STRENDS call → found (phase 2 discovery)
            if "STRENDS" in sparql:
                if self._call_count <= 1:
                    return {"results": {"bindings": []}}
                return {
                    "results": {
                        "bindings": [
                            {"task": {"type": "uri", "value": task_iri}}
                        ]
                    },
                }
            return {"results": {"bindings": []}}

    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)
    ctx.graph = StatefulGraph()

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
    assert len(body_cmds) >= 1
    assert body_cmds[0]["params"]["iri"] == task_iri
    assert body_cmds[0]["params"]["body"] == "Detailed description"


# ===================================================================
# Tests — existing issue update
# ===================================================================


@pytest.mark.asyncio
async def test_patches_existing_task():
    """Existing task (SPARQL returns IRI) produces object.patch in bulk POST."""
    issue = make_issue(id="issue-exist")
    slug = compute_issue_slug("ws-123", "issue-exist")
    task_iri = f"https://example.org/data/Task/{slug}"

    graph = MockGraphClient(slug_map={slug: task_iri})
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)
    ctx.graph = graph

    result = await pull_sync(ctx)

    assert result["updated"] == 1
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    patch_cmds = [c for c in all_cmds if c["command"] == "object.patch"]
    assert len(patch_cmds) >= 1
    assert patch_cmds[0]["params"]["iri"] == task_iri


@pytest.mark.asyncio
async def test_body_set_for_existing_task():
    """Existing task with description gets body.set using existing IRI."""
    issue = make_issue(id="issue-body-exist", description="Updated body")
    slug = compute_issue_slug("ws-123", "issue-body-exist")
    task_iri = f"https://example.org/data/Task/{slug}"

    graph = MockGraphClient(slug_map={slug: task_iri})
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)
    ctx.graph = graph

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
    assert len(body_cmds) == 1
    assert body_cmds[0]["params"]["iri"] == task_iri
    assert body_cmds[0]["params"]["body"] == "Updated body"


# ===================================================================
# Tests — assignee handling
# ===================================================================


@pytest.mark.asyncio
async def test_assignee_creates_edge():
    """Existing task with assignee produces edge.create for assignedTo."""
    issue = make_issue(id="issue-assign")
    slug = compute_issue_slug("ws-123", "issue-assign")
    task_iri = f"https://example.org/data/Task/{slug}"

    graph = MockGraphClient(slug_map={slug: task_iri})
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)
    ctx.graph = graph

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    edge_cmds = [c for c in all_cmds if c["command"] == "edge.create"]
    assert len(edge_cmds) >= 1
    assert edge_cmds[0]["params"]["source"] == task_iri
    assert edge_cmds[0]["params"]["predicate"] == f"{BPKM}assignedTo"


@pytest.mark.asyncio
async def test_no_assignee_no_edge():
    """Issue without assignee produces no edge.create command."""
    issue = make_issue(id="issue-noassign", assignee=None)
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    edge_cmds = [c for c in all_cmds if c["command"] == "edge.create"]
    assert len(edge_cmds) == 0


# ===================================================================
# Tests — trashed issues
# ===================================================================


@pytest.mark.asyncio
async def test_skips_new_trashed_issue():
    """Trashed issue with no existing task produces zero commands."""
    issue = make_issue(id="issue-trash-new", trashed=True)
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    result = await pull_sync(ctx)

    assert result["created"] == 0
    assert result["updated"] == 0
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    assert len(bulk_posts) == 0


@pytest.mark.asyncio
async def test_cancels_existing_trashed_issue():
    """Trashed issue with existing task patches status to cancelled."""
    issue = make_issue(id="issue-trash-exist", trashed=True)
    slug = compute_issue_slug("ws-123", "issue-trash-exist")
    task_iri = f"https://example.org/data/Task/{slug}"

    graph = MockGraphClient(slug_map={slug: task_iri})
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)
    ctx.graph = graph

    result = await pull_sync(ctx)

    assert result["updated"] == 1
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    patch_cmds = [c for c in all_cmds if c["command"] == "object.patch"]
    assert len(patch_cmds) == 1
    assert patch_cmds[0]["params"]["properties"][f"{BPKM}taskStatus"] == "cancelled"


# ===================================================================
# Tests — delta sync cursor
# ===================================================================


@pytest.mark.asyncio
async def test_stores_last_sync_at_on_success():
    """Successful sync stores a last_sync_at timestamp in state."""
    issue = make_issue()
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    last_sync = await ctx.state.get("last_sync_at")
    assert last_sync is not None
    assert "T" in last_sync  # ISO-8601 format


@pytest.mark.asyncio
async def test_passes_last_sync_at_to_query():
    """When last_sync_at exists, the GraphQL query includes updatedAfter."""
    issue = make_issue()
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(
        state_data=_make_connected_state(last_sync_at="2026-03-17T00:00:00+00:00"),
        http_client=http,
    )

    await pull_sync(ctx)

    # The GraphQL POST should include updatedAfter in variables
    gql_posts = [p for p in http.posts if "linear.app" in p["url"]]
    assert len(gql_posts) >= 1
    variables = gql_posts[0]["json"]["variables"]
    assert "updatedAfter" in variables
    assert variables["updatedAfter"] == "2026-03-17T00:00:00+00:00"


# ===================================================================
# Tests — batching
# ===================================================================


@pytest.mark.asyncio
async def test_batches_large_command_sets():
    """1500 commands are submitted in 2 batches (1000 + 500)."""
    http = MockHttpClient()
    commands = [{"command": "object.patch", "params": {"iri": f"iri-{i}"}} for i in range(1500)]

    await _submit_commands_batched(http, commands, "test batch", "test")

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    assert len(bulk_posts) == 2
    assert len(bulk_posts[0]["json"]["commands"]) == 1000
    assert len(bulk_posts[1]["json"]["commands"]) == 500


# ===================================================================
# Tests — error handling
# ===================================================================


@pytest.mark.asyncio
async def test_per_issue_error_does_not_abort_sync():
    """One bad issue doesn't prevent others from being processed."""
    good_issue = make_issue(id="good-1", title="Good")
    # Bad issue — missing 'id' key in a way that causes an error
    bad_issue = {"title": "Bad", "state": {"type": "started"}}

    http = MockHttpClient(
        graphql_responses=[_graphql_issues_response([bad_issue, good_issue])]
    )
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    result = await pull_sync(ctx)

    # Should still complete and process at least one issue
    assert result["status"] == "ok"
    # Either created or errors should be non-empty
    total = result["created"] + result["updated"] + len(result["errors"])
    assert total >= 1


@pytest.mark.asyncio
async def test_error_recorded_in_result():
    """Per-issue errors appear in the result's errors list with issue_id and message."""
    # Issue that will fail — missing required 'id' key
    bad_issue = {"title": "Bad", "state": {"type": "started"}}

    http = MockHttpClient(
        graphql_responses=[_graphql_issues_response([bad_issue])]
    )
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    result = await pull_sync(ctx)

    assert len(result["errors"]) >= 1
    err = result["errors"][0]
    assert "issue_id" in err
    assert "error" in err


# ===================================================================
# Tests — result shape
# ===================================================================


@pytest.mark.asyncio
async def test_result_contains_counts():
    """Result dict has status, created, updated, unchanged, and errors fields."""
    issue = make_issue()
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    result = await pull_sync(ctx)

    assert "status" in result
    assert "created" in result
    assert "updated" in result
    assert "unchanged" in result
    assert "errors" in result
    assert isinstance(result["errors"], list)


# ===================================================================
# Tests — bulk command bypass
# ===================================================================


@pytest.mark.asyncio
async def test_commands_posted_directly_not_via_sdk():
    """Commands go to /api/commands/bulk via http_client, not SDK execute()."""
    issue = make_issue(id="issue-bypass")
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    # http_client.post was called with /api/commands/bulk
    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    assert len(bulk_posts) >= 1

    # SDK CommandClient.execute was NOT called for task commands
    # (it may be called by PersonMatcher for creating persons)
    task_sdk_calls = [
        c for c in ctx.commands.commands if c["params"].get("type", "").endswith("Task")
    ]
    assert len(task_sdk_calls) == 0


# ===================================================================
# Tests — no-description new issue
# ===================================================================


@pytest.mark.asyncio
async def test_new_issue_without_description_skips_body_set():
    """New issue with empty description produces no body.set in phase 2."""
    issue = make_issue(id="issue-nodesc", description=None)
    http = MockHttpClient(graphql_responses=[_graphql_issues_response([issue])])
    ctx = MockAppContext(state_data=_make_connected_state(), http_client=http)

    await pull_sync(ctx)

    bulk_posts = [p for p in http.posts if p["url"] == "/api/commands/bulk"]
    all_cmds = [c for p in bulk_posts for c in p["json"]["commands"]]
    body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
    assert len(body_cmds) == 0
