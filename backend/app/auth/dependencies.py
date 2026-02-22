"""FastAPI auth dependencies for session-based authentication.

Provides get_current_user, require_role, and optional_current_user
dependencies that extract the session cookie and verify against the database.
"""

from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserSession
from app.config import settings
from app.db.session import get_db_session


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
