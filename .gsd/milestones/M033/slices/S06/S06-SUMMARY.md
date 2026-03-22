---
id: S06
parent: M033
milestone: M033
provides:
  - AppManifestSchema extended with category, features, readme fields (backward-compatible)
  - Admin detail page redesigned catalog-first with collapsible Operations section
  - Admin list page with category badges
  - Workspace catalog list route (GET /browser/apps/catalog) with searchable card grid
  - Workspace catalog detail route (GET /browser/apps/catalog/{app_id}) with features, permissions, actions
  - openCatalogTab() and openCatalogDetailTab() JS functions
  - Browse Catalog sidebar entry in APPS explorer
  - Catalog-specific CSS (grid, cards, feature list, pills, permissions, detail layout)
requires: []
affects: []
key_files:
  - backend/app/apps/manifest.py
  - backend/app/browser/apps.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/templates/admin/apps/list.html
  - backend/app/templates/browser/catalog_list.html
  - backend/app/templates/browser/catalog_detail.html
  - backend/app/templates/browser/apps_explorer.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/style.css
key_decisions: []
patterns_established:
  - "color-mix(in srgb, var(--color-primary) 15%, transparent) for category pill background"
  - "Catalog routes use Depends(get_current_user) — no role restriction for browsing; template conditionally renders actions for owner role"
  - "workspace-layout.js special panel routing: 'catalog' → /browser/apps/catalog, 'catalog-detail' → /browser/apps/catalog/{appId}"
observability_surfaces:
  - "logger.warning on 404 for unknown app_id in catalog_detail"
  - "logger.warning on manifest parse failures for available apps"
  - "Pydantic ValidationError on invalid category/features/readme at manifest parse time"
  - "window.openCatalogTab / window.openCatalogDetailTab available in browser console"
drill_down_paths:
  - .gsd/milestones/M033/slices/S06/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S06/tasks/T02-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-22
---

# S06: App Catalog Pages

**Extended manifest schema with catalog metadata and built browsable app catalog for both admin portal and workspace sidebar — all 8 verification checks pass**

## What Happened

T01 extended `AppManifestSchema` with three optional fields: `category` (str), `features` (list[str]), and `readme` (str) — all defaulting to empty for backward compatibility. Redesigned the admin detail page to lead with a catalog showcase (description, features checklist, permissions table, dependencies) with operational sections (status, logs, actions, task history) collapsed inside a `<details>` element. Added category badges to the admin list page.

T02 added workspace-side catalog browsing. Two new routes on the browser apps router: `/apps/catalog` returns a searchable card grid of all apps (installed from registry + available from disk), and `/apps/catalog/{app_id}` returns a full detail page. Both accept any authenticated user. Install/uninstall/start/stop/restart actions are conditionally rendered for owner role only. Added `openCatalogTab()` and `openCatalogDetailTab()` to workspace.js, with corresponding special panel routing in workspace-layout.js. Added a "Browse Catalog" entry with `layout-grid` icon to the APPS explorer sidebar. Added ~220 lines of catalog CSS.

## Verification

All 8 slice verification checks pass:
1. Schema defaults work (`category == ''`, `features == []`, `readme == ''`)
2. Extended fields parse correctly (`category='sync'` validates)
3. `openCatalogTab` exists in workspace.js
4. Catalog routes exist in apps.py
5. `catalog_list.html` template exists
6. `catalog_detail.html` template exists
7. Admin detail has `Operations` collapsed section
8. `Browse Catalog` appears in apps_explorer.html

Route registration confirmed: both `/apps/catalog` and `/apps/catalog/{app_id}` present on `apps_router`. Clean Python import — no circular dependencies.

## Deviations

- T01 used `appId='test'` instead of `appId='t'` in verification commands — the plan's `'t'` violates the 2-char minimum constraint.
- T02 added workspace-layout.js routing (not mentioned in plan) — necessary because all special panel URL mapping happens there, not in workspace.js.
- T02 duplicated `_format_uptime` helper in the browser apps router from admin_router — small DRY violation, but avoids coupling browser and admin routers.

## Known Limitations

- Catalog detail actions (install/uninstall/start/stop) POST to `/admin/apps/...` which requires the `owner` role dependency — non-owner users won't see the buttons (correct), but if somehow triggered, the admin endpoint's `require_role("owner")` will reject the request.
- No real-time status updates in the catalog — status is snapshot at page load.
- The `readme` field is accepted in the schema but not yet rendered anywhere (could be used for a full README tab in future).

## Follow-ups

None.

## Files Created/Modified

- `backend/app/apps/manifest.py` — Added `category`, `features`, `readme` fields to `AppManifestSchema`
- `backend/app/apps/admin_router.py` — Added `category` to app dict in list builder
- `backend/app/browser/apps.py` — Added catalog_list and catalog_detail routes, imports, _format_uptime
- `backend/app/templates/admin/apps/detail.html` — Redesigned: catalog showcase at top, ops in `<details>`
- `backend/app/templates/admin/apps/list.html` — Added category badge pill on app cards
- `backend/app/templates/browser/catalog_list.html` — New: searchable card grid template
- `backend/app/templates/browser/catalog_detail.html` — New: full detail page with conditional actions
- `backend/app/templates/browser/apps_explorer.html` — Added "Browse Catalog" tree-leaf entry
- `frontend/static/js/workspace.js` — Added openCatalogTab() and openCatalogDetailTab()
- `frontend/static/js/workspace-layout.js` — Added catalog/catalog-detail special panel routing
- `frontend/static/css/style.css` — Added ~220 lines of catalog CSS

## Forward Intelligence

### What the next slice should know
- The catalog routes use the same pattern as the admin list for discovering available apps — scanning `app_manager._apps_dir` for directories with `manifest.yaml`. If the apps directory structure changes, both admin and catalog need updating.
- `openCatalogDetailTab(appId, appName)` takes an optional second arg for the tab title — callers from the grid pass the app name for a clean tab label.

### What's fragile
- The `_format_uptime` helper is duplicated between `admin_router.py` and `browser/apps.py` — if the format changes, both need updating. Could be extracted to a shared utility.

### Authoritative diagnostics
- Route list: `cd backend && .venv/bin/python -c "from app.browser.apps import apps_router; print([r.path for r in apps_router.routes])"` — confirms all 7 routes registered
- JS functions: `window.openCatalogTab` and `window.openCatalogDetailTab` in browser console

### What assumptions changed
- None — the plan was accurate. The only addition was workspace-layout.js routing which is an implementation detail the planner didn't need to specify.
