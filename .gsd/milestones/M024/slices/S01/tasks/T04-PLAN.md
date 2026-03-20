---
estimated_steps: 6
estimated_files: 4
---

# T04: Person matcher, board selection routes, and connect_status wiring

**Slice:** S01 — Auth + GraphQL client + field mapper + person matcher
**Milestone:** M024

## Description

Complete the slice by implementing the PersonMatcher (SPARQL email lookup → create-on-miss with LRU cache) and wiring the board selection UI into the app routes so the connect_status template shows real boards with save/load persistence. This task also updates app.py to import MondayClient and wire `_render_connect_status()` to call `get_boards()`.

The PersonMatcher follows the exact same pattern as `apps/jira-sync/services/person_matcher.py`. The only difference is Monday.com users have numeric IDs (not UUIDs) and email comes from the `get_users([user_id])` API response.

## Steps

1. **Create `apps/monday-sync/services/person_matcher.py`** — follow `apps/jira-sync/services/person_matcher.py` exactly:
   - `PersonMatcher(graph_client, command_client, monday_client)` — injected dependencies
   - `resolve(user_id, display_name=None, email=None) -> str | None`
     - Step 1: cache hit by user_id (convert to str for cache key)
     - Step 2: SPARQL lookup by email (foaf:mbox or crm:email) if email provided
     - Step 3: If no email, fetch from Monday.com via `monday_client.get_users([user_id])`, extract email and display_name
     - Step 4: SPARQL fallback by user_id (bpkm:externalId)
     - Step 5: Create new Person via command_client on miss
     - Cache the result
   - `_lookup_by_email(email) -> str | None` — SPARQL query with UNION on foaf:mbox and crm:email
   - `_lookup_by_user_id(user_id) -> str | None` — SPARQL query on bpkm:externalId
   - `_create_person(user_id, display_name, email) -> str` — create bpkm:Person via command_client
   - `_slugify(text) -> str` — URL-safe slug (lowercase, replace whitespace, strip non-alnum)

2. **Update `apps/monday-sync/app.py`** — wire MondayClient into routes:
   - Import `MondayClient` from `services.monday_client` (use try/except for importlib compat)
   - Update `_make_client(ctx)` to return a `MondayClient(ctx.http, ctx.state)`
   - Update `_render_connect_status(ctx)` to:
     - Create client via `_make_client(ctx)`
     - Call `get_connection_status(ctx.state, client)` for connection info
     - Call `client.get_boards()` for board list (wrapped in try/except)
     - Read `selected_boards` from settings (JSON list of board IDs)
     - Read sync config: `sync_direction`, `poll_interval`, last sync timestamps
     - Pass all to `connect_status.html` template
   - Verify `save_boards` route reads form checkboxes, saves JSON list of board ID strings to settings

3. **Update `apps/monday-sync/frontend/templates/connect_status.html`** — ensure template renders:
   - Board selection with checkboxes (board name + board ID), with checked state from `selected_boards`
   - Board selection form posts to `/app/monday-sync/_fragments/settings/boards`
   - Sync configuration section (direction radios, interval dropdown) posts to `/app/monday-sync/_fragments/settings/sync-config`
   - Sync Now button posts to `/app/monday-sync/_fragments/settings/sync-now`
   - Sync stats section (last sync time, pull/push results)
   - Disconnect button posts to `/app/monday-sync/_fragments/connect/disconnect`
   - Note: Column mapping UI is deferred to S02 — only board selection in this slice

4. **Write `backend/tests/test_monday_person_matcher.py`** — 20+ tests using importlib loading:
   - `MockGraphClient` — returns canned SPARQL bindings
   - `MockCommandClient` — captures execute calls, returns `{"iri": "..."}`
   - `MockMondayClient` — returns canned user dicts from `get_users()`
   - Test: cache hit (second call returns cached IRI)
   - Test: email match via foaf:mbox
   - Test: email match via crm:email
   - Test: email fetch from Monday.com API when not provided
   - Test: user_id fallback via bpkm:externalId
   - Test: create person on miss (verify slug, title, email property)
   - Test: None user_id returns None
   - Test: Monday.com API failure graceful fallback (still creates person)
   - Test: _slugify various inputs

5. **Run full test suite** — verify all 4 test files pass together:
   - `python -m pytest backend/tests/test_monday_auth.py backend/tests/test_monday_client.py backend/tests/test_monday_field_mapper.py backend/tests/test_monday_person_matcher.py -v`

6. **Final syntax check** — verify all app files parse:
   - `find apps/monday-sync -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \;`

## Must-Haves

- [ ] PersonMatcher with 5-step resolution cascade (cache → email → API fetch → user_id → create)
- [ ] LRU cache per sync run prevents duplicate API calls
- [ ] SPARQL lookup uses UNION on foaf:mbox and crm:email (case-insensitive)
- [ ] Person creation via command_client with bpkm:externalId set
- [ ] app.py routes wired to MondayClient for board fetching
- [ ] connect_status.html shows real board checkboxes with save persistence
- [ ] All htmx URLs prefixed with `/app/monday-sync/`
- [ ] 20+ person matcher tests passing
- [ ] All 150+ tests across 4 test files pass

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_person_matcher.py -v` — 20+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_auth.py backend/tests/test_monday_client.py backend/tests/test_monday_field_mapper.py backend/tests/test_monday_person_matcher.py -v` — all 150+ pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — no syntax errors

## Inputs

- `apps/monday-sync/services/auth.py` — from T01, provides credential management
- `apps/monday-sync/services/monday_client.py` — from T02, provides MondayClient with get_boards(), get_users()
- `apps/monday-sync/services/field_mapper.py` — from T03, not directly used in this task but confirms slice completeness
- `apps/monday-sync/app.py` — from T01, provides route scaffold to update
- `apps/monday-sync/frontend/templates/connect_status.html` — from T01, provides template skeleton to update
- `apps/jira-sync/services/person_matcher.py` — reference implementation for PersonMatcher pattern
- `backend/tests/test_jira_person_matcher.py` — reference for test patterns

## Observability Impact

- **New logger:** `monday_sync.person` (INFO for person creation, WARNING for Monday.com API fetch failures, DEBUG for cache hits and creation params)
- **Inspection:** Call `PersonMatcher.resolve(user_id)` with DEBUG logging to trace the full 5-step cascade (cache → email SPARQL → API fetch → externalId SPARQL → create)
- **Failure visibility:** Monday.com `get_users()` failures logged at WARNING and gracefully handled (falls through to externalId lookup or person creation)
- **Cache state:** `PersonMatcher._cache` dict holds user_id→IRI mappings for the current sync run — inspect via debugger or add DEBUG log
- **No new runtime signals:** PersonMatcher is a pure service with injected clients — no HTTP endpoints or state keys added by this task

## Expected Output

- `apps/monday-sync/services/person_matcher.py` — PersonMatcher with 5-step cascade + cache (~150 lines)
- `apps/monday-sync/app.py` — updated with MondayClient import and board-fetching wiring
- `apps/monday-sync/frontend/templates/connect_status.html` — updated with real board section
- `backend/tests/test_monday_person_matcher.py` — 20+ passing tests (~200 lines)
