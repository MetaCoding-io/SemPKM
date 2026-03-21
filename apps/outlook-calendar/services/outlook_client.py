"""OutlookClient — authenticated REST client for the Microsoft Graph API.

Wraps the SDK HttpClient for authenticated requests to Microsoft Graph
calendar endpoints.  Supports OAuth token refresh on 401 (via auth.py's
refresh_if_expired), @odata.nextLink pagination, delta queries with
@odata.deltaLink tracking, and patch_event for RSVP updates.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("outlook.sync.client")

OUTLOOK_API_URL = os.environ.get(
    "OUTLOOK_API_URL",
    "https://graph.microsoft.com/v1.0",
)

MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OutlookAPIError(Exception):
    """Base exception for Microsoft Graph API errors."""

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


class OutlookAuthError(OutlookAPIError):
    """Authentication/authorization error (401/403)."""


class OutlookRateLimitError(OutlookAPIError):
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

class OutlookClient:
    """Authenticated REST client for the Microsoft Graph API (Calendar).

    Args:
        http_client: SDK ``HttpClient`` instance.
        state_client: SDK ``StateClient`` for reading/writing auth tokens.
        client_id: Azure AD application (client) ID (needed for token refresh).
        client_secret: Azure AD client secret (needed for token refresh).
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
        """Build request headers with Bearer token from state.

        Raises:
            OutlookAuthError: If no access token is stored.
        """
        token = await self._state.get("access_token")
        if not token:
            raise OutlookAuthError("Not authenticated")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _handle_token_refresh(self) -> None:
        """Refresh access token using auth.py's refresh_if_expired.

        Acquires ``_refreshing`` lock to prevent concurrent refresh
        attempts.  Delegates to ``auth.refresh_if_expired`` which reads
        the refresh token from state, calls the Microsoft token endpoint,
        and stores the new access token.

        Raises:
            OutlookAuthError: If refresh fails or no refresh token available.
        """
        try:
            from services.auth import refresh_if_expired
        except ImportError:
            try:
                from auth import refresh_if_expired
            except ImportError:
                raise OutlookAuthError(
                    "Cannot import auth module for token refresh",
                    status_code=401,
                )

        async with self._refreshing:
            logger.info("Refreshing Microsoft OAuth token")
            try:
                await refresh_if_expired(
                    self._http,
                    self._state,
                    self._client_id or "",
                    self._client_secret or "",
                )
                logger.info("Microsoft OAuth token refreshed successfully")
            except Exception as exc:
                raise OutlookAuthError(
                    f"Token refresh failed: {exc}",
                    status_code=getattr(exc, "status_code", 401),
                    response_body=getattr(exc, "response_body", str(exc)),
                )

    # ---- request methods --------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        allow_refresh: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request with error handling.

        Handles 401 (token refresh + single retry), 403, 429 (parse
        Retry-After), and 5xx errors.

        Args:
            method: HTTP method ("GET", "POST", "PATCH", etc.).
            url: Full URL to request.
            allow_refresh: Whether to attempt token refresh on 401.
            **kwargs: Additional arguments passed to the HTTP client.

        Returns:
            Parsed JSON response body.

        Raises:
            OutlookAuthError: On 401/403 (after refresh attempt if applicable).
            OutlookRateLimitError: On 429 with ``retry_after`` seconds.
            OutlookAPIError: On other HTTP errors.
        """
        headers = await self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        logger.debug("%s %s", method, url)

        http_method = getattr(self._http, method.lower())
        resp = await http_method(url, headers=headers, **kwargs)

        # -- 401: try token refresh and retry once --------------------------
        if resp.status_code == 401:
            if allow_refresh:
                try:
                    await self._handle_token_refresh()
                except OutlookAuthError:
                    raise
                return await self._request(
                    method, url, allow_refresh=False, **kwargs
                )
            raise OutlookAuthError(
                f"Unauthorized after token refresh: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 403: forbidden -------------------------------------------------
        if resp.status_code == 403:
            raise OutlookAuthError(
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
            raise OutlookRateLimitError(
                "Rate limited by Microsoft Graph API",
                status_code=429,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- 5xx: server error ----------------------------------------------
        if resp.status_code >= 500:
            raise OutlookAPIError(
                f"Microsoft Graph API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- Other client errors --------------------------------------------
        if resp.status_code >= 400:
            raise OutlookAPIError(
                f"Microsoft Graph API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp.json()

    # ---- calendar methods -------------------------------------------------

    async def get_calendar_list(self) -> list[dict[str, Any]]:
        """Fetch the user's calendar list with @odata.nextLink pagination.

        Returns a list of calendar dicts, each with at least:
        ``id``, ``name``, ``isDefaultCalendar``, ``canEdit``.

        Raises:
            OutlookAuthError: On authentication/authorization failure.
            OutlookRateLimitError: On rate limit.
            OutlookAPIError: On other API errors.
        """
        all_calendars: list[dict[str, Any]] = []
        url: str | None = f"{OUTLOOK_API_URL}/me/calendars"

        for _ in range(MAX_PAGINATION_PAGES):
            if url is None:
                break

            data = await self._request("GET", url)

            for item in data.get("value", []):
                all_calendars.append({
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "isDefaultCalendar": item.get("isDefaultCalendar", False),
                    "canEdit": item.get("canEdit", False),
                })

            url = data.get("@odata.nextLink")

        return all_calendars

    # ---- events methods ---------------------------------------------------

    async def get_events_delta(
        self,
        calendar_id: str,
        delta_link: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Fetch calendar events using Microsoft Graph delta queries.

        On the first call (no *delta_link*), performs a full sync of
        the calendar.  Subsequent calls with a *delta_link* return only
        changes since the last sync.

        Paginates via ``@odata.nextLink`` and returns the final
        ``@odata.deltaLink`` for the next incremental call.

        Deleted events are included with ``@removed`` key set.

        Args:
            calendar_id: Outlook calendar ID.
            delta_link: Delta link from a previous call for incremental sync.

        Returns:
            ``(events, delta_link)`` tuple. ``delta_link`` is the token
            for the next incremental sync.

        Raises:
            OutlookAPIError: On API errors.
        """
        all_events: list[dict] = []
        new_delta_link: str | None = None

        if delta_link:
            url: str | None = delta_link
        else:
            url = (
                f"{OUTLOOK_API_URL}/me/calendars/{calendar_id}"
                f"/events/delta?$top=50"
            )

        for _ in range(MAX_PAGINATION_PAGES):
            if url is None:
                break

            data = await self._request("GET", url)

            all_events.extend(data.get("value", []))
            new_delta_link = data.get("@odata.deltaLink")
            url = data.get("@odata.nextLink")

        return (all_events, new_delta_link)

    async def patch_event(
        self,
        calendar_id: str,
        event_id: str,
        data: dict,
    ) -> dict:
        """Update an event via PATCH (partial update).

        Used for RSVP push-back: sends a partial body with the updated
        responseStatus.

        Args:
            calendar_id: Outlook calendar ID.
            event_id: Microsoft Graph event ID.
            data: Partial event body (e.g. responseStatus update).

        Returns:
            Updated event dict from the API.

        Raises:
            OutlookAPIError: On API errors.
        """
        url = (
            f"{OUTLOOK_API_URL}/me/calendars/{calendar_id}"
            f"/events/{event_id}"
        )
        return await self._request("PATCH", url, json=data)
