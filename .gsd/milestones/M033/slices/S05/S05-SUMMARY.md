---
slice: S05
milestone: M033
title: "App Catalog Pages"
status: done
started: 2026-03-21
completed: 2026-03-21
tasks_completed: 2
tasks_total: 2
verification: passed
---

# S05 Summary: App Catalog Pages

## What Was Delivered

A browsable app catalog accessible from the workspace sidebar. Users click "App Catalog" in the APPS explorer section to open a dockview tab showing a card grid of all available apps (excluding test-app). Each card links to a detail page with full manifest info and install/uninstall actions for owners.

### Backend (T01)

- **`catalog.py`** — New sub-router with 4 endpoints:
  - `GET /catalog` — scans `apps/` directory for manifests, merges with runtime status from `app_manager.registry` and `_processes`, renders card grid
  - `GET /catalog/{app_id}` — renders detail page with permissions, model dependencies, tasks, settings
  - `POST /catalog/{app_id}/install` — owner-only, calls `app_manager.install()`, re-renders detail with updated status
  - `POST /catalog/{app_id}/uninstall` — owner-only, calls `app_manager.uninstall()`, re-renders detail with updated status
- **`catalog_page.html`** — Card grid template following `docs_page.html` pattern. Status badges (available/installed/running/stopped).
- **`catalog_detail.html`** — Full detail template with back navigation, error alert, structured sections for permissions/deps/tasks/settings.
- **Router mount** — `catalog_router` included in `browser/router.py` after `apps_router` but before `objects_router` (catch-all avoidance).
- **14 unit tests** — Cover list rendering, test-app exclusion, status badges, empty state, detail content, 404, install/uninstall button visibility, owner role enforcement (403), app_manager invocation, error message rendering.

### Frontend (T02)

- **`openCatalogTab()`** — JS function in `workspace.js` following `openDocsTab()` pattern. Creates `special:catalog` dockview panel, reuses existing tab if open. Exposed on `window.openCatalogTab`.
- **Explorer entry** — Static "App Catalog" tree-leaf in APPS explorer section with Lucide `layout-grid` icon. Persists across htmx reloads via sibling placement outside the htmx target div.
- **CSS** — ~300 lines of `.catalog-*` rules: responsive card grid (3→2→1 columns), card hover effects, status badges (color-coded), detail page layout, error alert, permission/dep/task lists, tag pills.
- **`workspace-layout.js`** — `specialType: 'catalog'` routes to `/browser/catalog` via default URL logic (no code change needed, documented via comment).

## Key Patterns

1. **Static entries alongside htmx content**: The "App Catalog" link is a static DOM element that must survive `hx-swap="innerHTML"` on the APPS section. Solution: move `hx-get` to a sub-div (`#apps-tree-dynamic`) so the static entry is a sibling, not a child, of the swap target. (Recorded as Knowledge Pattern 7.)

2. **Catalog follows docs_page.html card grid pattern**: Same structural approach as the docs viewer — card grid in a scrollable container, htmx navigation within the panel.

3. **Status detection without async calls**: Runtime status reads `app_manager.registry` (installed?) and `_processes` dict (running?) directly instead of calling the async `get_status()` method, keeping the template render synchronous.

## Observability

- **Manifest parse failures** — logged at WARNING with `exc_info=True` (logger: `app.browser.catalog`). App silently excluded from listing.
- **Install/uninstall** — logged at INFO (success) or ERROR (failure) with `app_id` + `user.email`. No secrets logged.
- **Error rendering** — failures surface in the detail template via `error` context variable (red alert box visible to user).

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_catalog.py -v` — 14 tests | ✅ 14/14 pass |
| 2 | `rg -c "catalog_router" backend/app/browser/router.py` = 2 | ✅ 2 |
| 3 | `rg -c "openCatalogTab" frontend/static/js/workspace.js` >= 2 | ✅ 2 |
| 4 | `rg -c "catalog" frontend/static/js/workspace-layout.js` >= 1 | ✅ 1 |

## Files Created/Modified

**Created:**
- `backend/app/browser/catalog.py`
- `backend/app/templates/browser/catalog_page.html`
- `backend/app/templates/browser/catalog_detail.html`
- `backend/tests/test_catalog.py`

**Modified:**
- `backend/app/browser/router.py` — catalog_router import + include
- `frontend/static/js/workspace.js` — `openCatalogTab()` + window exposure
- `frontend/static/js/workspace-layout.js` — comment documenting catalog specialType
- `backend/app/templates/browser/workspace.html` — "App Catalog" explorer entry + htmx restructure
- `frontend/static/css/workspace.css` — ~300 lines of `.catalog-*` CSS

## What Next Slices Should Know

- The catalog router is at `/browser/catalog` — any future app-related UI should be aware it exists alongside `apps_router` at `/browser/apps`.
- Install/uninstall endpoints require owner role — non-owners see the catalog but can't modify app state.
- The card grid template can be extended with screenshots (currently not pre-captured) and more manifest fields as needed.
- The `#apps-tree-dynamic` sub-div pattern means future htmx-loaded explorer content in the APPS section targets that div, not `#apps-tree` directly.
