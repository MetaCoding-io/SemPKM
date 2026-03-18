---
id: T01
parent: S02
milestone: M013
provides:
  - GET /api/types endpoint returning all installed model types with labels, icons, and model attribution
  - TypeInfo and TypesResponse Pydantic response models for OpenAPI docs
  - _extract_model_id helper for IRI-to-model-id parsing
key_files:
  - backend/app/api/router.py
  - backend/tests/test_api_surface.py
key_decisions:
  - Parse model_id from type IRI convention (urn:sempkm:model:{id}:TypeName) via regex rather than querying the triplestore
patterns_established:
  - API endpoint pattern: merge data from ShapesService + IconService + ModelService with mock-based test fixtures
observability_surfaces:
  - GET /api/types response serves as runtime inventory of loaded models and types
  - Empty list response (not error) when no models installed
  - Auth failures return 401; service errors propagate as 500 in dev mode
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Implement GET /api/types endpoint

**Added GET /api/types endpoint that returns all installed model types with labels, Lucide icons, and model attribution**

## What Happened

Implemented the `/api/types` endpoint on `api_surface_router` in `backend/app/api/router.py`. The endpoint merges data from three services:

1. **ShapesService.get_types()** — provides type IRIs and labels from SHACL shapes graphs
2. **IconService.get_icon_map("tree")** — provides Lucide icon names and colors per type IRI
3. **ModelService.list_models()** — provides model name lookup for attribution (model_id parsed from IRI convention)

Defined Pydantic models `TypeInfo` (iri, label, icon, icon_color, model_id, model_name) and `TypesResponse` (types list) for OpenAPI schema generation. Protected the endpoint with `Depends(get_current_user_or_api)` for dual-auth (session cookie or Bearer token).

Added 8 tests covering: list response shape, required fields, icon presence/absence, model attribution, auth enforcement (cookie, Bearer, unauthenticated), and empty-state behavior.

## Verification

All 8 new tests pass. All 33 tests in the file pass (25 existing + 8 new). Slice-level `pytest -k "types or shapes"` returns 8 passed — shapes tests will be added in T02/T03.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "test_types"` | 0 | ✅ pass | 0.52s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 0.78s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "types or shapes"` | 0 | ✅ pass | 0.52s |

## Diagnostics

- **Inspect types at runtime:** `curl -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '.types | length'`
- **Empty state:** When no models are installed, returns `{"types": []}` (not an error)
- **Auth failures:** Returns 401 with `{"detail": "Not authenticated"}`
- **Service errors:** ShapesService/IconService exceptions propagate as 500 with stack trace in dev mode; ModelService errors are caught and logged (types still returned without model names)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/router.py` — Added TypeInfo, TypesResponse Pydantic models; _extract_model_id helper; GET /api/types endpoint
- `backend/tests/test_api_surface.py` — Added 8 tests in TestTypesEndpoint class with mock service fixtures
- `.gsd/milestones/M013/slices/S02/S02-PLAN.md` — Marked T01 done; added failure-path verification step
- `.gsd/milestones/M013/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section
