---
depends_on: [M048]
---

# M050: View System Rework

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Fix the view toolbar UX — replace the overwhelming 37-pill type bar with a smart dropdown, remove the confusing View Variants concept, fix responsive sizing, repair the save view flow, and make each renderer only show compatible types.

## Why This Milestone

The view toolbar is the primary interface for browsing data, and it's broken in multiple ways. 37 pills across 4 rows eat 140px of viewport. The "View Variants" dropdown is confusing. Views don't fill available space. The save flow is undiscoverable. Calendar nav icons are invisible in dark mode. These issues compound to make every view feel half-finished.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open any view and see a clean toolbar with a query scope dropdown + type filter dropdown (no pills)
- See only relevant types for the current renderer (kanban shows only types with status fields, timeline shows only types with date fields)
- Have views fill 100% available width and height
- Save a view configuration and find it later in Saved Views
- See calendar navigation buttons in both light and dark mode

### Entry point / environment

- Entry point: http://localhost:4000/browser/ → VIEWS section
- Environment: Docker Compose dev stack
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: E2E tests for type dropdown, responsive sizing, save/restore views
- Integration complete means: all 8 view renderers use the new toolbar consistently
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Open Kanban View → type dropdown shows only types with sh:in status fields
- Open Timeline View → type dropdown shows only types with date fields
- Resize browser window → all views fill available space
- Save a view → find it in Saved Views → open it → same filters restored
- Dark mode → calendar nav buttons visible

## Risks and Unknowns

- **Smart type filtering** requires querying SHACL shapes at view-open time to determine which types have compatible fields. This adds a query but could be cached.
- **Removing View Variants** may break existing saved views that reference variant IDs.
- **Save flow** — the existing save infrastructure may be partially built but broken, or may need full implementation.

## Existing Codebase / Prior Art

- `backend/app/views/service.py` — ViewSpecService with `_detect_status_field()`, `_detect_date_fields()`, `_detect_geo_fields()` already exist for kanban/calendar/map field detection
- `backend/app/views/router.py` — view rendering endpoints
- `frontend/static/js/workspace.js` — view toolbar pill rendering, variant dropdown
- `backend/app/templates/browser/view_toolbar.html` — the toolbar template with pills

## Scope

### In Scope

- **#37** Replace pill bar with type filter dropdown — smart-filtered by query result set
- **#38** Remove View Variants dropdown entirely
- **#39** Two-dropdown toolbar: query scope (primary) + type filter (secondary)
- **#47, #53** Smart type filtering by renderer (kanban→status types, timeline→date types, map→geo types)
- **#48, #55** Views take 100% available width and height
- **#49** Fix calendar nav button icons in dark mode
- **#50** Filter field shows human-readable labels instead of raw IRIs
- **#52** Timeline scroll-to-today
- **#54** Timeline popover dismiss on click-outside/Escape
- **#56** Timeline selection → object detail in right panel
- **#57, #58** Fix save view flow
- **#60** Add geo fields to CRM Contact/Company or basic-pkm Event + seed data for map view

### Out of Scope / Non-Goals

- Visual styling of view content (kanban cards, timeline bars) — that's M052 (Design System)
- Explorer composable filter/group/sort — that's M054
- New view renderers

## Open Questions

- Should the type dropdown be a multi-select (show multiple types simultaneously) or single-select?
- How should saved views store their configuration — RDF or localStorage?
