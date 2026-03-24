---
id: T01
parent: S04
milestone: M037
provides:
  - ContextZone SQLAlchemy model with CRUD service and API
  - Alembic migration 020 for context_zones table
  - Zone CRUD API at /api/context/zones (GET, POST, PUT, DELETE)
  - Pydantic validation for lat/lon/radius bounds
key_files:
  - backend/app/context/zone_models.py
  - backend/app/context/zone_service.py
  - backend/app/context/zone_router.py
  - backend/migrations/versions/020_context_zones.py
  - backend/tests/test_zone_service.py
  - backend/tests/test_zone_router.py
key_decisions:
  - Zone data stored in SQLite per D336 privacy-by-design
  - ZoneService follows same async_sessionmaker pattern as ContextService and RulesEngine
patterns_established:
  - Service tests with FK to users table need `import app.auth.models` for Base.metadata resolution
observability_surfaces:
  - context.zone_crud structured log on create/update/delete
  - GET /api/context/zones inspection endpoint
  - Standard 401/404/422 error responses
duration: 12 min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Backend zone model, migration 020, and CRUD API with tests

**Add ContextZone model, migration 020, ZoneService CRUD, and /api/context/zones router with 44 passing tests**

## What Happened

Built the full backend zone storage stack following the established context rules pattern:

1. **ContextZone model** (`zone_models.py`): UUID PK, user_id FK with CASCADE, name (100), lat/lon (Float), radius_meters (Float, default 200), enabled (Boolean, default True), created_at/updated_at timestamps. Index on user_id.

2. **Migration 020** (`020_context_zones.py`): Creates `context_zones` table chaining from revision 019. Includes index on user_id and both upgrade/downgrade functions.

3. **ZoneService** (`zone_service.py`): Full CRUD — create, list_for_user, get, update, delete. All methods scoped by user_id for tenant isolation. Structured `context.zone_crud` logging on mutations.

4. **Zone router** (`zone_router.py`): 4 endpoints at `/api/context/zones` — GET list, POST create (201), PUT update, DELETE (204). Pydantic validation enforces lat (-90,90), lon (-180,180), radius (50-10000). Auth via `get_current_user_or_api`.

5. **Wiring**: ZoneService registered on `app.state` in main.py lifespan, `get_zone_service` dependency in dependencies.py, router included in app.

## Verification

- `test_zone_service.py`: 18/18 passed — covers create, list, get, update, delete, user isolation, missing zone returns None, wrong-user returns None/False
- `test_zone_router.py`: 26/26 passed — covers all CRUD endpoints, auth enforcement, Pydantic validation (lat/lon/radius bounds, empty name), 404 handling, boundary values
- Migration chain: `rg "down_revision.*019"` confirms correct chaining

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py -v` | 0 | ✅ pass | 0.42s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_zone_router.py -v` | 0 | ✅ pass | 0.69s |
| 3 | `rg "down_revision.*019" backend/migrations/versions/020_context_zones.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Zone state**: `GET /api/context/zones` with auth header returns all zones for the user
- **Mutation logs**: `grep "context.zone_crud" <logfile>` shows action, user_id, zone_id, fields
- **Errors**: 422 for invalid coordinates/radius, 404 for missing zone, 401 for unauthenticated

## Deviations

- Service tests required `import app.auth.models` (noqa: F401) to register the `users` table in Base.metadata so `create_all` can resolve the FK. This is a known SQLAlchemy in-memory test pattern — the existing `test_context_service.py` has the same latent issue but wasn't caught because it wasn't recently run.

## Known Issues

None.

## Files Created/Modified

- `backend/app/context/zone_models.py` — ContextZone SQLAlchemy model with all specified fields
- `backend/app/context/zone_service.py` — ZoneService with CRUD methods scoped by user_id
- `backend/app/context/zone_router.py` — Zone CRUD API router (4 endpoints, Pydantic validation)
- `backend/migrations/versions/020_context_zones.py` — Alembic migration chaining from 019
- `backend/app/main.py` — modified: zone_service on app.state, zone_router included
- `backend/app/dependencies.py` — modified: get_zone_service dependency added
- `backend/tests/test_zone_service.py` — 18 service unit tests (in-memory SQLite)
- `backend/tests/test_zone_router.py` — 26 router unit tests (httpx + mocks)
- `.gsd/milestones/M037/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
