---
id: T03
parent: S01
milestone: M047
key_files:
  - backend/tests/test_manifest_v2.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
key_decisions:
  - Mocked TriplestoreClient.query with ASK-compatible dict format (not CSV)
  - Parametrized backward compat test over all 8 model dirs
duration: 
verification_result: passed
completed_at: 2026-04-04T23:27:11.355Z
blocker_discovered: false
---

# T03: 43 unit tests proving v1 backward compat (8 models), v2 manifest parsing, TBox loader validation, source_model CRUD, and ModelService install/remove TBox lifecycle

**43 unit tests proving v1 backward compat (8 models), v2 manifest parsing, TBox loader validation, source_model CRUD, and ModelService install/remove TBox lifecycle**

## What Happened

Created three test files: test_manifest_v2.py (16 tests parametrized over all 8 model dirs), test_tbox_loader.py (14 tests covering valid/invalid JSON, missing files, missing fields), and test_tbox_lifecycle.py (13 tests for DashboardService/WorkflowService source_model CRUD plus ModelService integration with mocked triplestore). Fixed initial mock format from CSV string to ASK-compatible dict. All 43 tests pass, existing 27 dashboard tests confirmed no regressions.

## Verification

43/43 new tests pass (0.87s). 27/27 existing dashboard tests pass (0.76s). Slice-level verification (v2 manifest parse + TBox loader) passes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_manifest_v2.py tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v --tb=short` | 0 | ✅ pass | 870ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -v --tb=short` | 0 | ✅ pass | 760ms |
| 3 | `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; ..." (slice verification)` | 0 | ✅ pass | 200ms |

## Deviations

Plan said tbox_loader returns None on missing file — actual code raises ValueError. Adapted test. Plan said 6 models — there are 8. Parametrized over all 8.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_manifest_v2.py`
- `backend/tests/test_tbox_loader.py`
- `backend/tests/test_tbox_lifecycle.py`
