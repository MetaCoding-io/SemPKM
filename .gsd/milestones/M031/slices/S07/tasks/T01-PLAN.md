---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T01: Write M031 E2E test spec and retire carousel tests

**Slice:** S07 — E2E Tests + User Guide Docs
**Milestone:** M031

## Description

M031 added 6 major features across S01–S06: carousel removal, generic view tabs from explorer, kanban renderer, saved query scope binding, saved views CRUD, and multiple view instances. The existing `carousel-views.spec.ts` tests removed functionality (references `.carousel-tab-bar`, `switchCarouselView()`, `sempkm_carousel_view` localStorage). This task deletes the stale test, adds missing test constants, updates shared helpers, and writes a comprehensive new E2E spec.

## Steps

1. **Delete `e2e/tests/02-views/carousel-views.spec.ts`** — this file tests carousel tab bar rendering, view switching via carousel, and localStorage persistence of carousel state. All that functionality was removed in S01.

2. **Add Task type to `e2e/fixtures/seed-data.ts`** — Add `Task: 'urn:sempkm:model:basic-pkm:Task'` to the `TYPES` constant. The kanban view test needs this to open a kanban view and verify Task objects appear in status columns. The basic-pkm seed data includes 4 Task objects with `bpkm:taskStatus` values.

3. **Add M031-specific selectors to `e2e/helpers/selectors.ts`** — Add entries to the `SEL.views` block:
   - `kanbanBoard: '.kanban-board'`
   - `kanbanColumn: '.kanban-column'`
   - `kanbanCard: '.kanban-card'`
   - `scopeSelect: '.view-scope-select'`
   - `variantSelect: '.view-variant-select'`
   - `saveViewBtn: '.save-view-btn'` (or whatever class the save button uses — check `view_toolbar.html`)

4. **Add `openGenericViewTab()` helper to `e2e/helpers/dockview.ts`** — Wraps `window.openGenericViewTab(renderer, scopeQuery?, scopeLabel?)` for E2E use. Waits for a generic view panel to appear. Pattern:
   ```typescript
   export async function openGenericViewTab(
     page: Page,
     renderer: 'table' | 'card' | 'graph' | 'kanban',
     waitSelector: string,
     scopeQuery?: string,
     scopeLabel?: string,
     timeoutMs = 15000,
   ) {
     await page.evaluate(({ renderer, scopeQuery, scopeLabel }) => {
       if (typeof (window as any).openGenericViewTab === 'function') {
         (window as any).openGenericViewTab(renderer, scopeQuery || '', scopeLabel || '');
       }
     }, { renderer, scopeQuery, scopeLabel });
     await page.waitForSelector(waitSelector, { timeout: timeoutMs });
   }
   ```

5. **Write `e2e/tests/02-views/m031-views.spec.ts`** with these test cases:
   - **"carousel tab bar is absent from generic views"** — Open a table view via `openGenericViewTab('table', ...)`, assert `.carousel-tab-bar` has count 0, assert `.carousel-tab` has count 0.
   - **"generic view tab opens from explorer sidebar click"** — Navigate to workspace, use `openGenericViewTab('table', SEL.views.table)`, verify `[data-testid="table-view"]` is visible.
   - **"kanban view renders board with status columns"** — Open kanban via `openGenericViewTab('kanban', '.kanban-board')`. First select Task type via the type filter mechanism (set `localStorage.setItem('sempkm_generic_type_kanban', TYPES.Task)`). Verify `.kanban-board` visible, at least 2 `.kanban-column` elements, at least 1 `.kanban-card`.
   - **"view scope dropdown is present on generic views"** — Open table view, check `.view-scope-select` is attached to DOM (may be visible or hidden depending on saved queries existing).
   - **"save view button is present on generic views"** — Open table view, check save view button exists.
   - **"multiple instances of same view type create separate tabs"** — Open table view, get tab count, open table view again, verify new tab count > previous.

   Import from `../../fixtures/auth` (test, expect, BASE_URL), `../../fixtures/seed-data` (TYPES, SEED), `../../helpers/selectors` (SEL), `../../helpers/wait-for` (waitForWorkspace, waitForIdle), `../../helpers/dockview` (openGenericViewTab, getTabCount).

## Must-Haves

- [ ] `carousel-views.spec.ts` deleted
- [ ] `Task` type in TYPES constant in `seed-data.ts`
- [ ] At least 4 M031 selectors added to `selectors.ts`
- [ ] `openGenericViewTab` helper in `dockview.ts`
- [ ] `m031-views.spec.ts` has ≥6 test cases covering carousel absence, generic view opening, kanban, scope dropdown, save button, and multi-instance
- [ ] All test imports resolve (no undefined symbols)

## Verification

- `test -f e2e/tests/02-views/m031-views.spec.ts` — new spec exists
- `! test -f e2e/tests/02-views/carousel-views.spec.ts` — old spec deleted
- `grep -q "Task:" e2e/fixtures/seed-data.ts` — Task type added
- `grep -q "openGenericViewTab" e2e/helpers/dockview.ts` — helper added
- `grep -c "test(" e2e/tests/02-views/m031-views.spec.ts` returns ≥ 6 — sufficient test cases
- `grep -q "kanbanBoard\|kanban-board" e2e/helpers/selectors.ts` — kanban selectors added
- `npx tsc --noEmit --project e2e/tsconfig.json 2>&1 | head -20` — no TypeScript errors (if tsconfig exists)

## Inputs

- `e2e/tests/02-views/carousel-views.spec.ts` — file to delete (175 lines testing removed carousel functionality)
- `e2e/fixtures/seed-data.ts` — needs Task type added to TYPES constant
- `e2e/helpers/selectors.ts` — needs M031 view selectors (kanban, scope, variant, save button)
- `e2e/helpers/dockview.ts` — needs `openGenericViewTab()` helper function
- `e2e/tests/02-views/graph-view.spec.ts` — reference for test structure and patterns
- `e2e/helpers/wait-for.ts` — existing helpers to import (waitForWorkspace, waitForIdle)
- `e2e/fixtures/auth.ts` — existing auth fixture (test, expect, BASE_URL)
- `frontend/static/js/workspace.js` — reference for `openGenericViewTab()` function signature (line 3217)
- `backend/app/templates/browser/view_toolbar.html` — reference for save button and scope dropdown class names

## Expected Output

- `e2e/tests/02-views/m031-views.spec.ts` — new E2E test spec with ≥6 test cases
- `e2e/fixtures/seed-data.ts` — updated with Task type in TYPES
- `e2e/helpers/selectors.ts` — updated with M031 view selectors
- `e2e/helpers/dockview.ts` — updated with openGenericViewTab helper

## Observability Impact

- **New diagnostic surface**: `m031-views.spec.ts` provides 6 E2E test cases that exercise the full M031 feature surface. Each test independently opens a generic view tab and asserts specific DOM selectors, making regressions in carousel removal, kanban rendering, toolbar controls, or multi-instance logic immediately visible via Playwright test output.
- **Helper inspectability**: The `openGenericViewTab()` helper wraps `window.openGenericViewTab()` with a timeout-guarded `waitForSelector`. Timeout failures in test output directly indicate whether the JS function exists, the panel was created, or the expected DOM selector was rendered.
- **Selector registry**: Adding `kanbanBoard`, `kanbanColumn`, `kanbanCard`, `scopeSelect`, `variantSelect`, and `saveViewBtn` to `SEL.views` creates a single source of truth for M031 view selectors across all E2E tests. Any future selector change only needs updating in `selectors.ts`.
- **Failure visibility**: A failing kanban test surfaces whether the issue is type selection (localStorage pre-set), panel creation (dockview API), or template rendering (`.kanban-board` / `.kanban-column` / `.kanban-card` selectors).
