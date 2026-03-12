# S04: Browser Router Refactor

**Goal:** Split the 1956-line `backend/app/browser/router.py` monolith into 6 focused domain sub-router modules with zero URL changes, zero behavior changes, and all 52 E2E tests passing unchanged.
**Demo:** The browser router directory contains 8 files (coordinator, helpers, 6 sub-routers). The app starts, all pages load, and all existing E2E tests pass. The `_validate_iri` test import still works.

## Must-Haves

- All 33 routes keep the exact same URL paths under `/browser/`
- `main.py` import `from app.browser.router import router as browser_router` unchanged
- `backend/tests/test_iri_validation.py` import path updated to `from app.browser._helpers import _validate_iri`
- Latent `Operation` import bug fixed in `objects.py` (was missing in original)
- All 52 existing E2E Playwright tests pass
- All existing backend pytest unit tests pass
- Route registration order preserved to avoid path-parameter shadowing

## Proof Level

- This slice proves: contract (structural refactor verified by existing test suite)
- Real runtime required: yes (Docker stack for E2E tests)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — all unit tests pass (including `test_iri_validation.py` with updated import)
- `cd e2e && npx playwright test` — all 52 E2E tests pass against Docker stack
- `python -c "from app.browser.router import router; print(len(router.routes))"` — route count matches original (33 routes + any auto-generated OPTIONS)
- `ls backend/app/browser/*.py | wc -l` — exactly 8 files (router.py, _helpers.py, settings.py, objects.py, events.py, search.py, workspace.py, pages.py)

## Observability / Diagnostics

- Runtime signals: FastAPI's built-in route registration logs at startup (shows all mounted paths)
- Inspection surfaces: `router.routes` list accessible at import time; `app.openapi()` shows all paths
- Failure visibility: import errors surface immediately at app startup; missing routes produce 404s detectable by E2E tests
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/browser/router.py` (the monolith being split), `backend/tests/test_iri_validation.py` (import path to update)
- New wiring introduced in this slice: `router.include_router()` calls in coordinator assembling 6 sub-routers
- What remains before the milestone is truly usable end-to-end: S05 (dependency pinning), S06 (federation), S07 (Obsidian import)

## Tasks

- [x] **T01: Extract shared helpers and settings/LLM sub-router** `est:45m`
  - Why: Creates the foundation (`_helpers.py`) all sub-routers depend on, plus extracts the first domain (settings + LLM, 7 routes) — validates the include_router pattern works end-to-end
  - Files: `backend/app/browser/_helpers.py`, `backend/app/browser/settings.py`, `backend/app/browser/router.py`
  - Do: Create `_helpers.py` with `_validate_iri`, `_format_date`, `_is_htmx_request`, `get_settings_service`, `get_icon_service`, `_MODELS_DIR`. Create `settings.py` with 7 settings/LLM routes. Update `router.py` to import and include the settings sub-router. Keep remaining routes in `router.py` for now. Update `test_iri_validation.py` import to `from app.browser._helpers import _validate_iri`.
  - Verify: `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` passes; app starts without import errors
  - Done when: `_helpers.py` and `settings.py` exist, settings sub-router included in coordinator, unit tests pass

- [x] **T02: Extract objects sub-router (CRUD, relations, edges, lint)** `est:45m`
  - Why: Extracts the largest domain (13 routes, ~800 lines) including the `Operation` import bug fix — this is the highest-risk extraction due to size and the latent bug
  - Files: `backend/app/browser/objects.py`, `backend/app/browser/router.py`
  - Do: Create `objects.py` with 13 object routes (`/object/{iri}`, `/tooltip/{iri}`, `/objects/{iri}/body`, `/relations/{iri}`, `/edge-provenance`, `/edge/delete`, `/objects/delete`, `/lint/{iri}`, `/types`, `/objects/new`, `/objects` POST, `/objects/{iri}/save`). Add missing `from app.events.store import Operation` import. Preserve all inline imports. Update `router.py` to include objects sub-router.
  - Verify: `cd backend && .venv/bin/pytest tests/ -v` passes; `python -c "from app.browser.objects import objects_router"` succeeds
  - Done when: `objects.py` exists with 13 routes and `Operation` import, coordinator includes it, unit tests pass

- [x] **T03: Extract events, search, workspace, and pages sub-routers** `est:45m`
  - Why: Extracts the remaining 4 domains (13 routes total), completing the split — events (3 routes), search (1 route), workspace (5 routes), pages (4 routes)
  - Files: `backend/app/browser/events.py`, `backend/app/browser/search.py`, `backend/app/browser/workspace.py`, `backend/app/browser/pages.py`, `backend/app/browser/router.py`
  - Do: Create 4 sub-router files. The coordinator `router.py` becomes a thin ~30-line file that creates `APIRouter(prefix="/browser")`, imports all 6 sub-routers, and calls `include_router()` for each in the original route registration order. Remove all handler code from `router.py`.
  - Verify: `cd backend && .venv/bin/pytest tests/ -v` passes; `python -c "from app.browser.router import router; print(len(router.routes))"` matches original count
  - Done when: All 6 sub-router files exist, `router.py` is a thin coordinator (~30 lines of real code), all unit tests pass

- [x] **T04: Full E2E verification and route count audit** `est:30m`
  - Why: The E2E suite is the definitive proof that zero behavior changed — this is the actual verification gate for REF-01
  - Files: (no new files — verification-only task)
  - Do: Start Docker test stack. Run all 52 Playwright E2E tests. Audit route count matches original. If any test fails, diagnose and fix the extraction (likely route order or missing import). Verify `docker compose up` starts cleanly with the refactored router.
  - Verify: `cd e2e && npx playwright test` — all 52 tests pass; Docker startup logs show all `/browser/*` routes registered
  - Done when: All 52 E2E tests pass, route count matches, Docker starts cleanly

## Files Likely Touched

- `backend/app/browser/router.py` (rewritten to thin coordinator)
- `backend/app/browser/_helpers.py` (new — shared utilities)
- `backend/app/browser/settings.py` (new — settings + LLM routes)
- `backend/app/browser/objects.py` (new — object CRUD routes)
- `backend/app/browser/events.py` (new — event log routes)
- `backend/app/browser/search.py` (new — search route)
- `backend/app/browser/workspace.py` (new — workspace/nav routes)
- `backend/app/browser/pages.py` (new — docs/canvas/lint-dashboard pages)
- `backend/tests/test_iri_validation.py` (import path update)
