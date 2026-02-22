"""Token generation and verification for auth flows.

Uses itsdangerous for signed tokens (magic link, invitation) and
secrets.token_urlsafe for random tokens (setup, session).

Secret key management: If settings.secret_key is empty, reads from
settings.secret_key_path file. If that file doesn't exist, generates
a key via secrets.token_urlsafe(64), writes to file, and uses it.
"""

import json
import secrets
from pathlib import Path

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

_serializer: URLSafeTimedSerializer | None = None


def _get_secret_key() -> str:
    """Resolve the secret key from settings, file, or auto-generation.

    Priority:
    1. settings.secret_key (from env var SECRET_KEY)
    2. Read from settings.secret_key_path file
    3. Generate, write to file, return
    """
    if settings.secret_key:
        return settings.secret_key

    key_path = Path(settings.secret_key_path)
    if key_path.exists():
        return key_path.read_text().strip()

    # Auto-generate and persist
    key = secrets.token_urlsafe(64)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key)
    return key


def _get_serializer() -> URLSafeTimedSerializer:
    """Lazy-init the URLSafeTimedSerializer with the resolved secret key."""
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(_get_secret_key())
    return _serializer


# --- Setup token (random, stored on disk, not signed) ---


def create_setup_token() -> str:
    """Generate a random setup token (not signed -- just random, stored on disk)."""
    return secrets.token_urlsafe(32)


def load_or_create_setup_token(path: str | None = None) -> str:
    """Read setup token from file if exists, create and write if not.

    Args:
        path: File path. Defaults to settings.setup_token_path.

    Returns:
        The setup token string.
    """
    token_path = Path(path or settings.setup_token_path)
    if token_path.exists():
        return token_path.read_text().strip()

    token = create_setup_token()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token)
    return token


def delete_setup_token(path: str | None = None) -> None:
    """Delete the setup token file after setup completes."""
    token_path = Path(path or settings.setup_token_path)
    if token_path.exists():
        token_path.unlink()


# --- Magic link tokens (signed with itsdangerous) ---


def create_magic_link_token(email: str) -> str:
    """Sign an email address for magic link authentication.

    Args:
        email: The email address to encode in the token.

    Returns:
        A URL-safe signed token string.
    """
    serializer = _get_serializer()
    return serializer.dumps(email, salt="magic-link")


def verify_magic_link_token(token: str, max_age_seconds: int = 600) -> str | None:
    """Verify a magic link token and return the email.

    Args:
        token: The signed token to verify.
        max_age_seconds: Maximum age in seconds (default 10 minutes).

    Returns:
        The email address if valid, None if expired or invalid.
    """
    serializer = _get_serializer()
    try:
        return serializer.loads(token, salt="magic-link", max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


# --- Invitation tokens (signed with itsdangerous) ---


def create_invitation_token(email: str, role: str) -> str:
    """Sign email and role for an invitation token.

    Args:
        email: The invited email address.
        role: The role to assign (member, guest).

    Returns:
        A URL-safe signed token string.
    """
    serializer = _get_serializer()
    payload = json.dumps({"email": email, "role": role})
    return serializer.dumps(payload, salt="invitation")


def verify_invitation_token(token: str, max_age_seconds: int = 604800) -> dict | None:
    """Verify an invitation token and return the payload.

    Args:
        token: The signed token to verify.
        max_age_seconds: Maximum age in seconds (default 7 days).

    Returns:
        Dict with {email, role} if valid, None if expired or invalid.
    """
    serializer = _get_serializer()
    try:
        payload_str = serializer.loads(
            token, salt="invitation", max_age=max_age_seconds
        )
        return json.loads(payload_str)
    except (BadSignature, SignatureExpired, json.JSONDecodeError):
        return None
