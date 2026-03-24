---
id: T02
parent: S01
milestone: M037
provides:
  - POST /api/context/update endpoint with dual auth and 12/min rate limit
  - GET /api/context/current endpoint returning context with is_stale field
  - GET /api/context/stream SSE endpoint following lint_stream pattern
  - ContextService and ContextBroadcast wired into app.state via lifespan
  - get_context_service and get_context_broadcast dependency functions
  - Pydantic ContextUpdateRequest model with field-level validation
  - 7 service tests + 13 router tests (20 total)
key_files:
  - backend/app/context/router.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/tests/test_context_service.py
  - backend/tests/test_context_router.py
key_decisions:
  - SSEEvent.data takes dict not JSON string — broadcast.publish gets dataclasses.asdict(ctx) directly
  - Rate limit set to 12/minute per IP via slowapi decorator (matches plan's ≈1 per 5s)
  - Empty POST body returns 422 with explicit message rather than silently accepting a no-op update
patterns_established:
  - Pydantic model_dump(exclude_unset=True) for partial-update endpoints — only passes fields the caller explicitly provided
  - ContextUpdateRequest with all-optional fields + exclude_unset gives clean merge semantics without null-vs-absent ambiguity
observability_surfaces:
  - HTTP 429 with Retry-After header on rate limit breach
  - HTTP 422 on invalid payload (field length, empty body) with field-level errors
  - HTTP 401 on missing/invalid auth for all three endpoints
  - GET /api/context/current returns full context including is_stale, updated_at, ttl_seconds
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Context API router, dependency wiring, and rate limiting

**Created FastAPI router with POST /update (rate-limited, SSE-publishing), GET /current, GET /stream endpoints; wired ContextService and ContextBroadcast into app.state; added dependency functions and 20 tests**

## What Happened

Created `backend/app/context/router.py` with three endpoints following established codebase patterns. POST /update accepts a Pydantic `ContextUpdateRequest` with all-optional fields, uses `model_dump(exclude_unset=True)` to pass only caller-provided fields to `ContextService.update()`, then publishes the updated context via `ContextBroadcast` as an SSE event. The endpoint is rate-limited to 12/minute via the existing slowapi `limiter` decorator and protected by `get_current_user_or_api` for dual auth. GET /current returns the context wrapped in `{"context": {...}}` or `{"context": null}`. GET /stream is a direct replica of the `lint_stream()` SSE pattern — shutdown_event race, 30s keepalive, subscribe/unsubscribe cleanup.

Added `get_context_service` and `get_context_broadcast` dependency functions in `dependencies.py`. Wired both into `main.py` lifespan after the persona_service block. Included the context router in the `app.include_router()` chain.

Also created both test files referenced by the slice verification: `test_context_service.py` (7 tests covering insert, merge-update, staleness with zero TTL, unknown user → None) and `test_context_router.py` (13 tests covering update flow, SSE event publishing, empty body 422, partial fields, field length validation, null context, stale context, auth enforcement on POST and GET, and Pydantic model validation).

## Verification

Both task-level verification checks pass:
1. `from app.context.router import router; print(f'Routes: {len(router.routes)}')` → "Routes: 3"
2. `grep -q "context_service" ... && grep -q "context_broadcast" ... && grep -q "context_router" ...` → all present

Slice-level test verification passes: all 20 tests green in 0.69s.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.context.router import router; print(f'Routes: {len(router.routes)}')"` | 0 | ✅ pass | <1s |
| 2 | `grep -q "context_service" backend/app/main.py && grep -q "context_broadcast" backend/app/main.py && grep -q "context_router" backend/app/main.py` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` — 20 passed | 0 | ✅ pass | 0.69s |

## Diagnostics

- `GET /api/context/current` returns full state including `is_stale`, `updated_at`, `ttl_seconds` — primary inspection surface
- `GET /api/context/stream` provides live SSE events for real-time monitoring
- HTTP 429 response with `Retry-After` header surfaces rate-limit enforcement
- HTTP 422 response with field-level Pydantic errors surfaces validation failures
- HTTP 401 surfaces auth failures (no cookie, no Bearer, expired token)

## Deviations

- Created both test files (service + router) in T02 rather than deferring to T03, since the slice verification requires both to pass and the tests were straightforward to write alongside the router implementation. T03 can focus on additional coverage or skip if sufficient.

## Known Issues

None.

## Files Created/Modified

- `backend/app/context/router.py` — FastAPI router with POST /update (rate-limited), GET /current, GET /stream (SSE) endpoints
- `backend/app/dependencies.py` — Added get_context_service and get_context_broadcast dependency functions
- `backend/app/main.py` — Wired ContextService + ContextBroadcast into lifespan, included context_router
- `backend/tests/test_context_service.py` — 7 tests for ContextService upsert and TTL staleness logic
- `backend/tests/test_context_router.py` — 13 tests for router endpoints, auth enforcement, and Pydantic validation
