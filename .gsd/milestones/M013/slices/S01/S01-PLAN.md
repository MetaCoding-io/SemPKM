# S01: Dual-Auth, CORS, nginx fix, and Well-Known Endpoint

**Goal:** Build the dual-auth FastAPI dependency (session cookie OR Bearer token), fix nginx to forward Authorization headers with CORS support, and ship the `/.well-known/sempkm` discovery endpoint — proving the entire external-client pipeline works end-to-end.
**Demo:** `curl -H "Authorization: Bearer <token>" localhost:3000/.well-known/sempkm` returns JSON discovery document through Docker Compose. Same endpoint works with session cookie.

## Must-Haves

- `get_current_user_or_api` FastAPI dependency that accepts either session cookie or `Authorization: Bearer <token>` header
- nginx `/api/` and `/.well-known/` blocks forward `Authorization` header
- CORS headers on `/api/` responses (`Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: Authorization, Content-Type`)
- `GET /.well-known/sempkm` returns JSON with version, endpoint URLs, auth methods, capabilities
- Unit tests for dual-auth dependency (cookie-only, bearer-only, both missing, invalid token)
- Unit tests for well-known endpoint response schema

## Proof Level

- This slice proves: integration (auth pipeline through nginx → FastAPI with real tokens)
- Real runtime required: yes (Docker Compose stack for nginx proxy verification)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` — unit tests pass
- `curl -v http://localhost:3000/.well-known/sempkm` — returns JSON with `version`, `endpoints`, `capabilities` keys
- `curl -v -H "Authorization: Bearer <token>" http://localhost:3000/.well-known/sempkm` — returns 200 with same JSON
- `curl -v -H "Authorization: Bearer invalid" http://localhost:3000/.well-known/sempkm` — returns 401
- `curl -v -X OPTIONS http://localhost:3000/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"` — returns CORS headers
- `curl -v -H "Authorization: Bearer invalid" http://localhost:3000/.well-known/sempkm` — returns 401 with JSON `{"detail": "Invalid or expired API token"}` (failure-path diagnostic)

## Observability / Diagnostics

- Runtime signals: 401 response with `"detail": "Invalid or expired API token"` on bad Bearer token; standard 401 on missing auth
- Inspection surfaces: `curl -v` shows `Authorization` header reaching FastAPI (visible in response); CORS headers in response
- Failure visibility: nginx access log shows forwarded request; FastAPI debug log shows auth path taken (cookie vs bearer)
- Redaction constraints: API tokens must not appear in log output

## Tasks

- [x] **T01: Build dual-auth FastAPI dependency** `est:45m`
  - Why: All four M013 endpoints need to accept either session cookie or Bearer API token. Current `get_current_user` only checks cookies. `AuthService.verify_api_token()` exists and is tested but isn't wired as a FastAPI dependency.
  - Files: `backend/app/auth/dependencies.py`
  - Do:
    1. Add `get_authorization_header` that extracts Bearer token from `Authorization` header (returns None if absent or not Bearer scheme)
    2. Add `get_current_user_or_api` async dependency that: (a) tries session cookie via existing `get_session_token` → `get_current_user` path, (b) if no cookie, tries Bearer token via `AuthService.verify_api_token()`, (c) raises 401 if neither succeeds
    3. The dependency needs access to `AuthService` — get it from `request.app.state.auth_service` (same pattern as other services). Import `Request` from fastapi and add it as a parameter.
    4. Keep existing `get_current_user` unchanged — htmx frontend still uses it
  - Verify: `python -m pytest tests/test_api_surface.py -v -k "test_dual_auth"` — tests for cookie-only, bearer-only, both missing, invalid bearer
  - Done when: `get_current_user_or_api` resolves a User from either auth method and raises 401 cleanly when neither is present

- [x] **T02: Fix nginx Authorization forwarding and add CORS** `est:30m`
  - Why: The `/api/` proxy block doesn't forward the `Authorization` header — only `/dav/` does. Without this, Bearer tokens from browser extensions are stripped by nginx. CORS headers are needed for cross-origin requests from browser extensions.
  - Files: `frontend/nginx.conf`
  - Do:
    1. In the `location /api/` block, add `proxy_set_header Authorization $http_authorization;` and `proxy_pass_header Authorization;` (matching the `/dav/` block pattern)
    2. Add a new `location /.well-known/sempkm` block that proxies to `http://api:8000/.well-known/sempkm` with the same Authorization forwarding
    3. Add CORS headers to both blocks: `add_header Access-Control-Allow-Origin "*" always;`, `add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;`, `add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;`
    4. Add an `if ($request_method = OPTIONS)` block in `/api/` that returns 204 with CORS headers for preflight requests
  - Verify: `docker compose restart frontend` then `curl -v -X OPTIONS http://localhost:3000/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"` returns CORS headers with 204
  - Done when: `Authorization` header reaches FastAPI through nginx, and CORS preflight returns proper headers

- [x] **T03: Implement /.well-known/sempkm endpoint** `est:30m`
  - Why: Instance discovery endpoint that external clients hit first to learn what the SemPKM instance supports. This is the first endpoint using dual-auth, proving the full pipeline.
  - Files: `backend/app/api/__init__.py`, `backend/app/api/router.py`, `backend/app/main.py`
  - Do:
    1. Create `backend/app/api/` module with `__init__.py` and `router.py`
    2. In `router.py`, create `well_known_router = APIRouter(tags=["api-discovery"])` and `api_surface_router = APIRouter(prefix="/api", tags=["api-surface"])`
    3. Add `GET /.well-known/sempkm` on `well_known_router` that returns JSON: `{"version": settings.app_version, "endpoints": {"types": "/api/types", "shapes": "/api/shapes/{type_iri}", "context_query": "/api/context-query", "sparql": "/api/sparql", "commands": "/api/commands"}, "auth": {"session": true, "api_key": true, "indieauth": "/auth/authorize"}, "capabilities": ["types", "shapes", "context-query", "sparql", "commands"]}`
    4. Endpoint requires auth via `Depends(get_current_user_or_api)` — external clients must authenticate to discover capabilities
    5. Add `APP_VERSION` to `config.py` settings (default "2.6.0") or read from a constant
    6. Wire both routers into `main.py` — `well_known_router` at root level, `api_surface_router` with `/api` prefix
  - Verify: `python -m pytest tests/test_api_surface.py -v -k "well_known"` passes; `curl http://localhost:3000/.well-known/sempkm` returns valid JSON after Docker rebuild
  - Done when: Discovery endpoint returns well-structured JSON with correct endpoint URLs and capabilities

- [ ] **T04: Unit tests for dual-auth and well-known** `est:30m`
  - Why: Verify auth dependency logic and response schemas without Docker. Tests also serve as documentation of the auth contract for downstream slice developers.
  - Files: `backend/tests/test_api_surface.py`
  - Do:
    1. Create `test_api_surface.py` with test fixtures for mock request objects (with/without cookies, with/without Authorization headers)
    2. Test `get_current_user_or_api`: (a) valid session cookie → returns user, (b) valid Bearer token → returns user, (c) no cookie + no header → raises 401, (d) invalid Bearer token → raises 401, (e) Bearer with wrong scheme (Basic) → falls through to 401
    3. Test well-known endpoint: (a) returns correct JSON schema, (b) contains all required keys (version, endpoints, auth, capabilities), (c) endpoint URLs are correct strings
    4. Use httpx.AsyncClient with FastAPI TestClient pattern for endpoint tests
  - Verify: `cd backend && python -m pytest tests/test_api_surface.py -v` — all tests pass
  - Done when: ≥8 unit tests covering both auth paths and well-known response schema

## Files Likely Touched

- `backend/app/auth/dependencies.py` — new `get_current_user_or_api` dependency
- `backend/app/api/__init__.py` — new module init
- `backend/app/api/router.py` — well-known endpoint + api surface router
- `backend/app/main.py` — router wiring
- `backend/app/config.py` — APP_VERSION setting
- `frontend/nginx.conf` — Authorization forwarding + CORS headers
- `backend/tests/test_api_surface.py` — unit tests
