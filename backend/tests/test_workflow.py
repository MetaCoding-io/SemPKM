"""Tests for WorkflowSpec model and service (M006/S06).

Mirrors test_dashboard.py structure for consistency.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.workflow.models import WorkflowSpec, VALID_STEP_TYPES
from app.workflow.service import WorkflowService, WorkflowData
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def service(async_session_factory):
    return WorkflowService(async_session_factory)


@pytest_asyncio.fixture
async def user_id(async_session_factory):
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


class TestWorkflowModel:
    def test_valid_step_types(self):
        assert "view" in VALID_STEP_TYPES
        assert "dashboard" in VALID_STEP_TYPES
        assert "form" in VALID_STEP_TYPES


class TestWorkflowServiceCreate:
    async def test_create_minimal(self, service, user_id):
        result = await service.create(user_id=user_id, name="My Workflow")
        assert result.name == "My Workflow"
        assert result.steps == []
        assert result.id

    async def test_create_with_steps(self, service, user_id):
        steps = [
            {"type": "view", "label": "Review Notes", "config": {"spec_iri": "urn:test:view:1"}},
            {"type": "form", "label": "Create Note", "config": {"target_class": "bpkm:Note"}},
            {"type": "dashboard", "label": "Summary", "config": {"dashboard_id": "abc-123"}},
        ]
        result = await service.create(user_id=user_id, name="Weekly Reflection", steps=steps)
        assert len(result.steps) == 3
        assert result.steps[0]["type"] == "view"
        assert result.steps[1]["label"] == "Create Note"
        assert result.steps[2]["type"] == "dashboard"

    async def test_create_invalid_step_type(self, service, user_id):
        with pytest.raises(ValueError, match="Invalid step type"):
            await service.create(
                user_id=user_id,
                name="Bad",
                steps=[{"type": "invalid", "config": {}}],
            )


class TestWorkflowServiceGet:
    async def test_get_existing(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        fetched = await service.get(uuid.UUID(created.id))
        assert fetched is not None
        assert fetched.name == "Test"

    async def test_get_nonexistent(self, service):
        result = await service.get(uuid.uuid4())
        assert result is None


class TestWorkflowServiceList:
    async def test_list_empty(self, service, user_id):
        result = await service.list_for_user(user_id)
        assert result == []

    async def test_list_multiple(self, service, user_id):
        await service.create(user_id=user_id, name="Alpha")
        await service.create(user_id=user_id, name="Beta")
        result = await service.list_for_user(user_id)
        assert len(result) == 2
        assert result[0].name == "Alpha"


class TestWorkflowServiceUpdate:
    async def test_update_name(self, service, user_id):
        created = await service.create(user_id=user_id, name="Old")
        updated = await service.update(uuid.UUID(created.id), user_id, name="New")
        assert updated is not None
        assert updated.name == "New"

    async def test_update_steps(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        new_steps = [{"type": "view", "label": "Step 1", "config": {}}]
        updated = await service.update(uuid.UUID(created.id), user_id, steps=new_steps)
        assert updated is not None
        assert len(updated.steps) == 1

    async def test_update_wrong_user(self, service, user_id):
        created = await service.create(user_id=user_id, name="Test")
        result = await service.update(uuid.UUID(created.id), uuid.uuid4(), name="Hack")
        assert result is None


class TestWorkflowServiceDelete:
    async def test_delete_existing(self, service, user_id):
        created = await service.create(user_id=user_id, name="To Delete")
        result = await service.delete(uuid.UUID(created.id), user_id)
        assert result is True
        assert await service.get(uuid.UUID(created.id)) is None

    async def test_delete_nonexistent(self, service, user_id):
        result = await service.delete(uuid.uuid4(), user_id)
        assert result is False
