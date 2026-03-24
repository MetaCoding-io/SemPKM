"""Tests for ZoneService — CRUD for user geofence zones.

Covers create, list, get, update, delete, user isolation, and
missing-zone edge cases. Uses in-memory SQLite.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.context.zone_models import ContextZone
from app.context.zone_service import ZoneService
from app.db.base import Base

# Import User model so Base.metadata includes the 'users' table —
# needed because ContextZone has a FK to users.id.
import app.auth.models  # noqa: F401


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
def service(session_factory):
    return ZoneService(session_factory)


# ── Create ───────────────────────────────────────────────────────


class TestZoneCreate:
    @pytest.mark.asyncio
    async def test_create_zone(self, service, user_id):
        zone = await service.create(
            user_id=user_id,
            name="Home",
            latitude=40.7128,
            longitude=-74.0060,
            radius_meters=150.0,
            enabled=True,
        )
        assert zone.name == "Home"
        assert zone.latitude == 40.7128
        assert zone.longitude == -74.0060
        assert zone.radius_meters == 150.0
        assert zone.enabled is True
        assert zone.user_id == user_id
        assert zone.id is not None

    @pytest.mark.asyncio
    async def test_create_uses_defaults(self, service, user_id):
        zone = await service.create(
            user_id=user_id,
            name="Office",
            latitude=51.5074,
            longitude=-0.1278,
        )
        assert zone.radius_meters == 200.0
        assert zone.enabled is True

    @pytest.mark.asyncio
    async def test_create_multiple_zones(self, service, user_id):
        await service.create(user_id=user_id, name="Home", latitude=40.0, longitude=-74.0)
        await service.create(user_id=user_id, name="Office", latitude=41.0, longitude=-73.0)
        zones = await service.list_for_user(user_id)
        assert len(zones) == 2


# ── List ─────────────────────────────────────────────────────────


class TestZoneList:
    @pytest.mark.asyncio
    async def test_list_empty(self, service, user_id):
        zones = await service.list_for_user(user_id)
        assert zones == []

    @pytest.mark.asyncio
    async def test_list_returns_user_zones(self, service, user_id):
        await service.create(user_id=user_id, name="Alpha", latitude=10.0, longitude=20.0)
        await service.create(user_id=user_id, name="Beta", latitude=30.0, longitude=40.0)
        zones = await service.list_for_user(user_id)
        assert len(zones) == 2
        # Ordered by name
        assert zones[0].name == "Alpha"
        assert zones[1].name == "Beta"


# ── Get ──────────────────────────────────────────────────────────


class TestZoneGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        fetched = await service.get(zone.id, user_id)
        assert fetched is not None
        assert fetched.id == zone.id
        assert fetched.name == "Home"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, service, user_id):
        result = await service.get(uuid.uuid4(), user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_wrong_user_returns_none(self, service, user_id, other_user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        result = await service.get(zone.id, other_user_id)
        assert result is None


# ── Update ───────────────────────────────────────────────────────


class TestZoneUpdate:
    @pytest.mark.asyncio
    async def test_update_name(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        updated = await service.update(zone.id, user_id, name="My House")
        assert updated is not None
        assert updated.name == "My House"
        # Other fields preserved
        assert updated.latitude == 40.0

    @pytest.mark.asyncio
    async def test_update_coordinates(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Office", latitude=40.0, longitude=-74.0
        )
        updated = await service.update(zone.id, user_id, latitude=41.0, longitude=-73.0)
        assert updated.latitude == 41.0
        assert updated.longitude == -73.0

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, service, user_id):
        result = await service.update(uuid.uuid4(), user_id, name="Nowhere")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_wrong_user_returns_none(self, service, user_id, other_user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        result = await service.update(zone.id, other_user_id, name="Hacked")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_enabled_flag(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        updated = await service.update(zone.id, user_id, enabled=False)
        assert updated.enabled is False

    @pytest.mark.asyncio
    async def test_update_radius(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        updated = await service.update(zone.id, user_id, radius_meters=500.0)
        assert updated.radius_meters == 500.0


# ── Delete ───────────────────────────────────────────────────────


class TestZoneDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, service, user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        result = await service.delete(zone.id, user_id)
        assert result is True
        # Verify gone
        zones = await service.list_for_user(user_id)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, service, user_id):
        result = await service.delete(uuid.uuid4(), user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user_returns_false(self, service, user_id, other_user_id):
        zone = await service.create(
            user_id=user_id, name="Home", latitude=40.0, longitude=-74.0
        )
        result = await service.delete(zone.id, other_user_id)
        assert result is False
        # Zone still exists for original user
        fetched = await service.get(zone.id, user_id)
        assert fetched is not None


# ── User Isolation ───────────────────────────────────────────────


class TestUserIsolation:
    @pytest.mark.asyncio
    async def test_list_only_returns_own_zones(self, service, user_id, other_user_id):
        await service.create(user_id=user_id, name="My Zone", latitude=10.0, longitude=20.0)
        await service.create(user_id=other_user_id, name="Their Zone", latitude=30.0, longitude=40.0)

        my_zones = await service.list_for_user(user_id)
        their_zones = await service.list_for_user(other_user_id)

        assert len(my_zones) == 1
        assert my_zones[0].name == "My Zone"
        assert len(their_zones) == 1
        assert their_zones[0].name == "Their Zone"
