"""Auth helpers for Outlook Calendar — Microsoft Identity Platform OAuth 2.0.

Pure helper functions for building OAuth URLs, exchanging authorization
codes, storing/retrieving/refreshing auth tokens, and managing connection
state.  All state persistence goes through the SDK StateClient.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

logger = logging.getLogger("outlook.sync.auth")

# Microsoft Identity Platform endpoints (common = multi-tenant)
OUTLOOK_AUTHORIZE_URL = os.environ.get(
    "OUTLOOK_AUTH_URL",
    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
)
OUTLOOK_TOKEN_URL = os.environ.get(
    "OUTLOOK_TOKEN_URL",
    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
)

# Microsoft Graph API base
OUTLOOK_API_URL = os.environ.get(
    "OUTLOOK_API_URL",
    "https://graph.microsoft.com/v1.0",
)

# Scopes: offline_access for refresh tokens, Calendars.ReadWrite for calendar CRUD
OUTLOOK_SCOPES = "Calendars.ReadWrite offline_access"

# State keys managed by this module
AUTH_STATE_KEYS = (
    "access_token",
    "refresh_token",
    "auth_method",
    "microsoft_email",
    "token_expiry",
)

# OutlookAuthError import — works both at runtime (app dir on sys.path)
# and in tests (module loaded via importlib spec_from_file_location).
try:
    from services.outlook_client import OutlookAuthError
except ImportError:
    try:
        from outlook_client import OutlookAuthError
    except ImportError:
        # Fallback: define locally so auth module can be loaded standalone
        # before the client module exists (e.g. T01 before T02).
        class OutlookAuthError(Exception):  # type: ignore[no-redef]
            """Auth error for Outlook Calendar API."""

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


def build_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build the Microsoft OAuth 2.0 authorization URL.

    Args:
        client_id: Azure AD application (client) ID.
        redirect_uri: Callback URL after authorization.
        state: CSRF state parameter.

    Returns:
        Full authorization URL with query parameters.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": OUTLOOK_SCOPES,
        "response_mode": "query",
        "state": state,
    }
    return f"{OUTLOOK_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(
    http_client,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """Exchange an OAuth authorization code for access and refresh tokens.

    Args:
        http_client: SDK HttpClient for making the token request.
        code: Authorization code from OAuth callback.
        client_id: Azure AD application (client) ID.
        client_secret: Azure AD client secret.
        redirect_uri: Same redirect_uri used in the authorize request.

    Returns:
        Dict with ``access_token``, ``refresh_token``, ``expires_in``.

    Raises:
        OutlookAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        OUTLOOK_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scope": OUTLOOK_SCOPES,
        },
    )

    if resp.status_code != 200:
        logger.warning(
            "OAuth token exchange failed: status=%d body=%s",
            resp.status_code,
            resp.text,
        )
        raise OutlookAuthError(
            f"OAuth token exchange failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    logger.info("OAuth token exchange succeeded")
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in"),
    }


async def refresh_access_token(
    http_client,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Refresh an expired access token using the refresh token.

    Args:
        http_client: SDK HttpClient for making the token request.
        refresh_token: OAuth refresh token from initial authorization.
        client_id: Azure AD application (client) ID.
        client_secret: Azure AD client secret.

    Returns:
        Dict with ``access_token``, ``refresh_token`` (may be rotated),
        and ``expires_in``.

    Raises:
        OutlookAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        OUTLOOK_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": OUTLOOK_SCOPES,
        },
    )

    if resp.status_code != 200:
        logger.warning(
            "Token refresh failed: status=%d body=%s",
            resp.status_code,
            resp.text,
        )
        raise OutlookAuthError(
            f"Token refresh failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    logger.info("OAuth token refreshed successfully")
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_in": data.get("expires_in"),
    }


async def refresh_if_expired(
    http_client,
    state_client,
    client_id: str,
    client_secret: str,
) -> str:
    """Check token expiry and refresh if needed.

    Reads ``token_expiry`` from state, compares against now + 5min buffer.
    If expired (or no expiry recorded), calls ``refresh_access_token``
    and stores the new token and expiry.  Microsoft may also rotate the
    refresh token, so we store that too.

    Args:
        http_client: SDK HttpClient for making the token request.
        state_client: SDK StateClient for reading/writing auth tokens.
        client_id: Azure AD application (client) ID.
        client_secret: Azure AD client secret.

    Returns:
        Current valid access token.

    Raises:
        OutlookAuthError: If refresh fails or no refresh token available.
    """
    access_token = await state_client.get("access_token")
    token_expiry = await state_client.get("token_expiry")

    # Check if token is still valid (with 5-minute buffer)
    if access_token and token_expiry:
        try:
            expiry_dt = datetime.fromisoformat(token_expiry)
            now = datetime.now(timezone.utc)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            if now + timedelta(minutes=5) < expiry_dt:
                return access_token
        except (ValueError, TypeError):
            pass  # Invalid expiry format — refresh anyway

    # Need to refresh
    refresh_token = await state_client.get("refresh_token")
    if not refresh_token:
        raise OutlookAuthError(
            "No refresh token available",
            status_code=401,
            response_body="",
        )

    result = await refresh_access_token(
        http_client, refresh_token, client_id, client_secret
    )

    new_access_token = result["access_token"]
    expires_in = result.get("expires_in")
    await state_client.set("access_token", new_access_token)

    # Microsoft may rotate the refresh token
    new_refresh_token = result.get("refresh_token")
    if new_refresh_token and new_refresh_token != refresh_token:
        await state_client.set("refresh_token", new_refresh_token)

    if expires_in is not None:
        new_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in)
        )
        await state_client.set("token_expiry", new_expiry.isoformat())

    return new_access_token


async def store_auth_tokens(
    state_client,
    access_token: str,
    refresh_token: str,
    expires_in: int | None,
    microsoft_email: str,
) -> None:
    """Persist auth tokens and metadata in the app's state store.

    Computes ``token_expiry`` as an ISO 8601 timestamp from ``expires_in``
    seconds, rather than storing the raw integer.

    Args:
        state_client: SDK StateClient instance.
        access_token: OAuth access token.
        refresh_token: OAuth refresh token.
        expires_in: Token lifetime in seconds (from Microsoft's response).
        microsoft_email: User's Microsoft email address.
    """
    await state_client.set("access_token", access_token)
    await state_client.set("refresh_token", refresh_token)
    await state_client.set("auth_method", "oauth")
    await state_client.set("microsoft_email", microsoft_email)

    if expires_in is not None:
        token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in)
        )
        await state_client.set("token_expiry", token_expiry.isoformat())

    logger.info("Auth tokens stored for %s", microsoft_email)


async def get_connection_status(state_client) -> dict:
    """Read current connection state from the app's state store.

    Returns:
        Dict with keys: ``connected`` (bool), ``auth_method`` (str|None),
        ``microsoft_email`` (str|None), ``token_expiry`` (str|None),
        ``token_preview`` (str|None) — first 8 chars of access token for
        debugging without exposing the full secret.
    """
    auth_method = await state_client.get("auth_method")
    microsoft_email = await state_client.get("microsoft_email")
    token_expiry = await state_client.get("token_expiry")
    access_token = await state_client.get("access_token")

    # Connected if we have a non-empty auth method recorded.
    # After clear_auth_state, values are "" (empty string) not None,
    # because StateClient has no delete — only set.
    connected = bool(auth_method)

    # Masked preview for diagnostics — never expose full token
    token_preview = None
    if access_token:
        token_preview = access_token[:8] + "..." if len(access_token) > 8 else "***"

    return {
        "connected": connected,
        "auth_method": auth_method,
        "microsoft_email": microsoft_email,
        "token_expiry": token_expiry,
        "token_preview": token_preview,
    }


async def clear_auth_state(state_client) -> None:
    """Remove all auth-related state keys.

    Sets each key to an empty string (StateClient.set is the only
    mutation primitive — there's no delete).
    """
    for key in AUTH_STATE_KEYS:
        await state_client.set(key, "")
    logger.info("Auth state cleared")
