"""LinearClient — authenticated GraphQL client for the Linear API.

Wraps the SDK HttpClient for authenticated requests to Linear's GraphQL
endpoint. Supports OAuth token refresh on 401, API key fallback, cursor-based
pagination, and typed exceptions for all error conditions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("linear_sync.client")

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"

MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LinearAPIError(Exception):
    """Base exception for Linear API errors."""

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


class LinearAuthError(LinearAPIError):
    """Authentication/authorization error (401/403)."""


class LinearRateLimitError(LinearAPIError):
    """Rate limit exceeded (429).

    ``retry_after`` is the number of seconds to wait before retrying,
    parsed from the ``Retry-After`` response header (default 60s).
    """

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response_body: str | None = None,
        retry_after: int = 60,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


class LinearQueryError(LinearAPIError):
    """GraphQL-level error (200 response with ``errors`` array)."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LinearClient:
    """Authenticated GraphQL client for the Linear API.

    Args:
        http_client: SDK ``HttpClient`` instance (domain-enforced to
            ``api.linear.app``).
        state_client: SDK ``StateClient`` for reading/writing auth tokens.
        client_id: OAuth application client ID (needed for token refresh).
        client_secret: OAuth application client secret (needed for token refresh).
    """

    def __init__(
        self,
        http_client: Any,
        state_client: Any,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._http = http_client
        self._state = state_client
        self._client_id = client_id
        self._client_secret = client_secret
        self._refreshing = asyncio.Lock()

    # ---- auth helpers -----------------------------------------------------

    async def _get_auth_header(self) -> dict[str, str]:
        """Build the Authorization header from stored credentials.

        Checks ``access_token`` first (OAuth), then falls back to ``api_key``.

        Raises:
            LinearAuthError: If neither token nor API key is stored.
        """
        token = await self._state.get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

        api_key = await self._state.get("api_key")
        if api_key:
            return {"Authorization": f"Bearer {api_key}"}

        raise LinearAuthError("Not authenticated")

    async def _handle_token_refresh(self) -> None:
        """Exchange the stored refresh token for a new access token.

        Acquires ``_refreshing`` lock to prevent concurrent refresh attempts.
        Stores the new ``access_token`` and ``refresh_token`` via StateClient.

        Raises:
            LinearAuthError: If no refresh token is available (API key auth)
                or if the token endpoint returns an error.
        """
        async with self._refreshing:
            refresh_token = await self._state.get("refresh_token")
            if not refresh_token:
                raise LinearAuthError(
                    "Token refresh not available with API key auth",
                    status_code=401,
                )

            logger.info("Refreshing Linear OAuth token")
            resp = await self._http.post(
                LINEAR_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id or "",
                    "client_secret": self._client_secret or "",
                    "refresh_token": refresh_token,
                },
            )

            if resp.status_code != 200:
                body = resp.text
                raise LinearAuthError(
                    f"Token refresh failed: {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            data = resp.json()
            new_access = data.get("access_token", "")
            new_refresh = data.get("refresh_token", "")

            if new_access:
                await self._state.set("access_token", new_access)
            if new_refresh:
                await self._state.set("refresh_token", new_refresh)

            logger.info("Linear OAuth token refreshed successfully")

    # ---- query methods ----------------------------------------------------

    async def query(
        self,
        graphql: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against the Linear API.

        Handles 401 (token refresh + single retry), 429 (rate limit), and
        GraphQL-level errors (200 with ``errors`` array).

        Args:
            graphql: GraphQL query string.
            variables: Optional query variables.

        Returns:
            The ``data`` dict from the GraphQL response.

        Raises:
            LinearAuthError: On 401/403 (after refresh attempt if applicable).
            LinearRateLimitError: On 429 with ``retry_after`` seconds.
            LinearQueryError: On GraphQL-level errors.
            LinearAPIError: On other HTTP errors.
        """
        return await self._execute_query(graphql, variables, allow_refresh=True)

    async def _execute_query(
        self,
        graphql: str,
        variables: dict[str, Any] | None = None,
        allow_refresh: bool = True,
    ) -> dict[str, Any]:
        """Internal query execution with optional token refresh retry."""
        payload = {"query": graphql, "variables": dict(variables) if variables else {}}
        headers = await self._get_auth_header()

        logger.debug("GraphQL request: %s", graphql[:80])
        resp = await self._http.post(
            LINEAR_GRAPHQL_URL,
            json=payload,
            headers=headers,
        )

        # -- 401: try token refresh and retry once --------------------------
        if resp.status_code == 401:
            if allow_refresh:
                try:
                    await self._handle_token_refresh()
                except LinearAuthError:
                    raise
                return await self._execute_query(graphql, variables, allow_refresh=False)
            raise LinearAuthError(
                f"Unauthorized after token refresh: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 429: rate limit ------------------------------------------------
        if resp.status_code == 429:
            retry_after_raw = resp.headers.get("Retry-After", "60")
            try:
                retry_after = int(retry_after_raw)
            except (ValueError, TypeError):
                retry_after = 60
            raise LinearRateLimitError(
                f"Rate limited by Linear API",
                status_code=429,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- Other errors ---------------------------------------------------
        if resp.status_code == 403:
            raise LinearAuthError(
                f"Forbidden: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        if resp.status_code >= 400:
            raise LinearAPIError(
                f"Linear API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- Parse JSON and check for GraphQL errors ------------------------
        body = resp.json()

        if "errors" in body:
            errors = body["errors"]
            first_msg = errors[0].get("message", "Unknown GraphQL error") if errors else "Unknown GraphQL error"
            raise LinearQueryError(
                first_msg,
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return body.get("data", {})

    # ---- pagination -------------------------------------------------------

    async def query_paginated(
        self,
        graphql: str,
        variables: dict[str, Any] | None,
        path_to_nodes: str,
        path_to_pageinfo: str,
    ) -> list[dict[str, Any]]:
        """Execute a paginated GraphQL query, aggregating all pages.

        Uses cursor-based pagination: injects ``$after`` variable on each
        iteration, extracts nodes and pageInfo via dot-delimited paths.

        Args:
            graphql: GraphQL query string (must accept ``$after: String``).
            variables: Base variables (``after`` will be injected).
            path_to_nodes: Dot-delimited path to nodes array (e.g. ``"issues.nodes"``).
            path_to_pageinfo: Dot-delimited path to pageInfo (e.g. ``"issues.pageInfo"``).

        Returns:
            Aggregated list of all node dicts across pages.
        """
        all_nodes: list[dict[str, Any]] = []
        cursor: str | None = None
        vars_ = dict(variables or {})

        for page in range(MAX_PAGINATION_PAGES):
            if cursor is not None:
                vars_["after"] = cursor
            elif "after" in vars_:
                del vars_["after"]

            data = await self.query(graphql, vars_)

            nodes = _resolve_path(data, path_to_nodes)
            if nodes is None:
                break
            all_nodes.extend(nodes)

            page_info = _resolve_path(data, path_to_pageinfo)
            if page_info is None or not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if cursor is None:
                break

        return all_nodes

    # ---- convenience methods ----------------------------------------------

    async def get_viewer(self) -> dict[str, Any]:
        """Get the authenticated user's profile."""
        data = await self.query("{ viewer { id name email } }")
        return data.get("viewer", {})

    async def get_teams(self) -> list[dict[str, Any]]:
        """Get the list of teams in the workspace."""
        data = await self.query(
            "{ teams { nodes { id name key description } } }"
        )
        return data.get("teams", {}).get("nodes", [])

    async def get_organization(self) -> dict[str, Any]:
        """Get workspace/organization info."""
        data = await self.query(
            "{ organization { id name urlKey } }"
        )
        return data.get("organization", {})

    async def get_workflow_states(self, team_id: str) -> list[dict[str, Any]]:
        """Get workflow states for a team.

        Returns a list of ``{id, name, type}`` dicts representing
        the team's workflow state definitions.
        """
        data = await self.query(
            'query($teamId: String!) { team(id: $teamId) { states { nodes { id name type } } } }',
            {"teamId": team_id},
        )
        return data.get("team", {}).get("states", {}).get("nodes", [])

    async def update_issue(
        self,
        issue_id: str,
        input_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a Linear issue via the ``issueUpdate`` mutation.

        Parameters
        ----------
        issue_id:
            The Linear issue UUID (not the human-readable identifier).
        input_dict:
            Fields to update, matching ``IssueUpdateInput`` schema.

        Returns
        -------
        dict
            The ``issueUpdate`` response data including ``success``
            and ``issue { id updatedAt }``.
        """
        mutation = (
            "mutation($id: String!, $input: IssueUpdateInput!) {"
            "  issueUpdate(id: $id, input: $input) {"
            "    success"
            "    issue { id updatedAt }"
            "  }"
            "}"
        )
        data = await self.query(mutation, {"id": issue_id, "input": input_dict})
        return data.get("issueUpdate", {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_path(data: dict[str, Any], path: str) -> Any:
    """Walk a dot-delimited path into a nested dict.

    Returns ``None`` if any segment is missing.
    """
    current: Any = data
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current
