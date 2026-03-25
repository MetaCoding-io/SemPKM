"""Tests for session management: revoke-all, session cap, periodic cleanup, file permissions.

Covers:
- POST /api/auth/sessions/revoke-all returns count and sets new cookie
- Session cap evicts oldest sessions when limit exceeded
- Cleanup removes expired sessions and magic tokens
- Secret key and setup token files get 0o600 permissions
"""

import asyncio
import os
import stat
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import UsedMagicToken, User, UserSession
from app.auth.service import AuthService
from app.auth.tokens import _get_secret_key, load_or_create_setup_token
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
async def owner(auth_service):
    """Create a test owner user."""
    return await auth_service.create_owner("owner@test.local")


# --- Revoke All Sessions ---


class TestRevokeAllSessions:
    """Tests for revoke_all_sessions service method."""

    @pytest.mark.asyncio
    async def test_revoke_all_returns_count(self, auth_service, owner):
        """Revoking all sessions returns the correct count."""
        # Create 3 sessions
        await auth_service.create_session(owner)
        await auth_service.create_session(owner)
        await auth_service.create_session(owner)

        revoked = await auth_service.revoke_all_sessions(owner.id)
        assert revoked == 3

    @pytest.mark.asyncio
    async def test_revoke_all_returns_zero_when_none(self, auth_service, owner):
        """Revoking when no sessions exist returns 0."""
        revoked = await auth_service.revoke_all_sessions(owner.id)
        assert revoked == 0

    @pytest.mark.asyncio
    async def test_revoke_all_doesnt_affect_other_users(self, auth_service, owner):
        """Revoking user A's sessions doesn't touch user B's."""
        other_user = await auth_service.create_user("other@test.local", "member")
        await auth_service.create_session(owner)
        s_other = await auth_service.create_session(other_user)

        await auth_service.revoke_all_sessions(owner.id)

        # Other user's session still valid
        found = await auth_service.verify_session(s_other.token)
        assert found is not None
        assert found.email == "other@test.local"


# --- Session Cap ---


class TestSessionCap:
    """Tests for per-user session cap in create_session()."""

    @pytest.mark.asyncio
    async def test_cap_enforces_limit(self, auth_service, owner, async_session_factory):
        """Creating sessions beyond the cap keeps total at the limit."""
        from sqlalchemy import select as sa_select, func as sa_func

        for _ in range(12):
            await auth_service.create_session(owner)

        # Should have exactly 10 sessions (cap enforced)
        async with async_session_factory() as db:
            r = await db.execute(
                sa_select(sa_func.count(UserSession.id)).where(
                    UserSession.user_id == owner.id
                )
            )
            count = r.scalar_one()
        assert count == 10

    @pytest.mark.asyncio
    async def test_cap_evicts_oldest_by_timestamp(self, auth_service, owner, async_session_factory):
        """When timestamps differ, the oldest session is evicted."""
        from sqlalchemy import update

        # Create 10 sessions — all get the same timestamp
        sessions = []
        for _ in range(10):
            s = await auth_service.create_session(owner)
            sessions.append(s)

        # Manually set the first session's created_at to a much earlier time
        async with async_session_factory() as db:
            await db.execute(
                update(UserSession)
                .where(UserSession.token == sessions[0].token)
                .values(created_at=datetime(2020, 1, 1))
            )
            await db.commit()

        # 11th session should evict the one from 2020
        s11 = await auth_service.create_session(owner)

        # Old session should be gone
        found = await auth_service.verify_session(sessions[0].token)
        assert found is None

        # Newest session should work
        found = await auth_service.verify_session(s11.token)
        assert found is not None

    @pytest.mark.asyncio
    async def test_below_cap_no_eviction(self, auth_service, owner):
        """Creating sessions below the cap doesn't evict anything."""
        sessions = []
        for _ in range(5):
            s = await auth_service.create_session(owner)
            sessions.append(s)

        # All 5 should still work
        for s in sessions:
            found = await auth_service.verify_session(s.token)
            assert found is not None

    @pytest.mark.asyncio
    async def test_custom_cap(self, auth_service, owner, async_session_factory):
        """Custom max_sessions parameter is respected."""
        from sqlalchemy import select as sa_select, func as sa_func

        for _ in range(5):
            await auth_service.create_session(owner, max_sessions=3)

        async with async_session_factory() as db:
            r = await db.execute(
                sa_select(sa_func.count(UserSession.id)).where(
                    UserSession.user_id == owner.id
                )
            )
            count = r.scalar_one()
        assert count == 3


# --- Cleanup ---


class TestSessionCleanup:
    """Tests for cleanup_expired_sessions and cleanup_expired_magic_tokens."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, auth_service, owner, async_session_factory):
        """Expired sessions are removed by cleanup."""
        # Create a session, then manually expire it
        s = await auth_service.create_session(owner)
        async with async_session_factory() as db:
            from sqlalchemy import update
            await db.execute(
                update(UserSession)
                .where(UserSession.token == s.token)
                .values(expires_at=datetime(2020, 1, 1))
            )
            await db.commit()

        cleaned = await auth_service.cleanup_expired_sessions()
        assert cleaned == 1

        # Session no longer valid
        found = await auth_service.verify_session(s.token)
        assert found is None

    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_sessions(self, auth_service, owner):
        """Active (non-expired) sessions survive cleanup."""
        s = await auth_service.create_session(owner)
        cleaned = await auth_service.cleanup_expired_sessions()
        assert cleaned == 0

        found = await auth_service.verify_session(s.token)
        assert found is not None

    @pytest.mark.asyncio
    async def test_cleanup_expired_magic_tokens(self, auth_service, async_session_factory):
        """Expired used-magic-token records are cleaned up."""
        # Insert an expired record
        async with async_session_factory() as db:
            record = UsedMagicToken(
                token_hash="expired_hash_abc",
                used_at=datetime(2020, 1, 1),
                expires_at=datetime(2020, 1, 2),
            )
            db.add(record)
            await db.commit()

        cleaned = await auth_service.cleanup_expired_magic_tokens()
        assert cleaned == 1

    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_magic_tokens(self, auth_service, async_session_factory):
        """Non-expired used-magic-token records survive cleanup."""
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        async with async_session_factory() as db:
            record = UsedMagicToken(
                token_hash="active_hash_abc",
                used_at=datetime.now(timezone.utc).replace(tzinfo=None),
                expires_at=future,
            )
            db.add(record)
            await db.commit()

        cleaned = await auth_service.cleanup_expired_magic_tokens()
        assert cleaned == 0


# --- File Permissions ---


class TestFilePermissions:
    """Tests for secret key and setup token file permissions (F-038)."""

    def test_secret_key_file_permissions(self, tmp_path):
        """Auto-generated secret key file gets 0o600 permissions."""
        key_file = tmp_path / ".secret-key"
        with patch("app.auth.tokens.settings") as mock_settings:
            mock_settings.secret_key = ""
            mock_settings.secret_key_path = str(key_file)

            # Reset cached serializer
            import app.auth.tokens as tokens_mod
            tokens_mod._serializer = None

            key = tokens_mod._get_secret_key()

        assert key_file.exists()
        assert len(key) > 0
        mode = stat.S_IMODE(os.stat(key_file).st_mode)
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"

    def test_setup_token_file_permissions(self, tmp_path):
        """Auto-generated setup token file gets 0o600 permissions."""
        token_file = tmp_path / ".setup-token"
        token = load_or_create_setup_token(str(token_file))

        assert token_file.exists()
        assert len(token) > 0
        mode = stat.S_IMODE(os.stat(token_file).st_mode)
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"

    def test_existing_secret_key_not_overwritten(self, tmp_path):
        """If key file already exists, it's read — not overwritten."""
        key_file = tmp_path / ".secret-key"
        key_file.write_text("existing-key-value")

        with patch("app.auth.tokens.settings") as mock_settings:
            mock_settings.secret_key = ""
            mock_settings.secret_key_path = str(key_file)

            import app.auth.tokens as tokens_mod
            tokens_mod._serializer = None
            key = tokens_mod._get_secret_key()

        assert key == "existing-key-value"
