---
id: T03
parent: S02
milestone: M033
provides:
  - 24 unit tests covering date detection, calendar query building, and FullCalendar event transformation
key_files:
  - backend/tests/test_calendar.py
key_decisions: []
patterns_established:
  - Calendar test helpers extend kanban helpers with datatype parameter for PropertyShape
observability_surfaces:
  - "none — test-only task, no runtime signals"
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Unit tests for date detection and calendar query builder

**Created 24 unit tests covering _detect_date_fields(), _build_calendar_select(), and execute_calendar_query() — all passing**

## What Happened

Created `backend/tests/test_calendar.py` following the `test_kanban.py` structure with adapted helpers (added `datatype` parameter to `_make_property()`). Three test classes cover all required scenarios:

- **TestDetectDateFields** (11 tests): Well-known path matching for both https and http schema.org variants, datatype-based detection (xsd:date, xsd:dateTime), fallback ranking (dueDate→start, completedDate→end), priority ordering (schema:startDate preferred over dcterms:created), no-date type → (None, None), shapes service None → (None, None), shapes exception → (None, None), form returns None → (None, None).

- **TestBuildCalendarSelect** (6 tests): Basic query with type + start/end paths, scope filter injection as sub-select, start-only (no end path), no-start-path fallback (FILTER-based common date predicates), no type filter, no scope filter.

- **TestExecuteCalendarQuery** (7 tests): FullCalendar JSON format with id/title/start/end/extendedProps, empty bindings → empty list, deduplication by IRI, events without startDate skipped, label fallback to local name from IRI, SPARQL failure → empty list, no type filter works.

## Verification

All 24 tests pass:

```
cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v
# 24 passed in 0.45s
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.45s |
| 2 | `cd frontend && npm ci` | 0 | ✅ pass | 2s |

The `npm ci` verification failure in the gate was caused by running `npm ci` from the project root (no package.json there) instead of from the `frontend/` directory. Running `cd frontend && npm ci` succeeds. This is a gate configuration issue, not a code problem.

## Diagnostics

Test-only task — no runtime signals. Run tests with: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v`

## Deviations

- Added 24 tests instead of the minimum 12 — additional edge cases for http vs https schema.org paths, form-returns-None, and no-start-path fallback behavior.
- Fixed test assertion: `dcterms/created` → `dc/terms/created` to match the actual purl.org IRI structure.

## Known Issues

- The verification gate runs `npm ci` from the project root instead of `frontend/`. This affects all tasks in slices that reference `npm ci`. The correct command is `cd frontend && npm ci`.

## Files Created/Modified

- `backend/tests/test_calendar.py` — 24 unit tests for calendar backend (date detection, query building, event transformation)
