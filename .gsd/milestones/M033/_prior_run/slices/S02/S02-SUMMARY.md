---
id: S02
parent: M033
milestone: M033
provides:
  - Calendar renderer registered in RENDERER_REGISTRY and _VALID_RENDERERS
  - SHACL-driven date property auto-detection (_detect_date_fields)
  - Calendar SPARQL query builder and FullCalendar-compatible JSON data endpoint
  - FullCalendar 6.x vendored with content-hash and CDN fallback
  - calendar_view.html template with type filter pills, view toolbar, error state
  - calendar.js with month/week/day views, eventClick → openTab(), auto-refetch
  - Dark mode CSS (13 --fc-* custom property overrides)
  - Explorer sidebar Calendar View entry with canvas drag support
  - 24 unit tests covering date detection, query building, event transformation
requires: []
affects:
  - S03  # Map view follows the same "new renderer" registration pattern
key_files:
  - backend/app/views/registry.py
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/js/calendar.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
  - frontend/build.js
  - backend/tests/test_calendar.py
key_decisions:
  - Date detection uses two-stage approach — exact well-known path match first (schema:startDate/endDate), then datatype+name ranking — because Event shape has no sh:datatype on startDate/endDate
  - FullCalendar loaded only in calendar template (not base.html) following D272 lazy-load pattern; calendar.js loaded in base.html so initCalendar is available for tryInit polling
  - Calendar data endpoint reuses generic_graph_data() with elif branch rather than a separate route
patterns_established:
  - New renderer registration pattern proven end-to-end — registry entry, _VALID_RENDERERS, generic_view branch, data endpoint branch, template, JS init function, explorer sidebar entry, workspace.js label
  - _detect_date_fields() follows _detect_status_field() pattern — SHACL PropertyShape scan with priority ranking
  - Vendor library build pipeline (build.js section → content-hash → manifest → CDN fallback) reusable for Leaflet (S03)
observability_surfaces:
  - execute_calendar_query INFO logs with type, paths, scope, event count
  - _detect_date_fields WARNING on shapes lookup failure
  - GET /browser/views/generic/calendar/data?type=<iri> JSON endpoint for debugging
  - console.warn '[calendar] Container not found' and console.error '[calendar] Failed to load events' in browser
drill_down_paths:
  - .gsd/milestones/M033/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S02/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-21
---

# S02: Calendar View Renderer

**Calendar view registered, wired end-to-end with SHACL-driven date detection, FullCalendar 6.x rendering, type filter pills, click-to-open, dark mode, and 24 unit tests**

## What Happened

Three tasks delivered the complete calendar view feature:

**T01 (backend)** registered "calendar" in `RENDERER_REGISTRY` and `_VALID_RENDERERS`, then added three methods to `ViewSpecService`: `_detect_date_fields()` scans SHACL PropertyShapes for date properties using a two-stage strategy — exact well-known path matching first (`schema:startDate`, `schema:endDate`), then datatype-based detection (`xsd:date`/`xsd:dateTime`) with path-name ranking as tiebreaker. `_build_calendar_select()` generates SPARQL SELECT queries with optional type filter, scope sub-select, and OPTIONAL end-date clause. `execute_calendar_query()` runs the query, transforms bindings to FullCalendar JSON format (`{id, title, start, end, extendedProps: {iri, type}}`), deduplicates by IRI, and skips entries without start dates. The `generic_view()` and `generic_graph_data()` functions received `elif renderer == "calendar"` branches.

**T02 (frontend)** vendored FullCalendar 6.x via `build.js` (content-hashed to `fullcalendar-b101204b.min.js` with manifest entry), created `calendar_view.html` using the `.view-flex-column` wrapper with type filter pills, view toolbar, error state for types without date properties, and tryInit polling. `calendar.js` is an IIFE with `initCalendar()` supporting dayGridMonth/timeGridWeek/timeGridDay header buttons, fetch-based event source with auto-refetch on type filter change, eventClick → `openTab()`, and double-init prevention. Dark mode handled via 13 `--fc-*` CSS custom property overrides in `views.css`. Explorer sidebar got a Calendar View tree-leaf entry with canvas drag support. `workspace.js` labels dict extended with `calendar: 'Calendar View'`.

**T03 (tests)** created 24 unit tests in `test_calendar.py` across three test classes: `TestDetectDateFields` (11 tests covering path matching, datatype detection, fallback ranking, http/https schema.org variants, error paths), `TestBuildCalendarSelect` (6 tests for query structure variants), and `TestExecuteCalendarQuery` (7 tests for JSON format, deduplication, label fallback, error handling).

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_calendar.py -v` | ✅ 24/24 passed (0.46s) |
| `"calendar"` in RENDERER_REGISTRY | ✅ Present |
| `"calendar"` in _VALID_RENDERERS | ✅ Present |
| `fullcalendar.js` in manifest.json | ✅ `fullcalendar-b101204b.min.js` |
| CDN fallback in calendar_view.html | ✅ jsdelivr fallback present |
| Explorer sidebar Calendar entry | ✅ `openGenericViewTab('calendar')` onclick |
| workspace.js label registered | ✅ `calendar: 'Calendar View'` |
| calendar.js month/week/day buttons | ✅ dayGridMonth, timeGridWeek, timeGridDay |
| calendar.js eventClick → openTab | ✅ Extracts iri from extendedProps |
| Dark mode --fc-* overrides | ✅ 13 custom properties in views.css |
| calendar.js in base.html | ✅ Script tag after kanban.js |
| Type filter pills included | ✅ type_filter_pills.html include |
| View toolbar included | ✅ view_toolbar.html include |

## Requirements Advanced

- CAL-01 through CAL-06 — All created and validated by this slice

## Requirements Validated

- CAL-01 — Calendar renderer registered and selectable (registry + explorer + workspace label)
- CAL-02 — Date property auto-detection from SHACL shapes (11 unit tests)
- CAL-03 — FullCalendar 6.x lazy-loaded with CDN fallback (build pipeline + manifest)
- CAL-04 — Month/week/day view switching (headerToolbar config)
- CAL-05 — Click-to-open object tab from calendar event (eventClick handler + 7 execute tests)
- CAL-06 — Calendar dark mode support (13 --fc-* overrides)

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- `calendar.js` added to `base.html` alongside `graph.js` and `kanban.js` — not in the original plan but necessary for the tryInit polling pattern (template checks `window.initCalendar` before FullCalendar loads).
- 24 tests written instead of the planned minimum 12 — additional edge cases for http/https schema.org variants and error paths were low-cost to add.

## Known Limitations

- Calendar view requires a running Docker stack with triplestore to render real data. Unit tests mock the SPARQL layer.
- No drag-to-reschedule — FullCalendar supports it but editable events would need a write-back API.
- Date detection relies on SHACL shapes existing for the type — types without shapes get the fallback FILTER query which may be slower on large datasets.

## Follow-ups

None — S02 is self-contained per the plan.

## Files Created/Modified

- `backend/app/views/registry.py` — Added "calendar" to RENDERER_REGISTRY
- `backend/app/views/router.py` — Added "calendar" to _VALID_RENDERERS, calendar branch in generic_view() and generic_graph_data()
- `backend/app/views/service.py` — Added _detect_date_fields(), _build_calendar_select(), execute_calendar_query()
- `backend/app/templates/browser/calendar_view.html` — New template with FullCalendar init, type pills, toolbar, error state
- `frontend/static/js/calendar.js` — New IIFE with initCalendar() for FullCalendar rendering
- `frontend/static/css/views.css` — Calendar container styles and dark mode --fc-* overrides
- `backend/app/templates/browser/views_explorer.html` — Calendar View tree-leaf entry
- `frontend/static/js/workspace.js` — calendar label in openGenericViewTab()
- `backend/app/templates/base.html` — calendar.js script tag
- `frontend/package.json` — fullcalendar dependency
- `frontend/build.js` — FullCalendar vendor section (section 7)
- `backend/tests/test_calendar.py` — 24 unit tests

## Forward Intelligence

### What the next slice should know
- The "new renderer" pattern is now proven across two views (kanban in M031, calendar here). S03 (Map) should follow the same steps: registry entry → _VALID_RENDERERS → generic_view branch → data endpoint branch → vendor via build.js → template with tryInit → JS init function → explorer sidebar entry → workspace.js label.
- `_detect_date_fields()` follows `_detect_status_field()` — both scan SHACL PropertyShapes with priority ranking. Map view's `_detect_geo_fields()` should follow the same pattern.
- The build.js vendor pipeline is straightforward: read from node_modules, content-hash, write to dist, add manifest entry. Leaflet for S03 will follow the same flow.

### What's fragile
- The tryInit polling pattern (setTimeout loop checking for global availability) works but adds ~100ms latency before render. If many view types pile up, consider a proper module loading system.
- The two-stage date detection (path match → datatype scan) depends on shape property paths being full IRIs. If models use prefixed paths in shapes, the well-known path matching would miss them.

### Authoritative diagnostics
- `GET /browser/views/generic/calendar/data?type=<iri>` — returns raw FullCalendar JSON, easiest way to verify the backend independently of the frontend.
- `pytest tests/test_calendar.py -v` — 24 tests cover all backend code paths.

### What assumptions changed
- Plan assumed FullCalendar v6 self-injects CSS (no separate CSS bundle needed) — confirmed correct. The vendor pipeline only processes the JS bundle.
- Plan assumed the data endpoint would need a separate route — actually reused generic_graph_data() with an elif, which is cleaner and consistent with the URL pattern.
