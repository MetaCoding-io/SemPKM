# S02: Types and Shapes JSON Endpoints

**Goal:** Ship `GET /api/types` and `GET /api/shapes/{type_iri}` endpoints that return structured JSON from ShapesService, IconService, and LabelService — proving that existing service-layer data serializes cleanly to JSON for external clients.
**Demo:** `curl localhost:3000/api/types` returns all installed model types with labels, icons, and model attribution. `curl localhost:3000/api/shapes/<Note_IRI>` returns property shapes matching the SHACL form editor's fields.

## Must-Haves

- `GET /api/types` returns JSON array of types with: IRI, label, icon (Lucide name), model name, model ID
- `GET /api/shapes/{type_iri}` returns JSON with: shape IRI, target class, label, groups (IRI, label, order), properties (path, name, datatype, constraints, helptext, order, group)
- Both endpoints use `get_current_user_or_api` from S01
- Unknown type IRI on shapes endpoint returns 404 with clear error message
- Pydantic response models for OpenAPI documentation
- Unit tests for both endpoints including edge cases

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "types or shapes"` — unit tests pass
- `curl http://localhost:3000/api/types` — returns JSON array with types from installed models
- `curl http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note` — returns JSON with property shapes matching the form editor
- `curl http://localhost:3000/api/shapes/urn:nonexistent:Type` — returns 404 with `{"detail": "No shape found for type: urn:nonexistent:Type"}`
- `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/types` without credentials — returns 401 (auth enforcement)
- `curl -s http://localhost:3000/api/shapes/urn:nonexistent:Type | jq '.detail'` — returns structured error `"No shape found for type: urn:nonexistent:Type"` (failure-path diagnostic)

## Observability / Diagnostics

- Runtime signals: 404 with `"detail": "No shape found for type: <iri>"` on unknown type; standard JSON error responses
- Inspection surfaces: `/api/types` response shows all loaded models and types at a glance
- Failure visibility: ShapesService exceptions propagate as 500 with stack trace in dev mode
- Redaction constraints: none — type/shape data is not sensitive

## Tasks

- [x] **T01: Implement GET /api/types endpoint** `est:40m`
  - Why: External clients need to know what types are available before they can create objects or request shapes. This endpoint combines ShapesService (type IRIs + labels), IconService (icon names), and model registry (model attribution) into a single JSON response.
  - Files: `backend/app/api/router.py`
  - Do:
    1. Define Pydantic response model `TypeInfo`: `iri: str`, `label: str`, `icon: str | None`, `icon_color: str | None`, `model_id: str | None`, `model_name: str | None`
    2. Define `TypesResponse`: `types: list[TypeInfo]`
    3. Implement `GET /api/types` on `api_surface_router`:
       - Get ShapesService from `request.app.state.shapes_service`
       - Call `shapes_service.get_types()` to get `[{iri, label}]`
       - Get IconService icon map from `request.app.state.icon_service.get_icon_map("tree")` for icon names
       - Get model registry from `request.app.state.model_service` to map type IRI → model ID/name (type IRI prefix `urn:sempkm:model:{model_id}:` encodes model)
       - Merge into `TypeInfo` objects and return
    4. Endpoint requires `Depends(get_current_user_or_api)`
  - Verify: `python -m pytest tests/test_api_surface.py -v -k "test_types"`
  - Done when: Endpoint returns JSON array with at least Note, Project, Person, Concept types (from basic-pkm) with labels and icons

- [x] **T02: Implement GET /api/shapes/{type_iri} endpoint** `est:45m`
  - Why: External clients (browser extension) need SHACL property shapes as structured JSON to dynamically render capture forms. ShapesService already extracts this data as Python dataclasses — this endpoint serializes them to JSON.
  - Files: `backend/app/api/router.py`
  - Do:
    1. Define Pydantic response models:
       - `PropertyShapeInfo`: `path: str`, `name: str`, `datatype: str | None`, `target_class: str | None`, `order: float`, `group: str | None`, `min_count: int`, `max_count: int | None`, `in_values: list[str]`, `default_value: str | None`, `description: str | None`, `helptext: str | None`
       - `PropertyGroupInfo`: `iri: str`, `label: str`, `order: float`
       - `ShapeResponse`: `shape_iri: str`, `target_class: str`, `label: str`, `groups: list[PropertyGroupInfo]`, `properties: list[PropertyShapeInfo]`, `helptext: str | None`
    2. Implement `GET /api/shapes/{type_iri:path}` on `api_surface_router`:
       - URL-decode `type_iri` (FastAPI handles this with `:path` converter)
       - Get ShapesService from `request.app.state.shapes_service`
       - Call `shapes_service.get_form_for_type(type_iri)` which returns `NodeShapeForm | None`
       - If None, raise HTTPException 404 with detail `"No shape found for type: {type_iri}"`
       - Convert `NodeShapeForm` → `ShapeResponse` by mapping dataclass fields to Pydantic model
    3. Endpoint requires `Depends(get_current_user_or_api)`
  - Verify: `python -m pytest tests/test_api_surface.py -v -k "test_shapes"`
  - Done when: Endpoint returns property shapes for basic-pkm Note type matching the fields in the SHACL form editor (title, body, tags, etc.)

- [x] **T03: Unit tests for types and shapes endpoints** `est:30m`
  - Why: Verify response schemas and edge cases without Docker. Shape serialization fidelity is a key risk — tests confirm all PropertyShape fields round-trip correctly.
  - Files: `backend/tests/test_api_surface.py`
  - Do:
    1. Add types endpoint tests:
       - `test_types_returns_list` — response is JSON array
       - `test_types_entries_have_required_fields` — each entry has iri, label
       - `test_types_includes_icon_data` — entries with known icons have icon field set
       - `test_types_requires_auth` — 401 without credentials
    2. Add shapes endpoint tests:
       - `test_shapes_returns_valid_json` — known type returns 200 with JSON
       - `test_shapes_has_properties` — response has non-empty properties list
       - `test_shapes_property_fields` — each property has path, name, order at minimum
       - `test_shapes_unknown_type_returns_404` — unknown IRI returns 404
       - `test_shapes_preserves_constraints` — in_values, min_count, max_count round-trip correctly
       - `test_shapes_requires_auth` — 401 without credentials
    3. Use mock ShapesService and IconService returning known test data, following existing test patterns from conftest.py
  - Verify: `cd backend && python -m pytest tests/test_api_surface.py -v -k "types or shapes"` — all tests green
  - Done when: ≥10 new tests covering both endpoints with edge cases

## Files Likely Touched

- `backend/app/api/router.py` — types and shapes endpoints with Pydantic models
- `backend/tests/test_api_surface.py` — additional unit tests
