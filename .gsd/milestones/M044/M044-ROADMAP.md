# M044: Frontend Code Quality Execution

**Vision:** Execute the frontend quality improvements decided from the M041 audit: centralized fetch error handling, memory leak fixes, window namespace consolidation, CSS theme completion, template hygiene, and convention documentation. Each slice delivers a measurable quality improvement that's independently verifiable.

## Success Criteria

- Zero unhandled fetch() calls — all 131 callers use apiFetch() with .catch + resp.ok
- All dynamic-element event listeners have cleanup when dockview panels are destroyed
- All window.* globals consolidated under window.SemPKM.* namespace
- CSS theme variable adoption ≥98% (from 89.7%) — standalone hex ≤10, standalone rgba ≤20
- Zero namespace() hacks or .append() side-effects in templates — computation in Python views
- Notion/Obsidian importer templates deduplicated into shared bases
- htmx conventions documented, breakpoints standardized, console.log cleaned
- Full Playwright E2E test suite passes against Docker test stack — zero functional regressions

## Slices

- [x] **S01: Centralized Fetch Wrapper & Migration** `risk:high` `depends:[]`
  > After this: After this: all 131 fetch() calls route through apiFetch() with consistent error handling — network failures show user-facing toasts instead of silently failing

- [x] **S02: Event Listener & Timer Leak Fixes** `risk:high` `depends:[]`
  > After this: After this: opening and closing dockview panels (graph, kanban, SPARQL console) no longer leaks event listeners; federation panel can be reopened without duplicate polling intervals

- [x] **S03: Window Namespace Consolidation** `risk:medium` `depends:[]`
  > After this: After this: all cross-IIFE communication uses window.SemPKM.functionName instead of window.functionName — zero collision risk with third-party libraries

- [x] **S04: CSS Theme Completion & Utilities** `risk:low` `depends:[]`
  > After this: After this: CSS theme variable adoption is ≥98%; shared utility classes reduce workspace.css by ~500 lines; breakpoints are standardized to 600/768

- [x] **S05: Template Hygiene & Deduplication** `risk:medium` `depends:[]`
  > After this: After this: template computation logic lives in Python views (testable); Notion/Obsidian importers share base templates; guide/docs pages use loops instead of 81 copy-pasted buttons

- [ ] **S06: Console Cleanup & Convention Documentation** `risk:low` `depends:[]`
  > After this: After this: browser console is clean in production; htmx conventions are documented; debug logging available via flag

- [ ] **S07: E2E Regression Suite** `risk:low` `depends:[S01,S02,S03,S04,S05,S06]`
  > After this: Full Playwright E2E test suite passes against the Docker test stack with all M044 frontend changes applied — confirming zero functional regressions from fetch wrapper migration, event listener cleanup, namespace consolidation, CSS variable changes, and template refactoring.

## Boundary Map

### S01 → S02, S03
Produces: `apiFetch()` utility in a shared JS file — S02 and S03 can use it for any new fetch calls

### S02 (standalone)
Produces: Cleaned-up event listener patterns; registerCleanup() examples for dockview panels

### S03 → S04, S05, S06
Produces: `window.SemPKM` namespace — S04-S06 use it for any new cross-IIFE references

### S04 (standalone)
Produces: Complete CSS variable theme; utility classes; standardized breakpoints

### S05 (standalone)
Produces: Cleaner templates with Python-side computation; shared importer bases

### S06 (standalone)
Produces: Documented conventions; debug() utility; clean console output
