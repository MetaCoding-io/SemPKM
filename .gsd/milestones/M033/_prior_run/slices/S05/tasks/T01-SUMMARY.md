---
id: T01
parent: S05
milestone: M033
provides:
  - catalog_router with list, detail, install, uninstall endpoints
  - catalog_page.html card grid template
  - catalog_detail.html full detail template
  - unit tests covering all catalog endpoints
key_files:
  - backend/app/browser/catalog.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/catalog_page.html
  - backend/app/templates/browser/catalog_detail.html
  - backend/tests/test_catalog.py
key_decisions:
  - Used _get_apps_dir() helper for test patching instead of injecting path through DI
  - Status detection reads _processes dict directly for running state rather than calling async get_status()
patterns_established:
  - Catalog card grid reuses docs_page.html structural pattern with catalog-specific CSS classes
  - htmx detail navigation uses hx-target="closest .group-editor-area" for in-panel navigation
observability_surfaces:
  - Structured log at WARNING for unparseable manifests (logger: app.browser.catalog)
  - Structured log at INFO for install/uninstall actions with app_id + user email
  - Error rendering via template context variable for install/uninstall failures
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Backend catalog router, templates, and unit tests

**Created catalog_router with 4 endpoints (list/detail/install/uninstall), two Jinja2 templates, and 14 unit tests — all passing.**

## What Happened

Built the complete backend for the app catalog:

1. **`catalog.py`** — Four endpoints on a `catalog_router`: `GET /catalog` scans the apps directory for manifests, excludes `test-app`, merges with installed/running status from `app_manager.registry` and `_processes`, and renders a card grid. `GET /catalog/{app_id}` renders a full detail page with permissions, model deps, tasks, and settings sections. `POST /catalog/{app_id}/install` and `POST /catalog/{app_id}/uninstall` require owner role via `Depends(require_role("owner"))`, call the appropriate app_manager methods, and re-render the detail page with updated status or error messages.

2. **`catalog_page.html`** — Card grid template following the `docs_page.html` pattern. Each card shows app name, truncated description, version badge, and status badge (available/installed/running). Cards use htmx to navigate to the detail view within the same panel.

3. **`catalog_detail.html`** — Full detail template with back navigation, error alert, app header with status badge, sections for author, model dependencies, permissions (SPARQL, network, commands, background tasks, settings), background tasks with intervals, and settings labels. Install/uninstall buttons are owner-only and use htmx POST with confirmation dialog for uninstall.

4. **`router.py`** — Mounted `catalog_router` after `apps_router` but before `objects_router` to avoid catch-all path conflicts.

5. **`test_catalog.py`** — 14 tests across 3 test classes covering list rendering, test-app exclusion, status badges, empty state, detail page content, 404 handling, install/uninstall button visibility, role-based access control (403 for non-owners), app_manager method invocation, and error message rendering.

## Verification

- All 14 unit tests pass: `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v`
- `rg -c "catalog_router" backend/app/browser/router.py` returns 2 (import + include)
- Remaining S05 slice checks (`openCatalogTab`, `workspace-layout.js` routing) are T02 scope — expected to not pass yet.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v` | 0 | ✅ pass | 0.72s |
| 2 | `rg -c "catalog_router" backend/app/browser/router.py` | 0 | ✅ pass (returns 2) | <0.1s |

## Diagnostics

- **Catalog endpoint logs** appear under logger `app.browser.catalog` — grep for `catalog:` prefix
- **Install/uninstall failures** are both logged at ERROR level and rendered in the detail page template via the `error` context variable
- **Manifest parse failures** are logged at WARNING with full traceback (exc_info=True) but silently skipped in the listing — the app just won't appear

## Deviations

None. Implementation matched the task plan.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/catalog.py` — new catalog sub-router with 4 endpoints
- `backend/app/browser/router.py` — added catalog_router import and include (before objects_router)
- `backend/app/templates/browser/catalog_page.html` — new card grid template for catalog listing
- `backend/app/templates/browser/catalog_detail.html` — new detail template with permissions, deps, tasks, settings sections
- `backend/tests/test_catalog.py` — 14 unit tests for catalog endpoints
- `.gsd/milestones/M033/slices/S05/S05-PLAN.md` — added Observability section, marked T01 done
