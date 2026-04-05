---
id: T03
parent: S03
milestone: M047
key_files:
  - backend/app/dashboard/seed.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
key_decisions:
  - Unresolved dashboard name integration test creates a full minimal v2 model archive to exercise the real install pipeline rather than mocking around it
duration: 
verification_result: passed
completed_at: 2026-04-05T00:10:44.366Z
blocker_discovered: false
---

# T03: Trimmed SEED_WORKFLOWS to 1 generic entry, added unresolved dashboard_name integration test and seed/content validation tests — 35 tests pass

**Trimmed SEED_WORKFLOWS to 1 generic entry, added unresolved dashboard_name integration test and seed/content validation tests — 35 tests pass**

## What Happened

Removed 4 PPV-specific workflows (Weekly/Monthly/Quarterly/Yearly Review) and the _PPV namespace constant from seed.py, leaving only the generic "Create & Review" workflow. PPV review workflows are now model-sourced via models/ppv/workflows/ppv.json and installed through the TBox lifecycle. Added TestSeedWorkflows class with count and no-PPV-reference tests, updated test_real_ppv_dashboards to assert >= 5 dashboards with name-level checks, and added an unresolved dashboard_name integration test that creates a minimal v2 model archive to exercise the real install path in degraded mode.

## Verification

35 tests pass across test_tbox_loader.py and test_tbox_lifecycle.py. Seed workflow count assertion confirms exactly 1 entry. No _PPV constant remains in seed.py.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v` | 0 | ✅ pass | 950ms |
| 2 | `cd backend && .venv/bin/python -c "from app.dashboard.seed import SEED_WORKFLOWS; assert len(SEED_WORKFLOWS)==1; print('OK')"` | 0 | ✅ pass | 500ms |

## Deviations

The unresolved dashboard name integration test required creating full minimal v2 model archives (ontology/shapes/views JSON-LD files) because ModelService.install() validates the full archive before processing TBox entrypoints.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/seed.py`
- `backend/tests/test_tbox_loader.py`
- `backend/tests/test_tbox_lifecycle.py`
