"""FastAPI auth dependencies for session-based authentication.

Provides get_current_user, require_role, optional_current_user, and
get_current_user_or_api dependencies that extract session cookie or
Bearer API token and verify against the database.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserSession
from app.config import settings
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime for SQLite compatibility.

    SQLite stores datetimes without timezone info, so we use naive UTC
    datetimes for consistent comparisons.
    """
    return datetime.now(UTC).replace(tzinfo=None)


async def get_session_token(
    sempkm_session: str | None = Cookie(None),
) -> str:
    """Extract session token from the httpOnly cookie.

    Raises 401 if no cookie is present.
    """
    if sempkm_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return sempkm_session


async def get_current_user(
    token: str = Depends(get_session_token),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Look up session in DB and return the authenticated user.

    Implements sliding window: if session is past 50% of its lifetime,
    extend it by the full configured duration.

    Raises 401 if session is missing or expired.
    """
    now = _utcnow()
    result = await db.execute(
        select(UserSession).where(
            UserSession.token == token,
            UserSession.expires_at > now,
        )
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Sliding window: extend if past 50% of lifetime
    total_duration = timedelta(days=settings.session_duration_days)
    midpoint = user_session.expires_at - (total_duration / 2)
    if now > midpoint:
        user_session.expires_at = now + total_duration
        # Commit happens via the session dependency's try/commit pattern

    # Load the user
    user_result = await db.execute(
        select(User).where(User.id == user_session.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_role(*roles: str):
    """Factory returning a dependency that checks the user's role.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("owner"))])

    Or to get the user object:
        user: User = Depends(require_role("owner", "member"))
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return current_user

    return _check_role


async def optional_current_user(
    sempkm_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Same as get_current_user but returns None instead of 401.

    For endpoints that behave differently for authenticated vs unauthenticated
    users (e.g., the setup status page).
    """
    if sempkm_session is None:
        return None

    now = _utcnow()
    result = await db.execute(
        select(UserSession).where(
            UserSession.token == sempkm_session,
            UserSession.expires_at > now,
        )
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        return None

    user_result = await db.execute(
        select(User).where(User.id == user_session.user_id)
    )
    return user_result.scalar_one_or_none()


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Parse the Authorization header and return the Bearer token.

    Returns None if the header is absent, empty, or uses a non-Bearer scheme.
    """
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token if token else None


async def get_current_user_or_api(
    request: Request,
    sempkm_session: str | None = Cookie(None),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve a User from either a session cookie or a Bearer API token.

    Auth resolution order:
    1. Session cookie (``sempkm_session``) — same DB lookup as ``get_current_user``
    2. Bearer token from ``Authorization`` header — verified via ``AuthService``
    3. If neither succeeds, raises HTTP 401.

    This is the standard dependency for M013 API-surface endpoints that
    must accept both htmx (cookie) and external (Bearer) clients.
    """
    # --- Path 1: session cookie ---
    if sempkm_session is not None:
        now = _utcnow()
        result = await db.execute(
            select(UserSession).where(
                UserSession.token == sempkm_session,
                UserSession.expires_at > now,
            )
        )
        user_session = result.scalar_one_or_none()
        if user_session is not None:
            # Sliding window: extend if past 50% of lifetime
            total_duration = timedelta(days=settings.session_duration_days)
            midpoint = user_session.expires_at - (total_duration / 2)
            if now > midpoint:
                user_session.expires_at = now + total_duration

            user_result = await db.execute(
                select(User).where(User.id == user_session.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is not None:
                logger.debug("dual-auth resolved via session cookie for user=%s", user.email)
                return user

    # --- Path 2: Bearer API token ---
    bearer_token = _extract_bearer_token(authorization)
    if bearer_token is not None:
        auth_service = request.app.state.auth_service
        user = await auth_service.verify_api_token(bearer_token)
        if user is not None:
            logger.debug("dual-auth resolved via Bearer token for user=%s", user.email)
            return user
        # Token was provided but invalid — give a specific message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API token",
        )

    # --- Neither method succeeded ---
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
