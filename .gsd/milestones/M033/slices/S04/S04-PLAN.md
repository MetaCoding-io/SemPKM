# S04: Map View

**Goal:** Users can open a Map view from the views menu. Leaflet renders objects with geo coordinates as clustered markers on OpenStreetMap tiles. An instructive empty state explains what geo properties are needed when no data matches.
**Demo:** Open Map View from sidebar → see instructive empty state (no models define geo coords). With test geo data, Leaflet map renders clustered markers. Clicking a marker opens the object tab.

## Must-Haves

- `_detect_geo_fields()` finds lat/lng property pairs from SHACL shapes (wgs84, schema.org, heuristic)
- `execute_map_query()` returns `{"markers": [...], "geo_fields": {...}}` from SPARQL
- Map renderer branch in `generic_view()` and `generic_view_data()` with three empty-state paths
- `map_view.html` template with lazy-loaded Leaflet 1.9.4 + MarkerCluster 1.5.3
- Marker click calls `openTab(iri, title)` to open object tab
- ResizeObserver calls `map.invalidateSize()` on container resize
- Dark mode tile filter and Leaflet control overrides
- `"map"` entry in workspace.js labels and views_explorer sidebar
- Unit tests for `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all unit tests pass
- `cd e2e && npx playwright test tests/02-views/map-view.spec.ts` — E2E tests pass (empty-state verification, map loading)
- `grep -c 'execute_map_query: query failed' backend/app/views/service.py` — failure log line exists (diagnostic path)

## Observability / Diagnostics

- **Geo detection logging:** `_detect_geo_fields` logs at DEBUG level for IRI/heuristic matches and when no geo pair is found. Includes the type IRI and resolved property paths.
- **Query failure logging:** `execute_map_query` logs at WARNING level with `exc_info=True` when the SPARQL query fails, returning empty markers gracefully instead of crashing.
- **Router logging:** `generic_view()` map branch logs at INFO level when no type selected, WARNING when type has no geo fields, INFO with full details (type, scope_query, lat/lng paths) on success.
- **Empty-state visibility:** Three distinct empty states in the template (no type, no geo fields, geo data present but empty) — each with an instructive user-facing message identifying what's missing.
- **Redaction:** No secrets in any log statement — only IRIs and property paths.

## Tasks

- [x] **T01: Backend geo field detection, map query, and router wiring** `est:45m`
  - Why: Provides the data layer — geo property detection via SHACL, SPARQL query building, JSON data endpoint, and the `generic_view()` renderer branch for map. Mirrors calendar T01 exactly.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/tests/test_map.py`
  - Do: (1) Add `_WELL_KNOWN_GEO_PATHS`, `_XSD_DECIMAL_TYPES` class constants to ViewSpecService. (2) Add `_detect_geo_fields(type_iri)` method scanning SHACL PropertyShapes for lat/lng pairs — by well-known IRI (wgs84:lat/long, schema:latitude/longitude) and by path local-name heuristic. (3) Add `_build_map_select()` static method building the SPARQL query with required lat/lng and optional label. (4) Add `execute_map_query()` returning `{"markers": [...], "geo_fields": {...}}`. (5) Add `"map"` to `_VALID_RENDERERS`. (6) Add `elif renderer == "map":` branch in `generic_view()` with three empty-state paths (no type, no geo fields, geo fields present). (7) Add `elif renderer == "map":` in `generic_view_data()` and update allowed-renderers check from `("graph", "calendar")` to `("graph", "calendar", "map")`. (8) Write `test_map.py` mirroring `test_calendar.py` structure — test geo field detection (wgs84, schema.org, heuristic, no-match, no-shapes-service), query building, and execute_map_query event mapping.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all tests pass
  - Done when: All unit tests pass and `"map"` is a registered renderer with working data endpoint

- [ ] **T02: Frontend template, CSS, sidebar wiring, and E2E test** `est:45m`
  - Why: Provides the user-facing map UI — Leaflet template with marker rendering, empty state, dark mode, dockview integration, and sidebar entry. E2E test proves the view opens and shows correct empty state.
  - Files: `backend/app/templates/browser/map_view.html`, `frontend/static/css/views.css`, `frontend/static/js/workspace.js`, `backend/app/templates/browser/views_explorer.html`, `e2e/helpers/selectors.ts`, `e2e/tests/02-views/map-view.spec.ts`
  - Do: (1) Create `map_view.html` following `calendar_view.html` pattern: `.view-flex-column` wrapper, type filter pills include, view toolbar include, three empty-state branches (`error_message`, no `geo_fields`, normal), Leaflet CSS/JS lazy-load (CSS first, then leaflet.js, then markercluster.js), map init with `L.map().setView([20, 0], 2)`, OSM tile layer, MarkerCluster group, fetch from `map_data_url`, marker click → `openTab(iri, title)`, `fitBounds` when markers exist, `ResizeObserver` calling `map.invalidateSize()`. (2) Add `.map-container` CSS to `views.css` (flex:1, min-height:0, overflow:hidden, padding:12px) plus dark mode Leaflet overrides (tile filter, control backgrounds, attribution). (3) Add `map: 'Map View'` to labels dict in `workspace.js` `openGenericViewTab()`. (4) Add Map View sidebar entry to `views_explorer.html` (mirrors calendar entry with draggable, ondragstart, onclick). (5) Add `map: '[data-testid="map-view"]'` to `SEL.views` in `e2e/helpers/selectors.ts`. (6) Write `map-view.spec.ts` E2E test: opens map view, verifies empty-state message appears for a type without geo properties.
  - Verify: `cd e2e && npx playwright test tests/02-views/map-view.spec.ts` — E2E tests pass
  - Done when: Map View is openable from sidebar, shows instructive empty state, Leaflet loads when geo data exists, dark mode works, marker click opens object tab

## Files Likely Touched

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/tests/test_map.py`
- `backend/app/templates/browser/map_view.html`
- `frontend/static/css/views.css`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/views_explorer.html`
- `e2e/helpers/selectors.ts`
- `e2e/tests/02-views/map-view.spec.ts`
