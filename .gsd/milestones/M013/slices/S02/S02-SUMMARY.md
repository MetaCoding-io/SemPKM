---
id: S02
parent: M013
milestone: M013
provides:
  - GET /api/types endpoint returning all installed model types with labels, Lucide icons, icon colors, and model attribution
  - GET /api/shapes/{type_iri} endpoint returning SHACL property shapes as structured JSON (properties, groups, constraints, helptext)
  - TypeInfo, TypesResponse, PropertyShapeInfo, PropertyGroupInfo, ShapeResponse Pydantic response models for OpenAPI docs
  - _extract_model_id helper parsing model_id from type IRI convention
requires:
  - slice: S01
    provides: get_current_user_or_api dual-auth dependency, CORS headers, nginx Authorization forwarding, api_surface_router wired into main.py
affects:
  - S03
key_files:
  - backend/app/api/router.py
  - backend/tests/test_api_surface.py
key_decisions:
  - D160 — Shape serialization via dataclasses.asdict() to Pydantic models (no ShapesService refactor)
  - D164 — IconService created ad-hoc in endpoint handler matching codebase pattern (not app.state)
patterns_established:
  - API endpoint pattern: merge data from ShapesService + IconService + ModelService with mock-based test fixtures
  - Shape serialization: dataclass → asdict() → Pydantic model via **kwargs unpacking
  - IconService ad-hoc instantiation with user_type_icons overlay from app.state
observability_surfaces:
  - GET /api/types response serves as runtime inventory of all loaded models and types
  - GET /api/shapes/{type_iri} returns full SHACL property shapes for runtime inspection
  - 404 with structured detail "No shape found for type: <iri>" on unknown types
  - Auth failures return 401 JSON; service errors propagate as 500 in dev mode
drill_down_paths:
  - .gsd/milestones/M013/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013/slices/S02/tasks/T03-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-17
---

# S02: Types and Shapes JSON Endpoints

**Shipped GET /api/types (type inventory with icons and model attribution) and GET /api/shapes/{type_iri} (SHACL property shapes as structured JSON) — proving ShapesService dataclasses serialize cleanly to JSON for external clients**

## What Happened

Three tasks delivered two new endpoints on the `api_surface_router`, both protected by the S01 dual-auth dependency:

**T01 — GET /api/types:** Merges data from three services — ShapesService (type IRIs + labels), IconService (Lucide icon names + colors), and ModelService (model name lookup). The `_extract_model_id()` helper parses model_id from the `urn:sempkm:model:{id}:TypeName` convention via regex. Returns `TypesResponse` with a list of `TypeInfo` Pydantic models. Empty list (not error) when no models installed. 8 tests cover schema, fields, icons, model attribution, auth, and empty state.

**T02 — GET /api/shapes/{type_iri:path}:** Calls `ShapesService.get_form_for_type()` which returns a `NodeShapeForm` dataclass. Converts via `dataclasses.asdict()` → Pydantic models (`PropertyShapeInfo`, `PropertyGroupInfo`, `ShapeResponse`). Returns 404 with structured detail for unknown types. 11 tests cover schema, fields, constraint round-trip (in_values, min/max_count), target_class, group ordering, helptext, 404, and auth.

**T03 — Test enhancement:** Hardened field-completeness assertions in both test classes. `test_types_entries_have_required_fields` now asserts all 6 TypeInfo fields. `test_shapes_property_fields` asserts all 6 key fields with type validation.

**Runtime fix:** T03 discovered that `/api/types` returned 500 at runtime because `IconService` was expected on `app.state` but is never registered there. Fixed during slice completion by creating `IconService` ad-hoc in the endpoint handler (matching the codebase pattern used in admin router, browser helpers, and SPARQL router). Test fixtures updated to patch `IconService` via `unittest.mock.patch` instead of `app.state`. Decision D164 records this pattern.

## Verification

- `pytest tests/test_api_surface.py -v -k "types or shapes"` — 19 passed (8 types + 11 shapes)
- `pytest tests/test_api_surface.py -v` — 44 passed (25 S01 + 19 S02), zero regressions
- `pytest tests/ --tb=short -q` — 990 passed, zero failures, zero regressions
- All Pydantic response models documented via OpenAPI (TypeInfo, TypesResponse, PropertyShapeInfo, PropertyGroupInfo, ShapeResponse)
- Auth enforcement: 401 without credentials on both endpoints
- 404 with structured detail `"No shape found for type: urn:nonexistent:Type"` on unknown shapes

## Requirements Advanced

- API-02 — validated: 8 unit tests confirm types JSON array with icons, model attribution, auth, and empty state
- API-03 — validated: 11 unit tests confirm shapes JSON with constraints, groups, helptext, target_class, 404, and auth

## Requirements Validated

- API-02 — GET /api/types returns structured JSON with all TypeInfo fields. 8 unit tests passing.
- API-03 — GET /api/shapes/{type_iri} returns structured JSON matching SHACL form editor fields. 11 unit tests passing. Shape serialization fidelity (key M013 risk) proven via constraint round-trip tests.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **IconService runtime fix:** T01-T02 executor assumed `IconService` would be on `app.state.icon_service`. It isn't — the codebase creates it ad-hoc everywhere. Fixed during slice completion by following the established pattern. Tests updated to use `unittest.mock.patch` instead of `app.state` mocking.
- **Test timing:** Most tests were written during T01/T02 rather than T03. T03 enhanced field-completeness assertions rather than writing from scratch.

## Known Limitations

- `/api/types` creates `IconService` from `/app/models` directory — requires Docker volume mount to find model icon manifests at runtime. In development without Docker, icon data returns `None` for all types.
- Model ID extraction relies on IRI naming convention (`urn:sempkm:model:{id}:TypeName`). Types from user-created classes or non-standard IRIs will have `model_id: null`.

## Follow-ups

- S03 context-query endpoint can reuse `TypeInfo` for enriching results with type labels and icons
- S03 E2E tests should exercise both endpoints through real Docker stack with actual SHACL shapes
- Pydantic response models provide OpenAPI documentation — S03 user guide should reference the auto-generated schema

## Files Created/Modified

- `backend/app/api/router.py` — Added TypeInfo, TypesResponse, PropertyShapeInfo, PropertyGroupInfo, ShapeResponse Pydantic models; _extract_model_id helper; GET /api/types endpoint; GET /api/shapes/{type_iri:path} endpoint; IconService import and ad-hoc instantiation
- `backend/tests/test_api_surface.py` — Added 19 tests across TestTypesEndpoint (8) and TestShapesEndpoint (11) classes; updated fixtures to patch IconService via unittest.mock.patch

## Forward Intelligence

### What the next slice should know
- Both endpoints are fully functional and tested. S03 can depend on TypeInfo and ShapeResponse models for enriching context-query results.
- The `api_surface_router` is already wired into `main.py` from S01. S03 just adds the context-query endpoint to the same router.
- Pydantic models provide OpenAPI docs at `/docs` — useful for the user guide task.

### What's fragile
- IconService ad-hoc creation from `/app/models` path — if the models directory structure changes, icon lookup breaks silently (returns None). Not a crash, but icons disappear.
- `_extract_model_id` regex depends on `urn:sempkm:model:{id}:` IRI convention. User-created types have different IRI patterns and will return `model_id: null`.

### Authoritative diagnostics
- `pytest tests/test_api_surface.py -v -k "types or shapes"` — 19 tests, <1s, authoritative for endpoint correctness
- `curl -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '.types | length'` — runtime type count
- `curl http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | jq '.properties | length'` — runtime shape fidelity check

### What assumptions changed
- Original assumption: IconService available on app.state → Actually: IconService created ad-hoc everywhere (D164)
- Original risk: Shape serialization might have edge cases → Retired: dataclasses.asdict() + Pydantic handles all fields cleanly including None, empty lists, and nested groups
