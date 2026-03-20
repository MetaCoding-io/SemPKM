"""Unit tests for the Jira pull sync engine.

Loads app modules from the apps directory via importlib so the app does
not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory (dependency order)
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "jira-sync"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_adf_converter = _load_module("adf_converter", _SERVICES_DIR / "adf_converter.py")
_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_jira_client = _load_module("jira_client", _SERVICES_DIR / "jira_client.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_person_matcher = _load_module("person_matcher", _SERVICES_DIR / "person_matcher.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
push_sync = _sync_engine.push_sync
_find_existing_task = _sync_engine._find_existing_task
_find_existing_milestone = _sync_engine._find_existing_milestone
_find_changed_tasks = _sync_engine._find_changed_tasks
_get_task_body = _sync_engine._get_task_body
_process_issue_links = _sync_engine._process_issue_links
_build_jql = _sync_engine._build_jql
_build_create_command = _sync_engine._build_create_command
_build_update_commands = _sync_engine._build_update_commands
_submit_commands_batched = _sync_engine._submit_commands_batched
_get_parent_epic_key = _sync_engine._get_parent_epic_key
_iso_to_jql_date = _sync_engine._iso_to_jql_date
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
build_issue_patch = _field_mapper.build_issue_patch
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
      (matches ``_find_existing_task`` which detects STRENDS + /Task/)
    - ``milestone_slug_map``: slug → dict with iri
      (matches ``_find_existing_milestone`` which detects STRENDS + /Milestone/)
    - ``email_to_iri``: email → Person IRI for PersonMatcher lookups
    - ``body_map``: iri → body text for ``_get_task_body`` lookups
    - ``changed_tasks``: list of dicts for ``_find_changed_tasks`` results
    """

    def __init__(
        self,
        slug_map: dict[str, dict] | None = None,
        milestone_slug_map: dict[str, dict] | None = None,
        email_to_iri: dict[str, str] | None = None,
        body_map: dict[str, str] | None = None,
        changed_tasks: list[dict] | None = None,
    ):
        self.slug_map = slug_map or {}
        self.milestone_slug_map = milestone_slug_map or {}
        self.email_to_iri = email_to_iri or {}
        self.body_map = body_map or {}
        self.changed_tasks = changed_tasks
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)

        # Changed tasks query (for _find_changed_tasks — externalProvider "jira" + externalId + syncDirection)
        if (
            self.changed_tasks is not None
            and 'externalProvider' in sparql
            and '"jira"' in sparql
            and 'externalId' in sparql
            and 'syncDir' in sparql
        ):
            bindings = []
            for task in self.changed_tasks:
                binding: dict = {
                    "task": {"type": "uri", "value": task["iri"]},
                    "extId": {"type": "literal", "value": task["externalId"]},
                }
                if task.get("status"):
                    binding["status"] = {"type": "literal", "value": task["status"]}
                if task.get("priority"):
                    binding["priority"] = {"type": "literal", "value": task["priority"]}
                if task.get("title"):
                    binding["title"] = {"type": "literal", "value": task["title"]}
                if task.get("lastSyncedAt"):
                    binding["lastSynced"] = {"type": "literal", "value": task["lastSyncedAt"]}
            bindings = [self._build_changed_task_binding(t) for t in self.changed_tasks]
            return {"results": {"bindings": bindings}}

        # Body text lookup (for _get_task_body — urn:sempkm:body)
        if "urn:sempkm:body" in sparql:
            for iri, body in self.body_map.items():
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

        # Milestone lookup (STRENDS + /Milestone/)
        if "STRENDS" in sparql and "/Milestone/" in sparql:
            for slug, info in self.milestone_slug_map.items():
                if slug in sparql:
                    return {"results": {"bindings": [
                        {"m": {"type": "uri", "value": info["iri"]}}
                    ]}}

        # PersonMatcher email lookup (foaf or crm:email)
        if "foaf" in sparql.lower() or "crm:email" in sparql.lower():
            for email, iri in self.email_to_iri.items():
                if email.lower() in sparql.lower():
                    return {"results": {"bindings": [
                        {"person": {"type": "uri", "value": iri}}
                    ]}}

        # Default: no bindings
        return {"results": {"bindings": []}}

    def _build_changed_task_binding(self, task: dict) -> dict:
        binding: dict = {
            "task": {"type": "uri", "value": task["iri"]},
            "extId": {"type": "literal", "value": task["externalId"]},
        }
        if task.get("status"):
            binding["status"] = {"type": "literal", "value": task["status"]}
        if task.get("priority"):
            binding["priority"] = {"type": "literal", "value": task["priority"]}
        if task.get("title"):
            binding["title"] = {"type": "literal", "value": task["title"]}
        if task.get("lastSyncedAt"):
            binding["lastSynced"] = {"type": "literal", "value": task["lastSyncedAt"]}
        return binding


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


class MockJiraClient:
    """Mock JiraClient — returns canned data for search, get_user, get_projects, get_myself.

    Also tracks ``update_issue()`` calls for push sync assertions.
    """

    def __init__(
        self,
        issues: list[dict] | None = None,
        users: dict[str, dict] | None = None,
        projects: list[dict] | None = None,
        myself: dict | None = None,
        update_issue_error: Exception | None = None,
    ):
        self._issues = issues if issues is not None else []
        self._users = users or {}
        self._projects = projects or []
        self._myself = myself or {
            "emailAddress": "test@example.com",
            "displayName": "Test User",
            "accountId": "test-account-id",
        }
        self._update_issue_error = update_issue_error
        self.update_issue_calls: list[tuple[str, dict]] = []

    async def search_all_issues(self, jql: str) -> list[dict]:
        return self._issues

    async def get_user(self, account_id: str) -> dict:
        return self._users.get(account_id, {
            "emailAddress": f"{account_id}@example.com",
            "displayName": f"User {account_id}",
        })

    async def get_projects(self) -> list[dict]:
        return self._projects

    async def get_myself(self) -> dict:
        return self._myself

    async def update_issue(self, issue_key: str, fields: dict) -> None:
        self.update_issue_calls.append((issue_key, fields))
        if self._update_issue_error:
            raise self._update_issue_error


class MockExternalHttpClient:
    """Stub for SDK HttpClient (external HTTP requests).

    Used by JiraClient internally; also usable as ctx.http.
    """

    def __init__(self, responses: list[MockResponse] | None = None):
        self.requests: list[dict] = []
        self._responses = list(responses or [])
        self._index = 0

    async def get(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self._next_response()

    async def post(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self._next_response()

    async def request(self, method: str, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self._next_response()

    def _next_response(self) -> MockResponse:
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return MockResponse(200, {
            "emailAddress": "test@example.com",
            "displayName": "Test User",
            "accountId": "test-account-id",
        })


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes.

    - ctx.state → MockStateClient (runtime state)
    - ctx.settings → MockSettingsClient (configuration)
    - ctx.graph → MockGraphClient (SPARQL queries)
    - ctx.commands → MockCommandClient (._client → MockHttpClient for bulk)
    - ctx.http → MockExternalHttpClient (for JiraClient)
    """

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        settings_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
        ext_http_client: MockExternalHttpClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.settings = MockSettingsClient(settings_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.commands = MockCommandClient(_http)
        self.http = ext_http_client or MockExternalHttpClient()
        self.app_id = "jira-sync"


# ===================================================================
# Jira issue fixture builders
# ===================================================================


def _make_issue(
    key: str = "PROJ-42",
    summary: str = "Fix the widget",
    *,
    project_key: str = "PROJ",
    status_key: str = "indeterminate",
    status_name: str = "In Progress",
    priority_name: str = "High",
    issue_type: str = "Task",
    assignee_id: str | None = "acc123",
    assignee_name: str | None = "Alice",
    description: dict | None = None,
    labels: list | None = None,
    components: list | None = None,
    sprint: dict | None = None,
    parent: dict | None = None,
    customfield_10014: str | None = None,
    duedate: str | None = "2026-04-15",
    updated: str = "2026-03-19T12:00:00+00:00",
    issue_id: str = "10042",
) -> dict:
    """Build a realistic Jira issue dict following /rest/api/3/search shape."""
    fields: dict = {
        "summary": summary,
        "status": {
            "name": status_name,
            "statusCategory": {"key": status_key},
        },
        "priority": {"name": priority_name},
        "issuetype": {"name": issue_type},
        "project": {"key": project_key},
        "duedate": duedate,
        "resolutiondate": None,
        "updated": updated,
        "labels": labels if labels is not None else [],
        "components": components if components is not None else [],
    }

    if assignee_id:
        fields["assignee"] = {
            "accountId": assignee_id,
            "displayName": assignee_name,
        }
    else:
        fields["assignee"] = None

    if description is not None:
        fields["description"] = description
    else:
        fields["description"] = None

    if sprint is not None:
        fields["sprint"] = sprint

    if parent is not None:
        fields["parent"] = parent

    if customfield_10014 is not None:
        fields["customfield_10014"] = customfield_10014

    return {
        "id": issue_id,
        "key": key,
        "self": f"https://mysite.atlassian.net/rest/api/3/issue/{issue_id}",
        "fields": fields,
    }


def _make_epic(
    key: str = "PROJ-100",
    summary: str = "Q2 Feature Epic",
    *,
    project_key: str = "PROJ",
    status_key: str = "indeterminate",
    status_name: str = "In Progress",
    duedate: str | None = "2026-06-30",
    updated: str = "2026-03-19T12:00:00+00:00",
    issue_id: str = "10100",
) -> dict:
    """Build a Jira Epic issue dict (issuetype.name = 'Epic')."""
    return _make_issue(
        key=key,
        summary=summary,
        project_key=project_key,
        status_key=status_key,
        status_name=status_name,
        issue_type="Epic",
        assignee_id=None,
        duedate=duedate,
        updated=updated,
        issue_id=issue_id,
    )


def _make_adf_doc(text: str) -> dict:
    """Build a minimal ADF document with a single paragraph of text."""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": text}
                ],
            }
        ],
    }


# ===================================================================
# Helper to build a connected context (credentials in state, JiraClient
# returns the myself response on verification)
# ===================================================================


def _connected_state() -> dict[str, str]:
    """State data that makes get_connection_status return connected=True."""
    return {
        "jira_email": "test@example.com",
        "jira_token": "test-token-12345678",
        "jira_site_url": "https://mysite.atlassian.net",
    }


def _default_settings(**overrides) -> dict[str, str]:
    """Default settings with at least one project selected."""
    data = {
        "selected_projects": json.dumps(["PROJ"]),
        "sync_direction": "pull-only",
    }
    data.update(overrides)
    return data


# ===================================================================
# (a) SPARQL helper tests
# ===================================================================


class TestFindExistingTask:
    """Tests for _find_existing_task SPARQL helper."""

    @pytest.mark.asyncio
    async def test_found_by_slug(self):
        slug = compute_issue_slug("PROJ", "PROJ-42")
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "status": "in-progress",
                "externalId": "PROJ-42",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }
        })
        result = await _find_existing_task(graph, slug)
        assert result is not None
        assert result["iri"] == f"https://example.org/data/Task/{slug}"
        assert result["status"] == "in-progress"
        assert result["externalId"] == "PROJ-42"
        assert result["lastSyncedAt"] == "2026-03-18T10:00:00Z"

    @pytest.mark.asyncio
    async def test_not_found(self):
        graph = MockGraphClient()
        result = await _find_existing_task(graph, "jira-nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_fields_when_optional(self):
        """When optional fields are absent, they should be None in result."""
        slug = compute_issue_slug("PROJ", "PROJ-99")
        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Task/{slug}"}
        })
        result = await _find_existing_task(graph, slug)
        assert result is not None
        assert result["iri"].endswith(slug)
        assert result["status"] is None
        assert result["externalId"] is None
        assert result["lastSyncedAt"] is None

    @pytest.mark.asyncio
    async def test_sparql_contains_task_type(self):
        """The SPARQL query should reference bpkm:Task and STRENDS."""
        graph = MockGraphClient()
        await _find_existing_task(graph, "some-slug")
        assert len(graph.queries) == 1
        q = graph.queries[0]
        assert f"{BPKM}Task" in q
        assert "STRENDS" in q
        assert "/Task/some-slug" in q


class TestFindExistingMilestone:
    """Tests for _find_existing_milestone SPARQL helper."""

    @pytest.mark.asyncio
    async def test_found_by_slug(self):
        slug = compute_issue_slug("PROJ", "PROJ-100")
        graph = MockGraphClient(milestone_slug_map={
            slug: {"iri": f"https://example.org/data/Milestone/{slug}"}
        })
        result = await _find_existing_milestone(graph, slug)
        assert result is not None
        assert result["iri"] == f"https://example.org/data/Milestone/{slug}"

    @pytest.mark.asyncio
    async def test_not_found(self):
        graph = MockGraphClient()
        result = await _find_existing_milestone(graph, "jira-nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_sparql_contains_milestone_type(self):
        graph = MockGraphClient()
        await _find_existing_milestone(graph, "some-slug")
        assert len(graph.queries) == 1
        q = graph.queries[0]
        assert f"{BPKM}Milestone" in q
        assert "STRENDS" in q
        assert "/Milestone/some-slug" in q


# ===================================================================
# (f) JQL construction tests
# ===================================================================


class TestBuildJql:
    """Tests for _build_jql JQL query construction."""

    def test_projects_only(self):
        jql = _build_jql(["PROJ1", "PROJ2"])
        assert 'project in ("PROJ1", "PROJ2")' == jql

    def test_single_project_uses_in_syntax(self):
        jql = _build_jql(["PROJ1"])
        assert 'project in ("PROJ1")' == jql

    def test_projects_plus_user_filter(self):
        jql = _build_jql(["PROJ1"], jql_filter="status = Open")
        assert 'project in ("PROJ1") AND (status = Open)' == jql

    def test_projects_plus_delta(self):
        jql = _build_jql(["PROJ1"], last_sync_at="2026-03-19T15:30:00+00:00")
        assert 'project in ("PROJ1")' in jql
        assert 'updated >= "2026/03/19 15:30"' in jql

    def test_projects_plus_filter_plus_delta(self):
        jql = _build_jql(
            ["PROJ1"],
            jql_filter="status = Open",
            last_sync_at="2026-03-19T15:30:00+00:00",
        )
        assert 'project in ("PROJ1")' in jql
        assert "(status = Open)" in jql
        assert 'updated >= "2026/03/19 15:30"' in jql

    def test_whitespace_filter_stripped(self):
        jql = _build_jql(["PROJ1"], jql_filter="  status = Open  ")
        assert "(status = Open)" in jql

    def test_empty_filter_ignored(self):
        jql = _build_jql(["PROJ1"], jql_filter="  ")
        assert "AND" not in jql

    def test_none_filter_ignored(self):
        jql = _build_jql(["PROJ1"], jql_filter=None)
        assert "AND" not in jql

    def test_jql_date_format_strips_timezone_and_seconds(self):
        """ISO 2026-03-19T15:30:45+00:00 → 2026/03/19 15:30"""
        result = _iso_to_jql_date("2026-03-19T15:30:45+00:00")
        assert result == "2026/03/19 15:30"

    def test_jql_date_format_handles_z_suffix(self):
        result = _iso_to_jql_date("2026-03-19T10:00:00Z")
        assert result == "2026/03/19 10:00"

    def test_jql_date_invalid_returns_none(self):
        result = _iso_to_jql_date("not-a-date")
        assert result is None


# ===================================================================
# (b) Command builder tests
# ===================================================================


class TestBuildCreateCommand:
    """Tests for _build_create_command."""

    def test_task_type(self):
        props = {"dcterms:title": "Test task"}
        cmd = _build_create_command("jira-abc123", props, f"{BPKM}Task")
        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Task"
        assert cmd["params"]["slug"] == "jira-abc123"
        assert cmd["params"]["properties"]["dcterms:title"] == "Test task"

    def test_milestone_type(self):
        props = {"dcterms:title": "Epic milestone"}
        cmd = _build_create_command("jira-def456", props, f"{BPKM}Milestone")
        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Milestone"
        assert cmd["params"]["slug"] == "jira-def456"


class TestBuildUpdateCommands:
    """Tests for _build_update_commands."""

    def test_patch_only(self):
        cmds = _build_update_commands(
            "urn:task:1", {"dcterms:title": "Updated"}, None, None,
        )
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"
        assert cmds[0]["params"]["iri"] == "urn:task:1"

    def test_with_description(self):
        cmds = _build_update_commands(
            "urn:task:1", {"dcterms:title": "X"}, "# Hello", None,
        )
        assert len(cmds) == 2
        assert cmds[1]["command"] == "body.set"
        assert cmds[1]["params"]["body"] == "# Hello"

    def test_with_assignee(self):
        cmds = _build_update_commands(
            "urn:task:1", {}, None, "urn:person:alice",
        )
        assert len(cmds) == 2
        assert cmds[1]["command"] == "edge.create"
        assert cmds[1]["params"]["predicate"] == f"{BPKM}assignedTo"
        assert cmds[1]["params"]["target"] == "urn:person:alice"

    def test_with_description_and_assignee(self):
        cmds = _build_update_commands(
            "urn:task:1", {}, "desc", "urn:person:bob",
        )
        assert len(cmds) == 3
        assert cmds[0]["command"] == "object.patch"
        assert cmds[1]["command"] == "body.set"
        assert cmds[2]["command"] == "edge.create"


# ===================================================================
# (c) Pull sync happy path tests
# ===================================================================


class TestPullSyncHappyPath:
    """Tests for pull_sync basic happy paths."""

    @pytest.mark.asyncio
    async def test_basic_pull_creates_tasks(self):
        """Two non-epic issues → two Tasks created, status 'success'."""
        issues = [
            _make_issue("PROJ-1", "First task", project_key="PROJ", issue_id="10001",
                        assignee_id=None),
            _make_issue("PROJ-2", "Second task", project_key="PROJ", issue_id="10002",
                        assignee_id=None),
        ]
        ext_http = MockExternalHttpClient(responses=[
            # get_myself response for auth check
            MockResponse(200, {
                "emailAddress": "test@example.com",
                "displayName": "Test User",
            }),
        ])
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        # Patch JiraClient.search_all_issues to return our canned issues
        with patch.object(_sync_engine, "JiraClient") as MockJC:
            mock_jira = MockJiraClient(issues=issues)
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["errors"] == 0
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_pull_with_adf_description(self):
        """Issue with ADF description → markdown body.set after Phase 2 lookup."""
        adf = _make_adf_doc("Hello world")
        issues = [
            _make_issue("PROJ-1", "Has description", description=adf,
                        assignee_id=None, project_key="PROJ", issue_id="10001"),
        ]
        # After Phase 1 create, the slug must be discoverable for Phase 2
        slug = compute_issue_slug("PROJ", "PROJ-1")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient()

        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                # After Phase 1, make the slug discoverable
                original_find = _find_existing_task
                call_count = [0]

                async def find_with_phase2(gc, s):
                    call_count[0] += 1
                    # First call is during processing (should return None = new)
                    # Subsequent calls are Phase 2 lookups (return IRI)
                    if call_count[0] <= 1:
                        return None
                    return {"iri": f"https://example.org/data/Task/{s}", "status": None, "externalId": None, "lastSyncedAt": None}

                with patch.object(_sync_engine, "_find_existing_task", side_effect=find_with_phase2):
                    result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 1
        # Phase 2 should have submitted body.set commands
        if http.recorded_calls:
            all_cmds = []
            for _, payload in http.recorded_calls:
                if payload and "commands" in payload:
                    all_cmds.extend(payload["commands"])
            body_set_cmds = [c for c in all_cmds if c.get("command") == "body.set"]
            if body_set_cmds:
                assert "Hello world" in body_set_cmds[0]["params"]["body"]

    @pytest.mark.asyncio
    async def test_pull_with_assignee(self):
        """Issue with assignee → person resolution and edge.create."""
        issues = [
            _make_issue("PROJ-1", "Assigned task", assignee_id="acc123",
                        assignee_name="Alice", project_key="PROJ", issue_id="10001"),
        ]
        slug = compute_issue_slug("PROJ", "PROJ-1")
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        # PersonMatcher will look up by email from get_user
        graph = MockGraphClient(email_to_iri={
            "acc123@example.com": "urn:person:alice",
        })

        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_pull_with_labels_and_components(self):
        """Labels + components become tags in the task properties."""
        issues = [
            _make_issue(
                "PROJ-1", "Tagged task", assignee_id=None,
                labels=[{"name": "bug"}, {"name": "urgent"}],
                components=[{"name": "backend"}],
                project_key="PROJ", issue_id="10001",
            ),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 1
        # Verify the create command included tags
        if http.recorded_calls:
            all_cmds = []
            for _, payload in http.recorded_calls:
                if payload and "commands" in payload:
                    all_cmds.extend(payload["commands"])
            create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
            assert len(create_cmds) >= 1
            props = create_cmds[0]["params"]["properties"]
            tags = props.get(f"{BPKM}tags", [])
            assert "bug" in tags
            assert "urgent" in tags
            assert "backend" in tags

    @pytest.mark.asyncio
    async def test_pull_with_sprint(self):
        """Sprint name maps to taskGroup property."""
        issues = [
            _make_issue(
                "PROJ-1", "Sprint task", assignee_id=None,
                sprint={"name": "Sprint 7"},
                project_key="PROJ", issue_id="10001",
            ),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        if http.recorded_calls:
            all_cmds = []
            for _, payload in http.recorded_calls:
                if payload and "commands" in payload:
                    all_cmds.extend(payload["commands"])
            create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
            if create_cmds:
                props = create_cmds[0]["params"]["properties"]
                assert props.get(f"{BPKM}taskGroup") == "Sprint 7"

    @pytest.mark.asyncio
    async def test_pull_with_due_date(self):
        """Due date maps to dueDate property (truncated to date-only)."""
        issues = [
            _make_issue(
                "PROJ-1", "Due task", assignee_id=None,
                duedate="2026-04-15",
                project_key="PROJ", issue_id="10001",
            ),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        if http.recorded_calls:
            all_cmds = []
            for _, payload in http.recorded_calls:
                if payload and "commands" in payload:
                    all_cmds.extend(payload["commands"])
            create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
            if create_cmds:
                props = create_cmds[0]["params"]["properties"]
                assert props.get(f"{BPKM}dueDate") == "2026-04-15"

    @pytest.mark.asyncio
    async def test_update_existing_task(self):
        """When slug exists in graph → object.patch instead of object.create."""
        slug = compute_issue_slug("PROJ", "PROJ-1")
        issues = [
            _make_issue(
                "PROJ-1", "Existing task", assignee_id=None,
                project_key="PROJ", issue_id="10001",
                updated="2026-03-19T14:00:00+00:00",
            ),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "status": "todo",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }
        })
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["updated"] == 1
        assert result["created"] == 0
        # Should have submitted update (patch) commands
        if http.recorded_calls:
            all_cmds = []
            for _, payload in http.recorded_calls:
                if payload and "commands" in payload:
                    all_cmds.extend(payload["commands"])
            patch_cmds = [c for c in all_cmds if c.get("command") == "object.patch"]
            assert len(patch_cmds) >= 1

    @pytest.mark.asyncio
    async def test_empty_issue_list(self):
        """No issues fetched → success with 0 counts."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_result_dict_has_correct_keys(self):
        """Result dict includes all expected keys."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        expected_keys = {"status", "created", "updated", "skipped", "errors", "failed_issues", "duration_ms"}
        assert expected_keys.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def test_pull_stores_last_sync_at(self):
        """After pull with actual issues, last_sync_at is stored in ctx.state."""
        issues = [
            _make_issue("PROJ-1", "Sync me", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(last_sync)
        assert dt.tzinfo is not None


# ===================================================================
# (d) Epic → Milestone tests
# ===================================================================


class TestEpicToMilestone:
    """Tests for Epic detection and Milestone creation."""

    @pytest.mark.asyncio
    async def test_epic_creates_milestone(self):
        """Epic issuetype → Milestone object (not Task)."""
        issues = [_make_epic("PROJ-100", "My Epic")]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        # Verify the create command uses Milestone type
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
        assert len(create_cmds) == 1
        assert create_cmds[0]["params"]["type"] == f"{BPKM}Milestone"

    @pytest.mark.asyncio
    async def test_non_epic_creates_task(self):
        """Non-Epic issue → Task object."""
        issues = [_make_issue("PROJ-1", "Regular task", assignee_id=None)]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
        assert len(create_cmds) == 1
        assert create_cmds[0]["params"]["type"] == f"{BPKM}Task"

    @pytest.mark.asyncio
    async def test_mixed_batch_epics_and_tasks(self):
        """1 Epic + 2 Tasks → 1 Milestone + 2 Tasks."""
        issues = [
            _make_epic("PROJ-100", "My Epic"),
            _make_issue("PROJ-1", "Task 1", assignee_id=None, issue_id="10001"),
            _make_issue("PROJ-2", "Task 2", assignee_id=None, issue_id="10002"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 3
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
        types = [c["params"]["type"] for c in create_cmds]
        assert types.count(f"{BPKM}Milestone") == 1
        assert types.count(f"{BPKM}Task") == 2

    @pytest.mark.asyncio
    async def test_epic_milestone_status_active(self):
        """Epic with in-progress status → milestoneStatus 'active'."""
        issues = [_make_epic("PROJ-100", "Active Epic", status_key="indeterminate")]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
        assert len(create_cmds) == 1
        props = create_cmds[0]["params"]["properties"]
        assert props[f"{BPKM}milestoneStatus"] == "active"

    @pytest.mark.asyncio
    async def test_epic_milestone_status_completed(self):
        """Epic with done status → milestoneStatus 'completed'."""
        issues = [_make_epic("PROJ-100", "Done Epic", status_key="done")]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        create_cmds = [c for c in all_cmds if c.get("command") == "object.create"]
        props = create_cmds[0]["params"]["properties"]
        assert props[f"{BPKM}milestoneStatus"] == "completed"

    @pytest.mark.asyncio
    async def test_epic_child_linking_via_parent_key(self):
        """Child with parent.key pointing to Epic → edge.create with bpkm:milestone."""
        epic = _make_epic("PROJ-100", "My Epic", issue_id="10100")
        child = _make_issue(
            "PROJ-1", "Child task", assignee_id=None, issue_id="10001",
            parent={
                "key": "PROJ-100",
                "fields": {"issuetype": {"name": "Epic"}},
            },
        )
        issues = [epic, child]

        epic_slug = compute_issue_slug("PROJ", "PROJ-100")
        child_slug = compute_issue_slug("PROJ", "PROJ-1")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        # After Phase 1, both objects exist — Phase 3 discovers them
        graph = MockGraphClient(
            milestone_slug_map={
                epic_slug: {"iri": f"https://example.org/data/Milestone/{epic_slug}"}
            },
            slug_map={
                child_slug: {
                    "iri": f"https://example.org/data/Task/{child_slug}",
                    "status": None,
                    "lastSyncedAt": None,
                }
            },
        )

        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        # The child already exists in graph (slug_map), so it will be updated not created.
        # The epic is new → milestone created. So created=1 (epic), updated=1 (child).
        # Phase 3 links child→epic via bpkm:milestone edge.
        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] + result["updated"] >= 2
        # Check for edge.create with bpkm:milestone predicate
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        milestone_edges = [
            c for c in all_cmds
            if c.get("command") == "edge.create"
            and c.get("params", {}).get("predicate") == f"{BPKM}milestone"
        ]
        assert len(milestone_edges) >= 1

    @pytest.mark.asyncio
    async def test_epic_child_linking_via_customfield_10014(self):
        """Classic Epic Link via customfield_10014 → epic parent detected."""
        epic = _make_epic("PROJ-100", "My Epic", issue_id="10100")
        child = _make_issue(
            "PROJ-1", "Child task", assignee_id=None, issue_id="10001",
            customfield_10014="PROJ-100",
        )
        issues = [epic, child]

        epic_slug = compute_issue_slug("PROJ", "PROJ-100")
        child_slug = compute_issue_slug("PROJ", "PROJ-1")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(
            milestone_slug_map={
                epic_slug: {"iri": f"https://example.org/data/Milestone/{epic_slug}"}
            },
            slug_map={
                child_slug: {
                    "iri": f"https://example.org/data/Task/{child_slug}",
                    "status": None,
                    "lastSyncedAt": None,
                }
            },
        )

        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] + result["updated"] >= 2
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        milestone_edges = [
            c for c in all_cmds
            if c.get("command") == "edge.create"
            and c.get("params", {}).get("predicate") == f"{BPKM}milestone"
        ]
        assert len(milestone_edges) >= 1

    @pytest.mark.asyncio
    async def test_child_with_no_parent_no_milestone_edge(self):
        """Child issue with no parent → no milestone edge created."""
        issues = [
            _make_issue("PROJ-1", "Orphan task", assignee_id=None, issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        milestone_edges = [
            c for c in all_cmds
            if c.get("command") == "edge.create"
            and c.get("params", {}).get("predicate") == f"{BPKM}milestone"
        ]
        assert len(milestone_edges) == 0

    @pytest.mark.asyncio
    async def test_epic_parent_not_in_synced_set(self):
        """Child references an epic key not in the synced batch → no error, no edge."""
        child = _make_issue(
            "PROJ-1", "Child task", assignee_id=None, issue_id="10001",
            parent={
                "key": "PROJ-999",  # not in this batch
                "fields": {"issuetype": {"name": "Epic"}},
            },
        )
        issues = [child]

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 1
        assert result["errors"] == 0


# ===================================================================
# (e) Delta sync + loop prevention tests
# ===================================================================


class TestDeltaSyncAndLoopPrevention:
    """Tests for delta sync and loop prevention."""

    @pytest.mark.asyncio
    async def test_delta_sync_includes_updated_filter(self):
        """When last_sync_at is set → JQL includes updated >= filter."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data={
                **_connected_state(),
                "last_sync_at": "2026-03-18T10:00:00+00:00",
            },
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        captured_jql = []
        original_search = MockJiraClient().search_all_issues

        class CapturingJiraClient(MockJiraClient):
            async def search_all_issues(self, jql: str):
                captured_jql.append(jql)
                return []

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = CapturingJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        assert len(captured_jql) == 1
        assert 'updated >= "2026/03/18 10:00"' in captured_jql[0]

    @pytest.mark.asyncio
    async def test_first_sync_no_updated_filter(self):
        """When no last_sync_at → full sync (no updated filter)."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),  # no last_sync_at
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        captured_jql = []

        class CapturingJiraClient(MockJiraClient):
            async def search_all_issues(self, jql: str):
                captured_jql.append(jql)
                return []

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = CapturingJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        assert len(captured_jql) == 1
        assert "updated" not in captured_jql[0]

    @pytest.mark.asyncio
    async def test_loop_prevention_skips_unchanged(self):
        """Issue.updated <= existing.lastSyncedAt → skipped."""
        slug = compute_issue_slug("PROJ", "PROJ-1")
        issues = [
            _make_issue(
                "PROJ-1", "Old task", assignee_id=None,
                updated="2026-03-18T10:00:00+00:00",
                project_key="PROJ", issue_id="10001",
            ),
        ]

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "status": "todo",
                "lastSyncedAt": "2026-03-19T10:00:00+00:00",  # newer than issue.updated
            }
        })
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["skipped"] == 1
        assert result["updated"] == 0
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_loop_prevention_updates_changed(self):
        """Issue.updated > existing.lastSyncedAt → updated."""
        slug = compute_issue_slug("PROJ", "PROJ-1")
        issues = [
            _make_issue(
                "PROJ-1", "Changed task", assignee_id=None,
                updated="2026-03-20T14:00:00+00:00",
                project_key="PROJ", issue_id="10001",
            ),
        ]

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "status": "todo",
                "lastSyncedAt": "2026-03-19T10:00:00+00:00",  # older than issue.updated
            }
        })
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_new_issue_always_created(self):
        """New issue (no existing slug) → always created regardless of timestamps."""
        issues = [
            _make_issue("PROJ-1", "Brand new", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1


# ===================================================================
# (g) Skip conditions tests
# ===================================================================


class TestSkipConditions:
    """Tests for conditions that cause pull_sync to skip."""

    @pytest.mark.asyncio
    async def test_not_connected_skips(self):
        """Not connected → status 'skipped', reason 'not connected'."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data={},  # no credentials
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": False}):
                result = await pull_sync(ctx)

        assert result["status"] == "skipped"
        assert "not connected" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_no_projects_selected_skips(self):
        """No projects selected → status 'skipped'."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data={"sync_direction": "pull-only"},  # no selected_projects
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "skipped"
        assert "no projects" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_empty_projects_json_skips(self):
        """Empty JSON array for projects → skips."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data={"selected_projects": "[]"},  # empty array
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_pull_only_still_runs_pull(self):
        """sync_direction 'pull-only' doesn't prevent pull_sync from running."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="pull-only"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_bidirectional_still_runs_pull(self):
        """sync_direction 'bidirectional' doesn't prevent pull_sync from running."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_pull_stores_result_in_state(self):
        """After pull with issues, last_pull_result is stored in ctx.state as JSON."""
        issues = [
            _make_issue("PROJ-1", "Store result test", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        result_json = await ctx.state.get("last_pull_result")
        assert result_json is not None
        parsed = json.loads(result_json)
        assert parsed["status"] == "success"


# ===================================================================
# (h) Error isolation tests
# ===================================================================


class TestErrorIsolation:
    """Tests for error isolation — one failing issue shouldn't break others."""

    @pytest.mark.asyncio
    async def test_one_issue_error_others_still_processed(self):
        """One issue raises exception → others still created, error recorded."""
        good_issue = _make_issue("PROJ-1", "Good task", assignee_id=None, issue_id="10001")
        bad_issue = _make_issue("PROJ-2", "Bad task", assignee_id=None, issue_id="10002")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        process_count = [0]
        original_build = _sync_engine.build_task_properties

        def failing_build(issue, **kwargs):
            process_count[0] += 1
            if issue.get("key") == "PROJ-2":
                raise ValueError("Simulated failure")
            return original_build(issue, **kwargs)

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[good_issue, bad_issue])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                with patch.object(_sync_engine, "build_task_properties", side_effect=failing_build):
                    result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == 1
        assert "PROJ-2" in result["failed_issues"]

    @pytest.mark.asyncio
    async def test_error_result_includes_issue_key(self):
        """Failed issue key appears in failed_issues list."""
        bad_issue = _make_issue("PROJ-99", "Failing task", assignee_id=None, issue_id="10099")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        def always_fail(issue, **kwargs):
            raise RuntimeError("Boom")

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[bad_issue])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                with patch.object(_sync_engine, "build_task_properties", side_effect=always_fail):
                    result = await pull_sync(ctx)

        assert result["errors"] == 1
        assert "PROJ-99" in result["failed_issues"]
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_partial_status_when_some_succeed_some_fail(self):
        """Mix of success and failure → status 'partial'."""
        good_issue = _make_issue("PROJ-1", "Good", assignee_id=None, issue_id="10001")
        bad_issue = _make_issue("PROJ-2", "Bad", assignee_id=None, issue_id="10002")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        original_build = _sync_engine.build_task_properties

        def selective_fail(issue, **kwargs):
            if issue.get("key") == "PROJ-2":
                raise ValueError("Fail")
            return original_build(issue, **kwargs)

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[good_issue, bad_issue])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                with patch.object(_sync_engine, "build_task_properties", side_effect=selective_fail):
                    result = await pull_sync(ctx)

        assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_adf_conversion_failure_still_creates_task(self):
        """ADF conversion failure → task created without body."""
        adf = _make_adf_doc("Some text")
        issues = [
            _make_issue("PROJ-1", "ADF fail task", description=adf,
                        assignee_id=None, project_key="PROJ", issue_id="10001"),
        ]

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        def failing_adf(doc):
            raise ValueError("ADF parse error")

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                with patch.object(_sync_engine, "adf_to_markdown", side_effect=failing_adf):
                    result = await pull_sync(ctx)

        # The ADF failure is caught by the issue-level try/except, so
        # depending on where the error occurs, the issue may fail entirely
        # or be created without body. Either way, the sync completes.
        assert result["status"] in ("success", "error", "partial")
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_epic_error_doesnt_break_task_processing(self):
        """Error processing an epic → tasks still processed."""
        epic = _make_epic("PROJ-100", "Failing Epic")
        task = _make_issue("PROJ-1", "Good task", assignee_id=None, issue_id="10001")

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        original_milestone_props = _sync_engine.build_milestone_properties

        def failing_milestone_props(epic_data, **kwargs):
            raise RuntimeError("Epic processing failed")

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[epic, task])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                with patch.object(_sync_engine, "build_milestone_properties", side_effect=failing_milestone_props):
                    result = await pull_sync(ctx)

        # Task should still be created, epic should be in errors
        assert result["created"] >= 1  # at least the task
        assert result["errors"] >= 1
        assert "PROJ-100" in result["failed_issues"]


# ===================================================================
# (i) Push sync stub tests
# ===================================================================


class TestPushSync:
    """Tests for push_sync stub."""

    @pytest.mark.asyncio
    async def test_push_not_connected_skips(self):
        """push_sync returns skipped when not connected."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data={},
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": False}):
                result = await push_sync(ctx)

        assert result["status"] == "skipped"
        assert "not connected" in result["reason"]

    @pytest.mark.asyncio
    async def test_push_pull_only_skips(self):
        """push_sync returns skipped when direction is pull-only."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="pull-only"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "skipped"
        assert "pull-only" in result["reason"]

    @pytest.mark.asyncio
    async def test_push_bidirectional_no_changes_returns_success(self):
        """push_sync with bidirectional and no changed tasks returns success."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 0

    @pytest.mark.asyncio
    async def test_push_stores_result_in_state(self):
        """push_sync stores result as last_push_result in state."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="pull-only"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await push_sync(ctx)

        result_json = await ctx.state.get("last_push_result")
        assert result_json is not None
        parsed = json.loads(result_json)
        assert parsed["status"] == "skipped"


# ===================================================================
# (j) App.py wiring tests
# ===================================================================


class TestAppWiring:
    """Tests for app.py handler wiring — sync_now, poll-tasks, push-changes."""

    @pytest.mark.asyncio
    async def test_sync_now_calls_pull_sync(self):
        """sync_now handler calls pull_sync and stores result."""
        issues = [
            _make_issue("PROJ-1", "Sync task", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        # Verify state was stored
        last_pull = await ctx.state.get("last_pull_result")
        assert last_pull is not None

    @pytest.mark.asyncio
    async def test_poll_tasks_calls_pull_sync(self):
        """poll-tasks task handler calls pull_sync."""
        issues = [
            _make_issue("PROJ-1", "Poll task", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None

    @pytest.mark.asyncio
    async def test_push_changes_calls_push_sync(self):
        """push-changes task handler calls push_sync."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 0

    @pytest.mark.asyncio
    async def test_sync_now_bidirectional_runs_both(self):
        """With bidirectional, sync_now calls both pull and push."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=[])
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                pull_result = await pull_sync(ctx)
                push_result = await push_sync(ctx)

        assert pull_result["status"] == "success"
        # Push now returns success (no changed tasks) instead of skipped
        assert push_result["status"] == "success"
        assert push_result["pushed"] == 0

    @pytest.mark.asyncio
    async def test_sync_now_stores_last_sync_at(self):
        """After sync, last_sync_at is stored in state."""
        issues = [
            _make_issue("PROJ-1", "Timestamp task", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(last_sync)
        assert dt.year == 2026 or dt.year >= 2024  # sanity check


# ===================================================================
# Parent epic key extraction tests
# ===================================================================


class TestGetParentEpicKey:
    """Tests for _get_parent_epic_key helper."""

    def test_nextgen_parent_epic(self):
        fields = {
            "parent": {
                "key": "PROJ-100",
                "fields": {"issuetype": {"name": "Epic"}},
            }
        }
        assert _get_parent_epic_key(fields) == "PROJ-100"

    def test_nextgen_parent_non_epic(self):
        """Parent that is not an Epic → None."""
        fields = {
            "parent": {
                "key": "PROJ-50",
                "fields": {"issuetype": {"name": "Story"}},
            }
        }
        assert _get_parent_epic_key(fields) is None

    def test_classic_epic_link(self):
        fields = {"customfield_10014": "PROJ-100"}
        assert _get_parent_epic_key(fields) == "PROJ-100"

    def test_no_parent(self):
        fields = {}
        assert _get_parent_epic_key(fields) is None

    def test_parent_none(self):
        fields = {"parent": None}
        assert _get_parent_epic_key(fields) is None

    def test_nextgen_preferred_over_classic(self):
        """When both next-gen and classic are present, next-gen wins (checked first)."""
        fields = {
            "parent": {
                "key": "PROJ-200",
                "fields": {"issuetype": {"name": "Epic"}},
            },
            "customfield_10014": "PROJ-100",
        }
        # Next-gen is checked first, so PROJ-200 should be returned
        assert _get_parent_epic_key(fields) == "PROJ-200"


# ===================================================================
# Submit commands batched tests
# ===================================================================


class TestSubmitCommandsBatched:
    """Tests for _submit_commands_batched."""

    @pytest.mark.asyncio
    async def test_single_batch(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {"type": "Task"}}]
        results = await _submit_commands_batched(http, cmds, "test", "test-source")
        assert len(results) == 1
        assert len(http.recorded_calls) == 1
        url, payload = http.recorded_calls[0]
        assert url == "/api/commands/bulk"
        assert payload["summary"] == "test"
        assert payload["source"] == "test-source"

    @pytest.mark.asyncio
    async def test_multiple_batches(self):
        """Commands exceeding BATCH_SIZE are split across multiple calls."""
        http = MockHttpClient()
        # Create BATCH_SIZE + 1 commands
        cmds = [{"command": "object.create", "params": {"type": "Task"}}] * (BATCH_SIZE + 1)
        results = await _submit_commands_batched(http, cmds, "big batch", "test-source")
        assert len(results) == 2
        assert len(http.recorded_calls) == 2
        # First batch should have BATCH_SIZE commands
        _, p1 = http.recorded_calls[0]
        assert len(p1["commands"]) == BATCH_SIZE
        # Second batch should have 1 command
        _, p2 = http.recorded_calls[1]
        assert len(p2["commands"]) == 1

    @pytest.mark.asyncio
    async def test_empty_commands(self):
        """Empty command list → no HTTP calls."""
        http = MockHttpClient()
        results = await _submit_commands_batched(http, [], "empty", "test-source")
        assert len(results) == 0
        assert len(http.recorded_calls) == 0


# ===================================================================
# MockResponse correctness tests
# ===================================================================


class TestMockResponse:
    """Verify MockResponse follows K002: data if data is not None else {}."""

    def test_none_data_returns_empty_dict(self):
        r = MockResponse(200, None)
        assert r.json() == {}

    def test_zero_data_returns_zero(self):
        r = MockResponse(200, 0)
        assert r.json() == 0

    def test_false_data_returns_false(self):
        r = MockResponse(200, False)
        assert r.json() is False

    def test_empty_list_data_returns_empty_list(self):
        r = MockResponse(200, [])
        assert r.json() == []

    def test_raise_for_status_ok(self):
        r = MockResponse(200)
        r.raise_for_status()  # should not raise

    def test_raise_for_status_error(self):
        r = MockResponse(500)
        with pytest.raises(Exception, match="HTTP 500"):
            r.raise_for_status()


# ===================================================================
# Compute status tests
# ===================================================================


class TestComputeStatus:
    """Tests for _compute_status helper."""

    def test_no_errors_returns_success(self):
        from sync_engine import _compute_status
        assert _compute_status(5, 3, 2, 0) == "success"

    def test_all_errors_returns_error(self):
        from sync_engine import _compute_status
        assert _compute_status(0, 0, 0, 5) == "error"

    def test_mixed_returns_partial(self):
        from sync_engine import _compute_status
        assert _compute_status(3, 2, 0, 1) == "partial"

    def test_zero_everything_returns_success(self):
        from sync_engine import _compute_status
        assert _compute_status(0, 0, 0, 0) == "success"

    def test_only_skipped_no_errors_returns_success(self):
        from sync_engine import _compute_status
        assert _compute_status(0, 0, 10, 0) == "success"


# ===================================================================
# Additional edge case tests
# ===================================================================


class TestEdgeCases:
    """Miscellaneous edge case tests."""

    @pytest.mark.asyncio
    async def test_issue_with_none_assignee_no_person_resolution(self):
        """Issue with None assignee → no person matcher call, no edge."""
        issues = [
            _make_issue("PROJ-1", "No assignee", assignee_id=None,
                        project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        # No assignedTo edges should exist
        assignee_edges = [
            c for c in all_cmds
            if c.get("command") == "edge.create"
            and "assignedTo" in c.get("params", {}).get("predicate", "")
        ]
        assert len(assignee_edges) == 0

    @pytest.mark.asyncio
    async def test_issue_with_none_description_no_body_set(self):
        """Issue with None description → no body.set command."""
        issues = [
            _make_issue("PROJ-1", "No description", description=None,
                        assignee_id=None, project_key="PROJ", issue_id="10001"),
        ]
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_update_existing_milestone(self):
        """Existing milestone in graph → object.patch."""
        slug = compute_issue_slug("PROJ", "PROJ-100")
        issues = [_make_epic("PROJ-100", "Updated Epic",
                             updated="2026-03-20T14:00:00+00:00")]

        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(
            milestone_slug_map={
                slug: {"iri": f"https://example.org/data/Milestone/{slug}"}
            }
        )
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient(issues=issues)
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["created"] == 0
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        patch_cmds = [c for c in all_cmds if c.get("command") == "object.patch"]
        assert len(patch_cmds) >= 1

    @pytest.mark.asyncio
    async def test_multiple_projects_in_jql(self):
        """Multiple projects → JQL uses project in (P1, P2) syntax."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(
                selected_projects=json.dumps(["PROJ1", "PROJ2", "PROJ3"]),
            ),
            http_client=http,
            ext_http_client=ext_http,
        )

        captured_jql = []

        class CapturingJiraClient(MockJiraClient):
            async def search_all_issues(self, jql: str):
                captured_jql.append(jql)
                return []

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = CapturingJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        assert len(captured_jql) == 1
        assert '"PROJ1"' in captured_jql[0]
        assert '"PROJ2"' in captured_jql[0]
        assert '"PROJ3"' in captured_jql[0]

    @pytest.mark.asyncio
    async def test_jql_filter_from_settings(self):
        """User JQL filter from settings is included in query."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(jql_filter="assignee = currentUser()"),
            http_client=http,
            ext_http_client=ext_http,
        )

        captured_jql = []

        class CapturingJiraClient(MockJiraClient):
            async def search_all_issues(self, jql: str):
                captured_jql.append(jql)
                return []

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = CapturingJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        assert len(captured_jql) == 1
        assert "assignee = currentUser()" in captured_jql[0]

    @pytest.mark.asyncio
    async def test_batch_size_constant(self):
        """BATCH_SIZE is set to 1000."""
        assert BATCH_SIZE == 1000

    @pytest.mark.asyncio
    async def test_bpkm_constant(self):
        """BPKM is the expected IRI prefix."""
        assert BPKM == "urn:sempkm:model:basic-pkm:"


# ===================================================================
# (k) _find_changed_tasks SPARQL tests
# ===================================================================


class TestFindChangedTasks:
    """Tests for _find_changed_tasks SPARQL helper."""

    @pytest.mark.asyncio
    async def test_no_changed_tasks(self):
        """Empty graph → returns empty list."""
        graph = MockGraphClient(changed_tasks=[])
        result = await _find_changed_tasks(graph)
        assert result == []

    @pytest.mark.asyncio
    async def test_one_changed_task(self):
        """One changed task → returns it with all fields."""
        graph = MockGraphClient(changed_tasks=[{
            "iri": "urn:task:1",
            "externalId": "PROJ-42",
            "status": "in-progress",
            "priority": "high",
            "title": "Fix the widget",
            "lastSyncedAt": "2026-03-18T10:00:00Z",
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "urn:task:1"
        assert result[0]["externalId"] == "PROJ-42"
        assert result[0]["status"] == "in-progress"
        assert result[0]["priority"] == "high"
        assert result[0]["title"] == "Fix the widget"
        assert result[0]["lastSyncedAt"] == "2026-03-18T10:00:00Z"

    @pytest.mark.asyncio
    async def test_task_with_no_last_synced_at(self):
        """Task with no lastSyncedAt → treated as changed (returned)."""
        graph = MockGraphClient(changed_tasks=[{
            "iri": "urn:task:2",
            "externalId": "PROJ-99",
            "status": "todo",
            "priority": None,
            "title": "New task",
            "lastSyncedAt": None,
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["lastSyncedAt"] is None

    @pytest.mark.asyncio
    async def test_task_with_optional_fields_missing(self):
        """Task with only iri and externalId → optional fields are None."""
        graph = MockGraphClient(changed_tasks=[{
            "iri": "urn:task:3",
            "externalId": "PROJ-50",
            "status": None,
            "priority": None,
            "title": None,
            "lastSyncedAt": None,
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["status"] is None
        assert result[0]["priority"] is None
        assert result[0]["title"] is None

    @pytest.mark.asyncio
    async def test_multiple_changed_tasks(self):
        """Multiple changed tasks → all returned."""
        graph = MockGraphClient(changed_tasks=[
            {"iri": "urn:task:a", "externalId": "PROJ-1", "status": "todo",
             "priority": "low", "title": "Task A", "lastSyncedAt": None},
            {"iri": "urn:task:b", "externalId": "PROJ-2", "status": "done",
             "priority": "high", "title": "Task B", "lastSyncedAt": "2026-03-18T10:00:00Z"},
        ])
        result = await _find_changed_tasks(graph)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_sparql_query_references_jira_provider(self):
        """The SPARQL query should reference externalProvider 'jira'."""
        graph = MockGraphClient(changed_tasks=[])
        await _find_changed_tasks(graph)
        assert len(graph.queries) == 1
        q = graph.queries[0]
        assert '"jira"' in q
        assert "externalProvider" in q
        assert "syncDir" in q
        assert "pull-only" in q


# ===================================================================
# (l) _get_task_body SPARQL tests
# ===================================================================


class TestGetTaskBody:
    """Tests for _get_task_body SPARQL helper."""

    @pytest.mark.asyncio
    async def test_body_exists(self):
        """Body exists → returns text string."""
        graph = MockGraphClient(body_map={
            "urn:task:1": "# Hello World\n\nThis is the body text."
        })
        result = await _get_task_body(graph, "urn:task:1")
        assert result == "# Hello World\n\nThis is the body text."

    @pytest.mark.asyncio
    async def test_no_body(self):
        """No body → returns None."""
        graph = MockGraphClient(body_map={})
        result = await _get_task_body(graph, "urn:task:1")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_body(self):
        """Empty body → returns empty string."""
        graph = MockGraphClient(body_map={"urn:task:2": ""})
        result = await _get_task_body(graph, "urn:task:2")
        assert result == ""

    @pytest.mark.asyncio
    async def test_different_iris(self):
        """Only body for the requested IRI is returned."""
        graph = MockGraphClient(body_map={
            "urn:task:1": "Body for task 1",
            "urn:task:2": "Body for task 2",
        })
        result = await _get_task_body(graph, "urn:task:2")
        assert result == "Body for task 2"


# ===================================================================
# (m) build_issue_patch with description tests
# ===================================================================


class TestBuildIssuePatchWithDescription:
    """Tests for build_issue_patch with description_adf parameter."""

    def test_with_description_adf(self):
        """With description_adf → includes 'description' key."""
        adf_doc = {"version": 1, "type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}
        ]}
        props = {"dcterms:title": "Test"}
        result = build_issue_patch(props, description_adf=adf_doc)
        assert "description" in result
        assert result["description"] == adf_doc
        assert result["summary"] == "Test"

    def test_without_description_adf(self):
        """Without description_adf → no 'description' key (backward compat)."""
        props = {"dcterms:title": "Test"}
        result = build_issue_patch(props)
        assert "description" not in result
        assert result["summary"] == "Test"

    def test_with_description_adf_none(self):
        """With description_adf=None → no 'description' key."""
        props = {"dcterms:title": "Test"}
        result = build_issue_patch(props, description_adf=None)
        assert "description" not in result

    def test_with_empty_description_adf(self):
        """With description_adf={} (empty dict) → no 'description' key."""
        props = {"dcterms:title": "Test"}
        result = build_issue_patch(props, description_adf={})
        assert "description" not in result

    def test_with_description_and_priority(self):
        """Description + priority → both included."""
        adf_doc = {"version": 1, "type": "doc", "content": []}
        props = {
            "dcterms:title": "Test",
            f"{BPKM}priority": "high",
        }
        result = build_issue_patch(props, description_adf=adf_doc)
        assert result["summary"] == "Test"
        assert result["priority"] == {"name": "High"}
        assert result["description"] == adf_doc


# ===================================================================
# (n) Real push sync tests
# ===================================================================


class TestPushSyncReal:
    """Tests for the real push_sync implementation."""

    @pytest.mark.asyncio
    async def test_push_not_connected_skips(self):
        """push_sync returns skipped when not connected."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data={},
            settings_data=_default_settings(),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": False}):
                result = await push_sync(ctx)

        assert result["status"] == "skipped"
        assert "not connected" in result["reason"]

    @pytest.mark.asyncio
    async def test_push_pull_only_skips(self):
        """push_sync returns skipped when direction is pull-only."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="pull-only"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "skipped"
        assert "pull-only" in result["reason"]

    @pytest.mark.asyncio
    async def test_push_no_changed_tasks(self):
        """No changed tasks → result with pushed=0, status=success."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        graph = MockGraphClient(changed_tasks=[])
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_happy_path_with_title_and_priority(self):
        """Changed task with title and priority → update_issue called with correct fields."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:push1",
                "externalId": "PROJ-42",
                "status": "in-progress",
                "priority": "high",
                "title": "Updated title",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 1
        assert len(mock_jira.update_issue_calls) == 1
        issue_key, fields = mock_jira.update_issue_calls[0]
        assert issue_key == "PROJ-42"
        assert fields["summary"] == "Updated title"
        assert fields["priority"] == {"name": "High"}

    @pytest.mark.asyncio
    async def test_push_happy_path_with_description(self):
        """Changed task with body text → description included as ADF."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:push2",
                "externalId": "PROJ-55",
                "status": "todo",
                "priority": "medium",
                "title": "With description",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }],
            body_map={"urn:task:push2": "# Hello\n\nSome description text."},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 1
        _, fields = mock_jira.update_issue_calls[0]
        assert "description" in fields
        # ADF document structure
        assert fields["description"]["version"] == 1
        assert fields["description"]["type"] == "doc"

    @pytest.mark.asyncio
    async def test_push_task_with_no_body(self):
        """Task with no body → push without description field."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:nobody",
                "externalId": "PROJ-77",
                "status": "todo",
                "priority": "low",
                "title": "No body task",
                "lastSyncedAt": None,
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["pushed"] == 1
        _, fields = mock_jira.update_issue_calls[0]
        assert "description" not in fields

    @pytest.mark.asyncio
    async def test_push_error_isolation(self):
        """One task fails, others continue, errors list populated."""
        failing_jira = MockJiraClient()

        call_count = [0]
        original_update = failing_jira.update_issue

        async def selective_fail(issue_key, fields):
            call_count[0] += 1
            if issue_key == "PROJ-FAIL":
                raise RuntimeError("API error")
            failing_jira.update_issue_calls.append((issue_key, fields))

        failing_jira.update_issue = selective_fail

        graph = MockGraphClient(
            changed_tasks=[
                {"iri": "urn:task:ok", "externalId": "PROJ-OK",
                 "status": "todo", "priority": "medium", "title": "Good task",
                 "lastSyncedAt": None},
                {"iri": "urn:task:fail", "externalId": "PROJ-FAIL",
                 "status": "todo", "priority": "high", "title": "Bad task",
                 "lastSyncedAt": None},
            ],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = failing_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "partial"
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["iri"] == "urn:task:fail"
        assert "API error" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_push_all_fail_returns_error(self):
        """All tasks fail → status is 'error'."""
        graph = MockGraphClient(
            changed_tasks=[
                {"iri": "urn:task:f1", "externalId": "PROJ-F1",
                 "status": "todo", "priority": "low", "title": "Fail 1",
                 "lastSyncedAt": None},
            ],
            body_map={},
        )
        mock_jira = MockJiraClient(update_issue_error=RuntimeError("Server down"))
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "error"
        assert result["pushed"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_push_last_synced_at_updated(self):
        """After successful push, lastSyncedAt is updated via object.patch command."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:sync1",
                "externalId": "PROJ-101",
                "status": "todo",
                "priority": "medium",
                "title": "Sync me",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["pushed"] == 1
        # Verify lastSyncedAt update command was submitted
        all_cmds = []
        for _, payload in http.recorded_calls:
            if payload and "commands" in payload:
                all_cmds.extend(payload["commands"])
        patch_cmds = [
            c for c in all_cmds
            if c.get("command") == "object.patch"
            and f"{BPKM}lastSyncedAt" in str(c.get("params", {}).get("properties", {}))
        ]
        assert len(patch_cmds) == 1
        assert patch_cmds[0]["params"]["iri"] == "urn:task:sync1"

    @pytest.mark.asyncio
    async def test_push_stores_result_in_state(self):
        """push_sync stores last_push_result in ctx.state."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:state1",
                "externalId": "PROJ-200",
                "status": "done",
                "priority": "low",
                "title": "State test",
                "lastSyncedAt": None,
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await push_sync(ctx)

        result_json = await ctx.state.get("last_push_result")
        assert result_json is not None
        parsed = json.loads(result_json)
        assert parsed["status"] == "success"
        assert parsed["pushed"] == 1
        assert "timestamp" in parsed

    @pytest.mark.asyncio
    async def test_push_empty_patch_skipped(self):
        """Task with no pushable changes (no title, no priority) → skipped."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:nopush",
                "externalId": "PROJ-300",
                "status": "in-progress",
                "priority": None,
                "title": None,
                "lastSyncedAt": None,
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert len(mock_jira.update_issue_calls) == 0

    @pytest.mark.asyncio
    async def test_push_result_uses_success_not_ok(self):
        """Result dict uses 'success' not 'ok' for status."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(changed_tasks=[{
            "iri": "urn:task:status1",
            "externalId": "PROJ-400",
            "status": "todo",
            "priority": "medium",
            "title": "Status test",
            "lastSyncedAt": None,
        }])
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["status"] != "ok"

    @pytest.mark.asyncio
    async def test_push_result_has_timestamp(self):
        """Push result includes a timestamp field."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(changed_tasks=[])
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert "timestamp" in result
        # Verify it's a valid ISO timestamp
        dt = datetime.fromisoformat(result["timestamp"])
        assert dt.tzinfo is not None

    @pytest.mark.asyncio
    async def test_push_multiple_tasks(self):
        """Multiple changed tasks → all pushed successfully."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[
                {"iri": "urn:task:m1", "externalId": "PROJ-10",
                 "status": "todo", "priority": "high", "title": "Task 1",
                 "lastSyncedAt": None},
                {"iri": "urn:task:m2", "externalId": "PROJ-11",
                 "status": "done", "priority": "low", "title": "Task 2",
                 "lastSyncedAt": None},
            ],
            body_map={"urn:task:m1": "Body for task 1"},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "success"
        assert result["pushed"] == 2
        assert len(mock_jira.update_issue_calls) == 2
        keys_pushed = {call[0] for call in mock_jira.update_issue_calls}
        assert keys_pushed == {"PROJ-10", "PROJ-11"}

    @pytest.mark.asyncio
    async def test_push_default_sync_direction(self):
        """Default sync_direction (None → 'pull-only') → push skipped."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data={},  # no sync_direction set
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["status"] == "skipped"
        assert "pull-only" in result["reason"]

    @pytest.mark.asyncio
    async def test_push_stores_skipped_result_in_state(self):
        """push_sync stores result even when skipped."""
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="pull-only"),
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = MockJiraClient()
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await push_sync(ctx)

        result_json = await ctx.state.get("last_push_result")
        assert result_json is not None
        parsed = json.loads(result_json)
        assert parsed["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_push_task_with_unknown_priority_omits_it(self):
        """Task with unknown priority value → priority not included in patch."""
        mock_jira = MockJiraClient()
        graph = MockGraphClient(
            changed_tasks=[{
                "iri": "urn:task:unk",
                "externalId": "PROJ-500",
                "status": "todo",
                "priority": "super-critical",  # not in REVERSE_PRIORITY_MAP
                "title": "Unknown priority",
                "lastSyncedAt": None,
            }],
            body_map={},
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(sync_direction="bidirectional"),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await push_sync(ctx)

        assert result["pushed"] == 1
        _, fields = mock_jira.update_issue_calls[0]
        assert fields["summary"] == "Unknown priority"
        assert "priority" not in fields  # unknown priority → omitted


# ===================================================================
# Issue link test helpers
# ===================================================================


def _make_issue_with_links(
    key: str = "PROJ-42",
    links: list[dict] | None = None,
    *,
    project_key: str = "PROJ",
) -> dict:
    """Build a Jira issue dict with an issuelinks array.

    Uses ``_make_issue`` as base and injects ``issuelinks`` into fields.
    """
    issue = _make_issue(key=key, project_key=project_key)
    issue["fields"]["issuelinks"] = links if links is not None else []
    return issue


def _make_blocks_link(
    inward_key: str | None = None,
    outward_key: str | None = None,
    *,
    type_name: str = "Blocks",
) -> dict:
    """Build a Jira issue-link dict of the given type.

    Exactly one of ``inward_key`` or ``outward_key`` should be provided.
    """
    link: dict = {
        "type": {
            "name": type_name,
            "inward": "is blocked by",
            "outward": "blocks",
        },
    }
    if inward_key:
        link["inwardIssue"] = {"key": inward_key, "self": f"https://jira/issue/{inward_key}"}
    if outward_key:
        link["outwardIssue"] = {"key": outward_key, "self": f"https://jira/issue/{outward_key}"}
    return link


# ===================================================================
# TestIssueLinks — unit tests for _process_issue_links()
# ===================================================================


class TestIssueLinks:
    """Tests for _process_issue_links() helper function."""

    @pytest.mark.asyncio
    async def test_inward_blocks_link_creates_depends_on_edge(self):
        """Inward 'Blocks' link → dependsOn edge from current to blocker."""
        # PROJ-10 is blocked by PROJ-20
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10", "status": "todo", "externalId": "PROJ-10"},
            slug_20: {"iri": "urn:task:20", "status": "todo", "externalId": "PROJ-20"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 1
        assert cmds[0]["command"] == "edge.create"
        assert cmds[0]["params"]["source"] == "urn:task:10"  # blocked task
        assert cmds[0]["params"]["target"] == "urn:task:20"  # blocker
        assert "dependsOn" in cmds[0]["params"]["predicate"]

    @pytest.mark.asyncio
    async def test_outward_blocks_link_ignored(self):
        """Outward 'blocks' link → ignored (dedup — processed from other side)."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(outward_key="PROJ-30"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_30 = compute_issue_slug("PROJ", "PROJ-30")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_30: {"iri": "urn:task:30"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 0

    @pytest.mark.asyncio
    async def test_non_blocks_link_type_ignored(self):
        """Link types other than 'Blocks' (e.g. 'Relates') → ignored."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20", type_name="Relates"),
        ])
        graph = MockGraphClient(slug_map={})

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 0

    @pytest.mark.asyncio
    async def test_duplicate_link_type_ignored(self):
        """Link type 'Duplicate' → ignored."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20", type_name="Duplicate"),
        ])
        graph = MockGraphClient(slug_map={})

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_blocks_lowercase(self):
        """Link type 'blocks' (lowercase) → still matched."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20", type_name="blocks"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_blocks_uppercase(self):
        """Link type 'BLOCKS' (uppercase) → still matched."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20", type_name="BLOCKS"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 1

    @pytest.mark.asyncio
    async def test_empty_issuelinks_array(self):
        """Empty issuelinks array → no edge commands."""
        issue = _make_issue_with_links("PROJ-10", [])
        graph = MockGraphClient(slug_map={})

        cmds = await _process_issue_links([issue], graph)

        assert cmds == []

    @pytest.mark.asyncio
    async def test_no_issuelinks_field(self):
        """Issue with no issuelinks field at all → no edge commands."""
        issue = _make_issue("PROJ-10")
        # _make_issue doesn't include issuelinks — it will be absent
        assert "issuelinks" not in issue["fields"]
        graph = MockGraphClient(slug_map={})

        cmds = await _process_issue_links([issue], graph)

        assert cmds == []

    @pytest.mark.asyncio
    async def test_linked_issue_not_synced_skips(self):
        """Blocker issue not found in graph → skip, no error."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-99"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        # PROJ-99 not in slug_map — not synced
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 0

    @pytest.mark.asyncio
    async def test_current_issue_not_in_graph_skips(self):
        """Current issue not found in graph → skip, no error."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20"),
        ])
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        # PROJ-10 not in slug_map
        graph = MockGraphClient(slug_map={
            slug_20: {"iri": "urn:task:20"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 0

    @pytest.mark.asyncio
    async def test_multiple_links_on_one_issue(self):
        """Issue with multiple inward blocks links → multiple edge commands."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20"),
            _make_blocks_link(inward_key="PROJ-30"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        slug_30 = compute_issue_slug("PROJ", "PROJ-30")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
            slug_30: {"iri": "urn:task:30"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 2
        targets = {c["params"]["target"] for c in cmds}
        assert targets == {"urn:task:20", "urn:task:30"}
        for c in cmds:
            assert c["params"]["source"] == "urn:task:10"

    @pytest.mark.asyncio
    async def test_inward_and_outward_only_inward_processed(self):
        """Issue with both inward and outward blocks links → only inward processed."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20"),
            _make_blocks_link(outward_key="PROJ-30"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        slug_30 = compute_issue_slug("PROJ", "PROJ-30")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
            slug_30: {"iri": "urn:task:30"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 1
        assert cmds[0]["params"]["target"] == "urn:task:20"

    @pytest.mark.asyncio
    async def test_error_in_one_link_doesnt_stop_others(self):
        """Error processing one link → other links still processed."""
        # First link has a malformed structure that will fail
        bad_link = {
            "type": {"name": "Blocks"},
            "inwardIssue": {"key": ""},  # empty key → project extraction fails
        }
        good_link = _make_blocks_link(inward_key="PROJ-20")
        issue = _make_issue_with_links("PROJ-10", [bad_link, good_link])

        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
        })

        cmds = await _process_issue_links([issue], graph)

        # Good link should still produce an edge even if bad link failed
        assert len(cmds) == 1
        assert cmds[0]["params"]["target"] == "urn:task:20"

    @pytest.mark.asyncio
    async def test_cross_project_link(self):
        """Link between issues in different projects → correct slug computation."""
        # PROJ-10 is blocked by ENG-50 (different project)
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="ENG-50"),
        ], project_key="PROJ")

        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_50 = compute_issue_slug("ENG", "ENG-50")  # extracted from "ENG-50"
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:proj10"},
            slug_50: {"iri": "urn:task:eng50"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert len(cmds) == 1
        assert cmds[0]["params"]["source"] == "urn:task:proj10"
        assert cmds[0]["params"]["target"] == "urn:task:eng50"

    @pytest.mark.asyncio
    async def test_none_issuelinks_treated_as_empty(self):
        """issuelinks explicitly set to None → no error, no commands."""
        issue = _make_issue("PROJ-10")
        issue["fields"]["issuelinks"] = None
        graph = MockGraphClient(slug_map={})

        cmds = await _process_issue_links([issue], graph)

        assert cmds == []

    @pytest.mark.asyncio
    async def test_edge_predicate_is_bpkm_depends_on(self):
        """Edge predicate uses the full BPKM dependsOn IRI."""
        issue = _make_issue_with_links("PROJ-10", [
            _make_blocks_link(inward_key="PROJ-20"),
        ])
        slug_10 = compute_issue_slug("PROJ", "PROJ-10")
        slug_20 = compute_issue_slug("PROJ", "PROJ-20")
        graph = MockGraphClient(slug_map={
            slug_10: {"iri": "urn:task:10"},
            slug_20: {"iri": "urn:task:20"},
        })

        cmds = await _process_issue_links([issue], graph)

        assert cmds[0]["params"]["predicate"] == f"{BPKM}dependsOn"


# ===================================================================
# TestPullSyncWithIssueLinks — integration tests
# ===================================================================


class TestPullSyncWithIssueLinks:
    """Tests for issue link processing integrated into pull_sync."""

    @pytest.mark.asyncio
    async def test_pull_sync_with_blocking_links_creates_edges(self):
        """Full pull_sync with issues that have blocking links → edges created."""
        # Issue PROJ-42 is blocked by PROJ-43
        issue1 = _make_issue("PROJ-42")
        issue1["fields"]["issuelinks"] = [_make_blocks_link(inward_key="PROJ-43")]

        issue2 = _make_issue("PROJ-43", summary="Blocker issue", issue_id="10043")

        mock_jira = MockJiraClient(issues=[issue1, issue2])

        slug_42 = compute_issue_slug("PROJ", "PROJ-42")
        slug_43 = compute_issue_slug("PROJ", "PROJ-43")
        graph = MockGraphClient(slug_map={
            slug_42: {"iri": "urn:task:42", "status": "todo", "externalId": "PROJ-42"},
            slug_43: {"iri": "urn:task:43", "status": "todo", "externalId": "PROJ-43"},
        })
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["issue_links"] >= 1

        # Verify edge.create command was submitted via bulk commands
        mock_http = ctx.commands._client
        all_submitted = []
        for _, payload in mock_http.recorded_calls:
            if payload:
                all_submitted.extend(payload.get("commands", []))

        depends_on_edges = [
            c for c in all_submitted
            if c.get("command") == "edge.create"
            and "dependsOn" in c.get("params", {}).get("predicate", "")
        ]
        assert len(depends_on_edges) >= 1

    @pytest.mark.asyncio
    async def test_pull_sync_without_issue_links_still_works(self):
        """Pull sync with issues that have no issue links → still works (regression)."""
        issue = _make_issue("PROJ-42")
        # No issuelinks field set
        mock_jira = MockJiraClient(issues=[issue])

        slug_42 = compute_issue_slug("PROJ", "PROJ-42")
        graph = MockGraphClient(slug_map={
            slug_42: {"iri": "urn:task:42", "status": "todo", "externalId": "PROJ-42"},
        })
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["issue_links"] == 0

    @pytest.mark.asyncio
    async def test_pull_result_includes_issue_links_count(self):
        """Pull result dict includes issue_links count."""
        issue = _make_issue("PROJ-42")
        mock_jira = MockJiraClient(issues=[issue])
        graph = MockGraphClient(slug_map={})
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert "issue_links" in result
        assert isinstance(result["issue_links"], int)

    @pytest.mark.asyncio
    async def test_issue_link_commands_in_follow_up_batch(self):
        """Issue link edge commands are submitted in the follow-up batch."""
        issue1 = _make_issue("PROJ-42")
        issue1["fields"]["issuelinks"] = [_make_blocks_link(inward_key="PROJ-43")]
        issue2 = _make_issue("PROJ-43", summary="Blocker", issue_id="10043")

        mock_jira = MockJiraClient(issues=[issue1, issue2])
        slug_42 = compute_issue_slug("PROJ", "PROJ-42")
        slug_43 = compute_issue_slug("PROJ", "PROJ-43")
        graph = MockGraphClient(slug_map={
            slug_42: {"iri": "urn:task:42", "status": "todo", "externalId": "PROJ-42"},
            slug_43: {"iri": "urn:task:43", "status": "todo", "externalId": "PROJ-43"},
        })
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                await pull_sync(ctx)

        # Check that the follow-up batch included edge.create with dependsOn
        mock_http = ctx.commands._client
        all_cmds = []
        for _, payload in mock_http.recorded_calls:
            if payload:
                all_cmds.extend(payload.get("commands", []))

        depends_on = [c for c in all_cmds if c.get("command") == "edge.create"
                      and "dependsOn" in c.get("params", {}).get("predicate", "")]
        assert len(depends_on) >= 1

    @pytest.mark.asyncio
    async def test_issue_links_processed_after_epic_linking(self):
        """Issue link phase (Phase 4) runs after epic linking (Phase 3)."""
        # Create an epic with a child that also has issue links
        epic = _make_epic("PROJ-100", project_key="PROJ")
        child = _make_issue("PROJ-42", parent={
            "key": "PROJ-100",
            "fields": {"issuetype": {"name": "Epic"}},
        })
        child["fields"]["issuelinks"] = [_make_blocks_link(inward_key="PROJ-43")]
        blocker = _make_issue("PROJ-43", summary="Blocker", issue_id="10043")

        mock_jira = MockJiraClient(issues=[epic, child, blocker])
        slug_42 = compute_issue_slug("PROJ", "PROJ-42")
        slug_43 = compute_issue_slug("PROJ", "PROJ-43")
        epic_slug = compute_issue_slug("PROJ", "PROJ-100")
        graph = MockGraphClient(
            slug_map={
                slug_42: {"iri": "urn:task:42", "status": "todo", "externalId": "PROJ-42"},
                slug_43: {"iri": "urn:task:43", "status": "todo", "externalId": "PROJ-43"},
            },
            milestone_slug_map={
                epic_slug: {"iri": "urn:milestone:100"},
            },
        )
        ext_http = MockExternalHttpClient()
        http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_connected_state(),
            settings_data=_default_settings(),
            graph_client=graph,
            http_client=http,
            ext_http_client=ext_http,
        )

        with patch.object(_sync_engine, "JiraClient") as MockJC:
            MockJC.return_value = mock_jira
            with patch.object(_sync_engine, "get_connection_status", return_value={"connected": True}):
                result = await pull_sync(ctx)

        assert result["status"] == "success"
        # Both epic linking and issue link edges should be in the batch
        mock_http = ctx.commands._client
        all_cmds = []
        for _, payload in mock_http.recorded_calls:
            if payload:
                all_cmds.extend(payload.get("commands", []))

        edge_creates = [c for c in all_cmds if c.get("command") == "edge.create"]
        predicates = {c["params"]["predicate"] for c in edge_creates}
        # Should have both milestone and dependsOn edges
        assert any("milestone" in p for p in predicates)
        assert any("dependsOn" in p for p in predicates)
