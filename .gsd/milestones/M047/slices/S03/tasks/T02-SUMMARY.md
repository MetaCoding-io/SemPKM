---
id: T02
parent: S03
milestone: M047
key_files:
  - models/ppv/workflows/ppv.json
  - models/ppv/manifest.yaml
  - backend/app/services/models.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
key_decisions:
  - Used full ViewSpec IRIs in workflow steps for consistency with dashboard view-embed blocks
  - _resolve_dashboard_names replaces dashboard_name with dashboard_id and removes the name key; unresolved names left as-is (degraded mode per D380)
duration: 
verification_result: passed
completed_at: 2026-04-05T00:06:40.661Z
blocker_discovered: false
---

# T02: Created 5 PPV workflows with dashboard_name→UUID resolution at install time

**Created 5 PPV workflows with dashboard_name→UUID resolution at install time**

## What Happened

Created models/ppv/workflows/ppv.json with 5 PPV workflow definitions (Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review) using view/dashboard/form step types. Added workflows entrypoint to manifest. Implemented _resolve_dashboard_names() helper in ModelService that replaces dashboard_name with dashboard_id UUIDs during install and refresh, with graceful degradation for unresolved names. Added 5 new tests covering real file loading, name resolution logic, and full lifecycle integration.

## Verification

All 32 tests pass across test_tbox_loader.py and test_tbox_lifecycle.py. JSON structure validation confirms 5 workflows. Manifest validation confirms workflows entrypoint. The originally-failing verification gate was a path issue (missing cd backend), not a code issue.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import json; w=json.load(open('models/ppv/workflows/ppv.json')); assert len(w['workflows'])==5"` | 0 | ✅ pass | 100ms |
| 2 | `python3 -c "import yaml; m=yaml.safe_load(open('models/ppv/manifest.yaml')); assert m['entrypoints'].get('workflows')=='workflows/ppv.json'"` | 0 | ✅ pass | 100ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v` | 0 | ✅ pass | 940ms |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py::TestLoadTboxDashboards::test_real_ppv_dashboards -v` | 0 | ✅ pass | 50ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `models/ppv/workflows/ppv.json`
- `models/ppv/manifest.yaml`
- `backend/app/services/models.py`
- `backend/tests/test_tbox_loader.py`
- `backend/tests/test_tbox_lifecycle.py`
