---
id: T01
parent: S04
milestone: M043
key_files:
  - backend/app/sparql/router.py
  - backend/app/api/copilot.py
  - backend/app/auth/router.py
  - backend/app/auth/dependencies.py
  - backend/app/auth/rate_limit.py
  - backend/app/commands/router.py
  - backend/app/main.py
  - backend/app/triplestore/client.py
  - backend/app/workflow/router.py
  - backend/app/dashboard/router.py
  - backend/app/task_templates/router.py
  - backend/tests/test_security_hardening.py
  - backend/tests/test_commands_bearer_auth.py
key_decisions:
  - Keep headers_enabled=False on slowapi limiter and set Retry-After explicitly in custom handler — avoids crash on Pydantic-model-returning endpoints
  - Custom rate limit handler replaces default slowapi handler to add both logging and Retry-After header
  - Global exception handler uses @app.exception_handler(Exception) for unhandled errors — returns generic 500, logs full traceback
duration: ""
verification_result: passed
completed_at: 2026-03-25T15:11:56.545Z
blocker_discovered: false
---

# T01: Add rate limits to 4 endpoint groups, SPARQL query timeout, global exception handler, and auth failure logging

**Add rate limits to 4 endpoint groups, SPARQL query timeout, global exception handler, and auth failure logging**

## What Happened

Implemented four security hardening features:

**1. Rate limits on 4 endpoint groups** — Added `@limiter.limit` decorators to:
- `POST /api/sparql` (60/minute)
- `POST /api/copilot/chat` (20/minute)
- `POST /api/auth/tokens` (5/minute)
- `POST /api/commands` (20/minute)

The existing slowapi infrastructure (limiter instance in `app.auth.rate_limit`, `SlowAPIMiddleware` in main.py) handles enforcement. The custom `_rate_limit_exceeded_handler_with_logging` replaces the default handler — it logs rate limit events at WARNING with source IP and path, and explicitly sets `Retry-After: 60` header on 429 responses.

**2. SPARQL query timeout** — The triplestore client already had `timeout=30.0` on the httpx AsyncClient. Added `httpx.TimeoutException` catch blocks in both the GET and POST SPARQL endpoints, returning 504 with `"Query timed out after 30 seconds"`.

**3. Error disclosure protection (F-025)** — Added a global `@app.exception_handler(Exception)` in main.py that catches unhandled exceptions, logs the full traceback at ERROR level, and returns a generic `{"detail": "Internal server error"}` 500 response. Replaced all 6 `detail=str(e)` patterns across auth, workflow, dashboard, and task_templates routers with generic messages while logging the original error at WARNING.

**4. Failed auth attempt logging** — Added WARNING-level logs in:
- `auth/router.py`: verify endpoint logs IP on invalid/expired tokens and on token replay attempts
- `auth/dependencies.py`: `get_current_user_or_api` logs IP and token prefix (first 8 chars) on invalid Bearer tokens
- `main.py`: rate limit exceeded handler logs IP and path

**Key decisions:**
- Kept `headers_enabled=False` on the limiter to avoid slowapi's decorator trying to inject headers on Pydantic model responses (which crashes with `response must be an instance of Response`). Instead, the Retry-After header is set explicitly in the custom rate limit handler. This is the only reliable approach when endpoints return Pydantic models rather than Response objects.
- The global exception handler uses FastAPI's `@app.exception_handler(Exception)`. In production, Starlette's ServerErrorMiddleware sends the handler's response then re-raises (for server logging). httpx's ASGITransport also re-raises, so tests that verify the handler need `raise_app_exceptions=False`.

## Verification

All 5 new security hardening tests pass. All 111 related tests (auth tokens, bearer auth, token scopes, copilot, conversations) pass with zero regressions. The 104 pre-existing failures in the full suite are all from unrelated modules (caldav missing icalendar, notion import error, dashboard builder template mismatch, etc.).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_security_hardening.py -v` | 0 | ✅ pass | 850ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py tests/test_token_scopes.py tests/test_auth_tokens.py tests/test_ai_personas.py tests/test_conversation_service.py -v` | 0 | ✅ pass | 4480ms |
| 3 | `rg 'detail=str(e)' backend/app/ -g '*.py'` | 1 | ✅ pass (zero matches) | 50ms |


## Deviations

1. Did not use `headers_enabled=True` on the limiter — it causes crashes when endpoints return Pydantic models instead of Response objects. Used explicit Retry-After header in custom handler instead.
2. The task plan's verification command includes `--timeout=60` which is not installed. Tests run without it.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/router.py`
- `backend/app/api/copilot.py`
- `backend/app/auth/router.py`
- `backend/app/auth/dependencies.py`
- `backend/app/auth/rate_limit.py`
- `backend/app/commands/router.py`
- `backend/app/main.py`
- `backend/app/triplestore/client.py`
- `backend/app/workflow/router.py`
- `backend/app/dashboard/router.py`
- `backend/app/task_templates/router.py`
- `backend/tests/test_security_hardening.py`
- `backend/tests/test_commands_bearer_auth.py`
