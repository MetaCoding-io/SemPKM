---
phase: 05-data-browsing-and-visualization
plan: 01
subsystem: ui
tags: [sparql, htmx, jinja2, views, pagination, table, column-prefs]

# Dependency graph
requires:
  - phase: 03-mental-model-system
    provides: "Model registry, view spec JSONLD data in triplestore"
  - phase: 04-admin-shell-and-object-creation
    provides: "IDE workspace layout, tab system, browser router"
provides:
  - "ViewSpecService loading view specs from model views graphs"
  - "Extensible renderer registry with register_renderer() for custom types"
  - "Table view with sortable columns, text filtering, numbered pagination"
  - "Column visibility preferences persisted per type in localStorage"
  - "View endpoints for table rendering at /browser/views/table/{spec_iri}"
affects: [05-data-browsing-and-visualization, phase-6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "View spec execution pipeline: load from triplestore -> scope to current graph -> execute with pagination"
    - "SPARQL WHERE clause extraction and recomposition for count queries and pagination"
    - "htmx server-rendered table with query parameter state management for sort/filter/page"
    - "localStorage column preference persistence per type IRI"

key-files:
  created:
    - backend/app/views/__init__.py
    - backend/app/views/service.py
    - backend/app/views/registry.py
    - backend/app/views/router.py
    - backend/app/templates/browser/table_view.html
    - backend/app/templates/browser/pagination.html
    - backend/app/templates/browser/view_toolbar.html
    - backend/app/templates/browser/view_menu.html
    - frontend/static/css/views.css
    - frontend/static/js/column-prefs.js
  modified:
    - backend/app/dependencies.py
    - backend/app/main.py
    - backend/app/templates/base.html

key-decisions:
  - "SPARQL WHERE clause extraction via regex brace-depth counting for count query and pagination recomposition"
  - "Deduplication by ?s in table rows to handle OPTIONAL cross-product results per Research Pitfall 5"
  - "View router prefix /browser/views included before browser_router for route specificity"
  - "Column labels derived from SPARQL variable names (capitalized) rather than additional label resolution queries"

patterns-established:
  - "ViewSpecService pattern: query model registry -> build FROM clauses -> execute SPARQL -> parse results"
  - "View toolbar partial with type switcher, debounced filter input, and column settings gear"
  - "Pagination partial with numbered pages, ellipsis for large page counts, and jump-to-page input"

requirements-completed: [VIEW-07, VIEW-01]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 5 Plan 1: ViewSpecService and Table View Summary

**ViewSpecService loads view specs from installed model views graphs and executes SPARQL queries; table view renders with sortable columns, text filtering, numbered pagination, and column visibility preferences**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T22:20:09Z
- **Completed:** 2026-02-22T22:25:59Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- ViewSpecService loads all 12 view specs from Basic PKM model (4 types x 3 renderer types) via SPARQL FROM clauses
- Table view renders with sortable column headers, text filter with 300ms debounce, and numbered pagination
- Extensible renderer registry with table/card/graph built-in types plus register_renderer() for Mental Model custom types
- Column visibility preferences toggle and persist per type IRI in localStorage

## Task Commits

Each task was committed atomically:

1. **Task 1: ViewSpecService and renderer registry** - `617c857` (feat)
2. **Task 2: Table view router, templates, column prefs, and styles** - `79896c1` (feat)

## Files Created/Modified
- `backend/app/views/__init__.py` - Views module init
- `backend/app/views/service.py` - ViewSpecService with get_all_view_specs, get_view_specs_for_type, execute_table_query
- `backend/app/views/registry.py` - Renderer registry with RENDERER_REGISTRY, register_renderer, get_registered_renderers
- `backend/app/views/router.py` - View router with /browser/views/list and /browser/views/table endpoints
- `backend/app/templates/browser/table_view.html` - Server-rendered table with sortable headers and column prefs
- `backend/app/templates/browser/pagination.html` - Reusable pagination with numbered pages and jump-to-page
- `backend/app/templates/browser/view_toolbar.html` - Shared toolbar with type switcher, filter, and column settings
- `backend/app/templates/browser/view_menu.html` - View menu listing specs grouped by renderer type
- `frontend/static/css/views.css` - Styles for table, pagination, toolbar, column settings dropdown
- `frontend/static/js/column-prefs.js` - Column visibility toggle UI and localStorage persistence
- `backend/app/dependencies.py` - Added get_view_spec_service dependency
- `backend/app/main.py` - ViewSpecService in lifespan, views_router included before browser_router
- `backend/app/templates/base.html` - Added views.css and column-prefs.js

## Decisions Made
- SPARQL WHERE clause extraction uses regex brace-depth counting for reliable parsing of nested query structures
- Table rows are deduplicated by ?s to handle OPTIONAL cross-product results per Research Pitfall 5
- Views router included before browser_router since /browser/views is more specific than /browser
- Column header labels derived from SPARQL variable names (capitalized) for simplicity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ViewSpecService foundation ready for cards view (05-02) and graph view (05-03)
- Renderer registry ready for custom renderer registration from Mental Models
- Pagination partial is reusable for cards view
- View toolbar partial is reusable for all view types

## Self-Check: PASSED

All 10 created files verified present. Both task commits (617c857, 79896c1) verified in git log.

---
*Phase: 05-data-browsing-and-visualization*
*Completed: 2026-02-22*
