---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T02: Context API router, dependency wiring, and rate limiting

**Slice:** S01 — Backend Context API & Workspace Indicator
**Milestone:** M037

## Description

Create the FastAPI router with three endpoints (POST update, GET current, GET stream), wire ContextService and ContextBroadcast into `app.state` via the lifespan, register dependency functions, and include the router in `main.py`. Add per-user rate limiting on the update endpoint.

## Steps

1. Create `backend/app/context/router.py` with `APIRouter(prefix="/api/context", tags=["context"])`. Define three endpoints:
   - `POST /update` — accepts JSON body (Pydantic model or raw request.json) with optional fields: `location_zone` (str), `activity` (str), `time_period` (str), `calendar_event` (str), `calendar_busy` (bool), `device_id` (str). Calls `ContextService.update(user.id, **fields)`. Then calls `ContextBroadcast.publish(SSEEvent(event="context_update", data={...}))` with the updated context. Protected by `get_current_user_or_api` for dual auth. Apply slowapi rate limit `@limiter.limit("12/minute")` (≈1 per 5s). Returns the current context as JSON (200).
   - `GET /current` — calls `ContextService.get_current(user.id)` and returns JSON. Returns `{"context": null}` if no context exists. Protected by `get_current_user_or_api`.
   - `GET /stream` — SSE endpoint following the exact pattern of `lint_stream()` in `backend/app/lint/router.py`. Uses `ContextBroadcast.subscribe()` / `unsubscribe()`, races queue.get() against shutdown_event, sends 30s keepalive. Protected by `get_current_user_or_api`. Returns `StreamingResponse` with `text/event-stream`.

2. Add dependency functions in `backend/app/dependencies.py`:
   - `async def get_context_service(request: Request) -> ContextService` — returns `request.app.state.context_service`
   - `async def get_context_broadcast(request: Request) -> ContextBroadcast` — returns `request.app.state.context_broadcast`

3. In `backend/app/main.py` lifespan (after the persona_service registration block):
   - Import `ContextService` from `app.context.service` and `ContextBroadcast` from `app.context.broadcast`
   - Create instances: `context_service = ContextService(async_session_factory)` and `context_broadcast = ContextBroadcast()`
   - Store on app.state: `app.state.context_service = context_service` and `app.state.context_broadcast = context_broadcast`

4. In `backend/app/main.py` router includes (after persona routers):
   - Import `from app.context.router import router as context_router`
   - Add `app.include_router(context_router)`

5. Define a Pydantic request model `ContextUpdateRequest` in the router (or in a separate models file under context/) with all fields optional. Use this for the POST body to get automatic validation and OpenAPI docs.

## Must-Haves

- [ ] POST /api/context/update accepts both session cookie and Bearer token auth
- [ ] POST /api/context/update has rate limiting (12/minute per user)
- [ ] GET /api/context/stream follows the exact SSE pattern from lint_stream (shutdown_event, subscribe/unsubscribe, keepalive)
- [ ] ContextService and ContextBroadcast registered on app.state in lifespan
- [ ] Router included in app.include_router() chain
- [ ] POST endpoint publishes SSE event after persisting context

## Verification

- `cd backend && python -c "from app.context.router import router; print(f'Routes: {len(router.routes)}')"` — prints "Routes: 3"
- `grep -q "context_service" backend/app/main.py && grep -q "context_broadcast" backend/app/main.py && grep -q "context_router" backend/app/main.py` — all three present

## Observability Impact

- Signals added/changed: HTTP 429 response with Retry-After header on rate limit; structured JSON error on 422 validation failure
- How a future agent inspects this: `GET /api/context/current` for state, SSE stream for live events, OpenAPI docs at `/redoc` showing context tag
- Failure state exposed: 429 rate limit, 401 auth failure, 422 validation error

## Inputs

- `backend/app/context/service.py` — ContextService created in T01
- `backend/app/context/broadcast.py` — ContextBroadcast created in T01
- `backend/app/lint/router.py` — SSE stream pattern to replicate (lint_stream function)
- `backend/app/lint/broadcast.py` — SSEEvent class to import
- `backend/app/auth/dependencies.py` — `get_current_user_or_api` for dual auth
- `backend/app/auth/rate_limit.py` — `limiter` for slowapi rate limiting
- `backend/app/persona/router.py` — API router pattern to follow
- `backend/app/main.py` — lifespan registration and router include pattern
- `backend/app/dependencies.py` — dependency function registration pattern

## Expected Output

- `backend/app/context/router.py` — FastAPI router with POST /update, GET /current, GET /stream
- `backend/app/main.py` — modified with context service/broadcast registration and router include
- `backend/app/dependencies.py` — modified with get_context_service and get_context_broadcast
