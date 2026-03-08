---
phase: 40-e2e-test-coverage-v24
plan: 01
subsystem: testing
tags: [playwright, e2e, inference, lint-dashboard, htmx, bottom-panel]

requires:
  - phase: 35-owl2rl-inference
    provides: Inference panel UI and API endpoints
  - phase: 37-lint-dashboard
    provides: Global lint dashboard UI with filtering/sorting
provides:
  - Inference panel E2E tests (6 tests)
  - Lint dashboard E2E tests (7 tests)
affects: [40-02, e2e-maintenance]

tech-stack:
  added: []
  patterns:
    - "openBottomPanelTab() helper for bottom panel tab interaction"
    - ".first() locator for htmx-swapped duplicate elements"

key-files:
  created:
    - e2e/tests/09-inference/inference.spec.ts
    - e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts
  modified: []

key-decisions:
  - "Test inference UI infrastructure not triple content (seed data has pre-populated inverses)"
  - "Use .first() scoping on lint dashboard filter locators to handle htmx partial swap duplicates"

patterns-established:
  - "openBottomPanelTab(page, tabName): ensure panel open then click tab"
  - "htmx lazy-load testing: wait for revealed trigger then content selector"

requirements-completed: []

duration: 40min
completed: 2026-03-05
---

# Phase 40 Plan 01: Inference & Lint Dashboard E2E Tests Summary

**Playwright E2E tests for inference panel (6 tests) and global lint dashboard (7 tests) covering panel loading, API endpoints, filter controls, and htmx interactions**

## Performance

- **Duration:** 40 min
- **Started:** 2026-03-05T07:27:34Z
- **Completed:** 2026-03-05T08:08:04Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- 6 inference panel tests: panel loads, API run/triples/config endpoints work, filter controls have correct options, refresh button triggers htmx run
- 7 lint dashboard tests: dashboard lazy-loads via htmx revealed, creates invalid object to trigger violations, severity filter narrows rows, sort changes order, search filter works, health badge exists, API returns HTML partial
- Full suite: 192/201 tests pass (same 8 pre-existing failures, 1 pre-existing flaky)

## Task Commits

Each task was committed atomically:

1. **Task 1: Inference E2E tests** - `610e325` (test)
2. **Task 2: Lint dashboard E2E tests** - `d60baa1` (test)

## Files Created/Modified
- `e2e/tests/09-inference/inference.spec.ts` - 6 tests covering inference panel UI and API
- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` - 7 tests covering lint dashboard UI and API

## Decisions Made
- **Test inference UI infrastructure, not triple content**: The basic-pkm seed data already includes both sides of inverseOf relationships (hasParticipant + participatesIn), so owl:inverseOf inference produces 0 new triples. Additionally, rdfs:domain/rdfs:range inference triggers a pre-existing bug in _store_inferred_triples (SPARQL 400 from literal subjects). Tests verify panel rendering, filter controls, API response structure, and htmx refresh behavior instead.
- **Use .first() on lint dashboard filter locators**: The lint dashboard htmx filters target `#lint-dashboard-results` but the server response returns the full dashboard HTML, creating duplicate filter elements in the DOM. Using `.first()` ensures tests target the original (visible) filter controls.

## Deviations from Plan

### Discovery: Pre-existing inference storage bug

**Found during:** Task 1 investigation
- **Issue:** When rdfs:domain/rdfs:range entailment is enabled, inference produces triples where owlrl coerces literal values to URIRef subjects (e.g., `<knowledge-garden,curation,learning>`). The `_store_inferred_triples` method wraps all terms in angle brackets (`<{o}>`), producing invalid SPARQL for non-IRI URIRef objects. This causes HTTP 400 from the triplestore.
- **Impact:** Inference works correctly with owl:inverseOf + sh:rule (default config) since these produce 0 triples with current seed data. Only rdfs:domain/rdfs:range triggers the bug.
- **Scope:** Pre-existing (not caused by this plan's changes). Logged but not fixed per scope boundary rules.

### Discovery: Rules graph not loaded during model install

**Found during:** Task 1 investigation
- **Issue:** `models.py` install method writes ontology, shapes, and views graphs but does NOT write the rules graph (`basic-pkm.ttl`). SHACL-AF rules are never loaded into the triplestore, so sh:rule inference cannot find rules to execute.
- **Impact:** sh:rule entailment type is enabled in config but non-functional.
- **Scope:** Pre-existing. Logged but not fixed.

---

**Total deviations:** 0 auto-fixed, 2 pre-existing issues discovered and documented
**Impact on plan:** Tests adapted to verify UI infrastructure rather than specific triple content due to seed data completeness and pre-existing bugs.

## Issues Encountered
- Inference pipeline investigation consumed significant time (25+ min) before discovering seed data has pre-populated inverses and the domain/range storage bug
- The workspace-layout test `bottom panel exists with EVENT LOG, AI COPILOT tabs` fails because it expects 2 panel tabs but the workspace now has 4 (pre-existing, not from this plan)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Test infrastructure for bottom panel interaction established (openBottomPanelTab helper pattern)
- 40-02 (helptext + bug-fixes tests) can proceed independently
- Full test suite green except known pre-existing failures

---
*Phase: 40-e2e-test-coverage-v24*
*Completed: 2026-03-05*
