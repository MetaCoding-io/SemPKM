"""JiraClient — authenticated REST client for the Jira Cloud REST API v3.

Wraps the SDK HttpClient for authenticated requests to Jira's REST API.
Supports Basic auth (email + API token), JQL search with offset pagination,
and typed exceptions for all error conditions.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

logger = logging.getLogger("jira_sync.client")

# Override for testing — when set, ignores site_url from state.
JIRA_API_URL = os.environ.get("JIRA_API_URL", "")

MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class JiraAPIError(Exception):
    """Base exception for Jira API errors."""

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


class JiraAuthError(JiraAPIError):
    """Authentication error (401 or missing credentials)."""


class JiraRateLimitError(JiraAPIError):
    """Rate limit exceeded (429).

    ``retry_after`` is the number of seconds to wait before retrying,
    parsed from the ``Retry-After`` header. Defaults to 60s if the
    header is absent.
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

class JiraClient:
    """Authenticated REST client for the Jira Cloud API v3.

    Args:
        http_client: SDK ``HttpClient`` instance.
        state_client: SDK ``StateClient`` for reading credentials.
    """

    def __init__(
        self,
        http_client: Any,
        state_client: Any,
    ) -> None:
        self._http = http_client
        self._state = state_client

    # ---- auth helpers -----------------------------------------------------

    async def _get_auth_header(self) -> str:
        """Build Basic auth header from stored email + token.

        Returns:
            ``Basic <base64(email:token)>`` string.

        Raises:
            JiraAuthError: If email or token is missing from state.
        """
        email = await self._state.get("jira_email")
        token = await self._state.get("jira_token")
        if not email or not token:
            raise JiraAuthError(
                "Not authenticated — no Jira credentials configured"
            )
        credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
        return f"Basic {credentials}"

    async def _get_base_url(self) -> str:
        """Get the Jira site base URL.

        Uses ``JIRA_API_URL`` env var if set (for testing), otherwise
        reads ``jira_site_url`` from state.

        Returns:
            Base URL string (e.g. ``https://mysite.atlassian.net``).

        Raises:
            JiraAuthError: If no site URL is configured.
        """
        if JIRA_API_URL:
            return JIRA_API_URL

        site_url = await self._state.get("jira_site_url")
        if not site_url:
            raise JiraAuthError(
                "Not authenticated — no Jira site URL configured"
            )
        # Ensure no trailing slash
        return site_url.rstrip("/")

    # ---- low-level request ------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated HTTP request against the Jira API.

        Builds the full URL from base_url + path, adds auth and
        content-type headers, then delegates to the SDK HttpClient.

        Returns:
            The httpx Response object.

        Raises:
            JiraAuthError: On 401 responses.
            JiraRateLimitError: On 429 responses.
            JiraAPIError: On other 4xx/5xx responses.
        """
        auth_header = await self._get_auth_header()
        base_url = await self._get_base_url()

        full_url = (
            path if path.startswith("http") else f"{base_url}{path}"
        )

        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        logger.debug("%s %s", method, full_url)
        resp = await self._http.request(method, full_url, headers=headers, **kwargs)

        # -- 401: auth error ------------------------------------------------
        if resp.status_code == 401:
            raise JiraAuthError(
                f"Jira authentication failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 429: rate limit ------------------------------------------------
        if resp.status_code == 429:
            retry_after = self._parse_retry_after(resp)
            raise JiraRateLimitError(
                f"Jira rate limit exceeded: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- Other errors ---------------------------------------------------
        if resp.status_code >= 400:
            raise JiraAPIError(
                f"Jira API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp

    @staticmethod
    def _parse_retry_after(resp: Any) -> int:
        """Extract retry-after seconds from response headers.

        Checks the ``Retry-After`` header. Defaults to 60 seconds if
        the header is absent or unparseable.
        """
        retry_raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
        if retry_raw:
            try:
                return max(int(retry_raw), 1)
            except (ValueError, TypeError):
                pass
        return 60

    # ---- JQL search -------------------------------------------------------

    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 100,
    ) -> dict:
        """Search issues via JQL.

        Uses ``POST /rest/api/3/search`` with a JSON body containing
        the JQL query, pagination parameters, and field selection.

        Returns:
            Full response dict with ``issues``, ``startAt``,
            ``maxResults``, ``total``.
        """
        body = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ["*all"],
            "expand": ["names"],
        }
        resp = await self._request("POST", "/rest/api/3/search", json=body)
        return resp.json()

    async def search_all_issues(self, jql: str) -> list[dict]:
        """Paginated wrapper that fetches all issues matching a JQL query.

        Calls ``search_issues`` in a loop until all results are fetched.
        Enforces a maximum of ``MAX_PAGINATION_PAGES`` pages as a safety
        limit.

        Returns:
            Flat list of all issue dicts.
        """
        all_issues: list[dict] = []
        start_at = 0
        max_results = 100

        for _ in range(MAX_PAGINATION_PAGES):
            data = await self.search_issues(jql, start_at=start_at, max_results=max_results)
            issues = data.get("issues", [])
            all_issues.extend(issues)

            total = data.get("total", 0)
            start_at += len(issues)

            if start_at >= total or not issues:
                break

        return all_issues

    # ---- issue operations -------------------------------------------------

    async def get_issue(self, issue_key: str) -> dict:
        """Fetch a single issue by key.

        ``GET /rest/api/3/issue/{issue_key}``

        Returns:
            Issue dict with all fields.
        """
        resp = await self._request("GET", f"/rest/api/3/issue/{issue_key}")
        return resp.json()

    async def update_issue(self, issue_key: str, fields: dict) -> None:
        """Update issue fields.

        ``PUT /rest/api/3/issue/{issue_key}`` with body
        ``{"fields": fields}``. Returns None (204 No Content on success).
        """
        await self._request(
            "PUT",
            f"/rest/api/3/issue/{issue_key}",
            json={"fields": fields},
        )

    # ---- project operations -----------------------------------------------

    async def get_projects(self) -> list[dict]:
        """Fetch all accessible projects.

        ``GET /rest/api/3/project``

        Returns:
            List of project dicts (id, key, name).
        """
        resp = await self._request("GET", "/rest/api/3/project")
        return resp.json()

    # ---- user operations --------------------------------------------------

    async def get_user(self, account_id: str) -> dict:
        """Fetch a user by account ID.

        ``GET /rest/api/3/user?accountId={account_id}``

        Returns:
            User dict with emailAddress, displayName, etc.
        """
        resp = await self._request(
            "GET",
            f"/rest/api/3/user?accountId={account_id}",
        )
        return resp.json()

    async def get_myself(self) -> dict:
        """Fetch the authenticated user's profile.

        ``GET /rest/api/3/myself``

        Useful for verifying credentials on connect.

        Returns:
            User dict with emailAddress, displayName, accountId.
        """
        resp = await self._request("GET", "/rest/api/3/myself")
        return resp.json()
