---
estimated_steps: 8
estimated_files: 4
---

# T02: Add dependency extraction, tag resolution, and dependency edge processing

**Slice:** S03 — Push sync + LoopGuard + dependency edges
**Milestone:** M024

## Description

Extends the pull-side pipeline to handle dependency columns (MON-11) and resolve tag IDs to names (MON-12). Dependency extraction goes in `field_mapper.py`, dependency edge processing and tag resolution go in `sync_engine.py`. This completes the pull sync's data fidelity — after this task, dependency columns produce `bpkm:dependsOn` edges and tags resolve to human-readable names.

The dependency edge pattern follows Jira's `_process_issue_links()` exactly: iterate items with dependency data, look up target task IRIs via slug, create `edge.create` commands.

**Relevant skills:** `test` skill for test patterns.

## Steps

1. **Add `_extract_dependency()` to `field_mapper.py`** (after `_extract_dropdown`, before `_EXTRACTORS`):
   ```python
   def _extract_dependency(col_value: str | dict | None) -> list[int]:
       """Extract linked item IDs from a Monday.com dependency column.

       Dependency column value shape (read):
       ``{"linkedPulseIds": [{"linkedPulseId": 12345}]}``

       Returns:
           List of integer item IDs (empty list if no dependencies).
       """
       parsed = _parse_col_value(col_value)
       if parsed is None:
           return []
       if isinstance(parsed, dict):
           linked = parsed.get("linkedPulseIds", [])
           if isinstance(linked, list):
               return [
                   int(lp["linkedPulseId"])
                   for lp in linked
                   if isinstance(lp, dict) and "linkedPulseId" in lp
               ]
       return []
   ```

2. **Register `"dependency"` in `_EXTRACTORS` dict** in `field_mapper.py`:
   ```python
   _EXTRACTORS: dict[str, callable] = {
       "date": _extract_date,
       "people": _extract_people,
       "text": _extract_text,
       "long_text": _extract_long_text,
       "numbers": _extract_numbers,
       "tags": _extract_tags,
       "dropdown": _extract_dropdown,
       "dependency": _extract_dependency,  # NEW
   }
   ```

3. **Handle `dependency` in `build_task_properties()`** — in the per-column loop of `build_task_properties()`, add a branch for `bpkm_prop == "dependency"`. Since dependencies are not simple property values but reference other items by ID, store them in a special temp key `_dependency_item_ids` (not under the BPKM namespace) so the sync engine can process them separately:
   ```python
   elif bpkm_prop == "dependency":
       dep_ids = _extract_dependency(raw_value)
       if dep_ids:
           props["_dependency_item_ids"] = dep_ids
   ```
   This key gets popped by the sync engine before creating commands and is never written to the graph.

4. **Add `_process_dependencies()` to `sync_engine.py`** (after Phase 3 subitem processing, before follow-up submission). This function:
   - Takes a list of `(item_id, dependency_item_ids)` tuples collected during per-item processing
   - For each dependency, computes the target item's slug (requires knowing the target's name — but we only have the ID; so look up by `externalUrl` containing `/pulses/{dep_id}` using a helper query)
   - Actually simpler: use `_find_existing_task_by_external_url(graph_client, item_id)` approach — query for tasks whose `externalUrl` contains `/pulses/{dep_id}`
   - Create `edge.create` commands: source = current item, predicate = `bpkm:dependsOn`, target = dependency task IRI
   - Per-dependency error isolation with logging

   Implementation detail: Add a helper `_find_task_by_monday_item_id(graph_client, item_id)` that queries:
   ```sparql
   SELECT ?task WHERE {
     ?task a <{BPKM}Task> .
     ?task <{BPKM}externalProvider> "monday" .
     ?task <{BPKM}externalUrl> ?url .
     FILTER(CONTAINS(STR(?url), "/pulses/{item_id}"))
   } LIMIT 1
   ```

5. **Add tag resolution in pull_sync**:
   - During per-item processing, when `properties` contains tag ID lists (from `_extract_tags()` via the `tags` column type), collect all tag IDs into a set
   - After the per-board item loop, batch-resolve tag IDs via `monday_client.get_tags(list(all_tag_ids))` — one API call per board
   - Build an `id→name` lookup dict from the response
   - Before creating commands, substitute tag names for IDs in each item's properties. The property value for `bpkm:tags` should be a comma-separated string of tag names (or a list depending on what the property expects)
   - If tag resolution fails (API error), fall back to storing string IDs

6. **Wire dependency processing as Phase 4 in pull_sync**:
   - During per-item processing, collect `(item_slug, dependency_item_ids)` into a list when `_dependency_item_ids` is present in properties (pop it before creating commands)
   - After Phase 3, run `_process_dependencies()` to generate `edge.create` commands
   - Add dependency edge count to `_make_result()` output as `dependency_edges` key

7. **Extend `_make_result()` in sync_engine.py** to accept and include `dependency_edges` count (default 0).

8. **Add tests** (~25-30 new tests):
   - In `test_monday_field_mapper.py`:
     - `test_extract_dependency_normal` — `{"linkedPulseIds": [{"linkedPulseId": 123}]}` → `[123]`
     - `test_extract_dependency_multiple` — multiple linked items
     - `test_extract_dependency_empty_list` — `{"linkedPulseIds": []}` → `[]`
     - `test_extract_dependency_none` — None → `[]`
     - `test_extract_dependency_missing_key` — `{}` → `[]`
     - `test_extract_dependency_malformed_entry` — `{"linkedPulseIds": [{"foo": 1}]}` → `[]`
     - `test_extract_dependency_mixed_valid_invalid` — some valid, some invalid entries
     - `test_extract_dependency_string_value` — JSON string wrapping
     - `test_build_task_properties_with_dependency` — dependency column mapped, `_dependency_item_ids` in output
     - `test_build_task_properties_dependency_popped_for_graph` — dependency IDs don't leak into BPKM properties
   - In `test_monday_sync_engine.py`:
     - `test_find_task_by_monday_item_id_found` — SPARQL lookup returns task
     - `test_find_task_by_monday_item_id_not_found` — returns None
     - `test_process_dependencies_creates_edges` — dependency IDs produce edge.create commands
     - `test_process_dependencies_missing_target_skipped` — target not in graph → no edge
     - `test_process_dependencies_empty_list` — no dependencies → no commands
     - `test_process_dependencies_error_isolation` — one failure doesn't stop others
     - `test_pull_sync_resolves_tags` — tag IDs replaced with names in properties
     - `test_pull_sync_tag_resolution_fallback` — API failure falls back to IDs
     - `test_pull_sync_with_dependency_edges` — pull sync includes dependency edge count in result
     - `test_make_result_includes_dependency_edges` — result dict has `dependency_edges` key
   - Add `get_tags()` method to `MockMondayClient` in the test file — return configurable tag dicts

## Must-Haves

- [ ] `_extract_dependency()` function in `field_mapper.py` handles all documented value shapes
- [ ] `"dependency"` registered in `_EXTRACTORS` dict
- [ ] `build_task_properties()` stores dependency IDs in `_dependency_item_ids` temp key
- [ ] `_find_task_by_monday_item_id()` SPARQL helper in `sync_engine.py`
- [ ] `_process_dependencies()` creates `bpkm:dependsOn` `edge.create` commands
- [ ] Tag IDs resolved to names via `MondayClient.get_tags()` batch call in pull_sync
- [ ] `_make_result()` includes `dependency_edges` count
- [ ] 25+ new tests passing across both test files
- [ ] All existing Monday.com tests still pass (no regressions)

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_field_mapper.py -v` — all pass (existing + new)
- `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` — all pass (existing + new)
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` — valid syntax
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — valid syntax

## Observability Impact

- Signals added: `dependency_edges` count in `last_pull_result` JSON; `_process_dependencies` logs per-dependency errors at WARNING level
- How a future agent inspects this: read `last_pull_result` state key — `dependency_edges` shows edge creation count
- Failure state exposed: per-dependency errors logged individually; missing targets silently skipped with debug log

## Inputs

- `apps/monday-sync/services/field_mapper.py` — `_EXTRACTORS` dict at line 353, `build_task_properties()` loop, `_parse_col_value()` helper, `build_external_url()` at line 369
- `apps/monday-sync/services/sync_engine.py` — `pull_sync()` at line 309, `_find_existing_task()` at line 60, `_make_result()` at line 272, `_submit_commands_batched()` at line 224
- `backend/tests/test_monday_sync_engine.py` — mock infrastructure (MockGraphClient, MockMondayClient, SyncContext) at lines 65-230
- `backend/tests/test_monday_field_mapper.py` — existing `_extract_tags` tests as pattern reference
- Monday.com dependency column value shape: `{"linkedPulseIds": [{"linkedPulseId": 12345}]}`
- KNOWLEDGE.md Pattern #2: `data if data is not None else {}` for MockResponse

## Expected Output

- `apps/monday-sync/services/field_mapper.py` — MODIFIED: `_extract_dependency()` function, `"dependency"` in `_EXTRACTORS`, dependency branch in `build_task_properties()`
- `apps/monday-sync/services/sync_engine.py` — MODIFIED: `_find_task_by_monday_item_id()`, `_process_dependencies()`, tag resolution in pull_sync, Phase 4 dependency wiring, `_make_result()` extended with `dependency_edges`
- `backend/tests/test_monday_field_mapper.py` — MODIFIED: 10+ new dependency extraction tests
- `backend/tests/test_monday_sync_engine.py` — MODIFIED: 15+ new dependency/tag tests, `MockMondayClient.get_tags()` method added
