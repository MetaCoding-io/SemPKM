---
phase: 32-carousel-views-and-view-bug-fixes
plan: 02
subsystem: ui
tags: [carousel, view-switching, htmx, localStorage, two-container-pattern]

# Dependency graph
requires:
  - phase: 32-carousel-views-and-view-bug-fixes
    provides: "Plan 01 removed view-type-switcher and fixed htmx targets for dockview"
provides:
  - "Carousel tab bar for switching between Table/Cards/Graph views per type"
  - "switchCarouselView() and restoreCarouselView() JS functions"
  - "Two-container pattern: carousel bar outside htmx swap target"
  - "localStorage persistence of carousel view preference per type IRI"
affects: [33-layout-persistence, e2e-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-container-pattern, carousel-outerHTML-swap-with-select]

key-files:
  created:
    - backend/app/templates/browser/carousel_tab_bar.html
  modified:
    - backend/app/templates/browser/table_view.html
    - backend/app/templates/browser/cards_view.html
    - backend/app/templates/browser/graph_view.html
    - frontend/static/js/workspace.js
    - frontend/static/css/views.css

key-decisions:
  - "Two-container pattern eliminates need for _carouselSwitching flag -- carousel bar outside .carousel-view-body swap target"
  - "Prettified display names via renderer_type map: table->Table View, card->Cards View, graph->Graph View"
  - "sempkm_carousel_view localStorage key maps type_iri to spec_iri for per-type persistence"
  - "outerHTML swap with select: '.carousel-view-body' extracts only view body from response, discards response carousel bar"

patterns-established:
  - "Two-container pattern: carousel tab bar is outside the htmx swap target (.carousel-view-body), preventing re-render loops"
  - "Carousel view body wrapper: all view content (toolbar + body + pagination + scripts) wrapped in .carousel-view-body"

requirements-completed: [VIEW-02]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 32 Plan 02: Carousel Tab Bar Summary

**Carousel tab bar with two-container pattern for instant view switching, localStorage persistence, and CSS loading spinner**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T06:15:22Z
- **Completed:** 2026-03-03T06:18:28Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Carousel tab bar renders above view body for types with 2+ manifest views, hidden for single-view types
- Instant view switching via htmx with two-container pattern (tab bar persists, only view body swaps)
- Active tab persists per type IRI in localStorage across sessions
- Loading spinner overlay during view fetch, automatically removed by htmx swap
- Prettified tab labels: "Table View", "Cards View", "Graph View"

## Task Commits

Each task was committed atomically:

1. **Task 1: Create carousel tab bar template and integrate into views** - `fc94dad` (feat)
2. **Task 2: Add carousel view switching JS, loading spinner, and CSS** - `a554263` (feat)

## Files Created/Modified
- `backend/app/templates/browser/carousel_tab_bar.html` - Jinja2 partial rendering carousel tab bar with prettified display names
- `backend/app/templates/browser/table_view.html` - Added carousel include + .carousel-view-body wrapper
- `backend/app/templates/browser/cards_view.html` - Added carousel include + .carousel-view-body wrapper
- `backend/app/templates/browser/graph_view.html` - Added carousel include + .carousel-view-body wrapper
- `frontend/static/js/workspace.js` - switchCarouselView() and restoreCarouselView() functions
- `frontend/static/css/views.css` - Carousel tab bar styles, active state with bottom-border accent, loading spinner

## Decisions Made
- Two-container pattern eliminates need for _carouselSwitching state flag -- no infinite loop possible because carousel bar is not re-rendered during tab switches
- Prettified display names from renderer_type map (not stripping type prefix from spec.label)
- sempkm_carousel_view localStorage key follows existing sempkm_ namespace convention
- Filter input found via .view-filter-input class selector (not #view-filter ID) to avoid duplicate ID issues
- outerHTML swap with select: '.carousel-view-body' cleanly extracts only view body from full response

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Carousel tab bar is fully functional for all multi-view types
- Phase 32 is complete (Plan 01 bug fixes + Plan 02 carousel)
- Ready for Phase 33 (layout persistence) or Phase 34 (E2E test updates)

## Self-Check: PASSED

All 6 files verified present. Both task commits (fc94dad, a554263) confirmed in git log. SUMMARY.md exists.

---
*Phase: 32-carousel-views-and-view-bug-fixes*
*Completed: 2026-03-03*
