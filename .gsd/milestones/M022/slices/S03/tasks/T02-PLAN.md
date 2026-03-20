---
estimated_steps: 5
estimated_files: 2
---

# T02: Build push_sync pipeline in sync_engine.py

**Slice:** S03 — Push sync + section-based status moves
**Milestone:** M022

## Description

Add the push sync pipeline to `sync_engine.py`. This orchestrates the full push flow: SPARQL finds locally-changed Asana tasks → reverse-map bpkm properties → call Asana API (PATCH for custom fields, addTask for section moves) → update `lastSyncedAt` → store `last_push_result`. The two-path push (custom field PATCH vs section move) is the core novelty — when `status_source` is `"section"` and status changed, push uses `add_task_to_section()` instead of (or in addition to) `patch_task()`.

This task depends on T01's reverse mapping functions: `build_asana_patch()`, `resolve_section_gid_for_status()`, `reverse_status_mapping()`.

## Steps

1. **Read** `apps/asana-sync/services/sync_engine.py` to understand the existing pull_sync structure and `_read_field_config()` helper.

2. **Add `_find_changed_tasks(graph_client)`** — Clone from Linear's pattern (`apps/linear-sync/services/sync_engine.py` lines 87-130), changing `externalProvider` filter from `"linear"` to `"asana"`. Returns a list of dicts with keys: `iri`, `externalUuid` (Asana GID stored as UUID), `status`, `priority`, `title`, `dueDate`, `lastSyncedAt`. The SPARQL query should:
   - Filter `?task a <bpkm:Task>` with `externalProvider = "asana"`
   - Require `externalUuid` (was pulled from Asana)
   - OPTIONAL binds for status, priority, title, dueDate, lastSyncedAt, syncDirection, modified
   - FILTER: exclude pull-only tasks, include only tasks where modified > lastSyncedAt (or no lastSyncedAt)
   - Also extract `externalUrl` (needed to parse task GID for API calls — the Asana GID is stored in `externalUuid`)

3. **Add `push_sync(ctx)`** — The main push orchestrator. Follow this flow:
   a. Check auth via `get_connection_status(ctx.state)` — skip if not connected
   b. Read `sync_direction` from StateClient — skip if `"pull-only"`
   c. Read field_config via `_read_field_config(ctx.state)` (existing helper)
   d. Read `discovered_enum_fields` and `discovered_sections` from StateClient (JSON parse)
   e. Call `_find_changed_tasks(ctx.graph)` — skip if empty
   f. Build AsanaClient via `_make_client(ctx)` (need to add a helper or inline client construction)
   g. For each changed task:
      - Build bpkm properties dict from task's current values (status, priority, title, dueDate)
      - Call `build_asana_patch(bpkm_props, field_config, discovered_enum_fields)` for custom field PATCH body
      - If patch is non-empty, call `client.patch_task(task_gid, patch)`
      - If `field_config["status_source"] == "section"` and status is present, call `resolve_section_gid_for_status(status, field_config, discovered_sections)` — if GID found, call `client.add_task_to_section(section_gid, task_gid)`
      - Update `lastSyncedAt` on the task IRI via `_submit_commands_batched()` (same pattern as pull sync)
      - Per-task try/except for error isolation
   h. Store `last_push_result` in StateClient (JSON with status, pushed, skipped, errors, error_details)
   i. Return result dict

   **Important**: The task GID for API calls comes from `externalUuid` stored during pull sync. The `_submit_commands_batched` helper is already used in pull_sync for lastSyncedAt — reuse it here. Access the raw HTTP client via `ctx.commands._client` (same D204 bypass as pull).

4. **Add unit tests** to `backend/tests/test_asana_sync_engine.py` — approximately 30 tests in a new test class `TestPushSync`:
   - Guard tests: `test_push_sync_not_connected` (skip), `test_push_sync_pull_only` (skip), `test_push_sync_no_changed_tasks` (ok, pushed=0)
   - Custom field push: `test_push_sync_custom_field_status` — patches task with custom field enum GID
   - Section-based push: `test_push_sync_section_status` — calls add_task_to_section with resolved section GID
   - Priority push: `test_push_sync_priority_change` — includes priority in PATCH
   - Title push: `test_push_sync_title_change` — includes name in PATCH
   - Combined: `test_push_sync_multiple_fields` — status + priority + title all pushed
   - Section + custom field: `test_push_sync_section_status_plus_priority` — section move for status AND PATCH for priority in same push
   - Error isolation: `test_push_sync_partial_failure` — one task fails, others still push
   - lastSyncedAt: `test_push_sync_updates_last_synced_at` — verify timestamp update command
   - Result storage: `test_push_sync_stores_result` — `last_push_result` has pushed, errors, status keys
   - No section GID: `test_push_sync_section_gid_not_found` — status mapped but section GID missing → logged, not fatal
   - Empty patch + no section: `test_push_sync_no_pushable_changes` — task detected as changed but nothing reverse-maps → skipped
   - _find_changed_tasks tests: `test_find_changed_tasks_filters_asana_provider`, `test_find_changed_tasks_excludes_pull_only`, `test_find_changed_tasks_empty_result`

   Mock the AsanaClient methods (`patch_task`, `add_task_to_section`) and `_find_changed_tasks` return value. Mock `_read_field_config` and StateClient for discovered data. Use the same async test pattern as existing sync engine tests.

5. **Verify** all tests pass and syntax is valid.

## Must-Haves

- [ ] `_find_changed_tasks()` SPARQL correctly filters for `externalProvider = "asana"` and modified > lastSyncedAt
- [ ] `push_sync()` handles both custom field PATCH and section move paths based on status_source
- [ ] Per-task error isolation — one failure doesn't stop the batch
- [ ] `lastSyncedAt` updated after each successful push to prevent re-push
- [ ] `last_push_result` stored in StateClient with pushed/skipped/errors/status keys
- [ ] All existing 58 sync engine tests still pass
- [ ] 25+ new push sync tests pass

## Verification

- `uv run pytest backend/tests/test_asana_sync_engine.py -q` — 85+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` — no SyntaxError

## Observability Impact

- Signals added: `push_sync: found %d changed tasks`, `push_sync: pushed task %s`, `push_sync: section move for task %s`, per-task error warnings with task GID
- How a future agent inspects: `last_push_result` StateClient key → JSON with status/pushed/errors/error_details
- Failure state exposed: per-task error_details list (task IRI, task GID, error message) + overall status field

## Inputs

- `apps/asana-sync/services/sync_engine.py` — Existing pull sync module (~640 lines). Has `_read_field_config()`, `_submit_commands_batched()`, `pull_sync()`.
- `apps/asana-sync/services/field_mapper.py` — T01 added `build_asana_patch()`, `resolve_section_gid_for_status()`, `reverse_status_mapping()`, `reverse_priority_mapping()`, `_resolve_enum_option_gid()`.
- `apps/asana-sync/services/asana_client.py` — Already has `patch_task(task_gid, data)` and `add_task_to_section(section_gid, task_gid)`.
- `backend/tests/test_asana_sync_engine.py` — Existing 58 tests (~1258 lines).
- Linear push sync reference: `apps/linear-sync/services/sync_engine.py` — `_find_changed_tasks()` (lines 87-130) and `push_sync()` (lines 238-330) for structural pattern.
- BPKM namespace: `BPKM = "urn:sempkm:model:basic-pkm:"` — used in SPARQL queries and property key lookups.

## Expected Output

- `apps/asana-sync/services/sync_engine.py` — Extended with `_find_changed_tasks()` and `push_sync()` (~150-200 new lines)
- `backend/tests/test_asana_sync_engine.py` — Extended with TestPushSync class (~300-350 new lines, 25+ tests)
