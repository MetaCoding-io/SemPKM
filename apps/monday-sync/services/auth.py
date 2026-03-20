"""Auth helpers for Monday.com Sync — credential storage, verification, connection status.

Stores a single API token via the SDK StateClient.  Monday.com uses
``Authorization: <api_key>`` (bare token, no Basic/Bearer prefix).

Provides connection verification via the ``me`` GraphQL query and
masked token display.  All state persistence goes through the SDK
StateClient.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("monday_sync.auth")

# State key for stored credential
TOKEN_STATE_KEY = "monday_api_token"


def _mask_token(token: str) -> str:
    """Return a masked preview of a token: first 4 + **** + last 4.

    For tokens shorter than 10 chars, mask all but the first 4 chars.
    """
    if len(token) <= 8:
        return token[:4] + "****"
    return token[:4] + "****" + token[-4:]


async def store_credentials(state_client, api_token: str) -> None:
    """Store Monday.com API token in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        api_token: Monday.com API token.
    """
    await state_client.set(TOKEN_STATE_KEY, api_token)
    logger.info("Monday.com API token stored")


async def get_credentials(state_client) -> dict | None:
    """Read stored Monday.com credentials from state.

    Returns:
        Dict with ``api_token`` key, or ``None`` if the key is missing
        or empty.
    """
    token = await state_client.get(TOKEN_STATE_KEY)

    if not token:
        return None

    return {"api_token": token}


async def clear_credentials(state_client) -> None:
    """Remove stored credentials by setting the token key to empty string.

    StateClient has no delete — sets the key to empty string.
    """
    await state_client.set(TOKEN_STATE_KEY, "")
    logger.info("Monday.com credentials cleared (disconnected)")


async def verify_connection(state_client, monday_client) -> dict:
    """Verify the stored credentials by calling the ``me`` query.

    Args:
        state_client: SDK StateClient (unused here but kept for
            interface consistency with other sync apps).
        monday_client: MondayClient instance with ``get_me()`` method.

    Returns:
        Dict with user info from the ``me`` query (``id``, ``name``,
        ``email``).

    Raises:
        Exception: If the API call fails (auth error, network error, etc.).
    """
    user = await monday_client.get_me()
    logger.info(
        "Monday.com connection verified for user: %s (%s)",
        user.get("name", "unknown"),
        user.get("email", "unknown"),
    )
    return user


async def get_connection_status(state_client, monday_client) -> dict:
    """Read current connection state, verifying credentials if stored.

    Calls ``monday_client.get_me()`` to verify the credentials are
    valid.  Returns a status dict with connection details.

    Returns:
        Dict with keys:
        - ``connected`` (bool)
        - ``display_name`` (str|None)
        - ``email`` (str|None)
        - ``token_preview`` (str|None) — masked, never the raw token
        - ``error`` (str|None) — present only when credentials exist
          but verification fails
    """
    creds = await get_credentials(state_client)
    if not creds:
        return {
            "connected": False,
            "display_name": None,
            "email": None,
            "token_preview": None,
        }

    token_preview = _mask_token(creds["api_token"])

    try:
        user = await monday_client.get_me()
        return {
            "connected": True,
            "display_name": user.get("name"),
            "email": user.get("email"),
            "token_preview": token_preview,
        }
    except Exception as exc:
        logger.warning("Monday.com credential verification failed: %s", exc)
        return {
            "connected": False,
            "display_name": None,
            "email": None,
            "token_preview": token_preview,
            "error": str(exc),
        }
