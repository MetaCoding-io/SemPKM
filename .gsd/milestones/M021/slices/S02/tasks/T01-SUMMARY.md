---
id: T01
parent: S02
milestone: M021
provides:
  - CalDAV iCalendar field mapper with all ~20 VEVENT property extractions
  - Exhaustive unit tests (85 tests) validating icalendar library type handling
key_files:
  - apps/caldav-calendar/services/field_mapper.py
  - backend/tests/test_caldav_field_mapper.py
key_decisions:
  - Used importlib-based module loading in tests (matching existing test_caldav_client.py pattern) because the apps directory uses hyphenated names that aren't importable with regular Python imports
patterns_established:
  - icalendar BYDAY must be a list of individual weekday strings, not a comma-separated string (library validates each value individually)
  - _normalize_to_list() pattern for handling icalendar's single-value-vs-list return behavior (ATTENDEE, CATEGORIES)
observability_surfaces:
  - Test suite: `pytest tests/test_caldav_field_mapper.py -v` — 85 tests covering all extraction functions
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build iCalendar field mapper with exhaustive unit tests

**Built pure-function CalDAV field mapper (field_mapper.py) with 17 extraction functions and 85 passing unit tests covering all VEVENT property transforms including icalendar library type edge cases.**

## What Happened

Installed `icalendar` 7.0.3 in the backend venv via uv. Explored the icalendar library's actual return types by building real Event components — confirmed the documented pitfalls around single-vs-list ATTENDEE, date-vs-datetime DTSTART, vRecur.to_ical() output, and negative VALARM timedeltas.

Built `field_mapper.py` with:
- 5 enum maps (STATUS_MAP, CLASS_MAP, TRANSP_MAP, PARTSTAT_MAP, REVERSE_RESPONSE_STATUS_MAP)
- `compute_event_slug()` — deterministic caldav-prefixed SHA-256 slug
- 13 individual extraction functions covering all iCalendar properties from the domain mapping spec
- `_normalize_to_list()` utility for single/list/None normalization
- `build_event_properties()` orchestrator assembling the full bpkm property dict
- `build_event_patch()` stub (empty dict for S03)

Built test file with 85 tests across 17 test classes, organized by extraction function. All tests use real icalendar.Event components via `.add()` — no mocking of library internals.

One test data fix needed: icalendar's vRecur BYDAY parameter requires a list of individual weekday strings (`["MO", "WE", "FR"]`), not a comma-separated string (`"MO,WE,FR"`). The library validates each value as a weekday abbreviation.

## Verification

- `backend/.venv/bin/python -m pytest tests/test_caldav_field_mapper.py -v` → 85 passed
- `backend/.venv/bin/python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` → 62 passed (zero regressions)
- `backend/.venv/bin/python -c "from icalendar import Calendar; print('icalendar available')"` → prints ok

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_caldav_field_mapper.py -v` | 0 | ✅ pass (85 tests) | 0.14s |
| 2 | `pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` | 0 | ✅ pass (62 tests) | 0.09s |
| 3 | `python -c "from icalendar import Calendar; print('icalendar available')"` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 of 2):
- ✅ Field mapper tests pass (85 tests, >60 required)
- ✅ S01 tests pass (62/62, zero regressions)
- ✅ Field mapper covers all ~20 iCalendar properties with edge cases
- ⏳ Sync engine tests (T02)
- ⏳ Person matcher tests (T02)
- ⏳ Sync-token extraction test (T02)

## Diagnostics

Pure-function module — no runtime state, logging, or network calls. Diagnose by running tests:
- `pytest tests/test_caldav_field_mapper.py -v` — verifies all extraction functions
- `pytest tests/test_caldav_field_mapper.py -k "build_event"` — focuses on the orchestrator integration tests

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/caldav-calendar/services/field_mapper.py` — New pure-function field mapper module (~310 lines) with 17 extraction functions, 5 enum maps, and build_event_properties orchestrator
- `backend/tests/test_caldav_field_mapper.py` — New test file (~690 lines) with 85 unit tests across 17 test classes
- `.gsd/milestones/M021/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section
