---
estimated_steps: 4
estimated_files: 1
---

# T02: Add E2E test for new-object tab preservation

**Slice:** S04 — Create-New-Object Tab Fix
**Milestone:** M004

## Description

Write a Playwright E2E spec proving that the "Create New Object" flow preserves existing tabs. This prevents regression of the bug fixed in T01 — without this test, a future refactor could easily reintroduce the overwrite behavior.

## Steps

1. **Create test file** — `e2e/tests/12-bug-fixes/new-object-tab.spec.ts`. Import from `../../fixtures/auth` (for `ownerPage`), `../../fixtures/seed-data` (for `SEED`), and `../../helpers/wait-for` (for `waitForWorkspace`, `waitForIdle`).

2. **Test: "New Object opens in fresh tab without destroying existing tab"** —
   - Navigate to workspace, `waitForWorkspace`.
   - Open a seed object tab via `page.evaluate(() => window.openTab(iri, label))` using `SEED.notes.architecture`.
   - `waitForIdle`, then assert the seed object's tab is visible in `.dv-default-tab` (text contains the label).
   - Call `page.evaluate(() => window.showTypePicker())`.
   - `waitForIdle`, wait for `.type-picker` to appear.
   - Assert the original seed object tab still exists in the tab bar (`.dv-default-tab` with matching text).
   - Assert a second tab exists (at least 2 `.dv-default-tab` elements).

3. **Test: "Temp panel closes after object creation"** (stretch — only if the test infrastructure supports completing the full create flow easily) —
   - After showing type picker, click a type card.
   - Fill out the object form minimally (name field).
   - Submit the form.
   - Wait for `objectCreated` event to fire (wait for a new tab to appear, temp tab to disappear).
   - Assert: at least 2 tabs exist (original + new object), no tab with `__new-object` prefix title.
   - This step is optional — the first test is the critical regression guard.

4. **Run and verify** — `cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts`.

## Must-Haves

- [ ] E2E test file exists at `e2e/tests/12-bug-fixes/new-object-tab.spec.ts`
- [ ] Test opens a seed object tab, triggers showTypePicker, and asserts original tab survives
- [ ] Test passes against the Docker E2E stack

## Verification

- `cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts` passes
- Test output shows assertions for tab preservation

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: run the E2E test; failure messages clearly state which assertion failed (tab count, tab label presence)
- Failure state exposed: Playwright test failure with screenshot on assertion failure

## Inputs

- `frontend/static/js/workspace.js` — T01's fix must be in place (showTypePicker creates fresh panel)
- `e2e/fixtures/auth.ts` — `ownerPage` fixture
- `e2e/fixtures/seed-data.ts` — `SEED.notes.architecture` for a known object
- `e2e/helpers/wait-for.ts` — `waitForWorkspace`, `waitForIdle`
- `e2e/tests/03-navigation/tab-management.spec.ts` — reference for dockview tab assertion patterns

## Expected Output

- `e2e/tests/12-bug-fixes/new-object-tab.spec.ts` — new E2E test proving tab preservation on "Create New Object"
