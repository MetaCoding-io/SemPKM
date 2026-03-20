---
estimated_steps: 8
estimated_files: 3
---

# T01: Implement real push sync with SPARQL change detection and ADF description conversion

**Slice:** S03 — Push sync + issue links
**Milestone:** M023

## Description

Replace the `push_sync()` stub in `sync_engine.py` with a real implementation that enables bidirectional Jira sync. The implementation follows the proven Linear/GitHub push sync pattern: SPARQL change detection → reverse field mapping → API update → lastSyncedAt update.

Jira-specific additions: description push requires reading the task body text via SPARQL (`urn:sempkm:body`), converting it to ADF format via `markdown_to_adf()` from `adf_converter.py`, and including the ADF dict in the `update_issue()` fields payload. `build_issue_patch()` in `field_mapper.py` must be extended to accept and include ADF description.

Per D237: push is limited to title/description/priority — no status transitions.

**Relevant skills:** `test` skill for unit test generation patterns.

## Steps

1. **Add `_find_changed_tasks()` SPARQL function** in `sync_engine.py`. Query tasks where `externalProvider = "jira"`, with OPTIONAL bindings for `externalId`, `taskStatus`, `priority`, `dcterms:title`, `lastSyncedAt`, `dcterms:modified`, `syncDirection`. Filter: `(!BOUND(?syncDir) || ?syncDir != "pull-only")` AND `(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))`. Return list of dicts with keys: `iri`, `externalId`, `status`, `priority`, `title`, `lastSyncedAt`. Reference: `apps/linear-sync/services/sync_engine.py` lines 87-130.

2. **Add `_get_task_body()` SPARQL helper** in `sync_engine.py`. Query `SELECT ?body WHERE { <{iri}> <urn:sempkm:body> ?body } LIMIT 1`. Returns the body text string or None. This is needed because `_find_changed_tasks` can't efficiently bind body text in the same query (it's a large text field).

3. **Extend `build_issue_patch()` in `field_mapper.py`** to accept an optional `description_adf: dict | None = None` parameter. If provided and non-empty, include `"description": description_adf` in the result dict. The ADF dict is the output of `markdown_to_adf()` — a complete ADF document structure that Jira's v3 API expects for the `description` field.

4. **Replace `push_sync()` stub** in `sync_engine.py` with the real implementation:
   - Auth check via `get_connection_status()` — skip if not connected
   - Direction check via `ctx.settings.get("sync_direction")` — skip if "pull-only"
   - Call `_find_changed_tasks(ctx.graph)` — skip if empty
   - For each changed task:
     - Read body text via `_get_task_body(ctx.graph, task["iri"])`
     - Convert body to ADF via `markdown_to_adf(body_text)` (import already exists)
     - Build task_props dict from SPARQL result: `{"dcterms:title": title, f"{BPKM}priority": priority}`
     - Call `build_issue_patch(task_props, description_adf=adf_doc)` to get Jira fields dict
     - If fields dict is empty, increment skipped_count and continue
     - Call `client.update_issue(task["externalId"], fields)` — externalId IS the issue key for Jira
     - Update `lastSyncedAt` on the pushed task via `object.patch` command using `_submit_commands_batched()`
   - Per-task error isolation: wrap each task in try/except, append to errors list on failure
   - Build result dict with `status: "success"/"partial"/"error"`, `pushed`, `skipped`, `errors`, `timestamp`
   - Store result as `last_push_result` in `ctx.state`
   - **Important:** Use `"success"` not `"ok"` for result status — matches Jira connect_status.html template

5. **Add the `markdown_to_adf` import** to the existing import block at the top of `sync_engine.py` — it's already imported for pull_sync's `adf_to_markdown`, but add `markdown_to_adf` to the same import line.

6. **Write ~30 unit tests** in `test_jira_sync_engine.py`. Add new test classes after the existing `TestPushSync` class (which tests the stub — update those tests to match new behavior). Tests needed:

   **TestFindChangedTasks (new class, ~6 tests):**
   - No changed tasks → returns empty list
   - One changed task (modified > lastSyncedAt) → returns it with all fields
   - One unchanged task (modified <= lastSyncedAt) → returns empty
   - Task with no lastSyncedAt → treated as changed (returned)
   - Task with syncDirection "pull-only" → filtered out
   - Multiple tasks, mix of changed/unchanged → correct filtering

   **TestGetTaskBody (new class, ~3 tests):**
   - Body exists → returns text string
   - No body → returns None
   - Empty body → returns empty string or None

   **TestBuildIssuePatchWithDescription (extend existing tests, ~3 tests):**
   - With description_adf → includes "description" key
   - Without description_adf → no "description" key (backward compat)
   - With description_adf=None → no "description" key

   **TestPushSyncReal (update existing TestPushSync, ~15 tests):**
   - Update existing stub tests: `test_push_not_connected_skips` and `test_push_pull_only_skips` should still pass (same behavior)
   - Remove/update `test_push_bidirectional_returns_not_implemented` — now it works
   - Happy path: find changed → reverse map → update_issue called with correct fields including ADF description
   - No changed tasks → result with pushed=0
   - Error isolation: one task fails, others continue, errors list populated
   - lastSyncedAt updated after successful push
   - `last_push_result` stored in state
   - Empty issue patch (no pushable changes) → skipped
   - Task with no body → push without description field
   - Task with body → description included as ADF

   **Mock infrastructure updates:**
   - MockGraphClient needs a `body_map: dict[str, str]` (iri → body text) and routing for body SPARQL queries
   - MockJiraClient needs `update_issue()` tracking (record calls for assertion)

7. **Verify** all tests pass: `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v`

8. **Verify** Python validity: `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read()); ast.parse(open('apps/jira-sync/services/field_mapper.py').read()); print('VALID')"` 

## Must-Haves

- [ ] `_find_changed_tasks()` SPARQL function returns changed Jira tasks with correct filtering
- [ ] `_get_task_body()` reads body text from SPARQL by IRI
- [ ] `build_issue_patch()` accepts and includes optional `description_adf` parameter
- [ ] `push_sync()` replaces stub with real push pipeline: find changed → reverse map → update_issue → lastSyncedAt
- [ ] Description push converts body text via `markdown_to_adf()` and includes ADF in update
- [ ] Per-task error isolation — one failed push doesn't kill the run
- [ ] Result dict uses `status: "success"` not `"ok"`
- [ ] `last_push_result` stored in `ctx.state`
- [ ] All existing 95 tests still pass (regression)
- [ ] ~30 new push sync tests pass

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` — all ~125 tests pass
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read()); ast.parse(open('apps/jira-sync/services/field_mapper.py').read()); print('VALID')"` — prints VALID

## Observability Impact

- Signals added: `last_push_result` state key now contains real push results (pushed/skipped/errors) instead of stub "skipped" status. INFO logging for push phases, WARNING for per-task errors.
- How a future agent inspects this: `ctx.state.get("last_push_result")` JSON, rendered in connect_status.html sync stats section.
- Failure state exposed: `errors` list with per-task `{iri, error}` dicts in push result.

## Inputs

- `apps/jira-sync/services/sync_engine.py` — has push_sync stub at bottom (~lines 635-666), pull_sync with full pipeline, all SPARQL helpers and command builders
- `apps/jira-sync/services/field_mapper.py` — has `build_issue_patch()` at lines 368-403 with title + priority reverse mapping, needs description_adf extension
- `apps/jira-sync/services/adf_converter.py` — has `markdown_to_adf()` at line 356+, already imported in sync_engine.py for pull_sync direction
- `apps/jira-sync/services/jira_client.py` — has `update_issue(issue_key, fields)` at line 276, PUT /rest/api/3/issue/{key}
- `backend/tests/test_jira_sync_engine.py` — 95 tests, 2328 lines, with MockGraphClient (has slug_map + milestone_slug_map routing), MockStateClient, MockSettingsClient, MockCommandClient, MockJiraClient, MockAppContext
- Reference: `apps/linear-sync/services/sync_engine.py` lines 87-130 (_find_changed_tasks SPARQL), lines 238-350 (push_sync pipeline)
- Reference: `apps/github-sync/services/sync_engine.py` lines 181-225 (_find_changed_tasks SPARQL), lines 234-380 (push_sync pipeline)
- S02 Forward Intelligence: `ctx.settings` for config (sync_direction), `ctx.state` for runtime (last_push_result). Result dict must use `"success"` not `"ok"`.
- `BPKM` namespace constant already imported in sync_engine.py: `from services.field_mapper import ... BPKM`
- Jira `externalId` stores the issue key directly (e.g., "PROJ-123") — no URL parsing needed (unlike GitHub)

## Expected Output

- `apps/jira-sync/services/sync_engine.py` — push_sync stub replaced with ~100 lines of real implementation, `_find_changed_tasks()` ~30 lines, `_get_task_body()` ~15 lines. File grows from ~666 to ~810 lines.
- `apps/jira-sync/services/field_mapper.py` — `build_issue_patch()` gains `description_adf` parameter (~5 lines changed)
- `backend/tests/test_jira_sync_engine.py` — ~30 new tests in 4 test classes (TestFindChangedTasks, TestGetTaskBody, TestBuildIssuePatchWithDescription, updated TestPushSync). File grows from ~2328 to ~2900 lines.
