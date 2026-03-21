"""AsanaClient — authenticated REST client for the Asana API v1.0.

Wraps the SDK HttpClient for authenticated requests to Asana's REST
endpoints. Supports OAuth token refresh on 401, offset-based pagination,
opt_fields parameter injection, rate-limit backoff via Retry-After, and
typed exceptions for all error conditions.

Every GET request passes ``opt_fields`` so responses include more than
just ``gid`` and ``resource_type``. All Asana responses wrap payloads in
``{"data": ...}`` — this client unwraps automatically.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("asana.sync.client")

ASANA_BASE_URL = os.environ.get(
    "ASANA_API_URL", "https://app.asana.com/api/1.0"
)
ASANA_TOKEN_URL = os.environ.get(
    "ASANA_TOKEN_URL", "https://app.asana.com/-/oauth_token"
)

MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AsanaAPIError(Exception):
    """Base exception for Asana API errors."""

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


class AsanaAuthError(AsanaAPIError):
    """Authentication/authorization error (401/403)."""


class AsanaRateLimitError(AsanaAPIError):
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


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class AsanaClient:
    """Authenticated REST client for the Asana API v1.0.

    Args:
        http_client: SDK ``HttpClient`` instance (domain-enforced to
            ``app.asana.com``).
        state_client: SDK ``StateClient`` for reading/writing auth tokens.
        client_id: OAuth application client ID (needed for token refresh).
        client_secret: OAuth application client secret (needed for token
            refresh).
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

    async def _get_headers(self) -> dict[str, str]:
        """Build request headers from stored credentials.

        Reads ``access_token`` from state and returns Authorization +
        Accept headers.

        Raises:
            AsanaAuthError: If no access token is stored.
        """
        token = await self._state.get("access_token")
        if not token:
            raise AsanaAuthError("Not authenticated")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _handle_token_refresh(self) -> None:
        """Exchange the stored refresh token for a new access token.

        Acquires ``_refreshing`` lock to prevent concurrent refresh
        attempts. Stores the new ``access_token`` via StateClient.

        Raises:
            AsanaAuthError: If no refresh token is available or if the
                token endpoint returns an error.
        """
        async with self._refreshing:
            refresh_token = await self._state.get("refresh_token")
            if not refresh_token:
                raise AsanaAuthError(
                    "Token refresh not available — no refresh token",
                    status_code=401,
                )

            logger.info("Refreshing Asana OAuth token")
            resp = await self._http.post(
                ASANA_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id or "",
                    "client_secret": self._client_secret or "",
                    "refresh_token": refresh_token,
                },
            )

            if resp.status_code != 200:
                body = resp.text
                raise AsanaAuthError(
                    f"Token refresh failed: {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            data = resp.json()
            new_access = data.get("access_token", "")

            if new_access:
                await self._state.set("access_token", new_access)

            logger.info("Asana OAuth token refreshed successfully")

    # ---- request methods --------------------------------------------------

    async def _raw_request(
        self,
        method: str,
        url: str,
        *,
        allow_refresh: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request and return the full JSON body.

        Handles 401 (token refresh + single retry), 403, 429 (parse
        Retry-After), and 5xx errors. Returns the complete response JSON
        including the ``data`` and ``next_page`` wrapper fields.

        Args:
            method: HTTP method ("GET", "POST", "PATCH", etc.).
            url: Full URL to request.
            allow_refresh: Whether to attempt token refresh on 401.
            **kwargs: Additional arguments passed to the HTTP client.

        Returns:
            Full parsed JSON response body (dict).

        Raises:
            AsanaAuthError: On 401/403 (after refresh attempt if
                applicable).
            AsanaRateLimitError: On 429 with ``retry_after`` seconds.
            AsanaAPIError: On other HTTP errors.
        """
        headers = await self._get_headers()
        # Merge any caller-provided headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        http_method = getattr(self._http, method.lower())
        resp = await http_method(url, headers=headers, **kwargs)

        # -- 401: try token refresh and retry once --------------------------
        if resp.status_code == 401:
            if allow_refresh:
                try:
                    await self._handle_token_refresh()
                except AsanaAuthError:
                    raise
                return await self._raw_request(
                    method, url, allow_refresh=False, **kwargs
                )
            raise AsanaAuthError(
                f"Unauthorized after token refresh: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 403: forbidden -------------------------------------------------
        if resp.status_code == 403:
            raise AsanaAuthError(
                f"Forbidden: {resp.status_code}",
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
            raise AsanaRateLimitError(
                "Rate limited by Asana API",
                status_code=429,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- 5xx: server error ----------------------------------------------
        if resp.status_code >= 500:
            raise AsanaAPIError(
                f"Asana API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- Other client errors --------------------------------------------
        if resp.status_code >= 400:
            raise AsanaAPIError(
                f"Asana API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp.json()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        allow_refresh: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request, unwrapping the data envelope.

        Delegates to ``_raw_request`` and extracts the ``data`` field
        from Asana's ``{"data": ...}`` response wrapper.

        Returns:
            The ``data`` field from the response JSON (dict or list),
            or the full response JSON if no ``data`` key is present.
        """
        body = await self._raw_request(
            method, url, allow_refresh=allow_refresh, **kwargs
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    # ---- pagination -------------------------------------------------------

    async def _paginated_get(
        self,
        url: str,
        opt_fields: str | None = None,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """GET with offset-based pagination and opt_fields.

        Asana paginates via ``next_page.offset``. Each page returns up
        to ``limit`` items plus a ``next_page`` dict (or ``null``).

        Uses ``_raw_request`` to get both the ``data`` array and the
        ``next_page`` pagination cursor from each response.

        Args:
            url: Base endpoint URL (no query string).
            opt_fields: Comma-separated field names to request.
            params: Additional query parameters.

        Returns:
            Aggregated list of items from all pages.
        """
        all_items: list[dict[str, Any]] = []
        offset: str | None = None

        for _ in range(MAX_PAGINATION_PAGES):
            query_parts: list[str] = ["limit=100"]
            if opt_fields:
                query_parts.append(f"opt_fields={opt_fields}")
            if offset:
                query_parts.append(f"offset={offset}")
            if params:
                for key, value in params.items():
                    query_parts.append(f"{key}={value}")

            full_url = f"{url}?{'&'.join(query_parts)}"
            body = await self._raw_request("GET", full_url)

            page_data = body.get("data", [])
            if isinstance(page_data, list):
                all_items.extend(page_data)

            next_page = body.get("next_page")
            if next_page and isinstance(next_page, dict):
                offset = next_page.get("offset")
                if not offset:
                    break
            else:
                break

        return all_items

    # ---- resource endpoints -----------------------------------------------

    async def get_workspaces(self) -> list[dict[str, Any]]:
        """Fetch the user's workspaces.

        Returns:
            List of workspace dicts with ``gid`` and ``name``.
        """
        url = f"{ASANA_BASE_URL}/workspaces"
        return await self._paginated_get(url, opt_fields="name")

    async def get_projects(
        self,
        workspace_gid: str,
    ) -> list[dict[str, Any]]:
        """Fetch non-archived projects in a workspace.

        Args:
            workspace_gid: Workspace GID.

        Returns:
            List of project dicts with ``gid``, ``name``, ``archived``.
            Archived projects are filtered out.
        """
        url = f"{ASANA_BASE_URL}/workspaces/{workspace_gid}/projects"
        all_projects = await self._paginated_get(
            url, opt_fields="name,archived"
        )
        return [p for p in all_projects if not p.get("archived", False)]

    async def get_sections(
        self,
        project_gid: str,
    ) -> list[dict[str, Any]]:
        """Fetch sections in a project.

        Args:
            project_gid: Project GID.

        Returns:
            List of section dicts with ``gid`` and ``name``.
        """
        url = f"{ASANA_BASE_URL}/projects/{project_gid}/sections"
        return await self._paginated_get(url, opt_fields="name")

    async def get_custom_fields(
        self,
        project_gid: str,
    ) -> list[dict[str, Any]]:
        """Fetch custom field settings for a project.

        Returns the ``custom_field`` sub-object from each setting entry,
        including field name, type, and enum options.

        Args:
            project_gid: Project GID.

        Returns:
            List of custom field dicts, each with at least ``gid``,
            ``name``, ``resource_subtype``, and (for enum fields)
            ``enum_options``.
        """
        url = (
            f"{ASANA_BASE_URL}/projects/{project_gid}"
            f"/custom_field_settings"
        )
        opt_fields = (
            "custom_field,"
            "custom_field.name,"
            "custom_field.resource_subtype,"
            "custom_field.enum_options,"
            "custom_field.enum_options.name"
        )
        settings = await self._paginated_get(url, opt_fields=opt_fields)
        return [
            s["custom_field"]
            for s in settings
            if "custom_field" in s
        ]

    async def get_tasks(
        self,
        project_gid: str,
        opt_fields: str,
        modified_since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch tasks in a project.

        Args:
            project_gid: Project GID.
            opt_fields: Comma-separated field names to request.
            modified_since: ISO 8601 timestamp for incremental sync.

        Returns:
            List of task dicts with requested fields.
        """
        url = f"{ASANA_BASE_URL}/projects/{project_gid}/tasks"
        params: dict[str, str] = {}
        if modified_since:
            params["modified_since"] = modified_since
        return await self._paginated_get(
            url, opt_fields=opt_fields, params=params
        )

    async def get_subtasks(
        self,
        task_gid: str,
        opt_fields: str,
    ) -> list[dict[str, Any]]:
        """Fetch subtasks of a task.

        Args:
            task_gid: Parent task GID.
            opt_fields: Comma-separated field names to request.

        Returns:
            List of subtask dicts with requested fields.
        """
        url = f"{ASANA_BASE_URL}/tasks/{task_gid}/subtasks"
        return await self._paginated_get(url, opt_fields=opt_fields)

    async def get_user_me(self) -> dict[str, Any]:
        """Fetch the authenticated user's profile.

        Returns:
            User dict with ``gid``, ``name``, and ``email``.
        """
        url = f"{ASANA_BASE_URL}/users/me?opt_fields=name,email"
        return await self._request("GET", url)

    async def patch_task(
        self,
        task_gid: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a task via PATCH (partial update).

        Args:
            task_gid: Task GID to update.
            data: Partial task body (field values to update).

        Returns:
            Updated task dict from the API.
        """
        url = f"{ASANA_BASE_URL}/tasks/{task_gid}"
        return await self._request("PATCH", url, json={"data": data})

    async def add_task_to_section(
        self,
        section_gid: str,
        task_gid: str,
    ) -> None:
        """Move a task into a section.

        Args:
            section_gid: Target section GID.
            task_gid: Task GID to move.
        """
        url = f"{ASANA_BASE_URL}/sections/{section_gid}/addTask"
        await self._request(
            "POST", url, json={"data": {"task": task_gid}}
        )
