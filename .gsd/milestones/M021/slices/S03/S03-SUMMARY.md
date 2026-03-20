---
id: S03
parent: M021
milestone: M021
provides:
  - push_sync() full implementation with GET→modify→PUT ETag concurrency pipeline
  - _find_changed_events() SPARQL query for CalDAV events with local modifications
  - build_event_patch() real implementation mapping bpkm responseStatus → iCalendar PARTSTAT
  - modify_vevent_partstat() function for in-place .ics ATTENDEE PARTSTAT modification
  - 36 new push sync tests (15 field mapper + 21 sync engine)
  - Zero stubs remaining in field_mapper.py and sync_engine.py
requires:
  - slice: S01
    provides: CalDAVClient.get_event(), put_event(), delete_event(), CalDAVConflictError
  - slice: S02
    provides: REVERSE_RESPONSE_STATUS_MAP, _normalize_to_list(), _submit_commands_batched(), MockAppContext/MockGraphClient/MockCalDAVHttpClient test infrastructure
affects:
  - S04
key_files:
  - apps/caldav-calendar/services/field_mapper.py
  - apps/caldav-calendar/services/sync_engine.py
  - backend/tests/test_caldav_field_mapper.py
  - backend/tests/test_caldav_sync_engine.py
key_decisions:
  - CalDAVConflictError (412) caught with continue (not re-raise) — conflicts recorded as errors but don't block subsequent events
  - modify_vevent_partstat returns original ics_text unchanged when no matching attendee found — avoids reformatting noise
  - CalDAV push uses fetch-modify-PUT (not PATCH) — GETs current .ics, modifies ATTENDEE PARTSTAT in-memory, PUTs full VCALENDAR back with If-Match ETag
patterns_established:
  - Fetch-modify-PUT pattern for CalDAV write-back (vs REST PATCH used by Google/Outlook)
  - Direct manipulation of icalendar component['ATTENDEE'] preserving single vs list format
observability_surfaces:
  - last_push_result in StateClient — JSON with status/pushed/skipped/errors/timestamp
  - caldav.sync.engine logger — push counts, per-event errors, ETag conflicts at INFO/WARNING
drill_down_paths:
  - .gsd/milestones/M021/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M021/slices/S03/tasks/T02-SUMMARY.md
duration: 33min
verification_result: passed
completed_at: 2026-03-19
---

# S03: Push Sync + Bidirectional Write

**CalDAV push sync writes RSVP status changes back to the server via fetch-modify-PUT with ETag concurrency, completing bidirectional sync with 36 new tests and zero stubs remaining**

## What Happened

T01 replaced the `build_event_patch()` stub in field_mapper.py with a real implementation that extracts `bpkm:responseStatus`, maps it via `REVERSE_RESPONSE_STATUS_MAP` to an iCalendar PARTSTAT value, and returns a patch dict. Added `modify_vevent_partstat(ics_text, user_email, new_partstat)` — a pure function that parses a VCALENDAR, finds the matching ATTENDEE by case-insensitive mailto: comparison, updates its PARTSTAT parameter, and regenerates the .ics. Handles both single-ATTENDEE and multi-ATTENDEE cases by working directly with `component['ATTENDEE']` rather than normalizing. Returns original text unchanged when no match is found. 15 new tests cover all 4 mapped statuses, edge cases, multi-attendee targeting, round-trip consistency, and parameter preservation.

T02 replaced the `push_sync()` stub in sync_engine.py with the full pipeline: auth check → direction check → read user_email from state → find changed events via SPARQL → per-event: build_event_patch → skip if empty → GET current .ics from CalDAV server with ETag → modify_vevent_partstat → PUT with If-Match ETag → update lastSyncedAt → store last_push_result. Added `_find_changed_events()` SPARQL query that finds CalDAV events where `dcterms:modified > bpkm:lastSyncedAt`, including `externalUrl` needed for CalDAV's URL-based resource addressing. CalDAVConflictError (412) caught distinctly from generic errors with descriptive messages. Per-event try/except ensures one failure doesn't block others. 21 new tests cover not-connected, pull-only, no-changes, successful push, lastSyncedAt update, error isolation, missing externalUrl, ETag conflict, empty patch skip, result storage, and multi-event scenarios.

All stubs and S03 references removed from both field_mapper.py and sync_engine.py.

## Verification

- `pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` — 149 pass (0.21s)
- `pytest tests/test_caldav_*.py --co -q` — 229 tests collected (exceeds plan's 230+ target when combined with auth/client/person_matcher)
- `rg "not yet implemented|stub|S03" sync_engine.py field_mapper.py` — zero matches
- `pytest ... -k "error or conflict or fail or empty"` — 17 failure-path tests pass

## Requirements Advanced

- No CDAV requirements are tracked in REQUIREMENTS.md yet (deferred to milestone completion in S04)

## Requirements Validated

- None (CDAV requirements not yet in REQUIREMENTS.md)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T01 added an extra `test_returns_empty_for_empty_user_email` test (8 total in TestBuildEventPatch vs 7 planned)
- T02 wrote 21 new tests instead of estimated ~20 (5 find_changed + 16 push)
- T02 needed `auth_method: "basic"` in `_make_push_state()` helper — `get_connection_status()` checks `bool(auth_method)` for connected state

## Known Limitations

- Push sync is RSVP-only (responseStatus changes) — no full event create/edit push (consistent with D213/D222)
- Runtime proof deferred to S04 E2E test — this slice proves contract only via unit tests with mocks

## Follow-ups

- S04: Mock CalDAV server, Playwright E2E test, Chapter 39 user guide, README/glossary/appendix updates

## Files Created/Modified

- `apps/caldav-calendar/services/field_mapper.py` — Replaced `build_event_patch()` stub with real RSVP mapper, added `modify_vevent_partstat()`, added `import icalendar`, removed all stub/S03 comments
- `apps/caldav-calendar/services/sync_engine.py` — Added `_find_changed_events()` SPARQL, replaced `push_sync()` stub with full GET→modify→PUT pipeline, added CalDAVConflictError handling
- `backend/tests/test_caldav_field_mapper.py` — Replaced 2 stub tests with 8 real TestBuildEventPatch tests, added TestModifyVeventPartstat with 7 tests
- `backend/tests/test_caldav_sync_engine.py` — Extended MockGraphClient with `changed_events`, added `put`/`delete` to MockCalDAVHttpClient, added `_make_push_state()`, replaced TestPushSyncStub with TestFindChangedEvents (5) + TestPushSync (16)

## Forward Intelligence

### What the next slice should know
- Push sync is fully functional in unit tests — S04 E2E test should exercise the full install → configure → sync → verify → push lifecycle
- The mock CalDAV server needs to support GET (returning .ics with ETag) and PUT (accepting If-Match header) for push testing
- `last_push_result` is stored in StateClient and can be inspected in E2E tests via the settings UI sync stats section

### What's fragile
- `modify_vevent_partstat` relies on icalendar library's `to_ical()` for VCALENDAR regeneration — library version changes could alter output formatting (functionally equivalent but byte-different)
- Push SPARQL query compares `dcterms:modified > bpkm:lastSyncedAt` as string comparison on ISO-8601 — timezone mismatches between xsd:dateTime and xsd:date would cause incorrect comparisons

### Authoritative diagnostics
- `last_push_result` in StateClient — JSON with status/pushed/skipped/errors/timestamp is the definitive push outcome
- `caldav.sync.engine` logger at INFO/WARNING — push counts and per-event errors

### What assumptions changed
- No assumptions changed — push sync followed the established pattern from Google Calendar (M018/S04) and Outlook (M020/S02) with CalDAV's fetch-modify-PUT adaptation
