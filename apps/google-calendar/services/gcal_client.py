"""GCalClient — authenticated REST client for the Google Calendar API v3.

Wraps the SDK HttpClient for authenticated requests to Google Calendar's
REST endpoints. Supports OAuth token refresh on 401, pagination via
nextPageToken, and typed exceptions for all error conditions.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("google_calendar.client")

GCAL_BASE_URL = os.environ.get(
    "GCAL_API_URL", "https://www.googleapis.com/calendar/v3"
)

MAX_PAGINATION_PAGES = 50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GCalAPIError(Exception):
    """Base exception for Google Calendar API errors."""

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


class GCalAuthError(GCalAPIError):
    """Authentication/authorization error (401/403)."""


class GCalRateLimitError(GCalAPIError):
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

class GCalClient:
    """Authenticated REST client for the Google Calendar API v3.

    Args:
        http_client: SDK ``HttpClient`` instance (domain-enforced to
            ``www.googleapis.com``).
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

    async def _get_headers(self) -> dict[str, str]:
        """Build request headers from stored credentials.

        Reads ``access_token`` from state and returns Authorization + Accept
        headers.

        Raises:
            GCalAuthError: If no access token is stored.
        """
        token = await self._state.get("access_token")
        if not token:
            raise GCalAuthError("Not authenticated")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _handle_token_refresh(self) -> None:
        """Exchange the stored refresh token for a new access token.

        Acquires ``_refreshing`` lock to prevent concurrent refresh attempts.
        Stores the new ``access_token`` via StateClient.

        Raises:
            GCalAuthError: If no refresh token is available or if the
                token endpoint returns an error.
        """
        # Import here to avoid circular import at module level
        try:
            from services.auth import GOOGLE_TOKEN_URL
        except ImportError:
            try:
                from auth import GOOGLE_TOKEN_URL
            except ImportError:
                GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

        async with self._refreshing:
            refresh_token = await self._state.get("refresh_token")
            if not refresh_token:
                raise GCalAuthError(
                    "Token refresh not available — no refresh token",
                    status_code=401,
                )

            logger.info("Refreshing Google OAuth token")
            resp = await self._http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id or "",
                    "client_secret": self._client_secret or "",
                    "refresh_token": refresh_token,
                },
            )

            if resp.status_code != 200:
                body = resp.text
                raise GCalAuthError(
                    f"Token refresh failed: {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            data = resp.json()
            new_access = data.get("access_token", "")

            if new_access:
                await self._state.set("access_token", new_access)
            # Google does not always return a new refresh token
            new_refresh = data.get("refresh_token")
            if new_refresh:
                await self._state.set("refresh_token", new_refresh)

            logger.info("Google OAuth token refreshed successfully")

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
            method: HTTP method ("GET", "POST", etc.).
            url: Full URL to request.
            allow_refresh: Whether to attempt token refresh on 401.
            **kwargs: Additional arguments passed to the HTTP client.

        Returns:
            Parsed JSON response body.

        Raises:
            GCalAuthError: On 401/403 (after refresh attempt if applicable).
            GCalRateLimitError: On 429 with ``retry_after`` seconds.
            GCalAPIError: On other HTTP errors.
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
                except GCalAuthError:
                    raise
                return await self._request(
                    method, url, allow_refresh=False, **kwargs
                )
            raise GCalAuthError(
                f"Unauthorized after token refresh: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- 403: forbidden -------------------------------------------------
        if resp.status_code == 403:
            raise GCalAuthError(
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
            raise GCalRateLimitError(
                "Rate limited by Google Calendar API",
                status_code=429,
                response_body=resp.text,
                retry_after=retry_after,
            )

        # -- 5xx: server error ----------------------------------------------
        if resp.status_code >= 500:
            raise GCalAPIError(
                f"Google Calendar API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        # -- Other client errors --------------------------------------------
        if resp.status_code >= 400:
            raise GCalAPIError(
                f"Google Calendar API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp.json()

    # ---- calendar methods -------------------------------------------------

    async def get_calendar_list(self) -> list[dict[str, Any]]:
        """Fetch the user's calendar list, handling pagination.

        Returns a list of calendar dicts, each with at least:
        ``id``, ``summary``, ``primary``, ``accessRole``.

        Raises:
            GCalAuthError: On authentication/authorization failure.
            GCalRateLimitError: On rate limit.
            GCalAPIError: On other API errors.
        """
        all_calendars: list[dict[str, Any]] = []
        page_token: str | None = None

        for _ in range(MAX_PAGINATION_PAGES):
            url = f"{GCAL_BASE_URL}/users/me/calendarList"
            if page_token:
                url = f"{url}?pageToken={page_token}"

            data = await self._request("GET", url)

            items = data.get("items", [])
            for item in items:
                all_calendars.append({
                    "id": item.get("id", ""),
                    "summary": item.get("summary", ""),
                    "primary": item.get("primary", False),
                    "accessRole": item.get("accessRole", ""),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_calendars
