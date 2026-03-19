"""Auth helpers for Linear Sync — OAuth and API key flows.

Pure helper functions for building OAuth URLs, exchanging authorization
codes, storing/retrieving auth tokens, and managing connection state.
All state persistence goes through the SDK StateClient.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

logger = logging.getLogger("linear_sync.auth")

LINEAR_AUTHORIZE_URL = "https://linear.app/oauth/authorize"
LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"

# State keys managed by this module
AUTH_STATE_KEYS = (
    "access_token",
    "refresh_token",
    "api_key",
    "auth_method",
    "workspace_name",
    "workspace_id",
)

# LinearAuthError import — works both at runtime (app dir on sys.path)
# and in tests (module loaded via importlib spec_from_file_location).
try:
    from services.linear_client import LinearAuthError
except ImportError:
    try:
        from linear_client import LinearAuthError
    except ImportError:
        # Fallback: tests may inject this module before importing auth
        LinearAuthError = None  # type: ignore[assignment, misc]


def build_oauth_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build the Linear OAuth authorization URL.

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
        "scope": "read,write",
    }
    return f"{LINEAR_AUTHORIZE_URL}?{urlencode(params)}"


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
        LinearAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        LINEAR_TOKEN_URL,
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
        raise LinearAuthError(
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


async def store_auth_tokens(
    state_client,
    access_token: str,
    refresh_token: str | None,
    auth_method: str,
) -> None:
    """Persist auth tokens and method in the app's state store.

    For API key auth, pass auth_method="api_key" and the key as access_token.
    The key is stored under the ``api_key`` state key, not ``access_token``.

    Args:
        state_client: SDK StateClient instance.
        access_token: OAuth access token or API key value.
        refresh_token: OAuth refresh token (None for API key auth).
        auth_method: Either ``"oauth"`` or ``"api_key"``.
    """
    if auth_method == "api_key":
        await state_client.set("api_key", access_token)
    else:
        await state_client.set("access_token", access_token)
        if refresh_token:
            await state_client.set("refresh_token", refresh_token)
    await state_client.set("auth_method", auth_method)
    logger.info("Auth tokens stored (method=%s)", auth_method)


async def store_workspace_info(
    state_client,
    workspace_name: str,
    workspace_id: str,
) -> None:
    """Persist workspace metadata in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        workspace_name: Linear workspace/organization name.
        workspace_id: Linear workspace/organization ID.
    """
    await state_client.set("workspace_name", workspace_name)
    await state_client.set("workspace_id", workspace_id)
    logger.info("Workspace info stored: name=%s", workspace_name)


async def get_connection_status(state_client) -> dict:
    """Read current connection state from the app's state store.

    Returns:
        Dict with keys: ``connected`` (bool), ``auth_method`` (str|None),
        ``workspace_name`` (str|None), ``workspace_id`` (str|None).
    """
    auth_method = await state_client.get("auth_method")
    workspace_name = await state_client.get("workspace_name")
    workspace_id = await state_client.get("workspace_id")

    # Connected if we have a non-empty auth method recorded.
    # After clear_auth_state, values are "" (empty string) not None,
    # because StateClient has no delete — only set.
    connected = bool(auth_method)

    return {
        "connected": connected,
        "auth_method": auth_method,
        "workspace_name": workspace_name,
        "workspace_id": workspace_id,
    }


async def clear_auth_state(state_client) -> None:
    """Remove all auth-related state keys.

    Sets each key to an empty string (StateClient.set is the only
    mutation primitive — there's no delete). Then removes auth_method
    last so get_connection_status sees disconnected state.

    Note: StateClient uses SPARQL DELETE/INSERT — setting to empty string
    effectively clears the value. get() will return "" which is falsy
    but not None. We handle this in get_connection_status by checking
    auth_method specifically.
    """
    for key in AUTH_STATE_KEYS:
        await state_client.set(key, "")
    logger.info("Auth state cleared")
