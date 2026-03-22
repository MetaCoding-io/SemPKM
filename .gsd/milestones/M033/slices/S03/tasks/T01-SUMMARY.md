---
id: T01
parent: S03
milestone: M033
provides:
  - _detect_date_fields() on ViewSpecService — dual heuristic (sh:datatype + well-known path IRI)
  - _build_calendar_select() SPARQL builder with optional end date and scope filter
  - execute_calendar_query() returning FullCalendar-compatible event objects
  - "calendar" in _VALID_RENDERERS with full generic_view() branch
  - /browser/views/generic/calendar/data JSON endpoint
  - calendar_view.html skeleton template (T02 builds the full frontend)
  - 22 unit tests covering date detection, query building, and event mapping
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_calendar.py
  - backend/app/templates/browser/calendar_view.html
key_decisions:
  - Date detection uses dual heuristic — sh:datatype check plus well-known path local-name matching — because bpkm:Event's schema:startDate/endDate have no sh:datatype declared in the SHACL shapes
  - Calendar data endpoint reuses the existing /generic/{renderer}/data route (now handles both "graph" and "calendar") rather than creating a separate route
patterns_established:
  - Calendar view follows the same service/router/template pattern as kanban: _detect → _build_select → execute_query → generic_view branch → data endpoint
observability_surfaces:
  - _detect_date_fields logs detected start/end paths at DEBUG
  - execute_calendar_query logs event count at INFO
  - generic_view calendar branch logs type/scope/start/end at INFO
  - SPARQL failures logged at WARNING with exc_info, return empty events (not 500)
  - /browser/views/generic/calendar/data returns inspectable JSON
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Backend — date field detection, calendar query, router, and unit tests

**Added calendar view backend: date detection from SHACL shapes (dual heuristic), SPARQL query builder, router branch, JSON data endpoint, and 22 unit tests**

## What Happened

Implemented the full backend pipeline for the calendar view renderer:

1. **`_detect_date_fields()`** on ViewSpecService uses two criteria to find date properties: (a) `prop.datatype` matching `xsd:date` or `xsd:dateTime`, and (b) well-known path IRIs matched by local name (`startDate`, `endDate`, `dueDate`, `completedDate`, `targetDate`). This dual approach is necessary because bpkm:Event's `schema:startDate`/`schema:endDate` have no `sh:datatype` in the shapes file. Start field selection follows a priority order: startDate > dueDate > targetDate > created > first match.

2. **`_build_calendar_select()`** builds SPARQL SELECT for `?s ?label ?startDate` and optionally `?endDate`, with scope filter injection matching the kanban pattern.

3. **`execute_calendar_query()`** maps SPARQL bindings to FullCalendar event objects with `allDay` detection (date vs dateTime based on presence of 'T' separator), deduplication, and empty-start filtering.

4. **Router changes:** Added `"calendar"` to `_VALID_RENDERERS`, added `elif renderer == "calendar":` branch in `generic_view()` with three states (no type, no date fields, normal), and extended the `/generic/{renderer}/data` endpoint to handle calendar data requests.

5. **Template:** Created a minimal `calendar_view.html` skeleton with error states, type filter pills, and a calendar container — T02 will add the full FullCalendar frontend.

6. **Unit tests:** 22 tests covering all date detection scenarios (Event no-datatype, Project with-datatype, Task dueDate-only, Note no-dates, priority ordering, fallbacks, error paths), query building (start-only, start+end, scope filter), and event mapping (allDay detection, deduplication, empty start, label fallback, query failure).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — 22/22 passed
- `rg "\"calendar\"" backend/app/views/router.py` — confirmed calendar in `_VALID_RENDERERS` and all router branches
- `rg "_detect_date_fields" backend/app/views/service.py` — confirmed method exists with implementation
- Python import check on both `service.py` and `router.py` — no import errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.46s |
| 2 | `rg "\"calendar\"" backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 3 | `rg "_detect_date_fields" backend/app/views/service.py` | 0 | ✅ pass | <1s |
| 4 | `python -c "from app.views.service import ViewSpecService"` | 0 | ✅ pass | <1s |
| 5 | `python -c "from app.views.router import router"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Date detection:** `_detect_date_fields` emits DEBUG log `type=<iri> start=<path> end=<path|None>` — grep for `_detect_date_fields` in application logs.
- **Event count:** `execute_calendar_query` emits INFO log `type=<iri> events=<N>` — visible in application logs per request.
- **Data endpoint:** `curl /browser/views/generic/calendar/data?type=<encoded_iri>` returns JSON with `events` array and `date_fields` metadata. Empty response = no date fields or no type.
- **Failure path:** SPARQL errors return `{"events": [], "date_fields": {...}}` (not 500). Failure logged at WARNING.

## Deviations

- Extended the existing `/generic/{renderer}/data` route to handle both `graph` and `calendar` renderers, rather than creating a separate `/generic/calendar/data` route. The route function was renamed from `generic_graph_data` to `generic_view_data` to reflect this.

## Known Issues

- None

## Files Created/Modified

- `backend/app/views/service.py` — Added `_detect_date_fields()`, `_build_calendar_select()`, `execute_calendar_query()` methods to ViewSpecService
- `backend/app/views/router.py` — Added `"calendar"` to `_VALID_RENDERERS`, calendar branch in `generic_view()`, calendar handling in data endpoint
- `backend/tests/test_calendar.py` — New test file with 22 unit tests for date detection, query building, and event mapping
- `backend/app/templates/browser/calendar_view.html` — New minimal template with error states and calendar container (T02 builds full frontend)
- `.gsd/milestones/M033/slices/S03/S03-PLAN.md` — Added Observability/Diagnostics section and failure-path verification check
- `.gsd/milestones/M033/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
