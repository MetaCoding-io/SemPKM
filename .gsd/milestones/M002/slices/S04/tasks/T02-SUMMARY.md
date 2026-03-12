---
id: T02
parent: S04
milestone: M002
provides:
  - objects_router sub-router with 12 object/CRUD route handlers
  - Operation import bug fix (NameError in delete_edge and bulk_delete_objects)
key_files:
  - backend/app/browser/objects.py
  - backend/app/browser/router.py
key_decisions:
  - "Plan said 13 routes but only listed 12 paths — extracted the 12 that exist in the object domain; the count discrepancy was a plan estimation error, not a missing route"
patterns_established:
  - "Same sub-router pattern as T01: APIRouter(tags=[...]) with NO prefix, imported and included in coordinator"
observability_surfaces:
  - "objects_router.routes shows all 12 object routes; Operation import is verifiable at module load time"
  - "Import errors surface at app startup; missing routes produce 404s detectable by E2E tests"
duration: ~10min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Extract objects sub-router (CRUD, relations, edges, lint)

**Extracted 12 object/CRUD route handlers into `objects.py` sub-router, fixing the latent `Operation` NameError bug in `delete_edge` and `bulk_delete_objects`.**

## What Happened

Moved the entire object domain (CRUD, relations, edges, lint, type picker) from `router.py` into `backend/app/browser/objects.py` as a new `objects_router` sub-router. The extraction followed the same pattern as T01: `APIRouter(tags=["objects"])` with no prefix, imported and included via `router.include_router(objects_router)`.

Key changes:
- Created `objects.py` with 12 route handlers (~1176 lines)
- Added `from app.events.store import EventStore, Operation` as a top-level import, fixing the latent `NameError` bug where `Operation` was used in `delete_edge` (line 921) and `bulk_delete_objects` (line 1014) but never imported
- Cleaned up 7 unused imports from `router.py` (datetime, timezone, get_prefix_registry, get_validation_queue, PrefixRegistry, AsyncValidationQueue, _format_date)
- Updated module docstring in `router.py` to reflect its new coordinator role
- Router.py reduced from ~1646 lines to 507 lines

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — all 103 unit tests pass
- `cd backend && .venv/bin/python -c "from app.browser.objects import objects_router; print(len(objects_router.routes))"` — prints 12
- `cd backend && .venv/bin/python -c "from app.browser.router import router; print('OK')"` — coordinator imports cleanly
- Route count preserved: 33 routes with methods (same as pre-extraction)
- Route order within sub-router matches original file order exactly

### Slice-level checks (intermediate — partial pass expected):
- ✅ `cd backend && .venv/bin/pytest tests/ -v` — all 103 pass
- ✅ Route count: 33 (matches original)
- ⬜ E2E tests — not run (Docker stack not started; will verify on final task)
- ⬜ File count: 5 .py files (target is 9 at slice end)

## Diagnostics

- Import check: `python -c "from app.browser.objects import objects_router; print(objects_router.routes)"`
- Route count: `python -c "from app.browser.router import router; print(len([r for r in router.routes if hasattr(r, 'methods')]))"`
- Operation bug fix verified: `Operation` is now a top-level import in `objects.py`, so `delete_edge` and `bulk_delete_objects` will no longer crash with `NameError` at runtime

## Deviations

- Plan stated "13 routes" but only listed 12 explicit path patterns. Actual extraction is 12 handlers. The plan's route list is exhaustive and correct — the "13" count was an estimation error in the plan text.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — new sub-router with 12 object/CRUD route handlers and `Operation` import fix
- `backend/app/browser/router.py` — removed 12 extracted handlers, added objects_router import/include, cleaned unused imports, updated docstring
