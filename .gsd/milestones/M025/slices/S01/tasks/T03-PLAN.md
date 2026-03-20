---
estimated_steps: 5
estimated_files: 1
---

# T03: E2E Playwright test verifying anonymous access and write-blocking

**Slice:** S01 — Read-only enforcement + DEMO_MODE anonymous access
**Milestone:** M025

## Description

Write an E2E Playwright test that exercises the demo Docker stack to prove both DEMO-01 (anonymous workspace access) and DEMO-02 (write-blocking). The test runs against `localhost:3902` (the demo compose port from T02). This is the integration verification that proves the slice actually works end-to-end — a real browser hitting the real demo stack with real nginx write-blocking and real DEMO_MODE auth bypass.

The test does NOT need the authenticated test fixtures used by other E2E tests (no setup token, no login flow). It uses a fresh browser context with no cookies — the whole point is that anonymous access works.

## Steps

1. **Create test directory and file:**
   - Create `e2e/tests/50-demo/demo-read-only.spec.ts`
   - Use `import { test, expect } from '@playwright/test'` (no custom auth fixtures needed)
   - Set `test.describe.configure({ mode: 'serial' })` since tests share the same demo stack state

2. **Test 1: Anonymous workspace access (DEMO-01):**
   - Navigate to `http://localhost:3902/browser/`
   - Assert the page does NOT redirect to `/login.html` or `/setup.html` (check final URL contains `/browser`)
   - Assert the workspace content is visible — look for known workspace elements. The workspace page has identifiable elements like the explorer sidebar. Check for text or selectors that indicate workspace loaded successfully. At minimum, check that the page title or heading indicates the workspace (not a login page).
   - Assert HTTP status is 200 (Playwright `page.goto()` returns a response object)

3. **Test 2: Read routes return 200:**
   - Use `page.request.get()` (Playwright's API testing) to check several read endpoints:
     - `GET /api/health` → 200
     - `GET /api/auth/status` → 200
   - These verify that the demo nginx passes GET requests through correctly

4. **Test 3: Write methods blocked with 403 JSON (DEMO-02):**
   - Use `page.request.post()`, `page.request.put()`, `page.request.delete()`, `page.request.patch()` to test write-blocking on representative endpoints:
     - `POST /api/commands` with body `{"type": "object.create", "data": {"type_iri": "test"}}` → 403
     - `PUT /api/dashboards/fake-id` with empty body → 403
     - `DELETE /api/sparql/saved/fake-id` → 403
     - `PATCH /api/commands` → 403 (even though this endpoint doesn't exist, nginx blocks the method before routing)
   - For each: assert status is 403, and response body contains `"Demo instance is read-only"`
   - Also test `POST /browser/objects/test/body` → 403 (htmx write route)

5. **Test 4: CORS OPTIONS preflight still works:**
   - Use `page.request.fetch()` with method 'OPTIONS' on `/api/commands` → should return 204 (CORS preflight, not blocked by the write guard since OPTIONS is in the allow list)

## Must-Haves

- [ ] Test runs against `localhost:3902` (demo compose port)
- [ ] No auth fixtures or login required — fresh anonymous browser context
- [ ] Anonymous workspace access proven (no redirect to login)
- [ ] At least 4 write methods tested (POST, PUT, DELETE, PATCH) returning 403
- [ ] 403 response body contains the expected JSON error message
- [ ] GET read routes proven to return 200
- [ ] Test file is at `e2e/tests/50-demo/demo-read-only.spec.ts`

## Verification

- Start demo stack: `cd /home/james/Code/SemPKM/.gsd/worktrees/M024 && docker compose -f docker-compose.demo.yml up -d --build`
- Wait for healthy: `docker compose -f docker-compose.demo.yml ps` shows all healthy
- Run test: `cd e2e && npx playwright test tests/50-demo/demo-read-only.spec.ts --project=chromium`
- All assertions pass

## Inputs

- T01 output: `backend/app/auth/dependencies.py` with DEMO_MODE bypass (api container uses this)
- T01 output: `backend/app/config.py` with `demo_mode` setting
- T02 output: `docker-compose.demo.yml` with port 3902 and DEMO_MODE=true
- T02 output: `frontend/nginx.demo.conf` with read-only enforcement
- Existing E2E patterns: `e2e/tests/` directory for Playwright test conventions

## Observability Impact

- **Test output**: `npx playwright test tests/50-demo/demo-read-only.spec.ts --project=chromium` — 4 test cases report pass/fail against the live demo stack. Green = both DEMO-01 and DEMO-02 proven. Any red = regression in anonymous access or write-blocking.
- **Failure inspection**: Playwright HTML report at `e2e/playwright-report/index.html` shows screenshots, traces, and assertion details on failure. Run `npx playwright show-report` to view.
- **CI signal**: If the demo stack is not running (ports 3902/8902 down), all 4 tests fail with connection-refused errors — distinguishable from assertion failures by the error message.
- **Runtime requirement**: Tests require the demo Docker stack to be running (`docker compose -f docker-compose.demo.yml up -d --build`). They do NOT run against the dev or test stacks.

## Expected Output

- `e2e/tests/50-demo/demo-read-only.spec.ts` — New E2E test file with 4 test cases proving anonymous access and write-blocking
