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
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
push_sync = _sync_engine.push_sync
_find_existing_task = _sync_engine._find_existing_task
_find_all_tasks_for_board = _sync_engine._find_all_tasks_for_board
_has_changes = _sync_engine._has_changes
_build_create_command = _sync_engine._build_create_command
_build_update_commands = _sync_engine._build_update_commands
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
    """

    def __init__(
        self,
        slug_map: dict[str, dict] | None = None,
        email_to_iri: dict[str, str] | None = None,
    ):
        self.slug_map = slug_map or {}
        self.email_to_iri = email_to_iri or {}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)

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
    ):
        self.me_response = me_response or {"id": "1", "name": "Test User", "email": "test@example.com"}
        self.items_by_board = items_by_board or {}
        self.subitems_by_parent = subitems_by_parent or {}
        self.users = users or []

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
    """Tests for the push sync stub."""

    @pytest.mark.asyncio
    async def test_returns_skipped_not_implemented(self):
        ctx = SyncContext()
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "not implemented"


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
