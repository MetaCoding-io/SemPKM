---
estimated_steps: 5
estimated_files: 8
skills_used:
  - test
---

# T01: Backend zone model, migration 020, and CRUD API with tests

**Slice:** S04 — Mobile Geofencing & Location Zones
**Milestone:** M037

## Description

Create the server-side zone storage and CRUD API. This follows the exact pattern established by S02's `context_rules`: SQLAlchemy model → Alembic migration → service with CRUD methods → FastAPI router with auth → dependency injection wiring → pytest tests.

Zone data is stored in SQLite (not RDF) per D336 (privacy-by-design for coordinates). One zone = one circular geofence with name, center (lat/lon), radius in meters, and enabled flag. Zones are scoped to the authenticated user.

## Steps

1. **Create `ContextZone` model** in `backend/app/context/zone_models.py`. Fields: `id` (UUID PK), `user_id` (FK to `users.id` CASCADE), `name` (String 100, not null), `latitude` (Float, not null), `longitude` (Float, not null), `radius_meters` (Float, default 200, not null), `enabled` (Boolean, default True), `created_at` (DateTime timezone, server_default now), `updated_at` (DateTime timezone, server_default now, onupdate now). Index on `user_id`. Follow `ContextRule` model in `rules_models.py` as the template.

2. **Create Alembic migration 020** in `backend/migrations/versions/020_context_zones.py`. Chain from `down_revision = "019"`. Create `context_zones` table matching the model. Include index on `user_id`. Provide both `upgrade()` and `downgrade()` functions.

3. **Create `ZoneService`** in `backend/app/context/zone_service.py`. Methods: `create(user_id, name, latitude, longitude, radius_meters, enabled) → zone`, `list_for_user(user_id) → list[zone]`, `get(zone_id, user_id) → zone | None`, `update(zone_id, user_id, **fields) → zone | None`, `delete(zone_id, user_id) → bool`. All methods scoped to `user_id` for isolation. Uses `async_sessionmaker` pattern from `ContextService`.

4. **Create zone router** in `backend/app/context/zone_router.py` with 4 endpoints at prefix `/api/context/zones`. Pydantic models: `ZoneCreateRequest` (name 1-100 chars, latitude -90 to 90, longitude -180 to 180, radius_meters 50-10000 default 200, enabled default True), `ZoneUpdateRequest` (all optional). Endpoints: `GET /` → list, `POST /` → create (201), `PUT /{zone_id}` → update, `DELETE /{zone_id}` → delete (204). Auth via `get_current_user_or_api`. Follow `rules_router.py` pattern exactly. Include `_zone_to_dict()` serializer.

5. **Wire into app** — Register `zone_service` on `app.state` in `main.py` lifespan, add `get_zone_service` dependency in `dependencies.py`, import and `include_router(zone_router)` in `main.py`. Write `test_zone_service.py` (in-memory SQLite: create, list, get, update, delete, user isolation, missing zone returns None) and `test_zone_router.py` (httpx AsyncClient with mocked service: auth, validation, 404, user isolation, correct status codes) following `test_context_service.py` and `test_rules_router.py` patterns.

## Must-Haves

- [ ] `ContextZone` model with all specified fields and FK/index
- [ ] Migration 020 chains from 019, creates table, has downgrade
- [ ] `ZoneService` CRUD methods all scoped by user_id
- [ ] Router returns 201 on create, 204 on delete, 404 on missing
- [ ] Pydantic validation on lat (-90,90), lon (-180,180), radius (50-10000)
- [ ] All pytest tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py -v` — all pass
- `cd backend && .venv/bin/python -m pytest tests/test_zone_router.py -v` — all pass
- `rg "down_revision.*019" backend/migrations/versions/020_context_zones.py` — chains correctly

## Inputs

- `backend/app/context/rules_models.py` — template for SQLAlchemy model pattern
- `backend/app/context/rules_router.py` — template for CRUD router pattern
- `backend/app/context/service.py` — template for async session_factory service pattern
- `backend/migrations/versions/019_context_rules.py` — predecessor migration to chain from
- `backend/app/main.py` — lifespan registration and router inclusion
- `backend/app/dependencies.py` — dependency injection functions
- `backend/tests/test_context_service.py` — template for service tests (in-memory SQLite)
- `backend/tests/test_rules_router.py` — template for router tests (httpx + mocks)

## Expected Output

- `backend/app/context/zone_models.py` — ContextZone SQLAlchemy model
- `backend/app/context/zone_service.py` — ZoneService with CRUD methods
- `backend/app/context/zone_router.py` — Zone CRUD API router (4 endpoints)
- `backend/migrations/versions/020_context_zones.py` — Alembic migration
- `backend/app/main.py` — modified: zone_service on app.state, zone_router included
- `backend/app/dependencies.py` — modified: get_zone_service added
- `backend/tests/test_zone_service.py` — service unit tests
- `backend/tests/test_zone_router.py` — router unit tests
