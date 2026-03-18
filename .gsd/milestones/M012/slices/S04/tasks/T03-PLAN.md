---
estimated_steps: 6
estimated_files: 2
---

# T03: E2E Playwright tests for personas

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M012

**Relevant skills to load:** `test` (auto-detects Playwright framework)

## Description

Write a Playwright E2E spec file validating the S03 persona features (PERSONA-01 through PERSONA-05) in a running Docker test stack. Personas have a REST API, sidebar UI, command palette entries, and frontend lifecycle functions — the tests should cover all these surfaces.

The closest existing pattern is `e2e/tests/03-navigation/named-layouts.spec.ts` which tests a similar concept (save/restore workspace state via JS API). Follow its structure: API-level arrangement, browser-level assertions, cleanup after each test.

## Steps

1. Create `e2e/tests/29-personas/personas.spec.ts` with these tests:

   - **Test 1: "persona CRUD via API"** — Using `ownerRequest`:
     - POST `/api/personas` with `{name: "E2E Test Persona"}` → expect 201, response has `id` and `name`
     - GET `/api/personas` → expect array containing the created persona
     - PUT `/api/personas/{id}` with `{name: "Renamed E2E Persona"}` → expect 200
     - GET `/api/personas/{id}` → verify name is "Renamed E2E Persona"
     - DELETE `/api/personas/{id}` → expect 204
     - GET `/api/personas` → verify deleted persona is gone

   - **Test 2: "default persona auto-created on first workspace load"** — Navigate `ownerPage` to workspace. Wait for workspace load. Use `ownerRequest` GET `/api/personas` — expect at least one persona exists (initPersonas auto-creates "Default" if none exist). This tests PERSONA-05.

   - **Test 3: "persona selector visible in sidebar user popover"** — Navigate to workspace. Click the user avatar/popover trigger in the sidebar (`.user-popover-trigger` or similar). Wait for the persona selector partial to load (it loads via hx-trigger="load"). Assert that the persona selector UI is visible — look for `.persona-selector` or persona list items. This tests PERSONA-03.

   - **Test 4: "command palette has persona commands"** — Navigate to workspace. Open command palette (Alt+K). Evaluate `ninja-keys` data to check for persona-related commands (IDs starting with "persona-" or section "Persona"). Assert at least "persona-switch", "persona-save", "persona-create" commands exist. This tests PERSONA-04.

   - **Test 5: "persona activation via API switches active persona"** — Using `ownerRequest`:
     - GET `/api/personas` to find current personas (auto-created Default should exist)
     - POST `/api/personas` with `{name: "Second Persona"}` to create a new one
     - POST `/api/personas/{id}/activate` to activate the new persona
     - GET `/api/personas` → verify the new persona has `is_active: true` and the old one has `is_active: false`
     - Cleanup: DELETE the test persona

2. Import from standard fixtures:
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
   ```

3. Add cleanup in tests that create personas — delete test personas after assertions to avoid polluting subsequent tests. The Docker test stack is stateful across tests.

**Key implementation details from S03 summary:**
- Persona API is at `/api/personas` with standard REST CRUD
- List endpoint: `GET /api/personas` returns `[{id, name, is_active, created_at, updated_at}]` (no layout_json)
- Create: `POST /api/personas` with `{name}` body, returns 201
- Activate: `POST /api/personas/{id}/activate`
- Save state: `POST /api/personas/{id}/save-state` with `{layout_json, sidebar_positions_json, explorer_mode}`
- Rename: `PUT /api/personas/{id}` with `{name}`
- Delete: `DELETE /api/personas/{id}` returns 204
- Browser selector partial: `GET /browser/personas/selector` loaded via hx-trigger="load" in sidebar
- `initPersonas()` creates "Default" persona when API returns empty list on workspace load
- Command palette IDs: `persona-switch`, `persona-save`, `persona-create` with section "Persona"

## Must-Haves

- [ ] Persona CRUD test covering create, list, rename, get, delete via API
- [ ] Default persona auto-creation verified via API after workspace load
- [ ] Persona selector UI presence verified in sidebar
- [ ] Command palette persona entries verified
- [ ] Test cleanup — no orphan test personas left after test run

## Verification

- `cd e2e && npx playwright test tests/29-personas --project=chromium` — all tests pass
- Tests don't break existing suite: `cd e2e && npx playwright test --project=chromium` — passes

## Inputs

- T01 merge completed — all S01/S02/S03 code on main
- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerRequest`, `BASE_URL`
- `e2e/helpers/wait-for.ts` — provides `waitForWorkspace`, `waitForIdle`
- `e2e/tests/03-navigation/named-layouts.spec.ts` — reference pattern for workspace state save/restore tests
- S03 summary — persona API surface documentation

## Observability Impact

**Runtime signals added:**
- Playwright test results for `tests/29-personas/personas.spec.ts` — 5 tests covering persona CRUD, auto-creation, UI selector, command palette, and activation switching
- Test failures produce Playwright HTML reports in `e2e/playwright-report/` with screenshots and traces

**Inspection commands:**
- `cd e2e && npx playwright test tests/29-personas --project=chromium` — run persona tests in isolation
- `cd e2e && npx playwright show-report` — view HTML test report with failure details
- `curl -s http://localhost:3901/api/personas` — verify persona API availability on test stack

**Failure visibility:**
- Persona CRUD test failures indicate API regression in `backend/app/persona/router.py`
- Default persona auto-creation failure indicates `initPersonas()` in `workspace.js` is broken
- Selector UI test failure indicates htmx partial at `/browser/personas/selector` is not loading
- Command palette test failure indicates ninja-keys data in `workspace.js` is missing persona entries

## Expected Output

- `e2e/tests/29-personas/personas.spec.ts` — 4-5 tests covering PERSONA-01 through PERSONA-05
