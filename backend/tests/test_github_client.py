"""Unit tests for the GitHub REST API client.

Loads ``github_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All HTTP and state interactions
are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load github_client module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "github-sync"
    / "services"
    / "github_client.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("github_client", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["github_client"] = mod
    spec.loader.exec_module(mod)
    return mod


gc = _load_module()
GitHubClient = gc.GitHubClient
GitHubAPIError = gc.GitHubAPIError
GitHubAuthError = gc.GitHubAuthError
GitHubRateLimitError = gc.GitHubRateLimitError
GITHUB_API_URL = gc.GITHUB_API_URL


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: dict | list | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)

    def json(self) -> Any:
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class MockHttpClient:
    """Records calls and returns preset responses."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self._idx = 0

    async def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})


class MockStateClient:
    """In-memory state store."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(body: Any, headers: dict[str, str] | None = None) -> MockResponse:
    """200 OK response with optional headers."""
    return MockResponse(200, body, headers)


def _link_header(next_url: str | None) -> dict[str, str]:
    """Build a Link header dict with rel='next'."""
    if next_url is None:
        return {}
    return {"Link": f'<{next_url}>; rel="next"'}


def _rate_limit_headers(remaining: int, reset_epoch: int) -> dict[str, str]:
    """Build rate-limit response headers."""
    return {
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_epoch),
    }


def _make_client(
    responses: list[MockResponse],
    pat: str = "ghp_test123",
) -> tuple[GitHubClient, MockHttpClient, MockStateClient]:
    """Create a client with mocked HTTP and state."""
    http = MockHttpClient(responses)
    state = MockStateClient({"github_pat": pat} if pat else {})
    client = GitHubClient(http, state)
    return client, http, state


# ===========================================================================
# Tests: Link-header pagination
# ===========================================================================

class TestPagination:

    @pytest.mark.asyncio
    async def test_single_page_no_link_header(self):
        """Single page of results when no Link header is present."""
        client, http, _ = _make_client([
            _ok([{"id": 1}, {"id": 2}]),
        ])

        result = await client._paginate("/repos")

        assert result == [{"id": 1}, {"id": 2}]
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_multi_page_follows_link_header(self):
        """Follows Link header across 3 pages."""
        client, http, _ = _make_client([
            _ok([{"id": 1}], _link_header("https://api.github.com/repos?page=2")),
            _ok([{"id": 2}], _link_header("https://api.github.com/repos?page=3")),
            _ok([{"id": 3}]),  # No Link → stop
        ])

        result = await client._paginate("/repos")

        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert len(http.calls) == 3
        # Second call should use the absolute URL from Link header
        assert http.calls[1]["url"] == "https://api.github.com/repos?page=2"
        assert http.calls[2]["url"] == "https://api.github.com/repos?page=3"

    @pytest.mark.asyncio
    async def test_max_pages_guard(self):
        """Stops at MAX_PAGINATION_PAGES even if Link header has next."""
        responses = []
        for i in range(55):
            responses.append(
                _ok([{"id": i}], _link_header(f"https://api.github.com/r?page={i + 2}"))
            )
        client, http, _ = _make_client(responses)

        result = await client._paginate("/r")

        assert len(result) == 50
        assert len(http.calls) == 50

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Empty list response returns empty results."""
        client, _, _ = _make_client([_ok([])])

        result = await client._paginate("/repos")

        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_link_header_stops(self):
        """Malformed Link header without rel='next' stops pagination."""
        client, http, _ = _make_client([
            _ok([{"id": 1}], {"Link": 'malformed-garbage'}),
        ])

        result = await client._paginate("/repos")

        assert result == [{"id": 1}]
        assert len(http.calls) == 1

    @pytest.mark.asyncio
    async def test_first_request_uses_params(self):
        """First page request includes query params; subsequent don't re-add them."""
        client, http, _ = _make_client([
            _ok([{"id": 1}], _link_header("https://api.github.com/repos?page=2&per_page=100")),
            _ok([{"id": 2}]),
        ])

        await client._paginate("/repos", params={"per_page": "100", "sort": "updated"})

        # First call should have params
        assert http.calls[0].get("params") == {"per_page": "100", "sort": "updated"}
        # Second call uses URL from Link header, no extra params
        assert "params" not in http.calls[1] or http.calls[1].get("params") is None


# ===========================================================================
# Tests: Rate-limit checking
# ===========================================================================

class TestRateLimitChecking:

    @pytest.mark.asyncio
    async def test_remaining_above_threshold_no_sleep(self):
        """No sleep when remaining > 100."""
        client, _, _ = _make_client([])
        mock_sleep = _AsyncNoopMock()

        with patch.object(gc.asyncio, "sleep", mock_sleep):
            await client._check_rate_limit({"X-RateLimit-Remaining": "500"})
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_remaining_below_threshold_sleeps(self):
        """Sleeps when remaining < 100."""
        client, _, _ = _make_client([])
        reset_epoch = int(time.time()) + 30
        mock_sleep = _AsyncNoopMock()

        with patch.object(gc.asyncio, "sleep", mock_sleep):
            await client._check_rate_limit({
                "X-RateLimit-Remaining": "50",
                "X-RateLimit-Reset": str(reset_epoch),
            })
            mock_sleep.assert_called_once()
            sleep_val = mock_sleep.call_args[0][0]
            assert 1 <= sleep_val <= 35  # roughly 30s ± clock skew

    @pytest.mark.asyncio
    async def test_zero_remaining_sleeps(self):
        """Sleeps when remaining is 0."""
        client, _, _ = _make_client([])
        reset_epoch = int(time.time()) + 60
        mock_sleep = _AsyncNoopMock()

        with patch.object(gc.asyncio, "sleep", mock_sleep):
            await client._check_rate_limit({
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_epoch),
            })
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_headers_no_error(self):
        """No error or sleep when rate-limit headers are absent."""
        client, _, _ = _make_client([])
        mock_sleep = _AsyncNoopMock()

        with patch.object(gc.asyncio, "sleep", mock_sleep):
            await client._check_rate_limit({})
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_remaining_below_threshold_no_reset_header_defaults_60s(self):
        """Sleeps 60s when remaining is low but X-RateLimit-Reset is missing."""
        client, _, _ = _make_client([])
        mock_sleep = _AsyncNoopMock()

        with patch.object(gc.asyncio, "sleep", mock_sleep):
            await client._check_rate_limit({"X-RateLimit-Remaining": "10"})
            mock_sleep.assert_called_once_with(60)


# ===========================================================================
# Tests: Error handling
# ===========================================================================

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        client, _, _ = _make_client([MockResponse(401, "Bad credentials")])

        with pytest.raises(GitHubAuthError) as exc_info:
            await client._request("GET", "/user")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_403_raises_rate_limit_error(self):
        client, _, _ = _make_client([
            MockResponse(403, "Rate limit exceeded", {"X-RateLimit-Remaining": "0"}),
        ])

        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client._request("GET", "/repos")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error_with_retry_after(self):
        client, _, _ = _make_client([
            MockResponse(429, "Too Many Requests", {"Retry-After": "30"}),
        ])

        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client._request("GET", "/repos")
        assert exc_info.value.retry_after == 30
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_without_retry_after_defaults_60(self):
        client, _, _ = _make_client([MockResponse(429, "Rate limit")])

        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client._request("GET", "/repos")
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self):
        client, _, _ = _make_client([MockResponse(500, "Internal Server Error")])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client._request("GET", "/repos")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_no_pat_raises_auth_error(self):
        """Missing PAT in state raises GitHubAuthError before making request."""
        client, http, _ = _make_client([], pat="")

        with pytest.raises(GitHubAuthError, match="Not authenticated"):
            await client.verify_token()
        assert len(http.calls) == 0


# ===========================================================================
# Tests: verify_token
# ===========================================================================

class TestVerifyToken:

    @pytest.mark.asyncio
    async def test_success_returns_user(self):
        user_data = {"login": "octocat", "id": 1, "name": "The Octocat"}
        client, http, _ = _make_client([_ok(user_data)])

        result = await client.verify_token()

        assert result == user_data
        assert http.calls[0]["method"] == "GET"
        assert "/user" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        client, _, _ = _make_client([MockResponse(401, "Bad credentials")])

        with pytest.raises(GitHubAuthError):
            await client.verify_token()


# ===========================================================================
# Tests: fetch_repos
# ===========================================================================

class TestFetchRepos:

    @pytest.mark.asyncio
    async def test_returns_flat_list(self):
        repos = [{"id": 1, "name": "repo-a"}, {"id": 2, "name": "repo-b"}]
        client, _, _ = _make_client([_ok(repos)])

        result = await client.fetch_repos()

        assert result == repos

    @pytest.mark.asyncio
    async def test_pagination_works(self):
        client, http, _ = _make_client([
            _ok([{"id": 1}], _link_header("https://api.github.com/user/repos?page=2")),
            _ok([{"id": 2}]),
        ])

        result = await client.fetch_repos()

        assert result == [{"id": 1}, {"id": 2}]
        assert len(http.calls) == 2

    @pytest.mark.asyncio
    async def test_auth_error_propagates(self):
        client, _, _ = _make_client([MockResponse(401, "Bad credentials")])

        with pytest.raises(GitHubAuthError):
            await client.fetch_repos()


# ===========================================================================
# Tests: fetch_issues
# ===========================================================================

class TestFetchIssues:

    @pytest.mark.asyncio
    async def test_basic_fetch(self):
        issues = [
            {"number": 1, "title": "Bug"},
            {"number": 2, "title": "Feature", "pull_request": {}},
        ]
        client, _, _ = _make_client([_ok(issues)])

        result = await client.fetch_issues("owner", "repo")

        # Client returns all items including PRs — filtering is sync engine's job
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_since_parameter_passed(self):
        client, http, _ = _make_client([_ok([])])

        await client.fetch_issues("owner", "repo", since="2026-01-01T00:00:00Z")

        params = http.calls[0]["params"]
        assert params["since"] == "2026-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_since_absent_when_none(self):
        client, http, _ = _make_client([_ok([])])

        await client.fetch_issues("owner", "repo")

        params = http.calls[0]["params"]
        assert "since" not in params

    @pytest.mark.asyncio
    async def test_empty_repo(self):
        client, _, _ = _make_client([_ok([])])

        result = await client.fetch_issues("owner", "empty-repo")

        assert result == []


# ===========================================================================
# Tests: patch_issue
# ===========================================================================

class TestPatchIssue:

    @pytest.mark.asyncio
    async def test_success(self):
        updated = {"number": 42, "title": "Updated", "state": "closed"}
        client, http, _ = _make_client([_ok(updated)])

        result = await client.patch_issue("owner", "repo", 42, {"state": "closed"})

        assert result == updated
        assert http.calls[0]["method"] == "PATCH"
        assert "/repos/owner/repo/issues/42" in http.calls[0]["url"]
        assert http.calls[0]["json"] == {"state": "closed"}

    @pytest.mark.asyncio
    async def test_error(self):
        client, _, _ = _make_client([MockResponse(422, "Validation Failed")])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.patch_issue("owner", "repo", 42, {"state": "invalid"})
        assert exc_info.value.status_code == 422


# ===========================================================================
# Tests: fetch_timeline
# ===========================================================================

class TestFetchTimeline:

    @pytest.mark.asyncio
    async def test_fetch_timeline_basic(self):
        """Returns timeline events list for an issue."""
        events = [
            {"event": "labeled", "label": {"name": "bug"}},
            {"event": "cross-referenced", "source": {"issue": {"number": 10}}},
        ]
        client, http, _ = _make_client([_ok(events)])

        result = await client.fetch_timeline("owner", "repo", 42)

        assert result == events
        assert len(http.calls) == 1
        assert "/repos/owner/repo/issues/42/timeline" in http.calls[0]["url"]

    @pytest.mark.asyncio
    async def test_fetch_timeline_pagination(self):
        """Follows Link header for multi-page timelines."""
        page1_url = "https://api.github.com/repos/owner/repo/issues/42/timeline?page=2"
        client, http, _ = _make_client([
            _ok([{"event": "labeled"}], _link_header(page1_url)),
            _ok([{"event": "cross-referenced"}]),
        ])

        result = await client.fetch_timeline("owner", "repo", 42)

        assert len(result) == 2
        assert len(http.calls) == 2
        assert http.calls[1]["url"] == page1_url

    @pytest.mark.asyncio
    async def test_fetch_timeline_empty(self):
        """Returns empty list for issue with no timeline events."""
        client, _, _ = _make_client([_ok([])])

        result = await client.fetch_timeline("owner", "repo", 1)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_timeline_auth_error(self):
        """Raises GitHubAuthError on 401."""
        client, _, _ = _make_client([MockResponse(401, "Bad credentials")])

        with pytest.raises(GitHubAuthError) as exc_info:
            await client.fetch_timeline("owner", "repo", 42)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_fetch_timeline_api_error(self):
        """Raises GitHubAPIError on 404."""
        client, _, _ = _make_client([MockResponse(404, "Not Found")])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.fetch_timeline("owner", "repo", 999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_fetch_timeline_server_error(self):
        """Raises GitHubAPIError on 500."""
        client, _, _ = _make_client([MockResponse(500, "Internal Server Error")])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.fetch_timeline("owner", "repo", 42)
        assert exc_info.value.status_code == 500


# ===========================================================================
# Tests: Request construction
# ===========================================================================

class TestRequestConstruction:

    @pytest.mark.asyncio
    async def test_sends_correct_headers(self):
        client, http, _ = _make_client([_ok({"login": "octocat"})])

        await client.verify_token()

        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "token ghp_test123"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    @pytest.mark.asyncio
    async def test_relative_url_gets_base(self):
        client, http, _ = _make_client([_ok({"login": "octocat"})])

        await client.verify_token()

        assert http.calls[0]["url"] == f"{GITHUB_API_URL}/user"

    @pytest.mark.asyncio
    async def test_absolute_url_preserved(self):
        client, http, _ = _make_client([_ok([])])

        await client._request("GET", "https://custom.github.com/endpoint")

        assert http.calls[0]["url"] == "https://custom.github.com/endpoint"


# ===========================================================================
# Async mock helper
# ===========================================================================

class _AsyncNoopMock:
    """Mock for asyncio.sleep that tracks calls without actually sleeping."""

    def __init__(self):
        self._calls = []

    async def __call__(self, seconds):
        self._calls.append(seconds)

    def assert_called_once(self):
        assert len(self._calls) == 1, f"Expected 1 call, got {len(self._calls)}"

    def assert_not_called(self):
        assert len(self._calls) == 0, f"Expected 0 calls, got {len(self._calls)}"

    def assert_called_once_with(self, seconds):
        assert len(self._calls) == 1, f"Expected 1 call, got {len(self._calls)}"
        assert self._calls[0] == seconds, f"Expected sleep({seconds}), got sleep({self._calls[0]})"

    @property
    def call_args(self):
        """Return last call args in a format compatible with mock assertions."""
        if self._calls:
            return ([self._calls[-1]],)
        return None


def _async_noop():
    return _AsyncNoopMock()
