---
estimated_steps: 5
estimated_files: 2
---

# T01: Implement reverse field mapper and iCalendar PARTSTAT modifier

**Slice:** S03 — Push Sync + Bidirectional Write
**Milestone:** M021

## Description

Replace the `build_event_patch()` stub in field_mapper.py with a real implementation that extracts pushable RSVP changes from bpkm event properties, and add a new `modify_vevent_partstat()` function that parses a .ics string, modifies the correct ATTENDEE's PARTSTAT parameter, and regenerates a valid VCALENDAR. These are pure functions with no I/O — push_sync (T02) depends on both.

The `REVERSE_RESPONSE_STATUS_MAP` is already defined at line 55 of field_mapper.py — it maps bpkm response statuses back to iCalendar PARTSTAT values (needs-action→NEEDS-ACTION, accepted→ACCEPTED, declined→DECLINED, tentative→TENTATIVE).

## Steps

1. **Replace `build_event_patch()` stub** (line 432 of `apps/caldav-calendar/services/field_mapper.py`):
   - Extract `bpkm:responseStatus` from `event_props` dict (keys are full IRI strings like `urn:sempkm:model:basic-pkm:responseStatus`)
   - Look up in `REVERSE_RESPONSE_STATUS_MAP` — if not found or no responseStatus, return `{}`
   - Return `{"responseStatus": partstat_value}` where partstat_value is the iCalendar PARTSTAT string (e.g. "ACCEPTED")
   - Require `user_email` to be non-empty — return `{}` if None or empty
   - Remove the "stub" / "S03" comments from the docstring

2. **Add `modify_vevent_partstat(ics_text, user_email, new_partstat)` function** after `build_event_patch()`:
   - Parse `ics_text` with `icalendar.Calendar.from_ical(ics_text)`
   - Walk subcomponents to find the VEVENT
   - Get ATTENDEE list using `_normalize_to_list(component.get('ATTENDEE'))` — this handles single vCalAddress vs list
   - For each attendee, extract email from the `mailto:` URI (case-insensitive comparison on the email portion only — strip `mailto:` prefix, compare `.lower()`)
   - When matching attendee found, update its PARTSTAT param: `attendee.params['PARTSTAT'] = icalendar.vText(new_partstat)`
   - Regenerate the full VCALENDAR: `cal.to_ical().decode('utf-8')`
   - If no matching attendee found, return the original ics_text unchanged
   - **Important:** When writing back, if the original had a single ATTENDEE (not a list), preserve that format. Use `_normalize_to_list()` only for reading. When modifying, work directly with `component['ATTENDEE']` — if it's a single vCalAddress, modify it directly; if it's a list, modify the matching item in-place.

3. **Replace the 2 stub tests in `TestBuildEventPatch`** (line 762 of `backend/tests/test_caldav_field_mapper.py`):
   - `test_returns_empty_for_no_response_status` — empty props → `{}`
   - `test_returns_empty_for_unmapped_status` — `responseStatus: "unknown-value"` → `{}`
   - `test_returns_empty_for_no_user_email` — valid status but `user_email=None` → `{}`
   - `test_returns_accepted` — `responseStatus: "accepted"` → `{"responseStatus": "ACCEPTED"}`
   - `test_returns_declined` — `responseStatus: "declined"` → `{"responseStatus": "DECLINED"}`
   - `test_returns_tentative` — `responseStatus: "tentative"` → `{"responseStatus": "TENTATIVE"}`
   - `test_returns_needs_action` — `responseStatus: "needs-action"` → `{"responseStatus": "NEEDS-ACTION"}`

4. **Add `TestModifyVeventPartstat` test class** after `TestBuildEventPatch`:
   - `test_modifies_single_attendee` — .ics with one ATTENDEE, modify PARTSTAT, verify round-trip
   - `test_modifies_correct_attendee_in_multi` — .ics with 3 attendees, modify only the target, verify others unchanged
   - `test_returns_unchanged_when_email_not_found` — .ics with attendees, user_email doesn't match any → returns original text unchanged (or equivalent regenerated .ics)
   - `test_case_insensitive_mailto` — `mailto:User@Example.COM` matches `user@example.com`
   - `test_round_trip_modify_then_extract` — modify PARTSTAT → re-parse → extract_attendees → verify PARTSTAT matches expected
   - `test_no_attendees_returns_unchanged` — VEVENT with no ATTENDEE property → returns unchanged
   - `test_preserves_other_attendee_params` — ATTENDEE with CN, ROLE, RSVP params → only PARTSTAT changed, others preserved

   Use the `_build_ics()` helper from test_caldav_sync_engine.py as a reference for building test .ics strings, but build them directly with the `icalendar` library in these tests since they're in the field mapper test file.

5. **Update imports** in test file — add `modify_vevent_partstat` to the imports from field_mapper module at the top of the file.

## Must-Haves

- [ ] `build_event_patch()` returns correct PARTSTAT for all 4 mapped statuses (ACCEPTED, DECLINED, TENTATIVE, NEEDS-ACTION)
- [ ] `build_event_patch()` returns `{}` for empty props, unmapped status, and missing user_email
- [ ] `modify_vevent_partstat()` correctly modifies PARTSTAT on matching ATTENDEE
- [ ] `modify_vevent_partstat()` uses case-insensitive email comparison
- [ ] `modify_vevent_partstat()` returns unchanged .ics when email not found or no attendees
- [ ] `modify_vevent_partstat()` preserves other ATTENDEE params (CN, ROLE, RSVP)
- [ ] All 85 existing field mapper tests still pass (zero regressions)
- [ ] No "stub" or "S03" comments remain in field_mapper.py reverse mapping section

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && uv run python -m pytest tests/test_caldav_field_mapper.py -v -x` — all tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && uv run python -m pytest tests/test_caldav_field_mapper.py -v -k "BuildEventPatch or ModifyVevent"` — ~14 new tests pass
- Grep: `rg "stub|S03|not yet implemented" apps/caldav-calendar/services/field_mapper.py` — zero matches (run from worktree root)

## Inputs

- `apps/caldav-calendar/services/field_mapper.py` — Contains stub `build_event_patch()` at line 432, `REVERSE_RESPONSE_STATUS_MAP` at line 55, `_normalize_to_list()` at line 186, and `BPKM` namespace constant at line 24
- `backend/tests/test_caldav_field_mapper.py` — Contains `TestBuildEventPatch` stub tests at line 762, imports `build_event_patch` from field_mapper at line 63
- S02 summary: `_normalize_to_list()` handles icalendar's single-vs-list return behavior for ATTENDEE; BPKM prefix is `urn:sempkm:model:basic-pkm:`

## Observability Impact

- **What changes:** `build_event_patch()` transitions from a no-op stub to a real mapper that returns iCalendar PARTSTAT values. `modify_vevent_partstat()` is a new pure function — no runtime logging, but its return value (modified .ics text or unchanged original) is the primary diagnostic signal for push_sync (T02).
- **How to inspect:** Both functions are pure — call them directly in a REPL or test to verify behavior. `build_event_patch()` returns `{}` on all non-actionable inputs (easy to check). `modify_vevent_partstat()` returns the original text unchanged when no matching attendee is found (detectable by string equality).
- **Failure visibility:** `build_event_patch()` never raises — it returns `{}` for any unrecognized input. `modify_vevent_partstat()` propagates icalendar parse errors if the input is invalid .ics. The T02 push_sync pipeline will log per-event errors from these functions.

## Expected Output

- `apps/caldav-calendar/services/field_mapper.py` — `build_event_patch()` returns real RSVP dicts, new `modify_vevent_partstat()` function added, no stub comments
- `backend/tests/test_caldav_field_mapper.py` — `TestBuildEventPatch` has 7 real tests, new `TestModifyVeventPartstat` with ~7 tests, all 85 existing + ~14 new pass
