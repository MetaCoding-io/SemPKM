---
id: S32
parent: M001
milestone: M001
provides:
  - "Working htmx targets in all view templates (closest .group-editor-area)"
  - "Collapsible accordion card groups with chevron, label, count"
  - "Ungrouped cards sort to end of group list"
  - "Old view-type-switcher removed from toolbar"
  - "Carousel tab bar for switching between Table/Cards/Graph views per type"
  - "switchCarouselView() and restoreCarouselView() JS functions"
  - "Two-container pattern: carousel bar outside htmx swap target"
  - "localStorage persistence of carousel view preference per type IRI"
requires: []
affects: []
key_files: []
key_decisions:
  - "Accordion collapse state is ephemeral (no localStorage persistence per user decision)"
  - "Ungrouped cards sort last via (x[0] == 'Ungrouped', x[0]) tuple sort key"
  - "Two-container pattern eliminates need for _carouselSwitching flag -- carousel bar outside .carousel-view-body swap target"
  - "Prettified display names via renderer_type map: table->Table View, card->Cards View, graph->Graph View"
  - "sempkm_carousel_view localStorage key maps type_iri to spec_iri for per-type persistence"
  - "outerHTML swap with select: '.carousel-view-body' extracts only view body from response, discards response carousel bar"
patterns_established:
  - "htmx target pattern: hx-target='closest .group-editor-area' for all view templates in dockview world"
  - "CSS grid-template-rows 0fr/1fr for collapsible sections (consistent with Phase 31 properties)"
  - "Two-container pattern: carousel tab bar is outside the htmx swap target (.carousel-view-body), preventing re-render loops"
  - "Carousel view body wrapper: all view content (toolbar + body + pagination + scripts) wrapped in .carousel-view-body"
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-03
blocker_discovered: false
---
# S32: Carousel Views And View Bug Fixes

**# Phase 32 Plan 01: View Bug Fixes and Card Accordion Summary**

## What Happened

# Phase 32 Plan 01: View Bug Fixes and Card Accordion Summary

**Fixed all broken htmx targets from dockview migration, removed old view-type-switcher, and redesigned card groups as collapsible accordion sections with chevron/count UI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T06:08:57Z
- **Completed:** 2026-03-03T06:12:28Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Fixed all htmx targets in view templates from broken `#editor-area` to `closest .group-editor-area` (dockview-compatible)
- Removed the old broken `.view-type-switcher` markup, CSS, and `switchViewType()` JS function
- Redesigned cards group-by as collapsible accordion sections with chevron icons, labels, and count badges
- Changed ungrouped cards label from "(No value)" to "Ungrouped" and sorted to end of group list

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix all htmx targets and remove view-type-switcher** - `87e38c8` (fix)
2. **Task 2: Redesign cards group-by as collapsible accordion sections** - `3cd2baf` (feat)

## Files Created/Modified
- `backend/app/templates/browser/view_toolbar.html` - Removed view-type-switcher; fixed filter hx-target and afterSwap listener
- `backend/app/templates/browser/cards_view.html` - Fixed group-by hx-target; accordion section markup with toggleCardGroup()
- `backend/app/templates/browser/table_view.html` - Fixed sort header hx-target
- `backend/app/templates/browser/pagination.html` - Fixed all 5 hx-targets and 2 inline JS htmx.ajax targets
- `backend/app/templates/browser/search_suggestions.html` - Fixed "Create new" hx-target
- `backend/app/views/service.py` - Changed "(No value)" to "Ungrouped"; sort Ungrouped to end
- `frontend/static/css/views.css` - Removed view-type-switcher/btn CSS; added full accordion CSS

## Decisions Made
- Accordion collapse/expand state is ephemeral (all groups expanded by default, no persistence)
- Used tuple sort key `(x[0] == "Ungrouped", x[0])` to always sort Ungrouped last while keeping other groups alphabetical
- Followed CLAUDE.md Lucide icon rules for chevron SVG in flex container (flex-shrink: 0, stroke: currentColor via CSS)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All view htmx targets are dockview-compatible, ready for Plan 02 carousel tab bar
- Old view-type-switcher completely removed, clearing the toolbar for carousel replacement
- Card accordion pattern established, consistent with Phase 31 properties collapse

## Self-Check: PASSED

All 7 modified files verified present on disk. Both task commits (87e38c8, 3cd2baf) verified in git log.

---
*Phase: 32-carousel-views-and-view-bug-fixes*
*Completed: 2026-03-03*

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
