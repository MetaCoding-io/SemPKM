---
estimated_steps: 6
estimated_files: 4
---

# T03: Implement /.well-known/sempkm endpoint

**Slice:** S01 — Dual-Auth, CORS, nginx fix, and Well-Known Endpoint
**Milestone:** M013

## Description

Create the `/.well-known/sempkm` discovery endpoint that external clients hit first to learn instance capabilities. This is the first endpoint using the dual-auth dependency, proving the full auth + proxy pipeline works.

## Steps

1. Create `backend/app/api/__init__.py` (empty)
2. Create `backend/app/api/router.py` with:
   - `well_known_router = APIRouter(tags=["api-discovery"])` for the `/.well-known/` endpoint
   - `api_surface_router = APIRouter(prefix="/api", tags=["api-surface"])` for future `/api/types`, `/api/shapes`, `/api/context-query` endpoints
3. Implement `GET /.well-known/sempkm` on `well_known_router`:
   - Depends on `get_current_user_or_api` from T01
   - Returns Pydantic model `InstanceInfo` with fields: `version: str`, `endpoints: dict`, `auth: dict`, `capabilities: list[str]`
   - Populate version from a constant (e.g. `"2.6.0"`)
   - Endpoints dict: `{"types": "/api/types", "shapes": "/api/shapes/{type_iri}", "context_query": "/api/context-query", "sparql": "/api/sparql", "commands": "/api/commands"}`
   - Auth dict: `{"session": True, "api_key": True, "indieauth": "/auth/authorize"}`
   - Capabilities list: `["types", "shapes", "context-query", "sparql", "commands"]`
4. Wire routers into `backend/app/main.py`: include `well_known_router` at root level and `api_surface_router` (empty for now, S02 adds endpoints)
5. Add `APP_VERSION = "2.6.0"` constant to `backend/app/config.py` or as a module-level constant in `api/router.py`
6. Verify the endpoint returns correct JSON by running the unit tests from T04

## Must-Haves

- [ ] `GET /.well-known/sempkm` returns JSON with version, endpoints, auth, capabilities
- [ ] Endpoint requires authentication (either session cookie or Bearer token)
- [ ] Response uses Pydantic model for OpenAPI documentation
- [ ] Router wired into main.py app

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "well_known"`
- After Docker restart: `curl http://localhost:3000/.well-known/sempkm` returns JSON (with session cookie)

## Inputs

- `backend/app/auth/dependencies.py` — `get_current_user_or_api` from T01
- `backend/app/main.py` — router registration pattern from existing modules

## Expected Output

- `backend/app/api/__init__.py` — new module
- `backend/app/api/router.py` — well-known endpoint + api surface router
- `backend/app/main.py` — updated with new router includes
