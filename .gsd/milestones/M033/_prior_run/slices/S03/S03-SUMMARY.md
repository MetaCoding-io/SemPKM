---
slice: S03
milestone: M033
title: "Map View Renderer"
status: done
tasks_completed: 3
tasks_total: 3
test_count: 25
test_status: all_passing
duration_estimate: 115m
duration_actual: ~40m
---

# S03 Summary: Map View Renderer

## What Was Delivered

A Leaflet-based map renderer that displays RDF objects with geographic coordinates as clustered markers on an OpenStreetMap basemap. The implementation mirrors the S02 calendar renderer pattern exactly — same registry/router/service/template/JS/build/test structure.

### Backend (T01)

- **Registry**: `"map"` entry in `RENDERER_REGISTRY` with template, label, icon
- **Valid renderers**: `_VALID_RENDERERS` extended to include `"map"`
- **Geo field detection**: `_detect_geo_fields()` on `ViewSpecService` — two-stage detection: (1) exact path match against `schema:latitude`/`schema:longitude` (http + https variants), (2) fallback scan by path name fragments (`lat`, `latitude`, `lng`, `lon`, `longitude`). Mirrors `_detect_date_fields()` pattern.
- **SPARQL query builder**: `_build_map_select()` generates SELECT with required lat/lng bindings, optional label/type, type filter, and scope sub-select support
- **Query executor**: `execute_map_query()` — builds query, scopes to current graph, deduplicates by IRI, parses coordinates to float, returns `[{id, label, lat, lng, type, properties}]`
- **Router branches**: `elif renderer == "map"` in both `generic_view()` and `generic_graph_data()`
- **Template**: `map_view.html` with `.view-flex-column` wrapper, type filter pills, toolbar, geo-missing empty state, Leaflet CSS/JS with CDN fallback, `tryInit()` polling
- **Model data**: `schema:latitude` (xsd:decimal) and `schema:longitude` (xsd:decimal) added to EventShape. 4 seed events with global coordinates (Mountain View, Pittsburgh, London, Tokyo)

### Frontend (T02)

- **map.js**: IIFE with `initMap(containerId, dataUrl, options)` — L.map + OSM tiles + L.markerClusterGroup + popup with click-to-open via `openTab()`. ResizeObserver for dockview panel resize. XSS-safe HTML escaping for popup content. Tile error logging (once per container).
- **Leaflet vendoring**: `leaflet@1.9.4` and `leaflet.markercluster@^1.5.3` in package.json, 4 sections in build.js (JS + CSS for each), content-hashed with manifest entries
- **Explorer entry**: Map View with globe emoji (🌍) and canvas drag support
- **Workspace label**: `map: 'Map View'` in labels dict
- **Dark mode**: CSS filter (invert + hue-rotate) on tile pane, dark popup backgrounds
- **Marker style**: L.divIcon with CSS-styled circles (avoids default PNG icon path issues)

### Tests (T03)

- **25 unit tests** across 3 classes:
  - `TestDetectGeoFields` (10): exact match, http/https variants, fallback, missing shapes, error handling, lat-only, decimal datatype, priority ordering
  - `TestBuildMapSelect` (6): type filter, no type, scope filter, custom paths, label alternatives, no sub-select
  - `TestExecuteMapQuery` (9): JSON format, dedup, label fallback, empty results, error handling, float coordinates, missing paths, invalid coordinates

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Marker rendering | L.divIcon with CSS circles | Avoids vendored PNG icon path issues; CSS styling for dark mode and customization |
| Popup security | _escapeHtml/_escapeAttr helpers | Object labels are user-controlled; prevents XSS in popup content |
| Geo detection strategy | Two-stage (exact + fallback) matching _detect_date_fields | Consistent pattern across all field-detection methods; covers both schema.org and custom ontologies |
| Coordinate storage | xsd:decimal in SHACL shapes | Precision for lat/lng; parsed to float in execute_map_query |

## Patterns Established

1. **Map renderer mirrors calendar renderer exactly**: registry entry → router branches → service methods → template → JS IIFE → build vendoring → explorer entry → workspace label → dark mode CSS → unit tests. Any future renderer (timeline, treemap, etc.) follows this same 10-step pattern.
2. **Geo field detection via SHACL shapes**: `_detect_geo_fields()` parallels `_detect_date_fields()` — same two-stage approach (well-known paths → name fragment fallback). Future field detectors should follow this pattern.
3. **L.divIcon over default markers**: Avoids Leaflet's well-known `icon-default` path issue in bundled environments.

## Observability

- **Backend**: `execute_map_query` INFO log with type, lat/lng paths, scope, marker count. `_detect_geo_fields` WARNING on shapes lookup failure. `execute_map_query: missing lat_path or lng_path` WARNING when type has no geo properties.
- **Frontend**: `[map] Container not found` (warn), `[map] Failed to load markers` (error), `[map] Tile loading failed` (warn). `container._mapInstance` for DevTools inspection.
- **Data endpoint**: `GET /browser/views/generic/map/data?type=<iri>` returns raw JSON marker array for debugging.

## Requirements Validated

MAP-01 through MAP-07 created and validated — covering renderer registration, geo detection, Leaflet lazy-loading, marker clustering, click-to-open, dark mode, and geo seed data.

## What the Next Slice Should Know

- The renderer pattern is now proven twice (calendar + map). S04 (Isometric Graph) is a different kind of feature — a Cytoscape layout extension, not a view renderer — so it won't follow this pattern.
- The `_VALID_RENDERERS` set in router.py now contains 6 entries: table, card, graph, kanban, calendar, map.
- Leaflet and MarkerCluster are vendored — any future map-related feature can reuse them without adding dependencies.
- The `generic_graph_data()` function now has branches for graph, calendar, and map data endpoints.

## Files Changed

### Created
- `backend/app/templates/browser/map_view.html`
- `frontend/static/js/map.js`
- `backend/tests/test_map.py`

### Modified
- `backend/app/views/registry.py` — map entry
- `backend/app/views/router.py` — map branches + valid renderers
- `backend/app/views/service.py` — geo detection + query builder + executor
- `frontend/build.js` — Leaflet + MarkerCluster vendoring
- `frontend/package.json` — leaflet + markercluster deps
- `frontend/static/css/views.css` — map container, markers, dark mode
- `backend/app/templates/browser/views_explorer.html` — Map View entry
- `frontend/static/js/workspace.js` — map label
- `backend/app/templates/base.html` — map.js script tag
- `models/basic-pkm/shapes/basic-pkm.jsonld` — latitude/longitude PropertyShapes
- `models/basic-pkm/seed/basic-pkm.jsonld` — 4 geo-located seed events
