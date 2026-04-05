# S03: Save/Restore Flow + E2E Tests

**Goal:** Fix the save/restore view flow so that saved views preserve and restore their type filter and scope query, and prove it with E2E tests.
**Demo:** After this: Save a view with type filter and scope query → find it in Saved Views sidebar → click to open → same type filter and scope are restored. E2E tests pass.

## Tasks
- [x] **T01: Added selectedType parameter to openGenericViewTab with localStorage fallback, wired type_filter from saved views template, and updated E2E helpers and selectors** — ## Description

The save/restore flow stores `type_filter` correctly in RDF but never restores it because `openGenericViewTab()` only reads from localStorage, and `my_views.html` doesn't pass the stored value. This task fixes both bugs and updates the E2E infrastructure.

## Steps

1. **Read** `frontend/static/js/workspace.js` around the `openGenericViewTab` function (line ~3765). Add `selectedType` as a 4th parameter with fallback:
   - Change signature from `function openGenericViewTab(renderer, scopeQuery, scopeLabel)` to `function openGenericViewTab(renderer, scopeQuery, scopeLabel, selectedType)`
   - Change the selectedType assignment from `var selectedType = localStorage.getItem('sempkm_generic_type_' + renderer) || '';` to `var selectedType = selectedType || localStorage.getItem('sempkm_generic_type_' + renderer) || '';`
   - **Important:** The new param must shadow the `var` declaration. Rename the `var` to avoid confusion: use `var resolvedType = selectedType || localStorage.getItem(...)` and pass `resolvedType` to the dockview params.

2. **Read** `backend/app/templates/browser/my_views.html`. Update the non-query onclick handler:
   - Change from: `onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id | default('') }}', '{{ pv.display_label | replace("'", "\\'") }}')"`
   - Change to: `onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id | default('') }}', '{{ pv.display_label | replace("'", "\\'") }}', '{{ pv.type_filter | default('') }}')"`

3. **Read** `e2e/helpers/dockview.ts`. Add `selectedType` parameter to the `openGenericViewTab` helper:
   - Add `selectedType?: string` parameter after `scopeLabel`
   - Update the `page.evaluate` call to pass `selectedType` and forward it to `window.SemPKM.openGenericViewTab(renderer, scopeQuery || '', scopeLabel || '', selectedType || '')`

4. **Read** `e2e/helpers/selectors.ts`. In the `views:` block:
   - Remove `variantSelect: '.view-variant-select'` (View Variants was removed in S02)
   - Add `typeFilterDropdown: '.type-filter-select'`
   - Add `savedViewsTree: '#saved-views-tree'`
   - Add `savedViewEntry: '.view-leaf[data-view-id]'`

5. **Verify** all changes with grep checks.

## Must-Haves

- [ ] `openGenericViewTab()` accepts optional 4th `selectedType` parameter with localStorage fallback
- [ ] All existing callers (which pass 3 args) continue working — the 4th param is optional
- [ ] `my_views.html` passes `pv.type_filter` to `openGenericViewTab()`
- [ ] E2E `openGenericViewTab` helper forwards `selectedType`
- [ ] `variantSelect` removed from selectors.ts
  - Estimate: 30m
  - Files: frontend/static/js/workspace.js, backend/app/templates/browser/my_views.html, e2e/helpers/dockview.ts, e2e/helpers/selectors.ts
  - Verify: rg 'function openGenericViewTab' frontend/static/js/workspace.js | grep -q 'selectedType' && rg 'openGenericViewTab' backend/app/templates/browser/my_views.html | grep -q 'type_filter' && rg 'variantSelect' e2e/helpers/selectors.ts | wc -l | grep -q '^0$' && echo 'T01 PASS'
- [x] **T02: Created E2E test for save/restore view flow covering save with type filter, sidebar restore, type preservation, and delete — passes Chromium and Firefox** — ## Description

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
  - Estimate: 45m
  - Files: e2e/tests/02-views/save-restore-view.spec.ts
  - Verify: cd /home/james/Code/SemPKM && npx playwright test e2e/tests/02-views/save-restore-view.spec.ts --reporter=list
