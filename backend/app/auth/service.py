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

from app.auth.models import ApiToken, Invitation, User, UserSession
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

    async def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions. Returns count deleted."""
        now = _utcnow()
        async with self._session_factory() as session:
            result = await session.execute(
                delete(UserSession).where(UserSession.expires_at <= now)
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

    async def create_api_token(
        self, user_id: uuid.UUID, name: str
    ) -> tuple[str, ApiToken]:
        """Create a new API token. Returns (plaintext_token, ApiToken).

        The plaintext token is returned exactly once -- caller must store it.
        The database only stores the SHA-256 hash.
        """
        import hashlib

        plaintext = secrets.token_hex(32)  # 64-char hex string
        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        async with self._session_factory() as session:
            token = ApiToken(user_id=user_id, name=name, token_hash=token_hash)
            session.add(token)
            await session.commit()
            await session.refresh(token)
            return plaintext, token

    async def list_api_tokens(self, user_id: uuid.UUID) -> list[ApiToken]:
        """Return all API tokens for a user, ordered by created_at ascending."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ApiToken)
                .where(ApiToken.user_id == user_id)
                .order_by(ApiToken.created_at.asc())
            )
            return list(result.scalars().all())

    async def revoke_api_token(
        self, user_id: uuid.UUID, token_id: uuid.UUID
    ) -> bool:
        """Delete an API token row (user-scoped for safety). Returns True if deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(ApiToken).where(
                    ApiToken.id == token_id,
                    ApiToken.user_id == user_id,
                )
            )
            await session.commit()
            return result.rowcount > 0

    async def verify_api_token(self, plaintext: str) -> User | None:
        """Verify a plaintext API token, return its User or None if invalid/revoked."""
        import hashlib

        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        async with self._session_factory() as session:
            result = await session.execute(
                select(ApiToken).where(
                    ApiToken.token_hash == token_hash,
                    ApiToken.revoked_at.is_(None),
                )
            )
            token_row = result.scalar_one_or_none()
            if not token_row:
                return None
            # Update last_used_at
            token_row.last_used_at = _utcnow()
            await session.commit()
            # Load user
            user_result = await session.execute(
                select(User).where(User.id == token_row.user_id)
            )
            return user_result.scalar_one_or_none()

    def verify_api_token_sync(
        self, plaintext: str, db_url: str
    ) -> tuple[str, str] | None:
        """Verify a plaintext API token synchronously for WSGI thread use.

        Returns (user_email, user_role) or None if invalid/revoked.
        Uses a synchronous SQLAlchemy engine -- safe to call from wsgidav threads.
        """
        import hashlib

        from sqlalchemy import create_engine, select as sync_select
        from sqlalchemy.orm import Session

        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        sync_url = db_url.replace("+aiosqlite", "")
        engine = create_engine(sync_url)
        try:
            with Session(engine) as session:
                result = session.execute(
                    sync_select(ApiToken).where(
                        ApiToken.token_hash == token_hash,
                        ApiToken.revoked_at.is_(None),
                    )
                )
                token_row = result.scalar_one_or_none()
                if not token_row:
                    return None
                # Update last_used_at
                token_row.last_used_at = _utcnow()
                session.commit()
                # Load user
                user_result = session.execute(
                    sync_select(User).where(User.id == token_row.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return None
                return user.email, user.role
        finally:
            engine.dispose()

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
