---
id: T02
parent: S04
milestone: M033
provides:
  - Map view Jinja2 template with lazy-loaded Leaflet + MarkerCluster
  - Map view CSS with dark mode tile filter and Leaflet control overrides
  - Map View sidebar entry in views explorer with drag-drop support
  - Map View label in workspace.js openGenericViewTab labels dict
  - E2E tests for empty state and sidebar entry (Chromium + Firefox)
key_files:
  - backend/app/templates/browser/map_view.html
  - frontend/static/css/views.css
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/views_explorer.html
  - e2e/tests/02-views/map-view.spec.ts
key_decisions:
  - Lazy-load chain with idempotency guards (check typeof L and L.markerClusterGroup before loading) so opening a second map tab reuses already-loaded libraries
  - Globe emoji (🌎 &#127758;) for sidebar icon — consistent with geographic theme
patterns_established:
  - Map view mirrors calendar view pattern exactly — same lazy-load → init → fetch → render flow
  - Sidebar test must expand VIEWS section before asserting entry visibility (sections start collapsed)
observability_surfaces:
  - "[map]" console prefix on data fetch failures and library load failures
  - Three distinct .view-empty-state messages for no-type / no-geo-fields / error conditions
  - ResizeObserver on map container calls map.invalidateSize() for dockview panel resize
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Frontend template, CSS, sidebar wiring, and E2E test

**Created map view template with lazy-loaded Leaflet/MarkerCluster, dark mode CSS, sidebar entry, and E2E tests for empty state and sidebar visibility**

## What Happened

Implemented the complete frontend for the map view, following the calendar view pattern:

1. **`map_view.html`** — Jinja2 template with `.view-flex-column` wrapper, type filter pills, view toolbar, three conditional branches (error message, no geo fields instructive text, map container). The map branch lazy-loads Leaflet CSS, then Leaflet JS, then MarkerCluster JS in sequence, with idempotency guards to skip already-loaded libraries. `initMap()` creates the map, adds OSM tiles, fetches marker data from `map_data_url`, creates a MarkerCluster group, adds markers with popups and click handlers calling `openTab()`, and fits bounds when markers exist. ResizeObserver invalidates Leaflet's cached dimensions on panel resize.

2. **`views.css`** — Added `.map-container` (flex:1, min-height:0, overflow:hidden) and dark mode overrides for tiles (brightness/invert/contrast filter), container background, zoom controls, attribution, and popups.

3. **`workspace.js`** — Added `map: 'Map View'` to the labels dict in `openGenericViewTab()`.

4. **`views_explorer.html`** — Added Map View sidebar entry after Calendar View with draggable support, ondragstart canvas payload, onclick handler, and globe emoji icon.

5. **`selectors.ts`** — Added `map: '[data-testid="map-view"]'` to `SEL.views`.

6. **`dockview.ts`** — Added `'map'` to the renderer type union in `openGenericViewTab()`.

7. **`map-view.spec.ts`** — Two E2E tests: empty state verification (opens map view, asserts `.view-empty-state` with geo-related text) and sidebar entry verification (expands VIEWS section, asserts Map View link is visible).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — 23/23 passed
- `cd e2e && TEST_BASE_URL=http://localhost:3000 npx playwright test tests/02-views/map-view.spec.ts` — 4/4 passed (Chromium + Firefox)
- `grep -q "map-view" backend/app/templates/browser/map_view.html` — confirmed
- `grep -q "map: 'Map View'" frontend/static/js/workspace.js` — confirmed
- `grep -c 'execute_map_query: query failed' backend/app/views/service.py` — returns 1 (diagnostic path exists)
- Browser verification: Map View entry visible in sidebar, empty state renders "Select a type to use Map View" when no type selected

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` | 0 | ✅ pass | 3.8s |
| 2 | `cd e2e && TEST_BASE_URL=http://localhost:3000 npx playwright test tests/02-views/map-view.spec.ts` | 0 | ✅ pass | 9.0s |
| 3 | `grep -q "map-view" backend/app/templates/browser/map_view.html` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "map: 'Map View'" frontend/static/js/workspace.js` | 0 | ✅ pass | <0.1s |
| 5 | `grep -c 'execute_map_query: query failed' backend/app/views/service.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Console errors:** Grep browser console for `[map]` to find CDN load failures or data fetch errors.
- **Empty states:** Three distinct `.view-empty-state` messages visible in the DOM — inspect text content to determine which branch rendered (no type, no geo fields, or custom error message).
- **Leaflet loaded:** Check `typeof L !== 'undefined'` in browser console to verify Leaflet loaded. Check `L.markerClusterGroup` to verify MarkerCluster loaded.
- **ResizeObserver:** Automatic — map.invalidateSize() fires on container resize. No manual intervention needed.

## Deviations

- E2E sidebar test initially failed because VIEWS section starts collapsed. Added section expansion (click `.explorer-section-header`) before asserting visibility — consistent with the project knowledge entry "Workspace explorer sections start collapsed".
- E2E run uses `TEST_BASE_URL=http://localhost:3000` (dev stack) since no test stack on port 3901 is running.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/map_view.html` — New Jinja2 template with Leaflet map, MarkerCluster, three empty-state branches
- `frontend/static/css/views.css` — Added `.map-container` and dark mode Leaflet overrides (tiles, controls, popups)
- `frontend/static/js/workspace.js` — Added `map: 'Map View'` to labels dict
- `backend/app/templates/browser/views_explorer.html` — Added Map View sidebar entry with drag-drop support
- `e2e/helpers/selectors.ts` — Added `map: '[data-testid="map-view"]'` to `SEL.views`
- `e2e/helpers/dockview.ts` — Added `'map'` to `openGenericViewTab()` renderer type union
- `e2e/tests/02-views/map-view.spec.ts` — New E2E test file with empty-state and sidebar tests
