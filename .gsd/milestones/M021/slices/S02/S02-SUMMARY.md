---
id: S02
parent: M021
milestone: M021
provides:
  - CalDAV iCalendar field mapper with all ~20 VEVENT property extractions and 5 enum maps
  - Pull sync engine with two-phase bulk create, sync-token incremental sync, 410 Gone recovery, loop prevention, per-event error isolation
  - Person matcher with SPARQL email lookup, create-on-miss, LRU cache
  - Sync-token extraction from multistatus XML root element
  - app.py wired to real sync engine (all stubs removed)
  - 134 new unit tests (85 field mapper + 31 sync engine + 18 person matcher)
requires:
  - slice: S01
    provides: CalDAVClient with get_events/put_event/delete_event, auth module with credentials and headers, app.py route/task stubs
affects:
  - S03
key_files:
  - apps/caldav-calendar/services/field_mapper.py
  - apps/caldav-calendar/services/sync_engine.py
  - apps/caldav-calendar/services/person_matcher.py
  - apps/caldav-calendar/services/caldav_client.py
  - apps/caldav-calendar/app.py
  - backend/tests/test_caldav_field_mapper.py
  - backend/tests/test_caldav_sync_engine.py
  - backend/tests/test_caldav_person_matcher.py
key_decisions:
  - Used _report_raw() alongside _report() for backward compat — _report() unchanged for discovery methods, _report_raw() adds raw XML capture for sync-token extraction
  - PhaseAwareGraphClient test helper for two-phase create tests — tracks per-slug query counts to simulate new-event discovery path
patterns_established:
  - icalendar RRULE BYDAY must be list of individual weekday strings, not comma-separated (library validates each value)
  - _normalize_to_list() pattern for icalendar single-vs-list return behavior (ATTENDEE, CATEGORIES)
  - CalDAV selected_calendars can be list of strings or list of dicts — sync engine normalizes to (href, name) tuples
  - Self-attendee/organizer filtering by user email from state username field
observability_surfaces:
  - caldav.sync.engine logger — per-calendar event counts, sync-token incremental vs full, per-event errors
  - caldav.sync.person_matcher logger — email lookups, person creation
  - last_pull_result in StateClient — JSON with status/created/updated/unchanged/errors/timestamp
  - sync_token:{calendar_href} per-calendar sync tokens in StateClient
  - last_sync_at ISO timestamp in StateClient
drill_down_paths:
  - .gsd/milestones/M021/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M021/slices/S02/tasks/T02-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-19
---

# S02: Pull Sync + Field Mapping + Person Matching

**CalDAV pull sync pipeline complete — field mapper extracts all ~20 VEVENT properties from iCalendar data, sync engine orchestrates two-phase bulk create with incremental sync-token support, person matcher resolves attendees via SPARQL. 196 total tests pass across the full CalDAV test suite.**

## What Happened

T01 built the field mapper as a pure-function module with 17 extraction functions covering every VEVENT property in the domain mapping spec. The `icalendar` library (v7.0.3) has non-obvious type behavior — `component.get('ATTENDEE')` returns a `vCalAddress` for a single value, a `list` for multiple, and `None` for missing. A `_normalize_to_list()` helper handles this uniformly. RRULE extraction needed a fix: the library's `vRecur.to_ical()` returns bytes with a `RRULE:` prefix that must be stripped. BYDAY values must be passed as a list of individual weekday strings, not comma-separated. Five enum maps (STATUS, CLASS, TRANSP, PARTSTAT, REVERSE_RESPONSE_STATUS) cover the CalDAV↔bpkm value translations.

T02 built the sync engine, person matcher, and sync-token extraction. The sync engine follows the Google Calendar pattern adapted for CalDAV: auth check → selected calendars → per-calendar event fetch → iCalendar parse → VEVENT walk → classify new/update/unchanged → two-phase bulk create. Sync-token extraction was added to `caldav_client.py` via `_report_raw()` which returns `(entries, raw_xml)` — the raw XML is parsed for the root-level `<d:sync-token>` element. The original `_report()` method is unchanged for backward compat. The person matcher is cloned from Google Calendar — same SPARQL email lookup (foaf:mbox + crm:email UNION), create-on-miss, LRU cache. App.py stubs were replaced with real `pull_sync(ctx)` calls in sync_now, poll_events, and push_changes routes.

## Verification

- 196 total tests pass: 85 field mapper + 31 sync engine + 18 person matcher + 62 S01 (zero regressions)
- All tests run in <0.25s combined
- Sync-token extraction: `test_extracts_sync_token_from_multistatus` proves non-None return from real XML
- 410 recovery: `test_410_clears_token_and_retries` proves two REPORT requests made after 410
- Per-event error isolation: `test_malformed_ics_is_captured_as_error` proves good events still processed alongside failures
- Loop prevention: `test_event_not_modified_since_last_sync_is_unchanged` proves no commands for unmodified events
- Two-phase create: `test_single_new_event_creates_commands` proves phase 1 object.create + phase 2 body.set/edge.create
- Person matching: email match, cache hit, create-on-miss, None email all covered
- No stubs remaining in app.py (grep verified)

## Requirements Advanced

- No new CDAV requirements validated — this is contract-level proof only (unit tests with mocks). Runtime validation deferred to S04 E2E.

## Requirements Validated

- None — runtime proof required for CDAV requirement validation, deferred to S04.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Plan suggested `_report_with_raw()` method name — implemented as `_report_raw()` for brevity. Same behavior.
- T02 produced 49 tests (31 sync engine + 18 person matcher) vs plan's "40+ new tests" target — exceeded.

## Known Limitations

- `push_sync()` returns a stub result — real push implementation is S03 scope.
- `build_event_patch()` returns empty dict — reverse field mapping for push is S03 scope.
- No runtime/E2E verification yet — all proof is contract-level via unit tests with mocks. Real CalDAV interaction tested in S04.

## Follow-ups

- S03 needs to implement `push_sync()` with real RSVP push-back via CalDAV PUT + ETag concurrency
- S03 needs `build_event_patch()` reverse mapping in field_mapper.py
- S04 needs mock CalDAV server + E2E test to prove runtime correctness

## Files Created/Modified

- `apps/caldav-calendar/services/field_mapper.py` — New: 443-line pure-function field mapper with 17 extraction functions and 5 enum maps
- `apps/caldav-calendar/services/sync_engine.py` — New: 550-line sync engine with pull_sync and push_sync stub
- `apps/caldav-calendar/services/person_matcher.py` — New: 139-line person matcher with SPARQL lookup and LRU cache
- `apps/caldav-calendar/services/caldav_client.py` — Modified: added _extract_sync_token(), _report_raw(), updated get_events()
- `apps/caldav-calendar/app.py` — Modified: sync_now/poll_events/push_changes wired to real sync functions
- `backend/tests/test_caldav_field_mapper.py` — New: 794-line test file with 85 tests across 17 test classes
- `backend/tests/test_caldav_sync_engine.py` — New: 1300-line test file with 31 tests covering full sync pipeline
- `backend/tests/test_caldav_person_matcher.py` — New: 294-line test file with 18 tests covering person matching

## Forward Intelligence

### What the next slice should know
- `build_event_patch()` in field_mapper.py is a stub returning `{}` — S03 must implement the reverse mapping from bpkm properties to iCalendar VEVENT properties for push sync.
- `push_sync()` in sync_engine.py returns `{"status": "skipped", "reason": "push not yet implemented"}` — S03 replaces this with real implementation.
- The `REVERSE_RESPONSE_STATUS_MAP` is already defined in field_mapper.py — S03 can use it directly for RSVP push-back.
- CalDAVClient already has `put_event()` and `delete_event()` from S01 — S03 needs these for push.

### What's fragile
- `_normalize_to_list()` is critical — any new iCalendar properties that have single-vs-list behavior must use it. The icalendar library does not normalize this for you.
- `_report_raw()` returns `(entries, raw_xml)` while `_report()` returns just `entries` — callers must use the right one. `get_events()` already uses `_report_raw()`.

### Authoritative diagnostics
- `pytest tests/test_caldav_field_mapper.py -v` — 85 tests proving all field extractions
- `pytest tests/test_caldav_sync_engine.py -v` — 31 tests proving sync pipeline including 410 recovery and loop prevention
- `pytest tests/test_caldav_person_matcher.py -v` — 18 tests proving person matching
- All three suites run in <0.25s total

### What assumptions changed
- icalendar BYDAY requires individual strings not comma-separated — documented in KNOWLEDGE.md pattern #3
- Selected calendars format varies (string list vs dict list) — sync engine normalizes both
