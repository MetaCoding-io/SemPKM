# S01: Read-only enforcement + DEMO_MODE anonymous access — UAT

**Milestone:** M025
**Written:** 2026-03-20

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: The slice is about network behavior (HTTP responses, redirects, content-type headers) that can only be verified against the running Docker stack

## Preconditions

- Demo Docker stack running: `docker compose -f docker-compose.demo.yml up -d --build` from worktree root
- All 3 services healthy: `docker compose -f docker-compose.demo.yml ps` shows triplestore, api, frontend running
- No other service on ports 3902 or 8902
- A web browser (or curl) available for testing

## Smoke Test

Open `http://localhost:3902/browser/` in a fresh browser (no cookies). The workspace should render immediately — no login page, no setup wizard, no redirect.

## Test Cases

### 1. Anonymous workspace access (no login redirect)

1. Open a fresh incognito/private browser window
2. Navigate to `http://localhost:3902/browser/`
3. **Expected:** Page loads with HTTP 200, URL stays on `/browser/` (not redirected to `/login.html` or `/setup.html`), workspace container is visible with explorer sidebar

### 2. Auth status returns demo-mode values

1. Run: `curl -s http://localhost:3902/api/auth/status | jq .`
2. **Expected:** Response is `{"setup_complete": true, "setup_mode": false}` — no 401, no redirect

### 3. Health check still works

1. Run: `curl -s http://localhost:3902/api/health`
2. **Expected:** HTTP 200 with health check JSON response

### 4. POST to /api/commands blocked with 403 JSON

1. Run: `curl -s -X POST http://localhost:3902/api/commands -H 'Content-Type: application/json' -d '{"type":"object.create","data":{"type_iri":"urn:test"}}' -w '\n%{http_code}\n%{content_type}'`
2. **Expected:** HTTP 403, body contains `{"error": "Demo instance is read-only"}`, Content-Type is `application/json`

### 5. PUT method blocked

1. Run: `curl -s -X PUT http://localhost:3902/api/commands -w '\n%{http_code}'`
2. **Expected:** HTTP 403 with read-only JSON error

### 6. DELETE method blocked

1. Run: `curl -s -X DELETE http://localhost:3902/api/commands -w '\n%{http_code}'`
2. **Expected:** HTTP 403 with read-only JSON error

### 7. PATCH method blocked

1. Run: `curl -s -X PATCH http://localhost:3902/api/commands -w '\n%{http_code}'`
2. **Expected:** HTTP 403 with read-only JSON error

### 8. htmx POST route blocked

1. Run: `curl -s -X POST http://localhost:3902/browser/objects/test/body -w '\n%{http_code}'`
2. **Expected:** HTTP 403 with read-only JSON error (htmx POST routes are also blocked)

### 9. CORS OPTIONS preflight passes through

1. Run: `curl -s -X OPTIONS http://localhost:3902/api/commands -w '\n%{http_code}'`
2. **Expected:** HTTP 204 (OPTIONS is in the allow list, not blocked by write guard)

### 10. GET read routes return 200

1. Run: `curl -s -o /dev/null -w '%{http_code}' http://localhost:3902/browser/nav-tree`
2. **Expected:** HTTP 200 (read routes pass through nginx normally)

### 11. Non-demo-mode unaffected

1. Run: `cd backend && DEMO_MODE=false .venv/bin/python -c "from app.auth.dependencies import get_current_user; print('OK')"`
2. **Expected:** Prints "OK" — module loads without error when demo_mode is disabled

## Edge Cases

### Fresh instance with no models installed

1. Start the demo stack fresh (empty volumes)
2. Navigate to `http://localhost:3902/browser/`
3. **Expected:** Workspace renders (may be empty), no setup wizard redirect, no 500 error. The auth bypass and setup wizard bypass work even when no models or data exist.

### Direct API access bypassing nginx

1. Run: `curl -s -X POST http://localhost:8902/api/commands -H 'Content-Type: application/json' -d '{"type":"object.create","data":{"type_iri":"urn:test"}}'`
2. **Expected:** This MAY succeed (nginx is the write-blocking layer). The API port 8902 is exposed for seeding and debugging. In production deployment (S04), only port 3902 should be exposed publicly.

### Concurrent anonymous visitors

1. Open two separate incognito windows
2. Navigate both to `http://localhost:3902/browser/`
3. **Expected:** Both see the workspace. Neither interferes with the other. The synthetic user is transient (not persisted to DB), so no session collision occurs.

## Failure Signals

- **302 redirect to `/login.html`** — auth bypass not working. Check: `docker compose -f docker-compose.demo.yml exec api env | grep DEMO_MODE` should show `DEMO_MODE=true`
- **302 redirect to `/setup.html`** — setup wizard bypass not working. Check: `curl http://localhost:3902/api/auth/status` should return `{"setup_complete": true, "setup_mode": false}`
- **POST returns 200/500 instead of 403** — nginx write-blocking not active. Check: the frontend container is using `nginx.demo.conf` not `nginx.conf`. Run `docker compose -f docker-compose.demo.yml exec frontend cat /etc/nginx/conf.d/default.conf | head -5` — should show the demo config comment.
- **403 with `text/plain` Content-Type** — the error_page pattern is broken. The named location `@read_only` must set `default_type application/json`.
- **Frontend container won't start** — nginx config syntax error. Check `docker compose -f docker-compose.demo.yml logs frontend`.

## Requirements Proved By This UAT

- DEMO-01 — Anonymous visitor sees workspace without login (tests 1, 2, 3)
- DEMO-02 — All write methods return 403 JSON (tests 4-8, correct content-type)

## Not Proven By This UAT

- DEMO-03 through DEMO-10 — Sample data, tour, dashboard, CTA, deployment, reset (S02-S04)
- SSL termination — only local HTTP tested (S04)
- Periodic reset mechanism — not yet implemented (S04)
- Comprehensive endpoint coverage — tests cover representative endpoints, not every single route

## Notes for Tester

- The demo stack uses separate Docker volumes (`rdf4j_demo_data`, `sempkm_demo_data`) — it won't interfere with the dev or test stacks
- Port 3902 is the frontend (nginx), port 8902 is the API direct — only 3902 has write-blocking
- The `guest` role on the synthetic user means SPARQL queries will be scoped to current graph only (not all graphs)
- The pre-existing test failure in `test_jira_sync_engine.py` is unrelated to this slice
