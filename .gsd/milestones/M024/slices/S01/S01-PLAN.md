# S01: Auth + GraphQL client + field mapper + person matcher

**Goal:** Create a fully scaffolded Monday.com Sync app with auth, GraphQL client, configurable field mapper, and person matcher — all proven by 150+ offline unit tests.
**Demo:** User can install Monday.com Sync, enter an API token, verify connection (showing their username), select boards to sync, and see discovered columns. All 6 service modules exist. 150+ unit tests prove auth, client pagination/complexity tracking, field mapper configurable transforms, and person matcher email resolution.

## Must-Haves

- App scaffold: `apps/monday-sync/` with manifest.yaml, requirements.txt, services/ package, templates, CSS
- Auth module: store/get/clear API token via StateClient, verify connection via `me` query, masked token display, connection status dict
- GraphQL client: `MondayClient` with `get_boards()`, `get_board_columns(board_id)`, `get_board_groups(board_id)`, `get_board_items(board_id, limit, cursor)`, `get_users(user_ids)`, `get_tags(tag_ids)`, `change_multiple_column_values(board_id, item_id, column_values_json)`, `create_item(board_id, group_id, name, column_values_json)`. Complexity tracking via query response. Cursor-based pagination. Error hierarchy: `MondayApiError`, `MondayAuthError`, `MondayRateLimitError`, `MondayComplexityError`.
- Field mapper: `build_task_properties(item, column_mapping, status_label_mapping, priority_label_mapping)` pure function that reads column values using user's stored mapping config. `build_reverse_column_values(task_properties, column_mapping, reverse_status_mapping, reverse_priority_mapping)` for push. `compute_slug(item_name, item_id)` for deterministic IRI slugs.
- Person matcher: `PersonMatcher` with `resolve_person(user_id, monday_client)` doing SPARQL email lookup → create-on-miss, LRU cache
- App routes: connect fragment, connect/credentials (POST), disconnect (POST), board selection save (POST), task handler stubs for poll-tasks and push-changes
- Connect form template: API token input
- Connect status template: connected state with board selection checkboxes (column mapping UI deferred to S02)
- Scoped CSS under `.monday-sync-settings`
- 150+ unit tests across test_monday_auth.py, test_monday_client.py, test_monday_field_mapper.py, test_monday_person_matcher.py

## Proof Level

- This slice proves: contract
- Real runtime required: no (all tests use importlib loading and mocks)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_auth.py -v` — 20+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_client.py -v` — 50+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_field_mapper.py -v` — 50+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_person_matcher.py -v` — 20+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_auth.py backend/tests/test_monday_client.py backend/tests/test_monday_field_mapper.py backend/tests/test_monday_person_matcher.py -v` — all 150+ pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — no syntax errors
- All app files pass Python syntax check

## Observability / Diagnostics

- Runtime signals: `monday_sync.auth` / `monday_sync.client` / `monday_sync.person` loggers with INFO and WARNING levels for connection state changes, API errors, and person creation
- Inspection surfaces: `get_connection_status()` returns dict with connected/error/display_name for UI display; complexity budget tracked per query response
- Failure visibility: `MondayApiError` hierarchy with status_code and response_body; `MondayComplexityError` with reset_in_seconds; auth errors surface in connection status dict
- Redaction constraints: API tokens masked to first4+****+last4 in connection status; never logged raw

## Integration Closure

- Upstream surfaces consumed: `sempkm-app-sdk` (App, AppContext, StateClient, HttpClient, CommandClient, render_template); `starlette` (Request, HTMLResponse)
- New wiring introduced in this slice: `apps/monday-sync/` directory with manifest.yaml discovered by app platform on install; route handlers registered via `@jira_sync_app.route`; task handlers via `@jira_sync_app.task`
- What remains before the milestone is truly usable end-to-end: S02 (column mapping UI + pull sync), S03 (push sync + LoopGuard + dependencies), S04 (E2E + docs)

## Tasks

- [x] **T01: App scaffold, auth module, connect UI, and auth tests** `est:1h30m`
  - Why: Creates the complete app directory structure and auth pipeline — the foundation every other task builds on. Without auth, no API calls are possible.
  - Files: `apps/monday-sync/manifest.yaml`, `apps/monday-sync/requirements.txt`, `apps/monday-sync/services/__init__.py`, `apps/monday-sync/services/auth.py`, `apps/monday-sync/app.py`, `apps/monday-sync/frontend/templates/connect.html`, `apps/monday-sync/frontend/templates/connect_status.html`, `apps/monday-sync/frontend/static/styles.css`, `backend/tests/test_monday_auth.py`
  - Do: Follow the Jira Sync app structure exactly. Monday.com uses a single API token (not email+token+site like Jira). The auth header is `Authorization: <api_key>` (no Basic encoding, no Bearer prefix). Verify connection via GraphQL `{ me { id name email } }` query. The connect_status template should show board checkboxes (loaded from S02's client.get_boards() but stubbed for now in the template). App.py should have connect/disconnect routes + task handler stubs.
  - Verify: `python -m pytest backend/tests/test_monday_auth.py -v` — 20+ tests pass covering store/get/clear credentials, verify connection, mask token, connection status connected/disconnected/error states
  - Done when: `apps/monday-sync/` directory has all scaffold files, auth module has complete credential lifecycle, 20+ auth tests pass

- [x] **T02: Monday.com GraphQL client with complexity tracking and error hierarchy** `est:2h`
  - Why: The GraphQL client is the most novel piece — Monday.com's complexity budget system and column-value-specific mutation format are unique to this provider. All later sync work depends on a correct client.
  - Files: `apps/monday-sync/services/monday_client.py`, `backend/tests/test_monday_client.py`
  - Do: Model after LinearClient but with Monday.com-specific adaptations: (1) API endpoint is `https://api.monday.com/v2` (override via `MONDAY_API_URL` env var for testing). (2) Auth header is `Authorization: <api_key>` (bare token, no Bearer). (3) Complexity tracking: Monday.com returns `{ "data": {...}, "complexity": {"after": N, "reset_in_x_seconds": M} }` — track remaining budget and raise `MondayComplexityError` when `after` drops to 0 or the response contains a complexity error. (4) Cursor-based pagination for items via `items_page(limit, cursor)`. (5) Error hierarchy: `MondayApiError` (base), `MondayAuthError` (401), `MondayRateLimitError` (429), `MondayComplexityError` (complexity budget exceeded — returned as 200 with error in response body). (6) Convenience methods: `get_boards()`, `get_board_columns(board_id)`, `get_board_groups(board_id)`, `get_board_items(board_id, limit, cursor)`, `get_users(user_ids)`, `get_tags(tag_ids)`, `change_multiple_column_values(board_id, item_id, column_values_json)`, `create_item(board_id, group_id, name, column_values_json)`, `get_me()`. (7) All GraphQL queries should be inline strings, not external files.
  - Verify: `python -m pytest backend/tests/test_monday_client.py -v` — 50+ tests covering: auth header construction, get_me, get_boards, get_board_columns, get_board_groups, get_board_items pagination, get_users, get_tags, change_multiple_column_values, create_item, 401→MondayAuthError, 429→MondayRateLimitError, complexity error→MondayComplexityError, GraphQL errors, MONDAY_API_URL env override
  - Done when: MondayClient with all 10 convenience methods, complexity tracking, 4-class error hierarchy, and 50+ passing tests

- [x] **T03: Configurable field mapper with per-column-type transforms and reverse mapping** `est:1h30m`
  - Why: Monday.com's fully customizable columns mean the mapper can't use hardcoded field positions like Jira/GitHub. The mapper must read from a user-provided column_mapping dict to know which Monday.com column maps to which bpkm property. This is the core data transformation engine.
  - Files: `apps/monday-sync/services/field_mapper.py`, `backend/tests/test_monday_field_mapper.py`
  - Do: (1) `build_task_properties(item, column_mapping, status_label_mapping, priority_label_mapping)` — takes a Monday.com item dict and the user's stored column mapping config. The `column_mapping` dict maps bpkm property names to Monday.com column IDs (e.g. `{"taskStatus": "status_col_id", "priority": "priority_col_id", "dueDate": "date_col_id"}`). For each mapped property, extract the column value from the item's `column_values` array (matched by `id`), then parse the column-type-specific JSON value. Column type handlers: `status` (read `label` field, map via status_label_mapping), `date` (read `date` field), `people` (read `personsAndTeams[0].id`), `text`/`long_text` (read `text` or `value` field), `numbers` (read `value`), `tags` (read `tag_ids`), `dropdown` (read `labels`). (2) `build_reverse_column_values(task_properties, column_mapping, reverse_status_mapping, reverse_priority_mapping)` — build the JSON dict for `change_multiple_column_values` mutation. The write format differs per column type (e.g., status writes `{"label": "Done"}`, date writes `{"date": "2025-01-15"}`, people writes `{"personsAndTeams": [{"id": 123, "kind": "person"}]}`). (3) `compute_slug(item_name, item_id)` — deterministic slug `monday-{sha256[:16]}`. (4) Standard status/priority default maps and reverse maps for when no user mapping is provided.
  - Verify: `python -m pytest backend/tests/test_monday_field_mapper.py -v` — 50+ tests covering: each column type extraction (status, date, people, text, long_text, numbers, tags, dropdown), status label mapping, priority label mapping, missing column graceful handling, empty column values, reverse mapping per column type, compute_slug determinism, build_task_properties with full item, build_reverse_column_values round-trip
  - Done when: field_mapper.py has build_task_properties, build_reverse_column_values, compute_slug with 8+ column type handlers, and 50+ passing tests

- [x] **T04: Person matcher, board selection routes, and connect_status wiring** `est:1h`
  - Why: Completes the slice by adding person resolution (SPARQL email lookup → create-on-miss) and wiring the board selection UI into the app routes so users can pick which boards to sync.
  - Files: `apps/monday-sync/services/person_matcher.py`, `apps/monday-sync/app.py` (update), `apps/monday-sync/frontend/templates/connect_status.html` (update), `backend/tests/test_monday_person_matcher.py`
  - Do: (1) PersonMatcher follows the exact same pattern as `apps/jira-sync/services/person_matcher.py` — SPARQL lookup by email (foaf:mbox or crm:email), fallback by Monday.com user_id (bpkm:externalId), create Person on miss, LRU cache per sync run. The key difference: Monday.com users have a numeric `id` (not UUID), and email comes from the `get_users([user_id])` response. (2) Update app.py: add `/_fragments/settings/boards` POST route that saves selected board IDs to settings as JSON; update `_render_connect_status()` to load boards via MondayClient.get_boards() and pass to template; add sync-config and sync-now stub routes. (3) Update connect_status.html: add board checkbox list section showing fetched boards with selection persistence, sync config section with direction/interval, disconnect button. Use `/app/monday-sync/` prefix on all htmx URLs per KNOWLEDGE.md pattern.
  - Verify: `python -m pytest backend/tests/test_monday_person_matcher.py -v` — 20+ tests covering: cache hit, email match, user_id fallback, create person, None account_id returns None, API fetch failure graceful handling
  - Done when: PersonMatcher with email+id lookup+cache+creation, board selection wired into app routes and template, all 150+ tests across 4 test files pass

## Files Likely Touched

- `apps/monday-sync/manifest.yaml`
- `apps/monday-sync/requirements.txt`
- `apps/monday-sync/app.py`
- `apps/monday-sync/services/__init__.py`
- `apps/monday-sync/services/auth.py`
- `apps/monday-sync/services/monday_client.py`
- `apps/monday-sync/services/field_mapper.py`
- `apps/monday-sync/services/person_matcher.py`
- `apps/monday-sync/frontend/templates/connect.html`
- `apps/monday-sync/frontend/templates/connect_status.html`
- `apps/monday-sync/frontend/static/styles.css`
- `backend/tests/test_monday_auth.py`
- `backend/tests/test_monday_client.py`
- `backend/tests/test_monday_field_mapper.py`
- `backend/tests/test_monday_person_matcher.py`
