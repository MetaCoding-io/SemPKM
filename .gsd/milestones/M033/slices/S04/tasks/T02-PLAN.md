---
estimated_steps: 6
estimated_files: 6
skills_used:
  - frontend-design
  - test
---

# T02: Frontend template, CSS, sidebar wiring, and E2E test

**Slice:** S04 — Map View
**Milestone:** M033

## Description

Create the user-facing map view: Jinja2 template with lazy-loaded Leaflet + MarkerCluster, CSS for map container and dark mode, workspace.js label entry, views explorer sidebar link, and an E2E test proving the view opens and shows the correct empty state.

## Steps

1. **Create `backend/app/templates/browser/map_view.html`** following `calendar_view.html` as the reference:
   - Wrap in `.view-flex-column` div
   - Include `browser/type_filter_pills.html` (gated on `is_generic`)
   - Include `browser/view_toolbar.html`
   - Three conditional branches:
     - `error_message` defined → show `<div class="view-empty-state"><p>{{ error_message }}</p></div>`
     - `geo_fields` is falsy → show instructive empty state: "This view displays objects with geographic coordinates on an interactive map. To use Map View, select a type that has latitude/longitude properties (e.g. `wgs84:lat` / `wgs84:long` or `schema:latitude` / `schema:longitude`)."
     - Otherwise → render map container `<div id="map-container" class="map-container" data-testid="map-view"></div>` with inline `<script>`
   - Lazy-load sequence: (a) create `<link>` elements for Leaflet CSS and MarkerCluster CSS, (b) load Leaflet JS (`https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`), (c) on Leaflet load, load MarkerCluster JS (`https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js`), (d) on MarkerCluster load, call `initMap()`
   - `initMap()`: create `L.map('map-container').setView([20, 0], 2)`, add OSM tile layer with attribution, fetch `map_data_url` with credentials, create `L.markerClusterGroup({ chunkedLoading: true })`, iterate markers adding `L.marker([m.lat, m.lng])` with popup showing title, marker click → `openTab(m.iri, m.title)`, add cluster group to map, `fitBounds` if markers exist (with 0.1 padding)
   - Add `ResizeObserver` on map container element calling `map.invalidateSize()` on resize (Leaflet caches container dimensions at init — must be invalidated when dockview panels resize)

2. **Add `.map-container` and dark mode overrides to `frontend/static/css/views.css`** (after the calendar CSS block at end of file):
   - `.map-container`: `flex: 1; min-height: 0; overflow: hidden;` (no padding — Leaflet needs full container)
   - Dark mode tile filter: `[data-theme="dark"] .leaflet-tile-pane { filter: brightness(0.6) invert(1) contrast(3) hue-rotate(200deg) saturate(0.3) brightness(0.7); }`
   - Dark mode container bg: `[data-theme="dark"] .leaflet-container { background: var(--color-bg); }`
   - Dark mode controls: `[data-theme="dark"] .leaflet-control-zoom a`, `[data-theme="dark"] .leaflet-control-attribution` — dark backgrounds, light text, themed borders
   - Dark mode popup: `[data-theme="dark"] .leaflet-popup-content-wrapper, [data-theme="dark"] .leaflet-popup-tip` — dark bg, light text

3. **Add `map: 'Map View'` to the labels dict** in `frontend/static/js/workspace.js` at line ~3478 (inside `openGenericViewTab()`), after `calendar: 'Calendar View'`

4. **Add Map View entry to `backend/app/templates/browser/views_explorer.html`** — insert a new `<a>` element right after the Calendar View entry, mirroring its structure exactly:
   - `class="tree-leaf view-leaf"`, `draggable="true"`
   - `ondragstart` with `window.__canvasDragPayload = {type:'view', id:'generic-map', label:'Map View', url:'/browser/views/generic/map?embed=1'}`
   - `onclick="openGenericViewTab('map'); return false;"`
   - Icon: `&#127758;` (globe emoji) or `&#128205;` (pushpin)
   - Label: `Map View`

5. **Add `map` selector to `e2e/helpers/selectors.ts`** in the `views` section: `map: '[data-testid="map-view"]'`

6. **Write `e2e/tests/02-views/map-view.spec.ts`** E2E test:
   - Import helpers: `SEL` from selectors, `openGenericViewTab` from dockview
   - Test "shows empty state for type without geo properties": navigate to workspace, open map view via `openGenericViewTab(page, 'map', '.view-empty-state')`, assert `.view-empty-state` is visible with text about geographic coordinates
   - Test "map view sidebar entry exists": navigate to workspace, expand VIEWS section, assert Map View link is present

## Must-Haves

- [ ] `map_view.html` renders three empty-state branches correctly
- [ ] Leaflet CSS loads before JS; MarkerCluster JS loads after Leaflet JS
- [ ] Marker click calls `openTab(iri, title)` to open object tab (MAP-02)
- [ ] `ResizeObserver` calls `map.invalidateSize()` on container resize
- [ ] Dark mode tile filter and Leaflet control overrides applied
- [ ] `map: 'Map View'` in workspace.js labels dict
- [ ] Map View entry in views_explorer sidebar with draggable support
- [ ] `data-testid="map-view"` on map container for E2E targeting
- [ ] E2E test verifies empty-state rendering

## Verification

- `cd e2e && npx playwright test tests/02-views/map-view.spec.ts` — E2E tests pass
- `grep -q "map-view" backend/app/templates/browser/map_view.html` — template has testid
- `grep -q "'map'" frontend/static/js/workspace.js` — map label registered

## Inputs

- `backend/app/views/router.py` — T01 added map renderer branch that references `browser/map_view.html` template
- `backend/app/views/service.py` — T01 added `execute_map_query()` that defines the data response shape
- `backend/app/templates/browser/calendar_view.html` — reference template to mirror
- `frontend/static/css/views.css` — existing view styles (calendar block ends at EOF)
- `frontend/static/js/workspace.js` — labels dict at line ~3478
- `backend/app/templates/browser/views_explorer.html` — existing sidebar with calendar entry
- `e2e/helpers/selectors.ts` — existing view selectors
- `e2e/helpers/dockview.ts` — `openGenericViewTab` helper

## Expected Output

- `backend/app/templates/browser/map_view.html` — new Jinja2 template with Leaflet map
- `frontend/static/css/views.css` — modified with map-container and dark mode Leaflet overrides
- `frontend/static/js/workspace.js` — modified with map label
- `backend/app/templates/browser/views_explorer.html` — modified with Map View sidebar entry
- `e2e/helpers/selectors.ts` — modified with map selector
- `e2e/tests/02-views/map-view.spec.ts` — new E2E test file
