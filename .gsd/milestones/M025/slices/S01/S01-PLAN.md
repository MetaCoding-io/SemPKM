# S01: Read-only enforcement + DEMO_MODE anonymous access

**Goal:** Anonymous visitors can reach the workspace without login and all write operations return 403 — proven by unit tests and E2E Playwright test against a running demo Docker stack.
**Demo:** A fresh browser hits the demo compose stack at `/browser/` and sees the workspace immediately (no login, no setup wizard). POST to `/api/commands` returns `403 {"error": "Demo instance is read-only"}`. All GET routes (explorer, graph, table, object view, canvas) return 200.

## Must-Haves

- `DEMO_MODE=true` env var in `backend/app/config.py` and `backend/app/auth/dependencies.py` that makes `get_current_user` return a synthetic read-only guest user (id, email, display_name, role="guest") without checking session/cookie
- `_is_html_route()` in `main.py` must NOT redirect 401→login when DEMO_MODE is active (the synthetic user avoids 401s entirely, but defense-in-depth)
- Read-only nginx config (`frontend/nginx.demo.conf`) that blocks all POST/PUT/DELETE/PATCH methods with 403 JSON, except `/api/health` and `/api/auth/status` (needed for health checks and frontend JS auth detection)
- `docker-compose.demo.yml` that extends the base compose with `DEMO_MODE=true`, the demo nginx config, separate volumes, and a separate port
- Unit tests proving DEMO_MODE auth bypass returns the synthetic user and that non-DEMO_MODE is unaffected
- E2E Playwright test proving anonymous workspace access and write-blocking against the live demo Docker stack

## Proof Level

- This slice proves: integration (real Docker stack, not mocks)
- Real runtime required: yes (Docker Compose demo stack must be running)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_demo_mode.py -v` — unit tests for DEMO_MODE auth bypass (synthetic user returned, guest role, non-demo-mode unchanged)
- `cd e2e && npx playwright test tests/50-demo/demo-read-only.spec.ts` — E2E test against demo Docker stack proving: (a) GET `/browser/` returns 200 workspace HTML, (b) POST `/api/commands` returns 403, (c) PUT/DELETE/PATCH on various endpoints return 403, (d) GET read routes return 200
- `cd backend && DEMO_MODE=false python -c "from app.auth.dependencies import get_current_user; print('non-demo auth unchanged')"` — verifies module loads without error when demo_mode is disabled (failure-path: import errors or misconfigured settings surface immediately)

## Observability / Diagnostics

- Runtime signals: `logger.info("DEMO_MODE active — returning synthetic guest user")` on first request in demo mode
- Inspection surfaces: `GET /api/health` returns 200 (unchanged). `GET /api/auth/status` returns `{"setup_complete": true/false, "setup_mode": true/false}` — works without auth.
- Failure visibility: If DEMO_MODE bypass fails, workspace returns 302→login.html (visible in browser/curl). nginx 403 on write attempts is the expected behavior, not a failure.

## Integration Closure

- Upstream surfaces consumed: `backend/app/auth/dependencies.py` (get_current_user), `backend/app/config.py` (Settings), `frontend/nginx.conf` (base routing), `docker-compose.yml` (base services)
- New wiring introduced: `docker-compose.demo.yml` composes DEMO_MODE env + demo nginx config into a deployable stack
- What remains before the milestone is truly usable end-to-end: S02 (sample data), S03 (tour + dashboard + CTA), S04 (SSL + deployment + docs)

## Tasks

- [x] **T01: Implement DEMO_MODE auth bypass with unit tests** `est:45m`
  - Why: The foundation for all demo functionality — without this, anonymous visitors can't reach the workspace. D244 specifies the approach: `DEMO_MODE=true` env var makes `get_current_user` return a synthetic guest user.
  - Files: `backend/app/config.py`, `backend/app/auth/dependencies.py`, `backend/tests/test_demo_mode.py`
  - Do: Add `demo_mode: bool = False` to Settings. In `get_current_user`, check `settings.demo_mode` first — if True, return a synthetic User object (fixed UUID, email="demo@sempkm.app", display_name="Demo Visitor", role="guest") without any DB lookup. Also update `optional_current_user` and `get_current_user_or_api` with the same check. Write unit tests covering: synthetic user returned in demo mode, correct guest role, normal auth still works when demo_mode=False, all three dependency functions handle demo mode.
  - Verify: `cd backend && python -m pytest tests/test_demo_mode.py -v` — all tests pass
  - Done when: DEMO_MODE=true causes all three auth dependencies to return the synthetic guest user without DB access; DEMO_MODE=false (default) behavior is completely unchanged

- [x] **T02: Create demo nginx config and docker-compose.demo.yml** `est:30m`
  - Why: The nginx read-only layer is defense-in-depth (D245) — even if the auth bypass fails, writes are blocked. The compose file wires everything together into a deployable demo stack.
  - Files: `frontend/nginx.demo.conf`, `docker-compose.demo.yml`
  - Do: Create `frontend/nginx.demo.conf` by copying `frontend/nginx.conf` and adding a default-deny block at the top of the `server {}` that returns `403 '{"error": "Demo instance is read-only"}'` for all POST/PUT/DELETE/PATCH methods, EXCEPT: `/api/health` (health checks), `/api/auth/status` (frontend auth detection — GET-only endpoint, no write risk). Use `$request_method` matching and `return 403` with JSON content-type. Create `docker-compose.demo.yml` that defines the same 3 services (triplestore, api, frontend) with: `DEMO_MODE: "true"` env on api, demo nginx.conf mounted on frontend, separate volumes (rdf4j_demo_data, sempkm_demo_data), separate port (3902:80 for frontend, 8902:8000 for api), separate network (sempkm-demo). Verify the nginx config is valid syntax.
  - Verify: `docker run --rm -v $(pwd)/frontend/nginx.demo.conf:/etc/nginx/conf.d/default.conf:ro nginx:stable-alpine nginx -t` — config syntax OK
  - Done when: `docker-compose.demo.yml` can start a 3-service stack with DEMO_MODE and read-only nginx, and `nginx -t` passes on the demo config

- [x] **T03: E2E Playwright test verifying anonymous access and write-blocking** `est:45m`
  - Why: The integration proof that the slice actually works — a real browser hits the demo Docker stack and verifies both anonymous workspace access and comprehensive write blocking. This retires the DEMO-01 and DEMO-02 requirements.
  - Files: `e2e/tests/50-demo/demo-read-only.spec.ts`
  - Do: Create a Playwright test that starts the demo Docker stack (or assumes it's running), then: (1) navigates to `http://localhost:3902/browser/` and asserts 200 with workspace content (look for known workspace elements like `#workspace` or explorer pane), (2) sends POST to `/api/commands` with a sample command payload and asserts 403 + JSON error body, (3) sends PUT/DELETE/PATCH to representative endpoints and asserts 403, (4) sends GET to read routes (`/api/health`, `/browser/nav-tree`, `/browser/views/generic/table`) and asserts 200. Use fetch/axios from the test for API assertions. The test should use `localhost:3902` (the demo compose port). Include test setup/teardown instructions in comments.
  - Verify: Start demo stack with `docker compose -f docker-compose.demo.yml up -d --build`, wait for healthy, then `cd e2e && npx playwright test tests/50-demo/demo-read-only.spec.ts` — all assertions pass
  - Done when: E2E test passes proving anonymous workspace access (no login redirect) and comprehensive write-blocking (403 on all mutation methods)

## Files Likely Touched

- `backend/app/config.py`
- `backend/app/auth/dependencies.py`
- `backend/tests/test_demo_mode.py`
- `frontend/nginx.demo.conf`
- `docker-compose.demo.yml`
- `e2e/tests/50-demo/demo-read-only.spec.ts`
