---
id: T03
parent: S03
milestone: M013
provides:
  - 7 Playwright E2E tests covering all four M013 API-surface endpoints through the full Docker stack
key_files:
  - e2e/tests/30-api-surface/api-surface.spec.ts
key_decisions:
  - Used ownerRequest fixture (authenticated APIRequestContext) instead of page.request for pure API tests — no browser context overhead
  - Added auth-gate test (unauthenticated → non-200) beyond the 5 minimum to verify middleware wiring
  - Added context-query validation test (empty body → 400) to exercise the failure path end-to-end
patterns_established:
  - API-only E2E tests use ownerRequest fixture for session-authenticated HTTP calls without browser navigation
  - Chain tests (shapes test fetches real type IRI from types endpoint) to avoid hardcoded seed-data dependencies
observability_surfaces:
  - Test output: `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — 7 named tests, each identifying the specific endpoint/behavior under test
  - Failure traces: Playwright captures .zip traces on retry for request/response debugging
duration: 15m
verification_result: passed
completed_at: 2026-03-17T19:49:00-04:00
blocker_discovered: false
---

# T03: E2E Playwright test for API surface

**Added 7 Playwright E2E tests exercising all four M013 API endpoints (well-known, types, shapes, context-query) through the full Docker Compose stack with real auth**

## What Happened

Created `e2e/tests/30-api-surface/api-surface.spec.ts` with 7 tests covering:

1. `GET /.well-known/sempkm` — verifies discovery document has version, endpoints map, capabilities, and auth section
2. `GET /.well-known/sempkm` (unauthenticated) — verifies auth middleware rejects anonymous requests
3. `GET /api/types` — verifies types array with ≥1 entry, each having iri + label
4. `GET /api/shapes/{type_iri}` — fetches a real type IRI from the types endpoint, verifies properties array is non-empty
5. `GET /api/shapes/urn:nonexistent:FakeType` — verifies 404 for missing type
6. `POST /api/context-query` with `{"keywords":"test"}` — verifies 200 with results array and total count
7. `POST /api/context-query` with `{}` — verifies 400 with detail message containing "required"

All tests use the `ownerRequest` fixture (authenticated `APIRequestContext` with session cookie) for authenticated calls and `anonApi` for the auth-gate test. No browser navigation needed — all pure HTTP assertions.

## Verification

- `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — 7 passed in 1.6s
- All 7 tests pass consistently across two consecutive runs
- Test execution time well under the 30s requirement

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run pytest tests/test_api_surface.py -v -k "context_query"` | 0 | ✅ pass | 0.75s |
| 2 | `curl -X POST http://localhost:3901/api/context-query -d '{"url":"https://example.com"}'` | 0 | ✅ pass (401 — auth required, expected without session) | <1s |
| 3 | `curl -X POST http://localhost:3901/api/context-query -d '{}'` | 0 | ✅ pass (401 — auth required, expected without session) | <1s |
| 4 | `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` | 0 | ✅ pass | 1.6s |
| 5 | `ls docs/guide/31-api-surface.md` | 2 | ⏳ pending (T04) | — |

## Diagnostics

- **Run tests**: `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium`
- **Debug failures**: Failed tests produce trace zips in `e2e/test-results/` — use `npx playwright show-trace <path>` to inspect
- **Test stack**: Must have `docker compose -f docker-compose.test.yml up -d` running on port 3901
- **No new runtime surfaces**: These are E2E tests only — they exercise existing API endpoints without adding backend code

## Deviations

- Added 7 tests instead of the minimum 5 — the extra auth-gate test and validation test are cheap to run and verify important edge cases
- Plan suggested `page.request.get/post` but `ownerRequest` (from auth fixture) is the established pattern in this codebase — it provides an authenticated `APIRequestContext` directly

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/30-api-surface/api-surface.spec.ts` — 7 E2E tests for all M013 API endpoints
- `.gsd/milestones/M013/slices/S03/tasks/T03-PLAN.md` — Added missing Observability Impact section
