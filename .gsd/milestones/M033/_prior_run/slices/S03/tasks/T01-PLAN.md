---
estimated_steps: 9
estimated_files: 6
skills_used: []
---

# T01: Backend map renderer — registry, geo detection, SPARQL query, data endpoint

**Slice:** S03 — Map View Renderer
**Milestone:** M033

## Description

Register the map renderer backend following the S02 calendar pattern exactly. This includes the `RENDERER_REGISTRY` entry, `_VALID_RENDERERS` extension, geo-field detection from SHACL shapes, SPARQL query building for geo-located objects, `execute_map_query()` returning JSON markers, router branches in `generic_view()` and `generic_graph_data()`, the `map_view.html` template, and model data updates (shape properties + seed coordinates).

The calendar implementation in S02 is the exact blueprint:
- `_detect_date_fields()` → `_detect_geo_fields()` (scans PropertyShapes for schema:latitude/longitude)
- `_build_calendar_select()` → `_build_map_select()` (SPARQL with lat/lng instead of start/end dates)
- `execute_calendar_query()` → `execute_map_query()` (returns `[{id, label, lat, lng, type}]`)
- `generic_view()` calendar branch → map branch (detects geo fields, builds data URL, renders template)
- `generic_graph_data()` calendar branch → map branch (detects geo fields, runs query, returns JSON)

## Steps

1. **Registry entry:** Add `"map": {"type": "map", "label": "Map View", "template": "browser/map_view.html", "icon": "🌍"}` to `RENDERER_REGISTRY` in `backend/app/views/registry.py`, following the calendar entry pattern.

2. **Valid renderers:** Add `"map"` to the `_VALID_RENDERERS` set in `backend/app/views/router.py`. Update the invalid-renderer error message to include "map".

3. **Geo field detection:** In `backend/app/views/service.py`, add class-level constants `_GEO_LAT_PATHS` and `_GEO_LNG_PATHS` (lists of well-known IRIs: `https://schema.org/latitude`, `http://schema.org/latitude`, etc.) and `_GEO_DATATYPES` (`xsd:decimal`, `xsd:float`, `xsd:double`). Add `async def _detect_geo_fields(self, type_iri: str) -> tuple[PropertyShape | None, PropertyShape | None]` method that:
   - Gets form via `self._shapes_service.get_form_for_type(type_iri)`
   - Stage 1: exact path match against `_GEO_LAT_PATHS` / `_GEO_LNG_PATHS`
   - Stage 2: fallback — scan for properties with path containing "lat"/"latitude" or "lng"/"lon"/"longitude"
   - Returns `(lat_property, lng_property)` — either may be None

4. **SPARQL query builder:** Add `@staticmethod def _build_map_select(type_iri, lat_path, lng_path, scope_filter=None) -> str` that builds:
   ```sparql
   SELECT ?s ?label ?lat ?lng ?type WHERE {
     [?s rdf:type <TYPE_IRI> .]
     ?s <LAT_PATH> ?lat .
     ?s <LNG_PATH> ?lng .
     OPTIONAL { ?s rdfs:label|dcterms:title ?label }
     OPTIONAL { ?s rdf:type ?type }
     [scope_filter sub-select if present]
   }
   ```
   When `type_iri` is None, omit the type triple. Lat and lng are required (not OPTIONAL).

5. **Query executor:** Add `async def execute_map_query(self, type_iri, lat_path, lng_path, scope_filter=None) -> list[dict]` that:
   - Calls `_build_map_select()`, scopes to current graph, executes via triplestore
   - Transforms bindings to `{id, label, lat, lng, type, properties: {iri, type}}`
   - Deduplicates by IRI
   - Logs INFO with type, paths, scope, marker count
   - Returns empty list on error (with WARNING log)

6. **Router `generic_view()` branch:** Add `elif renderer == "map":` after the calendar branch. Pattern:
   - Detect geo fields if `type_iri` is set
   - Build `map_data_url = "/browser/views/generic/map/data"` with query params
   - Pass `lat_field`, `lng_field`, `map_data_url` to template context
   - Render `browser/map_view.html`

7. **Router `generic_graph_data()` extension:** Change the guard from `if renderer not in ("graph", "calendar"):` to `if renderer not in ("graph", "calendar", "map"):`. Add `elif renderer == "map":` branch that detects geo fields, runs `execute_map_query()`, returns JSON.

8. **Template:** Create `backend/app/templates/browser/map_view.html` with:
   - `.view-flex-column` wrapper
   - `type_filter_pills.html` include (guarded by `is_generic`)
   - `view_toolbar.html` include
   - Empty state when `selected_type and not lat_field and not lng_field`
   - `<div id="map-container" class="map-container"></div>` for Leaflet
   - Leaflet CSS `<link>` tags (leaflet.css + leaflet-markercluster.css via `asset_url`)
   - Leaflet JS `<script>` tags (leaflet.js + leaflet-markercluster.js via `asset_url`)
   - CDN fallbacks for both
   - `tryInit()` polling script that calls `window.initMap('map-container', dataUrl, {})`

9. **Model data:** In `models/basic-pkm/shapes/basic-pkm.jsonld`, add two new PropertyShape entries to EventShape's `sh:property` array:
   - `schema:latitude` with `sh:datatype xsd:decimal`, `sh:maxCount 1`, `sh:name "Latitude"`, reasonable `sh:order`
   - `schema:longitude` with `sh:datatype xsd:decimal`, `sh:maxCount 1`, `sh:name "Longitude"`, reasonable `sh:order`
   In `models/basic-pkm/seed/basic-pkm.jsonld`, add `schema:latitude` and `schema:longitude` values to `bpkm:seed-event-offsite` (Mountain View: 37.3861, -122.0839). Add 3 new seed events with diverse locations:
   - `bpkm:seed-event-conference` (PyCon US, Pittsburgh: 40.4406, -79.9959)
   - `bpkm:seed-event-meetup` (Tech Meetup, London: 51.5074, -0.1278)
   - `bpkm:seed-event-workshop` (Design Workshop, Tokyo: 35.6762, 139.6503)
   Each new event needs `@type`, `dcterms:title`, `schema:startDate`, `dcterms:created`, `bpkm:eventStatus`, and the lat/lng.

## Must-Haves

- [ ] `"map"` in `RENDERER_REGISTRY` with template path
- [ ] `"map"` in `_VALID_RENDERERS`
- [ ] `_detect_geo_fields()` returns lat/lng PropertyShape pair from SHACL shapes
- [ ] `_build_map_select()` generates valid SPARQL with required lat/lng bindings
- [ ] `execute_map_query()` returns `[{id, label, lat, lng, type}]` list
- [ ] `generic_view()` renders `map_view.html` for `renderer == "map"`
- [ ] `generic_graph_data()` returns JSON for `renderer == "map"`
- [ ] `map_view.html` has `.view-flex-column`, type pills, toolbar, container, Leaflet script/link tags, CDN fallback, tryInit
- [ ] EventShape has `schema:latitude` and `schema:longitude` properties
- [ ] 4+ seed events have geographic coordinates

## Verification

- `rg '"map"' backend/app/views/registry.py` — shows RENDERER_REGISTRY entry
- `rg '"map"' backend/app/views/router.py` — shows _VALID_RENDERERS and elif branches
- `rg '_detect_geo_fields\|_build_map_select\|execute_map_query' backend/app/views/service.py` — all three methods exist
- `test -f backend/app/templates/browser/map_view.html` — template exists
- `rg 'schema:latitude' models/basic-pkm/shapes/basic-pkm.jsonld` — geo property in shape
- `rg 'latitude' models/basic-pkm/seed/basic-pkm.jsonld` — coordinates in seed data
- `python3 -c "import json; d=json.load(open('models/basic-pkm/seed/basic-pkm.jsonld')); evts=[x for x in d['@graph'] if 'schema:latitude' in x]; print(f'{len(evts)} events with coordinates'); assert len(evts) >= 4"` — at least 4 geo events

## Inputs

- `backend/app/views/registry.py` — existing RENDERER_REGISTRY with calendar entry
- `backend/app/views/router.py` — existing generic_view() and generic_graph_data() with calendar branches
- `backend/app/views/service.py` — existing _detect_date_fields(), _build_calendar_select(), execute_calendar_query() as patterns
- `backend/app/templates/browser/calendar_view.html` — template pattern to follow
- `models/basic-pkm/shapes/basic-pkm.jsonld` — EventShape to extend with lat/lng
- `models/basic-pkm/seed/basic-pkm.jsonld` — seed events to extend with coordinates

## Expected Output

- `backend/app/views/registry.py` — modified with map entry
- `backend/app/views/router.py` — modified with map branches
- `backend/app/views/service.py` — modified with geo detection, query builder, executor
- `backend/app/templates/browser/map_view.html` — new template
- `models/basic-pkm/shapes/basic-pkm.jsonld` — modified with latitude/longitude properties
- `models/basic-pkm/seed/basic-pkm.jsonld` — modified with geo coordinates on events

## Observability Impact

- **New INFO log**: `execute_map_query: type=<iri> lat_path=<path> lng_path=<path> scope=<bool>` — logged on every map data request with resolved paths and scope status
- **New INFO log**: `execute_map_query: returned <N> markers` — marker count after query execution
- **New WARNING log**: `execute_map_query: missing lat_path or lng_path` — logged when geo fields could not be detected
- **New WARNING log**: `execute_map_query: query failed for type=<iri>` — logged when SPARQL execution fails
- **New WARNING log**: `_detect_geo_fields: shapes lookup failed for <iri>` — logged when SHACL shapes service returns an error
- **Inspection surface**: `GET /browser/views/generic/map/data?type=<iri>` — returns raw JSON marker array for debugging geo data without rendering the UI
- **Future agent**: grep for `execute_map_query` in application logs to diagnose map data issues; hit the `/data` endpoint directly with curl to verify backend independently of frontend
