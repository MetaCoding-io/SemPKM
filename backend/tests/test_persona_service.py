"""Tests for Persona model and PersonaService (M012/S03).

Verifies persona CRUD operations, single-active-persona constraint,
auto-activation on delete, and workspace state save/restore.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.db.base import Base
from app.persona.models import Persona
from app.persona.service import PersonaData, PersonaService


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
async def service(async_session_factory):
    """Provide a PersonaService with in-memory database."""
    return PersonaService(async_session_factory)


@pytest_asyncio.fixture
async def user_id(async_session_factory):
    """Create a test user and return their ID."""
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            email="test@example.com",
            display_name="Test User",
        )
        session.add(user)
        await session.commit()
        return user.id


class TestPersonaCreate:
    """Test persona creation."""

    async def test_create_persona(self, service, user_id):
        """Create a persona with a name and verify returned data."""
        result = await service.create(user_id=user_id, name="Research")
        assert result.name == "Research"
        assert result.user_id == str(user_id)
        assert result.layout_json == "{}"
        assert result.sidebar_positions_json == "{}"
        assert result.explorer_mode == "by-type"
        assert result.is_active is False
        assert result.id  # UUID string, non-empty
        assert result.created_at  # Non-empty timestamp
        assert result.updated_at  # Non-empty timestamp

    async def test_create_persona_with_state(self, service, user_id):
        """Create a persona with initial layout state."""
        result = await service.create(
            user_id=user_id,
            name="Writing",
            layout_json='{"panels":[]}',
            sidebar_positions_json='{"details":"left"}',
            explorer_mode="by-namespace",
        )
        assert result.name == "Writing"
        assert result.layout_json == '{"panels":[]}'
        assert result.sidebar_positions_json == '{"details":"left"}'
        assert result.explorer_mode == "by-namespace"


class TestPersonaList:
    """Test persona listing."""

    async def test_list_personas_empty(self, service, user_id):
        """List returns empty for user with no personas."""
        result = await service.list_for_user(user_id)
        assert result == []

    async def test_list_personas_ordered(self, service, user_id):
        """Create multiple personas, list returns alphabetically sorted."""
        await service.create(user_id=user_id, name="Zeta")
        await service.create(user_id=user_id, name="Alpha")
        await service.create(user_id=user_id, name="Mu")
        result = await service.list_for_user(user_id)
        assert len(result) == 3
        assert result[0].name == "Alpha"
        assert result[1].name == "Mu"
        assert result[2].name == "Zeta"


class TestPersonaGet:
    """Test persona retrieval."""

    async def test_get_persona(self, service, user_id):
        """Create then get by ID returns matching persona."""
        created = await service.create(user_id=user_id, name="Test")
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is not None
        assert fetched.name == "Test"
        assert fetched.id == created.id

    async def test_get_persona_not_found(self, service):
        """Returns None for nonexistent persona ID."""
        result = await service.get(uuid.uuid4())
        assert result is None


class TestPersonaUpdate:
    """Test persona updates."""

    async def test_update_persona_name(self, service, user_id):
        """Update name succeeds and reflects change."""
        created = await service.create(user_id=user_id, name="Old Name")
        updated = await service.update(uuid.UUID(created.id), user_id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_wrong_user(self, service, user_id):
        """Returns None when user_id doesn't match."""
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.update(uuid.UUID(created.id), other_user, name="Hack")
        assert result is None


class TestPersonaDelete:
    """Test persona deletion."""

    async def test_delete_persona(self, service, user_id):
        """Delete returns True and persona is gone from list."""
        created = await service.create(user_id=user_id, name="To Delete")
        result = await service.delete(uuid.UUID(created.id), user_id)
        assert result is True
        remaining = await service.list_for_user(user_id)
        assert len(remaining) == 0

    async def test_delete_active_activates_another(self, service, user_id):
        """Deleting active persona auto-activates the first remaining one."""
        p1 = await service.create(user_id=user_id, name="Alpha")
        p2 = await service.create(user_id=user_id, name="Beta")
        # Activate p1
        await service.activate(uuid.UUID(p1.id), user_id)
        # Delete p1 (the active one)
        result = await service.delete(uuid.UUID(p1.id), user_id)
        assert result is True
        # Beta should now be active
        remaining = await service.list_for_user(user_id)
        assert len(remaining) == 1
        assert remaining[0].name == "Beta"
        assert remaining[0].is_active is True

    async def test_delete_nonexistent(self, service, user_id):
        """Delete of nonexistent persona returns False."""
        result = await service.delete(uuid.uuid4(), user_id)
        assert result is False

    async def test_delete_wrong_user(self, service, user_id):
        """Delete with wrong user_id returns False."""
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.delete(uuid.UUID(created.id), other_user)
        assert result is False


class TestPersonaActivation:
    """Test persona activation and single-active constraint."""

    async def test_activate_persona(self, service, user_id):
        """Activate sets is_active=True on the target."""
        created = await service.create(user_id=user_id, name="Test")
        activated = await service.activate(uuid.UUID(created.id), user_id)
        assert activated is not None
        assert activated.is_active is True

    async def test_activate_only_one_active(self, service, user_id):
        """Create 3, activate each in turn — only the last is active."""
        p1 = await service.create(user_id=user_id, name="One")
        p2 = await service.create(user_id=user_id, name="Two")
        p3 = await service.create(user_id=user_id, name="Three")

        await service.activate(uuid.UUID(p1.id), user_id)
        await service.activate(uuid.UUID(p2.id), user_id)
        await service.activate(uuid.UUID(p3.id), user_id)

        personas = await service.list_for_user(user_id)
        active_count = sum(1 for p in personas if p.is_active)
        assert active_count == 1
        active = next(p for p in personas if p.is_active)
        assert active.id == p3.id

    async def test_get_active(self, service, user_id):
        """get_active returns the currently active persona."""
        created = await service.create(user_id=user_id, name="Active One")
        await service.activate(uuid.UUID(created.id), user_id)
        active = await service.get_active(user_id)
        assert active is not None
        assert active.id == created.id
        assert active.is_active is True

    async def test_get_active_none(self, service, user_id):
        """get_active returns None when no personas exist."""
        result = await service.get_active(user_id)
        assert result is None

    async def test_activate_wrong_user(self, service, user_id):
        """Activate with wrong user returns None."""
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.activate(uuid.UUID(created.id), other_user)
        assert result is None


class TestPersonaSaveState:
    """Test workspace state save operations."""

    async def test_save_state(self, service, user_id):
        """Save all state fields and verify they are stored."""
        created = await service.create(user_id=user_id, name="Stateful")
        updated = await service.save_state(
            uuid.UUID(created.id),
            user_id,
            layout_json='{"grid":{"root":{}}}',
            sidebar_positions_json='{"explorer":"left","details":"right"}',
            explorer_mode="by-namespace",
        )
        assert updated is not None
        assert updated.layout_json == '{"grid":{"root":{}}}'
        assert updated.sidebar_positions_json == '{"explorer":"left","details":"right"}'
        assert updated.explorer_mode == "by-namespace"

    async def test_save_state_partial(self, service, user_id):
        """Save only layout_json — other fields remain unchanged."""
        created = await service.create(
            user_id=user_id,
            name="Partial",
            layout_json='{"original": true}',
            sidebar_positions_json='{"original": "positions"}',
            explorer_mode="by-type",
        )
        updated = await service.save_state(
            uuid.UUID(created.id),
            user_id,
            layout_json='{"updated": true}',
        )
        assert updated is not None
        assert updated.layout_json == '{"updated": true}'
        # Others unchanged
        assert updated.sidebar_positions_json == '{"original": "positions"}'
        assert updated.explorer_mode == "by-type"

    async def test_save_state_wrong_user(self, service, user_id):
        """save_state with wrong user returns None."""
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.save_state(
            uuid.UUID(created.id),
            other_user,
            layout_json='{"hacked": true}',
        )
        assert result is None
