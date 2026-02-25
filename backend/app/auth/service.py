"""Auth business logic: user creation, session lifecycle, invitation flow.

AuthService is the central service for all authentication operations.
It takes an async_session_factory as constructor arg and manages its own
database sessions internally.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)

from app.auth.models import Invitation, User, UserSession
from app.auth.tokens import create_invitation_token, verify_invitation_token
from app.config import settings


class AuthService:
    """Authentication and authorization business logic."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_user_count(self) -> int:
        """Count total users in the database."""
        async with self._session_factory() as session:
            result = await session.execute(select(func.count(User.id)))
            return result.scalar_one()

    async def is_setup_complete(self) -> bool:
        """Check if any user with role 'owner' exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(User.id).where(User.role == "owner").limit(1)
            )
            return result.first() is not None

    async def create_owner(self, email: str) -> User:
        """Create the instance owner user. Raises if owner already exists.

        If a user with this email already exists (e.g. created as a member
        before setup completed), their role is promoted to owner.
        """
        if await self.is_setup_complete():
            msg = "Owner already exists"
            raise ValueError(msg)

        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()
            if existing:
                existing.role = "owner"
                await session.commit()
                await session.refresh(existing)
                return existing

            user = User(email=email, role="owner")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def create_user(self, email: str, role: str) -> User:
        """Create a user with the specified role."""
        async with self._session_factory() as session:
            user = User(email=email, role=role)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Look up a user by email address."""
        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Look up a user by ID."""
        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def create_session(self, user: User) -> UserSession:
        """Create a new session for a user.

        Generates a random token and sets expiry based on settings.session_duration_days.
        """
        token = secrets.token_urlsafe(32)
        expires_at = _utcnow() + timedelta(days=settings.session_duration_days)

        async with self._session_factory() as session:
            user_session = UserSession(
                token=token,
                user_id=user.id,
                expires_at=expires_at,
            )
            session.add(user_session)
            await session.commit()
            await session.refresh(user_session)
            return user_session

    async def verify_session(self, token: str) -> User | None:
        """Find session by token where not expired.

        Implements sliding window: if session is past 50% of its lifetime,
        extend it by the full duration.

        Returns the associated user or None.
        """
        now = _utcnow()
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserSession)
                .where(UserSession.token == token, UserSession.expires_at > now)
            )
            user_session = result.scalar_one_or_none()
            if user_session is None:
                return None

            # Sliding window: extend if past 50% of lifetime
            total_duration = timedelta(days=settings.session_duration_days)
            midpoint = user_session.expires_at - (total_duration / 2)
            if now > midpoint:
                user_session.expires_at = now + total_duration
                await session.commit()

            # Load the user
            user_result = await session.execute(
                select(User).where(User.id == user_session.user_id)
            )
            return user_result.scalar_one_or_none()

    async def revoke_session(self, token: str) -> bool:
        """Delete a session by token. Returns True if found and deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(UserSession).where(UserSession.token == token)
            )
            await session.commit()
            return result.rowcount > 0

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> int:
        """Delete all sessions for a user. Returns the count deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(UserSession).where(UserSession.user_id == user_id)
            )
            await session.commit()
            return result.rowcount

    async def create_invitation(
        self, email: str, role: str, invited_by: uuid.UUID
    ) -> Invitation:
        """Create an invitation record with a signed token."""
        token = create_invitation_token(email, role)
        expires_at = _utcnow() + timedelta(days=7)

        async with self._session_factory() as session:
            invitation = Invitation(
                email=email,
                role=role,
                token=token,
                invited_by=invited_by,
                expires_at=expires_at,
            )
            session.add(invitation)
            await session.commit()
            await session.refresh(invitation)
            return invitation

    async def accept_invitation(
        self, token: str
    ) -> tuple[User, UserSession] | None:
        """Verify invitation token, create or get user, create session.

        Returns (user, session) tuple or None if token is invalid/expired.
        """
        payload = verify_invitation_token(token)
        if payload is None:
            return None

        email = payload["email"]
        role = payload["role"]

        # Find the invitation record
        async with self._session_factory() as session:
            result = await session.execute(
                select(Invitation).where(
                    Invitation.token == token, Invitation.accepted_at.is_(None)
                )
            )
            invitation = result.scalar_one_or_none()
            if invitation is None:
                return None

            # Mark invitation as accepted
            invitation.accepted_at = _utcnow()
            await session.commit()

        # Get or create user
        user = await self.get_user_by_email(email)
        if user is None:
            user = await self.create_user(email, role)

        # Create session for the user
        user_session = await self.create_session(user)
        return user, user_session
