---
estimated_steps: 39
estimated_files: 5
skills_used: []
---

# T02: Wire TBox lifecycle into ModelService install/remove and create test v2 manifest

Extend ModelService to create TBox dashboards/workflows on install and delete them on uninstall. Update the router to pass user_id. Create a minimal test v2 PPV manifest with one dashboard definition to prove the lifecycle.

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

## Inputs

- `backend/app/models/manifest.py`
- `backend/app/models/tbox_loader.py`
- `backend/app/dashboard/service.py`
- `backend/app/workflow/service.py`
- `backend/app/services/models.py`
- `backend/app/models/router.py`
- `backend/app/main.py`
- `models/ppv/manifest.yaml`

## Expected Output

- `backend/app/services/models.py`
- `backend/app/models/router.py`
- `backend/app/main.py`
- `models/ppv/dashboards/ppv.json`
- `models/ppv/manifest.yaml`

## Verification

cd backend && .venv/bin/python -c "
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
