---
id: T02
parent: S06
milestone: M033
provides:
  - Workspace catalog list route and grid template at /browser/apps/catalog
  - Workspace catalog detail route and template at /browser/apps/catalog/{app_id}
  - openCatalogTab() and openCatalogDetailTab() JS functions on window
  - Browse Catalog sidebar entry in APPS explorer section
  - Catalog CSS styles (grid, cards, detail, feature list, permissions, category pills)
key_files:
  - backend/app/browser/apps.py
  - backend/app/templates/browser/catalog_list.html
  - backend/app/templates/browser/catalog_detail.html
  - backend/app/templates/browser/apps_explorer.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/style.css
key_decisions: []
patterns_established:
  - "Catalog routes use Depends(get_current_user) — no role restriction for read-only browsing; template conditionally renders actions for owner role"
  - "workspace-layout.js special panel routing: 'catalog' → /browser/apps/catalog, 'catalog-detail' → /browser/apps/catalog/{appId}"
observability_surfaces:
  - "logger.warning on 404 for unknown app_id in catalog_detail"
  - "logger.warning on manifest parse failures for available (not-installed) apps"
  - "window.openCatalogTab / window.openCatalogDetailTab available in browser console"
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Workspace catalog routes, templates, sidebar entry, and CSS

**Added workspace catalog browsing with grid list, detail pages, sidebar entry, and catalog CSS — all 8 slice verification checks pass**

## What Happened

Added two new routes to the browser apps router: `GET /apps/catalog` (grid list of all apps) and `GET /apps/catalog/{app_id}` (detail page). Both accept any authenticated user — no role restriction for browsing. The catalog list collects installed apps from the registry and available (not-installed) apps by scanning `_apps_dir`, identical to the admin list pattern.

Created `catalog_list.html` as a standalone HTML fragment for dockview panels, with a searchable card grid. Each card shows name, version pill, status dot (running/stopped/available), category pill, truncated description, and author. Client-side search filters by name and description using a simple `oninput` handler.

Created `catalog_detail.html` with the full app detail: header with badges, description, author link, features checklist with Lucide check icons, permissions table, model dependencies table, and conditional actions section (install/uninstall/start/stop/restart) rendered only for `user.role == 'owner'`. Includes a "Back to Catalog" link.

Added `openCatalogTab()` and `openCatalogDetailTab(appId, appName)` to workspace.js following the existing `openAppPageTab` pattern. Added corresponding `specialType` routing in `workspace-layout.js` to map `catalog` → `/browser/apps/catalog` and `catalog-detail` → `/browser/apps/catalog/{appId}`.

Added a "Browse Catalog" tree-leaf entry to `apps_explorer.html` with `layout-grid` icon, always visible at the bottom of the APPS section.

Added catalog-specific CSS to style.css: `.catalog-grid` (auto-fill grid), `.catalog-card` (hover elevation), `.catalog-card-desc` (2-line clamp), `.catalog-search`, `.category-pill`, `.feature-list` (checkmark list), `.permission-badge`, `.catalog-detail` (max-width container), `.catalog-actions`, `.status-dot` indicators, and `.catalog-back-link`.

## Verification

All 8 slice-level verification checks pass. Route registration confirmed via Python import — both `/apps/catalog` and `/apps/catalog/{app_id}` are present on `apps_router`. No route ordering conflicts since parametric routes have more path segments.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q 'openCatalogTab' frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q 'openCatalogDetailTab' frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 3 | `test -f backend/app/templates/browser/catalog_list.html` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/app/templates/browser/catalog_detail.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'Browse Catalog' backend/app/templates/browser/apps_explorer.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'catalog-grid' frontend/static/css/style.css` | 0 | ✅ pass | <1s |
| 7 | `grep -q '/apps/catalog' backend/app/browser/apps.py` | 0 | ✅ pass | <1s |
| 8 | `python -c "...assert '/apps/catalog' in routes; assert '/apps/catalog/{app_id}' in routes"` | 0 | ✅ pass | 4s |

### Slice-level checks (all tasks):

| # | Check | Verdict |
|---|-------|---------|
| 1 | Schema defaults work | ✅ pass |
| 2 | Extended fields parse | ✅ pass |
| 3 | `openCatalogTab` in workspace.js | ✅ pass |
| 4 | Catalog routes in apps.py | ✅ pass |
| 5 | catalog_list.html exists | ✅ pass |
| 6 | catalog_detail.html exists | ✅ pass |
| 7 | Operations in admin detail | ✅ pass |
| 8 | Browse Catalog in explorer | ✅ pass |

## Diagnostics

- Catalog list: `curl http://localhost:3901/browser/apps/catalog` (requires auth cookie)
- Catalog detail: `curl http://localhost:3901/browser/apps/catalog/{app_id}`
- JS console: `window.openCatalogTab()` opens catalog list tab; `window.openCatalogDetailTab('rss-reader', 'RSS Reader')` opens detail tab
- Route list: `cd backend && .venv/bin/python -c "from app.browser.apps import apps_router; print([r.path for r in apps_router.routes])"`

## Deviations

- Added `workspace-layout.js` routing for `catalog` and `catalog-detail` special types — the task plan mentioned workspace.js but the actual URL mapping happens in workspace-layout.js's special panel init function. This is how all existing special panels work.
- Used `Depends(get_current_user)` import pattern from the existing browser routers rather than `request.state.user` — consistent with the codebase convention.
- Added `_format_uptime` helper to the browser apps router (duplicated from admin_router) to format uptime for catalog display.
- The `author` field in catalog list uses a Jinja2 `is mapping` test to handle both `AppAuthor` objects (installed apps) and raw dict/string values (available apps parsed from YAML).

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — Added catalog_list and catalog_detail routes, _format_uptime helper, yaml/auth imports
- `backend/app/templates/browser/catalog_list.html` — New: searchable card grid template for all apps
- `backend/app/templates/browser/catalog_detail.html` — New: full detail page with features, permissions, conditional actions
- `backend/app/templates/browser/apps_explorer.html` — Added "Browse Catalog" tree-leaf entry
- `frontend/static/js/workspace.js` — Added openCatalogTab() and openCatalogDetailTab() functions
- `frontend/static/js/workspace-layout.js` — Added special panel routing for catalog and catalog-detail types
- `frontend/static/css/style.css` — Added catalog CSS (~220 lines): grid, cards, detail, feature list, permissions, pills
- `.gsd/milestones/M033/slices/S06/tasks/T02-PLAN.md` — Added Observability Impact section
