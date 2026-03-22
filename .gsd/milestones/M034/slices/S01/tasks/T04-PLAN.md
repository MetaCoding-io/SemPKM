---
estimated_steps: 4
estimated_files: 1
skills_used:
  - test
---

# T04: Unit tests for merged calendar query, PATCH endpoint, and scheduling date field detection

**Slice:** S01 — Editable Calendar & Task Time-Blocking
**Milestone:** M034

## Description

Write comprehensive unit tests for all new backend functionality in this slice. Tests go in a new file `backend/tests/test_calendar_editable.py` following the exact pattern of the existing `backend/tests/test_calendar.py` (uses `pytest`, `unittest.mock.AsyncMock`, same `_build_service()` helper pattern).

Key behaviors to test:
1. `_detect_date_fields()` now returns scheduledStart/scheduledEnd for Tasks (higher priority than dueDate)
2. `execute_merged_calendar_query()` merges Events and Tasks with sourceType annotations
3. The PATCH endpoint validates input and dispatches object.patch correctly

## Steps

1. Create `backend/tests/test_calendar_editable.py` with imports matching the existing test_calendar.py pattern:
   ```python
   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch
   from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
   from app.views.service import ViewSpecService
   ```
   Reuse the `_make_property()`, `_make_form()`, `_build_service()` helpers from test_calendar.py (copy them or import if shared).

2. Write `TestDetectDateFieldsScheduling` class:
   - `test_task_with_scheduled_start_and_due_date`: Task with both scheduledStart (xsd:dateTime) and dueDate (xsd:date) → scheduledStart wins as start field because "startdate" appears in "scheduledstart".
   - `test_task_with_scheduled_start_end`: Task with scheduledStart + scheduledEnd → both detected correctly, scheduledEnd detected as end field.
   - `test_task_without_scheduling_falls_back`: Task with only dueDate and completedDate → dueDate detected as start (existing behavior preserved).
   - `test_event_type_unaffected`: Event type with schema:startDate/endDate → still detected correctly (no regression).

3. Write `TestMergedCalendarQuery` class:
   - `test_merges_events_and_tasks`: Mock two calls to `execute_calendar_query()` — one returning Event data, one returning Task data. Verify merged list has events from both, each annotated with `sourceType` and `backgroundColor`.
   - `test_tasks_only_when_no_events`: Only Task type has date fields → merged returns only task events.
   - `test_events_only_when_no_tasks`: Only Event type has date fields → merged returns only event events.
   - `test_empty_when_no_date_types`: Neither type has date fields → returns empty events.
   - `test_scope_filter_passed_through`: Verify scope_filter is passed to each `execute_calendar_query()` call.

4. Write `TestCalendarPatch` class (testing the router endpoint):
   - Use `httpx.AsyncClient` with the FastAPI `TestClient` pattern, or mock the command dispatch directly.
   - `test_patch_valid_iri_and_dates`: POST with valid IRI + scheduledStart + scheduledEnd → 200, command dispatch called with correct properties.
   - `test_patch_missing_iri`: POST without IRI → 400.
   - `test_patch_invalid_iri`: POST with malformed IRI → 400.
   - `test_patch_preserves_event_dates`: When patching an Event (not a Task), use schema:startDate/endDate predicates.

## Must-Haves

- [ ] Tests for scheduledStart priority over dueDate in date field detection
- [ ] Tests for merged calendar query with sourceType annotations
- [ ] Tests for PATCH endpoint validation and command dispatch
- [ ] All tests pass with `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` — 0 failures
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` — both files pass (no regression)

## Inputs

- `backend/app/views/service.py` — T02's `execute_merged_calendar_query()` and existing methods
- `backend/app/views/router.py` — T02's `calendar_patch()` endpoint
- `backend/tests/test_calendar.py` — existing test patterns to follow

## Expected Output

- `backend/tests/test_calendar_editable.py` — comprehensive test file covering all new backend behavior
