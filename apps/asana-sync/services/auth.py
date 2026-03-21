"""Auth helpers for Asana Sync — OAuth 2.0 + PAT flows.

Pure helper functions for building OAuth URLs, exchanging authorization
codes, storing/retrieving/refreshing auth tokens, verifying Personal
Access Tokens, and managing connection state. All state persistence
goes through the SDK StateClient.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

logger = logging.getLogger("asana.sync.auth")

ASANA_AUTHORIZE_URL = "https://app.asana.com/-/oauth_authorize"
ASANA_TOKEN_URL = os.environ.get(
    "ASANA_TOKEN_URL", "https://app.asana.com/-/oauth_token"
)
ASANA_API_URL = os.environ.get(
    "ASANA_API_URL", "https://app.asana.com/api/1.0"
)

# State keys managed by this module
AUTH_STATE_KEYS = (
    "access_token",
    "refresh_token",
    "auth_method",
    "asana_email",
    "token_expiry",
)

# AsanaAuthError import — works both at runtime (app dir on sys.path)
# and in tests (module loaded via importlib spec_from_file_location).
try:
    from services.asana_client import AsanaAuthError
except ImportError:
    try:
        from asana_client import AsanaAuthError
    except ImportError:
        # Fallback: define locally when asana_client isn't available yet.
        # T02 will define the canonical version in asana_client.py.
        class AsanaAuthError(Exception):  # type: ignore[no-redef]
            """Authentication/authorization error for Asana API."""

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


def build_asana_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build the Asana OAuth 2.0 authorization URL.

    Asana OAuth uses implicit scopes — no ``scope`` parameter is sent.

    Args:
        client_id: OAuth application client ID.
        redirect_uri: Callback URL after authorization.
        state: CSRF state parameter.

    Returns:
        Full authorization URL with query parameters.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }
    return f"{ASANA_AUTHORIZE_URL}?{urlencode(params)}"


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
        client_id: OAuth application client ID.
        client_secret: OAuth application client secret.
        redirect_uri: Same redirect_uri used in the authorize request.

    Returns:
        Dict with ``access_token``, ``refresh_token``, ``expires_in``.

    Raises:
        AsanaAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        ASANA_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        },
    )

    if resp.status_code != 200:
        logger.warning(
            "OAuth token exchange failed: status=%d", resp.status_code
        )
        raise AsanaAuthError(
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
        client_id: OAuth application client ID.
        client_secret: OAuth application client secret.

    Returns:
        Dict with ``access_token`` and ``expires_in``.

    Raises:
        AsanaAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        ASANA_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    if resp.status_code != 200:
        logger.warning(
            "Token refresh failed: status=%d", resp.status_code
        )
        raise AsanaAuthError(
            f"Token refresh failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    logger.info("OAuth token refreshed successfully")
    return {
        "access_token": data.get("access_token", ""),
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
    and stores the new token and expiry.

    Args:
        http_client: SDK HttpClient for making the token request.
        state_client: SDK StateClient for reading/writing auth tokens.
        client_id: OAuth application client ID.
        client_secret: OAuth application client secret.

    Returns:
        Current valid access token.

    Raises:
        AsanaAuthError: If refresh fails or no refresh token available.
    """
    access_token = await state_client.get("access_token")
    token_expiry = await state_client.get("token_expiry")

    # Check if token is still valid (with 5-minute buffer)
    if access_token and token_expiry:
        try:
            expiry_dt = datetime.fromisoformat(token_expiry)
            # Ensure timezone-aware comparison
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
        raise AsanaAuthError(
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
    if expires_in is not None:
        new_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in)
        )
        await state_client.set("token_expiry", new_expiry.isoformat())

    return new_access_token


async def verify_pat(http_client, pat: str) -> dict:
    """Verify a Personal Access Token by calling Asana's /users/me.

    Args:
        http_client: SDK HttpClient for making the API request.
        pat: Asana Personal Access Token.

    Returns:
        Dict with ``email`` and ``name`` of the authenticated user.

    Raises:
        AsanaAuthError: On non-200 response (invalid/expired PAT).
    """
    url = f"{ASANA_API_URL}/users/me"
    resp = await http_client.get(
        url,
        headers={"Authorization": f"Bearer {pat}"},
    )

    if resp.status_code != 200:
        logger.warning(
            "PAT verification failed: status=%d", resp.status_code
        )
        raise AsanaAuthError(
            f"PAT verification failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    user_data = data.get("data", data)
    logger.info("PAT verified for user: %s", user_data.get("email", "unknown"))
    return {
        "email": user_data.get("email", ""),
        "name": user_data.get("name", ""),
    }


async def store_auth_tokens(
    state_client,
    access_token: str,
    refresh_token: str,
    expires_in: int | None,
    asana_email: str,
    auth_method: str = "oauth",
) -> None:
    """Persist auth tokens and metadata in the app's state store.

    Computes ``token_expiry`` as an ISO 8601 timestamp from ``expires_in``
    seconds, rather than storing the raw integer.

    Args:
        state_client: SDK StateClient instance.
        access_token: OAuth access token or PAT.
        refresh_token: OAuth refresh token (empty string for PAT).
        expires_in: Token lifetime in seconds (None for PAT).
        asana_email: User's Asana email address.
        auth_method: Either ``"oauth"`` or ``"pat"``.
    """
    await state_client.set("access_token", access_token)
    await state_client.set("refresh_token", refresh_token)
    await state_client.set("auth_method", auth_method)
    await state_client.set("asana_email", asana_email)

    if expires_in is not None:
        token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in)
        )
        await state_client.set("token_expiry", token_expiry.isoformat())

    logger.info("Auth tokens stored (method=%s, email=%s)", auth_method, asana_email)


async def get_connection_status(state_client) -> dict:
    """Read current connection state from the app's state store.

    Returns:
        Dict with keys: ``connected`` (bool), ``auth_method`` (str|None),
        ``asana_email`` (str|None), ``token_expiry`` (str|None).
    """
    auth_method = await state_client.get("auth_method")
    asana_email = await state_client.get("asana_email")
    token_expiry = await state_client.get("token_expiry")

    # Connected if we have a non-empty auth method recorded.
    # After clear_auth_state, values are "" (empty string) not None,
    # because StateClient has no delete — only set.
    connected = bool(auth_method)

    return {
        "connected": connected,
        "auth_method": auth_method,
        "asana_email": asana_email,
        "token_expiry": token_expiry,
    }


async def clear_auth_state(state_client) -> None:
    """Remove all auth-related state keys.

    Sets each key to an empty string (StateClient.set is the only
    mutation primitive — there's no delete).
    """
    for key in AUTH_STATE_KEYS:
        await state_client.set(key, "")
    logger.info("Auth state cleared")
