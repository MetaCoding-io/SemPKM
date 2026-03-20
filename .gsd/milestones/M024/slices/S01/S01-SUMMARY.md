---
id: S01
parent: M024
milestone: M024
provides:
  - Complete Monday.com Sync app scaffold with manifest, auth, GraphQL client, configurable field mapper, and person matcher
  - 4 service modules (auth.py, monday_client.py, field_mapper.py, person_matcher.py) with full S02/S03 interfaces
  - App routes for connect/disconnect/board-selection/sync-config/sync-now with task handler stubs
  - Connect form template (API token input) and connect_status template (board checkboxes, sync config, stats)
  - Scoped CSS under .monday-sync-settings
  - 277 passing unit tests across 4 test files
requires: []
affects:
  - S02
  - S03
key_files:
  - apps/monday-sync/manifest.yaml
  - apps/monday-sync/app.py
  - apps/monday-sync/services/auth.py
  - apps/monday-sync/services/monday_client.py
  - apps/monday-sync/services/field_mapper.py
  - apps/monday-sync/services/person_matcher.py
  - apps/monday-sync/frontend/templates/connect.html
  - apps/monday-sync/frontend/templates/connect_status.html
  - apps/monday-sync/frontend/static/styles.css
  - backend/tests/test_monday_auth.py
  - backend/tests/test_monday_client.py
  - backend/tests/test_monday_field_mapper.py
  - backend/tests/test_monday_person_matcher.py
key_decisions:
  - Monday.com uses single API token (not email+token+site like Jira) — stored as `monday_api_token` state key
  - Auth header is bare `Authorization: <api_key>` — no Basic encoding, no Bearer prefix
  - GraphQL queries use inline string interpolation (not GraphQL variables) because Monday.com expects integer board IDs directly in queries
  - Complexity error detection uses dual check — extensions.code == "COMPLEXITY" OR message contains "complexity" — handles both documented and undocumented error formats
  - build_task_properties returns (props, assignee_user_id) tuple — raw person ID separated for async PersonMatcher resolution
  - Column mapping is fully configurable via dict parameter (not hardcoded) — core differentiator from Jira/GitHub/Linear mappers
  - Monday.com user_id (numeric) stored as string for SPARQL bpkm:externalId compatibility
patterns_established:
  - Single-token auth pattern: store_credentials(state, token), verify via GraphQL `{ me { id name email } }`, masked token display
  - MondayClient._execute_query() single HTTP gateway — all 10 convenience methods delegate to it (LinearClient pattern)
  - Configurable column mapping: build_task_properties accepts column_mapping dict keyed by bpkm property names mapped to Monday.com column IDs
  - Column value extraction: _parse_col_value normalizes JSON string / dict / None, then type-specific extractors handle parsed shape
  - PersonMatcher 5-step cascade: cache → email SPARQL → API fetch → externalId SPARQL → create person
observability_surfaces:
  - monday_sync.auth logger (INFO on store/clear/verify, WARNING on verify failures)
  - monday_sync.client logger (DEBUG complexity budget per query, standard error logging)
  - monday_sync.person logger (DEBUG cache hits/creation, WARNING API fetch failures)
  - get_connection_status() returns structured dict with connected/display_name/email/token_preview/error
  - MondayApiError hierarchy carries status_code + response_body; MondayComplexityError.reset_in_seconds for retry timing
drill_down_paths:
  - .gsd/milestones/M024/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M024/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M024/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M024/slices/S01/tasks/T04-SUMMARY.md
duration: 71m
verification_result: passed
completed_at: 2026-03-19
---

# S01: Auth + GraphQL client + field mapper + person matcher

**Complete Monday.com Sync app scaffold with auth credential lifecycle, GraphQL client (10 methods, complexity tracking, 4-class error hierarchy), configurable field mapper (9 column-type extractors with reverse mapping), and person matcher (5-step resolution cascade) — all proven by 277 offline unit tests.**

## What Happened

Built the full `apps/monday-sync/` directory from scratch across 4 tasks, following established sync app patterns (Jira, Linear, GitHub) while adapting for Monday.com's unique characteristics.

**T01 (Auth + scaffold)** created the app directory structure, manifest, auth module, connect/disconnect routes, templates, and scoped CSS. Monday.com auth is simpler than Jira — a single API token instead of email+token+site. The auth header is a bare `Authorization: <api_key>` (no Basic/Bearer prefix). The connect_status template already includes board selection checkboxes, sync direction/interval configuration, sync-now button, and sync stats display. 31 tests.

**T02 (GraphQL client)** built MondayClient with 10 convenience methods (`get_me`, `get_boards`, `get_board_columns`, `get_board_groups`, `get_board_items`, `get_users`, `get_tags`, `change_multiple_column_values`, `create_item`, plus `get_all_board_items` paginated wrapper). The client tracks Monday.com's complexity budget per query response, handles cursor-based pagination with a MAX_PAGINATION_PAGES=50 safety limit, and implements a 4-class error hierarchy: MondayApiError (base), MondayAuthError (401), MondayRateLimitError (429 with retry_after), MondayComplexityError (200 with complexity budget exceeded, carries reset_in_seconds). 64 tests.

**T03 (Field mapper)** implemented the configurable field mapper — the core differentiator from other sync apps. Monday.com's fully customizable columns mean the mapper can't use hardcoded field positions. Instead, `build_task_properties()` accepts a `column_mapping` dict parameter mapping bpkm property names to Monday.com column IDs. Nine column-type extractors handle status, priority, date, people, text, long_text, numbers, tags, and dropdown columns. `build_reverse_column_values()` handles the read/write format asymmetry (e.g., status reads as `{label, index}` but writes as `{label: "Done"}`). `compute_slug()` generates deterministic `monday-{sha256[:16]}` IRIs. 155 tests.

**T04 (Person matcher)** created PersonMatcher with a 5-step resolution cascade: in-memory LRU cache → SPARQL email lookup (foaf:mbox/crm:email UNION) → Monday.com API fetch → SPARQL externalId fallback → create new Person. Adapted for Monday.com's numeric user IDs (stored as strings for SPARQL compatibility). The app.py routes and connect_status template were already fully wired from T01, requiring no additional changes. 27 tests.

## Verification

- **277 unit tests pass** across 4 test files (31 auth + 64 client + 155 field mapper + 27 person matcher) in 0.25s
- All 6 Python source files pass `ast.parse()` syntax validation
- All 11 expected files exist in `apps/monday-sync/` (manifest, requirements, 4 services, app.py, 2 templates, CSS)
- Test counts exceed plan minimums: auth 31/20+, client 64/50+, field_mapper 155/50+, person_matcher 27/20+, total 277/150+

## Requirements Advanced

- MON-01 (auth) — API token storage, verification via `me` query, masked display, connection status dict fully implemented and tested
- MON-02 (board discovery) — `get_boards()` and `get_board_columns()` client methods implemented with board selection UI in connect_status template
- MON-13 (person matching) — PersonMatcher with email SPARQL lookup, create-on-miss, LRU cache fully implemented and tested

## Requirements Validated

- none — requirements stay active until runtime integration proves them in S02+

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Field mapper has 9 column-type extractors instead of the planned 8 — priority extraction was separated from status extraction because missing priority should return None (omit) while missing status defaults to "todo"
- `build_task_properties` returns `(props, assignee_user_id)` tuple instead of embedding user_id in the props dict — cleaner separation for async PersonMatcher resolution
- T04 required no app.py or template changes — T01 had already wired everything including MondayClient import, board fetching, sync config routes, and the complete connect_status template

## Known Limitations

- Column mapping configuration UI not yet built (S02 deliverable) — board columns are discovered via `get_board_columns()` but there's no UI for mapping them to bpkm properties
- Pull sync engine not implemented (S02 deliverable) — field mapper functions exist but aren't wired to actual sync orchestration
- Push sync not implemented (S03 deliverable) — `change_multiple_column_values()` and `build_reverse_column_values()` exist but aren't used yet
- Task handler stubs (`poll-tasks`, `push-changes`) return placeholder responses — need S02/S03 to implement actual sync logic

## Follow-ups

- none — all planned work completed within scope

## Files Created/Modified

- `apps/monday-sync/manifest.yaml` — App manifest with appId, permissions, tasks, UI page, network: ["api.monday.com"]
- `apps/monday-sync/requirements.txt` — Empty dependencies file (SDK provides core deps)
- `apps/monday-sync/services/__init__.py` — Empty package init
- `apps/monday-sync/services/auth.py` — Auth helpers: store/get/clear/verify/status + _mask_token (~100 lines)
- `apps/monday-sync/services/monday_client.py` — GraphQL client with error hierarchy, complexity tracking, 10 convenience methods (~330 lines)
- `apps/monday-sync/services/field_mapper.py` — Configurable field mapper with 9 extractors, build/reverse functions, compute_slug (~340 lines)
- `apps/monday-sync/services/person_matcher.py` — PersonMatcher with 5-step cascade, LRU cache, SPARQL lookup (~150 lines)
- `apps/monday-sync/app.py` — Route handlers (connect/disconnect/boards/sync-config/sync-now) and task stubs (~250 lines)
- `apps/monday-sync/frontend/templates/connect.html` — API token input form with htmx POST
- `apps/monday-sync/frontend/templates/connect_status.html` — Connected state with board checkboxes, sync config, stats, disconnect
- `apps/monday-sync/frontend/static/styles.css` — Scoped CSS under .monday-sync-settings
- `backend/tests/test_monday_auth.py` — 31 auth tests
- `backend/tests/test_monday_client.py` — 64 client tests
- `backend/tests/test_monday_field_mapper.py` — 155 field mapper tests
- `backend/tests/test_monday_person_matcher.py` — 27 person matcher tests

## Forward Intelligence

### What the next slice should know
- The field mapper is fully configurable — S02 needs to build the UI that lets users create the `column_mapping` dict that `build_task_properties()` consumes. The dict format is `{"taskStatus": "status_col_id", "priority": "priority_col_id", "dueDate": "date_col_id"}` mapping bpkm property short names to Monday.com column IDs.
- `get_board_columns(board_id)` returns column metadata including `id`, `title`, and `type` — the UI should use `type` to filter which bpkm properties are valid mapping targets for each column.
- Status and priority label mappings (`status_label_mapping`, `priority_label_mapping`) are separate dicts passed to `build_task_properties()`. S02 needs UI for mapping Monday.com custom labels (e.g., "Working on it") to bpkm enum values (e.g., "in-progress").
- The connect_status template already has board selection UI and sync config controls wired — S02 adds column mapping UI as a new section/page.

### What's fragile
- Complexity error detection relies on string matching ("complexity" in message) as fallback — if Monday.com changes their error message format, this could miss complexity errors. The primary check via `extensions.code == "COMPLEXITY"` is more stable.
- Monday.com column value JSON shapes vary by column type and API version — the 9 extractors handle known shapes but new column types or format changes could produce None silently.

### Authoritative diagnostics
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py -v` — 277 tests, authoritative contract verification for all 4 service modules
- `get_connection_status()` return dict — the single source of truth for UI rendering of connection state

### What assumptions changed
- T04 assumed app.py and connect_status.html would need updates for board selection wiring — T01 had already built everything, so T04 only needed person_matcher.py and its tests.
