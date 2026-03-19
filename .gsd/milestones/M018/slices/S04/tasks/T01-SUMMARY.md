---
id: T01
parent: S04
milestone: M018
provides:
  - RSVP push-back pipeline (reverse mapping, PATCH, push_sync, loop prevention, app.py wiring)
  - 32 new unit tests covering push pipeline, loop prevention, and reverse mapping
key_files:
  - apps/google-calendar/services/field_mapper.py
  - apps/google-calendar/services/gcal_client.py
  - apps/google-calendar/services/sync_engine.py
  - apps/google-calendar/app.py
  - backend/tests/test_gcal_field_mapper.py
  - backend/tests/test_gcal_sync_engine.py
key_decisions:
  - Loop prevention uses string comparison of Google updated vs lastSyncedAt timestamps (same approach as GitHub sync)
  - push_sync reads sync_direction from state (not settings) since gcal app stores it there
patterns_established:
  - Push sync follows same pattern as GitHub sync: auth check → direction check → SPARQL change detection → reverse map → API call → update lastSyncedAt
observability_surfaces:
  - last_push_result state key stores structured JSON {status, pushed, skipped, errors, timestamp}
  - google_calendar.sync logger INFO for push start/complete with counts, WARNING on per-event failures
  - Per-event errors captured with event_iri and error string in result errors array
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: RSVP push-back pipeline (reverse mapping, PATCH, push_sync, loop prevention, wiring)

**Built complete RSVP push-back pipeline: reverse mapping, GCalClient.patch_event, push_sync engine, pull_sync loop prevention, and app.py handler wiring with 32 new tests**

## What Happened

Implemented the full RSVP push-back pipeline for Google Calendar sync, following the GitHub sync push_sync pattern:

1. **field_mapper.py** — Added `REVERSE_RESPONSE_STATUS_MAP` (inverse of all 4 responseStatus values) and `build_event_patch()` which constructs the Google Events.patch body with `attendeesOmitted: true` and a partial attendees array containing only the self-attendee entry.

2. **gcal_client.py** — Added `patch_event(calendar_id, event_id, data)` method that sends PATCH to the correct Google Calendar API URL using the existing `_request()` infrastructure.

3. **sync_engine.py** — Added `_find_changed_events()` SPARQL query (finds events where modified > lastSyncedAt with externalProvider = "google-calendar") and `push_sync(ctx)` which: checks auth → checks sync_direction → reads google_email → finds changed events → for each: reverse maps responseStatus → PATCHes Google API → updates lastSyncedAt → stores structured result in state.

4. **sync_engine.py (pull_sync)** — Added loop prevention: when an existing event is found, compares Google's `updated` timestamp against `lastSyncedAt`. If `updated <= lastSyncedAt`, increments `unchanged_count` and skips. This prevents re-importing events that were just pushed.

5. **app.py** — Replaced all three push placeholders with real `push_sync()` calls: `push_changes` task handler, `sync_now` route (when bidirectional), and `poll_events` task (when bidirectional).

## Verification

- `pytest tests/test_gcal_field_mapper.py -v` — 75 tests pass (11 new: 2 normalization map + 9 build_event_patch)
- `pytest tests/test_gcal_sync_engine.py -v` — 57 tests pass (21 new: 4 find_changed_events + 11 push_sync + 3 loop_prevention + 3 push_wiring)
- `pytest -x` — full suite green: 1641 passed (was 1609, +32 new)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_gcal_field_mapper.py -v` | 0 | ✅ pass | 0.10s |
| 2 | `pytest tests/test_gcal_sync_engine.py -v` | 0 | ✅ pass | 0.14s |
| 3 | `pytest -x` | 0 | ✅ pass | 8.30s |

## Diagnostics

- **Push result state:** `ctx.state.get("last_push_result")` returns JSON with `{status: "ok"|"partial"|"error", pushed: N, skipped: N, errors: [...], timestamp: "..."}`
- **Per-event errors:** Each error in the `errors` array has `event_iri` and `error` string
- **Logs:** `google_calendar.sync` logger at INFO for push start/complete with counts, WARNING on per-event push failures
- **Google email:** Read from state, not logged in error messages (redaction constraint)

## Deviations

- push_sync reads `sync_direction` from `ctx.state` rather than `ctx.settings` (unlike GitHub sync which uses `ctx.settings`). This matches how the gcal app stores sync_direction in state via the settings form handler.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/services/field_mapper.py` — Added REVERSE_RESPONSE_STATUS_MAP and build_event_patch()
- `apps/google-calendar/services/gcal_client.py` — Added patch_event() method
- `apps/google-calendar/services/sync_engine.py` — Added _find_changed_events(), push_sync(), and loop prevention in pull_sync
- `apps/google-calendar/app.py` — Wired push_sync into push_changes, sync_now, and poll_events handlers
- `backend/tests/test_gcal_field_mapper.py` — Added TestBuildEventPatch class and reverse map tests (11 new)
- `backend/tests/test_gcal_sync_engine.py` — Added TestFindChangedEvents, TestPushSync, TestLoopPrevention, TestPushWiring classes (21 new)
