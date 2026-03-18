---
id: T02
parent: S02
milestone: M013
provides:
  - GET /api/shapes/{type_iri} endpoint returning SHACL property shapes as structured JSON
  - PropertyShapeInfo, PropertyGroupInfo, and ShapeResponse Pydantic response models for OpenAPI docs
key_files:
  - backend/app/api/router.py
  - backend/tests/test_api_surface.py
key_decisions:
  - Use dataclasses.asdict() to convert ShapesService dataclasses to Pydantic models — fields match 1:1 so no manual mapping needed
patterns_established:
  - Shape serialization pattern: dataclass → asdict() → Pydantic model via **kwargs unpacking
observability_surfaces:
  - GET /api/shapes/{type_iri} returns full SHACL property shapes as JSON for runtime inspection
  - 404 with structured detail "No shape found for type: <iri>" for unknown types
  - Auth failures return 401; ShapesService errors propagate as 500 in dev mode
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Implement GET /api/shapes/{type_iri} endpoint

**Added GET /api/shapes/{type_iri} endpoint that serializes SHACL property shapes, groups, and constraints to structured JSON via Pydantic models**

## What Happened

Implemented the `/api/shapes/{type_iri:path}` endpoint on `api_surface_router` in `backend/app/api/router.py`. The endpoint:

1. Accepts a type IRI as a path parameter (FastAPI `:path` converter handles URL-encoded colons)
2. Calls `ShapesService.get_form_for_type(type_iri)` which returns a `NodeShapeForm` dataclass or `None`
3. Returns 404 with structured detail message if no shape found
4. Converts `NodeShapeForm` → `ShapeResponse` via `dataclasses.asdict()` + Pydantic model unpacking

Defined three Pydantic models: `PropertyShapeInfo` (12 fields matching PropertyShape dataclass), `PropertyGroupInfo` (iri, label, order), and `ShapeResponse` (wrapping shape_iri, target_class, label, groups, properties, helptext). All constraint fields (in_values, min_count, max_count, default_value) serialize correctly.

Added 11 tests covering: valid JSON response, top-level fields, property count, field presence, constraint round-trip (in_values, min/max_count), target_class on object references, group ordering, 404 for unknown types, auth enforcement (cookie + Bearer), and property-level helptext.

## Verification

All 11 shapes tests pass. Full slice-level verification `pytest -k "types or shapes"` returns 19 passed (8 types + 11 shapes). Full file runs 44 tests with zero failures and zero regressions.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "test_shapes"` | 0 | ✅ pass | 0.68s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "types or shapes"` | 0 | ✅ pass | 0.82s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 1.11s |

## Diagnostics

- **Inspect shapes at runtime:** `curl -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | jq '.properties | length'`
- **404 on unknown type:** `curl -s http://localhost:3000/api/shapes/urn:nonexistent:Type | jq '.detail'` → `"No shape found for type: urn:nonexistent:Type"`
- **Auth failures:** Returns 401 with `{"detail": "Not authenticated"}`
- **Service errors:** ShapesService exceptions propagate as 500 with stack trace in dev mode

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/router.py` — Added PropertyShapeInfo, PropertyGroupInfo, ShapeResponse Pydantic models; GET /api/shapes/{type_iri:path} endpoint with 404 handling and asdict() conversion
- `backend/tests/test_api_surface.py` — Added 11 tests in TestShapesEndpoint class with sample NodeShapeForm fixture data
- `.gsd/milestones/M013/slices/S02/S02-PLAN.md` — Marked T02 done; added failure-path verification step
- `.gsd/milestones/M013/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section
