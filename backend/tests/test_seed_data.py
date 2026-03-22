"""Tests for seed_sample_data — idempotent sample data creation."""

import uuid
from unittest.mock import AsyncMock, call

import pytest

from app.dashboard.seed import seed_sample_data, SEED_WORKFLOWS


# ---- helpers ----------------------------------------------------------------

def _make_workflow(name: str) -> object:
    """Return a lightweight object with a ``.name`` attribute."""

    class _FakeWF:
        def __init__(self, n: str):
            self.name = n
            self.id = str(uuid.uuid4())

    return _FakeWF(name)


SEED_NAMES: list[str] = [w["name"] for w in SEED_WORKFLOWS]
REVIEW_NAMES: list[str] = [
    n for n in SEED_NAMES if n != "Create & Review"
]


# ---- fixtures ---------------------------------------------------------------

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


# ---- dashboard tests --------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_creates_dashboard_when_empty(
    dashboard_service, workflow_service, user_id
):
    """When user has no dashboards, seed creates the Getting Started dashboard."""
    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["dashboard_created"] is True
    dashboard_service.create.assert_called_once()
    kw = dashboard_service.create.call_args.kwargs
    assert kw["name"] == "Getting Started"
    assert kw["layout"] == "sidebar-main"
    blocks = kw["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["type"] == "markdown"
    assert blocks[1]["type"] == "view-embed"


@pytest.mark.asyncio
async def test_seed_skips_dashboard_when_exists(
    dashboard_service, workflow_service, user_id
):
    """When user already has a dashboard, seed does not create another."""
    dashboard_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["dashboard_created"] is False
    dashboard_service.create.assert_not_called()


# ---- workflow seed: fresh user (no workflows) --------------------------------

@pytest.mark.asyncio
async def test_seed_creates_all_workflows_when_empty(
    dashboard_service, workflow_service, user_id
):
    """When user has no workflows, all 5 seed workflows are created."""
    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["workflow_created"] is True
    assert result["workflows_created"] == len(SEED_WORKFLOWS)
    assert workflow_service.create.call_count == len(SEED_WORKFLOWS)

    # Verify all expected names appear in create calls
    created_names = {
        c.kwargs["name"] for c in workflow_service.create.call_args_list
    }
    assert created_names == set(SEED_NAMES)


@pytest.mark.asyncio
async def test_seed_review_workflow_step_details(
    dashboard_service, workflow_service, user_id
):
    """Verify PPV review workflows have correct step counts and types."""
    await seed_sample_data(dashboard_service, workflow_service, user_id)

    calls_by_name = {
        c.kwargs["name"]: c.kwargs
        for c in workflow_service.create.call_args_list
    }

    # Weekly Review: 4 steps (view, view, form, view)
    weekly = calls_by_name["Weekly Review"]
    assert len(weekly["steps"]) == 4
    assert weekly["steps"][0]["type"] == "view"
    assert weekly["steps"][2]["type"] == "form"
    assert "WeeklyReview" in weekly["steps"][2]["config"]["target_class"]

    # Monthly Review: 4 steps
    monthly = calls_by_name["Monthly Review"]
    assert len(monthly["steps"]) == 4
    assert "MonthlyReview" in monthly["steps"][2]["config"]["target_class"]

    # Quarterly Review: 3 steps
    quarterly = calls_by_name["Quarterly Review"]
    assert len(quarterly["steps"]) == 3
    assert "QuarterlyReview" in quarterly["steps"][1]["config"]["target_class"]

    # Yearly Review: 3 steps
    yearly = calls_by_name["Yearly Review"]
    assert len(yearly["steps"]) == 3
    assert "YearlyReview" in yearly["steps"][1]["config"]["target_class"]


# ---- workflow seed: idempotency (per-name) -----------------------------------

@pytest.mark.asyncio
async def test_seed_skips_when_all_seed_workflows_exist(
    dashboard_service, workflow_service, user_id
):
    """When all seed workflows already exist, none are created."""
    workflow_service.list_for_user = AsyncMock(
        return_value=[_make_workflow(n) for n in SEED_NAMES]
    )

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["workflow_created"] is False
    assert result["workflows_created"] == 0
    workflow_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_seed_review_workflows_idempotent(
    dashboard_service, workflow_service, user_id
):
    """Calling seed twice doesn't duplicate workflows."""
    # First call — empty
    await seed_sample_data(dashboard_service, workflow_service, user_id)
    assert workflow_service.create.call_count == len(SEED_WORKFLOWS)

    # Reset and simulate second call where all names now exist
    workflow_service.create.reset_mock()
    workflow_service.list_for_user = AsyncMock(
        return_value=[_make_workflow(n) for n in SEED_NAMES]
    )

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["workflow_created"] is False
    assert result["workflows_created"] == 0
    workflow_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_seed_partial_review_workflows(
    dashboard_service, workflow_service, user_id
):
    """When some seed workflows exist, only missing ones are created."""
    # Only "Create & Review" and "Weekly Review" already exist
    existing = [_make_workflow("Create & Review"), _make_workflow("Weekly Review")]
    workflow_service.list_for_user = AsyncMock(return_value=existing)

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["workflow_created"] is True
    assert result["workflows_created"] == 3  # Monthly, Quarterly, Yearly

    created_names = {
        c.kwargs["name"] for c in workflow_service.create.call_args_list
    }
    assert created_names == {"Monthly Review", "Quarterly Review", "Yearly Review"}


@pytest.mark.asyncio
async def test_seed_preserves_user_workflows(
    dashboard_service, workflow_service, user_id
):
    """User-created workflows are never deleted or overwritten.

    When a user has their own custom workflow, seeding still creates
    all 5 seed workflows without touching the custom one.
    """
    # User has one custom workflow
    workflow_service.list_for_user = AsyncMock(
        return_value=[_make_workflow("My Flow")]
    )

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    # All 5 seed workflows should be created (none match "My Flow")
    assert result["workflow_created"] is True
    assert result["workflows_created"] == len(SEED_WORKFLOWS)
    assert workflow_service.create.call_count == len(SEED_WORKFLOWS)

    # No delete calls — user's workflow is untouched
    assert not hasattr(workflow_service.delete, "call_count") or \
        workflow_service.delete.call_count == 0


# ---- backward compat: mixed dashboard + workflow scenarios -------------------

@pytest.mark.asyncio
async def test_seed_creates_only_dashboard_when_all_workflows_exist(
    dashboard_service, workflow_service, user_id
):
    """When user has all seed workflows but no dashboards, only dashboard is created."""
    workflow_service.list_for_user = AsyncMock(
        return_value=[_make_workflow(n) for n in SEED_NAMES]
    )

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["dashboard_created"] is True
    assert result["workflow_created"] is False
    dashboard_service.create.assert_called_once()
    workflow_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_seed_creates_only_workflows_when_dashboard_exists(
    dashboard_service, workflow_service, user_id
):
    """When user has a dashboard but no workflows, all seed workflows are created."""
    dashboard_service.list_for_user = AsyncMock(return_value=[{"id": "existing"}])

    result = await seed_sample_data(dashboard_service, workflow_service, user_id)

    assert result["dashboard_created"] is False
    assert result["workflow_created"] is True
    assert result["workflows_created"] == len(SEED_WORKFLOWS)
    dashboard_service.create.assert_not_called()
    assert workflow_service.create.call_count == len(SEED_WORKFLOWS)
