---
phase: 05-data-browsing-and-visualization
plan: 02
subsystem: ui
tags: [htmx, jinja2, views, cards, css-flip, pagination, grouping]

# Dependency graph
requires:
  - phase: 05-data-browsing-and-visualization
    plan: 01
    provides: "ViewSpecService, renderer registry, pagination partial, view toolbar partial"
provides:
  - "Cards view renderer with CSS 3D flip animation"
  - "execute_cards_query method for paginated card data with properties and relationships"
  - "Card grouping by property value"
  - "Reusable pagination and toolbar partials across view types"
affects: [05-data-browsing-and-visualization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS 3D flip card: perspective + backface-visibility + rotateY transform"
    - "Batch SPARQL property and relationship fetching for card data"
    - "View-type-aware shared partials via Jinja2 default filters"

key-files:
  created:
    - backend/app/templates/browser/cards_view.html
  modified:
    - backend/app/views/service.py
    - backend/app/views/router.py
    - frontend/static/css/views.css
    - backend/app/templates/browser/pagination.html
    - backend/app/templates/browser/view_toolbar.html

key-decisions:
  - "Router endpoint uses /card/ (singular) to match renderer_type value from view specs for consistent type switcher navigation"
  - "Card properties fetched via separate SPARQL queries (literals, outbound IRI, inbound IRI) for clean separation"
  - "Pagination and toolbar partials made view-type-aware via Jinja2 default filters for reuse across table/card/graph"
  - "Body snippet from urn:sempkm:body with dcterms:description fallback, truncated to 100 chars"

patterns-established:
  - "Card data pipeline: subjects query -> properties query -> outbound query -> inbound query -> label resolution -> assembly"
  - "View-type-aware partials: view_type variable drives URL construction in shared toolbar and pagination"

requirements-completed: [VIEW-02]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 5 Plan 2: Cards View Summary

**Flippable card grid with CSS 3D flip animation showing title/snippet on front, properties/relationships on back, optional grouping by property, and shared pagination**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T22:30:07Z
- **Completed:** 2026-02-22T22:34:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Cards view renders with CSS 3D flip animation (GPU-composited transform only)
- Card front shows title and body snippet (truncated to 100 chars with ellipsis)
- Card back shows all properties and both outbound/inbound relationships with clickable links
- Optional grouping by any property value via Group By dropdown
- Pagination and toolbar partials made reusable across all view types (table, card, graph)

## Task Commits

Each task was committed atomically:

1. **Task 1: Cards query execution and router endpoint** - `9e7e924` (feat)
2. **Task 2: Cards view template with CSS flip animation** - `0f3e9df` (feat)

## Files Created/Modified
- `backend/app/templates/browser/cards_view.html` - Server-rendered card grid with CSS flip and group-by support
- `backend/app/views/service.py` - Added execute_cards_query with property/relation batch fetching
- `backend/app/views/router.py` - Added GET /browser/views/card/{spec_iri} endpoint with grouping and view_type for table
- `frontend/static/css/views.css` - Card grid, flip animation, group header, and group-by bar styles
- `backend/app/templates/browser/pagination.html` - Made view-type-aware via pag_view_type variable
- `backend/app/templates/browser/view_toolbar.html` - Made view-type-aware via filter_base_url variable

## Decisions Made
- Router endpoint uses `/card/` (singular) to match the `renderer_type` value from view specs, ensuring the type switcher in the toolbar navigates correctly between table/card/graph views
- Card properties fetched via three separate SPARQL queries (literal properties, outbound IRI relationships, inbound IRI relationships) rather than a single complex query for reliability
- Pagination and toolbar partials refactored to derive URLs from a `view_type` context variable instead of hardcoding `/browser/views/table/`
- Body snippet sourced from `urn:sempkm:body` with `dcterms:description` fallback, truncated to 100 characters

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made pagination and toolbar partials view-type-aware**
- **Found during:** Task 1 (Router endpoint implementation)
- **Issue:** Both pagination.html and view_toolbar.html had hardcoded `/browser/views/table/` URLs, preventing reuse for cards view
- **Fix:** Introduced `view_type` context variable and Jinja2 `default('table')` filters to dynamically construct URLs
- **Files modified:** backend/app/templates/browser/pagination.html, backend/app/templates/browser/view_toolbar.html
- **Verification:** Table view continues working (backward compatible default); cards view uses correct URLs
- **Committed in:** 9e7e924 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed endpoint URL to match renderer_type convention**
- **Found during:** Task 2 (Template implementation)
- **Issue:** Plan specified `/browser/views/cards/` but view spec renderer_type is `card` (singular), causing type switcher navigation to fail
- **Fix:** Changed endpoint from `/cards/` to `/card/` and matched view_type context variable
- **Files modified:** backend/app/views/router.py, backend/app/templates/browser/cards_view.html
- **Verification:** Type switcher URLs now match router endpoints
- **Committed in:** 0f3e9df (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes essential for correct routing. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Cards view complete, ready for graph view (05-03)
- View-type-aware partials ready for graph view reuse
- All three renderer types (table, card, graph) now have URL patterns established

## Self-Check: PASSED

All files verified present. Both task commits (9e7e924, 0f3e9df) verified in git log.

---
*Phase: 05-data-browsing-and-visualization*
*Completed: 2026-02-22*
