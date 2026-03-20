---
estimated_steps: 9
estimated_files: 3
---

# T03: Implement push sync pipeline with LoopGuard integration

**Slice:** S03 — Push sync + LoopGuard + dependency edges
**Milestone:** M024

## Description

Replaces the `push_sync()` stub in `sync_engine.py` with the full push pipeline (MON-09) and wires LoopGuard echo prevention into both push and pull sync (MON-10). This is the largest deliverable of S03, following the exact Jira/GitHub push sync pattern.

The pipeline: auth check → sync direction check → SPARQL change detection (`_find_changed_tasks`) → per-task loop (parse Monday.com URL → load board's column mapping → reverse-map properties → call `change_multiple_column_values` mutation → mark in LoopGuard → update `lastSyncedAt`) → store result.

The LoopGuard module was created in T01. The test infrastructure (MockMondayClient with `get_tags()`) was updated in T02.

**Relevant skills:** `test` skill for test patterns.

## Steps

1. **Add `parse_external_url()` helper** to `sync_engine.py`:
   ```python
   def parse_external_url(url: str) -> tuple[str, str] | None:
       """Parse board_id and item_id from a Monday.com URL.

       Expected format: https://monday.com/boards/{board_id}/pulses/{item_id}

       Returns (board_id, item_id) as strings, or None if parsing fails.
       """
   ```
   Use `str.split()` or a regex. Handle edge cases: None, empty string, wrong format, missing segments. Return None on failure (push skips the task with a warning).

2. **Add `_find_changed_tasks()` SPARQL query** to `sync_engine.py` (clone from Jira, change provider to "monday"):
   ```python
   async def _find_changed_tasks(graph_client) -> list[dict]:
       """Find Monday-synced tasks with local modifications.

       A task is changed when:
       - externalProvider = "monday"
       - dcterms:modified > bpkm:lastSyncedAt (or no lastSyncedAt)
       """
   ```
   The query should SELECT: `?task`, `?extUrl` (externalUrl), `?status`, `?priority`, `?title`, `?dueDate`, `?lastSynced`. The externalUrl is needed to extract board_id and item_id for the mutation call.

3. **Add `_get_task_body()` helper** to `sync_engine.py` (simple SPARQL query reading `<iri> <urn:sempkm:body> ?body`). Same as Jira pattern. Monday.com doesn't have ADF — body text may be pushed to a text/long_text column if mapped.

4. **Create module-level LoopGuard singleton** at the top of `sync_engine.py`:
   ```python
   try:
       from services.loop_guard import LoopGuard
   except ImportError:
       from loop_guard import LoopGuard

   _loop_guard = LoopGuard(ttl_seconds=30)
   ```

5. **Replace `push_sync()` stub** with the full pipeline:
   - **Auth check**: Create `MondayClient`, check `get_connection_status()`. If not connected, store result with `"reason": "not connected"` and return.
   - **Sync direction check**: Read `sync_direction` from settings. If `"pull-only"`, store result with `"reason": "sync direction is pull-only"` and return.
   - **Find changed tasks**: Call `_find_changed_tasks(ctx.graph)`. If empty list, store success with `pushed=0`.
   - **Per-task push loop**:
     a. Parse `externalUrl` via `parse_external_url()` → get `(board_id, item_id)`. Skip task if parse fails.
     b. Load column mapping: `column_mapping_{board_id}` from settings.
     c. Load label mapping: `label_mapping_{board_id}` from settings. Extract `reverse_status_mapping` and `reverse_priority_mapping` by inverting the label dicts.
     d. Build task properties dict from SPARQL result (title, status, priority, dueDate).
     e. Call `build_reverse_column_values(task_props, column_mapping, reverse_status, reverse_priority)`.
     f. If column_values is empty → skip (nothing to push).
     g. Call `monday_client.change_multiple_column_values(board_id, item_id, json.dumps(column_values_dict))`.
     h. Mark in LoopGuard: `_loop_guard.mark_pushed(item_id, "*")`.
     i. Update `lastSyncedAt` via `_submit_commands_batched()` with `object.patch` command.
     j. Increment `pushed_count`.
   - **Error handling**: Per-task try/except with task IRI and error in errors list.
   - **Store result**: Build result dict with status/pushed/skipped/errors/timestamp, store in `last_push_result`.

6. **Wire LoopGuard echo check into `pull_sync()`**:
   - In the per-item processing loop (around line 430 in pull_sync), after computing `item_id`, add:
     ```python
     if _loop_guard.is_echo(str(item_id), "*"):
         logger.debug("LoopGuard: skipping echo for item %s", item_id)
         skipped_count += 1
         continue
     ```
   - Same check in the subitem processing loop.

7. **Add `change_multiple_column_values()` and `get_tags()` methods to `MockMondayClient`** in `test_monday_sync_engine.py` (if not already added by T02):
   ```python
   async def change_multiple_column_values(self, board_id, item_id, column_values_json):
       self.mutations.append({"board_id": board_id, "item_id": item_id, "values": column_values_json})
       return {"id": str(item_id), "name": "Updated"}
   ```
   Add `self.mutations = []` to MockMondayClient `__init__`.

8. **Update `SyncContext` to support MondayClient injection** — the push sync needs to create a `MondayClient` from `ctx.http` and `ctx.state`. The test pattern is: mock the `MondayClient` constructor or inject a mock monday_client into the context. Simplest approach: make push_sync accept an optional `monday_client` parameter (for testing), defaulting to creating one from `ctx.http`/`ctx.state`.

   Alternatively, follow the Jira pattern where the test patches the client construction. The Jira tests mock `get_connection_status` and `JiraClient` directly. For Monday.com, patch `get_connection_status` at the module level and inject mock objects.

9. **Add 50+ push sync tests** in `test_monday_sync_engine.py`:
   - **TestParseExternalUrl** (~8 tests):
     - Valid URL → `("12345", "67890")`
     - Missing scheme → None
     - Wrong domain → None (or still parse — it's a format thing)
     - Empty string → None
     - None → None (guard)
     - Extra path segments → still works
     - Numeric board/item IDs extracted correctly
     - URL with trailing slash
   - **TestFindChangedTasks** (~5 tests):
     - No changed tasks → empty list
     - One changed task → correct dict fields
     - Multiple changed tasks → all returned
     - SPARQL includes externalUrl
     - Handles missing optional fields gracefully
   - **TestPushSyncAuth** (~4 tests):
     - Not connected → `{"status": "skipped", "reason": "not connected"}`
     - Pull-only direction → `{"status": "skipped", "reason": "sync direction is pull-only"}`
     - Bidirectional direction → proceeds
     - Result stored in `last_push_result` state key
   - **TestPushSyncPipeline** (~15 tests):
     - No changed tasks → success with pushed=0
     - One changed task → mutation called with correct board_id, item_id
     - Column mapping loaded from settings for correct board
     - Reverse column values passed to mutation
     - `lastSyncedAt` updated after push
     - LoopGuard marks item after push
     - Parse URL failure → task skipped, not crashed
     - Missing column mapping for board → task skipped
     - Mutation API error → error recorded, other tasks continue
     - Multiple tasks across different boards → each loads correct mapping
     - Empty reverse column values → task skipped
     - Push result has correct status/pushed/skipped/errors counts
     - Partial success → status "partial"
     - All errors → status "error"
     - Timestamp in ISO format
   - **TestLoopGuardIntegrationPull** (~8 tests):
     - Marked item skipped in pull_sync
     - Unmarked item processed normally
     - Expired mark → item processed (TTL passed)
     - Multiple items, only marked one skipped
     - Marked subitem also skipped
     - Echo skip increments skipped_count
     - LoopGuard cleanup doesn't break sync
     - Module-level singleton shared between push and pull
   - **TestGetTaskBody** (~4 tests):
     - Body found → returns text
     - No body → returns None
     - Empty bindings → returns None
     - SPARQL queries correct IRI

## Must-Haves

- [ ] `parse_external_url()` handles valid URLs and returns None for invalid ones
- [ ] `_find_changed_tasks()` SPARQL query finds Monday-synced tasks with modified > lastSyncedAt
- [ ] `push_sync()` replaces stub with full pipeline
- [ ] Auth and direction checks skip with stored result and reason
- [ ] Per-task: parse URL → load mapping → reverse map → mutate → mark LoopGuard → update lastSyncedAt
- [ ] Per-task error isolation (one failure doesn't stop others)
- [ ] LoopGuard echo check in `pull_sync()` item loop — marked items skipped
- [ ] LoopGuard echo check in `pull_sync()` subitem loop
- [ ] `last_push_result` stored in state with status/pushed/skipped/errors/timestamp
- [ ] Module-level `_loop_guard` singleton shared between push and pull
- [ ] 50+ new tests passing
- [ ] All existing Monday.com tests still pass (no regressions)
- [ ] Total Monday.com test count ≥ 590

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` — 160+ tests pass
- `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 590+ total tests pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — valid syntax
- `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` — zero results

## Observability Impact

- Signals added: `last_push_result` state key (JSON) with `status`, `pushed`, `skipped`, `errors`, `timestamp`; push pipeline logs at INFO for phase transitions, WARNING for per-task errors
- How a future agent inspects this: read `last_push_result` state key; check `monday_sync.sync` logger output; `errors` list in result has per-task `{iri, error}` details
- Failure state exposed: auth skip with reason; direction skip with reason; per-task errors with IRI and exception message; overall status degrades from success → partial → error

## Inputs

- `apps/monday-sync/services/loop_guard.py` — T01 output: `LoopGuard` class
- `apps/monday-sync/services/sync_engine.py` — T02 output with `_process_dependencies()`, `_find_task_by_monday_item_id()`, tag resolution in pull_sync
- `apps/monday-sync/services/field_mapper.py` — `build_reverse_column_values()` (S01), `build_external_url()`, `BPKM` constant
- `apps/monday-sync/services/monday_client.py` — `MondayClient.change_multiple_column_values()` (S01)
- `apps/monday-sync/services/auth.py` — `get_connection_status()` (S01)
- `backend/tests/test_monday_sync_engine.py` — T02 output with updated MockMondayClient, SyncContext, existing test patterns
- Jira push sync pattern at `apps/jira-sync/services/sync_engine.py` lines 819-947 — auth check, direction check, find changed tasks, per-task push loop, error isolation, result storage
- Column mapping stored at `column_mapping_{board_id}` and label mapping at `label_mapping_{board_id}` as JSON in settings (D242)
- S02 Forward Intelligence: column_mapping is `{bpkm_prop → monday_col_id}`, label_mapping has `status_label_mapping` and `priority_label_mapping` sub-dicts

## Expected Output

- `apps/monday-sync/services/sync_engine.py` — MODIFIED: `parse_external_url()`, `_find_changed_tasks()`, `_get_task_body()`, LoopGuard import + singleton, full `push_sync()` implementation, LoopGuard echo check in `pull_sync()`
- `backend/tests/test_monday_sync_engine.py` — MODIFIED: 50+ new tests across 6 test classes, MockMondayClient extended with mutations tracking
