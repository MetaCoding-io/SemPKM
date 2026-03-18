---
estimated_steps: 8
estimated_files: 3
---

# T02: E2E Playwright tests for event log polish and body.diff

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M012

**Relevant skills to load:** `test` (auto-detects Playwright framework)

## Description

Write two Playwright E2E spec files validating the S01 (event log labels, helptext, autocomplete) and S02 (body.diff) features in a running Docker test stack. These tests are the final validation step for requirements EVTLOG-01/02/03 and BDIFF-01/02/03.

Both spec files follow established patterns from `e2e/tests/06-settings/event-log.spec.ts` and `e2e/tests/06-settings/event-undo.spec.ts`: use `ownerPage`/`ownerRequest` fixtures from `e2e/fixtures/auth.ts`, use `waitForWorkspace()`/`waitForIdle()` from `e2e/helpers/wait-for.ts` for htmx timing, use `TYPES` and `SEED` from `e2e/fixtures/seed-data.ts` for test data.

Tests run against a Docker test stack on port 3901. Tests are sequential (single worker). The test stack must be running with all S01/S02/S03 code (ensured by T01 merge).

## Steps

1. Create `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` with these tests:
   - **Test 1: "event detail shows human-readable predicate labels"** — Create an object via `ownerRequest` POST to `/api/commands` (object.create with title). Open workspace in `ownerPage`. Open bottom panel (evaluate `toggleBottomPanel()`). Click EVENT LOG tab. Wait for event rows via `waitForIdle()`. Click the Diff button on the first event row to expand detail. Assert that `.diff-pred-label` elements contain human-readable text like "Title" (not raw IRI like "http://purl.org/dc/terms/title" or bare local name "title").
   - **Test 2: "predicate labels have helptext tooltips"** — Reuse the expanded event detail from Test 1 pattern. Assert that at least one `.diff-pred-label.has-helptext` element exists with a non-empty `title` attribute (this is the SHACL helptext tooltip).
   - **Test 3: "autocomplete suggestions appear for operation type filter"** — Open event log. Focus the operation type filter input (`.event-autocomplete-target input` or the input with htmx suggest-types trigger). Assert that a suggestions dropdown (`.event-autocomplete-target .suggestion-item`) becomes visible with at least one item.
   - **Test 4: "predicate filter shows suggestions on input"** — Focus the predicate filter input, type "tit" slowly (to trigger keyup debounce). Assert suggestion dropdown appears with items containing "Title" or "title".

2. Create `e2e/tests/28-body-diff/body-diff.spec.ts` with these tests:
   - **Test 1: "body.diff event appears after editing existing body"** — Via `ownerRequest`: (a) create a Note object, (b) PUT first body text to `/browser/objects/{encoded_iri}/body` with `Content-Type: text/plain`, (c) PUT updated body text to same endpoint. Open workspace in `ownerPage`. Open event log. Wait for rows. Find the latest event row — it should have operation type badge showing "body.diff".
   - **Test 2: "body.diff detail shows diff highlighting"** — Continue from test 1 state (or recreate). Expand the body.diff event's detail via Diff button. Assert that the diff panel contains both `.diff-add` (green) and `.diff-remove` (red) elements showing the changed lines.
   - **Test 3: "first body set creates body.set event (not body.diff)"** — Via `ownerRequest`: create a new Note, set body for the first time only. Open event log. Find the event for this object — it should show "body.set" operation type, not "body.diff".

3. Ensure both spec files import from the right fixtures and helpers:
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { TYPES } from '../../fixtures/seed-data';
   import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
   ```

**Key implementation details from S01/S02 summaries:**
- The save body endpoint is `PUT /browser/objects/{encoded_iri}/body` with `Content-Type: text/plain` request body
- Encode the IRI for the URL path: `encodeURIComponent(objectIri)`
- Event detail is loaded via htmx into `.event-diff-container` when the `.event-btn-diff` button is clicked
- Predicate labels are rendered as `<span class="diff-pred-label">Title</span>` with optional `class="has-helptext"` and `title="helptext text"` attributes
- Autocomplete inputs are inside `.event-autocomplete-target` wrappers with suggestion items as `.suggestion-item` elements
- Operation type badges are `.event-op-badge` elements inside `.event-row`
- After clicking event log tab, always use `waitForIdle(ownerPage)` before asserting on content
- Autocomplete dropdowns close on outside click — interact promptly after they appear

## Must-Haves

- [ ] `event-log-polish.spec.ts` has ≥3 tests covering labels, helptext, and autocomplete
- [ ] `body-diff.spec.ts` has ≥3 tests covering body.diff rendering, diff highlighting, and body.set backward compat
- [ ] All tests use established fixtures (`ownerPage`, `ownerRequest`) and wait helpers
- [ ] Tests follow sequential pattern (no parallel assumptions)
- [ ] Tests are robust — use `waitForIdle()` after htmx swaps, `force: true` for clicks in layout-sensitive areas

## Verification

- `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium` — all tests pass
- Tests don't break existing suite: `cd e2e && npx playwright test --project=chromium` — passes

## Inputs

- T01 merge completed — all S01/S02/S03 code on main
- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerRequest`, `BASE_URL`
- `e2e/fixtures/seed-data.ts` — provides `TYPES.Note` for object creation
- `e2e/helpers/wait-for.ts` — provides `waitForWorkspace`, `waitForIdle`
- `e2e/tests/06-settings/event-log.spec.ts` — reference pattern for event log test setup
- `e2e/tests/06-settings/event-undo.spec.ts` — reference pattern for API + browser event testing

## Expected Output

- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — 3-4 tests for S01 features
- `e2e/tests/28-body-diff/body-diff.spec.ts` — 3 tests for S02 features
