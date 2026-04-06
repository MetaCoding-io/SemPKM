"""Tests for ExplorerConfigSpec model and ExplorerConfigService.

Verifies CRUD operations, preset auto-creation, user isolation,
preset protection, and config_json round-trip.
"""

import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Import User so the users table is registered in Base.metadata (Knowledge #8)
from app.auth.models import User
from app.browser.explorer_models import ExplorerConfigSpec
from app.browser.explorer_config_service import (
    ExplorerConfigData,
    ExplorerConfigService,
    PRESETS,
)
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
async def service(async_session_factory):
    """Provide an ExplorerConfigService with in-memory database."""
    return ExplorerConfigService(async_session_factory)


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


@pytest_asyncio.fixture
async def user_b_id(async_session_factory):
    """Create a second test user and return their ID."""
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="otheruser",
            email="other@example.com",
            display_name="Other User",
        )
        session.add(user)
        await session.commit()
        return user.id


class TestExplorerConfigCreate:
    """Test configuration creation."""

    @pytest.mark.asyncio
    async def test_create_minimal(self, service, user_id):
        result = await service.create(user_id=user_id, name="My Config")
        assert result.name == "My Config"
        assert result.config == {}
        assert result.is_preset is False
        assert result.user_id == str(user_id)
        assert result.id  # UUID string

    @pytest.mark.asyncio
    async def test_create_with_config(self, service, user_id):
        config = {"group_by": "type", "sort_by": "label", "sort_order": "asc"}
        result = await service.create(
            user_id=user_id, name="Typed View", config=config
        )
        assert result.name == "Typed View"
        assert result.config == config
        assert result.is_preset is False

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, service, user_id):
        result = await service.create(user_id=user_id, name="Timestamped")
        assert result.created_at
        assert result.updated_at


class TestExplorerConfigGet:
    """Test get by ID."""

    @pytest.mark.asyncio
    async def test_get_existing(self, service, user_id):
        created = await service.create(user_id=user_id, name="FindMe")
        found = await service.get(uuid.UUID(created.id))
        assert found is not None
        assert found.name == "FindMe"
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, service):
        result = await service.get(uuid.uuid4())
        assert result is None


class TestExplorerConfigList:
    """Test listing configs for a user."""

    @pytest.mark.asyncio
    async def test_list_returns_user_configs(self, service, user_id):
        await service.create(user_id=user_id, name="Config A")
        await service.create(user_id=user_id, name="Config B")
        configs = await service.list_for_user(user_id)
        names = [c.name for c in configs]
        assert "Config A" in names
        assert "Config B" in names

    @pytest.mark.asyncio
    async def test_list_includes_presets(self, service, user_id):
        await service.get_or_create_presets()
        await service.create(user_id=user_id, name="My Custom")
        configs = await service.list_for_user(user_id)
        names = [c.name for c in configs]
        assert "By Type" in names
        assert "By Tag" in names
        assert "My Custom" in names

    @pytest.mark.asyncio
    async def test_list_presets_first(self, service, user_id):
        """Presets should appear before user configs in the listing."""
        await service.get_or_create_presets()
        await service.create(user_id=user_id, name="AAA Custom")
        configs = await service.list_for_user(user_id)
        # All presets should come before non-presets
        preset_indices = [i for i, c in enumerate(configs) if c.is_preset]
        non_preset_indices = [i for i, c in enumerate(configs) if not c.is_preset]
        if preset_indices and non_preset_indices:
            assert max(preset_indices) < min(non_preset_indices)


class TestExplorerConfigUpdate:
    """Test configuration updates."""

    @pytest.mark.asyncio
    async def test_update_name(self, service, user_id):
        created = await service.create(user_id=user_id, name="Old Name")
        updated = await service.update(
            uuid.UUID(created.id), user_id, name="New Name"
        )
        assert updated is not None
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_config(self, service, user_id):
        created = await service.create(
            user_id=user_id,
            name="Updateable",
            config={"group_by": "type"},
        )
        new_config = {"group_by": "tag", "sort_by": "created"}
        updated = await service.update(
            uuid.UUID(created.id), user_id, config=new_config
        )
        assert updated is not None
        assert updated.config == new_config

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, service, user_id):
        result = await service.update(uuid.uuid4(), user_id, name="Nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_wrong_user(self, service, user_id, user_b_id):
        created = await service.create(user_id=user_id, name="Mine")
        result = await service.update(
            uuid.UUID(created.id), user_b_id, name="Stolen"
        )
        assert result is None


class TestExplorerConfigDelete:
    """Test configuration deletion."""

    @pytest.mark.asyncio
    async def test_delete_user_config(self, service, user_id):
        created = await service.create(user_id=user_id, name="Deletable")
        deleted = await service.delete(uuid.UUID(created.id), user_id)
        assert deleted is True
        # Verify it's gone
        found = await service.get(uuid.UUID(created.id))
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service, user_id):
        deleted = await service.delete(uuid.uuid4(), user_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user(self, service, user_id, user_b_id):
        created = await service.create(user_id=user_id, name="Mine")
        deleted = await service.delete(uuid.UUID(created.id), user_b_id)
        assert deleted is False
        # Should still exist
        found = await service.get(uuid.UUID(created.id))
        assert found is not None


class TestPresets:
    """Test built-in preset auto-creation."""

    @pytest.mark.asyncio
    async def test_get_or_create_presets_creates(self, service):
        presets = await service.get_or_create_presets()
        assert len(presets) == 2
        names = {p.name for p in presets}
        assert "By Type" in names
        assert "By Tag" in names
        for p in presets:
            assert p.is_preset is True
            assert p.user_id is None

    @pytest.mark.asyncio
    async def test_get_or_create_presets_idempotent(self, service):
        presets1 = await service.get_or_create_presets()
        presets2 = await service.get_or_create_presets()
        assert len(presets1) == len(presets2)
        # Same IDs
        ids1 = {p.id for p in presets1}
        ids2 = {p.id for p in presets2}
        assert ids1 == ids2

    @pytest.mark.asyncio
    async def test_preset_config_values(self, service):
        presets = await service.get_or_create_presets()
        by_type = next(p for p in presets if p.name == "By Type")
        assert by_type.config == {
            "group_by": "type",
            "sort_by": "label",
            "sort_order": "asc",
        }
        by_tag = next(p for p in presets if p.name == "By Tag")
        assert by_tag.config == {
            "group_by": "tag",
            "sort_by": "label",
            "sort_order": "asc",
        }

    @pytest.mark.asyncio
    async def test_delete_preset_rejected(self, service, user_id):
        """Presets cannot be deleted via the user delete method."""
        presets = await service.get_or_create_presets()
        preset_id = uuid.UUID(presets[0].id)
        deleted = await service.delete(preset_id, user_id)
        assert deleted is False
        # Still exists
        found = await service.get(preset_id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update_preset_rejected(self, service, user_id):
        """Presets cannot be updated by users."""
        presets = await service.get_or_create_presets()
        preset_id = uuid.UUID(presets[0].id)
        result = await service.update(preset_id, user_id, name="Hacked")
        assert result is None


class TestUserIsolation:
    """Test that users can only see/modify their own configs."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_configs(
        self, service, user_id, user_b_id
    ):
        await service.create(user_id=user_id, name="A's Config")
        await service.create(user_id=user_b_id, name="B's Config")

        a_configs = await service.list_for_user(user_id)
        b_configs = await service.list_for_user(user_b_id)

        a_names = {c.name for c in a_configs if not c.is_preset}
        b_names = {c.name for c in b_configs if not c.is_preset}

        assert "A's Config" in a_names
        assert "B's Config" not in a_names
        assert "B's Config" in b_names
        assert "A's Config" not in b_names


class TestConfigJsonRoundTrip:
    """Test that complex config_json values survive create/get cycle."""

    @pytest.mark.asyncio
    async def test_complex_config_round_trip(self, service, user_id):
        config = {
            "group_by": "type",
            "sort_by": "label",
            "sort_order": "desc",
            "type_filter": "http://example.org/Task",
            "show_count": True,
            "nested": {"key": "value", "list": [1, 2, 3]},
        }
        created = await service.create(
            user_id=user_id, name="Complex", config=config
        )
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is not None
        assert fetched.config == config

    @pytest.mark.asyncio
    async def test_empty_config(self, service, user_id):
        created = await service.create(user_id=user_id, name="Empty")
        assert created.config == {}

    @pytest.mark.asyncio
    async def test_none_config_defaults_to_empty(self, service, user_id):
        created = await service.create(
            user_id=user_id, name="None Config", config=None
        )
        assert created.config == {}
