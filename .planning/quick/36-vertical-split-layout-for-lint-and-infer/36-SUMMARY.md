---
phase: quick-36
plan: 01
subsystem: ui
tags: [css-layout, flexbox, htmx, inference, lint, vertical-split, cards]

requires:
  - phase: none
    provides: n/a
provides:
  - "Vertical split (sidebar + main) layout for lint dashboard and inference panels"
  - "Card-based rendering for inference triples (replaces table rows)"
affects: [workspace-ui, inference, lint]

tech-stack:
  added: []
  patterns: ["sidebar-group label pattern for stacked filter controls", "card-based triple rendering with hover-reveal actions"]

key-files:
  created: []
  modified:
    - backend/app/templates/browser/lint_dashboard.html
    - backend/app/templates/browser/inference_panel.html
    - frontend/static/css/workspace.css
    - backend/app/inference/router.py

key-decisions:
  - "Sidebar width 25% with min 180px / max 280px bounds for consistent sizing"
  - "Summary/meta info pushed to bottom of sidebar via margin-top: auto"
  - "Card layout uses inline subject-predicate-object flow instead of table columns"
  - "Responsive breakpoint at 600px stacks sidebar above main content"

patterns-established:
  - "Sidebar-group: labeled filter controls stacked vertically with uppercase micro-labels"

requirements-completed: [QUICK-36]

duration: 3min
completed: 2026-03-10
---

# Quick Task 36: Vertical Split Layout for Lint and Inference Summary

**Bottom panel lint dashboard and inference tabs converted to vertical split (25% sidebar + 75% results) with card-based inference triple rendering**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T04:58:55Z
- **Completed:** 2026-03-10T05:02:31Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Lint dashboard filters and summary moved to left sidebar, results table stays on right
- Inference panel controls, filters, and metadata moved to left sidebar with labeled groups
- Inference results render as cards (subject-predicate-object inline flow) instead of dense table rows
- Card actions (dismiss/promote) use `hx-target="closest .inference-card"` for correct htmx swap
- Responsive fallback stacks layout vertically below 600px

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure lint and inference templates to vertical split** - `01aebc1` (feat)
2. **Task 2: Update CSS for vertical split layout and inference card presentation** - `b359d08` (feat)

## Files Created/Modified
- `backend/app/templates/browser/lint_dashboard.html` - Restructured to sidebar+main two-column layout
- `backend/app/templates/browser/inference_panel.html` - Restructured to sidebar+main two-column layout with labeled filter groups
- `frontend/static/css/workspace.css` - New sidebar/main flex styles for both panels, card styles for inference, responsive fallback
- `backend/app/inference/router.py` - Replaced table row rendering with card-based div rendering

## Decisions Made
- Sidebar width set to 25% with min-width 180px and max-width 280px for consistent sizing across panel widths
- Summary/meta info pushed to sidebar bottom via `margin-top: auto` for visual hierarchy
- Card layout uses inline flex flow (subject -> predicate -> object) with type badge and hover-reveal actions
- Responsive breakpoint at 600px stacks sidebar above main content area

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Layout changes are purely visual, no API or data changes
- All htmx interactions preserved (filtering, dismiss, promote)

## Self-Check: PASSED
- All 4 modified files exist on disk
- 36-SUMMARY.md created
- Commit 01aebc1 (Task 1) found in git history
- Commit b359d08 (Task 2) found in git history
