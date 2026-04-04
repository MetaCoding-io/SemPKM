# S01: Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle

**Goal:** Manifest v2 format with optional dashboards/workflows entrypoints, source_model tracking on dashboard/workflow SQLite rows, and install/uninstall lifecycle that creates and removes model-sourced TBox surfaces. All 6 existing v1 models install unchanged.
**Demo:** After this: Install PPV with a v2 manifest carrying a test dashboard definition. Dashboard appears in workspace explorer tagged as model-sourced. Uninstall PPV — dashboard disappears. All 6 v1 models still install unchanged.

## Tasks
- [x] **T01: Added manifest v2 schema, source_model migration, model-sourced CRUD methods, and tbox_loader module** — Add manifest_version field and optional dashboards/workflows entrypoints to ManifestSchema. Create Alembic migration adding nullable source_model column to dashboard_specs and workflow_specs. Extend DashboardService and WorkflowService with methods for model-sourced CRUD (create_for_model, delete_by_model, list_by_model). Add a TBox loader module that reads JSON dashboard/workflow files from model archives.

## Steps

1. Edit `backend/app/models/manifest.py`:
   - Add `manifest_version: str | None = None` field to ManifestSchema (Optional, default None)
   - Add `dashboards: str | None = None` and `workflows: str | None = None` to ManifestEntrypoints
   - Add {modelId} placeholder resolution for the new entrypoint fields in the model_validator

2. Create Alembic migration `backend/migrations/versions/025_add_source_model.py`:
   - Revision 025, revises 024
   - `op.add_column('dashboard_specs', sa.Column('source_model', sa.String(64), nullable=True))`
   - `op.add_column('workflow_specs', sa.Column('source_model', sa.String(64), nullable=True))`
   - Add index on source_model for both tables (efficient delete-by-model)
   - downgrade: drop columns

3. Edit `backend/app/dashboard/models.py`:
   - Add `source_model: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)` to DashboardSpec

4. Edit `backend/app/workflow/models.py`:
   - Add `source_model: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)` to WorkflowSpec

5. Extend `backend/app/dashboard/service.py`:
   - Add `source_model` param to `create()` method (Optional[str] = None), pass to DashboardSpec constructor
   - Add `source_model` field to DashboardData dataclass, populate in `_to_data()`
   - Add `async def delete_by_model(self, model_id: str) -> int` — DELETE WHERE source_model = model_id, returns rowcount
   - Add `async def list_by_model(self, model_id: str) -> list[DashboardData]` — SELECT WHERE source_model = model_id

6. Extend `backend/app/workflow/service.py`:
   - Same 3 additions as dashboard: source_model param on create, delete_by_model, list_by_model
   - Add `source_model` field to WorkflowData dataclass

7. Create `backend/app/models/tbox_loader.py`:
   - `load_tbox_dashboards(model_dir: Path, manifest: ManifestSchema) -> list[dict] | None` — loads JSON file at entrypoints.dashboards path, returns list of dashboard dicts, or None if no entrypoint
   - `load_tbox_workflows(model_dir: Path, manifest: ManifestSchema) -> list[dict] | None` — same for workflows
   - JSON format: `{"dashboards": [...]}` where each item has name, description, layout, blocks (matching DashboardService.create params)
   - Validation: check each dashboard has required 'name' field, each workflow has required 'name' and 'steps' fields
   - Raise ValueError with clear message on malformed JSON
  - Estimate: 1h
  - Files: backend/app/models/manifest.py, backend/migrations/versions/025_add_source_model.py, backend/app/dashboard/models.py, backend/app/workflow/models.py, backend/app/dashboard/service.py, backend/app/workflow/service.py, backend/app/models/tbox_loader.py
  - Verify: cd backend && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:', manifest_version='2.0', entrypoints={'dashboards': 'dashboards/test.json'}); print('v2 OK:', m.manifest_version, m.entrypoints.dashboards)" && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:'); print('v1 OK:', m.manifest_version is None, m.entrypoints.dashboards is None)" && .venv/bin/python -c "from app.models.tbox_loader import load_tbox_dashboards; print('loader imported OK')"
- [x] **T02: Wire TBox dashboard/workflow lifecycle into ModelService install/remove/refresh and create PPV v2 manifest with test dashboard** — Extend ModelService to create TBox dashboards/workflows on install and delete them on uninstall. Update the router to pass user_id. Create a minimal test v2 PPV manifest with one dashboard definition to prove the lifecycle.

## Steps

1. Edit `backend/app/services/models.py` — ModelService.__init__:
   - Add `dashboard_service: DashboardService | None = None` and `workflow_service: WorkflowService | None = None` optional params
   - Store as `self._dashboard_service` and `self._workflow_service`
   - Making them optional preserves backward compat for tests that construct ModelService without them

2. Edit `backend/app/services/models.py` — ModelService.install():
   - Add `user_id: uuid.UUID | None = None` parameter
   - After seed materialization (step 8), add TBox dashboard/workflow creation:
     - Import and call `load_tbox_dashboards()` / `load_tbox_workflows()` from tbox_loader
     - For each dashboard: call `self._dashboard_service.create(user_id=user_id, name=d['name'], layout=d.get('layout', 'gridstack'), blocks=d.get('blocks', []), description=d.get('description', ''), source_model=model_id)`
     - Same pattern for workflows
     - Wrap in try/except — TBox creation failure is a warning (degraded mode), not install failure, per D380
     - Log count of created dashboards/workflows
   - Add created counts to InstallResult (new optional fields: dashboards_created: int = 0, workflows_created: int = 0)

3. Edit `backend/app/services/models.py` — ModelService.remove():
   - Add `user_id: uuid.UUID | None = None` parameter (used for authorization check but model-sourced deletes don't need it)
   - Before graph clearing (step 4), delete model-sourced dashboards/workflows:
     - Call `self._dashboard_service.delete_by_model(model_id)` and `self._workflow_service.delete_by_model(model_id)`
     - Log counts
     - Wrap in try/except — deletion failure is a warning
   - Add deleted counts to RemoveResult (new optional fields: dashboards_deleted: int = 0, workflows_deleted: int = 0)

4. Edit `backend/app/services/models.py` — ModelService.refresh_artifacts():
   - Add `user_id: uuid.UUID | None = None` parameter
   - After artifact graph refresh, delete old model-sourced dashboards/workflows and recreate from disk
   - This enables model updates to refresh TBox surfaces

5. Edit `backend/app/models/router.py`:
   - Pass `user.id` to `model_service.install(model_dir, user_id=user.id)`
   - Pass `user.id` to `model_service.remove(model_id, user_id=user.id)` (not strictly needed but consistent)

6. Edit `backend/app/main.py`:
   - Pass `dashboard_service` and `workflow_service` to ModelService constructor

7. Create `models/ppv/dashboards/ppv.json`:
   - Minimal JSON with one test dashboard: 'PPV Test Dashboard' with a markdown block
   - Format: `{"dashboards": [{"name": "PPV Test Dashboard", "description": "Test TBox dashboard", "layout": "single", "blocks": [{"type": "markdown", "config": {"content": "# PPV Test\n\nThis dashboard was installed from the PPV model."}}]}]}`

8. Edit `models/ppv/manifest.yaml`:
   - Add `manifest_version: "2.0"` 
   - Add `dashboards: "dashboards/ppv.json"` to entrypoints
   - Bump version to "2.0.0"

9. Verify the complete lifecycle works by running the import chain end-to-end in a Python check.
  - Estimate: 1.5h
  - Files: backend/app/services/models.py, backend/app/models/router.py, backend/app/main.py, models/ppv/dashboards/ppv.json, models/ppv/manifest.yaml
  - Verify: cd backend && .venv/bin/python -c "
from app.models.manifest import parse_manifest
from pathlib import Path
m = parse_manifest(Path('../models/ppv'))
assert m.manifest_version == '2.0', f'Expected 2.0, got {m.manifest_version}'
assert m.entrypoints.dashboards is not None, 'dashboards entrypoint missing'
print('v2 manifest parses OK')
from app.models.tbox_loader import load_tbox_dashboards
dashes = load_tbox_dashboards(Path('../models/ppv'), m)
assert dashes is not None and len(dashes) >= 1, f'Expected >=1 dashboard, got {dashes}'
print(f'Loaded {len(dashes)} dashboard(s) from PPV v2')
" && echo 'T02 verification passed'
- [ ] **T03: Comprehensive tests for v1 backward compat and v2 TBox install/uninstall lifecycle** — Write unit tests proving: (1) all 6 v1 models parse unchanged, (2) v2 manifests parse with new fields, (3) TBox loader reads/validates JSON dashboard/workflow files, (4) source_model column works in DashboardService and WorkflowService, (5) ModelService install creates TBox surfaces and uninstall removes them.

## Steps

1. Create `backend/tests/test_manifest_v2.py`:
   - Test v1 manifests (no manifest_version) parse with manifest_version=None and dashboards/workflows=None
   - Test all 6 existing models parse without error (parametrize over model dirs)
   - Test v2 manifest with manifest_version='2.0' and dashboards entrypoint parses correctly
   - Test {modelId} placeholder resolution in dashboards/workflows entrypoint paths
   - Test v2 manifest without dashboards/workflows (optional fields) still parses

2. Create `backend/tests/test_tbox_loader.py`:
   - Test load_tbox_dashboards with valid JSON returns list of dicts
   - Test load_tbox_dashboards with None entrypoint returns None
   - Test load_tbox_dashboards with missing file returns None (graceful)
   - Test load_tbox_dashboards with malformed JSON raises ValueError
   - Test load_tbox_dashboards with missing 'name' field raises ValueError
   - Same 5 tests for load_tbox_workflows
   - Test with the real PPV dashboards/ppv.json file

3. Create `backend/tests/test_tbox_lifecycle.py`:
   - In-memory SQLite fixture with dashboard_specs and workflow_specs tables (include source_model column)
   - Test DashboardService.create with source_model param stores it correctly
   - Test DashboardService.delete_by_model deletes only model-sourced rows, not user rows
   - Test DashboardService.list_by_model returns only model-sourced rows
   - Same 3 tests for WorkflowService
   - Test ModelService.install with a v2 manifest creates dashboards tagged with source_model
   - Test ModelService.remove deletes model-sourced dashboards/workflows
   - Test ModelService.install with v1 manifest creates zero dashboards/workflows (backward compat)
   - Test ModelService.install with TBox creation failure still returns success with warning (degraded mode)

4. Run all existing tests to verify no regressions:
   - `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_manifest_v2.py tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v`
  - Estimate: 1.5h
  - Files: backend/tests/test_manifest_v2.py, backend/tests/test_tbox_loader.py, backend/tests/test_tbox_lifecycle.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_manifest_v2.py tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v --tb=short 2>&1 | tail -20
