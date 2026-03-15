"""Tests for workflow builder and explorer routes (M006/S07).

Tests the GET /browser/workflow/new, GET /browser/workflow/{id}/edit,
and GET /browser/workflow/explorer routes return proper responses,
including 404 handling for missing workflows.
"""

import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.workflow.models import WorkflowSpec
from app.workflow.service import WorkflowService
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
        username="wf_builder_testuser",
        email="wfbuilder@example.com",
        display_name="WF Builder Test",
    )
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def workflow_service(async_session_factory):
    """Provide a WorkflowService with in-memory database."""
    return WorkflowService(async_session_factory)


@pytest_asyncio.fixture
async def test_app(async_session_factory, workflow_service, test_user):
    """Create a minimal FastAPI app with workflow routes for testing."""
    from pathlib import Path
    from unittest.mock import AsyncMock

    from fastapi import FastAPI
    from jinja2_fragments.fastapi import Jinja2Blocks

    from app.workflow.router import browser_router

    app = FastAPI()

    # Set up templates pointing to the real template directory
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=templates_dir)
    templates.env.filters.setdefault("tojson", json.dumps)
    app.state.templates = templates
    app.state.workflow_service = workflow_service

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


class TestWorkflowBuilderNew:
    """Test GET /browser/workflow/new route."""

    async def test_returns_200(self, client):
        """Builder form renders in create mode."""
        resp = await client.get("/browser/workflow/new")
        assert resp.status_code == 200
        body = resp.text
        assert "New Workflow" in body
        assert 'id="wf-builder-name"' in body

    async def test_contains_step_types(self, client):
        """All valid step types appear in the template data."""
        resp = await client.get("/browser/workflow/new")
        body = resp.text
        for step_type in ["view", "dashboard", "form"]:
            assert step_type in body

    async def test_no_workflow_id_hidden_input(self, client):
        """Create mode should not include a hidden workflow ID."""
        resp = await client.get("/browser/workflow/new")
        assert 'id="wf-builder-workflow-id"' not in resp.text


class TestWorkflowBuilderEdit:
    """Test GET /browser/workflow/{id}/edit route."""

    async def test_returns_200_with_populated_data(self, client, workflow_service, test_user):
        """Edit mode renders with pre-populated fields from existing workflow."""
        workflow = await workflow_service.create(
            user_id=test_user.id,
            name="Test Workflow",
            description="A test desc",
            steps=[
                {"type": "view", "label": "Step 1", "config": {"spec_iri": "http://example.org/view1"}},
                {"type": "form", "label": "Step 2", "config": {"target_class": "http://example.org/MyClass"}},
            ],
        )

        resp = await client.get(f"/browser/workflow/{workflow.id}/edit")
        assert resp.status_code == 200
        body = resp.text
        assert "Edit Workflow" in body
        assert f'value="{workflow.id}"' in body
        assert "Test Workflow" in body
        assert "A test desc" in body

    async def test_returns_404_for_missing_workflow(self, client):
        """Edit route returns 404 for nonexistent workflow."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/browser/workflow/{fake_id}/edit")
        assert resp.status_code == 404

    async def test_returns_400_for_invalid_id(self, client):
        """Edit route returns 400 for malformed UUID."""
        resp = await client.get("/browser/workflow/not-a-uuid/edit")
        assert resp.status_code == 400


class TestWorkflowExplorer:
    """Test GET /browser/workflow/explorer route."""

    async def test_returns_200_empty(self, client):
        """Explorer renders with no workflows — shows empty message and new button."""
        resp = await client.get("/browser/workflow/explorer")
        assert resp.status_code == 200
        body = resp.text
        assert "No workflows yet" in body
        assert "New Workflow" in body

    async def test_lists_user_workflows(self, client, workflow_service, test_user):
        """Explorer lists workflows as clickable leaf nodes."""
        await workflow_service.create(
            user_id=test_user.id,
            name="Alpha Flow",
            steps=[{"type": "view", "label": "S1", "config": {"spec_iri": "http://ex.org/v1"}}],
        )
        await workflow_service.create(
            user_id=test_user.id,
            name="Beta Flow",
            steps=[{"type": "form", "label": "S1", "config": {"target_class": "http://ex.org/C1"}}],
        )

        resp = await client.get("/browser/workflow/explorer")
        assert resp.status_code == 200
        body = resp.text
        assert "Alpha Flow" in body
        assert "Beta Flow" in body
        assert "openWorkflowTab" in body
        assert "New Workflow" in body
        assert "No workflows yet" not in body

    async def test_new_workflow_button_calls_builder(self, client):
        """The + New Workflow button calls openWorkflowBuilderTab()."""
        resp = await client.get("/browser/workflow/explorer")
        body = resp.text
        assert "openWorkflowBuilderTab()" in body

    async def test_delete_button_present(self, client, workflow_service, test_user):
        """Explorer items have delete buttons."""
        await workflow_service.create(
            user_id=test_user.id,
            name="Deletable Flow",
            steps=[],
        )
        resp = await client.get("/browser/workflow/explorer")
        body = resp.text
        assert "_deleteWorkflow" in body
        assert 'title="Delete workflow"' in body
