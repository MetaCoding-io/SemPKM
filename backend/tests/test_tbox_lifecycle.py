"""Tests for TBox lifecycle — model-sourced dashboard/workflow CRUD and ModelService integration.

Verifies:
- DashboardService.create with source_model stores it correctly
- DashboardService.delete_by_model deletes only model-sourced rows
- DashboardService.list_by_model returns only model-sourced rows
- Same for WorkflowService
- ModelService.install with v2 manifest creates model-sourced dashboards
- ModelService.remove deletes model-sourced dashboards/workflows
- ModelService.install with v1 manifest creates zero dashboards/workflows
- ModelService.install with TBox creation failure still succeeds (degraded mode)
"""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.dashboard.models import DashboardSpec
from app.dashboard.service import DashboardService
from app.db.base import Base
from app.workflow.models import WorkflowSpec
from app.workflow.service import WorkflowService


MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_session_factory():
    """In-memory SQLite async session factory with all tables."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def user_id(async_session_factory):
    """Create a test user and return their UUID."""
    uid = uuid.uuid4()
    async with async_session_factory() as session:
        user = User(
            id=uid,
            username="tbox-tester",
            email="tbox@example.com",
            display_name="TBox Tester",
        )
        session.add(user)
        await session.commit()
    return uid


@pytest_asyncio.fixture
async def dash_service(async_session_factory):
    return DashboardService(async_session_factory)


@pytest_asyncio.fixture
async def wf_service(async_session_factory):
    return WorkflowService(async_session_factory)


# ---------------------------------------------------------------------------
# DashboardService source_model tests
# ---------------------------------------------------------------------------

class TestDashboardServiceSourceModel:
    """DashboardService model-sourced CRUD."""

    @pytest.mark.asyncio
    async def test_create_with_source_model(self, dash_service, user_id):
        """source_model is stored on create and returned in data."""
        data = await dash_service.create(
            user_id=user_id,
            name="Model Dashboard",
            source_model="ppv",
        )
        assert data.source_model == "ppv"
        assert data.name == "Model Dashboard"

    @pytest.mark.asyncio
    async def test_create_without_source_model(self, dash_service, user_id):
        """Dashboards without source_model have source_model=None."""
        data = await dash_service.create(
            user_id=user_id,
            name="User Dashboard",
        )
        assert data.source_model is None

    @pytest.mark.asyncio
    async def test_delete_by_model_removes_only_model_sourced(self, dash_service, user_id):
        """delete_by_model deletes model-sourced rows and leaves user-created ones."""
        await dash_service.create(user_id=user_id, name="Model Dash 1", source_model="ppv")
        await dash_service.create(user_id=user_id, name="Model Dash 2", source_model="ppv")
        await dash_service.create(user_id=user_id, name="User Dash", source_model=None)

        deleted = await dash_service.delete_by_model("ppv")
        assert deleted == 2

        remaining = await dash_service.list_for_user(user_id)
        assert len(remaining) == 1
        assert remaining[0].name == "User Dash"

    @pytest.mark.asyncio
    async def test_list_by_model(self, dash_service, user_id):
        """list_by_model returns only dashboards for the specified model."""
        await dash_service.create(user_id=user_id, name="PPV Dash", source_model="ppv")
        await dash_service.create(user_id=user_id, name="CRM Dash", source_model="crm")
        await dash_service.create(user_id=user_id, name="User Dash", source_model=None)

        ppv_dashes = await dash_service.list_by_model("ppv")
        assert len(ppv_dashes) == 1
        assert ppv_dashes[0].name == "PPV Dash"
        assert ppv_dashes[0].source_model == "ppv"


# ---------------------------------------------------------------------------
# WorkflowService source_model tests
# ---------------------------------------------------------------------------

class TestWorkflowServiceSourceModel:
    """WorkflowService model-sourced CRUD."""

    @pytest.mark.asyncio
    async def test_create_with_source_model(self, wf_service, user_id):
        """source_model is stored on create and returned in data."""
        data = await wf_service.create(
            user_id=user_id,
            name="Model Workflow",
            steps=[{"type": "form"}],
            source_model="ppv",
        )
        assert data.source_model == "ppv"
        assert data.name == "Model Workflow"

    @pytest.mark.asyncio
    async def test_create_without_source_model(self, wf_service, user_id):
        """Workflows without source_model have source_model=None."""
        data = await wf_service.create(
            user_id=user_id,
            name="User Workflow",
            steps=[{"type": "view"}],
        )
        assert data.source_model is None

    @pytest.mark.asyncio
    async def test_delete_by_model_removes_only_model_sourced(self, wf_service, user_id):
        """delete_by_model deletes model-sourced rows and leaves user-created ones."""
        await wf_service.create(
            user_id=user_id, name="Model WF 1",
            steps=[{"type": "form"}], source_model="ppv",
        )
        await wf_service.create(
            user_id=user_id, name="Model WF 2",
            steps=[{"type": "view"}], source_model="ppv",
        )
        await wf_service.create(
            user_id=user_id, name="User WF",
            steps=[{"type": "dashboard"}], source_model=None,
        )

        deleted = await wf_service.delete_by_model("ppv")
        assert deleted == 2

        remaining = await wf_service.list_for_user(user_id)
        assert len(remaining) == 1
        assert remaining[0].name == "User WF"

    @pytest.mark.asyncio
    async def test_list_by_model(self, wf_service, user_id):
        """list_by_model returns only workflows for the specified model."""
        await wf_service.create(
            user_id=user_id, name="PPV WF",
            steps=[{"type": "form"}], source_model="ppv",
        )
        await wf_service.create(
            user_id=user_id, name="CRM WF",
            steps=[{"type": "view"}], source_model="crm",
        )
        await wf_service.create(
            user_id=user_id, name="User WF",
            steps=[{"type": "dashboard"}], source_model=None,
        )

        ppv_wfs = await wf_service.list_by_model("ppv")
        assert len(ppv_wfs) == 1
        assert ppv_wfs[0].name == "PPV WF"
        assert ppv_wfs[0].source_model == "ppv"


# ---------------------------------------------------------------------------
# ModelService TBox lifecycle integration tests
# ---------------------------------------------------------------------------

def _mock_triplestore(model_installed: bool = False):
    """Create a mock TriplestoreClient that simulates a triplestore.

    Args:
        model_installed: If True, ASK query returns True (model exists).
    """
    client = AsyncMock()
    # is_model_installed uses ASK query → expects dict with "boolean" key
    client.query.return_value = {"boolean": model_installed}
    # construct returns empty turtle (no ontology triples)
    client.construct.return_value = ""
    # update succeeds
    client.update.return_value = None
    # clear_graph succeeds
    client.clear_graph.return_value = None
    return client


def _mock_event_store():
    """Create a mock EventStore."""
    es = AsyncMock()
    es.materialize_graph.return_value = None
    return es


def _mock_prefix_registry():
    """Create a mock PrefixRegistry."""
    pr = MagicMock()
    pr.register_model_prefixes = MagicMock()
    return pr


class TestModelServiceTboxLifecycle:
    """ModelService install/remove with TBox surface creation."""

    @pytest.mark.asyncio
    async def test_install_v2_creates_dashboards(self, dash_service, wf_service, user_id):
        """Install of a v2 model with dashboards entrypoint creates model-sourced dashboards."""
        from app.services.models import ModelService

        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")

        client = _mock_triplestore()
        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=dash_service,
            workflow_service=wf_service,
        )

        result = await service.install(ppv_dir, user_id=user_id)
        assert result.success, f"Install failed: {result.errors}"
        assert result.dashboards_created >= 1

        # Verify dashboards are in the DB
        model_dashes = await dash_service.list_by_model("ppv")
        assert len(model_dashes) >= 1
        assert model_dashes[0].source_model == "ppv"

    @pytest.mark.asyncio
    async def test_install_v2_creates_workflows_with_resolved_dashboards(self, dash_service, wf_service, user_id):
        """Install of PPV v2 creates workflows with dashboard_name resolved to dashboard_id."""
        from app.services.models import ModelService

        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")

        client = _mock_triplestore()
        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=dash_service,
            workflow_service=wf_service,
        )

        result = await service.install(ppv_dir, user_id=user_id)
        assert result.success, f"Install failed: {result.errors}"
        assert result.workflows_created == 5

        # Verify workflows are in the DB with resolved dashboard IDs
        model_wfs = await wf_service.list_by_model("ppv")
        assert len(model_wfs) == 5

        # Find the Weekly Review workflow — has 2 dashboard steps
        weekly = [w for w in model_wfs if w.name == "Weekly Review"]
        assert len(weekly) == 1
        steps = weekly[0].steps
        dashboard_steps = [s for s in steps if s["type"] == "dashboard"]
        assert len(dashboard_steps) == 2
        for step in dashboard_steps:
            assert "dashboard_id" in step["config"], f"dashboard_name not resolved: {step}"
            assert "dashboard_name" not in step["config"]

    @pytest.mark.asyncio
    async def test_install_v1_creates_zero_tbox(self, dash_service, wf_service, user_id):
        """Install of a v1 model creates zero dashboards/workflows (backward compat)."""
        from app.services.models import ModelService

        bpkm_dir = MODELS_DIR / "basic-pkm"
        if not bpkm_dir.exists():
            pytest.skip("basic-pkm model not found")

        client = _mock_triplestore()
        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=dash_service,
            workflow_service=wf_service,
        )

        result = await service.install(bpkm_dir, user_id=user_id)
        assert result.success, f"Install failed: {result.errors}"
        assert result.dashboards_created == 0
        assert result.workflows_created == 0

        model_dashes = await dash_service.list_by_model("basic-pkm")
        assert len(model_dashes) == 0

    @pytest.mark.asyncio
    async def test_install_without_user_id_skips_tbox(self, dash_service, wf_service):
        """Install without user_id skips TBox surface creation entirely."""
        from app.services.models import ModelService

        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")

        client = _mock_triplestore()
        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=dash_service,
            workflow_service=wf_service,
        )

        result = await service.install(ppv_dir, user_id=None)
        assert result.success
        assert result.dashboards_created == 0

    @pytest.mark.asyncio
    async def test_install_tbox_failure_returns_success_with_warning(self, wf_service, user_id):
        """TBox creation failure during install results in success with warning."""
        from app.services.models import ModelService

        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")

        # Use a dashboard service that always raises
        broken_dash_service = AsyncMock()
        broken_dash_service.create = AsyncMock(side_effect=RuntimeError("DB broke"))

        client = _mock_triplestore()
        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=broken_dash_service,
            workflow_service=wf_service,
        )

        result = await service.install(ppv_dir, user_id=user_id)
        assert result.success, f"Install should succeed in degraded mode: {result.errors}"
        assert any("TBox" in w or "tbox" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_remove_deletes_model_sourced_tbox(self, dash_service, wf_service, user_id):
        """Remove deletes model-sourced dashboards/workflows."""
        from app.services.models import ModelService

        # Pre-create some model-sourced dashboards
        await dash_service.create(
            user_id=user_id, name="PPV Dash", source_model="ppv",
        )
        await dash_service.create(
            user_id=user_id, name="User Dash", source_model=None,
        )

        # Simulate an installed model for the remove check
        client = _mock_triplestore(model_installed=True)

        service = ModelService(
            triplestore_client=client,
            event_store=_mock_event_store(),
            prefix_registry=_mock_prefix_registry(),
            dashboard_service=dash_service,
            workflow_service=wf_service,
        )

        result = await service.remove("ppv", user_id=user_id)
        assert result.success, f"Remove failed: {result.errors}"
        assert result.dashboards_deleted == 1

        # User dashboard should survive
        remaining = await dash_service.list_for_user(user_id)
        assert len(remaining) == 1
        assert remaining[0].name == "User Dash"

    @pytest.mark.asyncio
    async def test_install_v2_unresolved_dashboard_name_logs_warning(self, dash_service, wf_service, user_id):
        """Workflow referencing a non-existent dashboard name installs in degraded mode."""
        from app.services.models import ModelService
        import json
        import tempfile
        from pathlib import Path

        # Create a minimal v2 model with a workflow referencing a missing dashboard
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            # Manifest
            (model_dir / "manifest.yaml").write_text(
                "manifest_version: '2.0'\n"
                "modelId: test-unresolved\n"
                "version: 1.0.0\n"
                "name: Test Unresolved\n"
                "namespace: 'urn:sempkm:model:test-unresolved:'\n"
                "entrypoints:\n"
                "  workflows: workflows/test.json\n"
            )
            # Minimal JSON-LD files required by loader (ontology, shapes, views)
            minimal_jsonld = json.dumps({
                "@context": {"rdfs": "http://www.w3.org/2000/01/rdf-schema#"},
                "@graph": [],
            })
            for subdir in ("ontology", "shapes", "views"):
                d = model_dir / subdir
                d.mkdir()
                (d / "test-unresolved.jsonld").write_text(minimal_jsonld)
            wf_dir = model_dir / "workflows"
            wf_dir.mkdir()
            (wf_dir / "test.json").write_text(json.dumps({
                "workflows": [
                    {
                        "name": "Test Workflow",
                        "steps": [
                            {
                                "type": "dashboard",
                                "label": "Missing Dashboard",
                                "config": {"dashboard_name": "Nonexistent Dashboard"},
                            },
                        ],
                    },
                ],
            }))

            client = _mock_triplestore()
            service = ModelService(
                triplestore_client=client,
                event_store=_mock_event_store(),
                prefix_registry=_mock_prefix_registry(),
                dashboard_service=dash_service,
                workflow_service=wf_service,
            )

            result = await service.install(model_dir, user_id=user_id)
            assert result.success, f"Install failed: {result.errors}"
            assert result.workflows_created == 1

            # Verify the unresolved step retains dashboard_name
            model_wfs = await wf_service.list_by_model("test-unresolved")
            assert len(model_wfs) == 1
            step = model_wfs[0].steps[0]
            assert step["config"]["dashboard_name"] == "Nonexistent Dashboard"
            assert "dashboard_id" not in step["config"]
