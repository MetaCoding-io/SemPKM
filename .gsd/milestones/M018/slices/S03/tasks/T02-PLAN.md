---
estimated_steps: 7
estimated_files: 5
---

# T02: Build person matcher, extend GCalClient with get_events, and build sync engine with tests

**Slice:** S03 — Pull sync + field mapping + settings
**Milestone:** M018

## Description

Build the three remaining service modules that together form the pull sync pipeline: person matcher (email → Person resolution), GCalClient events endpoint (syncToken-based incremental fetch), and sync engine (orchestration of the full pull cycle). This is the async integration layer that wires T01's pure field mapper into the platform's command and graph APIs.

The person matcher is nearly identical to linear-sync's — copy and adapt the logger name. The GCalClient extension adds `get_events()` with syncToken pagination and 410 Gone handling. The sync engine follows the exact two-phase bulk create pattern from linear-sync/github-sync.

## Steps

1. **Create `apps/google-calendar/services/person_matcher.py`** — copy from `apps/linear-sync/services/person_matcher.py` and change:
   - Logger name: `"google_calendar.person_matcher"` (was `"linear_sync.person_matcher"`)
   - Everything else stays identical: `PersonMatcher` class with `match_or_create()`, SPARQL email lookup via `foaf:mbox` and `crm:email`, creation on miss with slugified name, LRU cache per instance.

2. **Add `get_events()` to `apps/google-calendar/services/gcal_client.py`**:
   ```python
   async def get_events(
       self,
       calendar_id: str,
       sync_token: str | None = None,
       max_results: int = 250,
   ) -> tuple[list[dict], str | None]:
   ```
   - Builds URL: `{GCAL_BASE_URL}/calendars/{calendar_id}/events`
   - Query params: `maxResults={max_results}`, `singleEvents=false` (get master recurring events, not expanded instances)
   - If `sync_token` is provided, add `syncToken={sync_token}` to params
   - If no sync_token, add `timeMin` to limit scope (e.g., 90 days ago in RFC 3339 format) to avoid pulling entire history
   - Paginates via `nextPageToken` (same loop as `get_calendar_list()`)
   - Returns `(events_list, next_sync_token)` where `next_sync_token` is from the final page's `nextSyncToken`
   - **410 Gone handling:** If `_request()` raises `GCalAPIError` with `status_code == 410`, let it propagate — the sync engine handles the retry logic (clears syncToken, retries as full sync).
   - URL construction: build query string with `?` + `&`.join() pattern for all params.

3. **Create `apps/google-calendar/services/sync_engine.py`** following the linear-sync/github-sync pattern:
   - Imports via try/except pattern (same as linear-sync: try `from services.X` first, fall back to `from X`).
   - Logger: `"google_calendar.sync"`
   - `BATCH_SIZE = 1000`

   Core functions:
   - `async def _find_existing_event(graph_client, slug: str) -> dict | None` — SPARQL query for `bpkm:Event` with `externalProvider = "google-calendar"` and `STRENDS(STR(?event), "/Event/{slug}")`. Return `{iri, status, externalId, lastSyncedAt}` or None.
   - `def _build_create_command(slug: str, properties: dict) -> dict` — build `{"type": "object.create", "params": {"type": "urn:sempkm:model:basic-pkm:Event", "slug": slug, "properties": properties}}`.
   - `def _build_update_commands(existing_iri: str, properties: dict, description: str | None, attendee_iris: list[str], organizer_iri: str | None) -> list[dict]` — build a list of commands: `property.set` for each changed property, `body.set` if description present, `edge.create` for each attendee and organizer.
   - `async def _submit_commands_batched(http_client, commands: list[dict], summary: str, source: str) -> dict` — POST to `/api/commands/bulk` in BATCH_SIZE chunks. Use `http_client.post()` directly (bypass SDK CommandClient which enforces IRI prefix checks). The http_client is `ctx.commands._client` (internal httpx client with auth headers).
   - `async def pull_sync(ctx: AppContext) -> dict` — the main orchestration function:
     1. Read `selected_calendars` from state (JSON string → list)
     2. If empty, return `{"status": "ok", "message": "No calendars selected", "created": 0, "updated": 0}`
     3. Get valid access token via `refresh_if_expired()`
     4. Create `GCalClient` and `PersonMatcher` instances
     5. For each calendar_id in selected_calendars:
        a. Read `sync_token:{calendar_id}` from state
        b. Call `client.get_events(calendar_id, sync_token=sync_token)`
        c. If 410 GCalAPIError: clear syncToken from state, retry with `sync_token=None`
        d. For each event in results:
           - Compute slug via `compute_event_slug(calendar_id, event["id"])`
           - Check existing via `_find_existing_event()`
           - Build properties via `build_event_properties()`
           - Extract body via `extract_body()`
           - Process attendees: for each attendee (not self), call `person_matcher.match_or_create(email, displayName)` → collect IRIs
           - Process organizer: call `person_matcher.match_or_create(organizer_email, organizer_displayName)` → IRI
           - If new: add create command, track for phase 2 (body + edges)
           - If existing: add update commands (property patches + body + edges)
           - Wrap each event in try/except for per-event error isolation
        e. Phase 1: submit create commands in batch
        f. Phase 2: SPARQL-discover created IRIs by slug, submit body.set + edge.create commands
        g. Submit update commands in batch
        h. Store `sync_token:{calendar_id}` from response
     6. Store `last_sync_at` timestamp
     7. Store result summary as `last_pull_result` JSON in state
     8. Return `{"status": "ok", "created": N, "updated": N, "unchanged": N, "errors": [...]}`

   **Key constraints:**
   - Use `ctx.commands._client` for bulk POST (same pattern as linear-sync — bypasses SDK IRI prefix checks)
   - `externalProvider` must be `"google-calendar"`
   - `singleEvents=false` on events.list query
   - Per-event error isolation: wrap each event processing in try/except, collect errors, continue
   - Attendee and organizer are ObjectProperties → stored as `edge.create` commands to Person IRIs with predicates `{BPKM}attendee` and `{BPKM}organizer`, not as string properties
   - `push-changes` handler stays as placeholder — S04 scope

4. **Create `backend/tests/test_gcal_person_matcher.py`** — ≥8 tests using importlib loading. Test:
   - Email match found in SPARQL (cache miss → lookup → found)
   - No match → person created with slugified name
   - Cache hit (second call for same email returns cached IRI without query)
   - None email returns None
   - Empty email returns None
   - Display name used for slug when available
   - Email local part used for slug when no display name
   - Case-insensitive cache key

5. **Create `backend/tests/test_gcal_sync_engine.py`** — ≥30 tests using importlib loading. Module loading order: field_mapper → person_matcher → gcal_client → auth → sync_engine (dependency order). Mock classes:
   - `MockStateClient` — dict-backed async get/set
   - `MockGraphClient` — programmable async query returning canned SPARQL results
   - `MockHttpClient` — tracks POST calls, returns canned responses
   - `MockGCalClient` — returns canned event lists and sync tokens
   - `MockAppContext` — wires all mock clients together with `.state`, `.graph`, `.http`, `.commands._client` attributes

   Test classes covering:
   - `TestFindExistingEvent` — found, not found, empty bindings (~3 tests)
   - `TestBuildCreateCommand` — correct type IRI, slug, properties (~2 tests)
   - `TestBuildUpdateCommands` — property.set, body.set, edge.create for attendees/organizer (~3 tests)
   - `TestSubmitCommandsBatched` — single batch, multi-batch (>1000), empty commands (~3 tests)
   - `TestPullSync` — full pipeline with new events (creates), existing events (updates), mixed, empty calendar, no calendars selected, syncToken persistence, 410 Gone retry, per-event error isolation, attendee matching, organizer matching, multiple calendars, all-day events, events with conferenceData, events with recurrence (~15+ tests)

   **MockResponse pitfall:** Use `data if data is not None else {}` not `data or {}` (Knowledge Pattern #2).

6. **Run all tests:**
   - `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v`
   - `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v`
   - `cd backend && .venv/bin/python -m pytest -x` — full suite, zero regressions

## Must-Haves

- [ ] `person_matcher.py` has `PersonMatcher` class with `match_or_create()` using SPARQL email lookup + creation + LRU cache
- [ ] `GCalClient.get_events()` supports syncToken, pagination, and `singleEvents=false`
- [ ] `sync_engine.py` has `pull_sync(ctx)` with two-phase bulk create, per-calendar iteration, syncToken persistence, per-event error isolation
- [ ] `_find_existing_event()` queries for `bpkm:Event` with `externalProvider = "google-calendar"`
- [ ] Attendee/organizer stored as `edge.create` commands (ObjectProperty), not string properties
- [ ] Commands bypass SDK CommandClient via direct `/api/commands/bulk` POST
- [ ] ≥8 person matcher tests pass
- [ ] ≥30 sync engine tests pass
- [ ] Full backend suite passes with zero regressions

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` — ≥8 tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` — ≥30 tests pass
- `cd backend && .venv/bin/python -m pytest -x` — full suite passes

## Observability Impact

- Signals added: `google_calendar.sync` logger — INFO per calendar (events fetched count, created/updated/unchanged counts), WARNING on per-event errors with event_id context, INFO on syncToken state (fresh/incremental/410-reset)
- `google_calendar.person_matcher` logger — DEBUG on cache hits/misses, DEBUG on person creation
- How a future agent inspects: `pull_sync()` return dict has `{status, created, updated, unchanged, errors}` — errors array includes `{event_id, error}` for diagnosis
- Failure state exposed: Per-event errors captured in result; syncToken preserved on partial success so next sync resumes correctly

## Inputs

- `apps/google-calendar/services/field_mapper.py` — T01 output (build_event_properties, compute_event_slug, extract_body, BPKM constant)
- `apps/google-calendar/services/gcal_client.py` — S02 output (GCalClient base, _request(), GCalAPIError)
- `apps/google-calendar/services/auth.py` — S02 output (refresh_if_expired, get_connection_status)
- `apps/linear-sync/services/person_matcher.py` — reference implementation to copy
- `apps/linear-sync/services/sync_engine.py` — reference for two-phase bulk create, _find_existing_task, _submit_commands_batched patterns
- `backend/tests/test_github_sync_engine.py` — reference for importlib loading order and mock patterns

## Expected Output

- `apps/google-calendar/services/person_matcher.py` — ~140 lines (copy+adapt from linear-sync)
- `apps/google-calendar/services/gcal_client.py` — extended with `get_events()` method (~60 new lines)
- `apps/google-calendar/services/sync_engine.py` — ~350 lines, pull sync orchestration
- `backend/tests/test_gcal_person_matcher.py` — ~200 lines, ≥8 tests
- `backend/tests/test_gcal_sync_engine.py` — ~700 lines, ≥30 tests
