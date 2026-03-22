---
id: T03
parent: S03
milestone: M033
provides:
  - 25 unit tests across 3 test classes covering map geo detection, SPARQL query building, and marker data transformation
key_files:
  - backend/tests/test_map.py
key_decisions:
  - Added test_invalid_coordinates_skipped, test_missing_lat/lng_path_returns_empty, and test_exact_match_takes_priority_over_fallback beyond the 15-test minimum for fuller edge-case coverage
patterns_established:
  - Map test file mirrors calendar test file structure exactly — same helpers, same 3-class layout, same mock patterns
observability_surfaces:
  - none — test-only task, no runtime signals added
duration: 8m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Unit tests for map geo detection, query building, and data transformation

**Created test_map.py with 25 tests across 3 classes covering _detect_geo_fields(), _build_map_select(), and execute_map_query() — all passing.**

## What Happened

Created `backend/tests/test_map.py` following the `test_calendar.py` structure with shared helpers (`_make_property`, `_make_form`, `_build_service`) and three test classes:

1. **TestDetectGeoFields** (10 tests) — exact schema:latitude/longitude path matching, http/https variants, fallback by path name fragments (lat/lon/longitude), no-geo-properties returning None, shapes_service is None, shapes lookup error, form returns None, lat-only with no lng, decimal datatype detection, exact match priority over fallback.

2. **TestBuildMapSelect** (6 tests) — query with type filter and required lat/lng bindings, query without type, scope filter as sub-select, custom lat/lng path IRIs in query, label alternative paths (rdfs:label|dcterms:title), no scope filter produces no sub-select.

3. **TestExecuteMapQuery** (9 tests) — JSON marker format `{id, label, lat, lng, type, properties}`, deduplication by IRI, missing label falls back to local name, empty bindings returns empty list, triplestore error returns empty list, lat/lng are floats (not strings), missing lat_path returns empty, missing lng_path returns empty, invalid non-numeric coordinates skipped.

The `_build_service` helper was extended with a `query_side_effect` parameter (beyond the calendar pattern) to cleanly test triplestore error paths in `execute_map_query`.

## Verification

All 25 tests pass. All slice-level verification checks pass — this is the final task so all 10 checks were confirmed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `grep -c "def test_" backend/tests/test_map.py` | 0 | ✅ pass (25) | <1s |
| 3 | `grep -c "class Test" backend/tests/test_map.py` | 0 | ✅ pass (3) | <1s |
| 4 | `rg '"map"' backend/app/views/registry.py` | 0 | ✅ pass | <1s |
| 5 | `rg '"map"' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 6 | `rg 'leaflet.js' frontend/build.js` | 0 | ✅ pass | <1s |
| 7 | `rg 'initMap' frontend/static/js/map.js` | 0 | ✅ pass | <1s |
| 8 | `rg 'schema:latitude' models/basic-pkm/shapes/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 9 | `rg 'latitude' models/basic-pkm/seed/basic-pkm.jsonld` | 0 | ✅ pass | <1s |
| 10 | `rg "map.*Map View" backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 11 | `rg "map:" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 12 | `rg 'execute_map_query.*missing\|...\|_detect_geo_fields.*failed' backend/app/views/service.py` | 0 | ✅ pass | <1s |

## Diagnostics

Test-only task — no runtime diagnostics added. Run `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` to verify test suite.

## Deviations

- Added 10 extra tests beyond the 15-test minimum (25 total) for better edge-case coverage: invalid coordinates, missing lat/lng paths, exact-match priority over fallback.
- Extended `_build_service` helper with `query_side_effect` parameter not in the calendar pattern — needed for clean triplestore error testing.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_map.py` — New test file with 25 tests across 3 classes (TestDetectGeoFields, TestBuildMapSelect, TestExecuteMapQuery)
