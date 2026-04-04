---
id: T01
parent: S01
milestone: M047
key_files:
  - backend/app/models/manifest.py
  - backend/app/models/tbox_loader.py
  - backend/migrations/versions/025_add_source_model.py
  - backend/app/dashboard/models.py
  - backend/app/dashboard/service.py
  - backend/app/workflow/models.py
  - backend/app/workflow/service.py
key_decisions:
  - tbox_loader validates presence of 'name' for dashboards and 'name'+'steps' for workflows, raising ValueError with file path context
duration: 
verification_result: passed
completed_at: 2026-04-04T23:16:08.746Z
blocker_discovered: false
---

# T01: Added manifest v2 schema, source_model migration, model-sourced CRUD methods, and tbox_loader module

**Added manifest v2 schema, source_model migration, model-sourced CRUD methods, and tbox_loader module**

## What Happened

Extended ManifestSchema with manifest_version field and dashboards/workflows entrypoints on ManifestEntrypoints, both supporting {modelId} placeholder resolution. Created Alembic migration 025 adding nullable source_model column with index to dashboard_specs and workflow_specs. Extended DashboardService and WorkflowService with source_model parameter on create(), delete_by_model(), and list_by_model() methods. Created tbox_loader module with load_tbox_dashboards() and load_tbox_workflows() that read and validate JSON from model archives. All 8 existing v1 models parse unchanged.

## Verification

Ran 7 verification checks: v2 manifest parses with manifest_version and dashboards entrypoint, v1 manifest parses with None defaults, tbox_loader imports cleanly, all 8 existing models parse unchanged, ORM models have source_model attribute, service methods exist with correct signatures, tbox_loader validates malformed input correctly.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "ManifestSchema v2 test"` | 0 | ✅ pass | 1000ms |
| 2 | `python -c "ManifestSchema v1 test"` | 0 | ✅ pass | 1000ms |
| 3 | `python -c "tbox_loader import"` | 0 | ✅ pass | 1000ms |
| 4 | `python -c "parse all 8 models"` | 0 | ✅ pass | 1000ms |
| 5 | `python -c "service/model imports"` | 0 | ✅ pass | 1000ms |
| 6 | `python -c "tbox_loader validation"` | 0 | ✅ pass | 1000ms |
| 7 | `python -c "placeholder resolution"` | 0 | ✅ pass | 1000ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/models/manifest.py`
- `backend/app/models/tbox_loader.py`
- `backend/migrations/versions/025_add_source_model.py`
- `backend/app/dashboard/models.py`
- `backend/app/dashboard/service.py`
- `backend/app/workflow/models.py`
- `backend/app/workflow/service.py`
