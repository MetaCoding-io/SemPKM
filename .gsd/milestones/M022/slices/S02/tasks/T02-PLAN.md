---
estimated_steps: 8
estimated_files: 3
---

# T02: Build sync engine, wire app.py poll handler, and add sync-now route

**Slice:** S02 — Pull sync with configurable field transforms + subtask nesting
**Milestone:** M022

## Description

Build the pull sync orchestration layer — `sync_engine.py` with `pull_sync(ctx)` that coordinates AsanaClient, field_mapper, and PersonMatcher into a complete Asana→bpkm:Task pipeline. The two novel pieces vs prior sync apps are: (1) reading field mapping configuration from StateClient and passing it to `build_task_properties()`, and (2) `_fetch_subtasks_recursive()` with a depth counter bounded at 5 levels. Everything else follows the established Todoist/Linear two-phase bulk pattern.

Replace the skeleton `poll_tasks` handler in `app.py` with a real call to `pull_sync()`. Add a `sync_now` POST route to trigger pull on demand.

## Steps

1. **Read reference implementations** for the sync engine pattern:
   - `apps/todoist-sync/services/sync_engine.py` (~677 lines) — REST-only provider, closest API pattern to Asana. Study `pull_sync()` structure: auth check → read selected projects → fetch tasks → classify create/update → two-phase bulk → store result.
   - `apps/linear-sync/services/sync_engine.py` (~529 lines) — two-phase bulk, edge.create pattern
   - T01 outputs: `apps/asana-sync/services/field_mapper.py` — `build_task_properties(task, field_config, section_name)` signature, `compute_task_slug(task)`, `detect_milestone(task)`, `extract_body(task)`, `extract_assignee(task)`, `extract_followers(task)`, `extract_section_name(task)`, `BPKM` prefix
   - T01 outputs: `apps/asana-sync/services/person_matcher.py` — `PersonMatcher(graph_client, command_client)` with `match_or_create(email, display_name)`
   - `apps/asana-sync/services/asana_client.py` — `get_tasks(project_gid, opt_fields, modified_since)`, `get_subtasks(task_gid, opt_fields)`
   - `apps/asana-sync/services/auth.py` — `get_connection_status(state_client, http_client)`
   - `apps/asana-sync/app.py` — understand current skeleton handlers at bottom of file

2. **Create `apps/asana-sync/services/sync_engine.py`** (~400-450 lines):
   - Imports: field_mapper functions (use try/except for services. vs bare import), PersonMatcher, auth helpers, AsanaClient. Use the dual-import pattern from Linear/Todoist sync engines.
   - Constants: `BATCH_SIZE = 1000`, `MAX_SUBTASK_DEPTH = 5`, `TASK_OPT_FIELDS` string with the complete field list: `name,notes,html_notes,completed,completed_at,due_on,due_at,start_on,start_at,assignee,assignee.email,assignee.name,followers,followers.email,followers.name,tags,tags.name,memberships.section,memberships.section.name,custom_fields,custom_fields.name,custom_fields.gid,custom_fields.enum_value,custom_fields.enum_value.name,custom_fields.number_value,parent,permalink_url,resource_subtype,modified_at`
   - `_find_existing_task(graph_client, slug)` — SPARQL lookup for existing task by slug using `STRENDS` pattern. Returns `{iri, status, externalId, lastSyncedAt}` or None.
   - `_submit_commands_batched(http_client, commands)` — split commands into BATCH_SIZE chunks, POST to `/api/commands/bulk`.
   - `_read_field_config(state_client)` — read all field mapping StateClient keys into a dict: `status_source`, `status_field_gid`, `status_mapping` (JSON-parsed), `priority_field_gid`, `priority_mapping` (JSON-parsed), `story_points_field_gid`. Return the config dict.
   - `_build_update_commands(existing, task, field_config, section_name, body_text, person_iri, follower_iris)` — build patch + body.set + edge.create commands for an existing task (same pattern as Linear/Todoist).
   - `_fetch_subtasks_recursive(client, task_gid, opt_fields, depth, max_depth)` — if depth >= max_depth, return []. Call `client.get_subtasks(task_gid, opt_fields)`. For each subtask, annotate with `_parent_gid = task_gid`, then recurse on that subtask's GID with depth+1. Collect and return flat list of all subtask dicts.
   - `_make_result(status, start_time, sync_timestamp, **kwargs)` — build result dict with status, created, updated, unchanged, errors, error_details, duration_ms, timestamp.
   - `pull_sync(ctx)` — main entry point:
     1. Auth check via `get_connection_status()`
     2. Read selected projects from StateClient
     3. Read field config via `_read_field_config()`
     4. Read `last_sync_at` for incremental sync
     5. Set up PersonMatcher and http_client (via `ctx.commands._client` for D204 bypass)
     6. For each selected project:
        a. Fetch tasks via `client.get_tasks(project_gid, TASK_OPT_FIELDS, modified_since=last_sync_at)`
        b. For each top-level task: extract section_name, classify as create/update via `_find_existing_task()`, build properties via `build_task_properties()`, resolve assignee/followers via PersonMatcher, detect body, detect milestone type
        c. Fetch subtasks recursively via `_fetch_subtasks_recursive()` — process each subtask the same way, storing parent_gid for edge creation
     7. Phase 1: submit `object.create` commands for new tasks
     8. Phase 2: SPARQL-discover minted IRIs for new tasks, submit `body.set` + `edge.create` (assignee, followers, subtask→parent `dcterms:isPartOf`)
     9. Submit update commands for existing tasks
     10. Update `last_sync_at` and `last_pull_result` in StateClient
     11. Return result dict
   - Per-task error isolation: wrap each task's processing in try/except, log error, increment error_count, append to error_details, continue with next task
   - Loop prevention: for existing tasks, compare `lastSyncedAt` from SPARQL with `modified_at` from Asana — skip if not modified since last sync
   - Trashed/completed tasks: if `task["completed"]` is True and previous status was not "done", update to "done" (handled naturally by field_mapper status extraction)

3. **Modify `apps/asana-sync/app.py`**:
   - Add import for `pull_sync` from sync_engine (dual try/except pattern)
   - Replace skeleton `poll_tasks` handler body with: `result = await pull_sync(ctx)` then `return result`
   - Add `sync_now` POST route handler: `@asana_sync_app.route("/sync-now", methods=["POST"])` that calls `pull_sync(ctx)` and returns result as JSON. Use the same pattern as other sync apps.
   - Keep `push_changes` skeleton handler unchanged (S03 will implement it)

4. **Create `backend/tests/test_asana_sync_engine.py`** (~800-1000 lines, 40+ tests):
   - Build mock infrastructure:
     - `MockStateClient` with get/set (dict-backed)
     - `MockGraphClient` with configurable query responses
     - `MockCommandClient` with `_client` attribute for bulk bypass
     - `MockHttpClient` for AsanaClient's HTTP layer
     - `MockResponse` class (per KNOWLEDGE.md pattern #2: `data if data is not None else {}`)
     - `make_mock_ctx()` factory that assembles all mocks into a ctx-like object
   - Guard tests:
     - Not connected → returns status="skipped", reason="not connected"
     - No selected projects → returns status="skipped", reason="no projects selected"
     - Empty selected projects list → same skip
   - Create flow tests:
     - New task (not in SPARQL) → object.create command with correct type and properties
     - New milestone (resource_subtype="milestone") → object.create with bpkm:Milestone type
     - Multiple tasks → multiple create commands in one batch
     - Phase 2: body.set command after IRI discovery
     - Phase 2: edge.create for assignee
     - Phase 2: edge.create for followers
   - Update flow tests:
     - Existing task (in SPARQL) → object.patch command
     - Loop prevention: task not modified since lastSyncedAt → skipped (unchanged)
     - Task modified since lastSyncedAt → updated
   - Subtask recursion tests:
     - 1 level deep: parent with 2 subtasks → 3 total tasks processed
     - 3 levels deep: grandparent → parent → child → 3 tasks with correct parent linkage
     - Max depth (5) enforcement: tasks at depth 5 processed, depth 6 not fetched
     - Subtask→parent edge: `dcterms:isPartOf` edge.create command present
   - Error isolation tests:
     - One task raises exception → other tasks still processed, error in error_details
     - API error fetching project → error logged, other projects continue
   - Incremental sync test:
     - `last_sync_at` present → `modified_since` parameter passed to client
   - Status modes test:
     - field_config with custom_field status_source → correct properties
     - field_config with section status_source → section_name extracted and passed
   - Result storage:
     - `last_pull_result` contains created, updated, errors, duration_ms, timestamp
     - `last_sync_at` updated after successful sync

5. **Run all sync engine tests:**
   ```bash
   pytest backend/tests/test_asana_sync_engine.py -v --noconftest
   ```

6. **Run ALL S02 tests together** to confirm no conflicts:
   ```bash
   pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_person_matcher.py backend/tests/test_asana_sync_engine.py -v --noconftest
   ```

7. **Verify syntax** on modified files:
   ```bash
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"
   python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"
   ```

8. **Commit:** `feat(asana-sync): pull sync engine with subtask recursion + app.py wiring`

## Must-Haves

- [ ] `pull_sync(ctx)` reads field config from StateClient and passes to `build_task_properties()`
- [ ] Two-phase bulk create: Phase 1 object.create, Phase 2 body.set + edge.create after IRI discovery
- [ ] `_fetch_subtasks_recursive()` with depth counter bounded at MAX_SUBTASK_DEPTH=5
- [ ] Subtask→parent linking via `dcterms:isPartOf` edge.create commands
- [ ] Per-task error isolation: exception in one task doesn't stop others
- [ ] Incremental sync: `modified_since` parameter from `last_sync_at` StateClient key
- [ ] Loop prevention: skip tasks not modified since lastSyncedAt
- [ ] `last_pull_result` stored in StateClient with status, created, updated, errors, duration_ms
- [ ] `last_sync_at` cursor updated after successful sync
- [ ] `poll_tasks` handler calls `pull_sync(ctx)` instead of returning skeleton response
- [ ] `sync_now` POST route triggers pull sync on demand
- [ ] TASK_OPT_FIELDS includes all fields needed for complete mapping (custom_fields.gid, memberships.section.name, etc.)
- [ ] Commands bypass SDK IRI prefix enforcement via `ctx.commands._client` (D204 workaround)
- [ ] Milestone detection: tasks with `resource_subtype: "milestone"` use `bpkm:Milestone` type in create command
- [ ] 40+ sync engine tests passing with `--noconftest`

## Verification

- `pytest backend/tests/test_asana_sync_engine.py -v --noconftest` — 40+ tests pass
- `pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_person_matcher.py backend/tests/test_asana_sync_engine.py -v --noconftest` — 100+ total tests pass
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` — no error
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — no error
- At least one test verifies `last_pull_result` contains `created`, `errors`, `duration_ms` keys

## Observability Impact

- Signals added: `asana.sync.engine` logger with pull_sync start/complete events, per-task error logging, subtask recursion depth logging
- How a future agent inspects this: `ctx.state.get("last_pull_result")` returns JSON with full sync stats; `ctx.state.get("last_sync_at")` shows last incremental sync cursor
- Failure state exposed: `error_details` list in result dict with task_gid, project_gid, and error message per failure; overall `status` field distinguishes "success"/"partial"/"error"/"skipped"

## Inputs

- `apps/asana-sync/services/field_mapper.py` (T01 output) — `build_task_properties()`, `compute_task_slug()`, `detect_milestone()`, `extract_body()`, `extract_assignee()`, `extract_followers()`, `extract_section_name()`, `BPKM` prefix
- `apps/asana-sync/services/person_matcher.py` (T01 output) — `PersonMatcher` class with `match_or_create(email, display_name)`
- `apps/asana-sync/services/asana_client.py` (S01) — `AsanaClient` with `get_tasks(project_gid, opt_fields, modified_since)`, `get_subtasks(task_gid, opt_fields)`
- `apps/asana-sync/services/auth.py` (S01) — `get_connection_status(state_client, http_client)`
- `apps/asana-sync/app.py` (S01) — current skeleton with `poll_tasks` and `push_changes` handlers
- `apps/todoist-sync/services/sync_engine.py` — reference for REST-based pull_sync pattern, two-phase bulk, _find_existing_task SPARQL
- `apps/linear-sync/services/sync_engine.py` — reference for edge.create pattern, _submit_commands_batched

## Expected Output

- `apps/asana-sync/services/sync_engine.py` — ~400-450 lines, complete pull sync pipeline with subtask recursion
- `apps/asana-sync/app.py` — modified: poll_tasks calls pull_sync, sync_now route added
- `backend/tests/test_asana_sync_engine.py` — ~800-1000 lines, 40+ tests covering all sync paths
