"""MondayClient — authenticated GraphQL client for the Monday.com API.

Wraps the SDK HttpClient for authenticated requests to Monday.com's GraphQL
endpoint (``https://api.monday.com/v2``).  Supports complexity budget tracking,
cursor-based pagination, and a typed exception hierarchy.

Monday.com specifics vs. other GraphQL APIs:
- Auth header is bare ``Authorization: <api_token>`` — no Bearer/Basic prefix.
- Complexity budget: each query costs points; exceeding the budget returns a
  200 response with ``errors[0].extensions.code == "COMPLEXITY"``.
- Column value format asymmetry: reads use structured JSON; writes use a
  JSON *string* passed as a GraphQL variable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("monday_sync.client")

MONDAY_API_URL = os.environ.get("MONDAY_API_URL", "https://api.monday.com/v2")
MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MondayApiError(Exception):
    """Base exception for Monday.com API errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code (``None`` for GraphQL-level errors
            returned with HTTP 200).
        response_body: Raw response text for debugging.
    """

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


class MondayAuthError(MondayApiError):
    """Authentication error — 401 Unauthorized or missing credentials."""


class MondayRateLimitError(MondayApiError):
    """Rate limit exceeded — HTTP 429.

    ``retry_after`` is seconds to wait before retrying, parsed from the
    ``Retry-After`` response header (default 60 s).
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


class MondayComplexityError(MondayApiError):
    """Complexity budget exceeded.

    Monday.com returns this as HTTP 200 with an error body whose
    ``extensions.code`` is ``"COMPLEXITY"``.  ``reset_in_seconds``
    indicates when the complexity budget resets.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = 200,
        response_body: str | None = None,
        reset_in_seconds: int = 60,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.reset_in_seconds = reset_in_seconds


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class MondayClient:
    """Authenticated GraphQL client for the Monday.com API.

    Args:
        http_client: SDK ``HttpClient`` instance.
        state_client: SDK ``StateClient`` for reading stored API token.
    """

    def __init__(self, http_client: Any, state_client: Any) -> None:
        self._http = http_client
        self._state = state_client

    # ---- auth helper ------------------------------------------------------

    async def _get_auth_header(self) -> dict[str, str]:
        """Build the Authorization header from stored credentials.

        Monday.com uses the raw token — no "Bearer" prefix.

        Raises:
            MondayAuthError: If no API token is stored.
        """
        token = await self._state.get("monday_api_token")
        if not token:
            raise MondayAuthError("Not authenticated — no Monday.com API token stored")
        return {"Authorization": token}

    # ---- core query -------------------------------------------------------

    async def _execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against Monday.com.

        Handles:
        - HTTP 401 → ``MondayAuthError``
        - HTTP 429 → ``MondayRateLimitError`` (parses ``Retry-After``)
        - 200 with GraphQL complexity error → ``MondayComplexityError``
        - 200 with other GraphQL errors → ``MondayApiError``
        - Logs complexity budget at DEBUG level when present

        Returns:
            The ``data`` dict from the GraphQL response.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        headers = await self._get_auth_header()
        headers["Content-Type"] = "application/json"

        logger.debug("GraphQL request: %s", query[:120])
        resp = await self._http.request(
            "POST",
            MONDAY_API_URL,
            json=payload,
            headers=headers,
        )

        # -- HTTP-level errors ----------------------------------------------
        if resp.status_code == 401:
            raise MondayAuthError(
                "Unauthorized",
                status_code=401,
                response_body=resp.text,
            )

        if resp.status_code == 429:
            retry_after_raw = resp.headers.get("Retry-After", "60")
            try:
                retry_after = int(retry_after_raw)
            except (ValueError, TypeError):
                retry_after = 60
            raise MondayRateLimitError(
                "Rate limited by Monday.com API",
                status_code=429,
                response_body=resp.text,
                retry_after=retry_after,
            )

        if resp.status_code >= 400:
            raise MondayApiError(
                f"Monday.com API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- Parse JSON body ------------------------------------------------
        body = resp.json()

        # -- Complexity tracking --------------------------------------------
        complexity = body.get("complexity")
        if complexity and isinstance(complexity, dict):
            logger.debug(
                "Complexity budget — after: %s, reset_in: %ss",
                complexity.get("after"),
                complexity.get("reset_in_x_seconds"),
            )

        # -- GraphQL-level errors -------------------------------------------
        errors = body.get("errors")
        if errors:
            first_error = errors[0] if errors else {}
            first_msg = first_error.get("message", "Unknown GraphQL error")
            extensions = first_error.get("extensions", {})

            # Complexity error detection: check extensions.code or message
            is_complexity = (
                extensions.get("code") == "COMPLEXITY"
                or "complexity" in first_msg.lower()
            )
            if is_complexity:
                reset_in = extensions.get("reset_in_x_seconds", 60)
                # Also check top-level complexity field
                if complexity and isinstance(complexity, dict):
                    reset_in = complexity.get("reset_in_x_seconds", reset_in)
                raise MondayComplexityError(
                    first_msg,
                    status_code=resp.status_code,
                    response_body=resp.text,
                    reset_in_seconds=int(reset_in),
                )

            raise MondayApiError(
                first_msg,
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return body.get("data", {})

    # ---- convenience methods — queries ------------------------------------

    async def get_me(self) -> dict[str, Any]:
        """Get the authenticated user's profile.

        Returns:
            Dict with ``id``, ``name``, ``email``.
        """
        data = await self._execute_query("{ me { id name email } }")
        return data.get("me", {})

    async def get_boards(self) -> list[dict[str, Any]]:
        """Get all active boards.

        Returns:
            List of board dicts with ``id``, ``name``, ``state``.
        """
        data = await self._execute_query(
            '{ boards(limit: 100, state: active) { id name state } }'
        )
        return data.get("boards", [])

    async def get_board_columns(self, board_id: int) -> list[dict[str, Any]]:
        """Get column definitions for a board.

        Args:
            board_id: Monday.com board ID.

        Returns:
            List of column dicts with ``id``, ``title``, ``type``,
            ``settings_str``.
        """
        data = await self._execute_query(
            "{ boards(ids: [%d]) { columns { id title type settings_str } } }"
            % board_id
        )
        boards = data.get("boards", [])
        if not boards:
            return []
        return boards[0].get("columns", [])

    async def get_board_groups(self, board_id: int) -> list[dict[str, Any]]:
        """Get groups for a board.

        Args:
            board_id: Monday.com board ID.

        Returns:
            List of group dicts with ``id``, ``title``.
        """
        data = await self._execute_query(
            "{ boards(ids: [%d]) { groups { id title } } }" % board_id
        )
        boards = data.get("boards", [])
        if not boards:
            return []
        return boards[0].get("groups", [])

    async def get_board_items(
        self,
        board_id: int,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Get a single page of items from a board using cursor pagination.

        Args:
            board_id: Monday.com board ID.
            limit: Max items per page (default 100).
            cursor: Pagination cursor from a previous call (``None`` for
                the first page).

        Returns:
            Dict with ``items`` (list) and ``cursor`` (str or None).
        """
        if cursor:
            query = (
                '{ boards(ids: [%d]) { items_page(limit: %d, cursor: "%s") '
                "{ cursor items { id name group { id title } column_values { id text type value } } } } }"
                % (board_id, limit, cursor)
            )
        else:
            query = (
                "{ boards(ids: [%d]) { items_page(limit: %d) "
                "{ cursor items { id name group { id title } column_values { id text type value } } } } }"
                % (board_id, limit)
            )

        data = await self._execute_query(query)
        boards = data.get("boards", [])
        if not boards:
            return {"items": [], "cursor": None}
        items_page = boards[0].get("items_page", {})
        return {
            "items": items_page.get("items", []),
            "cursor": items_page.get("cursor"),
        }

    async def get_users(self, user_ids: list[int]) -> list[dict[str, Any]]:
        """Get user details by IDs.

        Args:
            user_ids: List of Monday.com user IDs.

        Returns:
            List of user dicts with ``id``, ``name``, ``email``.
        """
        ids_str = ", ".join(str(uid) for uid in user_ids)
        data = await self._execute_query(
            "{ users(ids: [%s]) { id name email } }" % ids_str
        )
        return data.get("users", [])

    async def get_tags(self, tag_ids: list[int]) -> list[dict[str, Any]]:
        """Get tag details by IDs.

        Args:
            tag_ids: List of Monday.com tag IDs.

        Returns:
            List of tag dicts with ``id``, ``name``.
        """
        ids_str = ", ".join(str(tid) for tid in tag_ids)
        data = await self._execute_query(
            "{ tags(ids: [%s]) { id name } }" % ids_str
        )
        return data.get("tags", [])

    # ---- convenience methods — mutations ----------------------------------

    async def change_multiple_column_values(
        self,
        board_id: int,
        item_id: int,
        column_values_json: str,
    ) -> dict[str, Any]:
        """Update multiple column values on an item.

        Args:
            board_id: Board ID containing the item.
            item_id: Item ID to update.
            column_values_json: JSON string of column values to set.

        Returns:
            The updated item dict (``id``, ``name``).
        """
        query = (
            "mutation { change_multiple_column_values("
            "board_id: %d, item_id: %d, "
            'column_values: %s'
            ") { id name } }"
            % (board_id, item_id, json.dumps(column_values_json))
        )
        data = await self._execute_query(query)
        return data.get("change_multiple_column_values", {})

    async def create_item(
        self,
        board_id: int,
        group_id: str,
        name: str,
        column_values_json: str | None = None,
    ) -> dict[str, Any]:
        """Create a new item on a board.

        Args:
            board_id: Board ID to create the item in.
            group_id: Group ID within the board.
            name: Item name.
            column_values_json: Optional JSON string of column values.

        Returns:
            The created item dict (``id``, ``name``).
        """
        if column_values_json:
            query = (
                "mutation { create_item("
                "board_id: %d, group_id: %s, "
                "item_name: %s, column_values: %s"
                ") { id name } }"
                % (
                    board_id,
                    json.dumps(group_id),
                    json.dumps(name),
                    json.dumps(column_values_json),
                )
            )
        else:
            query = (
                "mutation { create_item("
                "board_id: %d, group_id: %s, "
                "item_name: %s"
                ") { id name } }"
                % (board_id, json.dumps(group_id), json.dumps(name))
            )
        data = await self._execute_query(query)
        return data.get("create_item", {})

    # ---- paginated wrapper -----------------------------------------------

    async def get_subitems(self, item_ids: list[int]) -> list[dict[str, Any]]:
        """Get subitems for a list of parent item IDs.

        Args:
            item_ids: List of Monday.com parent item IDs.

        Returns:
            Flat list of subitem dicts, each augmented with
            ``parent_item_id`` from the containing parent item.
        """
        if not item_ids:
            return []
        ids_str = ", ".join(str(iid) for iid in item_ids)
        query = (
            "{ items(ids: [%s]) { id subitems { id name "
            "group { id title } "
            "column_values { id text type value } } } }" % ids_str
        )
        data = await self._execute_query(query)
        items = data.get("items", [])
        result: list[dict[str, Any]] = []
        for item in items:
            parent_id = item.get("id")
            for sub in item.get("subitems", []) or []:
                sub["parent_item_id"] = parent_id
                result.append(sub)
        return result

    async def get_all_board_items(self, board_id: int) -> list[dict[str, Any]]:
        """Get all items from a board, handling cursor pagination.

        Iterates through pages until the cursor is ``None`` or the
        safety limit (``MAX_PAGINATION_PAGES``) is reached.

        Args:
            board_id: Monday.com board ID.

        Returns:
            Aggregated list of all item dicts.
        """
        all_items: list[dict[str, Any]] = []
        cursor: str | None = None

        for page in range(MAX_PAGINATION_PAGES):
            result = await self.get_board_items(board_id, cursor=cursor)
            items = result.get("items", [])
            all_items.extend(items)

            cursor = result.get("cursor")
            if cursor is None:
                break

        return all_items
