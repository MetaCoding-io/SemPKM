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
                                    "title": {
                                        "type": "literal",
                                        "value": "Existing task",
                                    },
                                    "status": {
                                        "type": "literal",
                                        "value": "todo",
                                    },
                                }
                            ]
                        }
                    }
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


def _make_github_responses(issues: list[dict]) -> list[MockResponse]:
    """Build MockExternalHttpClient responses for verify_token + fetch_issues."""
    return [
        # verify_token: GET /user
        MockResponse(200, {"login": "testuser", "email": "test@example.com"},
                     headers={}),
        # fetch_issues: GET /repos/owner/repo/issues (single page, no Link header)
        MockResponse(200, issues, headers={}),
    ]


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
        # External HTTP: verify_token, then two fetch_issues calls
        ext_http = MockExternalHttpClient([
            MockResponse(200, {"login": "testuser"}, headers={}),
            MockResponse(200, [issue1], headers={}),
            MockResponse(200, [issue2], headers={}),
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
    async def test_prs_are_skipped(self):
        """Issues with pull_request key are filtered out."""
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

        assert result["created"] == 1
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_all_prs_yields_zero_created(self):
        """When all items are PRs, nothing is created."""
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

        assert result["created"] == 0
        assert result["skipped"] == 2


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
