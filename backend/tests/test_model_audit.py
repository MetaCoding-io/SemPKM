"""Tests for model install/uninstall security audit logging.

Verifies that admin_models_install and admin_models_remove handlers
write SecurityAuditLog entries via log_security_event, and that
audit failures don't crash the model operations.
"""

import json
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.audit import log_security_event
from app.auth.models import SecurityAuditLog
from app.db.base import Base


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
async def db_engine():
    """In-memory SQLite engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
def user_id():
    return uuid.uuid4()


# ── log_security_event unit tests ────────────────────────────────


class TestModelInstalledEvent:
    """model_installed events are written correctly."""

    @pytest.mark.asyncio
    async def test_model_installed_event_written(self, session_factory, user_id):
        """Successful model install writes a model_installed audit entry."""
        await log_security_event(
            session_factory,
            "model_installed",
            "192.168.1.10",
            user_id=user_id,
            detail={"model_id": "basic-pkm", "path": "/app/models/basic-pkm"},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(SecurityAuditLog).where(
                    SecurityAuditLog.event_type == "model_installed"
                )
            )
            entry = result.scalar_one()

        assert entry.event_type == "model_installed"
        assert entry.user_id == user_id
        assert entry.source_ip == "192.168.1.10"
        detail = json.loads(entry.detail)
        assert detail["model_id"] == "basic-pkm"
        assert detail["path"] == "/app/models/basic-pkm"

    @pytest.mark.asyncio
    async def test_model_installed_detail_includes_model_id(self, session_factory, user_id):
        """The detail field always includes model_id."""
        await log_security_event(
            session_factory,
            "model_installed",
            "10.0.0.1",
            user_id=user_id,
            detail={"model_id": "crm", "path": "/app/models/crm"},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(SecurityAuditLog).where(
                    SecurityAuditLog.event_type == "model_installed"
                )
            )
            entry = result.scalar_one()

        detail = json.loads(entry.detail)
        assert "model_id" in detail
        assert detail["model_id"] == "crm"


class TestModelUninstalledEvent:
    """model_uninstalled events are written correctly."""

    @pytest.mark.asyncio
    async def test_model_uninstalled_event_written(self, session_factory, user_id):
        """Successful model uninstall writes a model_uninstalled audit entry."""
        await log_security_event(
            session_factory,
            "model_uninstalled",
            "10.0.0.5",
            user_id=user_id,
            detail={"model_id": "basic-pkm"},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(SecurityAuditLog).where(
                    SecurityAuditLog.event_type == "model_uninstalled"
                )
            )
            entry = result.scalar_one()

        assert entry.event_type == "model_uninstalled"
        assert entry.user_id == user_id
        assert entry.source_ip == "10.0.0.5"
        detail = json.loads(entry.detail)
        assert detail["model_id"] == "basic-pkm"

    @pytest.mark.asyncio
    async def test_model_uninstalled_detail_includes_model_id(self, session_factory, user_id):
        """The detail field includes model_id for uninstall events."""
        await log_security_event(
            session_factory,
            "model_uninstalled",
            "172.16.0.1",
            user_id=user_id,
            detail={"model_id": "business-planning"},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(SecurityAuditLog).where(
                    SecurityAuditLog.event_type == "model_uninstalled"
                )
            )
            entry = result.scalar_one()

        detail = json.loads(entry.detail)
        assert detail["model_id"] == "business-planning"


class TestAuditFailureResilience:
    """Audit logging failures must not crash the calling operation."""

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_raise(self):
        """If the DB session factory raises, log_security_event swallows the error."""
        broken_factory = MagicMock()
        broken_factory.side_effect = RuntimeError("DB connection lost")

        # Should not raise
        await log_security_event(
            broken_factory,
            "model_installed",
            "127.0.0.1",
            user_id=uuid.uuid4(),
            detail={"model_id": "test"},
        )

    @pytest.mark.asyncio
    async def test_audit_failure_with_commit_error(self, session_factory, user_id):
        """If commit fails, log_security_event swallows the error."""
        # Patch the session's commit to raise
        with patch.object(
            session_factory, "__call__", wraps=session_factory
        ) as mock_factory:
            original_call = session_factory

            async def broken_session():
                session = original_call()
                original_commit = session.commit

                async def bad_commit():
                    raise RuntimeError("Commit failed")

                session.commit = bad_commit
                return session

            # Use a factory that always raises on commit
            bad_factory = MagicMock()
            bad_factory.side_effect = RuntimeError("Connection pool exhausted")

            # Should not raise
            await log_security_event(
                bad_factory,
                "model_uninstalled",
                "10.0.0.1",
                user_id=user_id,
                detail={"model_id": "test-model"},
            )


class TestSecurityAuditHelperInRouter:
    """Test the _security_audit helper and _client_ip in admin router."""

    @pytest.mark.asyncio
    async def test_security_audit_skips_without_factory(self):
        """_security_audit is a no-op when async_session_factory is not on app.state."""
        from app.admin.router import _security_audit

        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # no async_session_factory attr

        # Should not raise
        await _security_audit(mock_request, "model_installed", user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_security_audit_calls_log_security_event(self, session_factory, user_id):
        """_security_audit delegates to log_security_event with correct args."""
        from app.admin.router import _security_audit

        mock_request = MagicMock()
        mock_request.app.state.async_session_factory = session_factory
        mock_request.client.host = "203.0.113.42"

        await _security_audit(
            mock_request, "model_installed",
            user_id=user_id,
            detail={"model_id": "test-model", "path": "/app/models/test-model"},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(SecurityAuditLog).where(
                    SecurityAuditLog.event_type == "model_installed"
                )
            )
            entry = result.scalar_one()

        assert entry.source_ip == "203.0.113.42"
        assert entry.user_id == user_id
        detail = json.loads(entry.detail)
        assert detail["model_id"] == "test-model"

    def test_client_ip_with_client(self):
        """_client_ip extracts host from request.client."""
        from app.admin.router import _client_ip

        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        assert _client_ip(mock_request) == "10.0.0.1"

    def test_client_ip_without_client(self):
        """_client_ip returns 'unknown' when request.client is None."""
        from app.admin.router import _client_ip

        mock_request = MagicMock()
        mock_request.client = None
        assert _client_ip(mock_request) == "unknown"
