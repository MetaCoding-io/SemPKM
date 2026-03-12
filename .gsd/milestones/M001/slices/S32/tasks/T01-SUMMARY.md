---
id: T01
parent: S32
milestone: M001
provides:
  - "Working htmx targets in all view templates (closest .group-editor-area)"
  - "Collapsible accordion card groups with chevron, label, count"
  - "Ungrouped cards sort to end of group list"
  - "Old view-type-switcher removed from toolbar"
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-03
blocker_discovered: false
---
# T01: 32-carousel-views-and-view-bug-fixes 01

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
