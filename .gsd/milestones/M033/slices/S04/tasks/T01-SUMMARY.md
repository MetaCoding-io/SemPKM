---
id: T01
parent: S04
milestone: M033
provides:
  - geo field detection from SHACL shapes (wgs84, schema.org, heuristic)
  - SPARQL map query building with required lat/lng
  - map marker JSON endpoint via generic_view_data
  - map renderer branch in generic_view with three empty-state paths
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_map.py
key_decisions:
  - Two-pass geo detection (IRI match first, local-name heuristic second) with both lat+lng required
  - lat/lng are non-OPTIONAL in SPARQL — objects without both coords are excluded
patterns_established:
  - Map detection mirrors calendar detection pattern exactly — same service method shape, same router branching
observability_surfaces:
  - "_detect_geo_fields:" DEBUG logs for type + resolved lat/lng or no-match reason
  - "execute_map_query:" WARNING on SPARQL failure, INFO with marker count on success
  - "generic_view: renderer=map" INFO/WARNING for each empty-state branch
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Backend geo field detection, map query, and router wiring

**Added geo field detection, SPARQL map query builder, marker JSON endpoint, and map renderer branches with three empty-state paths**

## What Happened

Implemented the full backend data layer for the map view renderer, mirroring the calendar view pattern:

1. **Geo constants** — Added `_WELL_KNOWN_GEO_PATHS` (lat/latitude/long/longitude/lng), `_XSD_DECIMAL_TYPES`, and `_WELL_KNOWN_GEO_IRIS` (wgs84 + schema.org → role mapping) to `ViewSpecService`.

2. **`_detect_geo_fields()`** — Two-pass detection: first checks full IRIs against `_WELL_KNOWN_GEO_IRIS` (wgs84:lat/long, schema:latitude/longitude), then falls back to local-name heuristic. Returns `(None, None)` if both lat and lng aren't found — partial matches are rejected.

3. **`_build_map_select()`** — Static method generating SPARQL SELECT with `?s ?label ?lat ?lng`. Both lat and lng are required (non-OPTIONAL) so objects missing coordinates are excluded at the query level. Optional scope sub-select and label binding.

4. **`execute_map_query()`** — Executes the scoped query, deduplicates by IRI, parses coordinates as floats, skips entries with missing/invalid values. Returns `{"markers": [...], "geo_fields": {...}}`.

5. **Router changes** — Added `"map"` to `_VALID_RENDERERS`. Added `elif renderer == "map":` branch in `generic_view()` with three empty-state paths (no type, no geo fields, geo fields present). Added map branch in `generic_view_data()` and updated the allowed-renderers guard.

6. **Tests** — 23 unit tests covering all detection heuristics, query building, and marker mapping edge cases.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — 23/23 tests passed
- `grep -q '"map"' backend/app/views/router.py` — confirmed "map" in `_VALID_RENDERERS`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` | 0 | ✅ pass | 5.5s |
| 2 | `grep -q '"map"' backend/app/views/router.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Geo detection:** grep logs for `_detect_geo_fields:` to see which properties were resolved for a type
- **Query execution:** grep for `execute_map_query:` to see marker counts or SPARQL failures (with stack traces)
- **Router:** grep for `renderer=map` to trace the view rendering path and empty-state branches

## Deviations

None. Implementation follows the task plan exactly.

## Known Issues

- The `map_view.html` template does not exist yet — created in T02. Router will return a template-not-found error if map view is opened before T02 completes.

## Files Created/Modified

- `backend/app/views/service.py` — Added geo constants, `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()` methods
- `backend/app/views/router.py` — Added `"map"` to `_VALID_RENDERERS`, map branch in `generic_view()` and `generic_view_data()`
- `backend/tests/test_map.py` — New file with 23 unit tests for geo detection, query building, and marker mapping
