---
id: T01
parent: S03
milestone: M018
provides:
  - Pure field mapping module for Google Calendar events → bpkm:Event properties
  - 64 exhaustive tests covering all transforms, normalizations, and edge cases
key_files:
  - apps/google-calendar/services/field_mapper.py
  - backend/tests/test_gcal_field_mapper.py
key_decisions:
  - "externalProvider hardcoded to 'google-calendar' per S01 forward intelligence"
  - "visibility='default' excluded from VISIBILITY_MAP (property omitted per spec)"
  - "extract_body() returns stripped HTML as separate helper — body is set via body.set in sync engine, not as a property"
patterns_established:
  - "Same importlib loading pattern as github-sync and linear-sync field mapper tests"
  - "Same BPKM full-IRI constant pattern and None-stripping dict comprehension"
observability_surfaces:
  - none (pure functions — runtime observability comes from sync engine in T02)
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Build field mapper with all property transforms and exhaustive tests

**Built pure field mapper for Google Calendar events with 8 public functions, 4 normalization maps, and 64 passing tests covering every property transform and edge case.**

## What Happened

Created `apps/google-calendar/services/field_mapper.py` following the exact pattern from linear-sync and github-sync field mappers. The module has:

- 4 normalization constants: `STATUS_MAP`, `RESPONSE_STATUS_MAP`, `VISIBILITY_MAP`, `TRANSPARENCY_MAP` — all matching INTEGRATION-DOMAIN-MAPPING.md §5 exactly.
- 8 pure functions: `compute_event_slug`, `detect_all_day`, `extract_conference_url`, `extract_response_status`, `extract_rrule`, `strip_html_tags`, `extract_body`, `build_event_properties`.
- `build_event_properties` handles all 20+ fields from the spec: title, start/end dates, allDay detection, timeZone, eventStatus, location, visibility (with "default" omission), showAs (from transparency), conferenceUrl, recurrenceRule, recurringEventId, responseStatus, reminderMinutes, calendarName, externalId/Url/Provider, lastSyncedAt, created/modified.

Key constraints verified: `externalProvider` is exactly `"google-calendar"`, `allDay` produces `"true"`/`"false"` strings (xsd:boolean serialization), `visibility="default"` omits the property, `transparency` maps to `bpkm:showAs` (not `bpkm:transparency`), None values are excluded from output.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` — 64 passed (≥40 required)
- `cd backend && .venv/bin/python -m pytest -x` — 1562 passed, 0 failures (full suite, zero regressions)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` | 0 | ✅ pass | 0.09s |
| 2 | `cd backend && .venv/bin/python -m pytest -x` | 0 | ✅ pass | 8.12s |

## Diagnostics

Pure functions — no runtime diagnostics. Import the module and call any function with a sample dict to test transforms interactively. Test failures in `test_gcal_field_mapper.py` pinpoint which transform or normalization broke.

## Deviations

None. Implementation matches the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/services/field_mapper.py` — Pure field mapping module (165 lines): constants, helpers, property builder
- `backend/tests/test_gcal_field_mapper.py` — 64 tests across 10 test classes covering every function and edge case
- `.gsd/milestones/M018/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
