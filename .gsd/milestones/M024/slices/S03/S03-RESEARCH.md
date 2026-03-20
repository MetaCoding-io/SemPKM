# S03: Push sync + LoopGuard + dependency edges — Research

**Date:** 2026-03-20

## Summary

This slice implements push sync (SemPKM → Monday.com), LoopGuard echo prevention, dependency column → `bpkm:dependsOn` edges, and tag ID → name resolution. All four capabilities are straightforward applications of patterns already established in 3+ prior sync apps (Jira, GitHub, Linear). The push sync follows the exact same `_find_changed_tasks` SPARQL → reverse map → API mutation → `lastSyncedAt` update pipeline used by Jira (S03), GitHub (S03), and Linear (S03). The LoopGuard is a simple in-memory TTL dict (D241) that's trivially testable. Dependency edges follow the Jira `_process_issue_links` pattern. Tag resolution uses the existing `MondayClient.get_tags()` method.

All building blocks already exist: `field_mapper.build_reverse_column_values()` (S01), `MondayClient.change_multiple_column_values()` (S01), `_find_existing_task()` SPARQL helper (S02), `_submit_commands_batched()` (S02), and the push task handler stub in `app.py` (S02). This is a light-research slice — the work is well-scoped wiring of existing patterns.

## Recommendation

Follow the Jira push sync pattern exactly. Build in this order: (1) LoopGuard module (pure Python, zero dependencies, testable in isolation), (2) dependency extraction in field_mapper + dependency edge processing in sync_engine, (3) tag resolution in sync_engine, (4) push_sync implementation replacing the stub, (5) pull_sync LoopGuard integration. Target 100+ new tests across a new `test_monday_loop_guard.py` file and extensions to the existing `test_monday_sync_engine.py` and `test_monday_field_mapper.py`.

## Implementation Landscape

### Key Files

**Existing files to modify:**

- `apps/monday-sync/services/sync_engine.py` (683 lines) — Replace `push_sync()` stub with real implementation. Add `_find_changed_tasks()` SPARQL query (clone from Jira, change provider to "monday"). Add `_get_task_body()` for body text retrieval. Add `_process_dependencies()` for dependency column → `bpkm:dependsOn` edges (analogous to Jira's `_process_issue_links()`). Add tag ID resolution via `MondayClient.get_tags()` in the pull pipeline. Integrate LoopGuard: mark pushed items in push_sync, check in pull_sync.

- `apps/monday-sync/services/field_mapper.py` (719 lines) — Add `_extract_dependency()` function for dependency column values (shape: `{"linkedPulseIds": [{"linkedPulseId": 123}]}` or `{"linkedPulsIds": [{"linkedPulseId": 456}]}`). Add `"dependency"` to `_EXTRACTORS` dict. Update `build_task_properties()` to handle `bpkm_prop == "dependency"` branch extracting linked item IDs. No changes to `build_reverse_column_values()` needed — dependency edges are not pushed back.

- `apps/monday-sync/app.py` (538 lines) — Minimal changes. The `push_changes` task handler and `sync_now` route already call `push_sync()`. May need to add `"dependency"` to `BPKM_PROPERTY_LABELS` if the column mapping UI should display it (already in `COLUMN_TYPE_COMPATIBILITY` at line 47).

- `backend/tests/test_monday_sync_engine.py` (1857 lines) — Extend with push sync tests (auth checks, direction checks, changed task detection, reverse mapping, mutation calls, lastSyncedAt updates, LoopGuard integration, error paths, partial success). Add dependency edge processing tests. Add tag resolution tests.

- `backend/tests/test_monday_field_mapper.py` (1066 lines) — Add `_extract_dependency()` tests and `build_task_properties()` tests for dependency column mapping.

**New file to create:**

- `apps/monday-sync/services/loop_guard.py` (~40-50 lines) — Per D241: `LoopGuard` class with `mark_pushed(item_id, column_id)`, `is_echo(item_id, column_id) -> bool`, `cleanup()`. In-memory `dict[str, float]` mapping `f"{item_id}:{column_id}"` → timestamp. Configurable TTL (default 30s).

- `backend/tests/test_monday_loop_guard.py` (~150-200 lines) — Dedicated test file for LoopGuard: mark+check, TTL expiry, cleanup, concurrent marks, edge cases (empty, None, repeated marks).

### What Already Exists (do NOT re-implement)

| Component | Location | Status |
|---|---|---|
| `build_reverse_column_values()` | `field_mapper.py` lines 590-680 | Complete — maps bpkm props to Monday.com column JSON |
| `_serialize_status/priority/date/text/numbers/people` | `field_mapper.py` lines 546-588 | Complete — per-type serializers for write format |
| `MondayClient.change_multiple_column_values()` | `monday_client.py` lines 302-325 | Complete — GraphQL mutation method |
| `_find_existing_task()` | `sync_engine.py` lines 39-65 | Complete — SPARQL slug lookup |
| `_submit_commands_batched()` | `sync_engine.py` lines 171-190 | Complete — batched bulk POST |
| `_build_update_commands()` | `sync_engine.py` lines 140-168 | Complete — patch/body/edge commands |
| `_compute_status()` + `_make_result()` | `sync_engine.py` lines 196-239 | Complete — result dict builders |
| `push_changes` task handler | `app.py` lines 516-527 | Complete — calls `push_sync()` |
| `sync_now` route | `app.py` lines 463-493 | Complete — calls pull then push if bidirectional |
| `MondayClient.get_tags()` | `monday_client.py` lines 267-280 | Complete — resolves tag IDs → names |
| `_extract_tags()` | `field_mapper.py` lines 295-314 | Complete — extracts tag_ids list |
| Mock infrastructure | `test_monday_sync_engine.py` lines 65-230 | Complete — MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient, MockCommandClient, MockMondayClient, SyncContext |

### Push Sync Pipeline (to implement)

The push_sync function follows the exact Jira/GitHub pattern:

1. **Auth check** — verify connection via `get_connection_status()`
2. **Sync direction check** — skip if `"pull-only"` (read from settings)
3. **Find changed tasks** — `_find_changed_tasks()` SPARQL query finding Monday-synced tasks where `dcterms:modified > bpkm:lastSyncedAt`
4. **Per-task push loop:**
   a. Read per-board column mapping config from settings (need board_id from externalUrl)
   b. Read label mappings for reverse status/priority
   c. Build reverse column values via `build_reverse_column_values()`
   d. Call `MondayClient.change_multiple_column_values(board_id, item_id, column_values_json)`
   e. Mark pushed in LoopGuard: `loop_guard.mark_pushed(item_id, "*")`
   f. Update `lastSyncedAt` via `object.patch` command
5. **Store result** in `last_push_result` state key

**Key difference from Jira/GitHub:** Monday.com push needs to extract `board_id` and `item_id` from the stored `externalUrl` (format: `https://monday.com/boards/{board_id}/pulses/{item_id}`) to call the mutation. Need a `parse_external_url(url) -> (board_id, item_id)` helper.

### Dependency Edge Processing (to implement)

Analogous to Jira's `_process_issue_links()`. During pull sync, after items are processed:

1. For each item with a mapped `dependency` column, extract linked item IDs via `_extract_dependency()`
2. For each linked item ID, compute its slug and look up its Task IRI via `_find_existing_task()`
3. Create `edge.create` commands with `predicate: bpkm:dependsOn`
4. Direction: current item depends on the linked items (same as Jira "is blocked by" pattern)

**Dependency column value shape (read):** `{"linkedPulseIds": [{"linkedPulseId": 12345}]}` — the key may vary by API version. Extract all `linkedPulseId` values.

### Tag Resolution (to implement)

Currently `_extract_tags()` returns `list[int]` (tag IDs) which get stored as-is in properties. The sync engine should resolve these to tag names via `MondayClient.get_tags(tag_ids)` before storing as `bpkm:tags` values. This is a small enhancement in the pull_sync item processing loop — collect all tag IDs across items, batch-resolve via one `get_tags()` call, then substitute names for IDs in properties.

### LoopGuard Integration (to implement)

Per D241, LoopGuard is instantiated at the start of each sync cycle:

- **In push_sync:** After each successful mutation, call `loop_guard.mark_pushed(item_id, "*")` (wildcard column since we push multiple columns)
- **In pull_sync:** Before processing each item, check `loop_guard.is_echo(item_id, "*")` — if True, skip the item (it was just pushed)
- **Cross-run prevention:** LoopGuard is in-memory only, so it only prevents echoes within the same process lifetime. The `lastSyncedAt` comparison provides the cross-run guard.

**Process-lifetime sharing:** Both push_sync and pull_sync are called from the same process (sync_now calls push after pull, scheduler calls them in separate runs). For the sync_now case, the LoopGuard instance must be shared. Simplest approach: module-level singleton `_loop_guard = LoopGuard(ttl_seconds=30)` in sync_engine.py.

### Build Order

1. **T01: LoopGuard module + tests** — Create `loop_guard.py` (pure Python, ~40 lines) and `test_monday_loop_guard.py` (~25-30 tests). Zero dependencies, testable immediately. Unblocks T03.

2. **T02: Dependency extraction + tag resolution** — Add `_extract_dependency()` to field_mapper.py. Add dependency edge processing function to sync_engine.py. Add tag ID→name resolution in pull sync. Add tests to test_monday_field_mapper.py and test_monday_sync_engine.py (~25-30 tests). Unblocks T04 (dependency edges in pull pipeline).

3. **T03: Push sync implementation** — Replace push_sync stub in sync_engine.py with real pipeline. Add `_find_changed_tasks()`, `parse_external_url()`, LoopGuard integration, per-board reverse column mapping. Add LoopGuard echo check to pull_sync. Add tests (~50-60 tests covering auth checks, direction checks, changed tasks, reverse mapping, mutations, lastSyncedAt, LoopGuard, error paths).

### Verification Approach

```bash
# All Monday.com tests pass (target: 590+ = 490 existing + 100+ new)
cd backend && uv run python -m pytest tests/test_monday_*.py -v

# New LoopGuard tests pass
cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v

# Syntax validation on all modified files
python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"
python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"
python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"

# No conflict markers
grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py
```

## Common Pitfalls

- **Monday.com `externalUrl` parsing** — The URL format is `https://monday.com/boards/{board_id}/pulses/{item_id}`. The push sync must reliably parse both `board_id` and `item_id` from this URL. Edge case: if the URL format changes or is missing, push should skip the task with a warning, not crash.
- **Column mapping per-board in push** — Push sync needs to load the correct column mapping for the board the task belongs to. Unlike pull (which iterates by board), push iterates by changed task and must extract the board from the URL, then load `column_mapping_{board_id}` and `label_mapping_{board_id}` from settings.
- **Dependency column value shape** — Monday.com's dependency column uses `linkedPulseIds` (not `linked_items` as the research doc initially suggested). The exact shape may vary: `{"linkedPulseIds": [{"linkedPulseId": 123}]}`. The extractor must handle None, empty list, and missing keys gracefully.
- **Tag IDs stored vs tag names** — Currently `_extract_tags()` returns integer IDs. The sync engine must resolve these to names before storing as `bpkm:tags` string values. The resolution needs `MondayClient.get_tags()` which is an API call — should be batched per sync run.
- **LoopGuard singleton lifetime** — If push_sync and pull_sync are called in the same `sync_now` request, the LoopGuard must be the same instance. Module-level singleton is simplest but must handle cleanup to avoid memory growth over time.
- **MockResponse data pattern** — Per KNOWLEDGE.md Pattern #2: use `data if data is not None else {}` not `data or {}`. Empty lists are falsy in Python.
