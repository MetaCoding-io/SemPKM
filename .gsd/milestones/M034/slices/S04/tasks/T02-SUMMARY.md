---
id: T02
parent: S04
milestone: M034
provides:
  - ViewSpecService._expand_rrule() static method for RFC 5545 RRULE expansion via python-dateutil
  - _build_calendar_select() extended with OPTIONAL recurrenceRule + exceptionDates SPARQL clauses
  - execute_calendar_query() generates virtual calendar events with synthetic IDs and isVirtual flag
  - 24 unit tests covering RRULE expansion and virtual event generation
key_files:
  - backend/app/views/service.py
  - backend/tests/test_rrule_expansion.py
key_decisions:
  - Use naive datetimes throughout RRULE expansion to avoid dateutil rruleset.between() TypeError on mixed naive/aware comparison
  - Expansion window is ±6 months from now (183 days) with max 52 instances — wide enough for weekly recurrences
  - Virtual events skip the master event's own date to avoid duplicate rendering
patterns_established:
  - RRULE expansion tests use dynamic dates relative to now (not hardcoded past dates) to stay within the ±6 month expansion window
  - datetime.now(timezone.utc).replace(tzinfo=None) pattern for UTC-based naive datetime
observability_surfaces:
  - logger.info in execute_calendar_query reports real vs virtual event counts
  - logger.warning on malformed RRULE strings with task IRI for debugging
  - Virtual events carry extendedProps.isVirtual=true and extendedProps.masterIri for frontend inspection
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Implement backend RRULE expansion and unit tests

**Added _expand_rrule() method and virtual event generation to execute_calendar_query(), with 24 comprehensive unit tests covering FREQ=WEEKLY, EXDATE, COUNT, UNTIL, malformed input, and max instance cap**

## What Happened

Two files modified/created:

1. **`backend/app/views/service.py`** — Three changes:
   - Added `_expand_rrule()` static method that uses `dateutil.rrule.rrulestr` + `rruleset` to parse RFC 5545 RRULE strings, apply EXDATE exclusions, and return occurrences within a window. Catches all exceptions and returns empty list on malformed input.
   - Extended `_build_calendar_select()` to include `OPTIONAL { ?s <bpkm:recurrenceRule> ?recurrenceRule }` and `OPTIONAL { ?s <bpkm:exceptionDates> ?exceptionDates }` in the SPARQL query, plus adding both variables to the SELECT clause.
   - Extended `execute_calendar_query()` to detect non-empty `recurrenceRule` bindings and generate virtual events. For each RRULE occurrence that differs from the master's start date, creates a virtual event with: synthetic ID (`{iri}__recurrence__{isodate}`), `isVirtual: true`, `masterIri`, and computed start/end preserving the original duration. Logs real vs virtual counts.

2. **`backend/tests/test_rrule_expansion.py`** — 24 tests in three test classes:
   - `TestExpandRrule` (12 tests): weekly/daily/monthly recurrence, EXDATE single/multiple, COUNT, UNTIL, malformed input, empty string, max_instances cap, default cap (52), outside-window, monthly day preservation.
   - `TestBuildCalendarSelectRecurrence` (2 tests): OPTIONAL clauses present, SELECT variables include recurrence fields.
   - `TestExecuteCalendarQueryRecurrence` (10 tests): virtual event generation, synthetic ID pattern, isVirtual/masterIri props, master event retains recurrenceRule, EXDATE exclusion, non-recurring unchanged, malformed graceful degradation, all-day recurring, duration preservation, mixed recurring/plain.

Also cleaned up a redundant inline `from datetime import` in `execute_timeline_query()` since the module now imports datetime types at the top level.

## Verification

Both verification commands passed:

```
cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v  → 24 passed
cd backend && .venv/bin/python -c "from app.views.service import ViewSpecService; print('import OK')"  → import OK
cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v  → 22 passed (existing tests unbroken)
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `cd backend && .venv/bin/python -c "from app.views.service import ViewSpecService; print('import OK')"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.5s |

## Diagnostics

- Call calendar data endpoint with `?merged=true` and inspect response JSON for `extendedProps.isVirtual: true` entries
- Check server logs for `execute_calendar_query: type=... events=N (real=M virtual=V)` to verify expansion counts
- Check server logs for `_expand_rrule: failed to parse RRULE` warnings to catch malformed rules with task IRI context

## Deviations

- Used `datetime.now(timezone.utc).replace(tzinfo=None)` instead of `datetime.utcnow()` to avoid deprecation warning on Python 3.14 while keeping all rruleset operations in naive-datetime space. The plan didn't specify timezone handling — this was discovered during testing when `rruleset.between()` raised TypeError on mixed naive/aware comparison.
- Integration tests use dynamic dates relative to `datetime.now()` rather than hardcoded 2025 dates, since the ±6 month expansion window means fixed past dates fall outside the window.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/service.py` — Added `_expand_rrule()`, extended `_build_calendar_select()` with recurrence OPTIONAL clauses, extended `execute_calendar_query()` with virtual event generation
- `backend/tests/test_rrule_expansion.py` — New file with 24 unit tests for RRULE expansion and virtual event generation
- `.gsd/KNOWLEDGE.md` — Added entry about dateutil naive/aware datetime requirement
