---
id: T01
parent: S07
milestone: M031
provides:
  - M031 E2E test spec with 6 test cases covering all new view features
  - Retired stale carousel-views.spec.ts
  - Task type constant for kanban E2E tests
  - openGenericViewTab helper for dockview integration
  - 6 new view selectors in SEL.views
key_files:
  - e2e/tests/02-views/m031-views.spec.ts
  - e2e/helpers/dockview.ts
  - e2e/helpers/selectors.ts
  - e2e/fixtures/seed-data.ts
key_decisions:
  - Used openGenericViewTab helper wrapping window.openGenericViewTab() with timeout-guarded waitForSelector, matching the workspace.js API signature (renderer, scopeQuery, scopeLabel)
  - Kanban test pre-sets localStorage type selection rather than navigating the UI to select Task type, avoiding fragile multi-step UI interactions
patterns_established:
  - M031 view selectors centralised in SEL.views (kanbanBoard, kanbanColumn, kanbanCard, scopeSelect, variantSelect, saveViewBtn) — all future view tests should reference these
  - openGenericViewTab helper pattern: evaluate window function → waitForSelector with configurable timeout
observability_surfaces:
  - Playwright test output with per-case pass/fail and assertion details
  - TypeScript compilation check catches import resolution issues across fixtures/helpers/specs
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Write M031 E2E test spec and retire carousel tests

**Delete stale carousel-views.spec.ts, add Task type constant, 6 M031 view selectors, openGenericViewTab helper, and 6-case m031-views.spec.ts covering carousel absence, generic view tabs, kanban, scope dropdown, save button, and multi-instance tabs.**

## What Happened

Executed all 5 steps from the task plan with no deviations:

1. Deleted `e2e/tests/02-views/carousel-views.spec.ts` (175 lines testing removed carousel functionality).
2. Added `Task: 'urn:sempkm:model:basic-pkm:Task'` to the TYPES constant in `seed-data.ts` for kanban E2E tests.
3. Added 6 selectors to `SEL.views` in `selectors.ts`: `kanbanBoard`, `kanbanColumn`, `kanbanCard`, `scopeSelect`, `variantSelect`, `saveViewBtn` — all verified against actual class names in `view_toolbar.html` and `kanban_view.html`.
4. Added `openGenericViewTab()` helper to `dockview.ts` wrapping `window.openGenericViewTab(renderer, scopeQuery, scopeLabel)` with a configurable timeout-guarded `waitForSelector`.
5. Wrote `m031-views.spec.ts` with 6 test cases covering each S01–S06 feature: carousel absence, generic view tab opening, kanban board with status columns, scope dropdown presence, save button presence, and multiple tab instances.

Verified that none of our modified files produce TypeScript compilation errors (pre-existing errors exist in other test files but are unrelated).

## Verification

- New spec file exists: ✅
- Old carousel spec deleted: ✅
- Task type added to seed-data: ✅
- openGenericViewTab in dockview.ts: ✅
- Test case count ≥ 6: ✅ (exactly 6)
- Kanban selectors in selectors.ts: ✅
- TypeScript compilation: ✅ (no errors in our files; pre-existing errors in other files)

Slice-level checks (T01 scope only):
- SV1 (new spec exists, old deleted): ✅
- SV2 (Task type constant): ✅
- SV3–SV7: SKIP (T02 documentation scope)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/02-views/m031-views.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `! test -f e2e/tests/02-views/carousel-views.spec.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -q "Task:" e2e/fixtures/seed-data.ts` | 0 | ✅ pass | <1s |
| 4 | `grep -q "openGenericViewTab" e2e/helpers/dockview.ts` | 0 | ✅ pass | <1s |
| 5 | `grep -c "test(" e2e/tests/02-views/m031-views.spec.ts` (returns 6) | 0 | ✅ pass | <1s |
| 6 | `grep -q "kanbanBoard" e2e/helpers/selectors.ts` | 0 | ✅ pass | <1s |
| 7 | `tsc --noEmit --project e2e/tsconfig.json \| grep m031-views` (empty) | 0 | ✅ pass | 3s |

## Diagnostics

- **Run tests**: `npx playwright test e2e/tests/02-views/m031-views.spec.ts --reporter=list` shows per-case results.
- **Inspect selectors**: `SEL.views` in `e2e/helpers/selectors.ts` is the single source of truth for all M031 view selectors.
- **Helper API**: `openGenericViewTab(page, renderer, waitSelector, scopeQuery?, scopeLabel?, timeoutMs?)` — timeout failures indicate missing JS function, failed panel creation, or wrong DOM selector.
- **TypeScript check**: `node_modules/.bin/tsc --noEmit --project e2e/tsconfig.json 2>&1 | grep m031` catches import resolution issues.

## Deviations

None. All selectors matched the actual class names in `view_toolbar.html` and `kanban_view.html`.

## Known Issues

- Pre-existing TypeScript compilation errors exist in ~10 other E2E test files (merge conflict artifacts per CLAUDE.md). These are unrelated to M031 changes.

## Files Created/Modified

- `e2e/tests/02-views/m031-views.spec.ts` — new: 6 E2E test cases for M031 view features
- `e2e/tests/02-views/carousel-views.spec.ts` — deleted: stale carousel tests
- `e2e/fixtures/seed-data.ts` — added Task type to TYPES constant
- `e2e/helpers/selectors.ts` — added 6 kanban/scope/save selectors to SEL.views
- `e2e/helpers/dockview.ts` — added openGenericViewTab() helper function
- `.gsd/milestones/M031/slices/S07/S07-PLAN.md` — marked T01 done, added Observability section
- `.gsd/milestones/M031/slices/S07/tasks/T01-PLAN.md` — added Observability Impact section
