"""Tests for ContextService — upsert and TTL staleness logic.

Covers insert, update-merge, staleness detection, and None return
for unknown users.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.context.models import UserContext
from app.context.service import ContextData, ContextService, DEFAULT_TTL_SECONDS
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
def service(session_factory):
    return ContextService(session_factory)


# ── Tests ────────────────────────────────────────────────────────


class TestContextServiceUpdate:
    """Insert and merge-update semantics."""

    @pytest.mark.asyncio
    async def test_insert_new_context(self, service, user_id):
        ctx = await service.update(user_id, location_zone="office")
        assert ctx.location_zone == "office"
        assert ctx.is_stale is False
        assert ctx.user_id == str(user_id)

    @pytest.mark.asyncio
    async def test_merge_update_preserves_existing_fields(self, service, user_id):
        await service.update(user_id, location_zone="office", activity="stationary")
        ctx = await service.update(user_id, activity="walking")
        assert ctx.location_zone == "office"  # preserved
        assert ctx.activity == "walking"  # updated

    @pytest.mark.asyncio
    async def test_update_returns_non_stale(self, service, user_id):
        ctx = await service.update(user_id, location_zone="home")
        assert ctx.is_stale is False

    @pytest.mark.asyncio
    async def test_update_partial_only_location(self, service, user_id):
        """Update with only location_zone leaves other fields unchanged."""
        await service.update(
            user_id,
            location_zone="office",
            activity="stationary",
            time_period="work_hours",
        )
        ctx = await service.update(user_id, location_zone="transit")
        assert ctx.location_zone == "transit"
        assert ctx.activity == "stationary"  # unchanged
        assert ctx.time_period == "work_hours"  # unchanged

    @pytest.mark.asyncio
    async def test_calendar_busy_default_false(self, service, user_id):
        """New context without explicit calendar_busy defaults to False."""
        ctx = await service.update(user_id, location_zone="office")
        assert ctx.calendar_busy is False

    @pytest.mark.asyncio
    async def test_device_id_persists_across_updates(self, service, user_id):
        """device_id set in one update survives a subsequent update."""
        await service.update(user_id, device_id="phone-01")
        ctx = await service.update(user_id, location_zone="transit")
        assert ctx.device_id == "phone-01"

    @pytest.mark.asyncio
    async def test_upsert_one_row_per_user(self, service, user_id, session_factory):
        """Multiple updates produce exactly one row, not appends."""
        await service.update(user_id, location_zone="office")
        await service.update(user_id, location_zone="home")
        await service.update(user_id, location_zone="transit")
        async with session_factory() as session:
            from sqlalchemy import func, select
            count = await session.scalar(
                select(func.count()).select_from(UserContext).where(
                    UserContext.user_id == user_id
                )
            )
            assert count == 1


class TestContextServiceGetCurrent:
    """Read and TTL staleness."""

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_user(self, service):
        result = await service.get_current(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_fresh_context(self, service, user_id):
        await service.update(user_id, location_zone="office")
        ctx = await service.get_current(user_id)
        assert ctx is not None
        assert ctx.location_zone == "office"
        assert ctx.is_stale is False

    @pytest.mark.asyncio
    async def test_stale_with_zero_ttl(self, service, user_id):
        """With TTL=0, any existing context is stale."""
        await service.update(user_id, location_zone="office")
        ctx = await service.get_current(user_id, ttl_seconds=0)
        assert ctx is not None
        assert ctx.is_stale is True

    @pytest.mark.asyncio
    async def test_context_data_includes_all_fields(self, service, user_id):
        await service.update(
            user_id,
            location_zone="transit",
            activity="walking",
            time_period="evening",
            device_id="phone-01",
        )
        ctx = await service.get_current(user_id)
        assert ctx.location_zone == "transit"
        assert ctx.activity == "walking"
        assert ctx.time_period == "evening"
        assert ctx.device_id == "phone-01"
        assert ctx.ttl_seconds == DEFAULT_TTL_SECONDS
        assert ctx.updated_at != ""

    @pytest.mark.asyncio
    async def test_includes_ttl_seconds(self, service, user_id):
        """Returned data includes the TTL value."""
        await service.update(user_id, location_zone="office")
        ctx = await service.get_current(user_id, ttl_seconds=42)
        assert ctx.ttl_seconds == 42

    @pytest.mark.asyncio
    async def test_update_returns_all_fields(self, service, user_id):
        """Verify all ContextData fields are present in returned data."""
        ctx = await service.update(
            user_id,
            location_zone="office",
            activity="stationary",
            time_period="work_hours",
            calendar_event="Standup",
            calendar_busy=True,
            device_id="laptop-01",
        )
        assert ctx.user_id == str(user_id)
        assert ctx.location_zone == "office"
        assert ctx.activity == "stationary"
        assert ctx.time_period == "work_hours"
        assert ctx.calendar_event == "Standup"
        assert ctx.calendar_busy is True
        assert ctx.device_id == "laptop-01"
        assert ctx.is_stale is False
        assert ctx.ttl_seconds == DEFAULT_TTL_SECONDS
        assert ctx.updated_at != ""
        assert ctx.created_at != ""
