# S04: RSVP push-back + recurrence handling

**Goal:** User changes RSVP status in SemPKM and it reflects in Google Calendar. Recurring events stored as master (RRULE) + exceptions linked via recurringEventId.
**Demo:** Push sync detects a changed responseStatus on a bpkm:Event, PATCHes the Google Calendar API with the updated RSVP, and updates lastSyncedAt. Recurring event exceptions link to their master event via SPARQL-resolved IRIs.

## Must-Haves

- `REVERSE_RESPONSE_STATUS_MAP` and `build_event_patch()` in field_mapper.py for RSVP reverse mapping
- `GCalClient.patch_event()` method using the existing `_request("PATCH", ...)` pattern
- `_find_changed_events()` SPARQL query detecting events with modified > lastSyncedAt and externalProvider = "google-calendar"
- `push_sync(ctx)` function following the GitHub push_sync pattern (auth check → direction check → find changed → reverse map → PATCH → update lastSyncedAt)
- Loop prevention in `pull_sync()`: skip events where `updated <= lastSyncedAt`
- `push_changes` task handler wired to real push_sync; push called from sync_now and poll_events when bidirectional
- Recurrence exception linking: after pull phase 1+2, find new events with recurringEventId, SPARQL-lookup master by externalId, create edge.create commands
- ≥30 new tests across push pipeline and recurrence linking

## Proof Level

- This slice proves: contract (unit tests with mock HTTP/graph clients)
- Real runtime required: no (mock-based verification, E2E deferred to S05)
- Human/UAT required: no

## Verification

- `pytest backend/tests/test_gcal_field_mapper.py -v` — reverse mapping tests pass (≥5 new)
- `pytest backend/tests/test_gcal_sync_engine.py -v` — push_sync + recurrence tests pass (≥25 new)
- `pytest -x` — full suite stays green (currently 1609)
- Total new tests ≥ 30
- Diagnostic check: `push_sync()` returns structured `{status, pushed, skipped, errors, timestamp}` with `status` reflecting `ok|partial|error` and per-event errors in `errors` array — verified via unit test assertions on error isolation and partial status

## Observability / Diagnostics

- Runtime signals: `google_calendar.sync` logger INFO for push_sync (events found, pushed, errors), WARNING on per-event push failures
- Inspection surfaces: `last_push_result` state key stores structured JSON `{status, pushed, skipped, errors, timestamp}` — same shape as pull result for UI consistency
- Failure visibility: Per-event errors captured in result `errors` array with `event_iri` and `error` string; `push_sync` returns overall status `ok|partial|error`
- Redaction constraints: Google email read from state, not logged in error messages

## Integration Closure

- Upstream surfaces consumed: `field_mapper.py` (RESPONSE_STATUS_MAP, BPKM), `sync_engine.py` (pull_sync, _submit_commands_batched, _find_existing_event), `gcal_client.py` (GCalClient._request), `auth.py` (get_connection_status, refresh_if_expired), `app.py` (sync_now, poll_events, push_changes handlers)
- New wiring introduced in this slice: push_sync called from app.py sync_now/poll_events/push_changes; loop prevention filter added to pull_sync; recurrence edge linking added to pull_sync phase 2
- What remains before the milestone is truly usable end-to-end: S05 — mock Google Calendar API server, Playwright E2E test, user guide

## Tasks

- [x] **T01: RSVP push-back pipeline (reverse mapping, PATCH, push_sync, loop prevention, wiring)** `est:45m`
  - Why: Implements GCAL-05 — the full push pipeline from change detection through Google API PATCH to loop prevention. This is the highest-value feature in the slice and unblocks S05 E2E testing.
  - Files: `apps/google-calendar/services/field_mapper.py`, `apps/google-calendar/services/gcal_client.py`, `apps/google-calendar/services/sync_engine.py`, `apps/google-calendar/app.py`, `backend/tests/test_gcal_field_mapper.py`, `backend/tests/test_gcal_sync_engine.py`
  - Do: (1) Add `REVERSE_RESPONSE_STATUS_MAP` and `build_event_patch()` to field_mapper.py. (2) Add `patch_event(calendar_id, event_id, data)` to GCalClient. (3) Add `_find_changed_events()` SPARQL and `push_sync(ctx)` to sync_engine.py following GitHub push_sync pattern. (4) Add loop prevention filter to `pull_sync()` — skip events where Google `updated` <= existing `lastSyncedAt`. (5) Wire push_sync into app.py: replace push_changes placeholder, add push to sync_now and poll_events when bidirectional. (6) Tests for all of the above (≥22 new tests).
  - Verify: `pytest backend/tests/test_gcal_field_mapper.py backend/tests/test_gcal_sync_engine.py -v` — all pass; `pytest -x` — full suite green
  - Done when: push_sync detects changed events, reverse-maps responseStatus, PATCHes Google API, updates lastSyncedAt, prevents push→pull loops; ≥22 new tests pass

- [x] **T02: Recurrence exception linking in pull_sync** `est:25m`
  - Why: Implements GCAL-06 — recurring event exception instances need edges linking them to the master event via recurringEventId → externalId SPARQL resolution. This completes the recurrence story beyond just storing the property.
  - Files: `apps/google-calendar/services/sync_engine.py`, `backend/tests/test_gcal_sync_engine.py`
  - Do: (1) After pull_sync phase 1+2, collect all newly created/updated events that have `bpkm:recurringEventId` set (from the events already processed in the loop — track slugs with recurringEventId). (2) For each, SPARQL-lookup the master event by matching `bpkm:externalId` against the `recurringEventId` value. (3) Create `edge.create` commands linking exception → master via `bpkm:recurringEventId` predicate. (4) Handle gracefully: master not found (log warning, skip), master is self (skip). (5) Tests for recurrence linking (≥10 new tests covering master+exception, orphan exception, self-link skip, multiple exceptions to same master, batch submission).
  - Verify: `pytest backend/tests/test_gcal_sync_engine.py -v` — all pass; `pytest -x` — full suite green
  - Done when: Pull sync creates edges from exception events to master events; orphan exceptions handled gracefully; ≥10 new tests pass

## Files Likely Touched

- `apps/google-calendar/services/field_mapper.py`
- `apps/google-calendar/services/gcal_client.py`
- `apps/google-calendar/services/sync_engine.py`
- `apps/google-calendar/app.py`
- `backend/tests/test_gcal_field_mapper.py`
- `backend/tests/test_gcal_sync_engine.py`
