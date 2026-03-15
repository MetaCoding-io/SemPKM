"""Tests for DashboardSpec model and service (M006/S03).

Verifies dashboard CRUD operations, model validation, and block
configuration handling.
"""

import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.models import User
from app.dashboard.models import DashboardSpec, VALID_LAYOUTS, VALID_BLOCK_TYPES
from app.dashboard.service import DashboardService, DashboardData
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
    """Provide a DashboardService with in-memory database."""
    return DashboardService(async_session_factory)


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


class TestDashboardModel:
    """Test DashboardSpec model constants and structure."""

    def test_valid_layouts(self):
        assert "single" in VALID_LAYOUTS
        assert "sidebar-main" in VALID_LAYOUTS
        assert "grid-2x2" in VALID_LAYOUTS
        assert "grid-3" in VALID_LAYOUTS
        assert "top-bottom" in VALID_LAYOUTS

    def test_valid_block_types(self):
        assert "view-embed" in VALID_BLOCK_TYPES
        assert "markdown" in VALID_BLOCK_TYPES
        assert "object-embed" in VALID_BLOCK_TYPES
        assert "create-form" in VALID_BLOCK_TYPES
        assert "sparql-result" in VALID_BLOCK_TYPES
        assert "divider" in VALID_BLOCK_TYPES


class TestDashboardServiceCreate:
    """Test dashboard creation."""

    async def test_create_minimal(self, service, user_id):
        result = await service.create(user_id=user_id, name="My Dashboard")
        assert result.name == "My Dashboard"
        assert result.layout == "single"
        assert result.blocks == []
        assert result.id  # UUID string

    async def test_create_with_blocks(self, service, user_id):
        blocks = [
            {"type": "markdown", "config": {"content": "# Hello"}},
            {"type": "divider", "config": {}},
        ]
        result = await service.create(
            user_id=user_id,
            name="Block Dashboard",
            layout="grid-2x2",
            blocks=blocks,
        )
        assert result.layout == "grid-2x2"
        assert len(result.blocks) == 2
        assert result.blocks[0]["type"] == "markdown"

    async def test_create_invalid_layout(self, service, user_id):
        with pytest.raises(ValueError, match="Invalid layout"):
            await service.create(user_id=user_id, name="Bad", layout="nonexistent")

    async def test_create_invalid_block_type(self, service, user_id):
        with pytest.raises(ValueError, match="Invalid block type"):
            await service.create(
                user_id=user_id,
                name="Bad",
                blocks=[{"type": "invalid-type", "config": {}}],
            )


class TestDashboardServiceGet:
    """Test dashboard retrieval."""

    async def test_get_existing(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is not None
        assert fetched.name == "Test"
        assert fetched.id == created.id

    async def test_get_nonexistent(self, service):
        result = await service.get(uuid.uuid4())
        assert result is None


class TestDashboardServiceList:
    """Test dashboard listing."""

    async def test_list_empty(self, service, user_id):
        result = await service.list_for_user(user_id)
        assert result == []

    async def test_list_multiple(self, service, user_id):
        await service.create(user_id=user_id, name="Alpha")
        await service.create(user_id=user_id, name="Beta")
        result = await service.list_for_user(user_id)
        assert len(result) == 2
        # Sorted by name
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"


class TestDashboardServiceUpdate:
    """Test dashboard updates."""

    async def test_update_name(self, service, user_id):
        created = await service.create(user_id=user_id, name="Old Name")
        updated = await service.update(uuid.UUID(created.id), user_id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_blocks(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        new_blocks = [{"type": "markdown", "config": {"content": "Updated"}}]
        updated = await service.update(uuid.UUID(created.id), user_id, blocks=new_blocks)
        assert updated is not None
        assert len(updated.blocks) == 1
        assert updated.blocks[0]["config"]["content"] == "Updated"

    async def test_update_invalid_layout(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        with pytest.raises(ValueError, match="Invalid layout"):
            await service.update(uuid.UUID(created.id), user_id, layout="bad")

    async def test_update_nonexistent(self, service, user_id):
        result = await service.update(uuid.uuid4(), user_id, name="Nope")
        assert result is None

    async def test_update_wrong_user(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.update(uuid.UUID(created.id), other_user, name="Hack")
        assert result is None


class TestDashboardServiceDelete:
    """Test dashboard deletion."""

    async def test_delete_existing(self, service, user_id):
        created = await service.create(user_id=user_id, name="To Delete")
        result = await service.delete(uuid.UUID(created.id), user_id)
        assert result is True
        # Verify gone
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is None

    async def test_delete_nonexistent(self, service, user_id):
        result = await service.delete(uuid.uuid4(), user_id)
        assert result is False

    async def test_delete_wrong_user(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        other_user = uuid.uuid4()
        result = await service.delete(uuid.UUID(created.id), other_user)
        assert result is False


class TestDashboardRouter:
    """Test router layout definitions."""

    def test_layout_definitions_complete(self):
        from app.dashboard.router import LAYOUT_DEFINITIONS
        for layout in VALID_LAYOUTS:
            assert layout in LAYOUT_DEFINITIONS, f"Missing layout definition: {layout}"
            defn = LAYOUT_DEFINITIONS[layout]
            assert "css_class" in defn
            assert "slots" in defn
            assert "grid_template" in defn
            assert "columns" in defn
            assert len(defn["slots"]) > 0


class TestRenderBlockContextAttributes:
    """Test render_block view-embed context data attributes (S05/T01)."""

    async def test_view_embed_listens_to_context(self, service, user_id):
        """view-embed with listens_to_context produces data attributes."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
                "listens_to_context": "project",
            },
        }]
        created = await service.create(
            user_id=user_id, name="Context Dashboard", blocks=blocks,
        )
        # Now call render_block directly to check HTML output
        from app.dashboard.router import render_block
        from unittest.mock import AsyncMock, MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service
        mock_request.app.state.templates = MagicMock()

        # render_block returns HTMLResponse for view-embed
        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="",
            context_var="",
            user=mock_user,
        )
        html = response.body.decode()
        assert 'data-listens-to-context="project"' in html
        assert f'data-dashboard-id="{created.id}"' in html
        assert "dashboard_mode=1" in html

    async def test_view_embed_emits_context(self, service, user_id):
        """view-embed with emits_context produces data-emits-context attribute."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
                "emits_context": True,
            },
        }]
        created = await service.create(
            user_id=user_id, name="Emitter Dashboard", blocks=blocks,
        )
        from app.dashboard.router import render_block
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service

        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="",
            context_var="",
            user=mock_user,
        )
        html = response.body.decode()
        assert 'data-emits-context="1"' in html
        assert "dashboard_mode=1" in html

    async def test_view_embed_no_context_config(self, service, user_id):
        """view-embed without context config has no context data attributes."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
            },
        }]
        created = await service.create(
            user_id=user_id, name="Plain Dashboard", blocks=blocks,
        )
        from app.dashboard.router import render_block
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service

        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="",
            context_var="",
            user=mock_user,
        )
        html = response.body.decode()
        assert "data-listens-to-context" not in html
        assert "data-emits-context" not in html
        # But dashboard_mode=1 should still be there
        assert "dashboard_mode=1" in html

    async def test_view_embed_context_iri_passthrough(self, service, user_id):
        """view-embed with listens_to_context forwards context_iri to view URL."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
                "listens_to_context": "project",
            },
        }]
        created = await service.create(
            user_id=user_id, name="Consumer Dashboard", blocks=blocks,
        )
        from app.dashboard.router import render_block
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service

        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        # With context_iri — should appear in the view URL
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="http://example.org/proj1",
            context_var="project",
            user=mock_user,
        )
        html = response.body.decode()
        assert "context_iri=http%3A%2F%2Fexample.org%2Fproj1" in html
        assert "context_var=project" in html
        assert "dashboard_mode=1" in html

    async def test_view_embed_context_iri_not_forwarded_without_listens(self, service, user_id):
        """view-embed without listens_to_context does not forward context_iri."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
                "emits_context": True,
            },
        }]
        created = await service.create(
            user_id=user_id, name="Source Only", blocks=blocks,
        )
        from app.dashboard.router import render_block
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service

        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="http://example.org/proj1",
            context_var="project",
            user=mock_user,
        )
        html = response.body.decode()
        # emits_context blocks should not have context_iri in their view URL
        assert "context_iri=" not in html


class TestDashboardContextConfigRoundTrip:
    """Test context config fields survive create/update/retrieve cycle (S05/T03)."""

    async def test_roundtrip_emits_and_listens_config(self, service, user_id):
        """Create dashboard with emits/listens context config, retrieve, verify preserved."""
        blocks = [
            {
                "type": "view-embed",
                "config": {
                    "spec_iri": "urn:test:projects-view",
                    "renderer_type": "table",
                    "emits_context": True,
                },
            },
            {
                "type": "view-embed",
                "config": {
                    "spec_iri": "urn:test:notes-view",
                    "renderer_type": "cards",
                    "listens_to_context": "project",
                },
            },
        ]
        created = await service.create(
            user_id=user_id,
            name="Context Dashboard",
            layout="sidebar-main",
            blocks=blocks,
        )
        assert created.blocks[0]["config"]["emits_context"] is True
        assert created.blocks[1]["config"]["listens_to_context"] == "project"

        # Retrieve and verify
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is not None
        assert fetched.blocks[0]["config"]["emits_context"] is True
        assert fetched.blocks[1]["config"]["listens_to_context"] == "project"

    async def test_update_preserves_context_config(self, service, user_id):
        """Updating dashboard name doesn't clobber block context config."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:spec",
                "renderer_type": "table",
                "emits_context": True,
                "listens_to_context": "category",
            },
        }]
        created = await service.create(
            user_id=user_id, name="Original", blocks=blocks,
        )
        # Update name only
        updated = await service.update(
            uuid.UUID(created.id), user_id, name="Renamed",
        )
        assert updated is not None
        assert updated.name == "Renamed"
        # Block config unchanged
        assert updated.blocks[0]["config"]["emits_context"] is True
        assert updated.blocks[0]["config"]["listens_to_context"] == "category"

    async def test_view_embed_no_context_config_no_data_attrs(self, service, user_id):
        """view-embed without context config produces no data-listens/data-emits attrs."""
        blocks = [{
            "type": "view-embed",
            "config": {
                "spec_iri": "urn:test:plain",
                "renderer_type": "table",
            },
        }]
        created = await service.create(
            user_id=user_id, name="No Context", blocks=blocks,
        )
        from app.dashboard.router import render_block
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.app.state.dashboard_service = service

        from app.auth.models import User as AuthUser
        mock_user = AuthUser(
            id=user_id, username="test", email="t@t.com", display_name="T",
        )
        response = await render_block(
            request=mock_request,
            dashboard_id=created.id,
            block_index=0,
            context_iri="",
            context_var="",
            user=mock_user,
        )
        html = response.body.decode()
        assert "data-listens-to-context" not in html
        assert "data-emits-context" not in html
