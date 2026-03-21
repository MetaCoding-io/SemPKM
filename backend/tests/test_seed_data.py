"""Tests for seed_sample_data — idempotent sample data creation."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.dashboard.seed import seed_sample_data


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def dashboard_service():
    svc = AsyncMock()
    svc.list_for_user = AsyncMock(return_value=[])
    svc.create = AsyncMock()
    return svc


@pytest.fixture
def workflow_service():
    svc = AsyncMock()
    svc.list_for_user = AsyncMock(return_value=[])
    svc.create = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_seed_creates_dashboard_and_workflow_when_empty(
    dashboard_service, workflow_service, user_id
):
    """When user has no dashboards or workflows, seed creates both."""
    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result == {"dashboard_created": True, "workflow_created": True}

    # Dashboard was created with expected structure
    dashboard_service.create.assert_called_once()
    call_kwargs = dashboard_service.create.call_args
    assert call_kwargs.kwargs["user_id"] == user_id
    assert call_kwargs.kwargs["name"] == "Getting Started"
    assert call_kwargs.kwargs["layout"] == "sidebar-main"
    blocks = call_kwargs.kwargs["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["type"] == "markdown"
    assert blocks[1]["type"] == "view-embed"

    # Workflow was created with expected structure
    workflow_service.create.assert_called_once()
    wf_kwargs = workflow_service.create.call_args
    assert wf_kwargs.kwargs["user_id"] == user_id
    assert wf_kwargs.kwargs["name"] == "Create & Review"
    steps = wf_kwargs.kwargs["steps"]
    assert len(steps) == 2
    assert steps[0]["type"] == "form"
    assert steps[0]["label"] == "Create"
    assert steps[1]["type"] == "view"
    assert steps[1]["label"] == "Review"


@pytest.mark.asyncio
async def test_seed_skips_when_data_already_exists(
    dashboard_service, workflow_service, user_id
):
    """When user already has dashboards and workflows, seed creates nothing."""
    dashboard_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])
    workflow_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result == {"dashboard_created": False, "workflow_created": False}
    dashboard_service.create.assert_not_called()
    workflow_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_seed_creates_only_missing_item(
    dashboard_service, workflow_service, user_id
):
    """When user has dashboards but no workflows, only workflow is created."""
    dashboard_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])
    # workflow_service.list_for_user already returns [] from fixture

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result == {"dashboard_created": False, "workflow_created": True}
    dashboard_service.create.assert_not_called()
    workflow_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_seed_creates_only_dashboard_when_workflow_exists(
    dashboard_service, workflow_service, user_id
):
    """When user has workflows but no dashboards, only dashboard is created."""
    # dashboard_service.list_for_user already returns [] from fixture
    workflow_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result == {"dashboard_created": True, "workflow_created": False}
    dashboard_service.create.assert_called_once()
    workflow_service.create.assert_not_called()
