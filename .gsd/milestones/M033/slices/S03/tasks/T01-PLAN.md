---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Backend — date field detection, calendar query, router, and unit tests

**Slice:** S03 — Calendar View
**Milestone:** M033

## Description

Add calendar view backend support: date field detection from SHACL shapes, a SPARQL query builder for calendar events, the `generic_view()` router branch, and a JSON data endpoint. Write unit tests covering the critical `_detect_date_fields()` heuristic which must handle both `sh:datatype`-declared date fields and well-known date path IRIs (since `bpkm:Event`'s `schema:startDate`/`schema:endDate` have no `sh:datatype` in the shapes file).

Follow the kanban view pattern exactly — `_detect_status_field()` / `_build_kanban_select()` / `execute_kanban_query()` are the direct analogs.

## Steps

1. **Add `_detect_date_fields()` to `ViewSpecService`** in `backend/app/views/service.py`:
   - Get form via `self._shapes_service.get_form_for_type(type_iri)`
   - Iterate `form.properties` looking for date fields by TWO criteria:
     - `prop.datatype` in `{"http://www.w3.org/2001/XMLSchema#date", "http://www.w3.org/2001/XMLSchema#dateTime"}`
     - Well-known path IRIs: `schema:startDate`, `schema:endDate`, `bpkm:dueDate`, `bpkm:completedDate`, `bpkm:targetDate` (even when `prop.datatype is None`)
   - Collect all matching properties. Pick a start field (prefer paths containing `startDate`, then `dueDate`, then `targetDate`, then `dcterms:created`). Pick an end field (prefer paths containing `endDate`). Return `(start_field: PropertyShape, end_field: PropertyShape | None)` or `(None, None)`.

2. **Add `_build_calendar_select()` static method** to `ViewSpecService`:
   - Take `type_iri`, `start_path`, `end_path` (optional), `scope_filter` (optional)
   - Build SPARQL SELECT for `?s ?label ?startDate` and optionally `?endDate`
   - Use same pattern as `_build_kanban_select()` for scope injection

3. **Add `execute_calendar_query()` async method** to `ViewSpecService`:
   - Execute the SPARQL, map results to FullCalendar event objects: `{id, title, start, end, allDay, extendedProps: {iri}}`
   - Detect `allDay` from xsd:date (no time component) vs xsd:dateTime
   - Return `{"events": [...], "date_fields": {"start": {...}, "end": {...}}}`

4. **Wire calendar into `generic_view()` in `backend/app/views/router.py`**:
   - Add `"calendar"` to `_VALID_RENDERERS` set
   - Add `elif renderer == "calendar":` branch before the `else:  # kanban` block
   - Follow the kanban pattern: no-type → empty state, no-date-fields → empty state, else → render `calendar_view.html` with context
   - Add `/generic/calendar/data` JSON endpoint (new route function) that calls `execute_calendar_query()` and returns JSONResponse

5. **Write unit tests** in `backend/tests/test_calendar.py`:
   - Follow `test_kanban.py` test pattern exactly (same helpers, same mocking)
   - Test `_detect_date_fields()` with: Event type (schema:startDate with no datatype), Project type (schema:startDate with xsd:date datatype), Task type (bpkm:dueDate only, no end), Note type (no date props → returns None, None)
   - Test `_build_calendar_select()` output includes expected SPARQL structure
   - Test `execute_calendar_query()` maps bindings to FullCalendar event format

## Must-Haves

- [ ] `_detect_date_fields()` detects dates via BOTH `sh:datatype` check AND well-known path IRI matching
- [ ] Event type (no sh:datatype on schema:startDate) is correctly detected as having date fields
- [ ] `"calendar"` is in `_VALID_RENDERERS`
- [ ] `/browser/views/generic/calendar` route returns HTML with `calendar_view.html`
- [ ] `/browser/views/generic/calendar/data` route returns JSON with FullCalendar event format
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — all tests pass
- `rg "\"calendar\"" backend/app/views/router.py` confirms calendar in valid renderers
- `rg "_detect_date_fields" backend/app/views/service.py` confirms method exists

## Inputs

- `backend/app/views/service.py` — existing ViewSpecService with `_detect_status_field` as pattern
- `backend/app/views/router.py` — existing generic_view() with kanban branch as pattern
- `backend/tests/test_kanban.py` — test pattern with helpers and mock setup
- `backend/app/services/shapes.py` — PropertyShape dataclass (fields: path, name, datatype, in_values)

## Expected Output

- `backend/app/views/service.py` — modified with `_detect_date_fields()`, `_build_calendar_select()`, `execute_calendar_query()`
- `backend/app/views/router.py` — modified with `"calendar"` in `_VALID_RENDERERS`, calendar branch in `generic_view()`, calendar data endpoint
- `backend/tests/test_calendar.py` — new test file with date detection + query tests
