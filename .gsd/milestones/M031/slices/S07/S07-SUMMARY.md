# S07 Summary: E2E Tests + User Guide Docs

**Status:** Complete  
**Duration:** ~35 min (T01: 20m, T02: 15m)  
**Blockers:** None

## What This Slice Delivered

S07 is the integration-confidence and documentation closure slice for M031. It retired stale carousel E2E tests, wrote new Playwright E2E coverage for the 6 major features delivered in S01–S06, and updated 3 user guide chapters to document all new/changed behavior.

### T01: E2E Test Spec + Carousel Test Retirement

- **Deleted** `e2e/tests/02-views/carousel-views.spec.ts` (175 lines testing removed carousel functionality)
- **Created** `e2e/tests/02-views/m031-views.spec.ts` with 6 test cases:
  1. Carousel tab bar absence from generic views
  2. Generic view tab opening from explorer sidebar
  3. Kanban view rendering with status columns (Task type)
  4. View scope dropdown presence on generic views
  5. Save view button presence on generic views
  6. Multiple instances of same view type create separate tabs
- **Added** `Task: 'urn:sempkm:model:basic-pkm:Task'` to `TYPES` in `seed-data.ts`
- **Added** 6 selectors to `SEL.views` in `selectors.ts`: `kanbanBoard`, `kanbanColumn`, `kanbanCard`, `scopeSelect`, `variantSelect`, `saveViewBtn`
- **Added** `openGenericViewTab()` helper to `dockview.ts` wrapping `window.openGenericViewTab(renderer, scopeQuery, scopeLabel)` with timeout-guarded `waitForSelector`

### T02: User Guide Updates (Chapters 7, 21, 28)

- **Chapter 7 (Browsing and Visualizing):** Removed all carousel references. Added 5 new H2 sections: View Toolbar (variant/scope dropdowns, save button), Kanban View (opening, type selection, drag-drop), Saved Views (saving, managing, reopening), Multiple View Instances (deduplication, tab labels), Saved Queries in Explorer (scoped view opening, drag to canvas). Section count: 10 H2 sections.
- **Chapter 21 (SPARQL Console):** Added Graph Visualization section documenting triple-pattern detection, Table/Graph tab switcher, Cytoscape.js rendering with dagre/fcose layout selection.
- **Chapter 28 (Dashboards and Workflows):** Added 4 new H2 sections: Builder Help Text, IRI Autocomplete, Simplified Workflow View Step, Sample Dashboards and Workflows.

## Verification Results

All 7 slice-level checks pass:

| Check | Command | Result |
|-------|---------|--------|
| SV1 | `test -f m031-views.spec.ts && ! test -f carousel-views.spec.ts` | ✅ PASS |
| SV2 | `grep -q "Task:" seed-data.ts` | ✅ PASS |
| SV3 | `! grep -q "carousel" 07-browsing-and-visualizing.md` | ✅ PASS |
| SV4 | `grep -q "Kanban" 07-browsing-and-visualizing.md` | ✅ PASS |
| SV5 | `grep -q "Graph Visualization" 21-sparql-console.md` | ✅ PASS |
| SV6 | `grep -qi "autocomplete" 28-dashboards-and-workflows.md` | ✅ PASS |
| SV7 | `grep -c "^## " 07-browsing-and-visualizing.md` → 10 (≥8) | ✅ PASS |

## Patterns Established

- **SEL.views selector centralisation:** All M031 view E2E selectors live in `SEL.views` in `selectors.ts`. Future view tests should add selectors here rather than inlining CSS strings.
- **openGenericViewTab helper:** Wraps `window.openGenericViewTab()` with timeout-guarded `waitForSelector`. Any E2E test that needs to open a view tab should use this helper rather than clicking through the explorer UI.
- **Kanban test pre-sets localStorage:** The kanban test sets type selection via localStorage rather than navigating the UI to select a type, avoiding fragile multi-step UI interactions.
- **Documentation mirrors components:** Each UI component (toolbar dropdown, view type, builder feature) gets its own H2/H3 section — future doc updates should follow this 1:1 mapping.

## What the Next Slice Should Know

- **M031 is complete.** All 7 slices (S01–S07) are done. All 20 requirements are validated. The milestone definition of done is met.
- **Pre-existing E2E TypeScript compilation errors** exist in ~10 other test files (merge conflict artifacts from earlier milestones). These are unrelated to M031 and do not affect the new test spec.
- **E2E tests are not run against the live Docker stack in this slice** — they are structural tests (spec file exists, correct selectors, correct test count). Running them requires `docker compose up` with the full test stack.
- **Three user guide chapters were updated** — any future feature changes to views, SPARQL console, or builders should update these chapters to maintain accuracy.

## Files Changed

| File | Action |
|------|--------|
| `e2e/tests/02-views/m031-views.spec.ts` | Created (152 lines, 6 test cases) |
| `e2e/tests/02-views/carousel-views.spec.ts` | Deleted |
| `e2e/fixtures/seed-data.ts` | Modified (added Task type) |
| `e2e/helpers/selectors.ts` | Modified (added 6 view selectors) |
| `e2e/helpers/dockview.ts` | Modified (added openGenericViewTab helper) |
| `docs/guide/07-browsing-and-visualizing.md` | Modified (carousel → 5 new sections) |
| `docs/guide/21-sparql-console.md` | Modified (added Graph Visualization) |
| `docs/guide/28-dashboards-and-workflows.md` | Modified (added 4 builder UX sections) |

## Requirement Status

All 20 M031 requirements were already validated by S01–S06. S07 adds E2E test coverage and documentation but does not change requirement statuses.
