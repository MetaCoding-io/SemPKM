---
estimated_steps: 36
estimated_files: 1
skills_used: []
---

# T02: E2E test for save/restore view flow

## Description

Create an E2E test that exercises the full save→sidebar→restore round-trip: open a generic view, select a type filter, save the view, find it in the Saved Views sidebar, click to restore, and verify the type filter is preserved. Also test delete.

## Steps

1. **Read** existing E2E view tests for patterns: `e2e/tests/02-views/m031-views.spec.ts` (uses `openGenericViewTab` helper, `waitForWorkspace`, `SEL.views`). Read `e2e/fixtures/auth.ts` for the auth fixture import pattern.

2. **Create** `e2e/tests/02-views/save-restore-view.spec.ts` with these tests:

   **Test 1: Save a view with type filter and restore it**
   - Navigate to workspace, wait for load
   - Open a table view via `openGenericViewTab(ownerPage, 'table', SEL.views.table)`
   - Wait for `.type-filter-select` to appear and have options loaded (wait for `option[value]` child)
   - Select a type from the dropdown: `page.selectOption('.type-filter-select', { index: 1 })` (first non-empty option)
   - Read the selected type value for later assertion
   - Register a dialog listener that accepts with a view name (e.g., 'E2E Test View'): `page.on('dialog', d => d.accept('E2E Test View'))`
   - Click the save button: `page.click('.save-view-btn')`
   - Wait for toast or sidebar refresh
   - Expand the SAVED VIEWS section in the explorer sidebar (click `[data-panel-section="saved-views"]` or the section header)
   - Wait for `#saved-views-tree` to load (it uses `hx-trigger="intersect once"`)
   - Assert a `.view-leaf` with text 'E2E Test View' appears in `#saved-views-tree`
   - Click the saved view entry
   - Wait for the new dockview panel to appear (a second table view tab)
   - Assert the `.type-filter-select` in the new panel has the same type value selected

   **Test 2: Delete a saved view**
   - (After Test 1 or as a continuation) Click the pin-off button on the saved view entry
   - Handle the `confirm()` dialog
   - Assert the view entry is removed from the sidebar

3. **Handle edge cases:**
   - The saved views section may need explicit expansion (click the section header) before the htmx `intersect` trigger fires
   - The `window.prompt()` in saveCurrentView needs `page.on('dialog')` registered BEFORE clicking save
   - The `window.confirm()` in deleteSavedView also needs a dialog listener
   - Type dropdown options load via htmx — wait for options before selecting

4. **Run** `npx playwright test e2e/tests/02-views/save-restore-view.spec.ts --reporter=list` and iterate until it passes.

## Must-Haves

- [ ] Test file exists at `e2e/tests/02-views/save-restore-view.spec.ts`
- [ ] Covers save with type filter, find in sidebar, restore with type filter preserved, and delete
- [ ] Uses auth fixture, `openGenericViewTab` helper, and SEL selectors
- [ ] Handles `window.prompt()` and `window.confirm()` dialogs via Playwright dialog listeners
- [ ] All tests pass

## Inputs

- ``frontend/static/js/workspace.js` — openGenericViewTab() with selectedType parameter (from T01)`
- ``backend/app/templates/browser/my_views.html` — onclick with type_filter pass-through (from T01)`
- ``e2e/helpers/dockview.ts` — openGenericViewTab helper with selectedType (from T01)`
- ``e2e/helpers/selectors.ts` — updated selectors (from T01)`
- ``e2e/fixtures/auth.ts` — auth fixture providing ownerPage`
- ``e2e/helpers/wait-for.ts` — waitForWorkspace helper`
- ``e2e/tests/02-views/m031-views.spec.ts` — reference E2E test pattern for views`

## Expected Output

- ``e2e/tests/02-views/save-restore-view.spec.ts` — passing E2E test for save/restore view flow`

## Verification

cd /home/james/Code/SemPKM && npx playwright test e2e/tests/02-views/save-restore-view.spec.ts --reporter=list
