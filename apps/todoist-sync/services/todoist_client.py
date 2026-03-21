"""TodoistClient — authenticated REST client for the Todoist API v2.

Wraps the SDK HttpClient for authenticated requests to Todoist's REST API.
Uses Bearer token authentication from the app's state store. No pagination
needed — Todoist returns all items in a single response for personal accounts.
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    from services.auth import (
        PAT_STATE_KEY,
        TodoistAPIError,
        TodoistAuthError,
    )
except ImportError:
    from auth import (
        PAT_STATE_KEY,
        TodoistAPIError,
        TodoistAuthError,
    )

logger = logging.getLogger("todoist.sync.client")

TODOIST_API_URL = os.environ.get("TODOIST_API_URL", "https://api.todoist.com/rest/v2")


class TodoistClient:
    """Authenticated REST client for the Todoist REST API v2.

    Args:
        http_client: SDK ``HttpClient`` instance.
        state_client: SDK ``StateClient`` for reading the stored API token.
    """

    def __init__(self, http_client: Any, state_client: Any) -> None:
        self._http = http_client
        self._state = state_client

    # ── auth helpers ──────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        """Read the Todoist API token from state storage.

        Raises:
            TodoistAuthError: If no token is stored.
        """
        token = await self._state.get(PAT_STATE_KEY)
        if not token:
            raise TodoistAuthError(
                "Not authenticated — no Todoist API token configured",
                status_code=401,
            )
        return token

    def _auth_headers(self, token: str) -> dict[str, str]:
        """Build the Authorization header for a Todoist request."""
        return {"Authorization": f"Bearer {token}"}

    # ── low-level request ─────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an authenticated HTTP request against Todoist.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path relative to TODOIST_API_URL (e.g. ``/tasks``).
            params: Optional query parameters.
            json_body: Optional JSON request body (for POST/PUT).

        Returns:
            The HTTP response object.

        Raises:
            TodoistAuthError: On 401/403 responses.
            TodoistAPIError: On other 4xx/5xx responses.
        """
        token = await self._get_token()
        url = f"{TODOIST_API_URL}{path}"
        headers = self._auth_headers(token)

        logger.debug("%s %s", method, url)

        kwargs: dict[str, Any] = {"headers": headers}
        if params:
            kwargs["params"] = params
        if json_body is not None:
            kwargs["json"] = json_body

        resp = await self._http.request(method, url, **kwargs)

        if resp.status_code in (401, 403):
            body = getattr(resp, "text", "")
            raise TodoistAuthError(
                f"Todoist authentication failed (HTTP {resp.status_code})",
                status_code=resp.status_code,
            )

        if resp.status_code >= 400:
            body = getattr(resp, "text", "")
            raise TodoistAPIError(
                f"Todoist API error (HTTP {resp.status_code}): {body[:200]}",
                status_code=resp.status_code,
            )

        return resp

    # ── convenience methods ───────────────────────────────────────────────

    async def get_tasks(
        self, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all active tasks, optionally filtered by project.

        Args:
            project_id: Optional Todoist project ID to filter by.

        Returns:
            List of task dicts from the Todoist API.
        """
        params: dict[str, str] | None = None
        if project_id:
            params = {"project_id": project_id}

        resp = await self._request("GET", "/tasks", params=params)
        return resp.json()

    async def get_projects(self) -> list[dict[str, Any]]:
        """Fetch all projects for the authenticated user.

        Returns:
            List of project dicts.
        """
        resp = await self._request("GET", "/projects")
        return resp.json()

    async def get_labels(self) -> list[dict[str, Any]]:
        """Fetch all labels for the authenticated user.

        Returns:
            List of label dicts.
        """
        resp = await self._request("GET", "/labels")
        return resp.json()

    async def close_task(self, task_id: str) -> None:
        """Mark a task as completed.

        Args:
            task_id: Todoist task ID.
        """
        await self._request("POST", f"/tasks/{task_id}/close")

    async def reopen_task(self, task_id: str) -> None:
        """Reopen a completed task.

        Args:
            task_id: Todoist task ID.
        """
        await self._request("POST", f"/tasks/{task_id}/reopen")

    async def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task.

        Args:
            data: Task fields (content, description, priority, etc.).

        Returns:
            Created task dict.
        """
        resp = await self._request("POST", "/tasks", json_body=data)
        return resp.json()

    async def update_task(
        self, task_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing task.

        Args:
            task_id: Todoist task ID.
            data: Fields to update.

        Returns:
            Updated task dict.
        """
        resp = await self._request("POST", f"/tasks/{task_id}", json_body=data)
        return resp.json()
