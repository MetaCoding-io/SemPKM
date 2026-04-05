---
estimated_steps: 21
estimated_files: 3
skills_used: []
---

# T01: Add compatible-types endpoint and filter types by renderer

Add a `get_compatible_types(renderer, exclude_iris)` method to ViewSpecService that leverages the existing `_detect_status_field()`, `_detect_date_fields()`, and `_detect_geo_fields()` methods to return only types whose SHACL shapes are compatible with a given renderer.

Then add a new endpoint `GET /browser/views/compatible-types?renderer=kanban` that returns JSON `{types: [{iri, label}]}`. Update `generic_view()` to call `get_compatible_types()` instead of `shapes_service.get_types()` so templates receive the already-filtered list.

**Renderer compatibility rules:**
- `table`, `card`, `graph`: all types (no filtering)
- `kanban`: types where `_detect_status_field(type_iri)` returns non-None
- `calendar`, `timeline`: types where `_detect_date_fields(type_iri)` returns non-None start field
- `map`: types where `_detect_geo_fields(type_iri)` returns non-None pair
- `quadrant`, `bmc`, `okr`, `decision-matrix`: all types (model-declared renderers, rare usage)

**Steps:**
1. Read `backend/app/views/service.py` — understand `_detect_status_field`, `_detect_date_fields`, `_detect_geo_fields` signatures
2. Add `async def get_compatible_types(self, renderer: str, exclude_iris: set[str] | None = None) -> list[dict]` to `ViewSpecService`:
   - Call `self._shapes_service.get_types(exclude_iris=exclude_iris)` to get all types
   - For `kanban`: iterate types, call `_detect_status_field(t['iri'])`, keep only those returning non-None
   - For `calendar`/`timeline`: iterate types, call `_detect_date_fields(t['iri'])`, keep only those with start_field
   - For `map`: iterate types, call `_detect_geo_fields(t['iri'])`, keep only those returning non-None pair
   - For all other renderers: return all types unfiltered
   - Log `compatible_types: renderer=%s total=%d compatible=%d`
3. Add `GET /browser/views/compatible-types?renderer=table` endpoint to `backend/app/views/router.py` that calls `get_compatible_types()`
4. In `generic_view()`, replace `types_list = await shapes_service.get_types(...)` with `types_list = await view_spec_service.get_compatible_types(renderer, ...)`
5. Add unit test `backend/tests/test_compatible_types.py` that mocks ShapesService to return a set of types, then verifies kanban filtering returns only status-field types
6. Run tests to verify

## Inputs

- ``backend/app/views/service.py` — existing _detect_status_field, _detect_date_fields, _detect_geo_fields methods`
- ``backend/app/views/router.py` — existing generic_view() and type_pills() endpoints`
- ``backend/app/services/shapes.py` — ShapesService.get_types() and get_form_for_type()`

## Expected Output

- ``backend/app/views/service.py` — new get_compatible_types() method`
- ``backend/app/views/router.py` — new /views/compatible-types endpoint, updated generic_view()`
- ``backend/tests/test_compatible_types.py` — unit tests for renderer-specific type filtering`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_compatible_types.py -v

## Observability Impact

Adds structured log line `compatible_types: renderer=%s total=%d compatible=%d` on the new endpoint and inside get_compatible_types(). GET /browser/views/compatible-types?renderer=kanban returns JSON for inspection.
