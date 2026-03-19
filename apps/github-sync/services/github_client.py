"""GitHubClient — authenticated REST client for the GitHub API.

Wraps the SDK HttpClient for authenticated requests to GitHub's REST API v3.
Supports PAT authentication, Link-header pagination, rate-limit header checking
with sleep, and typed exceptions for all error conditions.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger("github_sync.client")

GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")
MAX_PAGINATION_PAGES = 50

# Precompiled pattern for extracting rel="next" URL from Link header.
# Example: <https://api.github.com/user/repos?page=2>; rel="next"
_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class GitHubAuthError(GitHubAPIError):
    """Authentication/authorization error (401)."""


class GitHubRateLimitError(GitHubAPIError):
    """Rate limit exceeded (403 with X-RateLimit-Remaining: 0, or 429).

    ``retry_after`` is the number of seconds to wait before retrying,
    parsed from ``Retry-After`` header or computed from ``X-RateLimit-Reset``
    epoch timestamp. Defaults to 60s if neither header is present.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        retry_after: int = 60,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class GitHubClient:
    """Authenticated REST client for the GitHub API.

    Args:
        http_client: SDK ``HttpClient`` instance (domain-enforced to
            ``api.github.com``).
        state_client: SDK ``StateClient`` for reading the PAT token.
    """

    def __init__(
        self,
        http_client: Any,
        state_client: Any,
    ) -> None:
        self._http = http_client
        self._state = state_client

    # ---- auth helpers -----------------------------------------------------

    async def _get_token(self) -> str:
        """Read the Personal Access Token from state storage.

        Raises:
            GitHubAuthError: If no PAT is stored.
        """
        token = await self._state.get("github_pat")
        if not token:
            raise GitHubAuthError("Not authenticated — no GitHub PAT configured")
        return token

    # ---- low-level request ------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated HTTP request against the GitHub API.

        Builds the full URL from ``GITHUB_API_URL`` if ``url`` starts with
        ``/``, adds auth and accept headers, then delegates to the SDK
        HttpClient.

        Returns:
            The httpx Response object.

        Raises:
            GitHubAuthError: On 401 responses.
            GitHubRateLimitError: On 403 (rate-limited) or 429 responses.
            GitHubAPIError: On other 4xx/5xx responses.
        """
        token = await self._get_token()

        full_url = url if url.startswith("http") else f"{GITHUB_API_URL}{url}"

        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

        logger.debug("%s %s", method, full_url)
        resp = await self._http.request(method, full_url, headers=headers, **kwargs)

        # -- 401: auth error ------------------------------------------------
        if resp.status_code == 401:
            raise GitHubAuthError(
                f"GitHub authentication failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 403 or 429: potential rate limit -------------------------------
        if resp.status_code in (403, 429):
            retry_after = self._parse_retry_after(resp)
            raise GitHubRateLimitError(
                f"GitHub rate limit or forbidden: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- Other errors ---------------------------------------------------
        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp

    @staticmethod
    def _parse_retry_after(resp: Any) -> int:
        """Extract retry-after seconds from response headers.

        Checks ``Retry-After`` header first (seconds value), then falls
        back to computing delta from ``X-RateLimit-Reset`` (epoch timestamp).
        Defaults to 60 seconds if neither header provides a usable value.
        """
        # Explicit Retry-After header (seconds)
        retry_raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
        if retry_raw:
            try:
                return max(int(retry_raw), 1)
            except (ValueError, TypeError):
                pass

        # X-RateLimit-Reset (epoch timestamp)
        reset_raw = resp.headers.get("X-RateLimit-Reset") or resp.headers.get("x-ratelimit-reset")
        if reset_raw:
            try:
                reset_epoch = int(reset_raw)
                delta = reset_epoch - int(time.time())
                return max(delta, 1)
            except (ValueError, TypeError):
                pass

        return 60

    # ---- rate limit checking ----------------------------------------------

    async def _check_rate_limit(self, response_headers: dict[str, str]) -> None:
        """Check rate-limit headers and sleep if running low.

        If ``X-RateLimit-Remaining`` is present and below 100, calculates
        the time until reset from ``X-RateLimit-Reset`` and sleeps.
        """
        remaining_raw = (
            response_headers.get("X-RateLimit-Remaining")
            or response_headers.get("x-ratelimit-remaining")
        )
        if remaining_raw is None:
            return

        try:
            remaining = int(remaining_raw)
        except (ValueError, TypeError):
            return

        if remaining >= 100:
            return

        reset_raw = (
            response_headers.get("X-RateLimit-Reset")
            or response_headers.get("x-ratelimit-reset")
        )
        if not reset_raw:
            sleep_seconds = 60
        else:
            try:
                reset_epoch = int(reset_raw)
                sleep_seconds = max(reset_epoch - int(time.time()), 1)
            except (ValueError, TypeError):
                sleep_seconds = 60

        logger.warning(
            "GitHub rate limit low: %d remaining, sleeping %ds until reset",
            remaining,
            sleep_seconds,
        )
        await asyncio.sleep(sleep_seconds)

    # ---- pagination -------------------------------------------------------

    async def _paginate(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a paginated GitHub REST endpoint.

        Follows ``Link: <url>; rel="next"`` headers up to
        ``MAX_PAGINATION_PAGES`` pages. Checks rate limits after each page.

        Args:
            url: API path (relative to GITHUB_API_URL) or absolute URL.
            params: Query parameters for the first request.

        Returns:
            Flat list of all result dicts across all pages.
        """
        all_items: list[dict[str, Any]] = []
        next_url: str | None = url

        for page_num in range(MAX_PAGINATION_PAGES):
            # First request uses params; subsequent requests use the full URL
            # from the Link header which already contains query params.
            if page_num == 0:
                resp = await self._request("GET", next_url, params=params)
            else:
                resp = await self._request("GET", next_url)

            data = resp.json()
            if isinstance(data, list):
                all_items.extend(data)
            elif isinstance(data, dict):
                # Some endpoints wrap results (e.g. search)
                all_items.append(data)

            await self._check_rate_limit(dict(resp.headers))

            # Parse Link header for next page
            link_header = resp.headers.get("Link") or resp.headers.get("link") or ""
            match = _LINK_NEXT_RE.search(link_header)
            if not match:
                break
            next_url = match.group(1)

        return all_items

    # ---- convenience methods ----------------------------------------------

    async def verify_token(self) -> dict[str, Any]:
        """Verify the stored PAT by fetching the authenticated user.

        Returns:
            User dict from ``GET /user``.

        Raises:
            GitHubAuthError: If the token is invalid.
        """
        resp = await self._request("GET", "/user")
        return resp.json()

    async def fetch_repos(self) -> list[dict[str, Any]]:
        """Fetch all repositories accessible to the authenticated user.

        Returns:
            Flat list of repo dicts, sorted by most recently updated.
        """
        return await self._paginate(
            "/user/repos",
            params={"type": "all", "sort": "updated", "per_page": "100"},
        )

    async def fetch_issues(
        self,
        owner: str,
        repo: str,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all issues (including PRs) for a repository.

        Args:
            owner: Repository owner (user or org).
            repo: Repository name.
            since: Optional ISO-8601 timestamp for delta sync.

        Returns:
            Flat list of issue dicts, sorted by updated ascending.
        """
        params: dict[str, str] = {
            "state": "all",
            "sort": "updated",
            "direction": "asc",
            "per_page": "100",
        }
        if since:
            params["since"] = since

        return await self._paginate(
            f"/repos/{owner}/{repo}/issues",
            params=params,
        )

    async def patch_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a GitHub issue via PATCH.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            data: Fields to update (title, state, body, labels, etc.).

        Returns:
            Updated issue dict.

        Raises:
            GitHubAPIError: On API errors.
        """
        resp = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json=data,
        )
        return resp.json()
