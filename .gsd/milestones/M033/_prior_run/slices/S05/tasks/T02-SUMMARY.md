---
id: T02
parent: S05
milestone: M033
provides:
  - openCatalogTab() JS function exposed on window for dockview tab creation
  - "App Catalog" entry in APPS explorer sidebar (persists across htmx reloads)
  - Full CSS styling for catalog card grid, detail page, status badges, and responsive layout
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/app/templates/browser/workspace.html
  - frontend/static/css/workspace.css
key_decisions:
  - Moved htmx hx-get to a sub-div (apps-tree-dynamic) so the static catalog entry survives htmx innerHTML swaps
patterns_established:
  - Static explorer entries placed as siblings above htmx-loaded containers to survive swap cycles
observability_surfaces:
  - Tab creation uses standard dockview special-panel lifecycle — no additional JS logging
  - CSS classes match T01 template classes exactly, so styling failures indicate CSS load issues
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Frontend integration — JS, CSS, explorer entry

**Added openCatalogTab() function, "App Catalog" sidebar entry, and full responsive CSS for catalog card grid and detail pages.**

## What Happened

1. **`workspace.js`** — Added `openCatalogTab()` following the exact `openDocsTab()`/`openCanvasTab()` pattern. Creates a `special:catalog` dockview panel with `specialType: 'catalog'`, reuses existing tab if already open. Exposed on `window.openCatalogTab`.

2. **`workspace-layout.js`** — Added a comment documenting that `specialType: 'catalog'` routes to `/browser/catalog` via the default `url = '/browser/' + st` logic. No code change needed since the default routing works.

3. **`workspace.html`** — Added a static `tree-leaf catalog-entry` div with a Lucide `layout-grid` icon inside the APPS explorer section. Restructured the htmx loading: moved `hx-get="/browser/apps/explorer"` from `#apps-tree` to a new `#apps-tree-dynamic` sub-div so the catalog entry persists when htmx replaces the dynamic app list content.

4. **`workspace.css`** — Added ~300 lines of `.catalog-*` CSS rules covering: page container with overflow-y auto, responsive card grid (3→2→1 columns via media queries), card hover effects, icon containers with `flex-shrink: 0` and `stroke: currentColor` per CLAUDE.md, status badges (green/running, blue/installed, amber/stopped, gray/available), empty state, detail page layout with header/sections/action buttons, error alert box, back navigation, permission/dependency/task lists, and tag pills.

## Verification

All four slice-level checks pass:
- 14/14 unit tests pass in `test_catalog.py`
- `catalog_router` count in `router.py` = 2
- `openCatalogTab` count in `workspace.js` = 2
- `catalog` count in `workspace-layout.js` = 1

Task-level checks:
- `rg -c "openCatalogTab" workspace.js` → 2 (function def + window exposure)
- `rg "App Catalog" workspace.html` → 1 match
- `rg -c ".catalog-card" workspace.css` → 12

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v` | 0 | ✅ pass | 0.71s |
| 2 | `rg -c "catalog_router" backend/app/browser/router.py` | 0 | ✅ pass (returns 2) | <0.1s |
| 3 | `rg -c "openCatalogTab" frontend/static/js/workspace.js` | 0 | ✅ pass (returns 2) | <0.1s |
| 4 | `rg -c "catalog" frontend/static/js/workspace-layout.js` | 0 | ✅ pass (returns 1) | <0.1s |

## Diagnostics

- **Tab creation**: If clicking "App Catalog" in the sidebar doesn't open a tab, check that `window.openCatalogTab` is defined in the browser console. If undefined, `workspace.js` isn't loaded or has a syntax error.
- **Catalog entry visibility**: The entry is a static DOM element in `workspace.html`. If it's missing, either the template wasn't reloaded or the APPS section isn't expanded (click the header to toggle).
- **Unstyled cards**: If catalog pages render without styling, check that `workspace.css` is loaded (network tab → 200 on the CSS file, no caching issues).
- **htmx routing**: The special-panel init computes `url = '/browser/catalog'` from `specialType: 'catalog'`. If the tab shows empty content, check that the catalog router is mounted at `/browser/catalog` in `router.py`.

## Deviations

- **htmx target restructuring**: The plan suggested placing the catalog entry inside the `#apps-tree` div alongside htmx content, but `hx-swap="innerHTML"` would destroy it on every htmx response. Moved htmx loading to a new `#apps-tree-dynamic` sub-div so the catalog entry persists as a sibling. No external code targets `#apps-tree` by ID, so this is safe.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — added `openCatalogTab()` function and `window.openCatalogTab` exposure
- `frontend/static/js/workspace-layout.js` — added comment documenting catalog specialType routing
- `backend/app/templates/browser/workspace.html` — added "App Catalog" tree-leaf entry, restructured APPS section htmx to preserve static entry
- `frontend/static/css/workspace.css` — added ~300 lines of `.catalog-*` CSS rules for card grid, detail page, status badges, responsive breakpoints
- `.gsd/milestones/M033/slices/S05/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight
