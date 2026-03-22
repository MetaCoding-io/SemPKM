---
estimated_steps: 8
estimated_files: 3
skills_used:
  - test
---

# T01: Backend geo field detection, map query, and router wiring

**Slice:** S04 — Map View
**Milestone:** M033

## Description

Add the backend data layer for the map view renderer. This mirrors the calendar view implementation exactly: SHACL-based property detection (`_detect_geo_fields()`), SPARQL query building (`_build_map_select()`), query execution returning marker JSON (`execute_map_query()`), and router branches in both `generic_view()` and `generic_view_data()`. Unit tests cover all detection heuristics and query mapping.

## Steps

1. **Add geo constants to `ViewSpecService`** in `backend/app/views/service.py`, placed right after the existing calendar constants (after line ~1168):
   - `_WELL_KNOWN_GEO_PATHS: set[str]` — `{"lat", "latitude", "long", "longitude", "lng"}` (matched against local name of `sh:path`, case-insensitive)
   - `_XSD_DECIMAL_TYPES: set[str]` — `{"http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2001/XMLSchema#double"}`
   - `_WELL_KNOWN_GEO_IRIS: dict[str, str]` — maps well-known full IRIs to their role: `{"http://www.w3.org/2003/01/geo/wgs84_pos#lat": "lat", "http://www.w3.org/2003/01/geo/wgs84_pos#long": "lng", "http://schema.org/latitude": "lat", "http://schema.org/longitude": "lng"}`

2. **Add `_detect_geo_fields()` method** to `ViewSpecService` (after `execute_calendar_query`, before `_detect_status_field`):
   - Signature: `async def _detect_geo_fields(self, type_iri: str) -> tuple[PropertyShape | None, PropertyShape | None]`
   - Returns `(lat_field, lng_field)` or `(None, None)`
   - Uses `self._shapes_service.get_form_for_type(type_iri)` to get SHACL properties
   - Detection priority: (a) Well-known full IRI match (`_WELL_KNOWN_GEO_IRIS`), (b) local name heuristic against `_WELL_KNOWN_GEO_PATHS`
   - Must find both lat and lng — if only one found, return `(None, None)`

3. **Add `_build_map_select()` static method**:
   - Signature: `@staticmethod def _build_map_select(type_iri: str, lat_path: str, lng_path: str, scope_filter: str | None = None) -> str`
   - Returns SPARQL SELECT with required `?lat` and `?lng`, OPTIONAL `?label`, and optional scope sub-select
   - Both lat and lng are required (non-OPTIONAL) — objects without both are excluded

4. **Add `execute_map_query()` method**:
   - Signature: `async def execute_map_query(self, type_iri: str, lat_field: PropertyShape, lng_field: PropertyShape, scope_filter: str | None = None) -> dict`
   - Builds query via `_build_map_select()`, scopes to current graph, executes, maps bindings to `{"markers": [...], "geo_fields": {...}}`
   - Each marker: `{"iri": str, "title": str, "lat": float, "lng": float}`
   - Deduplicate by IRI, skip entries missing lat/lng values, parse lat/lng as float

5. **Add `"map"` to `_VALID_RENDERERS`** in `backend/app/views/router.py` (line 204): change from `{"table", "card", "graph", "kanban", "calendar"}` to include `"map"`

6. **Add `elif renderer == "map":` branch in `generic_view()`** — mirrors the calendar branch structure:
   - No type → empty state with "Select a type to use Map View"
   - Type but no geo fields → empty state with "This type has no geographic coordinate properties for Map display"
   - Type with geo fields → build `map_data_url`, pass `geo_fields` dict to template
   - Template name: `"browser/map_view.html"` (created in T02)
   - Context keys: same as calendar (`request`, `type_label`, `type_iri`, `selected_type`, `types`, `model_view_specs`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `is_generic`, `renderer`, `pagination_base_url`, `pag_extra`, `spec`) plus `map_data_url` and `geo_fields` (or `error_message`)

7. **Add `elif renderer == "map":` in `generic_view_data()`**:
   - Update guard from `if renderer not in ("graph", "calendar"):` to `if renderer not in ("graph", "calendar", "map"):`
   - Add map data branch: detect geo fields, return empty markers if none, execute map query

8. **Write `backend/tests/test_map.py`** mirroring `backend/tests/test_calendar.py`:
   - Test `_detect_geo_fields()`: wgs84 IRI pair, schema.org IRI pair, heuristic local name match, no match returns `(None, None)`, shapes service None, shapes service raises exception, only lat found (no lng) returns `(None, None)`
   - Test `_build_map_select()`: basic query structure, with scope filter, verify lat/lng are required (non-OPTIONAL)
   - Test `execute_map_query()`: maps SPARQL bindings to markers, deduplicates by IRI, handles empty results, handles query exception gracefully

## Must-Haves

- [ ] `_detect_geo_fields()` finds wgs84:lat/long and schema:latitude/longitude by full IRI
- [ ] `_detect_geo_fields()` finds lat/lng by local-name heuristic on any property
- [ ] `_detect_geo_fields()` returns `(None, None)` when only one coordinate found
- [ ] `_build_map_select()` generates SPARQL with both lat and lng as required (non-OPTIONAL)
- [ ] `execute_map_query()` returns `{"markers": [...], "geo_fields": {...}}` with float lat/lng
- [ ] `"map"` is in `_VALID_RENDERERS`
- [ ] `generic_view()` has map branch with three empty-state paths
- [ ] `generic_view_data()` serves map JSON data
- [ ] All unit tests in `test_map.py` pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all tests pass
- `grep -q '"map"' backend/app/views/router.py` — "map" registered as valid renderer

## Inputs

- `backend/app/views/service.py` — existing ViewSpecService with calendar detection pattern to mirror
- `backend/app/views/router.py` — existing router with calendar branches to mirror
- `backend/tests/test_calendar.py` — test structure and helpers to mirror
- `backend/app/services/shapes.py` — PropertyShape and NodeShapeForm dataclasses

## Expected Output

- `backend/app/views/service.py` — modified with `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()`, geo constants
- `backend/app/views/router.py` — modified with map renderer branches and `"map"` in `_VALID_RENDERERS`
- `backend/tests/test_map.py` — new file with comprehensive geo detection and query tests

## Observability Impact

- `_detect_geo_fields` emits DEBUG logs with type IRI + resolved lat/lng paths (or explanation of no-match)
- `execute_map_query` emits WARNING on SPARQL failure (with stack trace via `exc_info=True`), INFO on success (type + marker count)
- `generic_view()` map branch: INFO on no-type, WARNING on no-geo-fields, INFO with lat/lng/scope details on success
- **Future agent inspection:** grep for `_detect_geo_fields:`, `execute_map_query:`, or `renderer=map` in logs to trace map view data flow
