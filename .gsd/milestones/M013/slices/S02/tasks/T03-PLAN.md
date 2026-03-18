---
estimated_steps: 3
estimated_files: 1
---

# T03: Unit tests for types and shapes endpoints

**Slice:** S02 — Types and Shapes JSON Endpoints
**Milestone:** M013

## Description

Add unit tests for the types and shapes endpoints to verify response schemas, edge cases (no models, unknown type), and constraint serialization fidelity. Shape serialization is a key risk — tests confirm PropertyShape fields round-trip correctly from dataclass → Pydantic → JSON.

## Steps

1. Add types endpoint tests to `backend/tests/test_api_surface.py`:
   - `test_types_returns_list` — response has `types` key with list value
   - `test_types_entries_have_required_fields` — each entry has iri, label, icon, model_id
   - `test_types_requires_auth` — no credentials → 401
   - Mock ShapesService.get_types() and IconService.get_icon_map() with known test data
2. Add shapes endpoint tests:
   - `test_shapes_valid_type` — known type returns 200 with properties array
   - `test_shapes_property_fields_complete` — each property has path, name, order, datatype, min_count, max_count
   - `test_shapes_unknown_type_404` — nonexistent IRI → 404 with clear message
   - `test_shapes_in_values_serialized` — properties with `in_values` list serialize correctly
   - `test_shapes_groups_included` — response includes groups with iri, label, order
   - `test_shapes_requires_auth` — no credentials → 401
   - Mock ShapesService.get_form_for_type() returning a NodeShapeForm with known data
3. Run full test suite: `python -m pytest tests/ --tb=short -q`

## Must-Haves

- [ ] ≥4 tests for types endpoint
- [ ] ≥6 tests for shapes endpoint
- [ ] All mock ShapesService/IconService data exercises real field structures
- [ ] No regressions in existing test suite

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "types or shapes"` — all green
- `cd backend && python -m pytest tests/ --tb=short -q` — no regressions

## Inputs

- `backend/app/api/router.py` — endpoints from T01 and T02
- `backend/tests/test_api_surface.py` — existing test file from S01/T04
- `backend/app/services/shapes.py` — dataclass definitions for mock data construction

## Expected Output

- `backend/tests/test_api_surface.py` — expanded with ≥10 new tests for types and shapes
