---
estimated_steps: 4
estimated_files: 1
skills_used:
  - test
---

# T03: Unit tests for map geo detection, query building, and data transformation

**Slice:** S03 — Map View Renderer
**Milestone:** M033

## Description

Create `backend/tests/test_map.py` following the `test_calendar.py` structure (472 lines, 24 tests, 3 test classes). Tests cover `_detect_geo_fields()`, `_build_map_select()`, and `execute_map_query()` on `ViewSpecService` using mocked shapes and triplestore services.

The test file structure mirrors `test_calendar.py` exactly:
- Helper functions: `_make_property()`, `_make_form()`, `_build_service()` 
- `TestDetectGeoFields` — SHACL shape scanning for lat/lng
- `TestBuildMapSelect` — SPARQL query generation
- `TestExecuteMapQuery` — JSON response format and error handling

## Steps

1. **Test helpers:** Copy the helper pattern from `test_calendar.py` — `_make_property(path, name, order, datatype, in_values)`, `_make_form(target_class, properties, label)`, `_build_service(form_return, form_side_effect, shapes_service_none, triplestore_results)`. These are identical since both test files operate on the same `ViewSpecService` class.

2. **TestDetectGeoFields** (target: 8-10 tests):
   - `test_exact_match_schema_latitude_longitude` — shape has `schema:latitude` + `schema:longitude`, both detected
   - `test_http_schema_variant` — `http://schema.org/latitude` matches (not just https)
   - `test_fallback_by_path_fragment` — properties with "lat"/"longitude" in path name are detected when no exact match
   - `test_no_geo_properties` — shape has no geo properties, returns (None, None)
   - `test_no_shapes_service` — `shapes_service` is None, returns (None, None)
   - `test_shapes_lookup_error` — exception in `get_form_for_type`, returns (None, None) with warning
   - `test_no_form_for_type` — form returns None, returns (None, None)
   - `test_lat_only_no_lng` — shape has only latitude property, returns (lat, None)
   - `test_decimal_datatype_detected` — `xsd:decimal` datatype on a "lat" property triggers detection

3. **TestBuildMapSelect** (target: 5-6 tests):
   - `test_basic_query_with_type` — verifies SELECT has `?s ?label ?lat ?lng ?type`, required lat/lng triples, OPTIONAL label/type
   - `test_query_without_type` — no type IRI → no `rdf:type` triple in WHERE
   - `test_query_with_scope_filter` — scope filter injected as sub-select
   - `test_lat_lng_paths_in_query` — actual path IRIs appear in the query string
   - `test_query_has_label_alternative_paths` — OPTIONAL label uses `rdfs:label|dcterms:title`

4. **TestExecuteMapQuery** (target: 5-7 tests):
   - `test_transforms_bindings_to_marker_json` — verifies output format `{id, label, lat, lng, type}`
   - `test_deduplication_by_iri` — same IRI with multiple type bindings → single entry
   - `test_missing_label_falls_back_to_iri` — no label binding → uses IRI as label
   - `test_empty_results` — no bindings → empty list
   - `test_error_returns_empty_list` — triplestore error → empty list, no crash
   - `test_lat_lng_are_floats` — lat/lng values converted from string bindings to float

## Must-Haves

- [ ] 15+ tests across three test classes
- [ ] All tests pass: `cd backend && .venv/bin/python -m pytest tests/test_map.py -v`
- [ ] Geo detection covers exact match, fallback, error paths, and None returns
- [ ] Query builder covers type/no-type, scope filter, required lat/lng bindings
- [ ] Response transformation covers JSON format, deduplication, fallback label, float conversion

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` — all tests pass
- `grep -c "def test_" backend/tests/test_map.py` — returns 15 or more
- `grep -c "class Test" backend/tests/test_map.py` — returns 3

## Inputs

- `backend/tests/test_calendar.py` — structural pattern to follow (helpers, test classes, mock setup)
- `backend/app/views/service.py` — T01 added `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()` methods
- `backend/app/services/shapes.py` — `NodeShapeForm`, `PropertyShape` types used by detection

## Expected Output

- `backend/tests/test_map.py` — new test file with 15+ tests across 3 classes
