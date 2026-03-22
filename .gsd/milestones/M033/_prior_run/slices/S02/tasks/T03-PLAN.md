---
estimated_steps: 3
estimated_files: 1
skills_used:
  - test
---

# T03: Unit tests for date detection and calendar query builder

**Slice:** S02 — Calendar View Renderer
**Milestone:** M033

## Description

Create comprehensive unit tests for `_detect_date_fields()`, `_build_calendar_select()`, and `execute_calendar_query()` on ViewSpecService. Follows the `test_kanban.py` structure (same helper functions, same mocking approach). Tests validate that date detection works across all SHACL shape configurations and that the calendar query builder produces correct SPARQL and FullCalendar JSON output.

## Steps

1. **Create `test_calendar.py`** following `test_kanban.py` structure:
   - Import `PropertyShape`, `NodeShapeForm`, `ShapesService`, `ViewSpecService`
   - Reuse the same helper pattern: `_make_property()`, `_make_form()`, `_build_service()` with mocked dependencies
   - Add `datatype` parameter to `_make_property()` helper (kanban's doesn't use it, but calendar needs it)

2. **Test `_detect_date_fields()`** — at least 7 tests:
   - Event shape with `schema:startDate` + `schema:endDate` (no explicit datatype) → detected by path name
   - Task shape with `bpkm:dueDate` (xsd:date datatype) → detected as start, no end
   - Type with `dcterms:created` (xsd:dateTime) → detected as fallback start
   - Type with explicit `xsd:date` datatype on custom property → detected
   - Type with no date-like properties → returns `(None, None)`
   - Shapes service returns None → returns `(None, None)`
   - Shapes service raises exception → returns `(None, None)` with logged warning
   - Priority ordering: `schema:startDate` preferred over `dcterms:created` when both exist

3. **Test `_build_calendar_select()` and `execute_calendar_query()`** — at least 5 tests:
   - Basic query structure with type + start/end paths
   - Query with scope filter injected
   - Query with start path only (no end path)
   - `execute_calendar_query()` with mock bindings → correct FullCalendar JSON format
   - `execute_calendar_query()` with empty bindings → empty list
   - `execute_calendar_query()` deduplicates by IRI

## Must-Haves

- [ ] ≥12 unit tests covering date detection, query building, and result transformation
- [ ] Tests pass: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v`
- [ ] Date detection tests cover: path-based matching, datatype-based matching, priority ordering, fallback to dcterms:created, no-date type, shapes service unavailable
- [ ] Query builder tests cover: basic query, scope filter, start-only (no end), result format
- [ ] Tests follow `test_kanban.py` conventions: mocked dependencies, no real triplestore needed

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v --tb=short 2>&1 | tail -5` — shows ≥12 passed

## Inputs

- `backend/app/views/service.py` — the calendar methods added in T01 (_detect_date_fields, _build_calendar_select, execute_calendar_query)
- `backend/tests/test_kanban.py` — reference pattern for test structure, helper functions, and mocking approach
- `backend/app/services/shapes.py` — PropertyShape and NodeShapeForm dataclasses (need `datatype` field)

## Expected Output

- `backend/tests/test_calendar.py` — comprehensive unit tests for calendar backend
