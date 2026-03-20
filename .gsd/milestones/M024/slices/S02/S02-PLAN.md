# S02: Column mapping configuration UI + pull sync

**Goal:** User configures which Monday.com columns map to which bpkm properties via type-filtered dropdowns, maps custom status/priority labels to bpkm enum values, and triggers sync. Monday.com items appear as correctly-mapped bpkm:Task objects with groups as taskGroup and subitems linked via parentTask.

**Demo:** In the Monday.com Sync settings, user clicks "Configure Columns" for a selected board. A form shows type-filtered dropdown menus — each bpkm property (Status, Priority, Due Date, Assignee, etc.) paired with compatible Monday.com columns. User saves, then configures label mappings (Monday.com status label → bpkm taskStatus). User clicks "Sync Now" and sees Monday.com items appear as bpkm:Task objects with correct property values. Items from different Monday.com groups have distinct `taskGroup` values. Subitems are linked to parents via `parentTask`.

## Must-Haves

- Column mapping configuration routes: `configure-columns` GET, `save-column-mapping` POST, `configure-labels` GET, `save-label-mapping` POST
- Type-filtered dropdowns — each bpkm property shows only Monday.com columns of compatible types (e.g., "Status" only shows status-type columns)
- Status label mapping form that discovers labels from `settings_str` and maps them to bpkm:taskStatus enum values
- Priority label mapping form with same pattern
- Column mapping stored per-board as JSON in settings (key: `column_mapping_{board_id}`)
- connect_status.html shows "Configure Columns" link per selected board and mapping status indicator
- `get_board_items` GraphQL query includes `group { id title }` for group→taskGroup mapping
- `get_subitems` method on MondayClient for subitem fetching
- `sync_engine.py` with `pull_sync(ctx)` implementing two-phase bulk create following the Jira pattern
- `push_sync(ctx)` stub returning `{"status": "skipped", "reason": "not implemented"}`
- Group title → `bpkm:taskGroup` property (from item.group, not column_values)
- Subitems create separate Task objects with `bpkm:parentTask` edge to parent task
- Per-item error isolation in sync engine
- Content comparison for change detection (no `updated_at` filter available)
- 150+ new unit tests across `test_monday_column_mapping.py` and `test_monday_sync_engine.py`

## Proof Level

- This slice proves: contract + integration
- Real runtime required: no (offline unit tests prove all paths)
- Human/UAT required: no (UAT deferred to E2E in S04)

## Verification

- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_column_mapping.py -v` — 50+ column mapping route tests pass
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` — 100+ sync engine tests pass
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` — all Monday tests (S01 + S02), 427+ total, all pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — syntax valid after route additions
- Verify 5 service modules exist in `apps/monday-sync/services/` (auth, monday_client, field_mapper, person_matcher, sync_engine)
- Verify 2 new template files exist: `configure_columns.html`, `configure_labels.html`
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_column_mapping.py -v -k "error or malformed or missing"` — error-path tests (missing board_id, malformed settings_str, missing columns) all pass, confirming failure visibility

## Observability / Diagnostics

- Runtime signals: `monday_sync.sync` logger — INFO for sync start/complete/phase transitions, WARNING for per-item errors, ERROR for sync-level failures
- Inspection surfaces: `last_pull_result` / `last_push_result` in state (JSON with status, created, updated, skipped, errors, duration_ms, failed_items)
- Failure visibility: `failed_items` list in pull result identifies which Monday.com items failed with per-item error isolation; `_make_result()` captures duration and error counts
- Redaction constraints: API tokens never appear in logs or results (auth module handles masking)

## Integration Closure

- Upstream surfaces consumed: `services/auth.py` (get_connection_status, get_credentials), `services/monday_client.py` (MondayClient with extended queries), `services/field_mapper.py` (build_task_properties, compute_slug, BPKM), `services/person_matcher.py` (PersonMatcher.resolve)
- New wiring introduced in this slice: `sync_engine.py` imported lazily in `app.py` sync_now route and task handlers (already wired by S01). Column mapping routes added to `app.py`. `configure_columns.html` and `configure_labels.html` templates linked from `connect_status.html`.
- What remains before the milestone is truly usable end-to-end: S03 (push sync + LoopGuard + dependency edges), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Column mapping configuration routes, templates, and client extension** `est:1h`
  - Why: The novel, highest-risk work — builds the UI for mapping Monday.com columns to bpkm properties and mapping status/priority labels. Also extends MondayClient to include `group { id title }` in the items query and adds subitem fetching.
  - Files: `apps/monday-sync/app.py`, `apps/monday-sync/services/monday_client.py`, `apps/monday-sync/frontend/templates/configure_columns.html`, `apps/monday-sync/frontend/templates/configure_labels.html`, `apps/monday-sync/frontend/templates/connect_status.html`, `apps/monday-sync/frontend/static/styles.css`
  - Do: Add `COLUMN_TYPE_COMPATIBILITY` constant mapping bpkm properties to compatible Monday.com column types. Add 4 routes to app.py: `configure-columns` GET (discovers board columns, renders type-filtered dropdowns), `save-column-mapping` POST (saves mapping as JSON), `configure-labels` GET (parses `settings_str` to discover status/priority labels, renders label mapping form), `save-label-mapping` POST (saves label mappings). Create `configure_columns.html` with dropdown per bpkm property filtered by column type. Create `configure_labels.html` with status/priority label → bpkm enum value dropdowns. Extend `connect_status.html` to show "Configure Columns" link per selected board with mapping status indicator. Extend MondayClient: add `group { id title }` to `get_board_items` query, add `get_subitems(item_ids)` method. Add CSS for column mapping forms.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` and `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/monday_client.py').read())"` pass. Templates exist and contain expected elements.
  - Done when: 4 new routes added to app.py, 2 new templates created, connect_status.html updated, MondayClient extended with group field and subitems method, CSS added.

- [x] **T02: Pull sync engine with group and subitem support** `est:1h`
  - Why: Implements the core sync pipeline that converts Monday.com items into bpkm:Task objects using stored column mappings. This is the largest file but follows the established Jira sync engine pattern exactly.
  - Files: `apps/monday-sync/services/sync_engine.py`
  - Do: Clone the Jira sync_engine structure: `_find_existing_task()` SPARQL lookup, `_build_create_command()`, `_build_update_commands()`, `_submit_commands_batched()`, `_make_result()`, `_compute_status()`. Implement `pull_sync(ctx)` with Monday.com specifics: auth check → read selected boards from settings → per-board iteration → read column mapping config from settings → paginated `get_all_board_items()` → build properties via `build_task_properties()` with stored mapping → resolve assignee via PersonMatcher → set taskGroup from `item["group"]["title"]` (not column_values) → classify create/update via `_find_existing_task()` → Phase 1 bulk create → Phase 2 discover IRIs + body.set + edge.create → Phase 3 subitem→parentTask edges → store sync timestamp. Implement `push_sync(ctx)` stub returning `{"status": "skipped", "reason": "not implemented"}`. Use `ctx.commands._client` for bulk bypassing IRI prefix enforcement.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` passes.
  - Done when: `sync_engine.py` exists with `pull_sync()` and `push_sync()` functions; pull_sync implements complete two-phase bulk with group/subitem support; push_sync returns skipped stub.

- [x] **T03: Column mapping route unit tests** `est:45m`
  - Why: Proves the column mapping UI routes handle all cases — board column discovery, type filtering, label parsing from settings_str, mapping save/load, and error handling.
  - Files: `backend/tests/test_monday_column_mapping.py`
  - Do: Create test file using the importlib loading pattern from S01 tests. Build MockStateClient, MockSettingsClient, MockHttpClient, MockGraphClient matching the Jira test pattern. Test `configure-columns` GET renders type-filtered dropdowns. Test `save-column-mapping` POST stores per-board mapping in settings. Test `configure-labels` GET parses `settings_str` and renders label forms. Test `save-label-mapping` POST stores label mappings. Test error paths: missing board_id, no boards selected, malformed settings_str, empty column list. Test COLUMN_TYPE_COMPATIBILITY filtering logic. Test that extended MondayClient.get_board_items includes group data. Test get_subitems method.
  - Verify: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_column_mapping.py -v` — 50+ tests pass.
  - Done when: 50+ tests covering all column mapping routes, type compatibility filtering, label discovery from settings_str, client extension for groups and subitems, and error paths.

- [ ] **T04: Sync engine unit tests** `est:1h`
  - Why: Proves the sync engine handles all cases — create/update classification, two-phase bulk, group→taskGroup, subitem→parentTask, per-item error isolation, content comparison, and edge cases.
  - Files: `backend/tests/test_monday_sync_engine.py`
  - Do: Create test file using the importlib loading pattern. Build MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient following the Jira sync test pattern (MockGraphClient dispatches on SPARQL content to return slug lookups, email lookups, body text). Test `_find_existing_task()` SPARQL lookup (found/not-found). Test `pull_sync()` full pipeline: auth check, skip when not connected, skip when no boards selected, single board create, single board update, multiple boards, group→taskGroup from item.group, subitem→parentTask edge creation, per-item error isolation, empty results. Test Phase 1/Phase 2 command structure. Test content comparison for change detection. Test `push_sync()` returns skipped stub. Test `_make_result()` and `_compute_status()` helpers.
  - Verify: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` — 100+ tests pass. Then `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` — 427+ total tests pass.
  - Done when: 100+ tests covering all sync engine paths; combined Monday test count 427+; zero failures.

## Files Likely Touched

- `apps/monday-sync/app.py` — 4 new routes for column mapping + label mapping
- `apps/monday-sync/services/monday_client.py` — group field in items query, get_subitems method
- `apps/monday-sync/services/sync_engine.py` — NEW: pull sync engine + push stub
- `apps/monday-sync/frontend/templates/connect_status.html` — "Configure Columns" link + mapping status
- `apps/monday-sync/frontend/templates/configure_columns.html` — NEW: column mapping form
- `apps/monday-sync/frontend/templates/configure_labels.html` — NEW: label mapping form
- `apps/monday-sync/frontend/static/styles.css` — column mapping form styles
- `backend/tests/test_monday_column_mapping.py` — NEW: 50+ route tests
- `backend/tests/test_monday_sync_engine.py` — NEW: 100+ sync engine tests
