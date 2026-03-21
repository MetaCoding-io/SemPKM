"""Auth helpers for CalDAV — HTTP Basic credential management.

Pure helper functions for building Basic auth headers, storing/retrieving
credentials, testing connections, and managing connection state. All state
persistence goes through the SDK StateClient.
"""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger("caldav.auth")

# State keys managed by this module
AUTH_STATE_KEYS = ("server_url", "username", "password", "auth_method")

# CalDAVAuthError import — works both at runtime (app dir on sys.path)
# and in tests (module loaded via importlib spec_from_file_location).
try:
    from services.caldav_client import CalDAVAuthError
except ImportError:
    try:
        from caldav_client import CalDAVAuthError
    except ImportError:
        CalDAVAuthError = None  # type: ignore[assignment, misc]


def get_auth_headers(username: str, password: str) -> dict[str, str]:
    """Build HTTP Basic auth headers.

    Args:
        username: CalDAV username.
        password: CalDAV password.

    Returns:
        Dict with Authorization header.
    """
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


async def store_credentials(
    state_client,
    server_url: str,
    username: str,
    password: str,
) -> None:
    """Store CalDAV credentials in the app's state store.

    Args:
        state_client: SDK StateClient instance.
        server_url: CalDAV server URL (trailing slash stripped).
        username: CalDAV username.
        password: CalDAV password.
    """
    # Strip trailing slash for consistency
    clean_url = server_url.rstrip("/")

    await state_client.set("server_url", clean_url)
    await state_client.set("username", username)
    await state_client.set("password", password)
    await state_client.set("auth_method", "basic")

    logger.info("Credentials stored for %s@%s", username, clean_url)


async def check_connection(
    http_client,
    server_url: str,
    username: str,
    password: str,
) -> dict:
    """Test a CalDAV connection by sending a PROPFIND to the server.

    Sends a Depth:0 PROPFIND requesting DAV:current-user-principal.
    A 207 Multi-Status response indicates a working CalDAV server
    with valid credentials.

    Args:
        http_client: SDK HttpClient for making the test request.
        server_url: CalDAV server URL.
        username: CalDAV username.
        password: CalDAV password.

    Returns:
        Dict with success (bool), message (str), status_code (int).
    """
    headers = get_auth_headers(username, password)
    headers["Content-Type"] = "application/xml; charset=utf-8"
    headers["Depth"] = "0"

    # Minimal PROPFIND body requesting current-user-principal
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<d:propfind xmlns:d="DAV:">'
        "<d:prop>"
        "<d:current-user-principal/>"
        "</d:prop>"
        "</d:propfind>"
    )

    try:
        resp = await http_client.request(
            "PROPFIND",
            server_url,
            headers=headers,
            content=body,
        )
    except Exception as exc:
        logger.warning("Connection test failed with exception: %s", exc)
        return {
            "success": False,
            "message": f"Connection error: {exc}",
            "status_code": 0,
        }

    status = resp.status_code
    logger.info("Connection test to %s → %d", server_url, status)

    if status == 207:
        return {
            "success": True,
            "message": "Connected successfully",
            "status_code": 207,
        }

    if status == 401:
        return {
            "success": False,
            "message": "Authentication failed — check username and password",
            "status_code": 401,
        }

    if status == 404:
        return {
            "success": False,
            "message": "CalDAV endpoint not found — check server URL",
            "status_code": 404,
        }

    return {
        "success": False,
        "message": f"Server returned status {status}",
        "status_code": status,
    }


async def get_connection_status(state_client) -> dict:
    """Read current connection state from the app's state store.

    Returns:
        Dict with keys: connected (bool), auth_method (str|None),
        server_url (str|None), username (str|None).
        Never includes password.
    """
    auth_method = await state_client.get("auth_method")
    server_url = await state_client.get("server_url")
    username = await state_client.get("username")

    # Connected if we have a non-empty auth method recorded.
    # After clear_auth_state, values are "" (empty string) not None.
    connected = bool(auth_method)

    return {
        "connected": connected,
        "auth_method": auth_method,
        "server_url": server_url,
        "username": username,
    }


async def clear_auth_state(state_client) -> None:
    """Remove all auth-related state keys.

    Sets each key to an empty string (StateClient.set is the only
    mutation primitive — there's no delete).
    """
    for key in AUTH_STATE_KEYS:
        await state_client.set(key, "")
    logger.info("Auth state cleared")
