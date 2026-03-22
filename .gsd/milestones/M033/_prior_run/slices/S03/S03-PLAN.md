# S03: Map View Renderer

**Goal:** Register a Leaflet-based map renderer that displays objects with geographic coordinates as clustered markers on an OpenStreetMap basemap, following the S02 calendar renderer pattern.
**Demo:** User opens "Map" from VIEWS explorer, sees bpkm:Event objects with lat/lng as markers on OpenStreetMap. Clicking a marker shows a popup with object info and "Open" link. Marker clustering handles dense data. Dark mode inverts tiles.

## Must-Haves

- `"map"` registered in `RENDERER_REGISTRY` and `_VALID_RENDERERS`
- `_detect_geo_fields()` discovers `schema:latitude`/`schema:longitude` from SHACL shapes
- `_build_map_select()` generates SPARQL for geo-located objects
- `execute_map_query()` returns `[{id, label, lat, lng, type}]` JSON
- `generic_view()` and `generic_graph_data()` have `elif renderer == "map"` branches
- `map_view.html` template with type filter pills, view toolbar, graceful empty state
- `map.js` IIFE with `initMap()` — Leaflet + markercluster + popup + click-to-open
- Leaflet 1.9.4 and Leaflet.markercluster vendored via `build.js` with CDN fallback
- Explorer sidebar "Map View" entry with canvas drag support
- `workspace.js` labels dict includes `map: 'Map View'`
- `schema:latitude` and `schema:longitude` added to EventShape in basic-pkm model
- Seed events have geographic coordinates for demoability
- Dark mode CSS filter on tile pane
- `ResizeObserver` on container calling `map.invalidateSize()` for dockview panel resize
- Unit tests for `_detect_geo_fields`, `_build_map_select`, `execute_map_query`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all tests pass
- `rg '"map"' backend/app/views/registry.py` — map in RENDERER_REGISTRY
- `rg '"map"' backend/app/views/router.py` — map in _VALID_RENDERERS
- `rg 'leaflet.js' frontend/build.js` — Leaflet vendored
- `rg 'initMap' frontend/static/js/map.js` — JS init function exists
- `rg 'schema:latitude' models/basic-pkm/shapes/basic-pkm.jsonld` — geo properties in shape
- `rg 'latitude' models/basic-pkm/seed/basic-pkm.jsonld` — seed data has coordinates
- `rg "map.*Map View" backend/app/templates/browser/views_explorer.html` — explorer entry
- `rg "map:" frontend/static/js/workspace.js` — label registered
- `rg 'execute_map_query.*missing\|execute_map_query.*failed\|_detect_geo_fields.*failed' backend/app/views/service.py` — failure-path logging present

## Observability / Diagnostics

- Runtime signals: `execute_map_query` INFO log with type, lat/lng paths, scope, marker count; `_detect_geo_fields` WARNING on shapes lookup failure
- Inspection surfaces: `GET /browser/views/generic/map/data?type=<iri>` JSON endpoint for debugging
- Failure visibility: `console.warn '[map] Container not found'`, `console.error '[map] Failed to load markers'`, `console.warn '[map] Tile loading failed'` in browser
- Redaction constraints: none

## Tasks

- [x] **T01: Backend map renderer — registry, geo detection, SPARQL query, data endpoint** `est:45m`
  - Why: The core backend for map rendering — field detection, query building, data serialization, and router wiring. Without this, the frontend has nothing to render.
  - Files: `backend/app/views/registry.py`, `backend/app/views/router.py`, `backend/app/views/service.py`, `backend/app/templates/browser/map_view.html`, `models/basic-pkm/shapes/basic-pkm.jsonld`, `models/basic-pkm/seed/basic-pkm.jsonld`
  - Do: (1) Add `"map"` entry to `RENDERER_REGISTRY` following calendar pattern. (2) Add `"map"` to `_VALID_RENDERERS` set. (3) Add `_GEO_LAT_PATHS`, `_GEO_LNG_PATHS` constants and `_detect_geo_fields()` method to `ViewSpecService` following `_detect_date_fields()` pattern. (4) Add `_build_map_select()` static method and `execute_map_query()` async method. (5) Add `elif renderer == "map"` branches in both `generic_view()` and `generic_graph_data()`. (6) Create `map_view.html` template with `.view-flex-column` wrapper, type pills, toolbar, geo-missing empty state, and map container div. Template loads Leaflet CSS+JS with CDN fallback. (7) Add `schema:latitude` (xsd:decimal) and `schema:longitude` (xsd:decimal) to EventShape in shapes JSON-LD. (8) Add lat/lng values to 2+ existing seed events and 2-3 new seed events with diverse global locations. (9) Update error message in router for invalid renderer to include "map".
  - Verify: `rg '"map"' backend/app/views/registry.py backend/app/views/router.py` shows map entries. `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); print([x for x in str(d) if 'latitude' in str(d)][:1])"` confirms shape has latitude.
  - Done when: Map renderer is registered, backend can detect geo fields, build SPARQL, execute query, and serve template with data URL.

- [x] **T02: Frontend map.js, Leaflet vendoring, explorer entry, dark mode CSS** `est:40m`
  - Why: The user-facing rendering layer — without map.js and vendored Leaflet, the template has no way to display markers.
  - Files: `frontend/static/js/map.js`, `frontend/build.js`, `frontend/static/css/views.css`, `backend/app/templates/browser/views_explorer.html`, `frontend/static/js/workspace.js`, `backend/app/templates/base.html`, `frontend/package.json`
  - Do: (1) Add `leaflet` and `leaflet.markercluster` to `package.json` devDependencies. (2) Add Leaflet JS, CSS, and markercluster JS+CSS build sections to `build.js` following the FullCalendar pattern (content-hash, manifest entries). (3) Create `map.js` IIFE with `initMap(containerId, dataUrl, options)` — init L.map, add OSM tile layer, create L.markerClusterGroup, fetch data URL, create markers with popups, fitBounds, handle tile errors. Use `ResizeObserver` on container to call `map.invalidateSize()`. Click-to-open via `openTab()`. (4) Add `<script>` tag for `map.js` in `base.html` after calendar.js. (5) Add Map View entry to `views_explorer.html` with globe emoji (🌍), canvas drag support, and `openGenericViewTab('map')`. (6) Add `map: 'Map View'` to labels dict in `workspace.js`. (7) Add dark mode CSS for map: `.dark .map-container .leaflet-tile-pane { filter: invert(1) hue-rotate(180deg) }` plus `.map-container` sizing in `views.css`. (8) Fix Leaflet default marker icon path issue with `L.Icon.Default.imagePath` or use `L.divIcon` with CSS-styled markers.
  - Verify: `rg 'initMap' frontend/static/js/map.js` and `rg 'leaflet' frontend/build.js` and `rg "map:" frontend/static/js/workspace.js` all return matches.
  - Done when: `npm run build` succeeds, Leaflet vendored with content-hash, map.js exposes `initMap`, explorer shows Map View entry, dark mode tiles invert.

- [x] **T03: Unit tests for map geo detection, query building, and data transformation** `est:30m`
  - Why: Test coverage matching S02's 24-test standard. Verifies geo detection, SPARQL construction, and JSON response format independently of a running triplestore.
  - Files: `backend/tests/test_map.py`
  - Do: Create `test_map.py` following `test_calendar.py` structure with three test classes: (1) `TestDetectGeoFields` — tests for exact path match (schema:latitude/longitude), http/https variants, fallback by path name fragments, missing shapes, error handling, non-geo types returning None. (2) `TestBuildMapSelect` — tests for query with type+lat+lng, with scope filter, without type, label/type OPTIONAL clauses. (3) `TestExecuteMapQuery` — tests for JSON format `{id, label, lat, lng, type}`, deduplication by IRI, missing label fallback to IRI, error handling, empty results.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all tests pass
  - Done when: 15+ tests pass covering all three geo-detection stages, query variants, and response transformation.

## Files Likely Touched

- `backend/app/views/registry.py`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/templates/browser/map_view.html`
- `backend/app/templates/browser/views_explorer.html`
- `backend/app/templates/base.html`
- `frontend/static/js/map.js`
- `frontend/static/js/workspace.js`
- `frontend/static/css/views.css`
- `frontend/build.js`
- `frontend/package.json`
- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `models/basic-pkm/seed/basic-pkm.jsonld`
- `backend/tests/test_map.py`
