# S07 Research: E2E Tests + User Guide Docs

**Date:** 2026-03-21  
**Depth:** Light research — straightforward application of established E2E patterns + documentation updates for completed features  

## Summary

S07 is the trailing slice for M031. All 6 upstream slices (S01–S06) are merged to main. The work is: (1) Playwright E2E tests for all new/changed behavior, (2) user guide doc updates, (3) retire broken carousel-views.spec.ts. Split into 3 tasks: tests, docs, requirement validation.

## Key Findings

- `carousel-views.spec.ts` (175 lines) must be deleted — tests removed functionality
- `seed-data.ts` TYPES constant needs Task type added for kanban tests
- All template selectors for new features are well-defined (`.kanban-board`, `.view-scope-select`, `.sparql-vocab-pill`, etc.)
- Chapter 7 (Browsing and Visualizing) has 13 lines of carousel content to replace
- Chapter 21 (SPARQL Console) needs graph visualization tab section
- Chapter 28 (Dashboards and Workflows) needs help text/autocomplete/simplification docs
- Magic-link rate limit (5/min) requires consolidating test assertions