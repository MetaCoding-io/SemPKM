---
id: T03
parent: S01
milestone: M025
provides:
  - E2E Playwright test proving DEMO-01 (anonymous workspace access) and DEMO-02 (write-blocking) against live demo Docker stack
  - Playwright demo project in config with dedicated global setup health check on port 3902
  - Fix for demo-mode /api/auth/status returning setup_complete=true to prevent setup wizard redirect
key_files:
  - e2e/tests/50-demo/demo-read-only.spec.ts
  - e2e/playwright.config.ts
  - e2e/fixtures/test-harness.ts
  - backend/app/auth/router.py
key_decisions:
  - Added `demo` project to playwright.config.ts (matching federation pattern) so demo tests use port 3902 and skip the test-stack health check
  - Fixed /api/auth/status to return setup_complete=true, setup_mode=false when DEMO_MODE=true — without this, fresh instances redirect to setup wizard even with auth bypass
patterns_established:
  - Demo E2E tests use `--project=demo` which triggers the demo health check (port 3902) in globalSetup, avoiding the port-3901 test-stack dependency
observability_surfaces:
  - Playwright HTML report at e2e/playwright-report/ shows pass/fail per test with screenshots on failure
  - If demo stack is not running, all 4 tests fail with connection-refused (distinguishable from assertion failures)
duration: 20m
verification_result: passed
completed_at: 2026-03-20T04:20:00-04:00
blocker_discovered: false
---

# T03: E2E Playwright test verifying anonymous access and write-blocking

**Added 4 E2E Playwright tests proving anonymous workspace access and write-blocking against the live demo Docker stack, plus fixed /api/auth/status demo-mode setup bypass**

## What Happened

Created `e2e/tests/50-demo/demo-read-only.spec.ts` with 4 serial test cases exercising the demo Docker stack at `localhost:3902`:

1. **Anonymous workspace access** — navigates to `/browser/`, asserts HTTP 200, verifies the URL stays on `/browser` (no redirect to `/login.html` or `/setup.html`), and confirms the workspace container is visible.
2. **Read routes return 200** — verifies `GET /api/health` and `GET /api/auth/status` pass through nginx correctly.
3. **Write methods blocked with 403 JSON** — tests POST, PUT, DELETE, PATCH, and an htmx POST route, asserting each returns 403 with `"Demo instance is read-only"` JSON body.
4. **CORS OPTIONS preflight** — verifies OPTIONS on `/api/commands` returns 204 (not blocked by the write guard).

During implementation, discovered that DEMO_MODE bypassed auth but not the setup wizard: fresh instances have `setup_mode=true`, and the client-side JS (`auth.js`) checks `/api/auth/status` and redirects to `/setup.html`. Fixed by adding a demo-mode guard to the `/api/auth/status` endpoint in `backend/app/auth/router.py` that returns `setup_complete=true, setup_mode=false` immediately when `DEMO_MODE=true`.

Also added a `demo` project to `playwright.config.ts` (matching the existing federation project pattern) and updated `test-harness.ts` global setup to health-check port 3902 when `--project=demo` is specified.

## Verification

1. Started demo stack: `docker compose -f docker-compose.demo.yml up -d --build` — all 3 services healthy
2. Ran E2E tests: `cd e2e && npx playwright test tests/50-demo/demo-read-only.spec.ts --project=demo` — **4 passed (2.3s)**
3. Ran unit tests: `cd backend && .venv/bin/python -m pytest tests/test_demo_mode.py -v` — **14 passed (0.32s)**
4. Ran import check: `DEMO_MODE=false .venv/bin/python -c "from app.auth.dependencies import get_current_user; print('non-demo auth unchanged')"` — **passed**

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx playwright test tests/50-demo/demo-read-only.spec.ts --project=demo` | 0 | ✅ pass | 4.2s |
| 2 | `.venv/bin/python -m pytest tests/test_demo_mode.py -v` | 0 | ✅ pass | 3.3s |
| 3 | `DEMO_MODE=false .venv/bin/python -c "from app.auth.dependencies import get_current_user; print('non-demo auth unchanged')"` | 0 | ✅ pass | 3.0s |

## Diagnostics

- **Run demo tests**: `cd e2e && npx playwright test tests/50-demo/demo-read-only.spec.ts --project=demo` (requires demo stack running on port 3902)
- **View test report**: `cd e2e && npx playwright show-report` — shows screenshots and traces on failure
- **Verify auth/status fix**: `curl -s http://localhost:3902/api/auth/status | jq .` should return `{"setup_complete": true, "setup_mode": false}` when DEMO_MODE=true
- **Stack not running**: All 4 tests fail with connection-refused errors — check `docker compose -f docker-compose.demo.yml ps`

## Deviations

- **Fixed /api/auth/status for demo mode** — Not in the original task plan. Fresh demo instances have `setup_mode=true`, causing client JS to redirect to `/setup.html` before the auth bypass can take effect. Added a 3-line guard to `backend/app/auth/router.py` that short-circuits the status endpoint in demo mode.
- **Added demo project to playwright.config.ts** — The global setup health-checks port 3901 (test stack), which blocks demo tests. Added a `demo` project entry and corresponding detection in `test-harness.ts` (mirroring the existing federation pattern).
- **Used `data-testid="workspace"` selector** instead of `#explorer-pane` for workspace visibility check — the workspace container has a stable test ID while the explorer pane selectors varied.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/50-demo/demo-read-only.spec.ts` — New E2E test file with 4 tests proving anonymous access and write-blocking
- `e2e/playwright.config.ts` — Added `demo` project targeting port 3902 with testMatch for `50-demo/` directory
- `e2e/fixtures/test-harness.ts` — Added demo stack detection and health check (port 3902) in global setup
- `backend/app/auth/router.py` — Added demo-mode guard to `/api/auth/status` endpoint returning setup_complete=true
- `.gsd/milestones/M025/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
