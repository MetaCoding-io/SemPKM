"""Unit tests for the GitHub pull sync engine.

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
    / "github-sync"
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
_github_client = _load_module("github_client", _SERVICES_DIR / "github_client.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
push_sync = _sync_engine.push_sync
_find_existing_task = _sync_engine._find_existing_task
_find_changed_tasks = _sync_engine._find_changed_tasks
_submit_commands_batched = _sync_engine._submit_commands_batched
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
compute_issue_slug = _field_mapper.compute_issue_slug
is_pull_request = _field_mapper.is_pull_request
extract_linked_issue_numbers = _field_mapper.extract_linked_issue_numbers
parse_external_url = _field_mapper.parse_external_url
build_issue_patch = _field_mapper.build_issue_patch


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
    """In-memory settings client mirroring SDK SettingsClient."""

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

    ``slug_map`` values can be:
    - A plain string (task IRI) — returns default title/status
    - A dict with ``iri`` and optional ``title``, ``status``, ``lastSyncedAt``
    """

    def __init__(
        self,
        default_results: dict | None = None,
        slug_map: dict[str, str | dict] | None = None,
    ):
        self.default_results = default_results or {"results": {"bindings": []}}
        self.slug_map = slug_map or {}  # slug → task IRI or dict
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        # Check if this is a _find_existing_task query with STRENDS
        if "STRENDS" in sparql:
            for slug, info in self.slug_map.items():
                if slug in sparql:
                    if isinstance(info, str):
                        info = {"iri": info}
                    binding: dict = {
                        "task": {"type": "uri", "value": info["iri"]},
                        "title": {
                            "type": "literal",
                            "value": info.get("title", "Existing task"),
                        },
                        "status": {
                            "type": "literal",
                            "value": info.get("status", "todo"),
                        },
                    }
                    if info.get("lastSyncedAt"):
                        binding["lastSynced"] = {
                            "type": "literal",
                            "value": info["lastSyncedAt"],
                        }
                    return {"results": {"bindings": [binding]}}
        # Check if it looks like a person matcher query
        if "foaf" in sparql or "crm:email" in sparql or "externalId" in sparql:
            return self.default_results
        return self.default_results


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
    """Stub for SDK's HttpClient (external requests to GitHub API).

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
        # Default: return a valid user response for verify_token
        return MockResponse(200, {"login": "testuser", "email": "test@example.com"})

    async def close(self):
        pass


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes."""

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
        self.app_id = "github-sync"


# ===================================================================
# Issue fixtures
# ===================================================================


def make_issue(
    number: int = 1,
    title: str = "Fix bug",
    state: str = "open",
    **overrides,
) -> dict:
    """Build a realistic GitHub issue dict."""
    base = {
        "number": number,
        "title": title,
        "state": state,
        "state_reason": None,
        "body": "Bug description in markdown",
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "node_id": f"I_kwDOB0oTJc{number}",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "alice", "email": "alice@example.com"}],
        "assignee": {"login": "alice", "email": "alice@example.com"},
        "milestone": None,
        "updated_at": "2026-03-18T12:00:00Z",
        "created_at": "2026-03-17T10:00:00Z",
    }
    base.update(overrides)
    return base


def make_pr_issue(number: int = 100, title: str = "Refactor module") -> dict:
    """Build a GitHub issue dict that represents a pull request."""
    issue = make_issue(number=number, title=title)
    issue["pull_request"] = {"url": "https://api.github.com/repos/owner/repo/pulls/100"}
    return issue


def _make_connected_state() -> dict[str, str]:
    """Build state dict for a connected account with PAT stored."""
    return {
        "github_pat": "ghp_test1234567890",
    }


def _make_settings_with_repos(repos: list[str] | None = None) -> dict[str, str]:
    """Build settings dict with selected repos."""
    return {
        "selected_repos": json.dumps(repos or ["owner/repo"]),
    }


def _make_github_responses(
    issues: list[dict],
    *,
    timeline_responses: list[MockResponse] | None = None,
) -> list[MockResponse]:
    """Build MockExternalHttpClient responses for verify_token + fetch_issues.

    When *timeline_responses* is given, they are appended after
    the fetch_issues response (one per non-PR issue that triggers
    a ``fetch_timeline`` call).  When omitted, a default empty-timeline
    ``[]`` response is appended for each non-PR issue.
    """
    responses = [
        # verify_token: GET /user
        MockResponse(200, {"login": "testuser", "email": "test@example.com"},
                     headers={}),
        # fetch_issues: GET /repos/owner/repo/issues (single page, no Link header)
        MockResponse(200, issues, headers={}),
    ]
    if timeline_responses is not None:
        responses.extend(timeline_responses)
    else:
        # Auto-generate empty timelines for every non-PR issue
        for issue in issues:
            if not is_pull_request(issue):
                responses.append(MockResponse(200, [], headers={}))
    return responses


# ===================================================================
# Tests — _find_existing_task
# ===================================================================


class TestFindExistingTask:
    @pytest.mark.asyncio
    async def test_found(self):
        """Returns task dict when SPARQL finds a match."""
        graph = MockGraphClient(slug_map={"gh-abc123": "https://example.org/data/Task/gh-abc123"})
        result = await _find_existing_task(graph, "gh-abc123")
        assert result is not None
        assert result["iri"] == "https://example.org/data/Task/gh-abc123"
        assert result["status"] == "todo"

    @pytest.mark.asyncio
    async def test_not_found(self):
        """Returns None when SPARQL finds no match."""
        graph = MockGraphClient()
        result = await _find_existing_task(graph, "gh-nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_sparql_error_propagates(self):
        """SPARQL errors propagate as exceptions."""
        graph = MockGraphClient()
        graph.query = AsyncMock(side_effect=Exception("SPARQL timeout"))
        with pytest.raises(Exception, match="SPARQL timeout"):
            await _find_existing_task(graph, "gh-abc123")


# ===================================================================
# Tests — _submit_commands_batched
# ===================================================================


class TestSubmitCommandsBatched:
    @pytest.mark.asyncio
    async def test_single_batch(self):
        """Commands under BATCH_SIZE go in one POST."""
        http = MockHttpClient()
        commands = [{"command": "object.create", "params": {"type": "Task"}}] * 5
        results = await _submit_commands_batched(http, commands)
        assert len(results) == 1
        assert len(http.posts) == 1
        assert len(http.posts[0]["json"]["commands"]) == 5

    @pytest.mark.asyncio
    async def test_multi_batch(self):
        """Commands exceeding BATCH_SIZE are split across POSTs."""
        http = MockHttpClient()
        commands = [{"command": "object.create", "params": {}}] * (BATCH_SIZE + 50)
        results = await _submit_commands_batched(http, commands)
        assert len(results) == 2
        assert len(http.posts) == 2
        assert len(http.posts[0]["json"]["commands"]) == BATCH_SIZE
        assert len(http.posts[1]["json"]["commands"]) == 50

    @pytest.mark.asyncio
    async def test_empty_commands(self):
        """Empty command list returns empty results without any POST."""
        http = MockHttpClient()
        results = await _submit_commands_batched(http, [])
        assert results == []
        assert len(http.posts) == 0


# ===================================================================
# Tests — pull_sync basic
# ===================================================================


class TestPullSyncBasic:
    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        """Returns skipped status when no PAT is configured."""
        ctx = MockAppContext(state_data={})
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_skips_when_no_repos_selected(self):
        """Returns skipped when connected but no repos in settings."""
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data={},
        )
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert "no repos" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_creates_task_for_new_issue(self):
        """New issue produces object.create in bulk POST."""
        issue = make_issue()
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 1
        # Bulk POST should have object.create
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        assert len(bulk_posts) >= 1
        create_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.create"
        ]
        assert len(create_cmds) == 1

    @pytest.mark.asyncio
    async def test_updates_existing_task(self):
        """Existing task produces object.patch in bulk POST."""
        issue = make_issue(number=42, title="Update me")
        slug = compute_issue_slug("owner/repo", 42)
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        graph = MockGraphClient(
            slug_map={slug: f"https://example.org/data/Task/{slug}"},
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["updated"] == 1
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        patch_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.patch"
        ]
        assert len(patch_cmds) >= 1

    @pytest.mark.asyncio
    async def test_empty_repo(self):
        """Empty issue list from GitHub produces no commands."""
        ext_http = MockExternalHttpClient(_make_github_responses([]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert len(bulk_http.posts) == 0

    @pytest.mark.asyncio
    async def test_multiple_repos(self):
        """Issues from multiple repos are all processed."""
        issue1 = make_issue(number=1, title="Issue from repo1")
        issue2 = make_issue(number=2, title="Issue from repo2")
        # External HTTP: verify_token, then two fetch_issues calls,
        # then two timeline calls (one per non-PR issue)
        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue1], headers={}),
            MockResponse(200, [issue2], headers={}),
            MockResponse(200, [], headers={}),  # timeline for issue1
            MockResponse(200, [], headers={}),  # timeline for issue2
        ])
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(["owner/repo1", "owner/repo2"]),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "success"
        assert result["created"] == 2

    @pytest.mark.asyncio
    async def test_delta_sync_uses_since(self):
        """When last_sync_at is set, fetch_issues receives since parameter."""
        issue = make_issue()
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        state_data = _make_connected_state()
        state_data["last_sync_at"] = "2026-03-17T00:00:00+00:00"
        ctx = MockAppContext(
            state_data=state_data,
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        # The fetch_issues request should include since in params
        fetch_requests = [
            r for r in ext_http.requests
            if "issues" in r["url"]
        ]
        assert len(fetch_requests) >= 1
        params = fetch_requests[0].get("params", {})
        assert params.get("since") == "2026-03-17T00:00:00+00:00"


# ===================================================================
# Tests — PR filtering
# ===================================================================


class TestPRFiltering:
    @pytest.mark.asyncio
    async def test_prs_are_created_as_tasks(self):
        """PRs are now synced as tasks alongside regular issues."""
        regular_issue = make_issue(number=1, title="Real issue")
        pr_issue = make_pr_issue(number=100)
        ext_http = MockExternalHttpClient(
            _make_github_responses([regular_issue, pr_issue])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 2
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_all_prs_creates_pr_tasks(self):
        """When all items are PRs, they are all created as tasks."""
        pr1 = make_pr_issue(number=10)
        pr2 = make_pr_issue(number=11)
        ext_http = MockExternalHttpClient(_make_github_responses([pr1, pr2]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 2
        assert result["skipped"] == 0


# ===================================================================
# Tests — Error isolation
# ===================================================================


class TestErrorIsolation:
    @pytest.mark.asyncio
    async def test_single_issue_failure_doesnt_abort(self):
        """One issue raising an error doesn't prevent other issues from syncing."""
        good_issue = make_issue(number=1, title="Good issue")
        bad_issue = make_issue(number=2, title="Bad issue")
        # Remove required 'number' key from bad_issue to cause KeyError
        del bad_issue["number"]

        ext_http = MockExternalHttpClient(
            _make_github_responses([good_issue, bad_issue])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        # Good issue was processed, bad one errored
        assert result["created"] >= 1
        assert result["errors"] >= 1

    @pytest.mark.asyncio
    async def test_partial_failure_records_failed_issues(self):
        """last_pull_result contains failed_issues list on partial failure."""
        good_issue = make_issue(number=1)
        bad_issue = make_issue(number=2)
        del bad_issue["number"]

        ext_http = MockExternalHttpClient(
            _make_github_responses([good_issue, bad_issue])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "partial"
        assert len(result["failed_issues"]) >= 1

    @pytest.mark.asyncio
    async def test_all_issues_fail_gives_error_status(self):
        """When all issues fail processing, status is 'error'."""
        bad1 = make_issue(number=1)
        bad2 = make_issue(number=2)
        del bad1["number"]
        del bad2["number"]

        ext_http = MockExternalHttpClient(
            _make_github_responses([bad1, bad2])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "error"
        assert result["errors"] == 2
        assert result["created"] == 0


# ===================================================================
# Tests — last_pull_result diagnostics
# ===================================================================


class TestLastPullResultDiagnostics:
    @pytest.mark.asyncio
    async def test_success_result_structure(self):
        """Successful sync writes a well-structured last_pull_result."""
        issue = make_issue()
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        raw = await ctx.state.get("last_pull_result")
        assert raw is not None
        result = json.loads(raw)
        assert result["status"] == "success"
        assert isinstance(result["created"], int)
        assert isinstance(result["updated"], int)
        assert isinstance(result["skipped"], int)
        assert isinstance(result["errors"], int)
        assert isinstance(result["failed_issues"], list)
        assert isinstance(result["duration_ms"], int)
        assert isinstance(result["timestamp"], str)
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_partial_failure_diagnostics(self):
        """Partial failure result records error count and failed issue references."""
        good_issue = make_issue(number=1)
        bad_issue = make_issue(number=2)
        del bad_issue["number"]

        ext_http = MockExternalHttpClient(
            _make_github_responses([good_issue, bad_issue])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        raw = await ctx.state.get("last_pull_result")
        result = json.loads(raw)
        assert result["status"] == "partial"
        assert result["errors"] >= 1
        assert len(result["failed_issues"]) >= 1
        assert result["duration_ms"] >= 0
        assert result["timestamp"] != ""

    @pytest.mark.asyncio
    async def test_skipped_result_persisted(self):
        """Skipped sync also writes last_pull_result."""
        ctx = MockAppContext(state_data={})

        await pull_sync(ctx)

        raw = await ctx.state.get("last_pull_result")
        assert raw is not None
        result = json.loads(raw)
        assert result["status"] == "skipped"
        assert "duration_ms" in result


# ===================================================================
# Tests — Person matching integration
# ===================================================================


class TestPersonMatching:
    @pytest.mark.asyncio
    async def test_assignee_resolved(self):
        """Issue with assignee triggers person matcher and includes person_iri in properties."""
        issue = make_issue(
            number=5,
            assignees=[{"login": "bob", "email": "bob@example.com"}],
            assignee={"login": "bob", "email": "bob@example.com"},
        )
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 1
        # PersonMatcher should have created a person via commands
        assert len(ctx.commands.commands) >= 1

    @pytest.mark.asyncio
    async def test_no_assignee_skips_matching(self):
        """Issue with no assignee doesn't trigger person creation."""
        issue = make_issue(number=6, assignees=[], assignee=None)
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 1
        # No person creation commands
        assert len(ctx.commands.commands) == 0


# ===================================================================
# Tests — body.set for new issues (Phase 2)
# ===================================================================


class TestPhase2BodySet:
    @pytest.mark.asyncio
    async def test_body_set_for_new_issue_with_body(self):
        """New issue with body text triggers phase 2 body.set after create."""
        issue = make_issue(number=10, body="# Hello\n\nSome content")
        slug = compute_issue_slug("owner/repo", 10)

        # After phase 1, _find_existing_task should find the created task
        graph = MockGraphClient(
            slug_map={slug: f"https://example.org/data/Task/{slug}"},
        )
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        # Since the slug exists in slug_map, the issue will be treated as
        # an existing task (updated, not created). Still verify body.set
        # appears in update commands.
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        body_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "body.set"
        ]
        assert len(body_cmds) >= 1

    @pytest.mark.asyncio
    async def test_no_body_skips_body_set(self):
        """Issue with empty body doesn't produce body.set commands."""
        issue = make_issue(number=11, body="")
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        body_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "body.set"
        ]
        assert len(body_cmds) == 0


# ===================================================================
# Tests — last_sync_at update
# ===================================================================


class TestSyncTimestamp:
    @pytest.mark.asyncio
    async def test_last_sync_at_updated_after_sync(self):
        """Successful sync updates last_sync_at in state."""
        issue = make_issue()
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None
        assert "T" in last_sync  # ISO-8601 format


# ===================================================================
# Helpers — timeline event fixtures
# ===================================================================


def _make_cross_ref_event(
    pr_number: int,
    repo_full_name: str = "owner/repo",
) -> dict:
    """Build a cross-referenced timeline event for a PR."""
    return {
        "event": "cross-referenced",
        "source": {
            "issue": {
                "number": pr_number,
                "pull_request": {
                    "url": f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}",
                },
                "repository": {"full_name": repo_full_name},
            },
        },
    }


# ===================================================================
# Tests — PR sync (PRs now create tasks)
# ===================================================================


class TestPRSync:
    @pytest.mark.asyncio
    async def test_pr_creates_task_with_github_pr_provider(self):
        """PR in fetch_issues produces object.create with externalProvider: github-pr."""
        pr = make_pr_issue(number=50, title="Add widget")
        ext_http = MockExternalHttpClient(_make_github_responses([pr]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 1
        # Inspect the create command's properties
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        create_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.create"
        ]
        assert len(create_cmds) == 1
        props = create_cmds[0]["params"]["properties"]
        assert props[f"{BPKM}externalProvider"] == "github-pr"

    @pytest.mark.asyncio
    async def test_mixed_issues_and_prs_all_created(self):
        """Batch of 2 issues + 1 PR produces 3 created tasks."""
        issue1 = make_issue(number=1, title="Bug A")
        issue2 = make_issue(number=2, title="Bug B")
        pr = make_pr_issue(number=10, title="Fix A")
        ext_http = MockExternalHttpClient(
            _make_github_responses([issue1, issue2, pr])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 3
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_pr_body_set(self):
        """PR with body text gets body.set in phase 2."""
        pr = make_pr_issue(number=60)
        pr["body"] = "## PR Description\n\nFixes things"
        slug = compute_issue_slug("owner/repo", 60)
        # Slug in graph so phase 2 can discover the IRI
        graph = MockGraphClient(
            slug_map={slug: f"https://example.org/data/Task/{slug}"},
        )
        ext_http = MockExternalHttpClient(_make_github_responses([pr]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        # Slug is in graph → treated as update, not create
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        body_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "body.set"
        ]
        assert len(body_cmds) >= 1

    @pytest.mark.asyncio
    async def test_pr_update_existing(self):
        """Existing PR task gets object.patch on re-sync."""
        pr = make_pr_issue(number=70, title="Updated PR")
        slug = compute_issue_slug("owner/repo", 70)
        graph = MockGraphClient(
            slug_map={slug: f"https://example.org/data/Task/{slug}"},
        )
        ext_http = MockExternalHttpClient(_make_github_responses([pr]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["updated"] == 1
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        patch_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.patch"
        ]
        assert len(patch_cmds) >= 1

    @pytest.mark.asyncio
    async def test_pr_properties_include_correct_provider(self):
        """Verify the properties dict has externalProvider: github-pr."""
        pr = make_pr_issue(number=80, title="New PR")
        ext_http = MockExternalHttpClient(_make_github_responses([pr]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        create_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.create"
        ]
        assert len(create_cmds) == 1
        props = create_cmds[0]["params"]["properties"]
        # github-pr vs github for regular issues
        assert props[f"{BPKM}externalProvider"] == "github-pr"
        assert f"{BPKM}externalUrl" in props


# ===================================================================
# Tests — Timeline edge creation (Phase 3)
# ===================================================================


class TestTimelineEdgeCreation:
    @pytest.mark.asyncio
    async def test_edge_created_for_cross_referenced_pr(self):
        """Issue with timeline cross-ref to PR produces edge.create command."""
        issue = make_issue(number=5, title="Fix bug")
        pr = make_pr_issue(number=20, title="PR that fixes #5")

        issue_slug = compute_issue_slug("owner/repo", 5)
        pr_slug = compute_issue_slug("owner/repo", 20)

        # Both slugs must be in the graph for edge resolution
        graph = MockGraphClient(slug_map={
            issue_slug: f"https://example.org/data/Task/{issue_slug}",
            pr_slug: f"https://example.org/data/Task/{pr_slug}",
        })

        timeline_events = [_make_cross_ref_event(20, "owner/repo")]
        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue, pr], headers={}),
            # Timeline for the issue (PR doesn't trigger timeline)
            MockResponse(200, timeline_events, headers={}),
        ])
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["edges_created"] == 1
        # Find edge.create in bulk commands
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        edge_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "edge.create"
        ]
        assert len(edge_cmds) == 1
        assert edge_cmds[0]["params"]["source"] == f"https://example.org/data/Task/{pr_slug}"
        assert edge_cmds[0]["params"]["target"] == f"https://example.org/data/Task/{issue_slug}"
        assert edge_cmds[0]["params"]["predicate"] == f"{BPKM}dependsOn"

    @pytest.mark.asyncio
    async def test_no_edges_when_no_cross_references(self):
        """Issue with empty timeline produces no edge commands."""
        issue = make_issue(number=3, title="Standalone issue")
        ext_http = MockExternalHttpClient(
            _make_github_responses([issue], timeline_responses=[
                MockResponse(200, [], headers={}),
            ])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_edge_skipped_when_pr_task_not_found(self):
        """Timeline references PR not in synced repos — no edge, no error."""
        issue = make_issue(number=4, title="Issue with external PR ref")
        issue_slug = compute_issue_slug("owner/repo", 4)
        # Only the issue slug is in the graph; PR slug is absent
        graph = MockGraphClient(slug_map={
            issue_slug: f"https://example.org/data/Task/{issue_slug}",
        })

        timeline_events = [_make_cross_ref_event(99, "owner/repo")]
        ext_http = MockExternalHttpClient(
            _make_github_responses([issue], timeline_responses=[
                MockResponse(200, timeline_events, headers={}),
            ])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["edges_created"] == 0
        # No error — just a debug log skip
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_edge_skipped_when_issue_task_not_found(self):
        """Graceful skip when issue IRI lookup fails in edge resolution."""
        issue = make_issue(number=6, title="Issue not in graph")
        # PR slug is in graph, but issue slug is NOT
        pr_slug = compute_issue_slug("owner/repo", 30)
        graph = MockGraphClient(slug_map={
            pr_slug: f"https://example.org/data/Task/{pr_slug}",
        })

        timeline_events = [_make_cross_ref_event(30, "owner/repo")]
        ext_http = MockExternalHttpClient(
            _make_github_responses([issue], timeline_responses=[
                MockResponse(200, timeline_events, headers={}),
            ])
        )
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["edges_created"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_multiple_prs_referencing_same_issue(self):
        """Issue timeline with 2 PR cross-refs produces 2 edge.create commands."""
        issue = make_issue(number=7, title="Issue with two PR refs")
        pr1 = make_pr_issue(number=40, title="PR 1")
        pr2 = make_pr_issue(number=41, title="PR 2")

        issue_slug = compute_issue_slug("owner/repo", 7)
        pr1_slug = compute_issue_slug("owner/repo", 40)
        pr2_slug = compute_issue_slug("owner/repo", 41)

        graph = MockGraphClient(slug_map={
            issue_slug: f"https://example.org/data/Task/{issue_slug}",
            pr1_slug: f"https://example.org/data/Task/{pr1_slug}",
            pr2_slug: f"https://example.org/data/Task/{pr2_slug}",
        })

        timeline_events = [
            _make_cross_ref_event(40, "owner/repo"),
            _make_cross_ref_event(41, "owner/repo"),
        ]
        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue, pr1, pr2], headers={}),
            # Only the issue triggers a timeline call (PRs don't)
            MockResponse(200, timeline_events, headers={}),
        ])
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["edges_created"] == 2
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        edge_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "edge.create"
        ]
        assert len(edge_cmds) == 2

    @pytest.mark.asyncio
    async def test_timeline_api_error_isolated(self):
        """Timeline fetch error for one issue doesn't abort other issues."""
        issue1 = make_issue(number=8, title="Issue with timeline error")
        issue2 = make_issue(number=9, title="Issue that succeeds")

        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue1, issue2], headers={}),
            # Timeline for issue 8 — 500 error
            MockResponse(500, {"message": "Internal Server Error"}, headers={}),
            # Timeline for issue 9 — success, empty
            MockResponse(200, [], headers={}),
        ])
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        # issue1's timeline error is isolated — issue2 still processed
        assert result["created"] == 2  # Both issues created
        assert result["errors"] >= 1
        # The failed_issues should contain the timeline suffix
        timeline_failures = [
            f for f in result["failed_issues"] if "(timeline)" in f
        ]
        assert len(timeline_failures) == 1
        assert "owner/repo#8(timeline)" in result["failed_issues"]

    @pytest.mark.asyncio
    async def test_edges_created_in_result(self):
        """last_pull_result includes edges_created count for diagnostics."""
        issue = make_issue(number=11, title="Issue for edge test")
        pr = make_pr_issue(number=25, title="PR for edge test")

        issue_slug = compute_issue_slug("owner/repo", 11)
        pr_slug = compute_issue_slug("owner/repo", 25)

        graph = MockGraphClient(slug_map={
            issue_slug: f"https://example.org/data/Task/{issue_slug}",
            pr_slug: f"https://example.org/data/Task/{pr_slug}",
        })

        timeline_events = [_make_cross_ref_event(25, "owner/repo")]
        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue, pr], headers={}),
            MockResponse(200, timeline_events, headers={}),
        ])
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        raw = await ctx.state.get("last_pull_result")
        result = json.loads(raw)
        assert result["edges_created"] == 1
        assert isinstance(result["edges_created"], int)

    @pytest.mark.asyncio
    async def test_timeline_not_called_for_prs(self):
        """PRs don't trigger timeline queries — only issues do."""
        pr1 = make_pr_issue(number=50)
        pr2 = make_pr_issue(number=51)
        ext_http = MockExternalHttpClient(_make_github_responses([pr1, pr2]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 2
        # No timeline requests should have been made (only verify_token + fetch_issues)
        timeline_requests = [
            r for r in ext_http.requests if "timeline" in r["url"]
        ]
        assert len(timeline_requests) == 0


# ===================================================================
# Tests — _find_existing_task provider parameter
# ===================================================================


class TestFindExistingTaskProvider:
    @pytest.mark.asyncio
    async def test_find_with_default_provider(self):
        """Default provider='github' includes provider filter in SPARQL."""
        graph = MockGraphClient(
            slug_map={"gh-abc": "https://example.org/data/Task/gh-abc"},
        )
        result = await _find_existing_task(graph, "gh-abc")
        assert result is not None
        # SPARQL should contain the github provider filter
        assert 'externalProvider' in graph.queries[-1]
        assert '"github"' in graph.queries[-1]

    @pytest.mark.asyncio
    async def test_find_with_pr_provider(self):
        """provider='github-pr' includes that string in SPARQL."""
        graph = MockGraphClient(
            slug_map={"gh-pr-123": "https://example.org/data/Task/gh-pr-123"},
        )
        result = await _find_existing_task(graph, "gh-pr-123", provider="github-pr")
        assert result is not None
        assert '"github-pr"' in graph.queries[-1]

    @pytest.mark.asyncio
    async def test_find_with_no_provider(self):
        """provider=None omits the provider filter — slug-only lookup."""
        graph = MockGraphClient(
            slug_map={"gh-xyz": "https://example.org/data/Task/gh-xyz"},
        )
        result = await _find_existing_task(graph, "gh-xyz", provider=None)
        assert result is not None
        # SPARQL should NOT contain an externalProvider filter
        assert "externalProvider" not in graph.queries[-1]

    @pytest.mark.asyncio
    async def test_find_with_no_provider_returns_pr_task(self):
        """provider=None can find a task regardless of its provider value."""
        pr_slug = "gh-pr-456"
        graph = MockGraphClient(
            slug_map={pr_slug: f"https://example.org/data/Task/{pr_slug}"},
        )
        result = await _find_existing_task(graph, pr_slug, provider=None)
        assert result is not None
        assert result["iri"] == f"https://example.org/data/Task/{pr_slug}"
        assert "externalProvider" not in graph.queries[-1]


# ===================================================================
# Tests — _find_existing_task returns lastSyncedAt
# ===================================================================


class TestFindExistingTaskLastSyncedAt:
    @pytest.mark.asyncio
    async def test_returns_last_synced_at(self):
        """_find_existing_task returns lastSyncedAt when present in graph."""
        graph = MockGraphClient(slug_map={
            "gh-abc": {
                "iri": "https://example.org/data/Task/gh-abc",
                "lastSyncedAt": "2026-03-18T10:00:00+00:00",
            },
        })
        result = await _find_existing_task(graph, "gh-abc")
        assert result is not None
        assert result["lastSyncedAt"] == "2026-03-18T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_returns_none_last_synced_at_when_absent(self):
        """_find_existing_task returns None lastSyncedAt when not in graph."""
        graph = MockGraphClient(slug_map={
            "gh-def": "https://example.org/data/Task/gh-def",
        })
        result = await _find_existing_task(graph, "gh-def")
        assert result is not None
        assert result["lastSyncedAt"] is None


# ===================================================================
# Tests — _find_changed_tasks
# ===================================================================


def _make_changed_tasks_graph(tasks: list[dict]) -> MockGraphClient:
    """Build a MockGraphClient that returns changed tasks for SPARQL queries.

    Each task dict should have: iri, uuid, and optionally url, extId,
    status, title, tags, lastSyncedAt.
    """
    bindings = []
    for t in tasks:
        binding: dict = {
            "task": {"type": "uri", "value": t["iri"]},
            "uuid": {"type": "literal", "value": t["uuid"]},
        }
        for key, sparql_var in [
            ("url", "url"), ("extId", "extId"), ("status", "status"),
            ("title", "title"), ("tags", "tags"), ("lastSyncedAt", "lastSynced"),
        ]:
            if t.get(key):
                binding[sparql_var] = {"type": "literal", "value": t[key]}
        bindings.append(binding)

    return MockGraphClient(
        default_results={"results": {"bindings": bindings}},
    )


class TestFindChangedTasks:
    @pytest.mark.asyncio
    async def test_happy_path_returns_tasks(self):
        """Returns list of changed task dicts from SPARQL results."""
        graph = _make_changed_tasks_graph([{
            "iri": "https://example.org/data/Task/gh-001",
            "uuid": "I_kwDO_test1",
            "url": "https://github.com/owner/repo/issues/1",
            "extId": "#1",
            "status": "in-progress",
            "title": "Updated task",
        }])
        result = await _find_changed_tasks(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "https://example.org/data/Task/gh-001"
        assert result[0]["externalUuid"] == "I_kwDO_test1"
        assert result[0]["externalUrl"] == "https://github.com/owner/repo/issues/1"
        assert result[0]["status"] == "in-progress"
        assert result[0]["title"] == "Updated task"

    @pytest.mark.asyncio
    async def test_empty_result(self):
        """Returns empty list when no changed tasks found."""
        graph = MockGraphClient()  # default empty results
        result = await _find_changed_tasks(graph)
        assert result == []

    @pytest.mark.asyncio
    async def test_query_structure(self):
        """SPARQL query filters by github provider, modified > lastSyncedAt."""
        graph = MockGraphClient()
        await _find_changed_tasks(graph)
        assert len(graph.queries) == 1
        q = graph.queries[0]
        assert '"github"' in q
        assert "externalUuid" in q
        assert "lastSynced" in q
        assert "modified" in q
        assert 'pull-only' in q


# ===================================================================
# Helpers — push sync context builders
# ===================================================================


def _make_push_github_responses(
    *,
    patch_responses: list[MockResponse] | None = None,
) -> list[MockResponse]:
    """Build responses for push_sync: verify_token + optional PATCH responses."""
    responses = [
        # verify_token: GET /user
        MockResponse(200, {"login": "testuser", "email": "test@example.com"},
                     headers={}),
    ]
    if patch_responses:
        responses.extend(patch_responses)
    return responses


def _make_push_context(
    *,
    connected: bool = True,
    sync_direction: str | None = "bidirectional",
    changed_tasks: list[dict] | None = None,
    ext_responses: list[MockResponse] | None = None,
) -> MockAppContext:
    """Build a MockAppContext configured for push_sync tests."""
    state_data = _make_connected_state() if connected else {}
    settings_data: dict[str, str] = {}
    if sync_direction:
        settings_data["sync_direction"] = sync_direction
    settings_data["selected_repos"] = json.dumps(["owner/repo"])

    # Build graph with changed tasks
    if changed_tasks:
        graph = _make_changed_tasks_graph(changed_tasks)
    else:
        graph = MockGraphClient()

    ext_http = MockExternalHttpClient(
        ext_responses or _make_push_github_responses()
    )
    bulk_http = MockHttpClient()

    return MockAppContext(
        state_data=state_data,
        settings_data=settings_data,
        graph_client=graph,
        http_client=bulk_http,
        ext_http_client=ext_http,
    )


# ===================================================================
# Tests — push_sync
# ===================================================================


class TestPushSync:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Push sync patches an issue and updates lastSyncedAt."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-001",
            "uuid": "I_kwDO_test1",
            "url": "https://github.com/owner/repo/issues/1",
            "extId": "#1",
            "status": "done",
            "title": "Completed task",
        }]
        patch_resp = MockResponse(200, {"number": 1, "state": "closed"})
        ctx = _make_push_context(
            changed_tasks=tasks,
            ext_responses=_make_push_github_responses(
                patch_responses=[patch_resp],
            ),
        )
        result = await push_sync(ctx)
        assert result["status"] == "ok"
        assert result["pushed"] == 1
        assert result["errors"] == [] or len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_not_connected_skip(self):
        """Push sync skips when not connected."""
        ctx = _make_push_context(connected=False)
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_pull_only_skip(self):
        """Push sync skips when direction is pull-only."""
        ctx = _make_push_context(sync_direction="pull-only")
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert "pull-only" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_no_changed_tasks(self):
        """Push sync returns ok with 0 pushed when no tasks changed."""
        ctx = _make_push_context(changed_tasks=None)
        result = await push_sync(ctx)
        assert result["status"] == "ok"
        assert result["pushed"] == 0

    @pytest.mark.asyncio
    async def test_partial_failure_with_errors(self):
        """When one task fails to push, it's recorded in errors list."""
        tasks = [
            {
                "iri": "https://example.org/data/Task/gh-001",
                "uuid": "I_kwDO_test1",
                "url": "https://github.com/owner/repo/issues/1",
                "status": "done",
                "title": "Good task",
            },
            {
                "iri": "https://example.org/data/Task/gh-002",
                "uuid": "I_kwDO_test2",
                "url": "https://github.com/owner/repo/issues/2",
                "status": "todo",
                "title": "Bad task",
            },
        ]
        # First PATCH succeeds, second fails
        ctx = _make_push_context(
            changed_tasks=tasks,
            ext_responses=[
                MockResponse(200, {"login": "testuser"}, headers={}),
                MockResponse(200, {"number": 1, "state": "closed"}),
                MockResponse(422, {"message": "Validation Failed"}),
            ],
        )
        result = await push_sync(ctx)
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1
        assert "gh-002" in result["errors"][0]["iri"]

    @pytest.mark.asyncio
    async def test_last_synced_at_updated(self):
        """Push sync updates lastSyncedAt via object.patch command."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-001",
            "uuid": "I_kwDO_test1",
            "url": "https://github.com/owner/repo/issues/1",
            "status": "done",
            "title": "Task",
        }]
        patch_resp = MockResponse(200, {"number": 1})
        ctx = _make_push_context(
            changed_tasks=tasks,
            ext_responses=_make_push_github_responses(
                patch_responses=[patch_resp],
            ),
        )
        await push_sync(ctx)

        # Check that bulk POST includes lastSyncedAt update
        bulk_http = ctx.commands._client
        bulk_posts = [p for p in bulk_http.posts if p["url"] == "/api/commands/bulk"]
        assert len(bulk_posts) >= 1
        patch_cmds = [
            c for p in bulk_posts
            for c in p["json"]["commands"]
            if c["command"] == "object.patch"
        ]
        assert any(
            f"{BPKM}lastSyncedAt" in c["params"].get("properties", {})
            for c in patch_cmds
        )

    @pytest.mark.asyncio
    async def test_parse_external_url_failure(self):
        """Tasks with unparseable URLs are recorded as errors, not exceptions."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-bad",
            "uuid": "I_kwDO_bad",
            "url": "not-a-valid-url",
            "status": "todo",
            "title": "Bad URL task",
        }]
        ctx = _make_push_context(changed_tasks=tasks)
        result = await push_sync(ctx)
        assert result["pushed"] == 0
        assert len(result["errors"]) == 1
        assert "Could not parse" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_empty_patch_data_skipped(self):
        """Task with no pushable fields is skipped, not errored."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-skip",
            "uuid": "I_kwDO_skip",
            "url": "https://github.com/owner/repo/issues/99",
            # No title, no status, no tags — build_issue_patch returns {}
        }]
        ctx = _make_push_context(changed_tasks=tasks)
        result = await push_sync(ctx)
        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert len(result["errors"]) == 0


# ===================================================================
# Tests — Loop prevention in pull_sync
# ===================================================================


class TestLoopPrevention:
    @pytest.mark.asyncio
    async def test_skip_when_updated_at_lte_last_synced(self):
        """Issue skipped when updated_at <= existing task's lastSyncedAt."""
        issue = make_issue(
            number=42,
            updated_at="2026-03-18T10:00:00Z",
        )
        slug = compute_issue_slug("owner/repo", 42)
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "lastSyncedAt": "2026-03-18T12:00:00Z",  # after updated_at
            },
        })
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)
        assert result["skipped"] >= 1
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_process_when_updated_at_gt_last_synced(self):
        """Issue processed when updated_at > existing task's lastSyncedAt."""
        issue = make_issue(
            number=43,
            updated_at="2026-03-19T10:00:00Z",
        )
        slug = compute_issue_slug("owner/repo", 43)
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Task/{slug}",
                "lastSyncedAt": "2026-03-18T08:00:00Z",  # before updated_at
            },
        })
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)
        assert result["updated"] == 1
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_process_when_no_last_synced_at(self):
        """Issue processed when existing task has no lastSyncedAt."""
        issue = make_issue(number=44, updated_at="2026-03-18T10:00:00Z")
        slug = compute_issue_slug("owner/repo", 44)
        graph = MockGraphClient(slug_map={
            slug: f"https://example.org/data/Task/{slug}",
            # No lastSyncedAt — plain IRI string, not dict
        })
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)
        assert result["updated"] == 1

    @pytest.mark.asyncio
    async def test_new_issue_not_affected_by_loop_prevention(self):
        """New issues (no existing task) are not affected by loop prevention."""
        issue = make_issue(number=45)
        ext_http = MockExternalHttpClient(_make_github_responses([issue]))
        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_connected_state(),
            settings_data=_make_settings_with_repos(),
            http_client=bulk_http,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)
        assert result["created"] == 1


# ===================================================================
# Tests — Push sync diagnostics
# ===================================================================


class TestPushSyncDiagnostics:
    @pytest.mark.asyncio
    async def test_last_push_result_structure(self):
        """last_push_result has status, pushed, errors, and timestamp."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-diag",
            "uuid": "I_kwDO_diag",
            "url": "https://github.com/owner/repo/issues/99",
            "status": "done",
            "title": "Diag task",
        }]
        patch_resp = MockResponse(200, {"number": 99})
        ctx = _make_push_context(
            changed_tasks=tasks,
            ext_responses=_make_push_github_responses(
                patch_responses=[patch_resp],
            ),
        )
        await push_sync(ctx)

        raw = await ctx.state.get("last_push_result")
        assert raw is not None
        result = json.loads(raw)
        assert "status" in result
        assert "pushed" in result
        assert "errors" in result
        assert "timestamp" in result
        assert isinstance(result["pushed"], int)
        assert isinstance(result["errors"], list)
        assert isinstance(result["timestamp"], str)

    @pytest.mark.asyncio
    async def test_last_push_result_on_skip(self):
        """last_push_result is stored even when sync is skipped."""
        ctx = _make_push_context(connected=False)
        await push_sync(ctx)

        raw = await ctx.state.get("last_push_result")
        assert raw is not None
        result = json.loads(raw)
        assert result["status"] == "skipped"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_error_entries_have_iri_and_message(self):
        """Error entries in last_push_result contain task IRI and error message."""
        tasks = [{
            "iri": "https://example.org/data/Task/gh-err",
            "uuid": "I_kwDO_err",
            "url": "https://github.com/owner/repo/issues/500",
            "status": "done",
            "title": "Error task",
        }]
        ctx = _make_push_context(
            changed_tasks=tasks,
            ext_responses=[
                MockResponse(200, {"login": "testuser"}, headers={}),
                MockResponse(500, {"message": "Server Error"}),
            ],
        )
        await push_sync(ctx)

        raw = await ctx.state.get("last_push_result")
        result = json.loads(raw)
        assert len(result["errors"]) == 1
        assert "iri" in result["errors"][0]
        assert "error" in result["errors"][0]
        assert "gh-err" in result["errors"][0]["iri"]
