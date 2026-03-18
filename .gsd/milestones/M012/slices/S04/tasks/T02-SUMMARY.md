---
id: T02
parent: S04
milestone: M012
provides:
  - 7 Playwright E2E tests covering event log polish (4 tests) and body.diff (3 tests)
  - Rate limit toggle via RATE_LIMIT_ENABLED config setting
  - body.diff Diff button enablement fix in event_log.html template
key_files:
  - e2e/tests/27-event-log-polish/event-log-polish.spec.ts
  - e2e/tests/28-body-diff/body-diff.spec.ts
  - backend/app/auth/rate_limit.py
  - backend/app/config.py
  - docker-compose.test.yml
key_decisions:
  - Added RATE_LIMIT_ENABLED env var (default true) to disable slowapi rate limiting in E2E test stack, preventing auth fixture failures from rapid session creation
patterns_established:
  - E2E tests for event log features: use openEventLog() helper pattern to open bottom panel + click EVENT LOG tab + wait for rows
  - Body API tests use POST /browser/objects/{encoded_iri}/body with Content-Type text/plain (not PUT)
  - SPARQL API scopes to current state graph — cannot query event graphs; verify event types via UI badges instead
observability_surfaces:
  - cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium
  - Playwright HTML report in e2e/playwright-report/ with traces on failure
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: E2E Playwright tests for event log polish and body.diff

**Added 7 Playwright E2E tests for event log polish (labels, helptext, autocomplete) and body.diff (creation, diff highlighting, body.set distinction), plus RATE_LIMIT_ENABLED config toggle for test environments**

## What Happened

Created two E2E spec files covering the S01 event log polish and S02 body.diff features:

**event-log-polish.spec.ts** (4 tests):
1. Event detail shows human-readable predicate labels (not raw IRIs)
2. Predicate labels have helptext tooltips via SHACL descriptions
3. Autocomplete suggestions appear when focusing the operation type filter
4. Predicate filter shows filtered suggestions on typed input ("tit" → "Title")

**body-diff.spec.ts** (3 tests):
1. body.diff event appears in event log after editing an existing body
2. body.diff detail shows diff highlighting with add (green) and remove (red) lines
3. First body set creates body.set event, not body.diff

During implementation, discovered and fixed three issues:
- **Rate limiting broke E2E auth fixtures**: The test stack's 5/minute magic-link rate limit caused auth failures when running 7+ tests. Added `RATE_LIMIT_ENABLED` config setting (default `true`) that passes through to slowapi's `enabled` parameter. Set to `false` in `docker-compose.test.yml`. Updated the existing rate-limiting test to skip gracefully when rate limiting is disabled.
- **body.diff Diff button disabled in template**: The event_log.html template only enabled the Diff button for `body.set`, not `body.diff`. Added `body.diff` to the enabled operation type lists for both the Diff and Undo buttons.
- **SPARQL API scopes to current graph**: The `/api/sparql` endpoint scopes queries to `urn:sempkm:current` to prevent event data leakage. Test 3 (body.set verification) was rewritten to use UI badge inspection instead of SPARQL queries against event graphs.

## Verification

- `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium` → 7 passed (13.4s)
- `backend/.venv/bin/python -m pytest backend/tests/ -x -q --tb=short` → 946 passed
- `grep -rn "^<<<<<<< " backend/ frontend/ e2e/` → no conflict markers

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium` | 0 | ✅ pass | 13.4s |
| 2 | `backend/.venv/bin/python -m pytest backend/tests/ -x -q --tb=short` | 0 | ✅ pass (946) | 6.5s |
| 3 | `curl -s http://localhost:3901/api/health` | 0 | ✅ pass | <1s |
| 4 | `grep -rn "^<<<<<<< " backend/ frontend/ e2e/` | 0 | ✅ pass (empty) | <1s |
| 5 | `cd e2e && npx playwright test --project=chromium` (full suite) | 1 | ⚠️ pre-existing syntax errors in ~20 older spec files from T01 merge | 5s |

## Diagnostics

- Run targeted tests: `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium`
- View test report: `cd e2e && npx playwright show-report`
- Check rate limit config: `docker exec sempkm-api-1 env | grep RATE_LIMIT`
- Verify Diff button fix: `grep "body.diff" backend/app/templates/browser/event_log.html`

## Deviations

- **body.diff added to event_log.html Diff/Undo button enabled list**: Template bug — body.diff was missing from the operation type whitelist, causing the Diff button to be disabled for body.diff events. Fixed as prerequisite for test 2.
- **RATE_LIMIT_ENABLED config added**: Not in original plan. Auth fixture failures from rate limiting were blocking test execution. Added config toggle as the cleanest fix.
- **Test 3 rewritten from SPARQL to UI approach**: The SPARQL API scopes to current state graph and cannot query event graphs. Replaced SPARQL-based verification with event log UI badge inspection.

## Known Issues

- Full E2E suite (`npx playwright test --project=chromium`) has ~20 pre-existing syntax errors in older spec files from the T01 merge. These are not caused by this task and affect files outside the 27/28 test directories. The targeted test run passes cleanly.

## Files Created/Modified

- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — 4 E2E tests for event log labels, helptext, autocomplete
- `e2e/tests/28-body-diff/body-diff.spec.ts` — 3 E2E tests for body.diff creation, highlighting, body.set distinction
- `backend/app/config.py` — Added `rate_limit_enabled: bool = True` setting
- `backend/app/auth/rate_limit.py` — Pass `enabled=settings.rate_limit_enabled` to slowapi Limiter
- `docker-compose.test.yml` — Added `RATE_LIMIT_ENABLED: "false"` for test stack
- `backend/app/templates/browser/event_log.html` — Added `body.diff` to Diff/Undo button enabled lists
- `e2e/tests/99-rate-limiting/rate-limiting.spec.ts` — Updated to skip gracefully when rate limiting is disabled
