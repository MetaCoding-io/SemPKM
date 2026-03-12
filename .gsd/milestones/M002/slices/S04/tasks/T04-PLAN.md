---
estimated_steps: 4
estimated_files: 0
---

# T04: Full E2E verification and route count audit

**Slice:** S04 — Browser Router Refactor
**Milestone:** M002

## Description

Run the complete E2E Playwright suite against the refactored router to prove zero behavior change. This is the definitive verification gate for requirement REF-01. The 52 E2E tests exercise all htmx wiring, template rendering, navigation, CRUD operations, and URL patterns — if they all pass, the refactor is proven safe.

## Steps

1. Rebuild the Docker test stack to pick up the refactored router code: `docker compose -f docker-compose.test.yml build` (or equivalent rebuild command). Start the stack and verify the app starts cleanly — check logs for any import errors or missing route warnings.
2. Run the full Playwright E2E suite: `cd e2e && npx playwright test`. All 52 tests must pass. If any test fails, diagnose the root cause (likely a route registration order issue, missing import, or incorrect sub-router prefix), fix it in the relevant sub-router file, and rerun.
3. Audit route count: run `docker compose -f docker-compose.test.yml exec backend python -c "from app.browser.router import router; print(len(router.routes))"` and verify the count matches the pre-refactor count. Also verify `ls backend/app/browser/*.py | wc -l` shows exactly 8 files.
4. Run the backend unit test suite one final time: `cd backend && .venv/bin/pytest tests/ -v` to confirm the `_validate_iri` import update and all other tests still pass after the complete refactor.

## Must-Haves

- [ ] All 52 E2E Playwright tests pass
- [ ] Route count matches pre-refactor count
- [ ] Docker stack starts cleanly with no import errors
- [ ] All backend unit tests pass
- [ ] 8 `.py` files in `backend/app/browser/`

## Verification

- `cd e2e && npx playwright test` — 52/52 tests pass
- `cd backend && .venv/bin/pytest tests/ -v` — all unit tests pass
- `ls backend/app/browser/*.py | wc -l` — exactly 8
- Docker compose logs show clean startup with all `/browser/*` routes registered

## Observability Impact

- Signals added/changed: None — verification-only task
- How a future agent inspects this: E2E test results in `e2e/playwright-report/`; pytest output
- Failure state exposed: Playwright HTML report with screenshots on failure; pytest traceback output

## Inputs

- All 8 files in `backend/app/browser/` — the fully refactored router (from T01–T03)
- `e2e/tests/**/*.spec.ts` — the 52 existing E2E tests
- `backend/tests/*.py` — the existing unit tests

## Expected Output

- No new files — this is a verification-only task
- Confirmation that all 52 E2E tests pass
- Confirmation that all unit tests pass
- If any failures found: fixes applied to the relevant sub-router files until all tests pass
