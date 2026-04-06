---
id: T01
parent: S03
milestone: M053
key_files:
  - backend/app/services/marketplace.py
  - backend/app/admin/router.py
  - backend/tests/test_marketplace_service.py
key_decisions:
  - Used packaging.version.Version for semantic version comparison
  - Update endpoint downloads and verifies BEFORE removing old version to prevent data loss
duration: 
verification_result: passed
completed_at: 2026-04-06T03:45:04.386Z
blocker_discovered: false
---

# T01: Added check_updates() with packaging.version.Version comparison, a safe download-before-remove update endpoint, and 10 unit tests

**Added check_updates() with packaging.version.Version comparison, a safe download-before-remove update endpoint, and 10 unit tests**

## What Happened

Implemented three coordinated changes: (1) check_updates() method on MarketplaceRegistryService that compares installed model versions against the catalog using packaging.version.Version with malformed-version resilience, (2) POST /admin/models/{model_id}/update endpoint that safely downloads and verifies archives before removing the old version to prevent data loss, (3) update_status context dict passed to both admin_models and marketplace template contexts for downstream badge/button rendering. Wrote 10 unit tests covering all edge cases.

## Verification

All 30 tests pass (20 existing + 10 new TestCheckUpdates). Import verification clean. rg confirms check_updates() exists in service and is called from both admin endpoints. LSP diagnostics show no errors on either edited file.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v` | 0 | ✅ pass | 690ms |
| 2 | `cd backend && .venv/bin/python -c "from app.services.marketplace import MarketplaceRegistryService; print('import ok')"` | 0 | ✅ pass | 500ms |
| 3 | `rg 'check_updates' backend/app/services/marketplace.py backend/app/admin/router.py` | 0 | ✅ pass | 50ms |

## Deviations

Added httpx import to router.py for the update endpoint's direct download calls. Wrote 10 tests instead of the 7 specified — added malformed installed version and multi-model coverage.

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/marketplace.py`
- `backend/app/admin/router.py`
- `backend/tests/test_marketplace_service.py`
