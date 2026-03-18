---
id: T03
parent: S01
milestone: M013
provides:
  - GET /.well-known/sempkm discovery endpoint returning InstanceInfo JSON
  - well_known_router (APIRouter, tags=api-discovery)
  - api_surface_router (APIRouter, prefix=/api, tags=api-surface) — empty, ready for S02 endpoints
  - InstanceInfo Pydantic model for OpenAPI documentation
  - APP_VERSION = "2.6.0" via settings.app_version
key_files:
  - backend/app/api/__init__.py
  - backend/app/api/router.py
  - backend/app/main.py
  - backend/app/config.py
  - backend/tests/test_api_surface.py
key_decisions:
  - Version constant reads from settings.app_version (env-overridable) rather than a hardcoded module constant
  - _is_html_route updated to exclude /.well-known/ paths so 401s return JSON, not 302 redirects
patterns_established:
  - Well-known endpoint pattern: router at root level with Depends(get_current_user_or_api), Pydantic response model
  - _is_html_route exclusion pattern: any new JSON API path prefix outside /api/ must be added
observability_surfaces:
  - "GET /.well-known/sempkm → 200 JSON (authenticated) / 401 JSON (unauthenticated) / 404 (route broken)"
  - "Startup log: 'Starting SemPKM API v2.6.0' confirms version constant"
  - "FastAPI OpenAPI schema: /.well-known/sempkm visible under api-discovery tag"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Implement /.well-known/sempkm endpoint

**Added /.well-known/sempkm discovery endpoint with InstanceInfo Pydantic model, dual-auth, and 8 passing tests**

## What Happened

Created the `backend/app/api/` module with the well-known discovery endpoint and an empty api_surface_router for future S02 endpoints. The `GET /.well-known/sempkm` endpoint uses `get_current_user_or_api` from T01 to require authentication (session cookie or Bearer token) and returns a Pydantic `InstanceInfo` model with version, endpoints, auth methods, and capabilities.

Updated `settings.app_version` default from `"0.1.0"` to `"2.6.0"` in `config.py`. The router module reads this via `settings.app_version` so the version is env-overridable and consistent across the FastAPI title, startup logs, and the discovery document.

Wired both routers into `main.py` — `well_known_router` at root level (right after monitoring_router) and `api_surface_router` with `/api` prefix.

Discovered that `_is_html_route()` in `main.py` treated `/.well-known/` paths as HTML routes, causing 401 responses to get converted into 302 redirects to `/login.html`. Fixed by adding `/.well-known/` to the exclusion list alongside `/api/`.

Added 8 tests to `test_api_surface.py` covering: successful auth via cookie, successful auth via Bearer, unauthenticated rejection, invalid Bearer rejection, version matching, endpoints structure, auth methods, and capabilities list.

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "well_known"` — 8 passed
- `cd backend && python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` — 15 passed (slice-level)
- `cd backend && python -m pytest tests/test_api_surface.py -v` — 23 passed (all, including T01 auth tests)
- `curl -s http://localhost:3901/.well-known/sempkm` — returns `{"detail":"Not authenticated"}` with 401
- `curl -s -H "Authorization: Bearer invalid" http://localhost:3901/.well-known/sempkm` — returns `{"detail":"Invalid or expired API token"}` with 401
- `curl -v -X OPTIONS http://localhost:3901/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"` — returns CORS headers with 204

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "well_known"` | 0 | ✅ pass | 0.52s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` | 0 | ✅ pass | 0.61s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 0.59s |
| 4 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3901/.well-known/sempkm` | 0 | ✅ pass (401) | <1s |
| 5 | `curl -s -w "\n%{http_code}" -H "Authorization: Bearer invalid" http://localhost:3901/.well-known/sempkm` | 0 | ✅ pass (401 + correct detail) | <1s |
| 6 | `curl -v -X OPTIONS http://localhost:3901/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"` | 0 | ✅ pass (204 + CORS headers) | <1s |

### Slice-Level Verification Status (T03 is task 3 of 4)

| Check | Status | Notes |
|-------|--------|-------|
| `pytest -k "auth or well_known"` | ✅ pass | 15/15 tests |
| `curl /.well-known/sempkm` (unauth) | ✅ pass | Returns 401 JSON |
| `curl -H "Bearer <token>" /.well-known/sempkm` | ⏳ pending T04 | Need real API token in Docker to test success path |
| `curl -H "Bearer invalid" /.well-known/sempkm` | ✅ pass | Returns 401 with specific error |
| CORS preflight on `/api/types` | ✅ pass | 204 with correct headers |

## Diagnostics

- **Inspect discovery document:** `curl -H "Authorization: Bearer <token>" http://localhost:3901/.well-known/sempkm` — should return `{"version":"2.6.0","endpoints":{...},"auth":{...},"capabilities":[...]}`
- **Verify auth rejection:** `curl http://localhost:3901/.well-known/sempkm` — should return `{"detail":"Not authenticated"}` (not a 302 redirect)
- **Check OpenAPI:** `curl http://localhost:3901/openapi.json | jq '.paths["/.well-known/sempkm"]'` — endpoint should be listed under `api-discovery` tag
- **Verify version:** `docker compose logs api | grep "Starting SemPKM API"` — should show `v2.6.0`
- **Failure indicator:** If `/.well-known/sempkm` returns 302 instead of 401 for unauthenticated requests, the `_is_html_route` fix was reverted

## Deviations

- **`_is_html_route` fix:** The plan did not anticipate that `/.well-known/` paths would be treated as HTML routes by the exception handler, causing 401 to become 302 redirects. Fixed by adding `/.well-known/` to the path exclusion in `_is_html_route()`.
- **Tests added in T03 instead of T04:** The plan allocated tests to T04, but T03's own verification section requires `pytest -k "well_known"` — so 8 well-known endpoint tests were added here. T04 can extend or skip as appropriate.

## Known Issues

- Pyright reports `Import "app.api.router" could not be resolved` — false positive, the import works at runtime and in tests. The Pyright configuration doesn't include the new `api/` subdirectory in its search paths.

## Files Created/Modified

- `backend/app/api/__init__.py` — new module init with docstring
- `backend/app/api/router.py` — well_known_router with GET /.well-known/sempkm, api_surface_router (empty), InstanceInfo model
- `backend/app/main.py` — import and register both routers; fix _is_html_route to exclude /.well-known/ paths
- `backend/app/config.py` — update app_version default from "0.1.0" to "2.6.0"
- `backend/tests/test_api_surface.py` — add 8 well-known endpoint tests (TestWellKnownEndpoint class)
- `.gsd/milestones/M013/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section
