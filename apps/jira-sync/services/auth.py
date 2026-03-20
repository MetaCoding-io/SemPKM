"""Auth helpers for Jira Sync — credential storage, verification, connection status.

Stores email + API token + site URL via the SDK StateClient. Provides
connection verification via ``get_myself()`` and masked token display.
All state persistence goes through the SDK StateClient.
"""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger("jira_sync.auth")

# State keys for stored credentials
EMAIL_STATE_KEY = "jira_email"
TOKEN_STATE_KEY = "jira_token"
SITE_URL_STATE_KEY = "jira_site_url"

# Import JiraAuthError for verify error handling.
try:
    from services.jira_client import JiraAuthError
except ImportError:
    try:
        from jira_client import JiraAuthError
    except ImportError:
        JiraAuthError = None  # type: ignore[assignment, misc]


def _mask_token(token: str) -> str:
    """Return a masked preview of a token: first 4 + **** + last 4.

    For tokens shorter than 10 chars, mask all but the first 4 chars.
    """
    if len(token) <= 8:
        return token[:4] + "****"
    return token[:4] + "****" + token[-4:]


def build_auth_header(email: str, token: str) -> str:
    """Build a Base64-encoded Basic auth header value.

    Returns:
        ``Basic <base64(email:token)>`` string.
    """
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {credentials}"


async def store_credentials(
    state_client,
    email: str,
    token: str,
    site_url: str,
) -> None:
    """Store Jira credentials in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        email: Jira account email address.
        token: Jira API token.
        site_url: Jira site URL (e.g. ``https://mysite.atlassian.net``).
    """
    await state_client.set(EMAIL_STATE_KEY, email)
    await state_client.set(TOKEN_STATE_KEY, token)
    await state_client.set(SITE_URL_STATE_KEY, site_url)
    logger.info("Jira credentials stored for %s", email)


async def get_credentials(state_client) -> dict | None:
    """Read stored Jira credentials from state.

    Returns:
        Dict with ``email``, ``token``, ``site_url`` keys, or ``None``
        if any key is missing or empty.
    """
    email = await state_client.get(EMAIL_STATE_KEY)
    token = await state_client.get(TOKEN_STATE_KEY)
    site_url = await state_client.get(SITE_URL_STATE_KEY)

    if not email or not token or not site_url:
        return None

    return {
        "email": email,
        "token": token,
        "site_url": site_url,
    }


async def clear_credentials(state_client) -> None:
    """Remove stored credentials by setting all keys to empty string.

    StateClient has no delete — sets each key to empty string.
    """
    await state_client.set(EMAIL_STATE_KEY, "")
    await state_client.set(TOKEN_STATE_KEY, "")
    await state_client.set(SITE_URL_STATE_KEY, "")
    logger.info("Jira credentials cleared (disconnected)")


async def get_connection_status(state_client, jira_client) -> dict:
    """Read current connection state, verifying credentials if stored.

    Calls ``jira_client.get_myself()`` to verify the credentials are
    valid. Returns a status dict with connection details.

    Returns:
        Dict with keys:
        - ``connected`` (bool)
        - ``email`` (str|None)
        - ``display_name`` (str|None)
        - ``token_preview`` (str|None) — masked, never the raw token
        - ``site_url`` (str|None)
        - ``error`` (str|None) — present only when credentials exist
          but verification fails
    """
    creds = await get_credentials(state_client)
    if not creds:
        return {
            "connected": False,
            "email": None,
            "display_name": None,
            "token_preview": None,
            "site_url": None,
        }

    token_preview = _mask_token(creds["token"])

    try:
        user = await jira_client.get_myself()
        return {
            "connected": True,
            "email": creds["email"],
            "display_name": user.get("displayName"),
            "token_preview": token_preview,
            "site_url": creds["site_url"],
        }
    except Exception as exc:
        logger.warning("Jira credential verification failed: %s", exc)
        return {
            "connected": False,
            "email": creds["email"],
            "display_name": None,
            "token_preview": token_preview,
            "site_url": creds["site_url"],
            "error": str(exc),
        }
