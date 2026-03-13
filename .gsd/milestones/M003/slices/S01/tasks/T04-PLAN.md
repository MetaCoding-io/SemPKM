---
estimated_steps: 4
estimated_files: 3
---

# T04: E2E tests and final verification

**Slice:** S01 — Explorer Mode Infrastructure
**Milestone:** M003

## Description

Complete the E2E test file with real assertions against the running Docker stack. Add explorer mode selectors to `selectors.ts`. Run the full E2E suite to verify no regressions. This task proves EXP-01 (mode dropdown with switchable strategies) and EXP-02 (by-type as default, behavior preserved).

## Steps

1. **Add explorer selectors to `selectors.ts`:**
   - Add `explorer` section with: `modeSelect: '#explorer-mode-select'`, `treeBody: '#explorer-tree-body'`, `placeholder: '[data-testid="explorer-placeholder"]'`

2. **Implement E2E tests in `explorer-mode-switching.spec.ts`:**
   - Remove `test.skip`/`test.fixme` markers from skeleton tests
   - Test "dropdown visible with three mode options": navigate to workspace, assert `#explorer-mode-select` visible, assert 3 options (by-type, hierarchy, by-tag)
   - Test "by-type mode shows nav sections by default": assert `[data-testid="nav-section"]` elements present in `#explorer-tree-body`
   - Test "switching to hierarchy shows placeholder": select "hierarchy" value in dropdown, wait for htmx swap, assert `[data-testid="explorer-placeholder"]` visible, assert `[data-testid="nav-section"]` not present
   - Test "switching to by-tag shows placeholder": select "by-tag", assert placeholder visible
   - Test "switching back to by-type restores real tree": select "by-type", wait for swap, assert `[data-testid="nav-section"]` present, assert placeholder not present
   - Test "lazy expansion works after mode round-trip": switch to hierarchy then back to by-type, click a type node, assert `[data-testid="nav-item"]` children appear
   - Test "multi-select clears on mode switch": click two objects with Ctrl, verify selection badge visible, switch mode, verify selection badge hidden

3. **Run existing test suites to check for regressions:**
   - Run `01-objects` suite — object creation and editing must still work
   - Run `03-navigation` suite — existing nav tree tests must pass
   - Run `13-v24-coverage` suite — workspace coverage tests must pass
   - Fix any regressions introduced by template or JS changes

4. **Final manual verification checklist:**
   - Fresh page load shows by-type tree (server-rendered, no flash)
   - `refreshNavTree()` from console works in by-type mode
   - `refreshNavTree()` from console works in placeholder mode
   - Bulk delete flow (select objects, delete) works unchanged
   - Drag-drop from nav tree to canvas works unchanged
   - Command palette "Create new..." entries present in all modes

## Must-Haves

- [ ] Explorer mode selectors added to `selectors.ts`
- [ ] All E2E test cases implemented and passing
- [ ] No regressions in existing `01-objects`, `03-navigation`, `13-v24-coverage` suites
- [ ] EXP-01 verified: dropdown switches modes, tree re-renders via htmx
- [ ] EXP-02 verified: by-type is default, behavior identical to pre-refactor

## Verification

- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list` — all tests pass
- `cd e2e && npx playwright test tests/01-objects/ --reporter=list` — no regressions
- `cd e2e && npx playwright test tests/03-navigation/ --reporter=list` — no regressions

## Observability Impact

- Signals added/changed: None — tests only
- How a future agent inspects this: E2E test output shows pass/fail per test case; test names map directly to requirements
- Failure state exposed: Playwright test reporter shows failing assertions with screenshots

## Inputs

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — T01 skeleton
- `e2e/helpers/selectors.ts` — existing selectors to extend
- All T01–T03 changes deployed in Docker stack
- `e2e/fixtures/auth.ts` — auth fixture for test setup

## Expected Output

- `e2e/helpers/selectors.ts` — explorer selectors added
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — all tests implemented and passing
- Green test results for explorer modes + no regressions in related suites
