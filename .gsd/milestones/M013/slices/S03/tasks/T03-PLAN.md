---
estimated_steps: 5
estimated_files: 1
---

# T03: E2E Playwright test for API surface

**Slice:** S03 — Context-Query, E2E Tests, and User Guide
**Milestone:** M013

## Description

Create Playwright E2E tests that exercise all four M013 API endpoints through the full Docker Compose stack (nginx → FastAPI → triplestore). Tests prove the entire pipeline works with real data, real auth, and real CORS headers.

## Steps

1. Create `e2e/tests/30-api-surface/api-surface.spec.ts`
2. Use the existing auth fixture pattern to get an authenticated session (session cookie)
3. Test 1: `GET /.well-known/sempkm` — verify 200, response has version/endpoints/capabilities
4. Test 2: `GET /api/types` — verify 200, response has types array with ≥1 entry, each with iri + label
5. Test 3: `GET /api/shapes/{type_iri}` — use a real type IRI from test 2's response, verify properties array exists and is non-empty
6. Test 4: `GET /api/shapes/urn:nonexistent:FakeType` — verify 404 response
7. Test 5: `POST /api/context-query` with `{"keywords":"test"}` — verify 200, response has results array (contents may vary based on test data)
8. Use `page.request.get/post` (Playwright's APIRequestContext) for direct HTTP calls — no browser navigation needed

## Must-Haves

- [ ] ≥5 E2E tests covering all four endpoints
- [ ] Tests use real session auth through Docker stack
- [ ] Tests run in <30s
- [ ] No dependency on specific seed data (handle empty results gracefully)

## Verification

- `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — all pass

## Inputs

- Running Docker Compose stack with at least one Mental Model installed
- `e2e/` directory structure and auth fixture patterns from existing E2E tests

## Observability Impact

- **Test output**: `npx playwright test tests/30-api-surface/ --project=chromium` — 7 named tests, each verifying a specific endpoint behavior through the full Docker stack
- **Failure signals**: Test names include the endpoint and expected behavior, so failures immediately identify which API surface contract is broken
- **Auth verification**: The "requires authentication" test proves the auth middleware is wired correctly at the nginx/FastAPI boundary
- **Inspection**: On failure, Playwright captures traces (`.zip`) for replay — `npx playwright show-trace <path>` to inspect request/response details
- **No new runtime observability**: These are pure E2E tests — they exercise existing endpoints without adding runtime logging or metrics

## Expected Output

- `e2e/tests/30-api-surface/api-surface.spec.ts` — ≥5 E2E tests
