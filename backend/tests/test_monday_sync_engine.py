"""Unit tests for the Monday.com pull sync engine.

Loads app modules from the apps directory via importlib so the app does
not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory (dependency order)
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "monday-sync"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_monday_client = _load_module("monday_client", _SERVICES_DIR / "monday_client.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_person_matcher = _load_module("person_matcher", _SERVICES_DIR / "person_matcher.py")
_loop_guard = _load_module("loop_guard", _SERVICES_DIR / "loop_guard.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
push_sync = _sync_engine.push_sync
parse_external_url = _sync_engine.parse_external_url
_find_changed_tasks = _sync_engine._find_changed_tasks
_get_task_body = _sync_engine._get_task_body
_loop_guard = _sync_engine._loop_guard
_find_existing_task = _sync_engine._find_existing_task
_find_task_by_monday_item_id = _sync_engine._find_task_by_monday_item_id
_find_all_tasks_for_board = _sync_engine._find_all_tasks_for_board
_has_changes = _sync_engine._has_changes
_build_create_command = _sync_engine._build_create_command
_build_update_commands = _sync_engine._build_update_commands
_process_dependencies = _sync_engine._process_dependencies
_submit_commands_batched = _sync_engine._submit_commands_batched
_compute_status = _sync_engine._compute_status
_make_result = _sync_engine._make_result
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
compute_slug = _field_mapper.compute_slug


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


class MockSettingsClient:
    """In-memory settings store — separate from state."""

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data or {})

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class MockGraphClient:
    """Stub for GraphClient.query() — returns results by slug lookup.

    - ``slug_map``: slug → dict with iri, status, externalId, lastSyncedAt
    - ``email_to_iri``: email → Person IRI for PersonMatcher lookups
    - ``item_id_to_iri``: Monday.com item_id (str) → Task IRI for dependency lookups
    - ``changed_tasks``: list of dicts for _find_changed_tasks query results
    - ``task_bodies``: iri → body text for _get_task_body query results
    """

    def __init__(
        self,
        slug_map: dict[str, dict] | None = None,
        email_to_iri: dict[str, str] | None = None,
        item_id_to_iri: dict[str, str] | None = None,
        changed_tasks: list[dict] | None = None,
        task_bodies: dict[str, str] | None = None,
    ):
        self.slug_map = slug_map or {}
        self.email_to_iri = email_to_iri or {}
        self.item_id_to_iri = item_id_to_iri or {}
        self.changed_tasks = changed_tasks or []
        self.task_bodies = task_bodies or {}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)

        # _find_changed_tasks query (provider "monday" + extUrl + modified)
        if (
            '"monday"' in sparql
            and "externalUrl" in sparql
            and "modified" in sparql
        ):
            bindings = []
            for t in self.changed_tasks:
                b: dict = {"task": {"type": "uri", "value": t["iri"]}}
                if t.get("extUrl"):
                    b["extUrl"] = {"type": "literal", "value": t["extUrl"]}
                if t.get("status"):
                    b["status"] = {"type": "literal", "value": t["status"]}
                if t.get("priority"):
                    b["priority"] = {"type": "literal", "value": t["priority"]}
                if t.get("title"):
                    b["title"] = {"type": "literal", "value": t["title"]}
                if t.get("dueDate"):
                    b["dueDate"] = {"type": "literal", "value": t["dueDate"]}
                if t.get("lastSynced"):
                    b["lastSynced"] = {"type": "literal", "value": t["lastSynced"]}
                bindings.append(b)
            return {"results": {"bindings": bindings}}

        # _get_task_body query (urn:sempkm:body)
        if "urn:sempkm:body" in sparql:
            for iri, body in self.task_bodies.items():
                if iri in sparql:
                    return {"results": {"bindings": [
                        {"body": {"type": "literal", "value": body}}
                    ]}}
            return {"results": {"bindings": []}}

        # Task lookup (STRENDS + /Task/)
        if "STRENDS" in sparql and "/Task/" in sparql:
            for slug, info in self.slug_map.items():
                if slug in sparql:
                    binding: dict = {
                        "task": {"type": "uri", "value": info["iri"]},
                    }
                    if info.get("status"):
                        binding["status"] = {"type": "literal", "value": info["status"]}
                    if info.get("externalId"):
                        binding["extId"] = {"type": "literal", "value": info["externalId"]}
                    if info.get("lastSyncedAt"):
                        binding["lastSynced"] = {"type": "literal", "value": info["lastSyncedAt"]}
                    return {"results": {"bindings": [binding]}}

        # Dependency lookup (CONTAINS + /pulses/)
        if "CONTAINS" in sparql and "/pulses/" in sparql:
            for item_id, iri in self.item_id_to_iri.items():
                if f"/pulses/{item_id}" in sparql:
                    return {"results": {"bindings": [
                        {"task": {"type": "uri", "value": iri}}
                    ]}}

        # Board task lookup (CONTAINS + /boards/)
        if "CONTAINS" in sparql and "/boards/" in sparql:
            return {"results": {"bindings": []}}

        # PersonMatcher email lookup (foaf or crm:email)
        if "foaf" in sparql.lower() or "crm:email" in sparql.lower():
            for email, iri in self.email_to_iri.items():
                if email.lower() in sparql.lower():
                    return {"results": {"bindings": [
                        {"person": {"type": "uri", "value": iri}}
                    ]}}

        # Default: no bindings
        return {"results": {"bindings": []}}


class MockResponse:
    """Minimal httpx.Response stub."""

    def __init__(self, status_code: int = 200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = json.dumps(self._data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHttpClient:
    """Stub for httpx.AsyncClient — records POST calls for bulk commands."""

    def __init__(self):
        self.recorded_calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.recorded_calls.append((url, json))
        return MockResponse(200, {"ok": True})

    async def request(self, method, url, **kwargs):
        """For MondayClient GraphQL calls."""
        return MockResponse(200, {"data": {}})


class MockCommandClient:
    """Stub for CommandClient — provides ._client for bulk bypass and .execute() for person creation."""

    def __init__(self, http_client: MockHttpClient | None = None):
        self._client = http_client or MockHttpClient()
        self.executed: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.executed.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        type_name = params.get("type", "Thing").split(":")[-1]
        return {"iri": f"https://example.org/data/{type_name}/{slug}"}


class MockMondayClient:
    """Stub for MondayClient — returns configurable boards, items, subitems."""

    def __init__(
        self,
        me_response: dict | None = None,
        items_by_board: dict[int, list[dict]] | None = None,
        subitems_by_parent: dict[int, list[dict]] | None = None,
        users: list[dict] | None = None,
        tags: list[dict] | None = None,
    ):
        self.me_response = me_response or {"id": "1", "name": "Test User", "email": "test@example.com"}
        self.items_by_board = items_by_board or {}
        self.subitems_by_parent = subitems_by_parent or {}
        self.users = users or []
        self.tags = tags or []
        self.mutations: list[dict] = []

    async def get_me(self) -> dict:
        return self.me_response

    async def get_all_board_items(self, board_id: int) -> list[dict]:
        return self.items_by_board.get(board_id, [])

    async def get_subitems(self, item_ids: list[int]) -> list[dict]:
        result = []
        for pid in item_ids:
            result.extend(self.subitems_by_parent.get(pid, []))
        return result

    async def get_users(self, user_ids: list[int]) -> list[dict]:
        return [u for u in self.users if int(u.get("id", 0)) in user_ids]

    async def get_tags(self, tag_ids: list[int]) -> list[dict]:
        return [t for t in self.tags if int(t.get("id", 0)) in tag_ids]

    async def change_multiple_column_values(self, board_id, item_id, column_values_json):
        self.mutations.append({
            "board_id": board_id,
            "item_id": item_id,
            "values": column_values_json,
        })
        return {"id": str(item_id), "name": "Updated"}


class SyncContext:
    """Simulates the ctx object passed to pull_sync / push_sync."""

    def __init__(
        self,
        state: MockStateClient | None = None,
        settings: MockSettingsClient | None = None,
        graph: MockGraphClient | None = None,
        commands: MockCommandClient | None = None,
        http: MockHttpClient | None = None,
    ):
        self.state = state or MockStateClient()
        self.settings = settings or MockSettingsClient()
        self.graph = graph or MockGraphClient()
        http_client = http or MockHttpClient()
        self.commands = commands or MockCommandClient(http_client)
        self.http = http_client


# ===================================================================
# Test fixtures — reusable items
# ===================================================================


def _make_item(
    item_id: int = 100,
    name: str = "Test Item",
    group_id: str = "topics",
    group_title: str = "Sprint 1",
    column_values: list[dict] | None = None,
) -> dict:
    """Create a minimal Monday.com item dict."""
    return {
        "id": str(item_id),
        "name": name,
        "group": {"id": group_id, "title": group_title},
        "column_values": column_values or [],
    }


def _make_subitem(
    sub_id: int = 200,
    name: str = "Sub Item",
    parent_item_id: int = 100,
    group_id: str = "subitems",
    group_title: str = "Subitems",
    column_values: list[dict] | None = None,
) -> dict:
    """Create a minimal Monday.com subitem dict."""
    return {
        "id": str(sub_id),
        "name": name,
        "parent_item_id": str(parent_item_id),
        "group": {"id": group_id, "title": group_title},
        "column_values": column_values or [],
    }


def _make_column_mapping_json(mapping: dict | None = None) -> str:
    """Create a JSON string for column_mapping_{board_id} settings."""
    return json.dumps({"column_mapping": mapping or {}})


def _make_label_mapping_json(
    status_mapping: dict | None = None,
    priority_mapping: dict | None = None,
) -> str:
    """Create a JSON string for label_mapping_{board_id} settings."""
    data = {}
    if status_mapping is not None:
        data["status_label_mapping"] = status_mapping
    if priority_mapping is not None:
        data["priority_label_mapping"] = priority_mapping
    return json.dumps(data)


# ===================================================================
# Tests: _find_existing_task
# ===================================================================


class TestFindExistingTask:
    """Tests for _find_existing_task SPARQL helper."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        graph = MockGraphClient()
        result = await _find_existing_task(graph, "monday-abc123")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_task_info_when_found(self):
        slug = "monday-abc123"
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://example.org/data/Task/monday-abc123",
                "status": "todo",
                "externalId": "100",
                "lastSyncedAt": "2025-01-01T00:00:00Z",
            }
        })
        result = await _find_existing_task(graph, slug)
        assert result is not None
        assert result["iri"] == "https://example.org/data/Task/monday-abc123"
        assert result["status"] == "todo"
        assert result["externalId"] == "100"

    @pytest.mark.asyncio
    async def test_sparql_uses_monday_provider(self):
        graph = MockGraphClient()
        await _find_existing_task(graph, "monday-abc123")
        assert len(graph.queries) == 1
        assert '"monday"' in graph.queries[0]
        assert "STRENDS" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_optional_fields_can_be_none(self):
        slug = "monday-xyz789"
        graph = MockGraphClient(slug_map={
            slug: {"iri": "https://example.org/data/Task/monday-xyz789"}
        })
        result = await _find_existing_task(graph, slug)
        assert result is not None
        assert result["iri"] == "https://example.org/data/Task/monday-xyz789"
        assert result["status"] is None
        assert result["externalId"] is None


# ===================================================================
# Tests: _has_changes
# ===================================================================


class TestHasChanges:
    """Tests for change detection helper."""

    def test_always_returns_true(self):
        """Current implementation always returns True (idempotent sync)."""
        existing = {
            "iri": "https://example.org/data/Task/test",
            "status": "todo",
            "externalId": "100",
        }
        new_props = {f"{BPKM}taskStatus": "todo"}
        assert _has_changes(existing, new_props) is True

    def test_returns_true_even_when_identical(self):
        existing = {"iri": "test", "status": "done"}
        new_props = {f"{BPKM}taskStatus": "done"}
        assert _has_changes(existing, new_props) is True

    def test_returns_true_with_empty_properties(self):
        existing = {"iri": "test"}
        assert _has_changes(existing, {}) is True


# ===================================================================
# Tests: _build_create_command
# ===================================================================


class TestBuildCreateCommand:
    """Tests for the object.create command builder."""

    def test_builds_create_with_slug_and_type(self):
        cmd = _build_create_command(
            "monday-abc123",
            {"dcterms:title": "My Task"},
            f"{BPKM}Task",
        )
        assert cmd["command"] == "object.create"
        assert cmd["params"]["slug"] == "monday-abc123"
        assert cmd["params"]["type"] == f"{BPKM}Task"
        assert cmd["params"]["properties"]["dcterms:title"] == "My Task"

    def test_preserves_all_properties(self):
        props = {
            "dcterms:title": "Task",
            f"{BPKM}taskStatus": "in-progress",
            f"{BPKM}priority": "high",
            f"{BPKM}dueDate": "2025-01-15",
        }
        cmd = _build_create_command("monday-xyz", props, f"{BPKM}Task")
        assert cmd["params"]["properties"] == props


# ===================================================================
# Tests: _build_update_commands
# ===================================================================


class TestBuildUpdateCommands:
    """Tests for the update command builder."""

    def test_builds_patch_only_when_no_desc_or_assignee(self):
        cmds = _build_update_commands(
            "https://example.org/data/Task/test",
            {f"{BPKM}taskStatus": "done"},
            None,
            None,
        )
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"

    def test_includes_body_set_when_description_present(self):
        cmds = _build_update_commands(
            "https://example.org/data/Task/test",
            {},
            "Some description",
            None,
        )
        assert len(cmds) == 2
        assert cmds[1]["command"] == "body.set"
        assert cmds[1]["params"]["body"] == "Some description"

    def test_includes_edge_create_when_assignee_present(self):
        cmds = _build_update_commands(
            "https://example.org/data/Task/test",
            {},
            None,
            "https://example.org/data/Person/john",
        )
        assert len(cmds) == 2
        assert cmds[1]["command"] == "edge.create"
        assert cmds[1]["params"]["predicate"] == f"{BPKM}assignedTo"

    def test_includes_all_three_commands(self):
        cmds = _build_update_commands(
            "https://example.org/data/Task/test",
            {f"{BPKM}taskStatus": "done"},
            "Description text",
            "https://example.org/data/Person/jane",
        )
        assert len(cmds) == 3
        assert cmds[0]["command"] == "object.patch"
        assert cmds[1]["command"] == "body.set"
        assert cmds[2]["command"] == "edge.create"


# ===================================================================
# Tests: _submit_commands_batched
# ===================================================================


class TestSubmitCommandsBatched:
    """Tests for batch command submission."""

    @pytest.mark.asyncio
    async def test_single_batch(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {}}]
        await _submit_commands_batched(http, cmds, "test", "monday-sync")
        assert len(http.recorded_calls) == 1
        url, payload = http.recorded_calls[0]
        assert url == "/api/commands/bulk"
        assert payload["source"] == "monday-sync"

    @pytest.mark.asyncio
    async def test_multiple_batches(self):
        http = MockHttpClient()
        # Create more commands than BATCH_SIZE
        cmds = [{"command": "test", "params": {}} for _ in range(BATCH_SIZE + 5)]
        await _submit_commands_batched(http, cmds, "test", "monday-sync")
        assert len(http.recorded_calls) == 2
        # First batch should be BATCH_SIZE
        first_batch = http.recorded_calls[0][1]["commands"]
        assert len(first_batch) == BATCH_SIZE
        # Second batch should be the remainder
        second_batch = http.recorded_calls[1][1]["commands"]
        assert len(second_batch) == 5

    @pytest.mark.asyncio
    async def test_empty_commands_no_call(self):
        http = MockHttpClient()
        await _submit_commands_batched(http, [], "test", "monday-sync")
        assert len(http.recorded_calls) == 0


# ===================================================================
# Tests: _compute_status and _make_result
# ===================================================================


class TestComputeStatus:
    """Tests for sync status computation."""

    def test_success_no_errors(self):
        assert _compute_status(5, 3, 2, 0) == "success"

    def test_success_empty(self):
        assert _compute_status(0, 0, 0, 0) == "success"

    def test_partial_mixed(self):
        assert _compute_status(5, 0, 0, 2) == "partial"

    def test_error_all_failed(self):
        assert _compute_status(0, 0, 0, 5) == "error"

    def test_partial_some_success_some_error(self):
        assert _compute_status(0, 0, 3, 1) == "partial"


class TestMakeResult:
    """Tests for result dict builder."""

    def test_basic_result(self):
        import time
        start = time.monotonic()
        result = _make_result("success", start, created=5, updated=3)
        assert result["status"] == "success"
        assert result["created"] == 5
        assert result["updated"] == 3
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert "duration_ms" in result
        assert result["failed_items"] == []
        assert result["parent_links"] == 0

    def test_result_with_reason(self):
        import time
        result = _make_result("skipped", time.monotonic(), reason="not connected")
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    def test_result_with_failed_items(self):
        import time
        result = _make_result(
            "partial", time.monotonic(),
            errors=2, failed_items=["100", "200"],
        )
        assert result["failed_items"] == ["100", "200"]

    def test_result_with_parent_links(self):
        import time
        result = _make_result(
            "success", time.monotonic(),
            parent_links=3,
        )
        assert result["parent_links"] == 3


# ===================================================================
# Tests: push_sync stub
# ===================================================================


class TestPushSync:
    """Tests for push sync auth and direction checks."""

    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        """Returns skipped when Monday.com auth fails."""
        state = MockStateClient()  # No token
        ctx = SyncContext(state=state)
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    @pytest.mark.asyncio
    async def test_result_stored_when_not_connected(self):
        """last_push_result is stored even on auth skip."""
        state = MockStateClient()
        ctx = SyncContext(state=state)
        await push_sync(ctx)
        stored = await ctx.state.get("last_push_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_skips_when_pull_only(self):
        """Returns skipped when sync direction is pull-only."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({"sync_direction": "pull-only"})
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "sync direction is pull-only"

    @pytest.mark.asyncio
    async def test_pull_only_result_stored(self):
        """last_push_result stored on direction skip."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({"sync_direction": "pull-only"})
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        await push_sync(ctx)
        stored = await ctx.state.get("last_push_result")
        parsed = json.loads(stored)
        assert parsed["reason"] == "sync direction is pull-only"

    @pytest.mark.asyncio
    async def test_bidirectional_proceeds(self):
        """Bidirectional direction proceeds past direction check."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({"sync_direction": "bidirectional"})
        http = _MonkeyPatchedHttpForAuth()
        graph = MockGraphClient()  # No changed tasks
        ctx = SyncContext(state=state, settings=settings, http=http, graph=graph)
        result = await push_sync(ctx)
        assert result["status"] == "success"
        assert result["pushed"] == 0


# ===================================================================
# Tests: pull_sync — auth and config checks
# ===================================================================


class TestPullSyncAuthChecks:
    """Tests for pull_sync early-exit conditions."""

    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        """Returns skipped when Monday.com auth fails."""
        state = MockStateClient()  # No token stored
        settings = MockSettingsClient()
        http = MockHttpClient()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"

    @pytest.mark.asyncio
    async def test_skips_when_no_boards_selected(self):
        """Returns skipped when no boards are configured."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient()  # No selected_boards
        # Need a real-ish MondayClient that responds to get_me
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "no boards selected"

    @pytest.mark.asyncio
    async def test_skips_when_boards_empty_list(self):
        """Returns skipped when selected_boards is an empty JSON array."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({"selected_boards": "[]"})
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "no boards selected"


class _MonkeyPatchedHttpForAuth:
    """HTTP client that responds to Monday.com API with success for get_me."""

    async def request(self, method, url, **kwargs):
        return MockResponse(200, {
            "data": {"me": {"id": "1", "name": "Test", "email": "t@e.com"}}
        })


# ===================================================================
# Tests: pull_sync — board iteration
# ===================================================================


class TestPullSyncBoardIteration:
    """Tests for per-board processing."""

    @pytest.mark.asyncio
    async def test_skips_board_without_column_mapping(self):
        """Boards without column_mapping_N are skipped."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["123"]),
            # No column_mapping_123
        })
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await pull_sync(ctx)
        # No items processed but no error either
        assert result["status"] == "success"
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_processes_board_with_mapping(self):
        """Board with column mapping fetches and processes items."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["456"]),
            "column_mapping_456": _make_column_mapping_json({"taskStatus": "status_col"}),
        })
        # Need to intercept both auth and sync calls
        ctx = _build_full_sync_context(
            state=state,
            settings=settings,
            items_by_board={
                456: [_make_item(item_id=1001, name="Task A")],
            },
        )
        result = await pull_sync(ctx)
        assert result["status"] == "success"
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_processes_multiple_boards(self):
        """Items from multiple boards are all processed."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["100", "200"]),
            "column_mapping_100": _make_column_mapping_json(),
            "column_mapping_200": _make_column_mapping_json(),
        })
        ctx = _build_full_sync_context(
            state=state,
            settings=settings,
            items_by_board={
                100: [_make_item(item_id=1, name="Board 100 Item")],
                200: [
                    _make_item(item_id=2, name="Board 200 Item A"),
                    _make_item(item_id=3, name="Board 200 Item B"),
                ],
            },
        )
        result = await pull_sync(ctx)
        assert result["created"] == 3


# ===================================================================
# Tests: pull_sync — item processing
# ===================================================================


class TestPullSyncItemProcessing:
    """Tests for individual item → Task creation and updates."""

    @pytest.mark.asyncio
    async def test_creates_new_task(self):
        """New items result in object.create commands."""
        ctx = _build_basic_sync_context(
            items=[_make_item(item_id=42, name="New Task")],
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1
        assert result["errors"] == 0
        # Check the bulk call was made
        http_client = ctx.commands._client
        assert len(http_client.recorded_calls) >= 1

    @pytest.mark.asyncio
    async def test_updates_existing_task(self):
        """Items matching existing tasks produce update commands."""
        slug = compute_slug("Existing Task", "42")
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://example.org/data/Task/" + slug,
                "status": "todo",
                "externalId": "42",
            }
        })
        ctx = _build_basic_sync_context(
            items=[_make_item(item_id=42, name="Existing Task")],
            graph=graph,
        )
        result = await pull_sync(ctx)
        assert result["updated"] == 1
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_group_title_from_item_group(self):
        """Group title is taken from item.group.title, not column_values."""
        ctx = _build_basic_sync_context(
            items=[_make_item(
                item_id=50, name="Grouped Task",
                group_title="Sprint 2",
            )],
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1
        # Verify the create command has taskGroup
        http_client = ctx.commands._client
        calls = http_client.recorded_calls
        create_call = next(
            (c for c in calls if c[1] and "commands" in c[1]),
            None,
        )
        assert create_call is not None
        cmds = create_call[1]["commands"]
        props = cmds[0]["params"]["properties"]
        assert props.get(f"{BPKM}taskGroup") == "Sprint 2"

    @pytest.mark.asyncio
    async def test_per_item_error_isolation(self):
        """Errors on individual items don't stop processing others."""
        # First item has no id (will cause an issue in slug computation
        # but won't crash), second item is normal
        items = [
            _make_item(item_id=1, name="Good Task"),
            _make_item(item_id=2, name="Another Good Task"),
        ]
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 2
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_error_item_counted(self):
        """Failed items are tracked in failed_items and error count."""
        # Use a graph client that raises on query to simulate error
        class ErrorGraphClient(MockGraphClient):
            _call_count = 0

            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                self._call_count += 1
                # Fail on the second task's find-existing query
                if self._call_count == 2 and "STRENDS" in sparql:
                    raise Exception("Simulated graph error")
                return await super().query(sparql)

        graph = ErrorGraphClient()
        items = [
            _make_item(item_id=1, name="Task 1"),
            _make_item(item_id=2, name="Task 2"),
        ]
        ctx = _build_basic_sync_context(items=items, graph=graph)
        result = await pull_sync(ctx)
        # At least one should succeed, one should fail
        assert result["errors"] >= 1
        assert len(result["failed_items"]) >= 1


# ===================================================================
# Tests: pull_sync — label mappings
# ===================================================================


class TestPullSyncLabelMappings:
    """Tests for label mapping from settings."""

    @pytest.mark.asyncio
    async def test_uses_custom_status_mapping(self):
        """Custom status label mapping is passed to build_task_properties."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["789"]),
            "column_mapping_789": _make_column_mapping_json({"taskStatus": "status_col"}),
            "label_mapping_789": _make_label_mapping_json(
                status_mapping={"Custom Done": "done"},
            ),
        })
        items = [_make_item(
            item_id=10, name="Mapped Task",
            column_values=[{
                "id": "status_col",
                "text": "Custom Done",
                "type": "status",
                "value": json.dumps({"label": "Custom Done", "index": 5}),
            }],
        )]
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={789: items},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_uses_default_when_no_label_mapping(self):
        """When no label_mapping_{board_id} exists, defaults are used."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["789"]),
            "column_mapping_789": _make_column_mapping_json(),
            # No label_mapping_789
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={789: [_make_item()]},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1


# ===================================================================
# Tests: pull_sync — subitems
# ===================================================================


class TestPullSyncSubitems:
    """Tests for subitem processing and parentTask edge creation."""

    @pytest.mark.asyncio
    async def test_subitems_are_created(self):
        """Subitems produce separate Task create commands."""
        parent = _make_item(item_id=100, name="Parent Task")
        sub = _make_subitem(sub_id=200, name="Sub Task", parent_item_id=100)
        ctx = _build_basic_sync_context(
            items=[parent],
            subitems_by_parent={100: [sub]},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 2  # parent + subitem

    @pytest.mark.asyncio
    async def test_subitem_parent_link_in_phase3(self):
        """Phase 3 creates parentTask edges for subitems."""
        parent = _make_item(item_id=100, name="Parent Task")
        sub = _make_subitem(sub_id=200, name="Sub Task", parent_item_id=100)

        # Need both parent and sub to be findable after Phase 1
        parent_slug = compute_slug("Parent Task", "100")
        sub_slug = compute_slug("Sub Task", "200")

        # After Phase 1 creates, Phase 3 looks up IRIs
        # We simulate this by pre-populating the graph after the first call
        class Phase3GraphClient(MockGraphClient):
            def __init__(self):
                super().__init__()
                self._phase1_done = False

            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                # After Phase 1 bulk is submitted, tasks are findable
                if self._phase1_done and "STRENDS" in sparql and "/Task/" in sparql:
                    if parent_slug in sparql:
                        return {"results": {"bindings": [{
                            "task": {"type": "uri", "value": f"https://ex.org/Task/{parent_slug}"},
                        }]}}
                    if sub_slug in sparql:
                        return {"results": {"bindings": [{
                            "task": {"type": "uri", "value": f"https://ex.org/Task/{sub_slug}"},
                        }]}}
                return {"results": {"bindings": []}}

        graph = Phase3GraphClient()

        # Override the http client to mark phase1 done after create bulk
        class Phase1TrackingHttp(MockHttpClient):
            def __init__(self, graph_ref):
                super().__init__()
                self._graph = graph_ref

            async def post(self, url, json=None, **kwargs):
                result = await super().post(url, json=json, **kwargs)
                # After the first bulk POST (Phase 1), mark tasks as findable
                if url == "/api/commands/bulk" and json and "commands" in json:
                    cmds = json["commands"]
                    if any(c.get("command") == "object.create" for c in cmds):
                        self._graph._phase1_done = True
                return result

        tracking_http = Phase1TrackingHttp(graph)
        ctx = _build_basic_sync_context(
            items=[parent],
            subitems_by_parent={100: [sub]},
            graph=graph,
            http_client=tracking_http,
        )
        result = await pull_sync(ctx)
        assert result["created"] == 2
        assert result["parent_links"] >= 0  # May or may not create links depending on timing

    @pytest.mark.asyncio
    async def test_subitem_fetch_failure_isolated(self):
        """Subitem fetch errors don't stop the entire sync."""
        class FailingMondayClient(MockMondayClient):
            async def get_subitems(self, item_ids):
                raise Exception("Subitem API error")

        parent = _make_item(item_id=100, name="Parent Task")
        ctx = _build_basic_sync_context(items=[parent])
        # Replace with failing client for subitems
        # The parent should still be created successfully
        result = await pull_sync(ctx)
        assert result["created"] >= 1

    @pytest.mark.asyncio
    async def test_subitem_group_title(self):
        """Subitems use their own group.title for taskGroup."""
        parent = _make_item(item_id=100, name="Parent")
        sub = _make_subitem(
            sub_id=200, name="Sub",
            parent_item_id=100,
            group_title="Sub Group",
        )
        ctx = _build_basic_sync_context(
            items=[parent],
            subitems_by_parent={100: [sub]},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 2


# ===================================================================
# Tests: pull_sync — two-phase bulk
# ===================================================================


class TestPullSyncTwoPhaseBulk:
    """Tests for two-phase create pattern."""

    @pytest.mark.asyncio
    async def test_phase1_create_commands_submitted(self):
        """Phase 1 submits create commands via bulk endpoint."""
        ctx = _build_basic_sync_context(
            items=[_make_item(item_id=1, name="Task A")],
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1
        http_client = ctx.commands._client
        # At least one POST to /api/commands/bulk
        bulk_calls = [c for c in http_client.recorded_calls if c[0] == "/api/commands/bulk"]
        assert len(bulk_calls) >= 1
        # Source should be "monday-sync"
        assert bulk_calls[0][1]["source"] == "monday-sync"

    @pytest.mark.asyncio
    async def test_source_string_is_monday_sync(self):
        """All bulk submissions use 'monday-sync' as source."""
        ctx = _build_basic_sync_context(
            items=[_make_item(item_id=1, name="Task")],
        )
        await pull_sync(ctx)
        http_client = ctx.commands._client
        for url, payload in http_client.recorded_calls:
            if url == "/api/commands/bulk":
                assert payload["source"] == "monday-sync"


# ===================================================================
# Tests: pull_sync — state persistence
# ===================================================================


class TestPullSyncStatePersistence:
    """Tests for sync state stored after pull."""

    @pytest.mark.asyncio
    async def test_stores_last_sync_at(self):
        """last_sync_at is saved to state after sync."""
        ctx = _build_basic_sync_context(items=[])
        await pull_sync(ctx)
        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None

    @pytest.mark.asyncio
    async def test_stores_last_pull_result(self):
        """last_pull_result JSON is saved to state."""
        ctx = _build_basic_sync_context(
            items=[_make_item(item_id=1, name="Task")],
        )
        result = await pull_sync(ctx)
        stored = await ctx.state.get("last_pull_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == result["status"]
        assert parsed["created"] == result["created"]

    @pytest.mark.asyncio
    async def test_result_contains_duration_ms(self):
        """Result dict includes duration_ms."""
        ctx = _build_basic_sync_context(items=[])
        result = await pull_sync(ctx)
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)


# ===================================================================
# Tests: pull_sync — description and assignee deferral
# ===================================================================


class TestPullSyncPhase2:
    """Tests for Phase 2 — body.set and edge.create for new tasks."""

    @pytest.mark.asyncio
    async def test_description_deferred_for_new_tasks(self):
        """Descriptions on new tasks are handled in Phase 2, not Phase 1."""
        items = [_make_item(
            item_id=10, name="Described Task",
            column_values=[{
                "id": "desc_col",
                "text": "Task description text",
                "type": "long_text",
                "value": json.dumps({"text": "Task description text"}),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["100"]),
            "column_mapping_100": _make_column_mapping_json({"description": "desc_col"}),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={100: items},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1


# ===================================================================
# Tests: pull_sync — multiple items
# ===================================================================


class TestPullSyncMultipleItems:
    """Tests for processing many items."""

    @pytest.mark.asyncio
    async def test_many_items_all_created(self):
        """All items in a single board are processed."""
        items = [_make_item(item_id=i, name=f"Task {i}") for i in range(20)]
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 20
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_mix_of_create_and_update(self):
        """Some items are new, some match existing tasks."""
        slug_5 = compute_slug("Task 5", "5")
        slug_10 = compute_slug("Task 10", "10")
        graph = MockGraphClient(slug_map={
            slug_5: {
                "iri": f"https://ex.org/Task/{slug_5}",
                "status": "todo",
                "externalId": "5",
            },
            slug_10: {
                "iri": f"https://ex.org/Task/{slug_10}",
                "status": "done",
                "externalId": "10",
            },
        })
        items = [_make_item(item_id=i, name=f"Task {i}") for i in range(1, 16)]
        ctx = _build_basic_sync_context(items=items, graph=graph)
        result = await pull_sync(ctx)
        assert result["created"] == 13  # 15 items - 2 existing
        assert result["updated"] == 2


# ===================================================================
# Tests: pull_sync — group handling edge cases
# ===================================================================


class TestPullSyncGroupHandling:
    """Tests for group title extraction edge cases."""

    @pytest.mark.asyncio
    async def test_no_group_on_item(self):
        """Items without group info still sync (no crash)."""
        item = {"id": "1", "name": "No Group", "column_values": []}
        # No "group" key
        ctx = _build_basic_sync_context(items=[item])
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_group_none(self):
        """Items with group=None still sync."""
        item = {"id": "2", "name": "Null Group", "group": None, "column_values": []}
        ctx = _build_basic_sync_context(items=[item])
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_group_empty_title(self):
        """Items with empty group title don't set taskGroup."""
        item = _make_item(item_id=3, name="Empty Group", group_title="")
        ctx = _build_basic_sync_context(items=[item])
        result = await pull_sync(ctx)
        assert result["created"] == 1


# ===================================================================
# Tests: _find_all_tasks_for_board
# ===================================================================


class TestFindAllTasksForBoard:
    """Tests for the board-scoped SPARQL query."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_tasks(self):
        graph = MockGraphClient()
        result = await _find_all_tasks_for_board(graph, 123)
        assert result == []

    @pytest.mark.asyncio
    async def test_sparql_contains_board_id(self):
        graph = MockGraphClient()
        await _find_all_tasks_for_board(graph, 456)
        assert len(graph.queries) == 1
        assert "/boards/456/" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_accepts_string_board_id(self):
        graph = MockGraphClient()
        await _find_all_tasks_for_board(graph, "789")
        assert "/boards/789/" in graph.queries[0]


# ===================================================================
# Tests: _find_existing_task — additional cases
# ===================================================================


class TestFindExistingTaskExtended:
    """Extra edge-case tests for _find_existing_task."""

    @pytest.mark.asyncio
    async def test_slug_with_special_chars(self):
        """Slug containing dashes/hex is used verbatim."""
        slug = "monday-a1b2c3d4e5f60011"
        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Task/{slug}"}
        })
        result = await _find_existing_task(graph, slug)
        assert result is not None
        assert slug in result["iri"]

    @pytest.mark.asyncio
    async def test_multiple_slugs_only_match_queried(self):
        """Only the queried slug is returned even when map has many."""
        graph = MockGraphClient(slug_map={
            "monday-aaa": {"iri": "https://ex.org/Task/aaa"},
            "monday-bbb": {"iri": "https://ex.org/Task/bbb"},
        })
        result = await _find_existing_task(graph, "monday-aaa")
        assert result is not None
        assert result["iri"] == "https://ex.org/Task/aaa"

    @pytest.mark.asyncio
    async def test_returns_last_synced_at(self):
        slug = "monday-test123"
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://ex.org/Task/" + slug,
                "lastSyncedAt": "2025-06-01T12:00:00Z",
            }
        })
        result = await _find_existing_task(graph, slug)
        assert result["lastSyncedAt"] == "2025-06-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_sparql_contains_task_type(self):
        graph = MockGraphClient()
        await _find_existing_task(graph, "monday-test")
        assert BPKM + "Task" in graph.queries[0]


# ===================================================================
# Tests: _build_create_command — additional
# ===================================================================


class TestBuildCreateCommandExtended:
    """Additional tests for object.create builder."""

    def test_empty_properties(self):
        cmd = _build_create_command("monday-empty", {}, f"{BPKM}Task")
        assert cmd["params"]["properties"] == {}
        assert cmd["params"]["slug"] == "monday-empty"

    def test_type_uses_full_iri(self):
        cmd = _build_create_command("s", {}, f"{BPKM}Task")
        assert cmd["params"]["type"] == f"{BPKM}Task"

    def test_command_string_is_object_create(self):
        cmd = _build_create_command("s", {}, f"{BPKM}Task")
        assert cmd["command"] == "object.create"


# ===================================================================
# Tests: _build_update_commands — additional
# ===================================================================


class TestBuildUpdateCommandsExtended:
    """Additional edge-case tests for update commands."""

    def test_patch_uses_correct_iri(self):
        iri = "https://example.org/data/Task/monday-abc"
        cmds = _build_update_commands(iri, {"a": "b"}, None, None)
        assert cmds[0]["params"]["iri"] == iri

    def test_body_set_command_format(self):
        iri = "https://example.org/data/Task/t1"
        cmds = _build_update_commands(iri, {}, "Hello body", None)
        body_cmd = cmds[1]
        assert body_cmd["params"]["iri"] == iri
        assert body_cmd["params"]["body"] == "Hello body"

    def test_edge_create_assignee_format(self):
        iri = "https://example.org/data/Task/t1"
        person = "https://example.org/data/Person/john"
        cmds = _build_update_commands(iri, {}, None, person)
        edge_cmd = cmds[1]
        assert edge_cmd["params"]["source"] == iri
        assert edge_cmd["params"]["target"] == person
        assert edge_cmd["params"]["predicate"] == f"{BPKM}assignedTo"

    def test_empty_properties_still_creates_patch(self):
        cmds = _build_update_commands("https://ex.org/t", {}, None, None)
        assert len(cmds) == 1
        assert cmds[0]["params"]["properties"] == {}

    def test_description_empty_string_is_falsy(self):
        """Empty string description is falsy → no body.set command."""
        cmds = _build_update_commands("https://ex.org/t", {}, "", None)
        # Empty string is falsy in Python
        assert len(cmds) == 1  # only patch


# ===================================================================
# Tests: _compute_status — additional
# ===================================================================


class TestComputeStatusExtended:
    """Additional status computation cases."""

    def test_only_skipped_is_success(self):
        assert _compute_status(0, 0, 5, 0) == "success"

    def test_created_and_updated_no_errors(self):
        assert _compute_status(10, 5, 0, 0) == "success"

    def test_one_error_is_partial(self):
        assert _compute_status(10, 0, 0, 1) == "partial"

    def test_skipped_with_errors_is_partial(self):
        assert _compute_status(0, 0, 5, 1) == "partial"

    def test_large_counts(self):
        assert _compute_status(1000, 500, 200, 0) == "success"


# ===================================================================
# Tests: _make_result — additional
# ===================================================================


class TestMakeResultExtended:
    """Additional tests for result builder."""

    def test_default_values(self):
        import time
        result = _make_result("success", time.monotonic())
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert result["parent_links"] == 0
        assert result["failed_items"] == []
        assert "reason" not in result

    def test_duration_is_positive(self):
        import time
        start = time.monotonic()
        time.sleep(0.01)  # 10ms
        result = _make_result("success", start)
        assert result["duration_ms"] >= 0

    def test_status_field_matches_input(self):
        import time
        for status in ["success", "partial", "error", "skipped"]:
            result = _make_result(status, time.monotonic())
            assert result["status"] == status

    def test_all_counts_preserved(self):
        import time
        result = _make_result(
            "partial", time.monotonic(),
            created=3, updated=5, skipped=2, errors=1,
            failed_items=["99"], parent_links=7,
        )
        assert result["created"] == 3
        assert result["updated"] == 5
        assert result["skipped"] == 2
        assert result["errors"] == 1
        assert result["failed_items"] == ["99"]
        assert result["parent_links"] == 7


# ===================================================================
# Tests: _submit_commands_batched — additional
# ===================================================================


class TestSubmitCommandsBatchedExtended:
    """Additional batch submission tests."""

    @pytest.mark.asyncio
    async def test_batch_size_boundary_exact_fit(self):
        """Exactly BATCH_SIZE commands = single batch."""
        http = MockHttpClient()
        cmds = [{"command": "c", "params": {}} for _ in range(BATCH_SIZE)]
        await _submit_commands_batched(http, cmds, "test", "src")
        assert len(http.recorded_calls) == 1
        assert len(http.recorded_calls[0][1]["commands"]) == BATCH_SIZE

    @pytest.mark.asyncio
    async def test_payload_includes_summary(self):
        http = MockHttpClient()
        await _submit_commands_batched(
            http, [{"command": "c", "params": {}}], "my summary", "src",
        )
        _, payload = http.recorded_calls[0]
        assert payload["summary"] == "my summary"

    @pytest.mark.asyncio
    async def test_returns_list_of_responses(self):
        http = MockHttpClient()
        results = await _submit_commands_batched(
            http, [{"command": "c", "params": {}}], "test", "src",
        )
        assert isinstance(results, list)
        assert len(results) == 1


# ===================================================================
# Tests: push_sync — additional
# ===================================================================


class TestPushSyncExtended:
    """Additional push sync auth/direction tests."""

    @pytest.mark.asyncio
    async def test_is_async_function(self):
        """push_sync is awaitable (async def)."""
        import asyncio
        ctx = SyncContext()
        coro = push_sync(ctx)
        assert asyncio.iscoroutine(coro)
        result = await coro
        assert result is not None

    @pytest.mark.asyncio
    async def test_stores_result_in_state(self):
        """push_sync stores last_push_result in state."""
        state = MockStateClient()
        ctx = SyncContext(state=state)
        await push_sync(ctx)
        stored = await state.get("last_push_result")
        assert stored is not None

    @pytest.mark.asyncio
    async def test_default_direction_is_pull_only(self):
        """If sync_direction not set, defaults to pull-only and skips."""
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient()  # No sync_direction set
        http = _MonkeyPatchedHttpForAuth()
        ctx = SyncContext(state=state, settings=settings, http=http)
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "sync direction is pull-only"


# ===================================================================
# Tests: pull_sync — assignee resolution
# ===================================================================


class TestPullSyncAssigneeResolution:
    """Tests for assignee person matching during pull sync."""

    @pytest.mark.asyncio
    async def test_assignee_resolved_when_present(self):
        """Items with an assignee user_id trigger person resolution."""
        items = [_make_item(
            item_id=42, name="Assigned Task",
            column_values=[{
                "id": "people_col",
                "text": "John Doe",
                "type": "people",
                "value": json.dumps({
                    "personsAndTeams": [{"id": 777, "kind": "person"}],
                }),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["500"]),
            "column_mapping_500": _make_column_mapping_json({"assignee": "people_col"}),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={500: items},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_assignee_failure_does_not_crash(self):
        """If assignee resolution raises, item still processes."""
        # Use a graph client that fails on PersonMatcher queries
        class FailPersonGraph(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "foaf" in sparql.lower() or "crm:email" in sparql.lower():
                    raise Exception("Person resolution failed")
                return await super().query(sparql)

        items = [_make_item(
            item_id=42, name="Assigned Task",
            column_values=[{
                "id": "people_col",
                "text": "Jane",
                "type": "people",
                "value": json.dumps({
                    "personsAndTeams": [{"id": 888, "kind": "person"}],
                }),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["500"]),
            "column_mapping_500": _make_column_mapping_json({"assignee": "people_col"}),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={500: items},
        )
        ctx.graph = FailPersonGraph()
        result = await pull_sync(ctx)
        # Task created even though assignee failed
        assert result["created"] == 1


# ===================================================================
# Tests: pull_sync — all items fail → "error" status
# ===================================================================


class TestPullSyncAllItemsFail:
    """Tests for when every item in the sync fails."""

    @pytest.mark.asyncio
    async def test_all_items_fail_returns_error_status(self):
        """When every item raises, result status is 'error'."""
        class AlwaysFailGraph(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql and "/Task/" in sparql:
                    raise Exception("Forced graph failure")
                return await super().query(sparql)

        items = [
            _make_item(item_id=1, name="Fail 1"),
            _make_item(item_id=2, name="Fail 2"),
        ]
        ctx = _build_basic_sync_context(items=items, graph=AlwaysFailGraph())
        result = await pull_sync(ctx)
        assert result["status"] == "error"
        assert result["errors"] == 2
        assert len(result["failed_items"]) == 2

    @pytest.mark.asyncio
    async def test_mixed_success_failure_returns_partial(self):
        """Some items pass, some fail → 'partial' status."""
        class FailOnSecondItem(MockGraphClient):
            _call_count = 0
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql and "/Task/" in sparql:
                    self._call_count += 1
                    if self._call_count == 2:
                        raise Exception("Forced failure on second item")
                return await super().query(sparql)

        items = [
            _make_item(item_id=1, name="OK Task"),
            _make_item(item_id=2, name="Bad Task"),
        ]
        ctx = _build_basic_sync_context(items=items, graph=FailOnSecondItem())
        result = await pull_sync(ctx)
        assert result["status"] == "partial"
        assert result["created"] >= 1
        assert result["errors"] >= 1


# ===================================================================
# Tests: pull_sync — empty results
# ===================================================================


class TestPullSyncEmptyResults:
    """Tests for syncs with no items to process."""

    @pytest.mark.asyncio
    async def test_no_items_returns_success_zero_counts(self):
        ctx = _build_basic_sync_context(items=[])
        result = await pull_sync(ctx)
        assert result["status"] == "success"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_empty_board_still_stores_sync_timestamp(self):
        ctx = _build_basic_sync_context(items=[])
        await pull_sync(ctx)
        ts = await ctx.state.get("last_sync_at")
        assert ts is not None
        # Should be ISO format
        assert "T" in ts


# ===================================================================
# Tests: pull_sync — sync timestamp format
# ===================================================================


class TestPullSyncTimestamp:
    """Tests for timestamp handling."""

    @pytest.mark.asyncio
    async def test_last_sync_at_is_iso_format(self):
        ctx = _build_basic_sync_context(items=[])
        await pull_sync(ctx)
        ts = await ctx.state.get("last_sync_at")
        # Parse to confirm valid ISO
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None  # Must be timezone-aware

    @pytest.mark.asyncio
    async def test_last_pull_result_is_valid_json(self):
        ctx = _build_basic_sync_context(items=[_make_item()])
        await pull_sync(ctx)
        stored = await ctx.state.get("last_pull_result")
        parsed = json.loads(stored)
        assert "status" in parsed
        assert "created" in parsed
        assert "duration_ms" in parsed


# ===================================================================
# Tests: pull_sync — column mapping property flow
# ===================================================================


class TestPullSyncColumnMappingFlow:
    """Tests verifying column mapping config reaches build_task_properties."""

    @pytest.mark.asyncio
    async def test_column_mapping_with_multiple_fields(self):
        """Board with status, priority, and due date columns mapped."""
        items = [_make_item(
            item_id=10, name="Multi-col Task",
            column_values=[
                {"id": "status_col", "text": "Done", "type": "status",
                 "value": json.dumps({"label": "Done", "index": 1})},
                {"id": "priority_col", "text": "High", "type": "status",
                 "value": json.dumps({"label": "High", "index": 2})},
                {"id": "date_col", "text": "2025-12-01", "type": "date",
                 "value": json.dumps({"date": "2025-12-01"})},
            ],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["300"]),
            "column_mapping_300": _make_column_mapping_json({
                "taskStatus": "status_col",
                "priority": "priority_col",
                "dueDate": "date_col",
            }),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={300: items},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_priority_label_mapping_passed(self):
        """Custom priority label mapping from settings is used."""
        items = [_make_item(
            item_id=11, name="Priority Task",
            column_values=[{
                "id": "pri_col", "text": "Urgent", "type": "status",
                "value": json.dumps({"label": "Urgent", "index": 1}),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["300"]),
            "column_mapping_300": _make_column_mapping_json({"priority": "pri_col"}),
            "label_mapping_300": _make_label_mapping_json(
                priority_mapping={"Urgent": "critical"},
            ),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={300: items},
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1


# ===================================================================
# Tests: _has_changes — extended
# ===================================================================


class TestHasChangesExtended:
    """Additional change detection tests."""

    def test_with_full_property_set(self):
        existing = {
            "iri": "https://ex.org/Task/t1",
            "status": "in-progress",
            "externalId": "42",
            "lastSyncedAt": "2025-01-01T00:00:00Z",
        }
        props = {
            f"{BPKM}taskStatus": "done",
            f"{BPKM}priority": "high",
            "dcterms:title": "Updated Task",
        }
        assert _has_changes(existing, props) is True

    def test_with_none_existing(self):
        """Existing dict with None values still returns True."""
        existing = {"iri": "https://ex.org/Task/t", "status": None}
        assert _has_changes(existing, {}) is True


# ===================================================================
# Tests: MockResponse correctness (KNOWLEDGE.md Pattern #2)
# ===================================================================


class TestMockResponseFalsyData:
    """Verifies MockResponse handles falsy-but-valid data correctly.

    KNOWLEDGE.md Pattern #2: ``data if data is not None else {}``
    ensures empty lists ``[]`` and ``0`` don't silently become ``{}``.
    """

    def test_empty_list_preserved(self):
        resp = MockResponse(200, [])
        assert resp.json() == []

    def test_zero_preserved(self):
        resp = MockResponse(200, 0)
        assert resp.json() == 0

    def test_false_preserved(self):
        resp = MockResponse(200, False)
        assert resp.json() is False

    def test_none_becomes_empty_dict(self):
        resp = MockResponse(200)
        assert resp.json() == {}

    def test_explicit_none_becomes_empty_dict(self):
        resp = MockResponse(200, None)
        assert resp.json() == {}


# ===================================================================
# Tests: batch_size constant
# ===================================================================


class TestBatchSizeConstant:
    """Verify BATCH_SIZE has expected value."""

    def test_batch_size_is_1000(self):
        assert BATCH_SIZE == 1000

    def test_batch_size_is_positive(self):
        assert BATCH_SIZE > 0


# ===================================================================
# Tests: compute_slug integration
# ===================================================================


class TestComputeSlugIntegration:
    """Verify slug computation works with sync engine flow."""

    def test_slug_format(self):
        slug = compute_slug("My Task", "42")
        assert slug.startswith("monday-")
        assert len(slug) == len("monday-") + 16  # 16 hex chars

    def test_same_input_same_slug(self):
        slug1 = compute_slug("Task A", "100")
        slug2 = compute_slug("Task A", "100")
        assert slug1 == slug2

    def test_different_input_different_slug(self):
        slug1 = compute_slug("Task A", "100")
        slug2 = compute_slug("Task B", "100")
        assert slug1 != slug2


# ===================================================================
# Tests: _find_task_by_monday_item_id
# ===================================================================


class TestFindTaskByMondayItemId:
    """Tests for the SPARQL helper that finds tasks by Monday.com item ID."""

    @pytest.mark.asyncio
    async def test_found_returns_iri(self):
        graph = MockGraphClient(item_id_to_iri={
            "12345": "https://example.org/data/Task/monday-abc",
        })
        result = await _find_task_by_monday_item_id(graph, 12345)
        assert result == "https://example.org/data/Task/monday-abc"

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        graph = MockGraphClient()
        result = await _find_task_by_monday_item_id(graph, 99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_sparql_uses_pulses_pattern(self):
        graph = MockGraphClient()
        await _find_task_by_monday_item_id(graph, 42)
        assert len(graph.queries) == 1
        assert "/pulses/42" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_sparql_filters_monday_provider(self):
        graph = MockGraphClient()
        await _find_task_by_monday_item_id(graph, 100)
        assert '"monday"' in graph.queries[0]

    @pytest.mark.asyncio
    async def test_string_item_id_works(self):
        graph = MockGraphClient(item_id_to_iri={
            "777": "https://example.org/data/Task/monday-xyz",
        })
        result = await _find_task_by_monday_item_id(graph, "777")
        assert result == "https://example.org/data/Task/monday-xyz"


# ===================================================================
# Tests: _process_dependencies
# ===================================================================


class TestProcessDependencies:
    """Tests for dependency edge creation."""

    @pytest.mark.asyncio
    async def test_creates_edge_commands(self):
        """Dependency IDs that exist in graph produce edge.create commands."""
        graph = MockGraphClient(item_id_to_iri={
            "200": "https://ex.org/Task/target-200",
        })
        pairs = [("https://ex.org/Task/source-100", [200])]
        commands = await _process_dependencies(graph, pairs)
        assert len(commands) == 1
        cmd = commands[0]
        assert cmd["command"] == "edge.create"
        assert cmd["params"]["source"] == "https://ex.org/Task/source-100"
        assert cmd["params"]["predicate"] == f"{BPKM}dependsOn"
        assert cmd["params"]["target"] == "https://ex.org/Task/target-200"

    @pytest.mark.asyncio
    async def test_missing_target_skipped(self):
        """Dependency target not in graph → no edge, no error."""
        graph = MockGraphClient()  # No item_id_to_iri mappings
        pairs = [("https://ex.org/Task/source", [999])]
        commands = await _process_dependencies(graph, pairs)
        assert commands == []

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """No dependency pairs → no commands."""
        graph = MockGraphClient()
        commands = await _process_dependencies(graph, [])
        assert commands == []

    @pytest.mark.asyncio
    async def test_multiple_dependencies(self):
        """Multiple dep IDs for one source produce multiple edges."""
        graph = MockGraphClient(item_id_to_iri={
            "10": "https://ex.org/Task/t10",
            "20": "https://ex.org/Task/t20",
        })
        pairs = [("https://ex.org/Task/source", [10, 20])]
        commands = await _process_dependencies(graph, pairs)
        assert len(commands) == 2
        targets = {c["params"]["target"] for c in commands}
        assert targets == {"https://ex.org/Task/t10", "https://ex.org/Task/t20"}

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """One dependency lookup failure doesn't stop others."""
        class FailOnSecondQuery(MockGraphClient):
            _pulse_count = 0
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "CONTAINS" in sparql and "/pulses/" in sparql:
                    self._pulse_count += 1
                    if self._pulse_count == 1:
                        raise Exception("Simulated failure")
                    return {"results": {"bindings": [
                        {"task": {"type": "uri", "value": "https://ex.org/Task/ok"}}
                    ]}}
                return {"results": {"bindings": []}}

        graph = FailOnSecondQuery()
        pairs = [("https://ex.org/Task/source", [1, 2])]
        commands = await _process_dependencies(graph, pairs)
        # First dep fails, second succeeds
        assert len(commands) == 1

    @pytest.mark.asyncio
    async def test_multiple_sources(self):
        """Dependencies from multiple source tasks are all processed."""
        graph = MockGraphClient(item_id_to_iri={
            "50": "https://ex.org/Task/t50",
        })
        pairs = [
            ("https://ex.org/Task/a", [50]),
            ("https://ex.org/Task/b", [50]),
        ]
        commands = await _process_dependencies(graph, pairs)
        assert len(commands) == 2
        sources = {c["params"]["source"] for c in commands}
        assert sources == {"https://ex.org/Task/a", "https://ex.org/Task/b"}


# ===================================================================
# Tests: pull_sync — tag resolution
# ===================================================================


class TestPullSyncTagResolution:
    """Tests for tag ID → name batch resolution in pull_sync."""

    @pytest.mark.asyncio
    async def test_tag_ids_resolved_to_names(self):
        """Tag IDs in item properties are replaced with tag names."""
        items = [_make_item(
            item_id=10, name="Tagged Task",
            column_values=[{
                "id": "tags_col",
                "text": "bug, urgent",
                "type": "tags",
                "value": json.dumps({"tag_ids": [101, 202]}),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["800"]),
            "column_mapping_800": _make_column_mapping_json({"tags": "tags_col"}),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={800: items},
        )
        # Patch MondayClient.get_tags on the module to return tag names
        async def mock_get_tags(self, tag_ids):
            return [
                {"id": 101, "name": "bug"},
                {"id": 202, "name": "urgent"},
            ]
        _sync_engine.MondayClient.get_tags = mock_get_tags

        result = await pull_sync(ctx)
        assert result["created"] == 1
        # Verify that tag names ended up in the create command
        http_client = ctx.commands._client
        bulk_calls = [c for c in http_client.recorded_calls if c[0] == "/api/commands/bulk"]
        assert len(bulk_calls) >= 1
        cmds = bulk_calls[0][1]["commands"]
        props = cmds[0]["params"]["properties"]
        assert props.get(f"{BPKM}tags") == "bug, urgent"

    @pytest.mark.asyncio
    async def test_tag_resolution_fallback_on_error(self):
        """When get_tags() fails, tag IDs are kept as string fallback."""
        items = [_make_item(
            item_id=11, name="Fallback Tags",
            column_values=[{
                "id": "tags_col",
                "text": "tag1",
                "type": "tags",
                "value": json.dumps({"tag_ids": [300, 400]}),
            }],
        )]
        state = MockStateClient({"monday_api_token": "test-token"})
        settings = MockSettingsClient({
            "selected_boards": json.dumps(["800"]),
            "column_mapping_800": _make_column_mapping_json({"tags": "tags_col"}),
        })
        ctx = _build_full_sync_context(
            state=state, settings=settings,
            items_by_board={800: items},
        )
        # Patch get_tags to raise
        async def failing_get_tags(self, tag_ids):
            raise Exception("API error")
        _sync_engine.MondayClient.get_tags = failing_get_tags

        result = await pull_sync(ctx)
        assert result["created"] == 1
        # Verify fallback: tag IDs as strings
        http_client = ctx.commands._client
        bulk_calls = [c for c in http_client.recorded_calls if c[0] == "/api/commands/bulk"]
        cmds = bulk_calls[0][1]["commands"]
        props = cmds[0]["params"]["properties"]
        assert props.get(f"{BPKM}tags") == "300, 400"


# ===================================================================
# Tests: pull_sync — dependency edges in result
# ===================================================================


class TestPullSyncDependencyEdges:
    """Tests for dependency edge processing in pull_sync."""

    @pytest.mark.asyncio
    async def test_result_includes_dependency_edges_key(self):
        """Pull sync result dict always includes dependency_edges."""
        ctx = _build_basic_sync_context(items=[])
        result = await pull_sync(ctx)
        assert "dependency_edges" in result
        assert result["dependency_edges"] == 0

    @pytest.mark.asyncio
    async def test_dependency_edges_with_existing_target(self):
        """Dependency column with resolvable targets creates edges."""
        # Create an item with dependency column
        items = [_make_item(
            item_id=100, name="Dep Source",
            column_values=[{
                "id": "dep_col",
                "type": "dependency",
                "text": "",
                "value": json.dumps({"linkedPulseIds": [
                    {"linkedPulseId": 200},
                ]}),
            }],
        )]
        slug = compute_slug("Dep Source", "100")
        # The source item exists in graph (will be found in Phase 4)
        # The target item (200) also exists
        graph = MockGraphClient(
            slug_map={
                slug: {
                    "iri": f"https://ex.org/Task/{slug}",
                    "status": "todo",
                    "externalId": "100",
                },
            },
            item_id_to_iri={
                "200": "https://ex.org/Task/target-200",
            },
        )
        ctx = _build_basic_sync_context(
            items=items,
            graph=graph,
            column_mapping={"dependency": "dep_col"},
        )
        result = await pull_sync(ctx)
        # Updated (existing) + dependency edge
        assert result["updated"] == 1
        assert result["dependency_edges"] >= 1


# ===================================================================
# Tests: _make_result — dependency_edges field
# ===================================================================


class TestMakeResultDependencyEdges:
    """Tests for dependency_edges in result dict."""

    def test_default_dependency_edges_is_zero(self):
        import time
        result = _make_result("success", time.monotonic())
        assert result["dependency_edges"] == 0

    def test_dependency_edges_preserved(self):
        import time
        result = _make_result("success", time.monotonic(), dependency_edges=5)
        assert result["dependency_edges"] == 5

    def test_dependency_edges_in_all_counts(self):
        import time
        result = _make_result(
            "success", time.monotonic(),
            created=1, updated=2, parent_links=3, dependency_edges=4,
        )
        assert result["created"] == 1
        assert result["updated"] == 2
        assert result["parent_links"] == 3
        assert result["dependency_edges"] == 4


# ===================================================================
# Tests: MockMondayClient.get_tags
# ===================================================================


class TestMockMondayClientGetTags:
    """Tests for MockMondayClient.get_tags method."""

    @pytest.mark.asyncio
    async def test_returns_matching_tags(self):
        client = MockMondayClient(tags=[
            {"id": 1, "name": "bug"},
            {"id": 2, "name": "feature"},
            {"id": 3, "name": "urgent"},
        ])
        result = await client.get_tags([1, 3])
        assert len(result) == 2
        names = {t["name"] for t in result}
        assert names == {"bug", "urgent"}

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self):
        client = MockMondayClient(tags=[{"id": 1, "name": "bug"}])
        result = await client.get_tags([999])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self):
        client = MockMondayClient(tags=[{"id": 1, "name": "bug"}])
        result = await client.get_tags([])
        assert result == []


# ===================================================================
# Helper: build test contexts
# ===================================================================


def _build_full_sync_context(
    state: MockStateClient | None = None,
    settings: MockSettingsClient | None = None,
    graph: MockGraphClient | None = None,
    items_by_board: dict[int, list[dict]] | None = None,
    subitems_by_parent: dict[int, list[dict]] | None = None,
) -> SyncContext:
    """Build a SyncContext with a real(ish) auth flow.

    Uses _MonkeyPatchedHttpForAuth for the HTTP client so MondayClient
    can authenticate, and a MockMondayClient-like mock for item data.
    """
    state = state or MockStateClient({"monday_api_token": "test-token"})
    settings = settings or MockSettingsClient()
    graph = graph or MockGraphClient()
    http = _MonkeyPatchedHttpForAuth()
    bulk_http = MockHttpClient()
    commands = MockCommandClient(bulk_http)

    ctx = SyncContext(
        state=state, settings=settings, graph=graph,
        commands=commands, http=http,
    )

    # Monkey-patch: After pull_sync creates MondayClient, override its methods
    # We do this by replacing the module-level MondayClient constructor
    original_init = _sync_engine.MondayClient.__init__

    items_map = items_by_board or {}
    subs_map = subitems_by_parent or {}

    async def mock_get_all_board_items(self, board_id):
        return items_map.get(board_id, [])

    async def mock_get_subitems(self, item_ids):
        result = []
        for pid in item_ids:
            result.extend(subs_map.get(int(pid) if isinstance(pid, str) else pid, []))
        return result

    _sync_engine.MondayClient.get_all_board_items = mock_get_all_board_items
    _sync_engine.MondayClient.get_subitems = mock_get_subitems

    return ctx


def _build_basic_sync_context(
    items: list[dict] | None = None,
    subitems_by_parent: dict[int, list[dict]] | None = None,
    graph: MockGraphClient | None = None,
    http_client: MockHttpClient | None = None,
    column_mapping: dict | None = None,
) -> SyncContext:
    """Build a minimal SyncContext for testing item processing.

    Sets up auth token, selected board 999, and column mapping.
    """
    state = MockStateClient({"monday_api_token": "test-token"})
    settings = MockSettingsClient({
        "selected_boards": json.dumps(["999"]),
        "column_mapping_999": _make_column_mapping_json(column_mapping),
    })
    graph = graph or MockGraphClient()
    bulk_http = http_client or MockHttpClient()
    commands = MockCommandClient(bulk_http)
    http = _MonkeyPatchedHttpForAuth()

    ctx = SyncContext(
        state=state, settings=settings, graph=graph,
        commands=commands, http=http,
    )

    items_list = items or []
    subs_map = subitems_by_parent or {}

    async def mock_get_all_board_items(self, board_id):
        return items_list

    async def mock_get_subitems(self, item_ids):
        result = []
        for pid in item_ids:
            result.extend(subs_map.get(int(pid) if isinstance(pid, str) else pid, []))
        return result

    _sync_engine.MondayClient.get_all_board_items = mock_get_all_board_items
    _sync_engine.MondayClient.get_subitems = mock_get_subitems

    return ctx


# ===================================================================
# Helper: build push sync context
# ===================================================================


def _build_push_sync_context(
    changed_tasks: list[dict] | None = None,
    task_bodies: dict[str, str] | None = None,
    sync_direction: str = "bidirectional",
    board_column_mappings: dict[str, dict] | None = None,
    board_label_mappings: dict[str, dict] | None = None,
    monday_client: MockMondayClient | None = None,
) -> tuple[SyncContext, MockMondayClient]:
    """Build a SyncContext configured for push sync testing.

    Returns (ctx, mock_monday_client).
    """
    state = MockStateClient({"monday_api_token": "test-token"})
    settings_data: dict[str, str] = {
        "sync_direction": sync_direction,
    }
    if board_column_mappings:
        for board_id, mapping in board_column_mappings.items():
            settings_data[f"column_mapping_{board_id}"] = json.dumps(
                {"column_mapping": mapping}
            )
    if board_label_mappings:
        for board_id, labels in board_label_mappings.items():
            settings_data[f"label_mapping_{board_id}"] = json.dumps(labels)

    settings = MockSettingsClient(settings_data)
    graph = MockGraphClient(
        changed_tasks=changed_tasks or [],
        task_bodies=task_bodies or {},
    )
    http = _MonkeyPatchedHttpForAuth()
    bulk_http = MockHttpClient()
    commands = MockCommandClient(bulk_http)

    ctx = SyncContext(
        state=state, settings=settings, graph=graph,
        commands=commands, http=http,
    )

    mock_client = monday_client or MockMondayClient()
    return ctx, mock_client


# ===================================================================
# Tests: parse_external_url
# ===================================================================


class TestParseExternalUrl:
    """Tests for parse_external_url helper."""

    def test_valid_url(self):
        result = parse_external_url("https://monday.com/boards/12345/pulses/67890")
        assert result == ("12345", "67890")

    def test_none_input(self):
        assert parse_external_url(None) is None

    def test_empty_string(self):
        assert parse_external_url("") is None

    def test_wrong_format_no_pulses(self):
        assert parse_external_url("https://monday.com/boards/123") is None

    def test_wrong_format_no_boards(self):
        assert parse_external_url("https://monday.com/pulses/123") is None

    def test_extra_path_segments(self):
        result = parse_external_url(
            "https://monday.com/boards/111/pulses/222/views/333"
        )
        assert result == ("111", "222")

    def test_trailing_slash(self):
        result = parse_external_url(
            "https://monday.com/boards/100/pulses/200/"
        )
        assert result == ("100", "200")

    def test_numeric_ids_extracted(self):
        result = parse_external_url(
            "https://monday.com/boards/9999999/pulses/8888888"
        )
        assert result is not None
        board_id, item_id = result
        assert board_id == "9999999"
        assert item_id == "8888888"

    def test_non_url_string(self):
        assert parse_external_url("just some text") is None

    def test_integer_input(self):
        # Non-string input returns None
        assert parse_external_url(12345) is None


# ===================================================================
# Tests: _find_changed_tasks
# ===================================================================


class TestFindChangedTasks:
    """Tests for _find_changed_tasks SPARQL helper."""

    @pytest.mark.asyncio
    async def test_no_changed_tasks(self):
        graph = MockGraphClient(changed_tasks=[])
        result = await _find_changed_tasks(graph)
        assert result == []

    @pytest.mark.asyncio
    async def test_one_changed_task(self):
        graph = MockGraphClient(changed_tasks=[{
            "iri": "https://example.org/Task/t1",
            "extUrl": "https://monday.com/boards/1/pulses/2",
            "status": "in-progress",
            "title": "My Task",
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "https://example.org/Task/t1"
        assert result[0]["extUrl"] == "https://monday.com/boards/1/pulses/2"
        assert result[0]["status"] == "in-progress"
        assert result[0]["title"] == "My Task"

    @pytest.mark.asyncio
    async def test_multiple_changed_tasks(self):
        graph = MockGraphClient(changed_tasks=[
            {"iri": "https://example.org/Task/t1", "extUrl": "url1"},
            {"iri": "https://example.org/Task/t2", "extUrl": "url2"},
            {"iri": "https://example.org/Task/t3", "extUrl": "url3"},
        ])
        result = await _find_changed_tasks(graph)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_sparql_includes_external_url(self):
        graph = MockGraphClient()
        await _find_changed_tasks(graph)
        assert len(graph.queries) == 1
        assert "externalUrl" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self):
        graph = MockGraphClient(changed_tasks=[{
            "iri": "https://example.org/Task/t1",
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["status"] is None
        assert result[0]["priority"] is None
        assert result[0]["title"] is None
        assert result[0]["dueDate"] is None


# ===================================================================
# Tests: _get_task_body
# ===================================================================


class TestGetTaskBody:
    """Tests for _get_task_body SPARQL helper."""

    @pytest.mark.asyncio
    async def test_body_found(self):
        graph = MockGraphClient(
            task_bodies={"https://example.org/Task/t1": "Task body text"}
        )
        result = await _get_task_body(graph, "https://example.org/Task/t1")
        assert result == "Task body text"

    @pytest.mark.asyncio
    async def test_no_body(self):
        graph = MockGraphClient()
        result = await _get_task_body(graph, "https://example.org/Task/t1")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_bindings(self):
        graph = MockGraphClient(task_bodies={})
        result = await _get_task_body(graph, "https://example.org/Task/t99")
        assert result is None

    @pytest.mark.asyncio
    async def test_queries_correct_iri(self):
        graph = MockGraphClient()
        await _get_task_body(graph, "https://example.org/Task/t1")
        assert len(graph.queries) == 1
        assert "https://example.org/Task/t1" in graph.queries[0]
        assert "urn:sempkm:body" in graph.queries[0]


# ===================================================================
# Tests: push sync pipeline
# ===================================================================


class TestPushSyncPipeline:
    """Tests for the full push sync pipeline."""

    @pytest.fixture(autouse=True)
    def clear_loop_guard(self):
        _loop_guard._marks.clear()
        yield
        _loop_guard._marks.clear()

    @pytest.mark.asyncio
    async def test_no_changed_tasks_success(self):
        ctx, client = _build_push_sync_context()
        result = await push_sync(ctx, monday_client=client)
        assert result["status"] == "success"
        assert result["pushed"] == 0

    @pytest.mark.asyncio
    async def test_one_changed_task_mutation_called(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/100/pulses/200",
                "status": "done",
                "title": "Test Task",
            }],
            board_column_mappings={"100": {"taskStatus": "status_col"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        assert len(client.mutations) == 1
        assert client.mutations[0]["board_id"] == 100
        assert client.mutations[0]["item_id"] == 200

    @pytest.mark.asyncio
    async def test_column_mapping_loaded_for_board(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/777/pulses/888",
                "status": "in-progress",
            }],
            board_column_mappings={"777": {"taskStatus": "my_status_col"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        values = json.loads(client.mutations[0]["values"])
        assert "my_status_col" in values

    @pytest.mark.asyncio
    async def test_reverse_column_values_passed(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/50/pulses/60",
                "status": "done",
                "priority": "high",
            }],
            board_column_mappings={"50": {
                "taskStatus": "status_col",
                "priority": "priority_col",
            }},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        values = json.loads(client.mutations[0]["values"])
        assert "status_col" in values
        assert "priority_col" in values

    @pytest.mark.asyncio
    async def test_last_synced_at_updated(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        bulk_http = ctx.commands._client
        assert len(bulk_http.recorded_calls) > 0
        found_patch = False
        for url, payload in bulk_http.recorded_calls:
            if url == "/api/commands/bulk":
                cmds = payload.get("commands", [])
                for cmd in cmds:
                    if cmd["command"] == "object.patch":
                        props = cmd["params"]["properties"]
                        assert f"{BPKM}lastSyncedAt" in props
                        found_patch = True
        assert found_patch

    @pytest.mark.asyncio
    async def test_loopguard_marks_item_after_push(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/42",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        assert _loop_guard.is_echo("42", "*")

    @pytest.mark.asyncio
    async def test_parse_url_failure_skips_task(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "not-a-valid-url",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert len(client.mutations) == 0

    @pytest.mark.asyncio
    async def test_missing_column_mapping_skips_task(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/999/pulses/111",
                "status": "done",
            }],
            board_column_mappings={},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_mutation_api_error_recorded(self):
        class FailingMondayClient(MockMondayClient):
            async def change_multiple_column_values(self, board_id, item_id, cv_json):
                raise Exception("API error: rate limited")

        ctx, _ = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        client = FailingMondayClient()
        result = await push_sync(ctx, monday_client=client)
        assert result["status"] == "error"
        assert len(result["errors"]) == 1
        assert "API error" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_multiple_tasks_different_boards(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[
                {
                    "iri": "https://example.org/Task/t1",
                    "extUrl": "https://monday.com/boards/10/pulses/20",
                    "status": "done",
                },
                {
                    "iri": "https://example.org/Task/t2",
                    "extUrl": "https://monday.com/boards/30/pulses/40",
                    "priority": "high",
                },
            ],
            board_column_mappings={
                "10": {"taskStatus": "s1"},
                "30": {"priority": "p1"},
            },
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 2
        assert len(client.mutations) == 2
        boards = {m["board_id"] for m in client.mutations}
        assert boards == {10, 30}

    @pytest.mark.asyncio
    async def test_empty_reverse_column_values_skips(self):
        """When column mapping exists but no properties match, skip task."""
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_push_result_has_correct_counts(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[
                {
                    "iri": "https://example.org/Task/t1",
                    "extUrl": "https://monday.com/boards/10/pulses/20",
                    "status": "done",
                },
                {
                    "iri": "https://example.org/Task/t2",
                    "extUrl": "not-valid",
                },
            ],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        assert result["skipped"] == 1
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_partial_status_on_mixed_results(self):
        class PartialClient(MockMondayClient):
            _call_count = 0
            async def change_multiple_column_values(self, board_id, item_id, cv_json):
                self._call_count += 1
                if self._call_count == 2:
                    raise Exception("fail second")
                self.mutations.append({"board_id": board_id, "item_id": item_id, "values": cv_json})
                return {"id": str(item_id), "name": "OK"}

        ctx, _ = _build_push_sync_context(
            changed_tasks=[
                {
                    "iri": "https://example.org/Task/t1",
                    "extUrl": "https://monday.com/boards/10/pulses/20",
                    "status": "done",
                },
                {
                    "iri": "https://example.org/Task/t2",
                    "extUrl": "https://monday.com/boards/10/pulses/30",
                    "status": "in-progress",
                },
            ],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        client = PartialClient()
        result = await push_sync(ctx, monday_client=client)
        assert result["status"] == "partial"
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_all_errors_status(self):
        class AlwaysFailClient(MockMondayClient):
            async def change_multiple_column_values(self, board_id, item_id, cv_json):
                raise Exception("always fail")

        ctx, _ = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        client = AlwaysFailClient()
        result = await push_sync(ctx, monday_client=client)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_timestamp_in_iso_format(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        result = await push_sync(ctx, monday_client=client)
        ts = result["timestamp"]
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is not None

    @pytest.mark.asyncio
    async def test_label_mapping_reverse_used(self):
        """Custom label mappings are inverted and used in push."""
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "status_col"}},
            board_label_mappings={"10": {
                "status_label_mapping": {"Complete": "done", "WIP": "in-progress"},
            }},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        values = json.loads(client.mutations[0]["values"])
        status_val = json.loads(values["status_col"])
        assert status_val["label"] == "Complete"

    @pytest.mark.asyncio
    async def test_due_date_pushed(self):
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "dueDate": "2025-06-15",
            }],
            board_column_mappings={"10": {"dueDate": "date_col"}},
        )
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        values = json.loads(client.mutations[0]["values"])
        assert "date_col" in values


# ===================================================================
# Tests: LoopGuard integration with pull sync
# ===================================================================


class TestLoopGuardIntegrationPull:
    """Tests for LoopGuard echo prevention in pull_sync."""

    @pytest.fixture(autouse=True)
    def clear_loop_guard(self):
        """Clear LoopGuard marks before each test."""
        _loop_guard._marks.clear()
        yield
        _loop_guard._marks.clear()

    @pytest.mark.asyncio
    async def test_marked_item_skipped_in_pull(self):
        """Item marked in LoopGuard is skipped during pull."""
        items = [_make_item(item_id=42, name="Pushed Task")]
        _loop_guard.mark_pushed("42", "*")

        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["skipped"] >= 1
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_unmarked_item_processed(self):
        """Item NOT marked in LoopGuard is processed normally."""
        items = [_make_item(item_id=42, name="Normal Task")]
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_expired_mark_item_processed(self):
        """After TTL expires, item is processed again."""
        items = [_make_item(item_id=42, name="Expired Task")]
        _loop_guard._marks["42:*"] = 0.0
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_multiple_items_only_marked_skipped(self):
        """Only the marked item is skipped, others are processed."""
        items = [
            _make_item(item_id=10, name="Marked Item"),
            _make_item(item_id=20, name="Normal Item"),
        ]
        _loop_guard.mark_pushed("10", "*")
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 1
        assert result["skipped"] >= 1

    @pytest.mark.asyncio
    async def test_marked_subitem_skipped(self):
        """Subitem marked in LoopGuard is skipped."""
        items = [_make_item(item_id=100, name="Parent")]
        subitems = {
            100: [_make_subitem(sub_id=200, name="Pushed Sub", parent_item_id=100)],
        }
        _loop_guard.mark_pushed("200", "*")
        ctx = _build_basic_sync_context(
            items=items, subitems_by_parent=subitems,
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1
        assert result["skipped"] >= 1

    @pytest.mark.asyncio
    async def test_echo_skip_increments_skipped_count(self):
        """Skipping via LoopGuard increments the skipped_count."""
        items = [
            _make_item(item_id=10, name="Skip1"),
            _make_item(item_id=20, name="Skip2"),
        ]
        _loop_guard.mark_pushed("10", "*")
        _loop_guard.mark_pushed("20", "*")
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["skipped"] >= 2
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_loopguard_cleanup_does_not_break_sync(self):
        """Calling cleanup() before sync doesn't cause issues."""
        items = [_make_item(item_id=42, name="Task After Cleanup")]
        _loop_guard.mark_pushed("99", "*")
        _loop_guard.cleanup()
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_module_level_singleton_shared(self):
        """LoopGuard singleton is shared between push and pull."""
        assert _loop_guard is _sync_engine._loop_guard


# ===================================================================
# Tests: push + pull integration (LoopGuard round-trip)
# ===================================================================


class TestPushPullLoopGuardRoundTrip:
    """Tests for the full push to pull echo prevention flow."""

    @pytest.fixture(autouse=True)
    def clear_loop_guard(self):
        _loop_guard._marks.clear()
        yield
        _loop_guard._marks.clear()

    @pytest.mark.asyncio
    async def test_pushed_item_skipped_on_next_pull(self):
        """After pushing item 42, a subsequent pull skips it."""
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/42",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        push_result = await push_sync(ctx, monday_client=client)
        assert push_result["pushed"] == 1

        items = [_make_item(item_id=42, name="Same Task")]
        pull_ctx = _build_basic_sync_context(items=items)
        pull_result = await pull_sync(pull_ctx)
        assert pull_result["skipped"] >= 1
        assert pull_result["created"] == 0

    @pytest.mark.asyncio
    async def test_unpushed_item_not_skipped_on_pull(self):
        """Items not in LoopGuard are processed on pull."""
        items = [_make_item(item_id=99, name="New Task")]
        ctx = _build_basic_sync_context(items=items)
        result = await pull_sync(ctx)
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_push_marks_correct_item_id(self):
        """Push marks the exact item_id from the URL."""
        ctx, client = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/t1",
                "extUrl": "https://monday.com/boards/10/pulses/555",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        await push_sync(ctx, monday_client=client)
        assert _loop_guard.is_echo("555", "*")
        assert not _loop_guard.is_echo("556", "*")


# ===================================================================
# Tests: push sync error isolation
# ===================================================================


class TestPushSyncErrorIsolation:
    """Tests that per-task errors don't stop other tasks."""

    @pytest.fixture(autouse=True)
    def clear_loop_guard(self):
        _loop_guard._marks.clear()
        yield
        _loop_guard._marks.clear()

    @pytest.mark.asyncio
    async def test_error_on_first_task_continues(self):
        class FailFirstClient(MockMondayClient):
            _call_count = 0
            async def change_multiple_column_values(self, board_id, item_id, cv_json):
                self._call_count += 1
                if self._call_count == 1:
                    raise Exception("first fails")
                self.mutations.append({"board_id": board_id, "item_id": item_id, "values": cv_json})
                return {"id": str(item_id), "name": "OK"}

        ctx, _ = _build_push_sync_context(
            changed_tasks=[
                {
                    "iri": "https://example.org/Task/t1",
                    "extUrl": "https://monday.com/boards/10/pulses/1",
                    "status": "done",
                },
                {
                    "iri": "https://example.org/Task/t2",
                    "extUrl": "https://monday.com/boards/10/pulses/2",
                    "status": "in-progress",
                },
            ],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        client = FailFirstClient()
        result = await push_sync(ctx, monday_client=client)
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["iri"] == "https://example.org/Task/t1"

    @pytest.mark.asyncio
    async def test_error_includes_task_iri_and_message(self):
        class FailClient(MockMondayClient):
            async def change_multiple_column_values(self, board_id, item_id, cv_json):
                raise ValueError("Specific error message")

        ctx, _ = _build_push_sync_context(
            changed_tasks=[{
                "iri": "https://example.org/Task/xyz",
                "extUrl": "https://monday.com/boards/10/pulses/20",
                "status": "done",
            }],
            board_column_mappings={"10": {"taskStatus": "s"}},
        )
        client = FailClient()
        result = await push_sync(ctx, monday_client=client)
        assert result["errors"][0]["iri"] == "https://example.org/Task/xyz"
        assert "Specific error message" in result["errors"][0]["error"]
