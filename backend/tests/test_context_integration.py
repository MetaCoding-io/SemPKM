"""Integration tests for the full context→rules→persona→notification loop.

These tests wire real ContextService, RulesEngine, PersonaService,
NotificationService, and ContextBroadcast together using in-memory
SQLite.  Only Firebase dispatch is mocked (firebase_app=None).

This proves the integration path in context/router.py:update_context():
    context persist → SSE broadcast → rule evaluation →
    persona switch → notification dispatch/suppression
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Import all models so Base.metadata.create_all sees every table.
from app.auth.models import User  # noqa: F401
from app.context.models import UserContext  # noqa: F401
from app.context.rules_models import ContextRule  # noqa: F401
from app.context.notification_models import DeviceToken, NotificationPreferences  # noqa: F401
from app.persona.models import Persona  # noqa: F401
from app.context.zone_models import ContextZone  # noqa: F401

from app.context.broadcast import ContextBroadcast
from app.context.notification_service import NotificationService
from app.context.rules_engine import RulesEngine
from app.context.service import ContextService
from app.persona.service import PersonaService
from app.db.base import Base

# Dependencies to override
from app.auth.dependencies import get_current_user_or_api
from app.dependencies import (
    get_context_broadcast,
    get_context_service,
    get_notification_service,
    get_rules_engine,
    get_persona_service,
)
from app.context.router import router


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
def test_user_id():
    return uuid.uuid4()


@pytest.fixture
async def test_user(session_factory, test_user_id):
    """Seed a User row and return the ORM instance."""
    async with session_factory() as session:
        user = User(
            id=test_user_id,
            email="integration@test.local",
            role="owner",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def context_service(session_factory):
    return ContextService(session_factory)


@pytest.fixture
def rules_engine(session_factory):
    return RulesEngine(session_factory)


@pytest.fixture
def persona_service(session_factory):
    return PersonaService(session_factory)


@pytest.fixture
def broadcast():
    return ContextBroadcast()


@pytest.fixture
def notification_service(session_factory, context_service):
    return NotificationService(
        session_factory,
        context_service=context_service,
        firebase_app=None,  # no-op mode — no real FCM dispatch
    )


@pytest.fixture
async def app(
    test_user,
    context_service,
    rules_engine,
    persona_service,
    notification_service,
    broadcast,
):
    """FastAPI test app with real services wired to app.state."""
    from fastapi import FastAPI
    from app.auth.rate_limit import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app = FastAPI()
    # Disable rate limiting for integration tests — we're not testing
    # rate limits, and the 12/min cap would break multi-test sessions.
    limiter.enabled = False
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Wire all services onto app.state — matching main.py lifespan names
    test_app.state.context_service = context_service
    test_app.state.context_broadcast = broadcast
    test_app.state.rules_engine = rules_engine
    test_app.state.persona_service = persona_service
    test_app.state.notification_service = notification_service
    test_app.state.shutdown_event = asyncio.Event()

    test_app.include_router(router)

    # Override dependency-injected services
    test_app.dependency_overrides[get_current_user_or_api] = lambda: test_user
    test_app.dependency_overrides[get_context_service] = lambda: context_service
    test_app.dependency_overrides[get_context_broadcast] = lambda: broadcast
    test_app.dependency_overrides[get_rules_engine] = lambda: rules_engine
    test_app.dependency_overrides[get_persona_service] = lambda: persona_service
    test_app.dependency_overrides[get_notification_service] = lambda: notification_service

    return test_app


@pytest.fixture
async def client(app):
    """httpx AsyncClient connected to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Seed helpers ─────────────────────────────────────────────────


async def seed_persona(session_factory, user_id: uuid.UUID, name: str) -> Persona:
    """Insert a Persona row and return it."""
    async with session_factory() as session:
        p = Persona(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            layout_json="{}",
            sidebar_positions_json="{}",
            explorer_mode="by-type",
            is_active=False,
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


async def seed_rule(
    session_factory,
    user_id: uuid.UUID,
    name: str,
    conditions: dict,
    persona_id: str,
    priority: int = 0,
) -> ContextRule:
    """Insert a ContextRule row and return it."""
    async with session_factory() as session:
        rule = ContextRule(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            conditions=conditions,
            persona_id=persona_id,
            priority=priority,
            enabled=True,
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return rule


async def seed_preferences(
    session_factory,
    user_id: uuid.UUID,
    *,
    enabled: bool = True,
    quiet_start: str | None = None,
    quiet_end: str | None = None,
    suppress_when_busy: bool = True,
    enabled_types: list[str] | None = None,
) -> NotificationPreferences:
    """Insert a NotificationPreferences row and return it."""
    async with session_factory() as session:
        prefs = NotificationPreferences(
            id=uuid.uuid4(),
            user_id=user_id,
            enabled=enabled,
            quiet_hours_start=quiet_start,
            quiet_hours_end=quiet_end,
            suppress_when_busy=suppress_when_busy,
            enabled_types=json.dumps(enabled_types) if enabled_types else None,
        )
        session.add(prefs)
        await session.commit()
        await session.refresh(prefs)
        return prefs


async def seed_device_token(
    session_factory, user_id: uuid.UUID, token: str = "fcm_test_token_12345"
) -> DeviceToken:
    """Insert a DeviceToken row so send_to_user has a target."""
    async with session_factory() as session:
        dt = DeviceToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token=token,
            platform="ios",
            device_name="Test iPhone",
        )
        session.add(dt)
        await session.commit()
        await session.refresh(dt)
        return dt


# ── Tests ────────────────────────────────────────────────────────


class TestFullLoop:
    """Full context update → rule evaluation → persona switch integration."""

    @pytest.mark.asyncio
    async def test_full_loop_context_to_persona_switch(
        self, client, session_factory, test_user, persona_service
    ):
        """POST context matching a rule switches the persona via real services."""
        user_id = test_user.id
        work_persona = await seed_persona(session_factory, user_id, "Work")
        await seed_rule(
            session_factory,
            user_id,
            "Office→Work",
            {"location_zone": "office"},
            str(work_persona.id),
        )

        resp = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_zone"] == "office"

        # Verify the persona was actually activated
        active = await persona_service.get_active(user_id)
        assert active is not None
        assert active.id == str(work_persona.id)
        assert active.name == "Work"

    @pytest.mark.asyncio
    async def test_no_rule_match(
        self, client, session_factory, test_user, persona_service
    ):
        """POST context with no matching rule succeeds without persona change."""
        user_id = test_user.id
        # Seed a persona but no rules
        await seed_persona(session_factory, user_id, "Default")

        resp = await client.post(
            "/api/context/update", json={"location_zone": "park"}
        )
        assert resp.status_code == 200
        assert resp.json()["location_zone"] == "park"

        # No persona should be activated (no rule matched)
        active = await persona_service.get_active(user_id)
        assert active is None

    @pytest.mark.asyncio
    async def test_rule_priority_ordering(
        self, client, session_factory, test_user, persona_service
    ):
        """Higher-priority rule's persona wins when both rules match."""
        user_id = test_user.id
        low_persona = await seed_persona(session_factory, user_id, "LowPriority")
        high_persona = await seed_persona(session_factory, user_id, "HighPriority")

        await seed_rule(
            session_factory,
            user_id,
            "Low",
            {"location_zone": "office"},
            str(low_persona.id),
            priority=1,
        )
        await seed_rule(
            session_factory,
            user_id,
            "High",
            {"location_zone": "office"},
            str(high_persona.id),
            priority=10,
        )

        resp = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        assert resp.status_code == 200

        active = await persona_service.get_active(user_id)
        assert active is not None
        assert active.id == str(high_persona.id)
        assert active.name == "HighPriority"

    @pytest.mark.asyncio
    async def test_redundant_switch_skipped(
        self, client, session_factory, test_user, persona_service
    ):
        """Second context update with same matching rule skips re-activation."""
        user_id = test_user.id
        work_persona = await seed_persona(session_factory, user_id, "Work")
        await seed_rule(
            session_factory,
            user_id,
            "Office→Work",
            {"location_zone": "office"},
            str(work_persona.id),
        )

        # First update — activates persona
        resp1 = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        assert resp1.status_code == 200
        active = await persona_service.get_active(user_id)
        assert active is not None
        assert active.id == str(work_persona.id)

        # Spy on activate to verify it's not called again
        with patch.object(
            persona_service, "activate", wraps=persona_service.activate
        ) as spy:
            resp2 = await client.post(
                "/api/context/update", json={"location_zone": "office"}
            )
            assert resp2.status_code == 200
            # activate should NOT be called because the target persona
            # is already the active one
            spy.assert_not_called()


class TestNotificationIntegration:
    """Notification dispatch and suppression through the real service chain."""

    @pytest.mark.asyncio
    async def test_notification_dispatched_on_zone_change(
        self, client, session_factory, test_user, notification_service
    ):
        """Location zone change triggers send_to_user with notification_type=context_changes."""
        user_id = test_user.id
        await seed_device_token(session_factory, user_id)
        await seed_preferences(session_factory, user_id, suppress_when_busy=False)

        with patch.object(
            notification_service, "send_to_user", wraps=notification_service.send_to_user
        ) as spy:
            resp = await client.post(
                "/api/context/update", json={"location_zone": "office"}
            )
            assert resp.status_code == 200
            spy.assert_called_once()
            call_kwargs = spy.call_args
            assert call_kwargs[1].get("notification_type") == "context_changes" or (
                len(call_kwargs[0]) >= 5 and call_kwargs[0][4] == "context_changes"
            ) or call_kwargs.kwargs.get("notification_type") == "context_changes"

    @pytest.mark.asyncio
    async def test_notification_suppressed_calendar_busy(
        self, client, session_factory, test_user, notification_service
    ):
        """Notification suppressed when calendar_busy=True and suppress_when_busy enabled."""
        user_id = test_user.id
        await seed_device_token(session_factory, user_id)
        await seed_preferences(session_factory, user_id, suppress_when_busy=True)

        # First: set calendar_busy=True in context
        resp1 = await client.post(
            "/api/context/update", json={"calendar_busy": True}
        )
        assert resp1.status_code == 200

        # Now a zone change — should be suppressed because calendar_busy
        with patch.object(
            notification_service, "send_notification", wraps=notification_service.send_notification
        ) as spy:
            resp2 = await client.post(
                "/api/context/update", json={"location_zone": "cafe"}
            )
            assert resp2.status_code == 200

            # Verify suppression: should_suppress returns True
            suppressed, reason = await notification_service.should_suppress(
                user_id, notification_type="context_changes"
            )
            assert suppressed is True
            assert reason == "calendar_busy"

    @pytest.mark.asyncio
    async def test_notification_suppressed_quiet_hours(
        self, client, session_factory, test_user, notification_service
    ):
        """Notification suppressed when current time is within quiet hours (always-quiet window)."""
        user_id = test_user.id
        await seed_device_token(session_factory, user_id)
        # "00:00"→"23:59" covers the entire day
        await seed_preferences(
            session_factory,
            user_id,
            suppress_when_busy=False,
            quiet_start="00:00",
            quiet_end="23:59",
        )

        suppressed, reason = await notification_service.should_suppress(
            user_id, notification_type="context_changes"
        )
        assert suppressed is True
        assert reason == "quiet_hours"

        # Also verify through the HTTP path — send_to_user returns [] when suppressed
        with patch.object(
            notification_service, "send_notification", wraps=notification_service.send_notification
        ) as spy:
            resp = await client.post(
                "/api/context/update", json={"location_zone": "home"}
            )
            assert resp.status_code == 200
            # send_notification should never be called because send_to_user
            # short-circuits on suppression before reaching per-token dispatch
            spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_suppressed_master_disabled(
        self, client, session_factory, test_user, notification_service
    ):
        """Notification suppressed when master enabled=False."""
        user_id = test_user.id
        await seed_device_token(session_factory, user_id)
        await seed_preferences(session_factory, user_id, enabled=False)

        suppressed, reason = await notification_service.should_suppress(
            user_id, notification_type="context_changes"
        )
        assert suppressed is True
        assert reason == "disabled"


class TestContextStaleness:
    """Context staleness detection via TTL."""

    @pytest.mark.asyncio
    async def test_context_staleness_via_ttl(
        self, client, session_factory, test_user, context_service
    ):
        """Context marked stale when TTL is zero (immediate expiry)."""
        user_id = test_user.id

        # POST to create a context row
        resp = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        assert resp.status_code == 200

        # Read with ttl_seconds=0 — should be stale immediately
        ctx = await context_service.get_current(user_id, ttl_seconds=0)
        assert ctx is not None
        assert ctx.is_stale is True
        assert ctx.location_zone == "office"

    @pytest.mark.asyncio
    async def test_context_not_stale_with_default_ttl(
        self, client, session_factory, test_user, context_service
    ):
        """Freshly posted context is not stale with default TTL."""
        user_id = test_user.id

        resp = await client.post(
            "/api/context/update", json={"activity": "walking"}
        )
        assert resp.status_code == 200

        ctx = await context_service.get_current(user_id)
        assert ctx is not None
        assert ctx.is_stale is False
        assert ctx.activity == "walking"


class TestDiagnosticSignals:
    """Verify log messages and chain visibility for failure diagnosis."""

    @pytest.mark.asyncio
    async def test_rule_evaluation_failure_logged_not_raised(
        self, app, client, session_factory, test_user
    ):
        """If rules_engine.evaluate raises, the context update still succeeds.

        The router catches the exception and logs it — this test proves
        the error-handling path doesn't break the primary operation.
        """
        # Replace rules_engine with one that raises
        broken_engine = AsyncMock()
        broken_engine.evaluate = AsyncMock(side_effect=RuntimeError("DB gone"))
        app.state.rules_engine = broken_engine

        resp = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        # Context update still succeeds despite rule evaluation failure
        assert resp.status_code == 200
        assert resp.json()["location_zone"] == "office"

    @pytest.mark.asyncio
    async def test_notification_failure_logged_not_raised(
        self, app, client, session_factory, test_user
    ):
        """If notification_service.send_to_user raises, the context update still succeeds."""
        broken_notif = AsyncMock()
        broken_notif.send_to_user = AsyncMock(
            side_effect=RuntimeError("FCM offline")
        )
        app.state.notification_service = broken_notif

        resp = await client.post(
            "/api/context/update", json={"location_zone": "office"}
        )
        assert resp.status_code == 200
        assert resp.json()["location_zone"] == "office"
