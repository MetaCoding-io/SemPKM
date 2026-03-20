---
id: T02
parent: S02
milestone: M021
provides:
  - CalDAV pull sync engine with two-phase bulk create, 410 recovery, loop prevention, per-event error isolation
  - CalDAV person matcher (SPARQL email lookup, create-on-miss, LRU cache)
  - Sync-token extraction from multistatus XML via _extract_sync_token() and _report_raw()
  - app.py sync_now/poll_events/push_changes wired to real sync engine (stubs removed)
  - 49 new unit tests (31 sync engine + 18 person matcher) all passing
key_files:
  - apps/caldav-calendar/services/sync_engine.py
  - apps/caldav-calendar/services/person_matcher.py
  - apps/caldav-calendar/services/caldav_client.py
  - apps/caldav-calendar/app.py
  - backend/tests/test_caldav_sync_engine.py
  - backend/tests/test_caldav_person_matcher.py
key_decisions:
  - Used _report_raw() alongside _report() for backward compat — _report() is unchanged for discovery methods, _report_raw() adds raw XML capture for sync-token extraction
  - PhaseAwareGraphClient test helper for two-phase create tests — tracks per-slug query counts to return empty on first lookup (phase 1) and found on second (phase 2)
patterns_established:
  - CalDAV selected_calendars can be list of strings or list of dicts — sync engine normalizes to (href, name) tuples
  - Self-attendee/organizer filtering by user email from state username field
observability_surfaces:
  - caldav.sync.engine logger with per-calendar event counts, sync-token mode (incremental/full), per-event errors
  - caldav.sync.person_matcher logger with email lookups and person creation
  - last_pull_result in StateClient — JSON with status/created/updated/unchanged/errors/timestamp
  - sync_token:{calendar_href} per-calendar tokens in StateClient
  - last_sync_at ISO timestamp in StateClient
duration: 35m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Build sync engine, person matcher, fix sync-token extraction, wire app.py

**Built CalDAV pull sync pipeline: sync engine (two-phase bulk create, 410 recovery, loop prevention), person matcher, sync-token extraction from XML, and wired app.py to real sync calls — 196 total tests passing with zero regressions**

## What Happened

Built three modules and modified two existing ones to complete the CalDAV pull sync pipeline:

1. **caldav_client.py** — Added `_extract_sync_token(xml_text)` module-level function that parses root-level `<d:sync-token>` from multistatus XML responses. Added `_report_raw()` method that returns `(entries, raw_xml)` tuple, keeping `_report()` unchanged for backward compat. Updated `get_events()` to use `_report_raw()` and extract sync tokens automatically.

2. **person_matcher.py** — Cloned from Google Calendar's pattern with only the logger name changed to `caldav.sync.person_matcher`. Same SPARQL email lookup (foaf:mbox + crm:email UNION), create-on-miss via object.create command, case-insensitive LRU cache.

3. **sync_engine.py** — ~400 line module following the Google Calendar sync engine pattern adapted for CalDAV. `pull_sync(ctx)` implements: auth check → read selected calendars (normalizes string or dict formats) → for each calendar: fetch events with sync-token, parse .ics with icalendar library, walk VEVENT components, classify new/update/unchanged. Two-phase bulk create (phase 1: object.create, phase 2: body.set + edge.create after IRI discovery). 410 Gone recovery (clear sync-token, retry with full sync). Loop prevention via lastSyncedAt comparison. Per-event error isolation. Attendee/organizer resolution via PersonMatcher with self-exclusion. `push_sync(ctx)` returns stub result for S03.

4. **app.py** — Replaced sync_now route stub with real `pull_sync(ctx)` call (+ optional `push_sync` for bidirectional). Replaced poll_events task stub with `pull_sync` + conditional `push_sync`. Replaced push_changes task stub with `push_sync`.

## Verification

- 196 total tests pass across all CalDAV test files (85 field mapper + 49 new + 62 S01)
- Zero regressions on S01 tests — `_report()` method unchanged, `_report_raw()` added alongside
- Sync-token extraction proven: `test_extracts_sync_token_from_multistatus` verifies non-None return
- 410 recovery proven: `test_410_clears_token_and_retries` verifies two REPORT requests made
- Per-event error isolation proven: `test_malformed_ics_is_captured_as_error` verifies good events still processed
- Loop prevention proven: `test_event_not_modified_since_last_sync_is_unchanged` verifies no commands submitted
- app.py stubs verified removed: `grep -r "Stub\|stub" app.py` returns no results

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py -v` | 0 | ✅ pass | 0.14s |
| 2 | `pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` | 0 | ✅ pass | 0.08s |
| 3 | `pytest tests/test_caldav_field_mapper.py -v` | 0 | ✅ pass | 0.10s |
| 4 | `pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py tests/test_caldav_auth.py tests/test_caldav_client.py -v` | 0 | ✅ pass | 0.24s |
| 5 | `grep -r "Stub\|stub\|not yet implemented" apps/caldav-calendar/app.py` | 1 | ✅ pass (no stubs) | <1s |

## Diagnostics

- **Runtime state**: `last_pull_result` in StateClient — JSON dict with status/created/updated/unchanged/errors/timestamp. `sync_token:{calendar_href}` stores per-calendar sync tokens. `last_sync_at` stores last sync timestamp.
- **Logs**: `caldav.sync.engine` logger at INFO for per-calendar fetch counts, sync-token mode, per-event errors. `caldav.sync.person_matcher` at DEBUG for cache hits and person creation.
- **Test diagnosis**: `pytest tests/test_caldav_sync_engine.py -v -k "pull_sync"` — tests the full pipeline. `pytest tests/test_caldav_sync_engine.py -k "sync_token"` — tests sync-token extraction and persistence. `pytest tests/test_caldav_person_matcher.py -v` — tests person matching in isolation.

## Deviations

- Plan suggested adding `_report_with_raw()` but I named it `_report_raw()` for brevity — same behavior.
- Plan mentioned `build_event_patch` in field mapper but that function already existed from T01 as a stub.
- The `PhaseAwareGraphClient` pattern was needed for new-event tests — standard `MockGraphClient` always finds the event, making it impossible to test the "new event" path. Created a reusable helper class that tracks per-slug query counts.

## Known Issues

None.

## Files Created/Modified

- `apps/caldav-calendar/services/sync_engine.py` — new: ~400 line pull sync engine with two-phase bulk create
- `apps/caldav-calendar/services/person_matcher.py` — new: ~140 line person matcher cloned from Google Calendar
- `apps/caldav-calendar/services/caldav_client.py` — modified: added `_extract_sync_token()`, `_report_raw()`, updated `get_events()`
- `apps/caldav-calendar/app.py` — modified: sync_now/poll_events/push_changes wired to real sync functions
- `backend/tests/test_caldav_sync_engine.py` — new: 31 tests covering sync engine pipeline
- `backend/tests/test_caldav_person_matcher.py` — new: 18 tests covering person matcher
