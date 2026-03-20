---
id: T01
parent: S03
milestone: M021
provides:
  - build_event_patch() real implementation mapping bpkm responseStatus → iCalendar PARTSTAT
  - modify_vevent_partstat() function for in-place .ics ATTENDEE PARTSTAT modification
key_files:
  - apps/caldav-calendar/services/field_mapper.py
  - backend/tests/test_caldav_field_mapper.py
key_decisions:
  - modify_vevent_partstat returns original ics_text unchanged (not re-serialized) when no matching attendee found — avoids reformatting noise
patterns_established:
  - Direct manipulation of component['ATTENDEE'] (single vs list) rather than normalizing then writing back — preserves icalendar's internal format
observability_surfaces:
  - Pure functions — no runtime logging. Diagnostic via return values: build_event_patch returns {} on all non-actionable inputs; modify_vevent_partstat returns original text unchanged when no match found.
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Implement reverse field mapper and iCalendar PARTSTAT modifier

**Replaced build_event_patch() stub with real RSVP mapper and added modify_vevent_partstat() for .ics ATTENDEE PARTSTAT rewriting**

## What Happened

Replaced the `build_event_patch()` stub in field_mapper.py with a real implementation that extracts `bpkm:responseStatus` from event properties, maps it via `REVERSE_RESPONSE_STATUS_MAP` to an iCalendar PARTSTAT value, and returns a patch dict. Guard rails: returns `{}` for missing user_email, missing responseStatus, or unmapped values.

Added `modify_vevent_partstat(ics_text, user_email, new_partstat)` — parses a VCALENDAR string, walks to the VEVENT, finds the matching ATTENDEE by case-insensitive email comparison on the `mailto:` URI, updates its PARTSTAT parameter in-place, and regenerates the VCALENDAR. Handles both single-ATTENDEE and multi-ATTENDEE cases by working directly with `component['ATTENDEE']` rather than normalizing and writing back. Returns original text unchanged when no match is found.

Added `import icalendar` to field_mapper.py (was not previously needed since all prior functions operated on pre-parsed components).

Replaced the 2 stub tests in `TestBuildEventPatch` with 8 real tests covering all 4 mapped statuses plus empty/unmapped/no-email edge cases. Added `TestModifyVeventPartstat` with 7 tests covering single attendee, multi-attendee targeting, email-not-found, case-insensitive matching, round-trip consistency with `extract_attendees`, no-attendees, and parameter preservation (CN, ROLE, RSVP).

Removed all "stub" and "S03" references from field_mapper.py.

## Verification

- `pytest tests/test_caldav_field_mapper.py -v -x` — 98 tests pass (85 existing + 15 new - 2 removed stubs)
- `pytest tests/test_caldav_field_mapper.py -v -k "BuildEventPatch or ModifyVevent"` — 15 selected, all pass
- `rg "stub|S03|not yet implemented" apps/caldav-calendar/services/field_mapper.py` — zero matches
- `pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` — 129 pass (no regressions)
- `pytest tests/test_caldav_*.py --co -q` — 209 tests collected

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_caldav_field_mapper.py -v -x` | 0 | ✅ pass | 0.17s |
| 2 | `pytest tests/test_caldav_field_mapper.py -v -k "BuildEventPatch or ModifyVevent"` | 0 | ✅ pass | 0.07s |
| 3 | `rg "stub\|S03\|not yet implemented" field_mapper.py` | 1 (no matches) | ✅ pass | <0.01s |
| 4 | `pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` | 0 | ✅ pass | 0.16s |
| 5 | `pytest tests/test_caldav_*.py --co -q` | 0 | ✅ pass (209 collected) | 0.11s |

## Diagnostics

Both functions are pure with no side effects. To inspect:
- `build_event_patch({"urn:sempkm:model:basic-pkm:responseStatus": "accepted"}, "user@test.com")` → `{"responseStatus": "ACCEPTED"}`
- `modify_vevent_partstat(ics_text, "user@test.com", "ACCEPTED")` → modified .ics string or unchanged original
- String equality check on `modify_vevent_partstat` return vs input detects whether a modification occurred

## Deviations

- Added `test_returns_empty_for_empty_user_email` (empty string edge case) beyond the 7 tests specified in the plan — 8 total in TestBuildEventPatch instead of 7.

## Known Issues

None.

## Files Created/Modified

- `apps/caldav-calendar/services/field_mapper.py` — Replaced `build_event_patch()` stub with real RSVP mapper, added `modify_vevent_partstat()`, added `import icalendar`, removed all stub/S03 comments
- `backend/tests/test_caldav_field_mapper.py` — Replaced 2 stub tests with 8 real `TestBuildEventPatch` tests, added `TestModifyVeventPartstat` with 7 tests, added `modify_vevent_partstat` import
