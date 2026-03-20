# S03: Push Sync + Bidirectional Write

**Goal:** CalDAV push sync writes RSVP status changes back to the server via fetch-modify-PUT with ETag concurrency control, completing bidirectional sync.
**Demo:** User changes RSVP status on a CalDAV-synced event in SemPKM → push_sync detects the change via SPARQL, fetches the current .ics, modifies the ATTENDEE PARTSTAT, PUTs the full VCALENDAR with If-Match ETag, and updates lastSyncedAt. All push stubs removed.

## Must-Haves

- `build_event_patch()` returns RSVP changes mapped via REVERSE_RESPONSE_STATUS_MAP (not empty dict)
- `modify_vevent_partstat()` parses .ics, modifies the correct ATTENDEE's PARTSTAT, regenerates valid VCALENDAR
- `_find_changed_events()` SPARQL finds caldav events where modified > lastSyncedAt, includes externalUrl
- `push_sync()` orchestrates: auth check → direction check → find changed → per-event GET→modify→PUT → update lastSyncedAt
- CalDAVConflictError (412) caught and recorded as error, not crash
- Per-event error isolation (one failure doesn't block others)
- `last_push_result` stored in state after every push run
- Loop prevention via lastSyncedAt comparison (already proven in pull_sync, reused here)
- Zero push stubs remaining in sync_engine.py and field_mapper.py

## Proof Level

- This slice proves: contract
- Real runtime required: no (unit tests with mocks; runtime proof deferred to S04 E2E)
- Human/UAT required: no

## Verification

- `cd backend && uv run python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` — all pass
- `cd backend && uv run python -m pytest tests/test_caldav_*.py --co -q` — 230+ tests collected (196 existing + ~35 new)
- `rg "not yet implemented|stub|S03" apps/caldav-calendar/services/sync_engine.py apps/caldav-calendar/services/field_mapper.py` — zero matches
- `cd backend && uv run python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -k "error or conflict or fail or empty" --no-header` — failure-path tests exist and pass (confirms diagnostic coverage)

## Observability / Diagnostics

- Runtime signals: `caldav.sync.engine` logger — push event counts, per-event errors, ETag conflicts
- Inspection surfaces: `last_push_result` in StateClient — JSON with status/pushed/skipped/errors/timestamp
- Failure visibility: per-event error dicts in push result with event_iri and error message; CalDAVConflictError distinguished from generic errors

## Integration Closure

- Upstream surfaces consumed: `CalDAVClient.get_event()`, `put_event()`, `delete_event()` from S01; `REVERSE_RESPONSE_STATUS_MAP` and `_normalize_to_list()` from S02 field_mapper; `_submit_commands_batched()` from S02 sync_engine; `MockAppContext`/`MockGraphClient`/`MockCalDAVHttpClient` test infrastructure from S02
- New wiring introduced in this slice: none — app.py already calls `push_sync()` in sync_now (bidirectional), poll_events, and push_changes routes. The stub just gets replaced with real logic.
- What remains before the milestone is truly usable end-to-end: S04 (mock CalDAV server, E2E test, user guide, docs)

## Tasks

- [x] **T01: Implement reverse field mapper and iCalendar PARTSTAT modifier** `est:30m`
  - Why: push_sync depends on `build_event_patch()` to detect pushable changes and `modify_vevent_partstat()` to rewrite the .ics file. These are pure functions testable in isolation.
  - Files: `apps/caldav-calendar/services/field_mapper.py`, `backend/tests/test_caldav_field_mapper.py`
  - Do: Replace `build_event_patch()` stub with real implementation using REVERSE_RESPONSE_STATUS_MAP. Add `modify_vevent_partstat(ics_text, user_email, new_partstat)` that parses with icalendar, finds matching ATTENDEE by case-insensitive mailto: comparison using `_normalize_to_list()`, updates PARTSTAT param, returns regenerated .ics. Replace the 2 stub tests in TestBuildEventPatch with ~15 real tests covering: empty props, unmapped status, each of 4 mapped statuses, no user_email; and for modify_vevent_partstat: single attendee, multiple attendees (correct one modified), email not found (unchanged), case-insensitive mailto, round-trip parse→modify→extract consistency.
  - Verify: `cd backend && uv run python -m pytest tests/test_caldav_field_mapper.py -v -x` — all pass including new push tests
  - Done when: `build_event_patch()` returns correct PARTSTAT dict for all 4 mapped statuses, `modify_vevent_partstat()` modifies correct attendee in multi-attendee .ics, and all 85 existing + ~15 new tests pass

- [x] **T02: Implement push_sync pipeline with change detection and ETag concurrency** `est:40m`
  - Why: Completes the bidirectional sync — `push_sync()` detects local RSVP changes, fetches current .ics from CalDAV server, modifies PARTSTAT, PUTs back with ETag, and updates lastSyncedAt. This is the last functional piece before S04 E2E.
  - Files: `apps/caldav-calendar/services/sync_engine.py`, `backend/tests/test_caldav_sync_engine.py`
  - Do: Add `_find_changed_events(graph_client)` SPARQL query for caldav events where modified > lastSyncedAt, returning iri/externalId/externalUrl/calendarName/responseStatus/lastSyncedAt. Replace `push_sync()` stub with full pipeline: (1) auth check, (2) direction check, (3) read user_email from state, (4) build CalDAVClient, (5) find changed events, (6) per-event: build_event_patch → skip if empty → get_event(externalUrl) → modify_vevent_partstat → put_event(url, modified_ics, etag) → update lastSyncedAt, (7) store last_push_result. Catch CalDAVConflictError on 412 with specific error message. Extend MockGraphClient with `changed_events` list support (same pattern as Google Calendar tests). Replace TestPushSyncStub with ~20 real tests: not connected → skips, pull-only → skips, no changed events → ok, successful RSVP push (assert GET + PUT with correct args), lastSyncedAt updated, error isolation (first fails, second succeeds), missing externalUrl → error, ETag conflict (412) → error with conflict message, _find_changed_events bindings shape, last_push_result stored in state.
  - Verify: `cd backend && uv run python -m pytest tests/test_caldav_sync_engine.py -v -x` — all pass including new push tests; `cd backend && uv run python -m pytest tests/test_caldav_*.py --co -q` — 230+ tests total; `rg "not yet implemented|stub|S03" apps/caldav-calendar/services/sync_engine.py apps/caldav-calendar/services/field_mapper.py` — zero matches
  - Done when: push_sync orchestrates full GET→modify→PUT cycle, CalDAVConflictError handled, error isolation proven, 196 existing + ~20 new sync engine tests pass, zero stubs remain

## Files Likely Touched

- `apps/caldav-calendar/services/field_mapper.py`
- `apps/caldav-calendar/services/sync_engine.py`
- `backend/tests/test_caldav_field_mapper.py`
- `backend/tests/test_caldav_sync_engine.py`
