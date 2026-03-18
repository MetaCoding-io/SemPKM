# S01: Dual-Auth, CORS, nginx fix, and Well-Known Endpoint — UAT

**Milestone:** M013
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven unit tests + live-runtime curl verification)
- Why this mode is sufficient: Unit tests verify auth logic and response schemas. Docker curl verifies the nginx proxy layer which can't be tested via pytest. No human-experience aspects — all criteria are machine-verifiable.

## Preconditions

- Docker Compose stack running: `docker compose up -d` (api, triplestore, frontend services)
- Backend Python venv available: `backend/.venv/bin/python` works
- At least one user exists in the database (created via setup wizard or seed)
- Know the Docker port mapping (typically `3901:80` or `3000:80`)

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` — all 25 tests pass in <1s.

## Test Cases

### 1. Unit tests: dual-auth dependency

1. `cd /home/james/Code/SemPKM/backend`
2. `.venv/bin/python -m pytest tests/test_api_surface.py -v -k "dual_auth"`
3. **Expected:** 7 tests pass — valid cookie, expired cookie fallthrough, valid bearer, invalid bearer, Basic scheme rejected, no credentials, cookie-over-bearer precedence

### 2. Unit tests: bearer token extraction

1. `cd /home/james/Code/SemPKM/backend`
2. `.venv/bin/python -m pytest tests/test_api_surface.py -v -k "TestExtractBearerToken"`
3. **Expected:** 8 tests pass — valid bearer, case insensitivity, None, empty, wrong scheme, no space, empty token, spaces in token

### 3. Unit tests: well-known endpoint

1. `cd /home/james/Code/SemPKM/backend`
2. `.venv/bin/python -m pytest tests/test_api_surface.py -v -k "TestWellKnownEndpoint"`
3. **Expected:** 10 tests pass — content-type, required keys, bearer auth, unauthenticated rejection, invalid bearer, version match, endpoint strings, endpoint structure, auth methods, capabilities list

### 4. Full backend regression

1. `cd /home/james/Code/SemPKM/backend`
2. `.venv/bin/python -m pytest tests/ --tb=short -q`
3. **Expected:** 971 tests pass, 0 failures

### 5. CORS preflight via Docker

1. Ensure Docker stack is running
2. `curl -v -X OPTIONS http://localhost:3901/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"`
3. **Expected:** HTTP 204 response with headers:
   - `Access-Control-Allow-Origin: *`
   - `Access-Control-Allow-Headers: Authorization, Content-Type, Accept`
   - `Access-Control-Allow-Methods: GET, POST, OPTIONS`

### 6. Well-known CORS preflight via Docker

1. `curl -v -X OPTIONS http://localhost:3901/.well-known/sempkm -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"`
2. **Expected:** HTTP 204 response with same CORS headers as test 5

### 7. Unauthenticated discovery returns 401 JSON

1. `curl -s -w "\n%{http_code}" http://localhost:3901/.well-known/sempkm`
2. **Expected:** HTTP 401 with JSON body `{"detail":"Not authenticated"}` (NOT a 302 redirect to login.html)

### 8. Invalid bearer returns 401 JSON with specific message

1. `curl -s -w "\n%{http_code}" -H "Authorization: Bearer invalid-token-12345" http://localhost:3901/.well-known/sempkm`
2. **Expected:** HTTP 401 with JSON body `{"detail":"Invalid or expired API token"}`

### 9. Authorization header forwarding

1. `curl -v -H "Authorization: Bearer test-token" http://localhost:3901/api/types`
2. **Expected:** The `> Authorization: Bearer test-token` line appears in curl verbose output (request sent). Backend returns 404 or 401 (endpoint not built yet in S01), but the Authorization header was forwarded.

### 10. nginx config syntax validation

1. `docker exec sempkm-frontend-1 nginx -t`
2. **Expected:** `nginx: the configuration file /etc/nginx/nginx.conf syntax is ok` and `nginx: configuration file /etc/nginx/nginx.conf test is successful`

### 11. Well-known endpoint with valid Bearer token (authenticated success path)

1. Create an API token in the database (via Settings UI or direct SQL)
2. `curl -s -H "Authorization: Bearer <real-token>" http://localhost:3901/.well-known/sempkm`
3. **Expected:** HTTP 200 with JSON:
   ```json
   {
     "version": "2.6.0",
     "endpoints": {
       "types": "/api/types",
       "shapes": "/api/shapes/{type_iri}",
       "context_query": "/api/context-query",
       "sparql": "/api/sparql",
       "commands": "/api/commands"
     },
     "auth": {
       "session": true,
       "api_key": true,
       "indieauth": "/auth/authorize"
     },
     "capabilities": ["types", "shapes", "context-query", "sparql", "commands"]
   }
   ```

### 12. Well-known endpoint with session cookie (htmx auth path)

1. Log in to the SemPKM workspace in a browser
2. Open browser DevTools → Network tab
3. Navigate to `http://localhost:3901/.well-known/sempkm` (or fetch via console)
4. **Expected:** HTTP 200 with same JSON as test 11 (session cookie authenticates the request)

## Edge Cases

### Wrong auth scheme (Basic instead of Bearer)

1. `curl -s -w "\n%{http_code}" -H "Authorization: Basic dXNlcjpwYXNz" http://localhost:3901/.well-known/sempkm`
2. **Expected:** HTTP 401 with `{"detail":"Not authenticated"}` — Basic scheme is ignored, no bearer token found, falls through to "no credentials" path

### Empty Authorization header

1. `curl -s -w "\n%{http_code}" -H "Authorization:" http://localhost:3901/.well-known/sempkm`
2. **Expected:** HTTP 401 with `{"detail":"Not authenticated"}`

### CORS on error responses

1. `curl -v http://localhost:3901/.well-known/sempkm`
2. **Expected:** Even the 401 error response includes `Access-Control-Allow-Origin: *` header (the `always` flag in nginx ensures this)

## Failure Signals

- `pytest` test failures in `test_api_surface.py` — auth contract or response schema regression
- CORS headers missing from OPTIONS response — nginx config syntax error or `always` flag removed
- `/.well-known/sempkm` returns 302 instead of 401 — `_is_html_route()` fix was reverted (D163)
- `/.well-known/sempkm` returns 404 — router not wired in `main.py` or nginx proxy block missing
- `Authorization` header not forwarded — `proxy_set_header Authorization` line missing from nginx `/api/` block

## Requirements Proved By This UAT

- API-01 — Tests 7, 8, 11, 12 prove the well-known endpoint returns correct JSON with auth enforcement
- API-05 — Tests 1, 2, 3, 11, 12 prove dual-auth dependency works for both cookie and bearer paths
- API-06 — Tests 5, 6, and edge case "CORS on error responses" prove CORS headers are correct
- API-07 — Test 9, 10 prove Authorization header forwarding through nginx

## Not Proven By This UAT

- Authenticated success path through Docker requires a real API token (test 11) — only testable if user creates one via Settings UI
- Session cookie success path through Docker (test 12) — requires interactive browser login
- These paths ARE tested in unit tests via dependency mocking; Docker tests focus on nginx proxy behavior

## Notes for Tester

- Docker port mapping may be `3901:80` (test stack) or `3000:80` (dev stack) — adjust curl commands accordingly
- The `backend/tests/` directory is not volume-mounted into Docker, so pytest must be run locally (not inside the container)
- Tests 11 and 12 require setup that is non-trivial to automate (API token creation, browser login) — they are primarily for manual verification or future E2E test coverage (S03)
- httpx DeprecationWarning about per-request cookies is expected noise — not a test failure
