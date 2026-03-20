---
estimated_steps: 6
estimated_files: 2
---

# T02: Implement push_sync pipeline with change detection and ETag concurrency

**Slice:** S03 — Push Sync + Bidirectional Write
**Milestone:** M021

## Description

Replace the `push_sync()` stub in sync_engine.py with the full bidirectional push pipeline: detect locally-modified CalDAV events via SPARQL, fetch their current .ics from the CalDAV server, modify the ATTENDEE PARTSTAT, PUT back with ETag concurrency control, and update lastSyncedAt. Add `_find_changed_events()` SPARQL query. Extend the test mock infrastructure and write ~20 push pipeline tests following the Google Calendar push test pattern.

## Steps

1. **Add `_find_changed_events()` SPARQL query** to sync_engine.py, after the existing `_find_existing_event()` function (around line 92):

   ```python
   async def _find_changed_events(graph_client) -> list[dict]:
   ```

   SPARQL query selects caldav events where `dcterms:modified > bpkm:lastSyncedAt` (or lastSyncedAt not bound):
   - `?event a bpkm:Event`
   - `?event bpkm:externalProvider "caldav"`
   - `?event bpkm:externalId ?extId`
   - `OPTIONAL { ?event bpkm:externalUrl ?extUrl }` — **critical for CalDAV**: this is the PUT URL
   - `OPTIONAL { ?event bpkm:calendarName ?calName }`
   - `OPTIONAL { ?event bpkm:responseStatus ?responseStatus }`
   - `OPTIONAL { ?event bpkm:lastSyncedAt ?lastSynced }`
   - `OPTIONAL { ?event dcterms:modified ?modified }`
   - `FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))`

   Returns list of dicts: `{iri, externalId, externalUrl, calendarName, responseStatus, lastSyncedAt}`

   Reference: Google Calendar's `_find_changed_events()` at `apps/google-calendar/services/sync_engine.py:184` — same pattern but with `externalProvider "google-calendar"` and without `externalUrl`.

2. **Replace `push_sync()` stub** (line 188) with full implementation:

   The pipeline follows Google Calendar's push_sync (line 223 of gcal sync_engine.py) with one key difference: step 6 uses fetch-modify-PUT instead of PATCH.

   ```
   push_timestamp = datetime.now(timezone.utc).isoformat()

   1. Auth check — call get_connection_status(ctx.state). If not connected, store+return skipped result.
   2. Direction check — read sync_direction from state. If "pull-only", store+return skipped result.
   3. Read user_email — from state key "username" (this is the CalDAV account email).
   4. Build CalDAVClient — CalDAVClient(http_client=ctx.http, state_client=ctx.state).
   5. Find changed events — call _find_changed_events(ctx.graph). If empty, store+return ok with 0 pushed.
   6. For each event:
      a. Build event_props dict from SPARQL result (e.g. {BPKM}responseStatus: event["responseStatus"])
      b. Call build_event_patch(event_props, user_email) — if empty, increment skipped, continue
      c. Check event["externalUrl"] — if missing, record error, continue
      d. get_event(externalUrl) → {etag, calendar_data}
      e. modify_vevent_partstat(calendar_data, user_email, patch["responseStatus"])
      f. put_event(externalUrl, modified_ics, etag) — catch CalDAVConflictError → record error with "ETag conflict" message
      g. Update lastSyncedAt via _submit_commands_batched with object.patch command
      h. Increment pushed count
      Wrap each event in try/except Exception for error isolation.
   7. Store last_push_result in state — JSON with status/pushed/skipped/errors/timestamp
   ```

   Import `CalDAVConflictError` from caldav_client module. Import `build_event_patch` and `modify_vevent_partstat` from field_mapper. Import `get_connection_status` from auth module (already imported for pull_sync).

   Remove ALL stub-related comments ("S03", "stub", "not yet implemented").

3. **Extend `MockGraphClient` in test file** to support `changed_events`:

   Add `changed_events: list[dict] | None = None` parameter to `__init__()`. In the `query()` method, add a branch (same pattern as Google Calendar test mock at `backend/tests/test_gcal_sync_engine.py:130`):

   ```python
   # Check _find_changed_events pattern
   elif "responseStatus" in sparql and "STRENDS" not in sparql and self.changed_events:
       bindings = []
       for evt in self.changed_events:
           binding = {"event": {"type": "uri", "value": evt["iri"]},
                      "extId": {"type": "literal", "value": evt["externalId"]}}
           if evt.get("externalUrl"):
               binding["extUrl"] = {"type": "literal", "value": evt["externalUrl"]}
           if evt.get("calendarName"):
               binding["calName"] = {"type": "literal", "value": evt["calendarName"]}
           if evt.get("responseStatus"):
               binding["responseStatus"] = {"type": "literal", "value": evt["responseStatus"]}
           if evt.get("lastSyncedAt"):
               binding["lastSynced"] = {"type": "literal", "value": evt["lastSyncedAt"]}
           bindings.append(binding)
       return {"results": {"bindings": bindings}}
   ```

   Note the `extUrl` key — CalDAV's `_find_changed_events` includes `externalUrl` which Google's doesn't.

4. **Add `_make_push_state()` helper** for constructing valid push test state:

   ```python
   def _make_push_state(sync_direction="bidirectional", username="user@example.com"):
       return {
           "server_url": "https://cal.example.com",
           "username": username,
           "password": "secret",
           "sync_direction": sync_direction,
       }
   ```

5. **Replace `TestPushSyncStub` with real push tests.** Add two test classes:

   **`TestFindChangedEvents`** (~4 tests):
   - `test_finds_changed_events` — graph with 1 changed event, verify returned dict has all keys including externalUrl
   - `test_filters_by_caldav_provider` — verify the SPARQL contains `"caldav"` provider filter
   - `test_empty_when_no_changes` — graph with empty changed_events → empty list
   - `test_missing_optional_fields` — event with only iri/externalId, missing externalUrl/calendarName/responseStatus → returns with None values

   **`TestPushSync`** (~15 tests):
   - `test_not_connected_skips` — empty state → status "skipped", reason "not connected"
   - `test_pull_only_skips` — sync_direction "pull-only" → status "skipped"
   - `test_no_changed_events` — connected but no changes → status "ok", pushed 0
   - `test_successful_rsvp_push` — one event with responseStatus "declined":
     - MockCalDAVHttpClient with 2 responses: GET (200, text=ics_with_attendee, headers={"ETag": '"abc"'}) then PUT (201, headers={"ETag": '"def"'})
     - Verify GET request was made to externalUrl
     - Verify PUT request was made with modified .ics containing new PARTSTAT
     - Result: pushed 1, errors []
   - `test_last_synced_at_updated` — after successful push, verify object.patch command posted with lastSyncedAt
   - `test_error_isolation` — first event fails (GET returns 500), second succeeds → partial status, 1 pushed, 1 error
   - `test_missing_external_url` — event without externalUrl → error recorded, not crash
   - `test_etag_conflict_412` — PUT returns 412 via CalDAVConflictError:
     - Mock GET succeeds, then mock PUT raises CalDAVConflictError
     - Or: mock the CalDAVClient path — since push_sync builds CalDAVClient internally, the test needs MockCalDAVHttpClient to return 412 on PUT. But CalDAVClient.put_event() raises CalDAVConflictError on 412. The test should verify the error is caught and recorded with "conflict" or "412" in the message.
   - `test_empty_patch_skipped` — event with no responseStatus → build_event_patch returns {} → skipped count incremented
   - `test_last_push_result_stored` — after any push, last_push_result in state contains valid JSON with expected fields
   - `test_partial_status_on_mixed` — some pushed, some errors → status "partial"
   - `test_all_errors_status` — all events fail → status "error"

   For tests that need CalDAVClient to make HTTP calls, note that `push_sync()` creates `CalDAVClient(http_client=ctx.http, state_client=ctx.state)` internally. The `ctx.http` is the MockCalDAVHttpClient which captures requests. For the GET→PUT sequence, configure MockCalDAVHttpClient with ordered responses: first GET response (200 with .ics text and ETag header), then PUT response (201 with new ETag).

   For the CalDAVConflictError test: CalDAVClient.put_event() checks `resp.status_code == 412` and raises `CalDAVConflictError`. So configure MockCalDAVHttpClient with: GET response (200), then PUT response (412). The CalDAVClient will raise the error, and push_sync should catch it.

   Use `_build_ics()` helper (already in this test file) to generate test .ics data with attendees.

6. **Update imports** at the top of the test file:
   - Add `_find_changed_events` to the imports from sync_engine module
   - Add `build_event_patch` and `modify_vevent_partstat` to imports from field_mapper module (for type verification in tests if needed)
   - Add `CalDAVConflictError` to imports from caldav_client module (already imported as `CalDAVError`)

## Must-Haves

- [ ] `_find_changed_events()` SPARQL includes externalUrl, externalProvider "caldav", modified>lastSyncedAt filter
- [ ] `push_sync()` implements full GET→modify→PUT cycle with ETag concurrency
- [ ] CalDAVConflictError (412) caught and recorded as error
- [ ] Per-event error isolation — one failure doesn't block subsequent events
- [ ] `last_push_result` stored in state after every push run
- [ ] MockGraphClient extended with `changed_events` support
- [ ] All 196 existing CalDAV tests pass (zero regressions)
- [ ] ~20 new push tests pass
- [ ] Zero stubs remain: `rg "not yet implemented|stub|S03" apps/caldav-calendar/services/sync_engine.py` returns nothing

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && uv run python -m pytest tests/test_caldav_sync_engine.py -v -x` — all pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && uv run python -m pytest tests/test_caldav_*.py --co -q` — 230+ tests collected
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && rg "not yet implemented|stub|S03" apps/caldav-calendar/services/sync_engine.py apps/caldav-calendar/services/field_mapper.py` — zero matches

## Inputs

- `apps/caldav-calendar/services/sync_engine.py` — Contains `push_sync()` stub at line 188, `_find_existing_event()` SPARQL pattern at line 59, `_submit_commands_batched()` at line 158, BPKM namespace
- `apps/caldav-calendar/services/field_mapper.py` — Contains `build_event_patch()` (now real from T01), `modify_vevent_partstat()` (new from T01), `BPKM` constant
- `apps/caldav-calendar/services/caldav_client.py` — `CalDAVClient` with `get_event()` (line 612, returns {etag, calendar_data}), `put_event()` (line 657, accepts url/ics_data/etag, returns new ETag), `CalDAVConflictError` (line 65, raised on 412)
- `apps/caldav-calendar/services/auth.py` — `get_connection_status()` (already imported in sync_engine.py)
- `backend/tests/test_caldav_sync_engine.py` — MockAppContext, MockGraphClient, MockCalDAVHttpClient, MockStateClient, MockResponse, _build_ics() helper, TestPushSyncStub to replace
- T01 output: `build_event_patch()` returns `{"responseStatus": "ACCEPTED"}` etc., `modify_vevent_partstat()` modifies .ics ATTENDEE PARTSTAT
- Reference: `apps/google-calendar/services/sync_engine.py` lines 184-370 — `_find_changed_events()` and `push_sync()` pipeline structure
- Reference: `backend/tests/test_gcal_sync_engine.py` lines 1059-1300 — TestFindChangedEvents and TestPushSync test patterns

## Expected Output

- `apps/caldav-calendar/services/sync_engine.py` — `_find_changed_events()` added, `push_sync()` fully implemented, zero stubs
- `backend/tests/test_caldav_sync_engine.py` — MockGraphClient extended with changed_events, TestPushSyncStub replaced with TestFindChangedEvents (~4 tests) + TestPushSync (~15 tests), all 196 existing + ~20 new pass

## Observability Impact

- **New logger output:** `caldav.sync.engine` logger emits push event counts, per-event errors, and ETag conflict warnings at INFO/WARNING level.
- **State inspection:** `last_push_result` stored in StateClient after every push run — JSON with `status`, `pushed`, `skipped`, `errors` (array of `{event_iri, error}`), `timestamp`. Inspect via `state.get("last_push_result")`.
- **Failure visibility:** CalDAVConflictError (412) is caught and recorded distinctly from generic errors — error message includes "ETag conflict". Per-event error isolation means one failure doesn't mask others in the errors array.
- **Future agent inspection:** To verify push pipeline state, check `last_push_result` in state. To debug a specific push failure, look for the `event_iri` in the errors array and check the error message for conflict vs generic failure.
