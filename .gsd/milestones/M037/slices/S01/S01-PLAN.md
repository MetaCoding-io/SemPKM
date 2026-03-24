# S01: Backend Context API & Workspace Indicator

**Goal:** User can POST context updates via API, see them in real-time in the workspace sidebar via SSE, and stale context (>15 min) shows as "Unknown"
**Demo:** POST a context update with curl → workspace sidebar shows location/activity/time in real-time → wait 15+ minutes (or set TTL to 5s for demo) → indicator shows "Unknown"

## Must-Haves

- `user_context` SQLite table with Alembic migration (018)
- `ContextService` with `update()`, `get_current()`, and TTL-based `is_stale` detection
- `ContextBroadcast` SSE fan-out (same pattern as LintBroadcast)
- `POST /api/context/update` — accepts JSON context snapshot, requires dual auth (cookie or Bearer)
- `GET /api/context/current` — returns current context with `is_stale` flag
- `GET /api/context/stream` — SSE stream pushing `context_update` and `context_stale` events
- Per-user rate throttle (max 1 update per 5 seconds) on POST endpoint
- Workspace sidebar context indicator consuming EventSource, updating in real-time
- Stale context (> TTL) displayed as "Unknown" in both API and UI
- All new endpoints accept both session cookie and Bearer API token auth

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (SSE stream, Docker stack)
- Human/UAT required: no (automated tests + curl verification sufficient)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` — all tests pass
- `curl -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"office","activity":"stationary","time_period":"work_hours"}' ` — returns 200 with context JSON
- `curl http://localhost:3901/api/context/current -H "Authorization: Bearer $TOKEN"` — returns context with `is_stale` field
- Context indicator visible in workspace sidebar (browser visual check)
- `curl -X POST http://localhost:3901/api/context/update -H "Content-Type: application/json" -d '{"location_zone":"office"}' 2>&1 | grep -q '401\|Not authenticated'` — returns 401 without auth (failure path)
- `curl http://localhost:3901/api/context/current -H "Authorization: Bearer $TOKEN" 2>&1 | grep -q 'is_stale'` — response includes staleness diagnostic field

## Observability / Diagnostics

- Runtime signals: `context.update` structured log on every POST (user_id, location_zone, device_id); `context.stale` log when TTL expires during GET
- Inspection surfaces: `GET /api/context/current` returns full context state including `is_stale`, `updated_at`, `ttl_seconds`; `ContextBroadcast.client_count` property
- Failure visibility: HTTP 429 on rate limit with `Retry-After` header; HTTP 422 on invalid payload with field-level errors
- Redaction constraints: no PII in context (zone labels, not coordinates); device_id is opaque string

## Integration Closure

- Upstream surfaces consumed: `LintBroadcast` pattern (`backend/app/lint/broadcast.py`), `PersonaService` pattern (`backend/app/persona/`), `get_current_user_or_api` dual-auth (`backend/app/auth/dependencies.py`), `app.state.*` registration (`backend/app/main.py` lifespan), Alembic migration chain (017 → 018)
- New wiring introduced in this slice: `ContextService` + `ContextBroadcast` on `app.state`, context router included in `main.py`, SSE endpoint, workspace sidebar partial
- What remains before the milestone is truly usable end-to-end: S02 rules engine for auto-persona switching, S03-S05 mobile app to push context automatically, S06 push notifications

## Tasks

- [x] **T01: Context domain — model, migration, service, and broadcast** `est:1h`
  - Why: Foundation for all context features — SQLAlchemy model, Alembic migration, ContextService with TTL staleness, ContextBroadcast for SSE fan-out
  - Files: `backend/app/context/__init__.py`, `backend/app/context/models.py`, `backend/app/context/service.py`, `backend/app/context/broadcast.py`, `backend/migrations/versions/018_user_context.py`
  - Do: Create `backend/app/context/` package. Define `UserContext` SQLAlchemy model with `id`, `user_id` (FK users.id CASCADE), `location_zone`, `activity`, `time_period`, `calendar_event`, `calendar_busy`, `device_id`, `updated_at` columns. Write Alembic migration 018 (up creates table, down drops it). Implement `ContextService` with `update(user_id, **fields)` (upsert pattern — one row per user), `get_current(user_id)` returning dict with `is_stale` computed from `updated_at` vs configurable TTL (default 900s / 15 min). Implement `ContextBroadcast` as exact copy of `LintBroadcast` pattern with `subscribe()`, `unsubscribe()`, `publish()`.
  - Verify: `python -c "from app.context.models import UserContext; from app.context.service import ContextService; from app.context.broadcast import ContextBroadcast; print('imports OK')"` succeeds from backend/
  - Done when: All four files exist, model has correct columns and FK, service has update/get_current with TTL logic, broadcast has fan-out pattern

- [ ] **T02: Context API router, dependency wiring, and rate limiting** `est:1h`
  - Why: Exposes the context domain via REST + SSE endpoints, wires service/broadcast into app.state, adds rate throttle
  - Files: `backend/app/context/router.py`, `backend/app/main.py`, `backend/app/dependencies.py`
  - Do: Create `router.py` with three endpoints: (1) `POST /api/context/update` accepting JSON body with optional fields (location_zone, activity, time_period, calendar_event, calendar_busy, device_id), calling `ContextService.update()` then `ContextBroadcast.publish()`, protected by `get_current_user_or_api` + slowapi rate limit (1/5s per user), returning current context JSON. (2) `GET /api/context/current` returning context dict with `is_stale`. (3) `GET /api/context/stream` SSE endpoint following the exact `lint_stream()` pattern (shutdown_event, subscribe/unsubscribe, 30s keepalive). Add `get_context_service` and `get_context_broadcast` dependency functions in `dependencies.py`. In `main.py` lifespan: create `ContextService(async_session_factory)` and `ContextBroadcast()`, store on `app.state.context_service` and `app.state.context_broadcast`. Include the context router via `app.include_router()`.
  - Verify: `python -c "from app.context.router import router; print('router OK')"` succeeds; `grep -q "context_service" backend/app/main.py` returns 0
  - Done when: All three endpoints defined, service+broadcast wired in main.py lifespan, dependencies registered, router included

- [ ] **T03: Unit tests for ContextService and context API endpoints** `est:1h`
  - Why: Proves the contract — TTL staleness, upsert semantics, rate limiting, SSE stream format, auth enforcement
  - Files: `backend/tests/test_context_service.py`, `backend/tests/test_context_router.py`
  - Do: Write `test_context_service.py` with in-memory SQLite (same pattern as `test_persona_service.py`): test create/update context, test get_current returns correct fields, test is_stale=False when fresh, test is_stale=True when updated_at is old (mock time or use tiny TTL), test upsert overwrites existing row, test get_current for non-existent user returns None/empty. Write `test_context_router.py` with httpx TestClient: test POST /api/context/update with valid payload returns 200, test POST with empty body returns 200 (all fields optional), test GET /api/context/current returns context after POST, test auth enforcement (401 without credentials), test rate limiting (multiple rapid POSTs), test SSE stream returns event-stream content type.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` — all pass
  - Done when: ≥10 service tests + ≥8 router tests pass, covering TTL, upsert, auth, rate limit, and SSE content type

- [ ] **T04: Workspace sidebar context indicator with SSE** `est:1h`
  - Why: Makes context visible in the UI — user sees location/activity/time updating in real-time
  - Files: `backend/app/templates/browser/workspace.html`, `frontend/static/js/context-indicator.js`, `frontend/static/css/context-indicator.css`
  - Do: Add a context indicator element in the workspace sidebar (bottom of `#nav-pane`, above the explorer sections or as a thin status bar at the top of the sidebar). The indicator shows: location zone icon (map-pin), activity (footprints/car/armchair), time period (sun/moon/briefcase), and optional calendar event name. Create `context-indicator.js` as a self-contained IIFE: on DOMContentLoaded, call `GET /api/context/current` to populate initial state, then open `EventSource('/api/context/stream')` for real-time updates. On `context_update` event, update indicator text/icons. On `context_stale` event (or when `is_stale` is true), show "Unknown" with muted styling. Create `context-indicator.css` with compact styling (small text, subtle icons, muted colors when stale). Add `<script src="/js/context-indicator.js">` and `<link href="/css/context-indicator.css">` to workspace.html. Include the indicator HTML partial in the sidebar.
  - Verify: `test -f frontend/static/js/context-indicator.js && test -f frontend/static/css/context-indicator.css` — files exist; `grep -q "context-indicator" backend/app/templates/browser/workspace.html` — indicator referenced in workspace
  - Done when: Context indicator renders in workspace sidebar, connects to SSE stream, updates on context_update events, shows "Unknown" when stale

## Files Likely Touched

- `backend/app/context/__init__.py`
- `backend/app/context/models.py`
- `backend/app/context/service.py`
- `backend/app/context/broadcast.py`
- `backend/app/context/router.py`
- `backend/migrations/versions/018_user_context.py`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/tests/test_context_service.py`
- `backend/tests/test_context_router.py`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/context-indicator.js`
- `frontend/static/css/context-indicator.css`
