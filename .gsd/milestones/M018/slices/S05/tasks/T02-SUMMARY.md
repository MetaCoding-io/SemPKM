---
id: T02
parent: S05
milestone: M018
provides:
  - googleCalendarSync selector block in e2e/helpers/selectors.ts
  - Playwright E2E test file for Google Calendar sync lifecycle (incomplete — needs debugging)
key_files:
  - e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - OAuth simulation via ownerRequest.post() to get 303 redirect + extract state param + navigate to callback URL directly
patterns_established:
  - OAuth E2E testing pattern: POST to OAuth initiation endpoint with maxRedirects:0, extract state from Location header, navigate browser to callback URL with mock code + state
observability_surfaces:
  - Playwright HTML report at e2e/playwright-report/
  - Failure screenshots at e2e/test-results/36-google-calendar-sync-*/
  - App subprocess logs via docker compose logs api
duration: partial
verification_result: failed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Playwright E2E test for Google Calendar sync lifecycle

**Added googleCalendarSync selectors and E2E test file; test fails at Phase 3 (connect fragment) due to app subprocess returning 500 on /_fragments/connect — requires debugging the subprocess error**

## What Happened

Created the `googleCalendarSync` selector block in `e2e/helpers/selectors.ts` with 13 selectors matching the connect.html and connect_status.html templates. Created `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` (~280 lines) following the github-sync.spec.ts pattern with all 6 phases: cleanup → install basic-pkm → install google-calendar → enter credentials + OAuth simulation → select calendars + sync → SPARQL verification → admin detail + cleanup.

The test is structurally complete and recognized by Playwright (`--list` shows the test). However, execution fails at Phase 3 because the google-calendar app subprocess returns HTTP 500 on `GET /_fragments/connect`. The Docker test stack starts correctly from the worktree with the mock-google-calendar service healthy and env vars (`GCAL_API_URL`, `GOOGLE_TOKEN_URL`) properly set on the API container. The UDS socket exists at `/tmp/sempkm-app-google-calendar.sock` and the subprocess responds — but with 500 Internal Server Error.

Investigation confirmed:
- mock-google-calendar service is healthy (`/health` returns 200)
- API container has correct env vars
- UDS socket exists and subprocess accepts connections
- The subprocess returns a generic "Internal Server Error" with no traceback in the proxy response
- The subprocess error is NOT in the test code — it's in the app subprocess itself

## Resume Notes

The next executor should:

1. **Debug the 500 from the app subprocess.** The error is in the google-calendar `connect_fragment()` handler. To get the actual traceback:
   - Check app subprocess stderr: look at `backend/app/apps/manager.py` `_log_buffers` — the admin detail page at `/admin/apps/google-calendar` renders these logs
   - Or add debug logging to `apps/google-calendar/app.py` `connect_fragment()` and rebuild
   - The likely cause is a template rendering error or a missing dependency — the subprocess's venv may not have all required packages, or a Jinja2 template variable is undefined

2. **After fixing the 500:** re-run `npx playwright test --project=chromium tests/36-google-calendar-sync/` from the `e2e/` directory

3. **Important Docker context:** The test stack MUST run from the worktree (`/home/james/Code/SemPKM/.gsd/worktrees/M018/`) because the main tree doesn't have the mock-google-calendar service. Container prefix is `m018-`.

4. **The test file itself is complete.** The OAuth simulation flow, SPARQL verification, and all phases are coded. Only the infrastructure issue (subprocess 500) needs fixing.

## Verification

- `npx playwright test --list --project=chromium tests/36-google-calendar-sync/` — ✅ lists 1 test
- `npx playwright test --project=chromium tests/36-google-calendar-sync/` — ❌ fails at Phase 3 (connect fragment 500)
- Mock server selftest — not re-verified in this task (T01 verified)
- SPARQL verification — not reached due to Phase 3 failure

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx playwright test --list --project=chromium tests/36-google-calendar-sync/` | 0 | ✅ pass | 2s |
| 2 | `npx playwright test --project=chromium tests/36-google-calendar-sync/` | 1 | ❌ fail | 167s |

## Diagnostics

- **Subprocess 500:** `docker compose -f docker-compose.test.yml exec -T api python -c "import httpx, asyncio; ..."` against `/tmp/sempkm-app-google-calendar.sock` — returns 500
- **Mock health:** `docker compose -f docker-compose.test.yml logs mock-google-calendar` — shows health checks passing
- **Env vars:** `docker compose -f docker-compose.test.yml exec -T api env | grep -E 'GCAL|GOOGLE_TOKEN'` — both set correctly
- **Socket exists:** `docker compose -f docker-compose.test.yml exec -T api python -c "import os; print(os.path.exists('/tmp/sempkm-app-google-calendar.sock'))"` — True

## Deviations

- Docker test stack had to be brought down from main tree and restarted from worktree to include the mock-google-calendar service — this was expected per KNOWLEDGE.md
- npm install required in worktree e2e/ directory for Playwright dependencies

## Known Issues

- App subprocess returns 500 on `/_fragments/connect` — root cause not yet identified. Likely a template rendering error or missing context variable in the `connect_fragment()` handler. The subprocess log buffer (accessible via admin detail page or `manager.get_logs()`) should contain the actual Python traceback.

## Files Created/Modified

- `e2e/helpers/selectors.ts` — added `googleCalendarSync` selector block with 13 selectors
- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — new, ~280 lines, full lifecycle test
- `.gsd/milestones/M018/slices/S05/tasks/T02-PLAN.md` — added Observability Impact section (preflight fix)
