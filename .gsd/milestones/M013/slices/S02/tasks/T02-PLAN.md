---
estimated_steps: 4
estimated_files: 1
---

# T02: Implement GET /api/shapes/{type_iri} endpoint

**Slice:** S02 — Types and Shapes JSON Endpoints
**Milestone:** M013

## Description

Build the `/api/shapes/{type_iri}` endpoint that returns SHACL property shapes as structured JSON. ShapesService already extracts this data as Python dataclasses (NodeShapeForm, PropertyShape, PropertyGroup) — this endpoint serializes them to JSON via Pydantic models. The response must match exactly what the SHACL form generator uses.

## Steps

1. Read `backend/app/services/shapes.py` `_extract_node_shape()` and `get_form_for_type()` to understand the NodeShapeForm structure (shape_iri, target_class, label, groups, properties, helptext)
2. Define Pydantic response models in `backend/app/api/router.py`:
   - `PropertyShapeInfo` with all fields from the PropertyShape dataclass (path, name, datatype, target_class, order, group, min_count, max_count, in_values, default_value, description, helptext)
   - `PropertyGroupInfo` with fields from PropertyGroup (iri, label, order)
   - `ShapeResponse` wrapping them (shape_iri, target_class, label, groups, properties, helptext)
3. Implement `GET /api/shapes/{type_iri:path}` on `api_surface_router`:
   - Call `shapes_service.get_form_for_type(type_iri)` — returns `NodeShapeForm | None`
   - If None, raise HTTPException 404
   - Convert dataclass fields to Pydantic model (direct field mapping, dataclasses.asdict() or manual)
4. Protect with `Depends(get_current_user_or_api)`

## Must-Haves

- [ ] Returns all property shapes for a known type with correct field values
- [ ] Groups included with correct ordering
- [ ] Returns 404 for unknown type IRIs
- [ ] Constraint fields (in_values, min_count, max_count) are correctly serialized

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "test_shapes"`
- After Docker: `curl -s http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | jq '.properties | length'` returns > 0

## Inputs

- `backend/app/api/router.py` — router from S01/T03 with types endpoint from T01
- `backend/app/services/shapes.py` — `ShapesService.get_form_for_type()`, `NodeShapeForm`, `PropertyShape`, `PropertyGroup` dataclasses

## Expected Output

- `backend/app/api/router.py` — with `/api/shapes/{type_iri}` endpoint and shape Pydantic models
