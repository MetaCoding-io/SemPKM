---
estimated_steps: 8
estimated_files: 5
---

# T02: Build sync engine + person matcher with 52+ unit tests

**Slice:** S02 — Pull Sync + Field Mapping + Recurrence Conversion
**Milestone:** M020

## Description

Wire the field mapper (T01) into a complete pull sync pipeline. Clone person_matcher from Google Calendar (near-identical, ~139 lines). Build sync_engine.py adapting Google's pattern for Outlook delta queries (`@odata.deltaLink` instead of syncToken, `@removed` key for deleted events). Create `requirements.txt` with markdownify. 52+ unit tests covering sync orchestration, error isolation, delta link management, and person matching.

**Clone sources:**
- `apps/google-calendar/services/sync_engine.py` (634 lines) — adapt for Outlook client + delta queries
- `apps/google-calendar/services/person_matcher.py` (139 lines) — near-identical, change logger name
- `backend/tests/test_gcal_sync_engine.py` (1529 lines) — adapt test patterns
- `backend/tests/test_gcal_person_matcher.py` (226 lines) — adapt test patterns

## Steps

1. **Read Google Calendar sync_engine.py** at `apps/google-calendar/services/sync_engine.py` and **person_matcher.py** at `apps/google-calendar/services/person_matcher.py` for the structural patterns. Read the corresponding test files at `backend/tests/test_gcal_sync_engine.py` (first 100 lines for mock patterns) and `backend/tests/test_gcal_person_matcher.py`.

2. **Create `apps/outlook-calendar/services/person_matcher.py`** — Clone from Google Calendar with these changes:
   - Logger name: `"outlook.sync.person_matcher"` (instead of `"google_calendar.person_matcher"`)
   - All other logic identical: `_slugify`, `_email_local_part`, `PersonMatcher` class with `_cache`, `match_or_create`, `_lookup_by_email` (SPARQL with foaf:mbox UNION crm:email), `_create_person` (creates bpkm:Person)
   - Same constants: `_FOAF_MBOX`, `_CRM_EMAIL`, `_BPKM_PERSON_TYPE`

3. **Create `apps/outlook-calendar/services/sync_engine.py`** adapting Google's pattern:

   **Imports:** Use the same try/except import pattern (runtime `from services.X` vs test-time `from X`):
   - `field_mapper`: `build_event_properties`, `build_event_patch`, `compute_event_slug`, `extract_body`, `BPKM`
   - `person_matcher`: `PersonMatcher`
   - `auth`: `get_connection_status`, `refresh_if_expired`
   - `outlook_client`: `OutlookClient`, `OutlookAPIError`

   **Constants:** `BATCH_SIZE = 1000`, logger `"outlook.sync"`

   **`_find_existing_event(graph_client, slug)`** — Same STRENDS pattern as Google but with `externalProvider = "outlook-calendar"`. Returns dict with iri, status, externalId, lastSyncedAt, or None.

   **`_build_create_command(slug, properties)`** — Identical to Google.

   **`_build_update_commands(existing_iri, properties, description, attendee_iris, organizer_iri)`** — Identical to Google.

   **`_submit_commands_batched(http_client, commands, summary, source)`** — Identical to Google.

   **`pull_sync(ctx)`** — Key differences from Google:
   - Uses `OutlookClient` instead of `GCalClient`
   - Delta link key: `delta_link:{calendar_id}` (instead of `sync_token:{calendar_id}`)
   - Calls `client.get_events_delta(calendar_id, delta_link)` which returns `(events, new_delta_link)`
   - Expired delta token: catch `OutlookAPIError` with status_code 410 (or any error), clear the stored delta link, retry with `delta_link=None` for full sync
   - **Deleted events:** Check for `@removed` key in event dict — if present, skip the event (don't create/update). If an existing event is found for that slug, it was already handled by delta query semantics.
   - **Attendee processing:** Outlook attendees are `event["attendees"][i]["emailAddress"]["address"]` and `event["attendees"][i]["emailAddress"]["name"]` (not `.email` / `.displayName` like Google)
   - **Organizer:** `event["organizer"]["emailAddress"]["address"]` and `.name`
   - **Loop prevention:** Same as Google — compare `lastModifiedDateTime` with existing `lastSyncedAt`
   - Store `last_sync_at` and `last_pull_result` in state

   **`push_sync(ctx)`** — Same structure as Google:
   - Check auth + sync_direction
   - `_find_changed_events(graph_client)` — same SPARQL but with `externalProvider = "outlook-calendar"`
   - For each changed event: `build_event_patch` → `OutlookClient.patch_event` → update lastSyncedAt
   - Read `microsoft_email` from state (instead of `google_email`)
   - Store `last_push_result`

   **`_find_changed_events(graph_client)`** — Same SPARQL as Google but with `externalProvider = "outlook-calendar"`.

4. **Create `apps/outlook-calendar/requirements.txt`:**
   ```
   markdownify
   ```

5. **Create `backend/tests/test_outlook_person_matcher.py`** — Clone from `test_gcal_person_matcher.py`:
   - Load from `apps/outlook-calendar/services/person_matcher.py` via importlib
   - 12 tests: `_slugify` (4 cases), `_email_local_part` (2 cases), `PersonMatcher.match_or_create` — cache hit, SPARQL match, create new, None email, empty email, display name fallback

6. **Create `backend/tests/test_outlook_sync_engine.py`** — Adapt from `test_gcal_sync_engine.py`:

   **Module loading:** Load all Outlook service modules in dependency order via importlib:
   1. `field_mapper` (from T01)
   2. `person_matcher`
   3. `outlook_client`
   4. `auth`
   5. `sync_engine`

   **Mock patterns:** Use the same `MockStateClient`, `MockGraphClient`, `MockCommandClient`, `MockHttpClient` pattern from the Google test file. Key adaptation:
   - `MockResponse` must use `data if data is not None else {}` (KNOWLEDGE.md pattern #2)
   - `MockOutlookClient` wraps get_events_delta returning `(events, delta_link)` and patch_event

   **Test categories (40+ tests):**
   - `_find_existing_event` (3 tests): found, not found, correct SPARQL structure with "outlook-calendar"
   - `pull_sync` (25+ tests):
     - Not connected → returns skipped
     - No calendars selected → returns ok with 0 counts
     - New events created (object.create commands submitted)
     - Existing events updated (object.patch commands)
     - **Deleted events** with `@removed` key → skipped, not created
     - Loop prevention: `lastModifiedDateTime <= lastSyncedAt` → unchanged
     - Delta link storage after sync
     - Delta link retrieval for incremental sync
     - **Expired delta token** → OutlookAPIError(410) caught, delta link cleared, full re-sync
     - Per-event error isolation: one bad event doesn't abort sync, error recorded in result
     - Attendee edge creation (bpkm:attendee)
     - Organizer edge creation (bpkm:organizer)
     - Two-phase bulk: create commands in phase 1, body.set/edge.create in phase 2
     - Calendar name passed through to properties
   - `push_sync` (6+ tests):
     - Not connected → skipped
     - Pull-only direction → skipped
     - No changed events → ok with 0 pushed
     - Changed event pushed via patch_event
     - lastSyncedAt updated after push
     - Error during push → captured in errors list
   - `_build_create_command` (2 tests): correct command structure
   - `_submit_commands_batched` (2 tests): single batch, multi-batch at BATCH_SIZE boundary
   - At least one test asserts `last_pull_result` contains `errors` list with event_id and error string (diagnostic surface)
   - At least one test asserts expired delta recovery clears the stored link and retries

7. **Run all Outlook tests together** and iterate until green:
   ```bash
   cd backend && python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short
   ```

8. **Verify total count** is 130+ tests across the three files.

## Must-Haves

- [ ] `person_matcher.py` with SPARQL email lookup, create-on-miss, LRU cache
- [ ] `sync_engine.py` with `pull_sync()` using delta queries, per-event error isolation, two-phase bulk create
- [ ] `sync_engine.py` handles `@removed` key for deleted events in delta responses
- [ ] `sync_engine.py` recovers from expired delta tokens (clears link, full re-sync)
- [ ] `push_sync()` skeleton with RSVP push-back structure ready for S03
- [ ] `requirements.txt` with markdownify
- [ ] 40+ sync engine tests including error isolation and expired delta recovery
- [ ] 12+ person matcher tests
- [ ] Full 130+ test suite (T01 + T02) passes green

## Verification

- `cd backend && python -m pytest tests/test_outlook_sync_engine.py -v` — 40+ tests pass
- `cd backend && python -m pytest tests/test_outlook_person_matcher.py -v` — 12+ tests pass
- `cd backend && python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 130+ total, all green
- `python3 -c "import importlib.util, sys; [exec(open('/dev/null').read()) for _ in [0]]"` — spot check: all three modules import without error via importlib
- At least one sync engine test verifies `last_pull_result` contains error detail for a failed event (diagnostic surface proof)
- At least one test proves expired delta link recovery (410 → clear link → full re-sync succeeds)

## Observability Impact

- Signals added: `outlook.sync` logger — INFO per-calendar event counts and sync result summary; WARNING per-event errors with event_id + exception message
- How a future agent inspects this: read `last_pull_result` / `last_push_result` state keys — JSON with status, created/updated/unchanged counts, errors array, timestamp
- Failure state exposed: per-event errors in `result["errors"]` list; expired delta token auto-recovery logged at INFO; overall sync status `"error"` / `"partial"` / `"ok"` in result

## Inputs

- `apps/outlook-calendar/services/field_mapper.py` — T01 output, provides all field transform functions
- `apps/outlook-calendar/services/auth.py` — S01 output, provides get_connection_status, refresh_if_expired
- `apps/outlook-calendar/services/outlook_client.py` — S01 output, provides OutlookClient, OutlookAPIError
- `apps/google-calendar/services/sync_engine.py` — structural clone source (634 lines)
- `apps/google-calendar/services/person_matcher.py` — near-identical clone source (139 lines)
- `backend/tests/test_gcal_sync_engine.py` — test pattern source (mock patterns, test structure)
- `backend/tests/test_gcal_person_matcher.py` — test pattern source

## Expected Output

- `apps/outlook-calendar/services/person_matcher.py` — Email-based attendee resolution (~140 lines)
- `apps/outlook-calendar/services/sync_engine.py` — Pull + push sync pipeline with delta queries (~650 lines)
- `apps/outlook-calendar/requirements.txt` — markdownify dependency
- `backend/tests/test_outlook_sync_engine.py` — 40+ tests covering all sync paths (~1200-1500 lines)
- `backend/tests/test_outlook_person_matcher.py` — 12+ tests (~220 lines)
