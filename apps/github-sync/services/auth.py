"""Auth helpers for GitHub Sync — PAT storage, verification, connection status.

Pure helper functions (except for StateClient/GitHubClient interactions) for
storing/retrieving a Personal Access Token, verifying it against the GitHub
API, and managing connection state. All state persistence goes through the
SDK StateClient.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("github_sync.auth")

# State key for the stored PAT
PAT_STATE_KEY = "github_pat"

# Import GitHubAuthError for verify_pat error handling.
try:
    from services.github_client import GitHubAuthError
except ImportError:
    try:
        from github_client import GitHubAuthError
    except ImportError:
        GitHubAuthError = None  # type: ignore[assignment, misc]


def _mask_pat(pat: str) -> str:
    """Return a masked preview of a PAT: first 4 + **** + last 4.

    For tokens shorter than 10 chars, mask all but the first 4 chars.
    """
    if len(pat) <= 8:
        return pat[:4] + "****"
    return pat[:4] + "****" + pat[-4:]


async def store_pat(state_client, pat: str) -> None:
    """Store a GitHub Personal Access Token in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        pat: Personal Access Token string.
    """
    await state_client.set(PAT_STATE_KEY, pat)
    logger.info("GitHub PAT stored")


async def get_pat(state_client) -> str | None:
    """Read the stored GitHub PAT from state.

    Returns:
        The PAT string, or ``None`` if no PAT is stored (empty string
        is treated as absent).
    """
    pat = await state_client.get(PAT_STATE_KEY)
    if not pat:
        return None
    return pat


async def verify_pat(github_client) -> dict:
    """Verify the stored PAT by calling the GitHub API.

    Args:
        github_client: GitHubClient instance (reads PAT from state internally).

    Returns:
        User dict from ``GET /user`` with keys like ``login``, ``name``,
        ``email``.

    Raises:
        GitHubAuthError: If the token is invalid or missing.
    """
    user = await github_client.verify_token()
    logger.info("PAT verified for user: %s", user.get("login"))
    return user


async def get_connection_status(state_client, github_client) -> dict:
    """Read current connection state, verifying the PAT if one is stored.

    Returns:
        Dict with keys:
        - ``connected`` (bool)
        - ``username`` (str|None)
        - ``pat_preview`` (str|None) — masked, never the raw token
        - ``error`` (str|None) — present only when PAT exists but fails verification
    """
    pat = await get_pat(state_client)
    if not pat:
        return {
            "connected": False,
            "username": None,
            "pat_preview": None,
        }

    pat_preview = _mask_pat(pat)

    try:
        user = await verify_pat(github_client)
        return {
            "connected": True,
            "username": user.get("login"),
            "pat_preview": pat_preview,
        }
    except Exception as exc:
        logger.warning("PAT verification failed: %s", exc)
        return {
            "connected": False,
            "username": None,
            "pat_preview": pat_preview,
            "error": str(exc),
        }


async def disconnect(state_client) -> None:
    """Remove the stored PAT by clearing the state key.

    StateClient has no delete — sets the key to empty string.
    """
    await state_client.set(PAT_STATE_KEY, "")
    logger.info("GitHub PAT cleared (disconnected)")
