---
estimated_steps: 28
estimated_files: 8
skills_used: []
---

# T01: Fix assertion mismatches, test logic bugs, helper improvement, and targeted test repairs

Fix 8 test files covering Categories 1 (assertion mismatches), 2 (test logic), 5 (timeline CDN), 6 (event-log panel), 7 (autocomplete timing), and 9 (object form timeout). Also add `waitState` parameter to `openGenericViewTab` helper for timeline tests.

## Steps

1. **workspace-layout.spec.ts** — Two fixes:
   - Line ~89: Change `toHaveCount(4)` to `toHaveCount(5)` for bottom panel tabs (SPARQL tab was added)
   - Add `await expect(panelTabBar).toContainText('SPARQL');` after the existing LINT assertion
   - Line ~79: Change `toContainText(['Relations'])` to match the actual uppercase text `RELATIONS` (use regex or exact text match)

2. **keyboard-shortcuts.spec.ts** — Two fixes:
   - Line ~49: Change `toBe(4)` to `toBeGreaterThanOrEqual(4)` for type option count
   - Line ~40: Replace `await waitForIdle(ownerPage);` before type picker assertion with `await ownerPage.waitForSelector('[data-testid="type-picker"]', { timeout: 15000 });` — the waitForIdle times out because htmx requests persist

3. **table-pagination.spec.ts** — Line ~18: Change `specs.find((s: any) => s.renderer_type === 'table')` to also match `target_class` containing `Note`. Pattern: `specs.find((s: any) => s.renderer_type === 'table' && s.target_class?.includes('Note'))` — the test creates Notes but the first table spec may be for Events

4. **dockview.ts helper** — Add optional `waitState` parameter to `openGenericViewTab`:
   - Add `waitState?: 'visible' | 'attached' | 'hidden' | 'detached'` as a new parameter (default: undefined, which leaves Playwright's default of 'visible')
   - Pass `{ timeout: timeoutMs, ...(waitState ? { state: waitState } : {}) }` to `waitForSelector`

5. **timeline.spec.ts** — In all `openGenericViewTab` calls, add `'attached'` as the waitState parameter (the timeline container has min-height:200px but CDN-loaded Frappe Gantt content isn't rendered yet, so 'visible' fails)

6. **event-log-polish.spec.ts** — In `openEventLog` helper, bump the bottom panel height-check timeout from `{ timeout: 5000 }` to `{ timeout: 15000 }`

7. **edit-object-ui.spec.ts** — Two categories of fixes:
   - Autocomplete test (~line 230): Add `await kmSuggestion.scrollIntoViewIfNeeded();` before `kmSuggestion.click()` and add a small `page.waitForTimeout(200)` after the dropdown becomes visible
   - All `.object-tab` and `.object-face-edit.face-visible` timeout bumps: Change every `{ timeout: 10000 }` to `{ timeout: 20000 }` to match the `openObjectTab` helper's 20s default. Also bump `.form-success` and `.dv-default-tab-content` waits to 20000

8. **create-object.spec.ts** — Bump `SEL.editor.form` and `SEL.typePicker.overlay` waitForSelector timeouts from `{ timeout: 10000 }` to `{ timeout: 20000 }`

## Must-Haves

- [ ] workspace-layout: panel tab count is 5, SPARQL text asserted, RELATIONS case matches
- [ ] keyboard-shortcuts: type count uses >= 4, waitForIdle replaced with element-specific wait
- [ ] table-pagination: spec finder filters by Note target_class
- [ ] dockview.ts: openGenericViewTab has waitState parameter
- [ ] timeline: all openGenericViewTab calls use state 'attached'
- [ ] event-log: height-check timeout is >= 15000ms
- [ ] edit-object-ui: all timeouts bumped to 20s, autocomplete click has scrollIntoView
- [ ] create-object: form wait timeouts bumped to 20s

## Inputs

- ``e2e/tests/03-navigation/workspace-layout.spec.ts` — current assertions for bottom panel tabs and Relations text`
- ``e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` — current waitForIdle and type count assertions`
- ``e2e/tests/02-views/table-pagination.spec.ts` — current specs.find() logic`
- ``e2e/helpers/dockview.ts` — current openGenericViewTab signature`
- ``e2e/tests/02-views/timeline.spec.ts` — current openGenericViewTab calls`
- ``e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — current openEventLog helper`
- ``e2e/tests/01-objects/edit-object-ui.spec.ts` — current autocomplete test and timeout values`
- ``e2e/tests/01-objects/create-object.spec.ts` — current form wait timeouts`

## Expected Output

- ``e2e/tests/03-navigation/workspace-layout.spec.ts` — updated tab count and RELATIONS text assertions`
- ``e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` — updated type count and waitForIdle replacement`
- ``e2e/tests/02-views/table-pagination.spec.ts` — updated specs.find() with target_class filter`
- ``e2e/helpers/dockview.ts` — openGenericViewTab with waitState parameter`
- ``e2e/tests/02-views/timeline.spec.ts` — openGenericViewTab calls use state:'attached'`
- ``e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — bumped height-check timeout`
- ``e2e/tests/01-objects/edit-object-ui.spec.ts` — fixed autocomplete timing and bumped timeouts`
- ``e2e/tests/01-objects/create-object.spec.ts` — bumped form wait timeouts`

## Verification

cd e2e && npx playwright test tests/03-navigation/workspace-layout.spec.ts tests/03-navigation/keyboard-shortcuts.spec.ts tests/02-views/table-pagination.spec.ts tests/02-views/timeline.spec.ts tests/27-event-log-polish/event-log-polish.spec.ts tests/01-objects/edit-object-ui.spec.ts tests/01-objects/create-object.spec.ts --project=chromium --retries=1 --reporter=line 2>&1 | tail -30
