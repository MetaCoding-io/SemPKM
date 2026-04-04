---
estimated_steps: 28
estimated_files: 3
skills_used: []
---

# T03: Comprehensive tests for v1 backward compat and v2 TBox install/uninstall lifecycle

Write unit tests proving: (1) all 6 v1 models parse unchanged, (2) v2 manifests parse with new fields, (3) TBox loader reads/validates JSON dashboard/workflow files, (4) source_model column works in DashboardService and WorkflowService, (5) ModelService install creates TBox surfaces and uninstall removes them.

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

## Inputs

- `backend/app/models/manifest.py`
- `backend/app/models/tbox_loader.py`
- `backend/app/dashboard/service.py`
- `backend/app/workflow/service.py`
- `backend/app/services/models.py`
- `models/ppv/manifest.yaml`
- `models/ppv/dashboards/ppv.json`

## Expected Output

- `backend/tests/test_manifest_v2.py`
- `backend/tests/test_tbox_loader.py`
- `backend/tests/test_tbox_lifecycle.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_manifest_v2.py tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v --tb=short 2>&1 | tail -20
