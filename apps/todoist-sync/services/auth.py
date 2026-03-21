"""Auth helpers for Todoist Sync — PAT storage, verification, connection status.

Pure helper functions for storing/retrieving a Todoist Personal API Token,
verifying it against the Todoist REST API, and managing connection state.
All state persistence goes through the SDK StateClient.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("todoist.sync.auth")

# State key for the stored PAT
PAT_STATE_KEY = "todoist_pat"


def _mask_token(token: str) -> str:
    """Return a masked preview of a token: first 4 + **** + last 4.

    For tokens shorter than 10 chars, mask all but the first 4 chars.
    """
    if len(token) <= 8:
        return token[:4] + "****"
    return token[:4] + "****" + token[-4:]


async def store_token(state_client, token: str) -> None:
    """Store a Todoist API token in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        token: Todoist API token string.
    """
    await state_client.set(PAT_STATE_KEY, token)
    logger.info("Todoist API token stored")


async def get_stored_token(state_client) -> str | None:
    """Read the stored Todoist API token from state.

    Returns:
        The token string, or ``None`` if no token is stored (empty string
        is treated as absent).
    """
    token = await state_client.get(PAT_STATE_KEY)
    if not token:
        return None
    return token


async def verify_token(http_client, token: str) -> dict:
    """Verify a Todoist API token by calling GET /rest/v2/projects.

    A valid token returns a list of projects. We use this to both verify
    auth and retrieve the user's project count.

    Args:
        http_client: SDK HttpClient instance (or any client with a ``get`` method).
        token: Todoist API token to verify.

    Returns:
        Dict with keys:
        - ``valid`` (bool) — True if the token is valid
        - ``projects_count`` (int) — number of projects in the account

    Raises:
        TodoistAuthError: If the token is invalid (401/403).
        TodoistAPIError: If the API returns an unexpected status code.
    """
    response = await http_client.get(
        f"{os.environ.get('TODOIST_API_URL', 'https://api.todoist.com/rest/v2')}/projects",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code in (401, 403):
        raise TodoistAuthError(
            f"Invalid Todoist API token (HTTP {response.status_code})",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        raise TodoistAPIError(
            f"Todoist API error (HTTP {response.status_code})",
            status_code=response.status_code,
        )

    projects = response.json()
    logger.info("Todoist token verified — %d projects found", len(projects))
    return {
        "valid": True,
        "projects_count": len(projects),
    }


async def get_connection_status(state_client, http_client) -> dict:
    """Read current connection state, verifying the token if one is stored.

    Returns:
        Dict with keys:
        - ``connected`` (bool)
        - ``auth_method`` (str|None) — always "api_token" when connected
        - ``projects_count`` (int|None) — number of projects in the account
        - ``token_preview`` (str|None) — masked, never the raw token
        - ``error`` (str|None) — present only when token exists but fails verification
    """
    token = await get_stored_token(state_client)
    if not token:
        return {
            "connected": False,
            "auth_method": None,
            "projects_count": None,
            "token_preview": None,
        }

    token_preview = _mask_token(token)

    try:
        result = await verify_token(http_client, token)
        return {
            "connected": True,
            "auth_method": "api_token",
            "projects_count": result["projects_count"],
            "token_preview": token_preview,
        }
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        return {
            "connected": False,
            "auth_method": None,
            "projects_count": None,
            "token_preview": token_preview,
            "error": str(exc),
        }


async def clear_credentials(state_client) -> None:
    """Remove the stored token by clearing the state key.

    StateClient has no delete — sets the key to empty string.
    """
    await state_client.set(PAT_STATE_KEY, "")
    logger.info("Todoist API token cleared (disconnected)")


# ── Exception classes ──


class TodoistAuthError(Exception):
    """Raised when the Todoist API rejects authentication."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class TodoistAPIError(Exception):
    """Raised for non-auth Todoist API errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
