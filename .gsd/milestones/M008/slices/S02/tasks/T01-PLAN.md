---
estimated_steps: 8
estimated_files: 2
---

# T01: Backend Properties Endpoint and Unit Tests

**Slice:** S02 — Property Flip on Object Nodes
**Milestone:** M008

## Description

Add `GET /api/canvas/properties?iri=<IRI>` endpoint to the canvas router that returns SHACL-derived property data as JSON. The endpoint follows the same query pattern as `objects.py` (lines 78-165): query current + inferred graphs, resolve types, get SHACL form, build property list with resolved labels. Unit tests mock all external services.

## Steps

1. **Add dependency imports to `backend/app/canvas/router.py`:**
   - Import `get_shapes_service` and `get_label_service` from `app.dependencies`
   - Import `ShapesService` from `app.services.shapes` and `LabelService` from `app.services.labels`
   - Import `logging` for warning-level error logging

2. **Implement `GET /api/canvas/properties` endpoint:**
   - Validate IRI via existing `_is_valid_iri()` — return 400 if invalid
   - Query `urn:sempkm:current` for `<IRI> ?p ?o` — extract `rdf:type` IRIs, `urn:sempkm:body`, and all other predicates
   - Query `urn:sempkm:inferred` for `<IRI> ?p ?o` — deduplicate against current, skip `rdf:type` and `urn:sempkm:body`
   - Resolve type: iterate `type_iris`, call `ShapesService.get_form_for_type(type_iri)` until a form is found
   - Resolve type label via `LabelService.resolve_batch(type_iris)` — use the first resolved label
   - Build property list from SHACL form `properties` (ordered by `sh:order`):
     - For each PropertyShape: look up values from `values` dict by `prop.path`
     - **Exclude** body properties: skip if `prop.name` and `prop.name.lower() == "body"`, also skip `urn:sempkm:body` predicate
     - Include only properties that have values in the graph
     - Each property entry: `{name: prop.name, path: prop.path, values: [...], datatype: prop.datatype, source: "current"}`
   - Append unmatched predicates (in graph but not in SHACL form) with local-name labels:
     - Local name: `iri.rsplit('#', 1)[-1]` or `iri.rsplit('/', 1)[-1]`
     - Skip well-known predicates: `rdf:type`, `urn:sempkm:body`, any predicate already matched by SHACL form
   - Append inferred properties tagged with `source: "inferred"`, same local-name fallback
   - Collect all IRI-type values (where `o.type == "uri"` in bindings), resolve labels via `LabelService.resolve_batch()`
   - Attach `ref_label` to property values that are IRIs with resolved labels
   - Return `{"type_label": str|null, "properties": [...]}`

3. **Track value types in bindings:**
   - When collecting values from SPARQL bindings, preserve whether each value is a URI or literal
   - URI values get `ref_label` resolution; literal values do not
   - For multi-value properties, `values` is an array of `{value, ref_label?, type?}` objects — or simplified to `{value, ref_label?}` for the frontend

4. **Write unit tests in `backend/tests/test_canvas_properties.py`:**
   - Use `pytest` + `httpx.AsyncClient` with FastAPI `TestClient` pattern (matching existing `test_canvas_resize.py` style), OR pure-function tests if the endpoint logic is extracted
   - **Better approach given the codebase pattern:** Extract the property-building logic into a helper function that takes query results + form + labels as input and returns the JSON structure. Test the helper as a pure function.
   - Tests:
     - **Happy path:** typed object with SHACL form → property list with names from form, ordered by sh:order
     - **No SHACL form:** untyped object → properties with local-name labels
     - **Body exclusion:** `urn:sempkm:body` and SHACL body property both excluded from output
     - **Multi-value:** property with multiple values returns array
     - **Inferred properties:** tagged with `source: "inferred"`, deduplicated against current
     - **Reference labels:** IRI values include resolved `ref_label`
     - **Invalid IRI:** returns 400 (test `_is_valid_iri` integration)
     - **Empty result:** non-existent IRI returns empty properties array with null type_label

## Must-Haves

- [ ] Endpoint returns correct JSON shape: `{type_label, properties: [{name, path, values, datatype, source, ref_label?}]}`
- [ ] Body properties excluded (both `urn:sempkm:body` and SHACL `name.lower() == "body"`)
- [ ] Inferred properties tagged with `source: "inferred"` and deduplicated
- [ ] IRI reference values include `ref_label` from LabelService
- [ ] Invalid IRI returns HTTP 400
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — all tests green
- No import errors: `cd backend && python -c "from app.canvas.router import router; print('OK')"`

## Observability Impact

- Signals added: new endpoint logs warnings on triplestore query failures (same pattern as objects.py)
- How a future agent inspects this: `curl /api/canvas/properties?iri=<IRI>` returns structured JSON
- Failure state exposed: 400 for invalid IRI, empty `properties` array for unknown IRI, warning logs for triplestore errors

## Inputs

- `backend/app/canvas/router.py` — existing canvas router with `_is_valid_iri()`, `get_triplestore_client` dependency
- `backend/app/browser/objects.py` lines 78-165 — reference query pattern for current + inferred graphs
- `backend/app/services/shapes.py` — `ShapesService.get_form_for_type()` returns `NodeShapeForm` with ordered `properties: list[PropertyShape]`
- `backend/app/dependencies.py` — `get_shapes_service`, `get_label_service` dependency providers
- `backend/tests/test_canvas_resize.py` — reference test pattern (pure-function tests, no Docker)

## Expected Output

- `backend/app/canvas/router.py` — extended with `GET /api/canvas/properties` endpoint and property-building helper
- `backend/tests/test_canvas_properties.py` — new file with 7-8 unit tests covering happy path, edge cases, and error cases
