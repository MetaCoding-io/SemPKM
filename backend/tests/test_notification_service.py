"""Tests for NotificationService — token CRUD, preferences, suppression logic,
and FCM dispatch (no-op mode, stale token cleanup).

Uses the same in-memory SQLite + async session pattern as test_context_service.py.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User  # noqa: F401 — registers 'users' table in metadata
from app.context.notification_models import DeviceToken, NotificationPreferences
from app.context.notification_service import NotificationService, _token_prefix
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


@pytest.fixture
def other_user_id():
    return uuid.uuid4()


@pytest.fixture
def context_service():
    """Mock ContextService with calendar_busy=False by default."""
    svc = AsyncMock()
    ctx = MagicMock()
    ctx.calendar_busy = False
    svc.get_current = AsyncMock(return_value=ctx)
    return svc


@pytest.fixture
def service(session_factory, context_service):
    return NotificationService(
        session_factory, context_service=context_service, firebase_app=None
    )


# ── Token prefix helper ─────────────────────────────────────────


class TestTokenPrefix:
    def test_long_token_truncated(self):
        assert _token_prefix("a" * 100) == "a" * 20 + "..."

    def test_short_token_unchanged(self):
        assert _token_prefix("short") == "short"


# ── Token CRUD ───────────────────────────────────────────────────


class TestTokenCRUD:
    @pytest.mark.asyncio
    async def test_register_new_token(self, service, user_id):
        tok = await service.register_token(user_id, "fcm_abc123", "ios")
        assert tok.token == "fcm_abc123"
        assert tok.platform == "ios"
        assert tok.user_id == user_id

    @pytest.mark.asyncio
    async def test_register_duplicate_token_updates(self, service, user_id):
        await service.register_token(user_id, "fcm_dup", "ios", "iPhone 15")
        tok = await service.register_token(user_id, "fcm_dup", "android", "Pixel 9")
        assert tok.platform == "android"
        assert tok.device_name == "Pixel 9"

    @pytest.mark.asyncio
    async def test_unregister_token(self, service, user_id):
        await service.register_token(user_id, "fcm_remove", "ios")
        deleted = await service.unregister_token("fcm_remove")
        assert deleted is True
        tokens = await service.get_tokens_for_user(user_id)
        assert len(tokens) == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_token(self, service):
        deleted = await service.unregister_token("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_tokens_multiple_devices(self, service, user_id):
        await service.register_token(user_id, "tok_a", "ios")
        await service.register_token(user_id, "tok_b", "android")
        tokens = await service.get_tokens_for_user(user_id)
        assert len(tokens) == 2
        token_values = {t.token for t in tokens}
        assert token_values == {"tok_a", "tok_b"}

    @pytest.mark.asyncio
    async def test_get_tokens_no_tokens(self, service, user_id):
        tokens = await service.get_tokens_for_user(user_id)
        assert tokens == []


# ── Preferences ──────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_default_preferences(self, service, user_id):
        prefs = await service.get_preferences(user_id)
        assert prefs["enabled"] is True
        assert prefs["quiet_hours_start"] is None
        assert prefs["suppress_when_busy"] is True
        assert isinstance(prefs["enabled_types"], list)
        assert "overdue_tasks" in prefs["enabled_types"]

    @pytest.mark.asyncio
    async def test_update_preferences(self, service, user_id):
        prefs = await service.update_preferences(
            user_id,
            enabled=False,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )
        assert prefs["enabled"] is False
        assert prefs["quiet_hours_start"] == "22:00"
        assert prefs["quiet_hours_end"] == "07:00"

    @pytest.mark.asyncio
    async def test_update_partial_preferences(self, service, user_id):
        await service.update_preferences(
            user_id,
            enabled=False,
            quiet_hours_start="23:00",
            quiet_hours_end="06:00",
        )
        # Update only enabled, leave quiet hours alone
        prefs = await service.update_preferences(user_id, enabled=True)
        assert prefs["enabled"] is True
        assert prefs["quiet_hours_start"] == "23:00"  # unchanged

    @pytest.mark.asyncio
    async def test_update_enabled_types_as_list(self, service, user_id):
        prefs = await service.update_preferences(
            user_id,
            enabled_types=["overdue_tasks"],
        )
        assert prefs["enabled_types"] == ["overdue_tasks"]


# ── Suppression ──────────────────────────────────────────────────


class TestSuppression:
    @pytest.mark.asyncio
    async def test_suppress_when_disabled(self, service, user_id):
        await service.update_preferences(user_id, enabled=False)
        suppressed, reason = await service.should_suppress(user_id)
        assert suppressed is True
        assert reason == "disabled"

    @pytest.mark.asyncio
    async def test_suppress_when_type_disabled(self, service, user_id):
        await service.update_preferences(
            user_id, enabled_types=["overdue_tasks"]
        )
        suppressed, reason = await service.should_suppress(
            user_id, notification_type="context_changes"
        )
        assert suppressed is True
        assert reason == "type_disabled"

    @pytest.mark.asyncio
    async def test_suppress_when_calendar_busy(
        self, service, user_id, context_service
    ):
        context_service.get_current.return_value.calendar_busy = True
        suppressed, reason = await service.should_suppress(user_id)
        assert suppressed is True
        assert reason == "calendar_busy"

    @pytest.mark.asyncio
    async def test_suppress_quiet_hours_normal_range(self, service, user_id):
        """Quiet hours 22:00–23:00, current time 22:30 → suppress."""
        await service.update_preferences(
            user_id, quiet_hours_start="22:00", quiet_hours_end="23:00"
        )
        fake_now = datetime(2026, 3, 23, 22, 30, tzinfo=timezone.utc)
        suppressed, reason = await service.should_suppress(
            user_id, _now=fake_now
        )
        assert suppressed is True
        assert reason == "quiet_hours"

    @pytest.mark.asyncio
    async def test_suppress_quiet_hours_midnight_span_late(self, service, user_id):
        """Quiet hours 22:00–07:00, current time 23:00 → suppress (after start)."""
        await service.update_preferences(
            user_id, quiet_hours_start="22:00", quiet_hours_end="07:00"
        )
        fake_now = datetime(2026, 3, 23, 23, 0, tzinfo=timezone.utc)
        suppressed, reason = await service.should_suppress(
            user_id, _now=fake_now
        )
        assert suppressed is True
        assert reason == "quiet_hours"

    @pytest.mark.asyncio
    async def test_suppress_quiet_hours_midnight_span_early(self, service, user_id):
        """Quiet hours 22:00–07:00, current time 03:00 → suppress (before end)."""
        await service.update_preferences(
            user_id, quiet_hours_start="22:00", quiet_hours_end="07:00"
        )
        fake_now = datetime(2026, 3, 24, 3, 0, tzinfo=timezone.utc)
        suppressed, reason = await service.should_suppress(
            user_id, _now=fake_now
        )
        assert suppressed is True
        assert reason == "quiet_hours"

    @pytest.mark.asyncio
    async def test_allow_outside_quiet_hours(self, service, user_id):
        """Quiet hours 22:00–07:00, current time 12:00 → allow."""
        await service.update_preferences(
            user_id, quiet_hours_start="22:00", quiet_hours_end="07:00"
        )
        fake_now = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
        suppressed, reason = await service.should_suppress(
            user_id, _now=fake_now
        )
        assert suppressed is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_allow_when_all_conditions_pass(self, service, user_id):
        """All conditions satisfied — notification allowed."""
        suppressed, reason = await service.should_suppress(user_id)
        assert suppressed is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_suppress_when_busy_disabled_allows(
        self, service, user_id, context_service
    ):
        """suppress_when_busy=False + calendar busy → not suppressed."""
        context_service.get_current.return_value.calendar_busy = True
        await service.update_preferences(user_id, suppress_when_busy=False)
        suppressed, reason = await service.should_suppress(user_id)
        assert suppressed is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_no_context_service_skips_calendar_check(
        self, session_factory, user_id
    ):
        """When context_service is None, calendar_busy check is skipped."""
        svc = NotificationService(session_factory, context_service=None)
        suppressed, reason = await svc.should_suppress(user_id)
        assert suppressed is False


# ── Dispatch ─────────────────────────────────────────────────────


class TestDispatch:
    @pytest.mark.asyncio
    async def test_noop_mode_no_firebase(self, service, user_id):
        """firebase_app=None → returns None and does not crash."""
        await service.register_token(user_id, "tok_noop", "ios")
        result = await service.send_notification("tok_noop", "Test", "Body")
        assert result is None

    @pytest.mark.asyncio
    async def test_stale_token_cleanup(self, session_factory, user_id):
        """UnregisteredError → token is auto-deleted."""

        # Create a real Exception subclass for UnregisteredError
        class FakeUnregisteredError(Exception):
            pass

        fake_app = MagicMock()
        svc = NotificationService(
            session_factory, context_service=None, firebase_app=fake_app
        )
        await svc.register_token(user_id, "tok_stale_123456789012345", "ios")

        # Build a mock messaging module whose UnregisteredError is catchable
        mock_messaging = MagicMock()
        mock_messaging.UnregisteredError = FakeUnregisteredError
        mock_messaging.Message = MagicMock()
        mock_messaging.Notification = MagicMock()

        # Wire firebase_admin.messaging so `from firebase_admin import messaging`
        # resolves to our mock_messaging
        mock_firebase_admin = MagicMock()
        mock_firebase_admin.messaging = mock_messaging

        async def fake_to_thread(fn, *args, **kwargs):
            raise FakeUnregisteredError("gone")

        with patch.dict(
            "sys.modules",
            {
                "firebase_admin": mock_firebase_admin,
                "firebase_admin.messaging": mock_messaging,
            },
        ), patch(
            "app.context.notification_service.asyncio.to_thread",
            side_effect=fake_to_thread,
        ):
            result = await svc.send_notification(
                "tok_stale_123456789012345", "Hi", "Body"
            )

        assert result is None
        # Token should be deleted
        tokens = await svc.get_tokens_for_user(user_id)
        assert len(tokens) == 0

    @pytest.mark.asyncio
    async def test_send_to_user_suppressed(self, service, user_id):
        """send_to_user skips when should_suppress returns True."""
        await service.update_preferences(user_id, enabled=False)
        await service.register_token(user_id, "tok_x", "ios")
        results = await service.send_to_user(user_id, "Title", "Body")
        assert results == []

    @pytest.mark.asyncio
    async def test_send_to_user_no_tokens(self, service, user_id):
        """send_to_user with no tokens returns empty list."""
        results = await service.send_to_user(user_id, "Title", "Body")
        assert results == []

    @pytest.mark.asyncio
    async def test_send_to_user_noop_delivers_to_all(self, service, user_id):
        """In no-op mode, send_to_user calls send_notification for each token
        (which returns None for each)."""
        await service.register_token(user_id, "tok_1", "ios")
        await service.register_token(user_id, "tok_2", "android")
        results = await service.send_to_user(user_id, "Title", "Body")
        assert len(results) == 2
        assert all(r is None for r in results)
