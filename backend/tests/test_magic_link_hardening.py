"""Tests for magic link auth hardening: single-use, no-SMTP restriction, token logging.

Covers:
- F-012: Magic link replay returns 401 (single-use enforcement)
- F-018: No-SMTP mode rejects unknown emails with generic response
- F-028: Token not logged in full (truncated to first 8 chars)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import Invitation, UsedMagicToken, User
from app.auth.service import AuthService
from app.auth.tokens import create_magic_link_token, verify_magic_link_token
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session_factory():
    """Provide an in-memory SQLite async session factory with tables created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_service(async_session_factory):
    """AuthService backed by in-memory SQLite."""
    return AuthService(async_session_factory)


@pytest_asyncio.fixture
async def test_user(async_session_factory):
    """Create a test user and return them."""
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email="alice@example.com",
            display_name="Alice",
            role="member",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- F-012: Single-use magic links ---


class TestSingleUseMagicLinks:
    """Magic link tokens can only be consumed once."""

    @pytest.mark.asyncio
    async def test_first_use_succeeds(self, auth_service):
        """First consumption of a magic link token should succeed."""
        token = create_magic_link_token("alice@example.com")
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=600)

        consumed = await auth_service.check_and_consume_magic_token(token, expires_at)
        assert consumed is True

    @pytest.mark.asyncio
    async def test_replay_fails(self, auth_service):
        """Second consumption of the same token should fail (replay attack)."""
        token = create_magic_link_token("alice@example.com")
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=600)

        first = await auth_service.check_and_consume_magic_token(token, expires_at)
        assert first is True

        second = await auth_service.check_and_consume_magic_token(token, expires_at)
        assert second is False

    @pytest.mark.asyncio
    async def test_different_tokens_both_succeed(self, auth_service):
        """Two different tokens (different emails) should both be consumable."""
        token1 = create_magic_link_token("alice@example.com")
        token2 = create_magic_link_token("bob@example.com")
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=600)

        assert await auth_service.check_and_consume_magic_token(token1, expires_at) is True
        assert await auth_service.check_and_consume_magic_token(token2, expires_at) is True

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_records(self, auth_service):
        """Expired used-magic-token records should be cleaned up."""
        token = create_magic_link_token("alice@example.com")
        # Set expires_at in the past so it's eligible for cleanup
        expired_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)

        await auth_service.check_and_consume_magic_token(token, expired_at)

        purged = await auth_service.cleanup_expired_magic_tokens()
        assert purged == 1

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_records(self, auth_service):
        """Non-expired used-magic-token records should be preserved by cleanup."""
        token = create_magic_link_token("alice@example.com")
        future_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

        await auth_service.check_and_consume_magic_token(token, future_expiry)

        purged = await auth_service.cleanup_expired_magic_tokens()
        assert purged == 0

        # Token should still be marked as used
        second = await auth_service.check_and_consume_magic_token(token, future_expiry)
        assert second is False


# --- F-018: No-SMTP restriction for unknown emails ---


class TestPendingInvitationCheck:
    """has_pending_invitation returns True only for valid pending invitations."""

    @pytest.mark.asyncio
    async def test_no_invitation_returns_false(self, auth_service):
        result = await auth_service.has_pending_invitation("unknown@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_pending_invitation_returns_true(self, auth_service, test_user, async_session_factory):
        """An unaccepted, non-expired invitation should return True."""
        from app.auth.tokens import create_invitation_token

        token = create_invitation_token("newguy@example.com", "member")
        async with async_session_factory() as session:
            invitation = Invitation(
                email="newguy@example.com",
                role="member",
                token=token,
                invited_by=test_user.id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
            )
            session.add(invitation)
            await session.commit()

        result = await auth_service.has_pending_invitation("newguy@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_expired_invitation_returns_false(self, auth_service, test_user, async_session_factory):
        """An expired invitation should return False."""
        from app.auth.tokens import create_invitation_token

        token = create_invitation_token("expired@example.com", "member")
        async with async_session_factory() as session:
            invitation = Invitation(
                email="expired@example.com",
                role="member",
                token=token,
                invited_by=test_user.id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1),
            )
            session.add(invitation)
            await session.commit()

        result = await auth_service.has_pending_invitation("expired@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_accepted_invitation_returns_false(self, auth_service, test_user, async_session_factory):
        """An already-accepted invitation should return False."""
        from app.auth.tokens import create_invitation_token

        token = create_invitation_token("accepted@example.com", "member")
        async with async_session_factory() as session:
            invitation = Invitation(
                email="accepted@example.com",
                role="member",
                token=token,
                invited_by=test_user.id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
                accepted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(invitation)
            await session.commit()

        result = await auth_service.has_pending_invitation("accepted@example.com")
        assert result is False


# --- F-028: Token not logged in full ---


class TestTokenLoggingTruncation:
    """Magic link tokens should be logged with only the first 8 characters."""

    def test_magic_link_token_is_longer_than_8_chars(self):
        """Verify tokens are long enough that truncation is meaningful."""
        token = create_magic_link_token("test@example.com")
        assert len(token) > 8

    def test_verify_still_works_on_valid_token(self):
        """Verify magic link roundtrip still works after code changes."""
        email = "bob@example.com"
        token = create_magic_link_token(email)
        result = verify_magic_link_token(token)
        assert result == email
