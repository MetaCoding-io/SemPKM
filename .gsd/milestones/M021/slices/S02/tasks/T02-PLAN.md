---
estimated_steps: 7
estimated_files: 6
---

# T02: Build sync engine, person matcher, fix sync-token extraction, wire app.py

**Slice:** S02 — Pull Sync + Field Mapping + Person Matching
**Milestone:** M021

## Description

Completes the pull sync pipeline by connecting T01's field mapper to S01's CalDAVClient via a sync engine, adding email-based person matching for attendees/organizer, fixing the sync-token extraction gap in caldav_client.py, and replacing app.py stubs with real sync calls. After this task, the slice demo is true: Sync Now triggers a real pull that creates bpkm:Event objects.

Three new modules: sync_engine.py (~400 lines), person_matcher.py (~140 lines), and two test files (~800 + ~200 lines). One existing module modified: caldav_client.py (sync-token extraction). One existing module rewired: app.py (stubs → real calls).

**Reference implementations:**
- `apps/google-calendar/services/sync_engine.py` (634 lines) — exact pattern to follow for pull_sync
- `apps/google-calendar/services/person_matcher.py` (139 lines) — verbatim clone with logger name change
- `backend/tests/test_gcal_sync_engine.py` (1529 lines) — test patterns for mock clients

**Key constraints from research:**
- Bulk commands must post directly to `/api/commands/bulk` via `ctx.commands._client` (same as Google Calendar D204)
- `get_events()` returns `new_sync_token=None` — must extract root-level `<sync-token>` from multistatus XML
- `_report()` return type must NOT change — add `_report_raw()` for backward compat
- CalDAVError (from S01) can carry status_code — use `status_code == 410` for sync-token expiry detection

## Steps

1. **Fix sync-token extraction in caldav_client.py.** Add module-level function `_extract_sync_token(xml_text: str) -> str | None` that parses the root-level `<d:sync-token>` element from multistatus XML. Add `_report_raw(self, url, body) -> tuple[list[dict], str]` method that returns `(parsed_entries, raw_xml)` — internally it does the same HTTP request as `_report()` but captures `resp.text` before parsing. Specifically: copy the HTTP request logic from `_report()`, save `resp.text`, call `self._handle_response(resp, url, "REPORT")` for entries, return `(entries, resp.text)`. Actually, simpler approach: in `_report_raw`, do the HTTP call, save `raw_text = resp.text`, get `entries = self._handle_response(resp, url, "REPORT")`, return `(entries, raw_text)`. Update `get_events()` to call `_report_raw()` instead of `_report()`, and call `_extract_sync_token(raw_xml)` to get the sync token. Verify: `_report()` is still used by any other callers (discovery methods) and stays unchanged. Run S01 tests to confirm no regressions.

2. **Create `apps/caldav-calendar/services/person_matcher.py`** (~140 lines). Clone from `apps/google-calendar/services/person_matcher.py` — change only the logger name to `caldav.sync.person_matcher`. Same interface: `PersonMatcher.__init__(graph_client, command_client)`, `async match_or_create(email, display_name) -> str | None`, internal `_lookup_by_email` SPARQL query (checking foaf:mbox and crm:email), `_create_person` via commands API, `_slugify` and `_email_local_part` helpers, and in-memory `_cache` dict as LRU. Keep the same SPARQL query patterns and BPKM IRI prefix.

3. **Create `apps/caldav-calendar/services/sync_engine.py`** (~400 lines). Follow Google Calendar sync_engine.py pattern exactly, adapted for CalDAV:
   - Constants: `BPKM` prefix, logger `caldav.sync.engine`
   - `_find_existing_event(graph_client, slug) -> dict | None` — SPARQL SELECT querying bpkm:externalId + bpkm:lastSyncedAt for the slug with externalProvider "caldav"
   - `_build_create_command(slug, properties) -> dict` — object.create command with "caldav" IRI prefix
   - `_build_update_commands(iri, properties, description, attendee_iris, organizer_iri) -> list[dict]` — property.set + body.set + edge.create commands for existing events
   - `_submit_commands_batched(http_client, commands, description, source) -> None` — POST to `/api/commands/bulk` via `ctx.commands._client` (bypasses SDK IRI prefix check per D204)
   - `async push_sync(ctx) -> dict` — stub returning `{"status": "skipped", "reason": "Push sync not yet implemented (S03)"}`
   - `async pull_sync(ctx) -> dict` — the main pipeline:
     1. Auth check via `get_connection_status(ctx.state)`
     2. Read selected calendars from state (JSON list of calendar dicts with href/name)
     3. Build CalDAVClient and PersonMatcher
     4. For each calendar: read per-calendar sync-token from state, call `client.get_events(calendar_href, sync_token)` with 410 retry (catch CalDAVError with status_code 410, clear sync-token, retry with sync_token=None). For each event entry:
        - Skip deleted resources (status containing "404") — these are sync-collection deletions, ignored for now (S03 handles delete sync)
        - Parse `.ics` text with `icalendar.Calendar.from_ical(calendar_data)` and walk VEVENT components
        - Call `build_event_properties(vevent, calendar_name, sync_timestamp, user_email)` from field mapper
        - Call `compute_event_slug(calendar_href, uid)` where UID comes from vevent
        - Look up existing event via `_find_existing_event()`
        - Loop prevention: if existing and `lastSyncedAt >= event modified date`, skip as unchanged
        - For new: build create command, defer body/edges to phase 2
        - For update: build update commands
        - Process attendees via PersonMatcher (exclude self by email match), process organizer
        - Per-event try/except for error isolation
     5. Phase 1: submit create commands via `_submit_commands_batched`
     6. Phase 2: discover IRIs of new events, submit body.set + edge.create
     7. Submit update commands
     8. Store per-calendar sync tokens and result in StateClient

4. **Wire app.py to real sync engine.** Replace the sync_now route stub: import `pull_sync` and `push_sync` from sync_engine, call `pull_sync(ctx)`, store result in state, conditionally call `push_sync(ctx)` if direction is bidirectional. Replace poll_events task: call `pull_sync(ctx)`, optionally `push_sync(ctx)`. Replace push_changes task: call `push_sync(ctx)`. Remove the stub JSON result construction.

5. **Create `backend/tests/test_caldav_person_matcher.py`** (~200 lines). Clone test patterns from `backend/tests/test_gcal_person_matcher.py`. Test cases: email match (SPARQL returns IRI), cache hit (second call skips SPARQL), create-on-miss (SPARQL returns empty, command created), None email (returns None), display name slugification, empty email string.

6. **Create `backend/tests/test_caldav_sync_engine.py`** (~800 lines). Use mock clients (MockStateClient, MockGraphClient, MockHttpClient) matching the established pattern from `test_gcal_sync_engine.py`. Build mock `.ics` text strings for test events using `icalendar.Calendar()` / `icalendar.Event()`. Test categories:
   - **pull_sync guards:** auth not connected → skipped, no calendars selected → ok with 0 counts
   - **New event creation (two-phase):** single new event → create command in phase 1, body.set + edge.create in phase 2. Verify slug, property keys, description handling.
   - **Existing event update:** event exists in graph → update commands with property.set, body.set, edge.create
   - **Loop prevention:** existing event with lastSyncedAt >= event LAST-MODIFIED → unchanged count incremented, no commands
   - **Per-event error isolation:** one event throws exception → error captured in result, other events still processed
   - **Sync-token persistence:** after successful sync, per-calendar sync-token stored in state
   - **410 recovery:** CalDAVError with status_code=410 → clear sync-token, retry with full sync
   - **Deleted resources:** sync-collection entry with status "HTTP/1.1 404" → skipped (not processed)
   - **push_sync stub:** returns skipped result
   - **Route handler tests:** sync_now calls pull_sync, poll_events calls pull_sync, push_changes calls push_sync
   - **Sync-token extraction:** test `_extract_sync_token()` with real multistatus XML containing `<sync-token>` element, and XML without it

7. **Run all tests and verify.** `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py tests/test_caldav_auth.py tests/test_caldav_client.py -v` — all pass, 100+ new tests + 62 S01 tests = 160+ total. Zero regressions.

## Must-Haves

- [ ] `_extract_sync_token()` correctly parses root-level sync-token from multistatus XML
- [ ] `_report_raw()` added — `_report()` unchanged (backward compat, 42 S01 tests pass)
- [ ] `get_events()` returns real sync-token from server responses
- [ ] PersonMatcher with SPARQL email lookup, create-on-miss, LRU cache
- [ ] pull_sync follows two-phase bulk create pattern
- [ ] 410 Gone recovery clears sync-token and retries with full sync
- [ ] Per-event error isolation (one bad event doesn't abort sync)
- [ ] Loop prevention via lastSyncedAt comparison
- [ ] app.py sync_now, poll_events, push_changes wired to real sync functions
- [ ] push_sync returns stub result
- [ ] 40+ new unit tests passing (sync engine + person matcher + sync-token)
- [ ] Zero regressions on all existing CalDAV tests (62 from S01 + T01's field mapper tests)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py -v` — 40+ new tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` — 62 S01 tests pass (no regressions from _report_raw addition)
- `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py -v` — T01 tests still pass
- At least one test proves `_extract_sync_token()` returns a non-None value from valid XML
- At least one test proves 410 recovery flow (CalDAVError with status_code=410 → retry)
- `grep -r "Stub\|stub\|not yet implemented" apps/caldav-calendar/app.py` — only push_sync mentions remain (push is S03's scope)

## Observability Impact

- Signals added: `caldav.sync.engine` logger with per-calendar event counts, sync-token mode (incremental/full), per-event errors; `caldav.sync.person_matcher` logger with email lookups and person creation
- How a future agent inspects this: `last_pull_result` in StateClient contains JSON with status/created/updated/unchanged/errors; `sync_token:{calendar_href}` per-calendar tokens; `last_sync_at` ISO timestamp
- Failure state exposed: per-event errors in result dict `errors` list with event href and error message; 410 recovery logged at INFO level; CalDAVError exceptions propagate with status_code for caller diagnosis

## Inputs

- `apps/caldav-calendar/services/field_mapper.py` — T01 output: `compute_event_slug()`, `build_event_properties()`, `extract_body()`, `extract_attendees()`, `extract_organizer()`
- `apps/caldav-calendar/services/caldav_client.py` — S01 output: CalDAVClient with `get_events()`, CalDAVError with status_code
- `apps/caldav-calendar/services/auth.py` — S01 output: `get_connection_status()`, `get_auth_headers()`
- `apps/caldav-calendar/app.py` — S01 output: stub route/task handlers to replace
- `apps/google-calendar/services/sync_engine.py` — reference pattern for pull_sync, _submit_commands_batched, _find_existing_event
- `apps/google-calendar/services/person_matcher.py` — verbatim clone source
- `backend/tests/test_gcal_sync_engine.py` — reference pattern for mock clients and test structure

## Expected Output

- `apps/caldav-calendar/services/sync_engine.py` — ~400 line module with pull_sync, push_sync stub, helper functions
- `apps/caldav-calendar/services/person_matcher.py` — ~140 line module cloned from Google Calendar
- `apps/caldav-calendar/services/caldav_client.py` — modified: `_extract_sync_token()`, `_report_raw()`, updated `get_events()`
- `apps/caldav-calendar/app.py` — modified: sync_now/poll_events/push_changes wired to real sync functions
- `backend/tests/test_caldav_sync_engine.py` — ~800 line test file with 30+ tests
- `backend/tests/test_caldav_person_matcher.py` — ~200 line test file with 10+ tests
