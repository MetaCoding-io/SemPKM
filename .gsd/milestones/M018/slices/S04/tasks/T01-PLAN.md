---
estimated_steps: 8
estimated_files: 6
---

# T01: RSVP push-back pipeline (reverse mapping, PATCH, push_sync, loop prevention, wiring)

**Slice:** S04 — RSVP push-back + recurrence handling
**Milestone:** M018

## Description

Build the complete RSVP push-back pipeline for Google Calendar sync. This mirrors the GitHub sync push_sync pattern (reference: `apps/github-sync/services/sync_engine.py` lines 181-373) adapted for Google Calendar's Events.patch API. The feature allows users to change their RSVP status on a synced event in SemPKM, and have that change pushed back to Google Calendar.

Key constraints from the research:
- Google Events.patch RSVP requires sending `attendeesOmitted: true` and a partial attendees array with only the self-attendee entry
- The self-attendee email is stored in state as `google_email` (set during OAuth)
- `bpkm:calendarName` already contains the calendar ID (not display name) because pull_sync passes `calendar_id` as `calendar_name`
- Reverse mapping is RSVP-only per D213 — no title/description/time push
- Loop prevention must exist in pull_sync to prevent pushed RSVP changes from being re-imported

## Steps

1. **Add reverse mapping to field_mapper.py.** Add `REVERSE_RESPONSE_STATUS_MAP` (inverse of `RESPONSE_STATUS_MAP`: `"accepted"→"accepted"`, `"declined"→"declined"`, `"tentative"→"tentative"`, `"needs-action"→"needsAction"`). Add `build_event_patch(event_props: dict, google_email: str) -> dict` that reads `bpkm:responseStatus` from event_props and returns `{"attendees": [{"email": google_email, "self": True, "responseStatus": "<gcal_value>"}], "attendeesOmitted": True}`. Return empty dict if no responseStatus or no mapping.

2. **Add `patch_event()` to GCalClient.** Add `async def patch_event(self, calendar_id: str, event_id: str, data: dict) -> dict` that calls `self._request("PATCH", f"{GCAL_BASE_URL}/calendars/{calendar_id}/events/{event_id}", json=data)`. Follow the same pattern as `get_events()` and `get_calendar_list()`.

3. **Add `_find_changed_events()` to sync_engine.py.** SPARQL query finding events where: `externalProvider = "google-calendar"`, `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt), and pull `?event ?status ?extId ?calName ?responseStatus ?lastSynced ?modified`. Return list of dicts with `iri`, `externalId`, `calendarName`, `responseStatus`, `lastSyncedAt`. Pattern follows `_find_changed_tasks()` from GitHub sync.

4. **Add `push_sync(ctx)` to sync_engine.py.** Follow GitHub push_sync pattern exactly:
   - Check auth via `get_connection_status()`
   - Read `sync_direction` from settings — skip if `pull-only`
   - Read `google_email` from state (needed for PATCH body)
   - Call `_find_changed_events()`
   - For each changed event: call `build_event_patch()` → call `gcal_client.patch_event()` → update `lastSyncedAt` via `object.patch` command
   - Store `last_push_result` in state as JSON
   - Return structured result dict `{status, pushed, skipped, errors, timestamp}`

5. **Add loop prevention to `pull_sync()`.** In the per-event processing loop, after `_find_existing_event()` returns an existing event, compare the Google event's `updated` timestamp against the existing event's `lastSyncedAt`. If `updated <= lastSyncedAt`, increment `unchanged_count` and skip. This prevents re-importing events that were just pushed.

6. **Wire push_sync into app.py handlers.** Replace `push_changes` task handler placeholder with real `push_sync()` call. In `sync_now` route: replace the bidirectional placeholder with actual `push_sync()` call and store result. In `poll_events` task: replace the bidirectional placeholder with actual `push_sync()` call and store result.

7. **Add reverse mapping tests to test_gcal_field_mapper.py.** New test class `TestBuildEventPatch` with ≥5 tests: accepted mapping, declined mapping, tentative mapping, needs-action mapping, no responseStatus returns empty dict, unknown status returns empty dict.

8. **Add push_sync tests to test_gcal_sync_engine.py.** New test classes:
   - `TestFindChangedEvents` (≥4 tests): finds changed events, skips pull-only, handles no changes, returns correct fields
   - `TestPushSync` (≥8 tests): not connected skips, pull-only skips, no changed events ok, successful RSVP push (mock PATCH), lastSyncedAt updated after push, error isolation per-event, last_push_result stored, partial status on mixed success/error
   - `TestLoopPrevention` (≥3 tests): event with updated <= lastSyncedAt skipped, event with updated > lastSyncedAt processed, event with no lastSyncedAt processed
   - `TestPushWiring` (≥3 tests): sync_now calls push when bidirectional, poll_events calls push when bidirectional, push_changes calls push_sync

   **Important for mock response queues:** The existing tests use `MockExternalHttpClient` with sequential response queues. Push tests need PATCH responses added. The `token_expiry: "2099"` trick means refresh_if_expired skips HTTP — only GCal API calls consume mock responses. Each push_sync test needs one mock PATCH response per pushed event.

## Must-Haves

- [ ] `REVERSE_RESPONSE_STATUS_MAP` correctly inverts all 4 responseStatus values
- [ ] `build_event_patch()` produces correct Google PATCH body with `attendeesOmitted: true`
- [ ] `GCalClient.patch_event()` sends PATCH to correct URL
- [ ] `_find_changed_events()` returns only google-calendar events where modified > lastSyncedAt
- [ ] `push_sync()` returns structured result dict matching pull_sync shape
- [ ] Loop prevention in pull_sync skips events where `updated <= lastSyncedAt`
- [ ] app.py push_changes/sync_now/poll_events call real push_sync when bidirectional
- [ ] ≥22 new tests pass

## Verification

- `pytest backend/tests/test_gcal_field_mapper.py -v` — all tests pass including new reverse mapping tests
- `pytest backend/tests/test_gcal_sync_engine.py -v` — all tests pass including new push/loop tests
- `pytest -x` — full suite stays green

## Observability Impact

- Signals added: `google_calendar.sync` logger INFO for push_sync start/complete with counts, WARNING on per-event push failures
- How a future agent inspects this: `ctx.state.get("last_push_result")` returns JSON with status/pushed/skipped/errors/timestamp
- Failure state exposed: per-event errors in result `errors` array with `event_iri` and `error`; overall `status` field reflects `ok|partial|error`

## Inputs

- `apps/google-calendar/services/field_mapper.py` — existing RESPONSE_STATUS_MAP, BPKM constant, build_event_properties()
- `apps/google-calendar/services/gcal_client.py` — existing GCalClient with `_request()` method
- `apps/google-calendar/services/sync_engine.py` — existing pull_sync, _find_existing_event, _submit_commands_batched
- `apps/google-calendar/app.py` — existing sync_now, poll_events, push_changes handlers with placeholders
- `apps/github-sync/services/sync_engine.py` lines 181-373 — reference implementation for push_sync pattern
- `apps/github-sync/services/field_mapper.py` line 298 — reference for build_issue_patch reverse mapping
- `backend/tests/test_gcal_sync_engine.py` — existing test infrastructure (MockStateClient, MockGraphClient, MockExternalHttpClient, importlib loading)
- S03 Forward Intelligence: mock response queue alignment is fragile — any new HTTP call needs corresponding mock response; `token_expiry: "2099"` trick avoids token refresh mock responses

## Expected Output

- `apps/google-calendar/services/field_mapper.py` — gains REVERSE_RESPONSE_STATUS_MAP + build_event_patch() (~20 lines)
- `apps/google-calendar/services/gcal_client.py` — gains patch_event() method (~15 lines)
- `apps/google-calendar/services/sync_engine.py` — gains _find_changed_events() + push_sync() (~120 lines); pull_sync() gains loop prevention filter (~8 lines)
- `apps/google-calendar/app.py` — push_changes/sync_now/poll_events wired to real push_sync (~20 lines changed)
- `backend/tests/test_gcal_field_mapper.py` — gains TestBuildEventPatch class (~40 lines)
- `backend/tests/test_gcal_sync_engine.py` — gains TestFindChangedEvents, TestPushSync, TestLoopPrevention, TestPushWiring classes (~250 lines)
