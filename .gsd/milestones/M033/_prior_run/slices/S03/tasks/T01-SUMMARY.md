---
id: T01
parent: S03
milestone: M033
provides:
  - Map renderer registered in RENDERER_REGISTRY and _VALID_RENDERERS
  - _detect_geo_fields() geo field detection from SHACL shapes
  - _build_map_select() SPARQL query builder for geo-located objects
  - execute_map_query() returns JSON marker array
  - Router branches in generic_view() and generic_graph_data() for map renderer
  - map_view.html template with type pills, toolbar, empty state, Leaflet CDN fallback
  - EventShape extended with schema:latitude and schema:longitude properties
  - 4 seed events with geographic coordinates across 4 continents
key_files:
  - backend/app/views/registry.py
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/templates/browser/map_view.html
  - models/basic-pkm/shapes/basic-pkm.jsonld
  - models/basic-pkm/seed/basic-pkm.jsonld
key_decisions:
  - Geo properties placed in EventInfoGroup at order 31-32, after existing metadata fields
  - _detect_geo_fields uses two-stage detection matching _detect_date_fields pattern
  - Coordinates stored as xsd:decimal for precision, parsed to float in execute_map_query
patterns_established:
  - Map renderer follows exact calendar renderer pattern for registry/router/service/template
observability_surfaces:
  - INFO log execute_map_query with type, lat/lng paths, scope, marker count
  - WARNING log on missing geo paths or query failure
  - GET /browser/views/generic/map/data JSON endpoint for debugging
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Backend map renderer — registry, geo detection, SPARQL query, data endpoint

**Added map renderer backend: registry entry, geo field detection from SHACL shapes, SPARQL query builder, JSON data endpoint, template, and EventShape lat/lng properties with 4 geo-located seed events.**

## What Happened

Followed the S02 calendar renderer pattern exactly to build the map renderer backend:

1. **Registry** — Added `"map"` entry to `RENDERER_REGISTRY` with template path `browser/map_view.html`, label, and icon.

2. **Valid renderers** — Added `"map"` to `_VALID_RENDERERS` set and updated the error message.

3. **Geo field detection** — Added `_GEO_LAT_PATHS`, `_GEO_LNG_PATHS`, `_GEO_DATATYPES` class constants and `_detect_geo_fields()` method to `ViewSpecService`. Two-stage detection: (1) exact path match against well-known IRIs (`schema:latitude`/`schema:longitude`, both http and https variants), (2) fallback scan by path name fragments (`lat`, `latitude`, `lng`, `lon`, `longitude`).

4. **SPARQL query builder** — Added `_build_map_select()` static method that generates a SELECT query with required lat/lng bindings (not OPTIONAL), optional label and type, and support for type filtering and scope sub-select.

5. **Query executor** — Added `execute_map_query()` that builds the query, scopes to current graph, executes via triplestore, deduplicates by IRI, parses lat/lng to float, and returns `[{id, label, lat, lng, type, properties}]`. Logs INFO with parameters and marker count. Returns empty list on error with WARNING log.

6. **Router branches** — Added `elif renderer == "map"` in both `generic_view()` (detects geo fields, builds data URL, renders template) and `generic_graph_data()` (detects geo fields, runs query, returns JSON). Extended the data endpoint guard to include `"map"`.

7. **Template** — Created `map_view.html` with `.view-flex-column` wrapper, type filter pills (guarded by `is_generic`), view toolbar, empty state when type selected but no geo fields detected, and map container div. Includes Leaflet CSS/JS and markercluster CSS/JS via `asset_url` with CDN fallbacks. Has `tryInit()` polling script that calls `window.initMap()`.

8. **Model data** — Added `schema:latitude` (xsd:decimal) and `schema:longitude` (xsd:decimal) PropertyShapes to EventShape at order 31-32. Added coordinates to `seed-event-offsite` (Mountain View) and created 3 new seed events: `seed-event-conference` (Pittsburgh), `seed-event-meetup` (London), `seed-event-workshop` (Tokyo).

## Verification

All T01-relevant checks pass:
- `"map"` present in RENDERER_REGISTRY and _VALID_RENDERERS
- `_detect_geo_fields`, `_build_map_select`, `execute_map_query` methods exist in service.py
- `map_view.html` template exists with correct structure
- `schema:latitude` and `schema:longitude` in EventShape
- 4 seed events have geographic coordinates
- All modified Python files pass syntax check
- Both JSON-LD files are valid JSON

Frontend checks (leaflet.js vendoring, map.js, explorer entry, workspace labels) are T02's responsibility and expected to not pass yet.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '"map"' backend/app/views/registry.py` | 0 | ✅ pass | <1s |
| 2 | `rg '"map"' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 3 | `rg '_detect_geo_fields\|_build_map_select\|execute_map_query' backend/app/views/service.py` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/app/templates/browser/map_view.html` | 0 | ✅ pass | <1s |
| 5 | `rg 'schema:latitude' models/basic-pkm/shapes/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 6 | `rg 'latitude' models/basic-pkm/seed/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import json; ... assert len(evts) >= 4"` | 0 | ✅ pass | <1s |
| 8 | `python3 -c "import ast; ast.parse(...)"` (3 files) | 0 | ✅ pass | <1s |
| 9 | `rg 'execute_map_query.*missing\|...' backend/app/views/service.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Logs**: grep for `execute_map_query` in application logs to see query parameters and marker counts
- **Data endpoint**: `GET /browser/views/generic/map/data?type=<encoded_type_iri>` returns raw JSON array of markers for debugging without the frontend
- **Geo detection**: `_detect_geo_fields` WARNING on shapes lookup failure surfaces in logs
- **Missing fields**: `execute_map_query: missing lat_path or lng_path` WARNING when type has no geo properties

## Deviations

None — implementation followed the task plan's 9 steps exactly, using the calendar renderer as the blueprint.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/registry.py` — Added `"map"` entry to RENDERER_REGISTRY
- `backend/app/views/router.py` — Added `"map"` to _VALID_RENDERERS, `elif renderer == "map"` branches in generic_view() and generic_graph_data()
- `backend/app/views/service.py` — Added _GEO_LAT_PATHS, _GEO_LNG_PATHS, _GEO_DATATYPES, _detect_geo_fields(), _build_map_select(), execute_map_query()
- `backend/app/templates/browser/map_view.html` — New template with type pills, toolbar, empty state, Leaflet scripts, tryInit
- `models/basic-pkm/shapes/basic-pkm.jsonld` — Added schema:latitude and schema:longitude PropertyShapes to EventShape
- `models/basic-pkm/seed/basic-pkm.jsonld` — Added coordinates to seed-event-offsite, created 3 new seed events with global coordinates
