---
id: T01
parent: S02
milestone: M033
provides:
  - Calendar renderer registered in RENDERER_REGISTRY and _VALID_RENDERERS
  - _detect_date_fields() with SHACL path + datatype detection and fallback ranking
  - _build_calendar_select() generating valid SPARQL for calendar data queries
  - execute_calendar_query() returning FullCalendar-compatible JSON events
  - Calendar branch in generic_view() and calendar data endpoint
key_files:
  - backend/app/views/registry.py
  - backend/app/views/router.py
  - backend/app/views/service.py
key_decisions:
  - Date detection uses two-stage approach — exact well-known path match first, then datatype+fallback ranking — because Event shape has no sh:datatype on startDate/endDate
  - Calendar data endpoint reuses the existing generic_graph_data route handler with an elif branch rather than a separate endpoint
patterns_established:
  - _detect_date_fields() follows the same pattern as _detect_status_field() — scans SHACL PropertyShapes with priority ranking
observability_surfaces:
  - execute_calendar_query INFO logs with type, paths, scope, and event count
  - _detect_date_fields WARNING logs on shapes lookup failure
  - GET /browser/views/generic/calendar/data?type=<iri> JSON endpoint for debugging
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Backend — register calendar renderer, date detection, data endpoint

**Registered calendar renderer with SHACL-driven date detection, SPARQL query builder, and FullCalendar-compatible JSON data endpoint**

## What Happened

Added the calendar renderer to the existing view system following the kanban pattern (D291). Three files modified:

1. **registry.py** — Added `"calendar"` entry to `RENDERER_REGISTRY` with template `browser/calendar_view.html`.

2. **service.py** — Added three methods to `ViewSpecService`:
   - `_detect_date_fields(type_iri)` — Two-stage date property detection from SHACL shapes. Stage 1: exact match on well-known paths (`schema:startDate`, `schema:endDate`). Stage 2: collect `xsd:date`/`xsd:dateTime`-typed properties and rank by path name fragments (`dueDate` > `targetDate` > `created` for start; `completedDate` > `modified` for end). Returns `(start_prop, end_prop)` tuple.
   - `_build_calendar_select()` — Static method generating SPARQL SELECT for `?s ?label ?startDate ?endDate ?type` with optional type filter, scope sub-select, and end-date OPTIONAL clause.
   - `execute_calendar_query()` — Runs the query via `scope_to_current_graph()`, transforms bindings to FullCalendar JSON format `{id, title, start, end, extendedProps: {iri, type}}`, deduplicates by IRI, skips entries without start dates, falls back to IRI local name when label is missing.

3. **router.py** — Added `"calendar"` to `_VALID_RENDERERS`. Added `elif renderer == "calendar"` branch in `generic_view()` that detects date fields, builds data URL, and renders the template. Extended `generic_graph_data()` to handle `renderer == "calendar"` — detects date fields for the type, calls `execute_calendar_query()`, returns JSON array.

## Verification

- Registry check: `assert 'calendar' in RENDERER_REGISTRY` — passed
- Valid renderers check: `assert 'calendar' in _VALID_RENDERERS` — passed
- Import check: all three methods present on `ViewSpecService` — passed
- Date detection unit tests (5 scenarios): Event shape (path match), Task shape (datatype match), Note shape (created/modified fallback), Tag shape (no date props → None,None), missing shape (None,None) — all passed
- Query builder: verified 4 SPARQL variants (type+both dates, type+start only, no type auto-detect, with scope filter) produce valid SPARQL
- execute_calendar_query mock test: deduplication, label fallback, end-date omission, no-start-date skip — all correct
- Syntax check: all 3 files parse without errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "from app.views.registry import RENDERER_REGISTRY; assert 'calendar' in RENDERER_REGISTRY"` | 0 | ✅ pass | <1s |
| 2 | `python -c "from app.views.service import ViewSpecService; assert hasattr(ViewSpecService, '_detect_date_fields')"` | 0 | ✅ pass | <1s |
| 3 | `python -c "from app.views.router import _VALID_RENDERERS; assert 'calendar' in _VALID_RENDERERS"` | 0 | ✅ pass | <1s |
| 4 | Date detection mock test (5 scenarios) | 0 | ✅ pass | <1s |
| 5 | Query builder test (4 variants) | 0 | ✅ pass | <1s |
| 6 | execute_calendar_query mock test (dedup, fallback, skip) | 0 | ✅ pass | <1s |
| 7 | `python -c "import ast; ast.parse(open(f).read())"` on all 3 files | 0 | ✅ pass | <1s |

### Slice-Level Verification (partial — T01 is first task)

| Check | Status | Notes |
|-------|--------|-------|
| `pytest tests/test_calendar.py` | ⏳ pending | T03 creates the test file |
| Calendar view renders in browser | ⏳ pending | T02 creates the template |
| FullCalendar JS loads from vendored bundle | ⏳ pending | T02 vendors FullCalendar |
| Click event → object tab opens | ⏳ pending | T02 |
| Type filter pills switch displayed objects | ⏳ pending | T02 |
| Month/week/day view buttons work | ⏳ pending | T02 |
| Dark mode renders correctly | ⏳ pending | T02 |
| Failure path returns empty JSON array | ✅ ready | Backend returns `[]` on empty/error |

## Diagnostics

- **Log grep:** `grep "execute_calendar_query" /app/logs/*.log` shows query execution with type, paths, scope, and event count
- **Data endpoint:** `curl /browser/views/generic/calendar/data?type=<iri>` returns JSON array of FullCalendar events
- **Empty result:** When no date properties found, `_detect_date_fields()` returns `(None, None)` and the fallback query uses common date predicates via FILTER

## Deviations

- The data endpoint reuses `generic_graph_data()` with an `elif` branch instead of a separate function — keeps the URL pattern consistent (`/browser/views/generic/{renderer}/data`) and follows the existing structure.
- Added `_datePred` variable with FILTER for the no-type fallback query instead of a UNION clause — simpler and equivalent for the common case.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/registry.py` — Added `"calendar"` entry to `RENDERER_REGISTRY`
- `backend/app/views/router.py` — Added `"calendar"` to `_VALID_RENDERERS`, calendar branch in `generic_view()`, calendar handling in `generic_graph_data()`
- `backend/app/views/service.py` — Added `_detect_date_fields()`, `_build_calendar_select()`, `execute_calendar_query()` methods to `ViewSpecService`
- `.gsd/milestones/M033/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M033/slices/S02/S02-PLAN.md` — Added failure-path verification check (pre-flight fix)
