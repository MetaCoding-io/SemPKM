---
id: T02
parent: S03
milestone: M033
provides:
  - map.js IIFE with window.initMap() — Leaflet + MarkerCluster map renderer
  - Leaflet 1.9.4 and leaflet.markercluster 1.5.3 vendored via build.js with content-hash + manifest
  - Explorer sidebar Map View entry with canvas drag support
  - workspace.js map label registration
  - Dark mode CSS tile inversion and map container layout
  - map.js loaded in base.html
key_files:
  - frontend/static/js/map.js
  - frontend/build.js
  - frontend/package.json
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
  - backend/app/templates/base.html
key_decisions:
  - Used L.divIcon with CSS-styled circles instead of Leaflet default PNG markers to avoid vendored icon path issues
  - Added HTML entity escaping (_escapeHtml, _escapeAttr) for popup content to prevent XSS from object labels
  - ResizeObserver cleanup tracked on container._resizeObserver for proper teardown on re-init
patterns_established:
  - Map JS follows exact calendar.js IIFE pattern — initMap mirrors initCalendar with container cleanup, tryInit polling, and window exposure
  - Leaflet vendoring follows FullCalendar pattern — readFileSync + writeHashed + manifest entry, with CSS concatenation for markercluster
observability_surfaces:
  - console.warn '[map] Container not found' — container DOM missing
  - console.error '[map] Failed to load markers' — data fetch failure
  - console.warn '[map] Tile loading failed' — OSM tile load error (logged once per container)
  - container._mapInstance — direct Leaflet map access from DevTools
  - manifest.json entries for leaflet.js, leaflet.css, leaflet-markercluster.js, leaflet-markercluster.css
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Frontend map.js, Leaflet vendoring, explorer entry, dark mode CSS

**Added map.js IIFE with initMap(), vendored Leaflet+MarkerCluster via build.js, added Map View to explorer sidebar and workspace labels, and added dark mode tile inversion CSS.**

## What Happened

Built the complete frontend rendering layer for the map view, following the calendar.js/FullCalendar pattern:

1. **Package dependencies** — Added `leaflet@1.9.4` and `leaflet.markercluster@^1.5.3` to `frontend/package.json` dependencies.

2. **Build pipeline** — Added 4 new sections to `frontend/build.js` after the FullCalendar section: Leaflet JS, Leaflet CSS, MarkerCluster JS, and MarkerCluster CSS (concatenating `MarkerCluster.css` + `MarkerCluster.Default.css`). All use the standard `writeHashed()` + manifest pattern. Build produces `leaflet-db49d009.min.js`, `leaflet-a7837102.css`, `leaflet-markercluster-1e4e1d22.min.js`, `leaflet-markercluster-72e44762.css`.

3. **map.js IIFE** — Created `frontend/static/js/map.js` with `initMap(containerId, dataUrl, options)`:
   - Creates `L.map` with OSM tile layer (attribution included)
   - Uses `L.divIcon` with CSS-styled circle markers (`.sempkm-map-marker`) to avoid default marker PNG path issues
   - Creates `L.markerClusterGroup`, fetches data endpoint, creates markers with popups
   - Popup includes escaped label, type, and click-to-open via `openTab()`
   - `ResizeObserver` calls `map.invalidateSize()` on container resize for dockview panel handling
   - Tile error handler logs once per container
   - Cleans up existing map and ResizeObserver on re-init

4. **base.html** — Added `<script src="{{ 'map.js' | asset_url }}"></script>` after calendar.js.

5. **Explorer sidebar** — Added Map View entry with globe emoji (🌍), canvas drag support, and `openGenericViewTab('map')`.

6. **Workspace label** — Added `map: 'Map View'` to the labels dict in workspace.js.

7. **CSS** — Added to `views.css`: `.map-container` layout (flex:1, min-height:0), `.sempkm-map-marker` styled circle, dark mode tile inversion (filter:invert(1) hue-rotate(180deg)), dark mode popup background, and Leaflet z-index fixes for dockview stacking context.

## Verification

All 8 task-level checks pass. 9 of 10 slice-level checks pass (test_map.py is T03's responsibility).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'initMap' frontend/static/js/map.js` | 0 | ✅ pass | <1s |
| 2 | `rg 'leaflet' frontend/build.js` | 0 | ✅ pass | <1s |
| 3 | `rg 'leaflet' frontend/dist/manifest.json` | 0 | ✅ pass | <1s |
| 4 | `rg "map.*Map View" backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 5 | `rg "map:" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 6 | `rg "map.js" backend/app/templates/base.html` | 0 | ✅ pass | <1s |
| 7 | `rg "map-container" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 8 | `rg "invalidateSize" frontend/static/js/map.js` | 0 | ✅ pass | <1s |
| 9 | `npm run build` (from frontend/) | 0 | ✅ pass | 1.0s |
| 10 | Slice: `rg '"map"' backend/app/views/registry.py` | 0 | ✅ pass | <1s |
| 11 | Slice: `rg '"map"' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 12 | Slice: `rg 'leaflet.js' frontend/build.js` | 0 | ✅ pass | <1s |
| 13 | Slice: `rg 'schema:latitude' models/basic-pkm/shapes/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 14 | Slice: `rg 'latitude' models/basic-pkm/seed/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 15 | Slice: failure-path logging in service.py | 0 | ✅ pass | <1s |
| 16 | Slice: `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` | — | ⏳ T03 | — |

## Diagnostics

- **Browser console**: `[map] Container not found` (warn), `[map] Failed to load markers` (error), `[map] Tile loading failed` (warn)
- **DevTools inspection**: `document.getElementById('map-container')._mapInstance` for direct Leaflet API access
- **Build verification**: Check `frontend/dist/manifest.json` for 4 leaflet-related entries
- **CDN fallback**: If vendored assets fail to load, map_view.html template falls back to CDN scripts

## Deviations

- Added `_escapeHtml()` and `_escapeAttr()` helper functions for popup content — not in the task plan but necessary for XSS safety when rendering user-controlled object labels
- Added ResizeObserver cleanup tracking on `container._resizeObserver` — plan only mentioned creating the observer, not cleaning up on re-init
- Added dark mode popup styling (`.dark .leaflet-popup-content-wrapper`) — plan mentioned "popup styling overrides if needed" and they are needed for readability

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/map.js` — New IIFE with initMap(), L.divIcon markers, markerCluster, ResizeObserver, popup with openTab()
- `frontend/build.js` — Added Leaflet JS/CSS and MarkerCluster JS/CSS vendoring sections with content-hash + manifest
- `frontend/package.json` — Added leaflet@1.9.4 and leaflet.markercluster@^1.5.3 to dependencies
- `frontend/static/css/views.css` — Added .map-container layout, .sempkm-map-marker styling, dark mode tile inversion, popup dark mode, z-index fixes
- `backend/app/templates/browser/views_explorer.html` — Added Map View entry with globe emoji and canvas drag
- `frontend/static/js/workspace.js` — Added `map: 'Map View'` to labels dict
- `backend/app/templates/base.html` — Added `<script>` tag for map.js after calendar.js
