---
estimated_steps: 5
estimated_files: 2
skills_used:
  - test
---

# T02: Implement backend RRULE expansion and unit tests

**Slice:** S04 — Recurring Tasks & RRULE Expansion
**Milestone:** M034

## Description

Add `_expand_rrule()` to `ViewSpecService` for expanding RFC 5545 RRULE strings into occurrence datetimes using `python-dateutil`. Extend the calendar SPARQL query to fetch `recurrenceRule` and `exceptionDates`, and extend `execute_calendar_query()` to generate virtual calendar events from recurring tasks. Write comprehensive unit tests.

The key integration point: `execute_calendar_query()` already maps SPARQL bindings to FullCalendar events. For bindings that include a non-empty `recurrenceRule`, we generate additional virtual events — one per RRULE occurrence within the expansion window. Virtual events share the original's title and color but get:
- Synthetic ID: `{original_iri}__recurrence__{iso_date}` (FullCalendar needs unique IDs)
- `extendedProps.isVirtual: true`
- `extendedProps.masterIri: original_iri`
- Computed `start`/`end` from the occurrence datetime + original duration

## Steps

1. **Add `_expand_rrule()` static method to `ViewSpecService`** in `backend/app/views/service.py`:
   ```python
   @staticmethod
   def _expand_rrule(
       rrule_str: str,
       dtstart: datetime,
       range_start: datetime,
       range_end: datetime,
       exdates: list[date] | None = None,
       max_instances: int = 52,
   ) -> list[datetime]:
   ```
   - Parse `rrule_str` with `dateutil.rrule.rrulestr(rrule_str, dtstart=dtstart)`
   - Create `rruleset`, add parsed rule, add each exdate
   - Call `set.between(range_start, range_end, inc=True)[:max_instances]`
   - Wrap all parsing in try/except — return empty list on malformed input, log warning
   - Import: `from dateutil.rrule import rrulestr, rruleset` and `from datetime import datetime, date, timedelta, timezone`

2. **Extend `_build_calendar_select()`** — Add two OPTIONAL clauses to the SPARQL query:
   ```sparql
   OPTIONAL { ?s <urn:sempkm:model:basic-pkm:recurrenceRule> ?recurrenceRule }
   OPTIONAL { ?s <urn:sempkm:model:basic-pkm:exceptionDates> ?exceptionDates }
   ```
   Add `?recurrenceRule ?exceptionDates` to the SELECT variables. These are hardcoded to the `bpkm:` namespace — only bpkm models have recurrence support.

3. **Extend `execute_calendar_query()`** — After building the base event from bindings, check for `recurrenceRule`:
   - If binding has non-empty `recurrenceRule` value:
     - Parse `start_val` into a datetime for `dtstart`
     - Parse `exceptionDates` (comma-separated ISO dates) into `list[date]`
     - Compute expansion window: `now - 6 months` to `now + 6 months`
     - Call `_expand_rrule()` to get occurrence datetimes
     - Compute original duration from start/end (default 1 hour if no end)
     - For each occurrence that isn't the master event's own date, create a virtual event dict with synthetic ID, `isVirtual: true`, `masterIri`, and computed start/end
     - Add `recurrenceRule` to the master event's extendedProps for frontend indicator
   - Log count of virtual events generated

4. **Also extend `execute_merged_calendar_query()`** — The merged path calls `execute_calendar_query()` per type, so virtual events flow through automatically. No code change needed here, but verify the `sourceType` and color annotations propagate to virtual events.

5. **Write `backend/tests/test_rrule_expansion.py`** — Test cases:
   - `_expand_rrule` with `FREQ=WEEKLY;BYDAY=FR` → returns Fridays
   - `_expand_rrule` with EXDATE → excluded date absent
   - `_expand_rrule` with `COUNT=5` → exactly 5 results
   - `_expand_rrule` with `UNTIL=<date>` → no results past that date
   - `_expand_rrule` with malformed string → empty list, no exception
   - `_expand_rrule` with max_instances=3 → at most 3 results
   - `execute_calendar_query` with recurrenceRule in bindings → virtual events produced
   - Virtual events have correct synthetic ID pattern (`__recurrence__`)
   - Virtual events have `isVirtual: true` and `masterIri` in extendedProps
   - Master event retains `recurrenceRule` in extendedProps
   
   Follow the pattern in `backend/tests/test_calendar.py` — use `_build_service()` helper with mocked triplestore client.

## Must-Haves

- [ ] `_expand_rrule()` handles FREQ=WEEKLY, EXDATE, COUNT, UNTIL, malformed input
- [ ] `_build_calendar_select()` fetches recurrenceRule and exceptionDates via OPTIONAL
- [ ] `execute_calendar_query()` generates virtual events with synthetic IDs and isVirtual flag
- [ ] Malformed RRULE gracefully returns empty list (no exception propagation)
- [ ] Max instances cap respected (default 52)
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` — all pass
- `cd backend && .venv/bin/python -c "from app.views.service import ViewSpecService; print('import OK')"` — no import errors

## Observability Impact

- Signals added/changed: `logger.info` in `execute_calendar_query` reports virtual event count alongside real event count; `logger.warning` on malformed RRULE strings
- How a future agent inspects this: Call calendar data endpoint, check `extendedProps.isVirtual` in response JSON
- Failure state exposed: Malformed RRULE logged with task IRI for debugging

## Inputs

- `backend/app/views/service.py` — existing `_build_calendar_select()`, `execute_calendar_query()`, `execute_merged_calendar_query()`
- `backend/tests/test_calendar.py` — existing test patterns and helpers (`_build_service`, `_make_property`, `_make_form`)
- `models/basic-pkm/shapes/basic-pkm.jsonld` — T01's recurrenceRule/exceptionDates properties (for knowing the property IRIs)

## Expected Output

- `backend/app/views/service.py` — `_expand_rrule()` method, extended calendar SPARQL and event mapping
- `backend/tests/test_rrule_expansion.py` — comprehensive unit test file (10+ test cases)
