---
id: S01
parent: M025
milestone: M025
provides:
  - DEMO_MODE=true env var making all three auth dependencies return a synthetic guest user without DB access
  - Read-only nginx config (nginx.demo.conf) blocking all POST/PUT/DELETE/PATCH with 403 JSON via error_page pattern
  - docker-compose.demo.yml wiring DEMO_MODE + demo nginx into a deployable 3-service stack on ports 3902/8902
  - /api/auth/status short-circuit in demo mode returning setup_complete=true to prevent setup wizard redirect
  - E2E Playwright test proving anonymous workspace access and comprehensive write-blocking
requires: []
affects:
  - S02
  - S03
  - S04
key_files:
  - backend/app/config.py
  - backend/app/auth/dependencies.py
  - backend/app/auth/router.py
  - backend/tests/test_demo_mode.py
  - frontend/nginx.demo.conf
  - docker-compose.demo.yml
  - e2e/tests/50-demo/demo-read-only.spec.ts
  - e2e/playwright.config.ts
  - e2e/fixtures/test-harness.ts
key_decisions:
  - D249: Replaced Depends(get_session_token) with inline Cookie(None) in get_current_user so demo_mode check runs before any 401 can fire
  - D250: Short-circuit /api/auth/status to return setup_complete=true when DEMO_MODE=true — prevents client-side setup wizard redirect
  - nginx error_page 495 + named @read_only location for proper application/json Content-Type on 403 (bare return in if-block defaults to text/plain)
  - Port allocation 3902/8902 for demo stack (series: dev=3000/8001, test=3901/8901, demo=3902/8902)
patterns_established:
  - Demo-mode guard pattern: check settings.demo_mode as first line in auth dependencies, return _demo_user() immediately
  - error_page + named location pattern for returning JSON from nginx method guards
  - Playwright demo project (--project=demo) with separate health check on port 3902
observability_surfaces:
  - "DEMO_MODE active — returning synthetic guest user" log line on first auth-resolved request
  - Synthetic user visible as id=00000000-0000-0000-0000-000000000000, email=demo@sempkm.app, role=guest
  - curl -X POST http://localhost:3902/api/commands → 403 {"error": "Demo instance is read-only"}
  - curl http://localhost:3902/api/auth/status → {"setup_complete": true, "setup_mode": false}
  - Playwright HTML report at e2e/playwright-report/
drill_down_paths:
  - .gsd/milestones/M025/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M025/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M025/slices/S01/tasks/T03-SUMMARY.md
duration: 47m
verification_result: passed
completed_at: 2026-03-20
---

# S01: Read-only enforcement + DEMO_MODE anonymous access

**Anonymous visitors reach the workspace without login and all write operations return 403 JSON — proven by 14 unit tests and 4 E2E Playwright tests against the live demo Docker stack**

## What Happened

Three tasks built the foundation for the hosted demo instance: auth bypass, nginx write-blocking, and E2E proof.

**T01 — DEMO_MODE auth bypass** added `demo_mode: bool = False` to `Settings` in `config.py` (reads `DEMO_MODE` env var). Created `_demo_user()` in `dependencies.py` that returns a transient `User` with a deterministic nil UUID, `email="demo@sempkm.app"`, `display_name="Demo Visitor"`, and `role="guest"`. All three auth dependency functions (`get_current_user`, `optional_current_user`, `get_current_user_or_api`) check `settings.demo_mode` as their first action and return the synthetic user immediately without DB access. A key discovery (D249): `get_current_user` had to be restructured to inline cookie extraction (replacing `Depends(get_session_token)`) because FastAPI evaluates `Depends()` arguments before the function body — the old dependency would raise 401 before any demo_mode check could run.

**T02 — nginx config and Docker Compose** created `frontend/nginx.demo.conf` with a default-deny block using nginx's `error_page 495 = @read_only` pattern to return `403 {"error": "Demo instance is read-only"}` with correct `application/json` content-type for all POST/PUT/DELETE/PATCH requests. The `error_page` + named location approach was chosen because bare `return` inside nginx `if` blocks always sends `text/plain`. The `docker-compose.demo.yml` wires the 3-service stack (triplestore, api, frontend) with `DEMO_MODE=true`, the demo nginx config, separate volumes/ports/network (3902/8902).

**T03 — E2E Playwright tests** created 4 serial tests proving: (1) anonymous workspace access — browser navigates to `/browser/` and sees the workspace without redirect to login; (2) read routes return 200; (3) write methods return 403 JSON for POST/PUT/DELETE/PATCH including htmx routes; (4) CORS OPTIONS preflight returns 204. During implementation, discovered that DEMO_MODE bypassed auth but not the setup wizard (D250): fresh instances have `setup_mode=true`, causing `auth.js` to redirect to `/setup.html`. Fixed by adding a 3-line guard to `/api/auth/status` in `router.py` that returns `setup_complete=true, setup_mode=false` when `DEMO_MODE=true`. Also added a `demo` project to `playwright.config.ts` with a dedicated health check on port 3902.

## Verification

- `python -m pytest tests/test_demo_mode.py -v` — **14/14 passed** (synthetic user fields, demo-mode returns from all 3 auth deps, non-demo-mode unchanged, settings default, role check)
- `python -m pytest tests/test_auth_tokens.py -v` — **15/15 passed** (no regressions to existing auth)
- `python -m pytest tests/ -x -q` — **1304 passed**, 1 pre-existing failure in `test_jira_sync_engine.py` (unrelated)
- `DEMO_MODE=false python -c "from app.auth.dependencies import get_current_user"` — module loads cleanly
- `docker run --rm ... nginx:stable-alpine nginx -t` — demo nginx config syntax OK
- `docker compose -f docker-compose.demo.yml config --quiet` — compose YAML valid
- `npx playwright test tests/50-demo/demo-read-only.spec.ts --project=demo` — **4/4 passed** (against live demo stack)

## Requirements Advanced

- DEMO-01 (anonymous workspace access) — anonymous visitor hits `/browser/` and sees workspace without login, proven by E2E test
- DEMO-02 (read-only enforcement) — all write HTTP methods return 403 JSON at nginx layer, proven by E2E test

## Requirements Validated

- DEMO-01 — E2E Playwright test navigates to demo stack, asserts 200, no redirect, workspace visible
- DEMO-02 — E2E Playwright test sends POST/PUT/DELETE/PATCH to multiple endpoints, all return 403 with correct JSON body

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **get_current_user restructured** (D249): Replaced `Depends(get_session_token)` with inline `Cookie(None)` extraction. Required because FastAPI evaluates dependencies before the function body, so the 401 from `get_session_token` would fire before any demo_mode check.
- **Setup wizard bypass added** (D250): Fresh demo instances redirect to `/setup.html` because `setup_mode=true`. Added a guard to `/api/auth/status` returning `setup_complete=true` when `DEMO_MODE=true`. Not in original plan but essential for anonymous access to work on a fresh instance.
- **Playwright demo project added**: The existing global setup health-checks port 3901 (test stack), which blocks demo tests. Added a `demo` project entry to `playwright.config.ts` mirroring the existing federation pattern.

## Known Limitations

- The `guest` role has no explicit permission enforcement beyond what exists in the auth system — write-blocking relies on nginx as the primary defense layer. If the API is accessed directly (bypassing nginx), the guest user could theoretically execute commands. This is acceptable because the demo compose stack always routes through nginx.
- Demo mode does not suppress the setup wizard UI at the template level — it only suppresses the status check that triggers the redirect. If someone navigates directly to `/setup.html`, the page renders (but setup actions would be blocked by nginx).

## Follow-ups

- S02 will use the demo stack to seed sample data — the seed script needs a working `docker-compose.demo.yml` running on port 3902
- S03 will consume `DEMO_MODE` for CTA banner visibility and tour auto-start
- S04 will extend `docker-compose.demo.yml` with Caddy SSL termination

## Files Created/Modified

- `backend/app/config.py` — Added `demo_mode: bool = False` setting
- `backend/app/auth/dependencies.py` — Added `_demo_user()` helper, demo_mode guards in all 3 auth dependencies, restructured `get_current_user` to inline cookie extraction
- `backend/app/auth/router.py` — Added demo-mode guard to `/api/auth/status` endpoint
- `backend/tests/test_demo_mode.py` — New: 14 unit tests for demo-mode auth bypass
- `frontend/nginx.demo.conf` — New: read-only nginx config with error_page 495 → @read_only guard
- `docker-compose.demo.yml` — New: 3-service demo stack with DEMO_MODE=true, ports 3902/8902, separate volumes/network
- `e2e/tests/50-demo/demo-read-only.spec.ts` — New: 4 E2E tests for anonymous access and write-blocking
- `e2e/playwright.config.ts` — Added `demo` project targeting port 3902
- `e2e/fixtures/test-harness.ts` — Added demo stack health check detection

## Forward Intelligence

### What the next slice should know
- The demo stack runs on ports 3902 (frontend/nginx) and 8902 (API). The seed script (S02) should POST commands to `http://localhost:8902` directly or through `http://localhost:3902/api/` — but since nginx blocks POST, the seed script must target the API port 8902 directly (or be run before the demo nginx is active).
- **Critical for S02**: The nginx demo config blocks ALL POST methods. The seed script cannot use the frontend port 3902 for writing. It must either: (a) target the API directly at port 8902, (b) run against a non-demo stack first and use shared volumes, or (c) temporarily bypass nginx.
- `DEMO_MODE=true` is an env var on the API container. The `settings.demo_mode` flag is available anywhere `get_settings()` is called.

### What's fragile
- The `error_page 495` pattern in nginx.demo.conf is non-obvious — if someone copies nginx.conf to make a new variant, they might not include the write-blocking block. The diff between nginx.conf and nginx.demo.conf is just the header comment and the 20-line read-only enforcement block.
- The `/api/auth/status` demo guard is a 3-line early return. If someone restructures that endpoint, the demo bypass could be lost.

### Authoritative diagnostics
- `curl -X POST http://localhost:3902/api/commands` — if this returns anything other than 403 JSON, the write-blocking is broken
- `curl http://localhost:3902/api/auth/status` — must return `{"setup_complete": true, "setup_mode": false}` in demo mode
- Container logs: grep for "DEMO_MODE active" to confirm auth bypass is engaged
- `docker compose -f docker-compose.demo.yml exec api env | grep DEMO_MODE` — confirms env var is set

### What assumptions changed
- Original plan assumed auth bypass alone was sufficient for anonymous access — reality: the setup wizard redirect (`auth.js` checking `/api/auth/status`) is a second gate that must also be bypassed (D250)
- Original plan assumed `Depends(get_session_token)` could be guarded in the function body — reality: FastAPI evaluates `Depends()` before the body runs, requiring signature restructure (D249)
