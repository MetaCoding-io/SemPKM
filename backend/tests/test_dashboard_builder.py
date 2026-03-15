"""Tests for dashboard builder routes (M006/S04).

Tests the GET /browser/dashboard/new and GET /browser/dashboard/{id}/edit
routes return proper responses, including 404 handling for missing dashboards.
"""

import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.dashboard.models import DashboardSpec
from app.dashboard.service import DashboardService
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session_factory():
    """Provide an in-memory SQLite async session factory."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(async_session_factory):
    """Create a test user and return them."""
    user = User(
        id=uuid.uuid4(),
        username="builder_testuser",
        email="builder@example.com",
        display_name="Builder Test",
    )
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def dashboard_service(async_session_factory):
    """Provide a DashboardService with in-memory database."""
    return DashboardService(async_session_factory)


@pytest_asyncio.fixture
async def test_app(async_session_factory, dashboard_service, test_user):
    """Create a minimal FastAPI app with dashboard routes for testing."""
    from pathlib import Path
    from unittest.mock import AsyncMock

    from fastapi import FastAPI
    from jinja2_fragments.fastapi import Jinja2Blocks

    from app.dashboard.router import browser_router

    app = FastAPI()

    # Set up templates pointing to the real template directory
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=templates_dir)
    # Register the tojson filter (Jinja2 built-in in newer versions, but ensure it)
    templates.env.filters.setdefault("tojson", json.dumps)
    app.state.templates = templates
    app.state.dashboard_service = dashboard_service

    # Override auth dependency to return test user
    from app.auth.dependencies import get_current_user

    async def override_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_user
    app.include_router(browser_router)

    yield app


@pytest_asyncio.fixture
async def client(test_app):
    """Provide an async HTTP client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestDashboardBuilderNew:
    """Test GET /browser/dashboard/new route."""

    async def test_returns_200(self, client):
        """Builder form renders in create mode."""
        resp = await client.get("/browser/dashboard/new")
        assert resp.status_code == 200
        body = resp.text
        assert "New Dashboard" in body
        assert 'id="builder-name"' in body
        assert 'name="layout"' in body

    async def test_contains_layout_options(self, client):
        """All 5 layouts appear as radio options."""
        resp = await client.get("/browser/dashboard/new")
        body = resp.text
        for layout_name in ["single", "sidebar-main", "grid-2x2", "grid-3", "top-bottom"]:
            assert f'value="{layout_name}"' in body

    async def test_no_dashboard_id_hidden_input(self, client):
        """Create mode should not include a hidden dashboard ID."""
        resp = await client.get("/browser/dashboard/new")
        assert 'id="builder-dashboard-id"' not in resp.text


class TestDashboardBuilderEdit:
    """Test GET /browser/dashboard/{id}/edit route."""

    async def test_returns_200_with_populated_data(self, client, dashboard_service, test_user):
        """Edit mode renders with pre-populated fields from existing dashboard."""
        dashboard = await dashboard_service.create(
            user_id=test_user.id,
            name="Test Dashboard",
            layout="grid-2x2",
            description="A test desc",
            blocks=[
                {"type": "markdown", "slot": "top-left", "config": {"content": "Hello"}},
                {"type": "divider", "slot": "top-right", "config": {}},
            ],
        )

        resp = await client.get(f"/browser/dashboard/{dashboard.id}/edit")
        assert resp.status_code == 200
        body = resp.text
        assert "Edit Dashboard" in body
        assert f'value="{dashboard.id}"' in body
        assert "Test Dashboard" in body
        assert "A test desc" in body
        # grid-2x2 should be checked
        assert 'value="grid-2x2"' in body

    async def test_returns_404_for_missing_dashboard(self, client):
        """Edit route returns 404 for nonexistent dashboard."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/browser/dashboard/{fake_id}/edit")
        assert resp.status_code == 404

    async def test_returns_400_for_invalid_id(self, client):
        """Edit route returns 400 for malformed UUID."""
        resp = await client.get("/browser/dashboard/not-a-uuid/edit")
        assert resp.status_code == 400


class TestDashboardExplorer:
    """Test GET /browser/dashboard/explorer route."""

    async def test_returns_200_empty(self, client):
        """Explorer renders with no dashboards — shows empty message and new button."""
        resp = await client.get("/browser/dashboard/explorer")
        assert resp.status_code == 200
        body = resp.text
        assert "No dashboards yet" in body
        assert "New Dashboard" in body

    async def test_lists_user_dashboards(self, client, dashboard_service, test_user):
        """Explorer lists dashboards as clickable leaf nodes."""
        await dashboard_service.create(
            user_id=test_user.id,
            name="Alpha Board",
            layout="single",
            blocks=[],
        )
        await dashboard_service.create(
            user_id=test_user.id,
            name="Beta Board",
            layout="grid-2x2",
            blocks=[],
        )

        resp = await client.get("/browser/dashboard/explorer")
        assert resp.status_code == 200
        body = resp.text
        assert "Alpha Board" in body
        assert "Beta Board" in body
        # Should have openDashboardTab calls
        assert "openDashboardTab" in body
        # New Dashboard action always present
        assert "New Dashboard" in body
        # Empty message should NOT be present
        assert "No dashboards yet" not in body

    async def test_new_dashboard_button_calls_builder(self, client):
        """The + New Dashboard button calls openDashboardBuilderTab()."""
        resp = await client.get("/browser/dashboard/explorer")
        body = resp.text
        assert "openDashboardBuilderTab()" in body
