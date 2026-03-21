# S07: E2E Tests + User Guide Docs

**Goal:** Playwright E2E tests cover all M031 new/changed behavior; user guide documents all new features; broken carousel tests are retired.
**Demo:** Running `npx playwright test e2e/tests/02-views/m031-views.spec.ts` passes. Chapters 7, 21, and 28 of the user guide describe the new view toolbar, scope binding, kanban, saved views, multiple instances, SPARQL graph tab, and builder UX improvements. `carousel-views.spec.ts` is deleted.

## Must-Haves

- `carousel-views.spec.ts` deleted — tests removed functionality
- New E2E spec `m031-views.spec.ts` covers: generic view tab opening from explorer, carousel absence, kanban board rendering with Task type, view scope dropdown presence, saved views toolbar button, multiple view tab instances
- `seed-data.ts` TYPES constant includes `Task` type for kanban tests
- Chapter 7 carousel content replaced with view toolbar, scope binding, kanban, saved views, and multiple instances documentation
- Chapter 21 adds SPARQL graph visualization tab section
- Chapter 28 adds builder contextual help text, autocomplete, and workflow view step simplification documentation

## Verification

- `test -f e2e/tests/02-views/m031-views.spec.ts && ! test -f e2e/tests/02-views/carousel-views.spec.ts` — new spec exists, old spec deleted
- `grep -q "Task:" e2e/fixtures/seed-data.ts` — Task type constant added
- `! grep -q "carousel" docs/guide/07-browsing-and-visualizing.md` — no carousel references remain in ch7
- `grep -q "Kanban" docs/guide/07-browsing-and-visualizing.md` — kanban documented
- `grep -q "Graph Visualization" docs/guide/21-sparql-console.md` — graph tab documented
- `grep -q "autocomplete\|Autocomplete" docs/guide/28-dashboards-and-workflows.md` — autocomplete documented
- `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` returns >= 8 — sufficient sections

## Tasks

- [x] **T01: Write M031 E2E test spec and retire carousel tests** `est:45m`
  - Why: M031 added/changed 6 major features (carousel removal, generic view tabs, kanban, scope binding, saved views, multi-instance tabs). The existing `carousel-views.spec.ts` tests removed functionality. New E2E coverage provides integration confidence.
  - Files: `e2e/tests/02-views/m031-views.spec.ts`, `e2e/tests/02-views/carousel-views.spec.ts`, `e2e/fixtures/seed-data.ts`, `e2e/helpers/selectors.ts`, `e2e/helpers/dockview.ts`
  - Do: (1) Delete `carousel-views.spec.ts`. (2) Add `Task: 'urn:sempkm:model:basic-pkm:Task'` to TYPES in `seed-data.ts`. (3) Add kanban/scope/saved-view selectors to `selectors.ts`. (4) Add `openGenericViewTab()` helper to `dockview.ts`. (5) Write `m031-views.spec.ts` with 6 test cases covering carousel absence, generic view tab opening, kanban board rendering, scope dropdown presence, save view button, and multiple tab instances.
  - Verify: `test -f e2e/tests/02-views/m031-views.spec.ts && ! test -f e2e/tests/02-views/carousel-views.spec.ts && grep -q "Task:" e2e/fixtures/seed-data.ts`
  - Done when: New spec file exists with ≥6 test cases, old carousel spec deleted, seed-data and helpers updated.

- [x] **T02: Update user guide chapters 7, 21, and 28 for M031 features** `est:30m`
  - Why: Three chapters reference removed features (carousel) or lack documentation for new features (kanban, scope binding, saved views, multi-instance tabs, SPARQL graph tab, builder UX improvements). Users need accurate documentation.
  - Files: `docs/guide/07-browsing-and-visualizing.md`, `docs/guide/21-sparql-console.md`, `docs/guide/28-dashboards-and-workflows.md`
  - Do: (1) Ch7: Replace "Carousel View Navigation" section (lines 33–45) with sections on View Toolbar (variant dropdown, scope binding), Kanban View, Saved Views, and Multiple View Instances. Update intro paragraph to remove carousel mention. (2) Ch21: Add "Graph Visualization" section after the results section documenting the triple-pattern graph tab. (3) Ch28: Add sections on contextual help text, IRI autocomplete, and simplified workflow view step.
  - Verify: `! grep -q "carousel" docs/guide/07-browsing-and-visualizing.md && grep -q "Kanban" docs/guide/07-browsing-and-visualizing.md && grep -q "Graph Visualization" docs/guide/21-sparql-console.md && grep -q "autocomplete\|Autocomplete" docs/guide/28-dashboards-and-workflows.md`
  - Done when: No carousel references in ch7, kanban/scope/saved views/multi-instance documented in ch7, graph tab documented in ch21, builder UX documented in ch28.

## Observability / Diagnostics

- **E2E test results**: `npx playwright test e2e/tests/02-views/m031-views.spec.ts --reporter=list` shows pass/fail per test case with assertion details. Failures surface the specific selector or count that didn't match.
- **Selector inspection**: The `SEL.views` object in `selectors.ts` centralises all kanban/scope/save selectors. A failing test that references `SEL.views.kanbanBoard` can be diagnosed by checking whether `.kanban-board` exists in the rendered DOM.
- **Dockview panel state**: `openGenericViewTab` helper logs nothing on success but throws Playwright timeout errors if `waitSelector` is not found within `timeoutMs`, making the root cause (missing panel, wrong selector, JS error) visible in the test output.
- **TypeScript compilation**: `tsc --noEmit --project e2e/tsconfig.json` catches import resolution issues across fixtures, helpers, and specs. Errors in the M031 files specifically indicate broken inter-file contracts.
- **Redaction**: No secrets or user data in test fixtures. The `TYPES` constant uses well-known seed URNs only.

## Files Likely Touched

- `e2e/tests/02-views/m031-views.spec.ts` (new)
- `e2e/tests/02-views/carousel-views.spec.ts` (deleted)
- `e2e/fixtures/seed-data.ts`
- `e2e/helpers/selectors.ts`
- `e2e/helpers/dockview.ts`
- `docs/guide/07-browsing-and-visualizing.md`
- `docs/guide/21-sparql-console.md`
- `docs/guide/28-dashboards-and-workflows.md`
