---
estimated_steps: 5
estimated_files: 1
---

# T01: Implement GET /api/types endpoint

**Slice:** S02 — Types and Shapes JSON Endpoints
**Milestone:** M013

## Description

Build the `/api/types` endpoint that returns all available types from installed Mental Models with labels, Lucide icon names, icon colors, and model attribution. Combines data from ShapesService (types + labels), IconService (icon names/colors), and model IRI convention (model attribution).

## Steps

1. Read `backend/app/services/shapes.py` `get_types()` method to understand the return format (`[{iri, label}]`)
2. Read `backend/app/services/icons.py` `get_icon_map()` to understand how icons are keyed by type IRI
3. In `backend/app/api/router.py`, define Pydantic models: `TypeInfo(iri, label, icon, icon_color, model_id, model_name)` and `TypesResponse(types: list[TypeInfo])`
4. Implement `GET /api/types` endpoint on `api_surface_router`:
   - Get shapes from `request.app.state.shapes_service.get_types()`
   - Get icon map from `request.app.state.icon_service.get_icon_map("tree")`
   - For each type, extract model_id from IRI convention (`urn:sempkm:model:{model_id}:TypeName` → parse model_id)
   - Get model name from `request.app.state.model_service` registry if available
   - Merge all into TypeInfo list
5. Protect with `Depends(get_current_user_or_api)`

## Must-Haves

- [ ] Returns all types from all installed models
- [ ] Each type has IRI, label, icon name (Lucide), model attribution
- [ ] Protected by dual-auth dependency
- [ ] Returns empty list (not error) when no models installed

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "test_types"`
- After Docker: `curl -s http://localhost:3000/api/types | jq '.types | length'` returns > 0

## Inputs

- `backend/app/api/router.py` — router scaffolding from S01/T03
- `backend/app/services/shapes.py` — `ShapesService.get_types()` 
- `backend/app/services/icons.py` — `IconService.get_icon_map()`

## Expected Output

- `backend/app/api/router.py` — with `/api/types` endpoint and Pydantic models

## Observability Impact

- **New signal:** `GET /api/types` returns the complete set of loaded types, serving as a runtime inventory of installed models and their type registrations.
- **Inspection:** `curl /api/types | jq '.types | length'` shows how many types are loaded; empty list (`{"types": []}`) indicates no models installed rather than an error.
- **Failure shape:** Service exceptions from ShapesService or IconService propagate as HTTP 500 with stack trace in dev mode. Auth failures return 401 with `{"detail": "Not authenticated"}`.
- **Logging:** Existing `ShapesService` INFO-level logs report shapes graph fetch and extraction counts; no new log lines needed.
