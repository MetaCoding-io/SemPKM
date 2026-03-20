# S02: Column mapping configuration UI + pull sync — Research

**Date:** 2026-03-19

## Summary

S02 builds three things on top of S01's scaffold: (1) column mapping configuration UI that lets users map Monday.com columns to bpkm properties and map status/priority labels to enum values, (2) the pull sync engine that uses those stored mappings to create bpkm:Task objects, and (3) groups-as-taskGroup and subitems-as-parentTask support.

This is moderate-complexity work following established patterns. The sync engine follows the exact Jira/Linear two-phase bulk pattern (already in `apps/jira-sync/services/sync_engine.py` and `apps/linear-sync/services/sync_engine.py`). The column mapping UI is the novel part — it's an htmx form with server-populated dropdowns filtered by column type, plus a second step for status/priority label mapping. No JavaScript framework is needed; the existing htmx + Jinja2 template pattern in connect_status.html handles it.

The S01 deliverables are clean and complete — 277 tests pass, all service modules exist with the interfaces S02 needs. The field mapper already accepts `column_mapping`, `status_label_mapping`, and `priority_label_mapping` as parameters. The sync engine just needs to read those from state and pass them through.

## Recommendation

Build in 4 tasks:

1. **Column mapping UI** — New routes (`configure-columns` GET, `save-column-mapping` POST, `configure-labels` GET, `save-label-mapping` POST) and templates (`configure_columns.html`, `configure_labels.html`) in app.py. Extend connect_status.html to show a "Configure Columns" button per board. This is the novel, highest-risk work — build it first to flush out UI issues early.

2. **Extend MondayClient for groups and subitems** — Add `group { id title }` to the `get_board_items` GraphQL query (currently missing), add `get_subitems(item_ids)` method for subitem fetching, add `get_board_items_with_subitems` wrapper. Add unit tests.

3. **Sync engine** — Clone the Jira sync_engine pattern: `pull_sync(ctx)` that reads stored column mapping config from state, calls `get_all_board_items()` per selected board, builds tasks via `build_task_properties()` with the stored mapping, does two-phase bulk create, and handles groups→taskGroup + subitems→parentTask. Add `push_sync(ctx)` stub that returns `{"status": "skipped"}` (real push is S03). This is the largest file but follows a completely established pattern.

4. **Unit tests** — Test column mapping UI routes (mock state/client), test extended client methods, test sync engine with mock clients. Target: 150+ tests across 2 new files (test_monday_sync_engine.py, test_monday_column_mapping.py).

## Implementation Landscape

### Key Files

**Files to create:**
- `apps/monday-sync/services/sync_engine.py` — Pull sync engine following Jira/Linear two-phase bulk pattern. ~400 lines. Functions: `pull_sync(ctx)`, `push_sync(ctx)` (stub), `_find_existing_task(graph, slug)`, `_build_create_command()`, `_build_update_commands()`, `_submit_commands_batched()`, `_make_result()`, `_compute_status()`.
- `apps/monday-sync/frontend/templates/configure_columns.html` — Column mapping form rendered per board. Shows discovered columns as dropdown sources, filtered by type. Each bpkm property ("Status", "Priority", "Due Date", etc.) gets a `<select>` populated with type-compatible columns + "None".
- `apps/monday-sync/frontend/templates/configure_labels.html` — Status and priority label mapping form. For each discovered status label on the mapped status column, shows a dropdown of bpkm:taskStatus values. Same for priority.
- `backend/tests/test_monday_sync_engine.py` — Sync engine tests following the Jira test structure (MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient). ~100+ tests.
- `backend/tests/test_monday_column_mapping.py` — Column mapping route handler tests. ~50+ tests.

**Files to modify:**
- `apps/monday-sync/app.py` — Add 4 new routes for column mapping UI + label mapping UI. Add `configure-columns` GET (renders column mapping form with board columns), `save-column-mapping` POST (stores mapping to state), `configure-labels` GET (renders label mapping form from column settings_str), `save-label-mapping` POST (stores label mappings). Update `sync_now` to use real `pull_sync`. Wire `pull_sync` import. ~100 lines added.
- `apps/monday-sync/services/monday_client.py` — Extend `get_board_items` GraphQL query to include `group { id title }` in the items fields. Add `get_subitems(item_ids)` method. ~40 lines added.
- `apps/monday-sync/frontend/templates/connect_status.html` — Add "Configure Columns" link/button per selected board (or a single section if mapping is per-board). Show column mapping status indicator.
- `apps/monday-sync/frontend/static/styles.css` — Add CSS for column mapping form (dropdowns, label mapping grid). ~80 lines added.

**Pattern files to follow (do NOT modify):**
- `apps/jira-sync/services/sync_engine.py` — Reference for pull_sync structure: auth check → read config → fetch items → classify create/update → Phase 1 create → Phase 2 body+edges → store state. **553 lines.**
- `apps/linear-sync/services/sync_engine.py` — Simpler reference (no Epics). **529 lines.**
- `apps/monday-sync/services/field_mapper.py` — Already built. `build_task_properties(item, column_mapping, status_label_mapping, priority_label_mapping, board_id, sync_time)` returns `(props, assignee_user_id)`. Uses it as-is.
- `apps/monday-sync/services/person_matcher.py` — Already built. `PersonMatcher.resolve(user_id, display_name)` resolves Monday.com user IDs. Uses it as-is.

### Critical Implementation Details

**Column mapping state shape (per-board, stored as JSON in settings):**
```python
# Key: f"column_mapping_{board_id}"
# Value: JSON string of:
{
    "column_mapping": {
        "taskStatus": "status_col_id",
        "priority": "priority_col_id",
        "dueDate": "date4",
        "assignedTo": "people_col",
        "description": "long_text_col",
        "estimatedEffort": "numbers_col",
        "tags": "tags_col"
    },
    "status_label_mapping": {
        "": "todo",
        "Working on it": "in-progress",
        "Done": "done",
        "Stuck": "blocked"
    },
    "priority_label_mapping": {
        "Low": "low",
        "Medium": "medium",
        "High": "high",
        "Critical ⚨": "critical"
    }
}
```

**Column type → bpkm property compatibility (for dropdown filtering):**
```python
COLUMN_TYPE_COMPATIBILITY = {
    "taskStatus": ["status"],           # status-type columns only
    "priority": ["status", "color"],    # status-type or color-type
    "dueDate": ["date", "timeline"],    # date or timeline columns
    "assignedTo": ["people"],           # people columns only
    "description": ["text", "long_text"], # text columns
    "estimatedEffort": ["numbers"],     # numbers columns
    "tags": ["tags", "dropdown"],       # tags or dropdown columns
    "dependency": ["dependency"],       # dependency columns
}
```

**Status label discovery from `settings_str`:**
Monday.com status columns have labels in `settings_str` JSON:
```json
{"labels": {"0": "", "1": "Working on it", "2": "Done", "5": "Stuck"}, "done_colors": [2], ...}
```
Parse `settings_str` → extract `labels` dict → present as label mapping options.

**Groups in items query — MUST ADD to get_board_items:**
Current query: `items { id name column_values { ... } }`
Needed: `items { id name group { id title } column_values { ... } }`
Without this, group→taskGroup mapping is impossible. The group info comes at the item level, not via column_values.

**Subitem handling:**
Monday.com subitems live on a separate auto-generated board. To fetch subitems, query `{ items(ids: [...]) { subitems { id name group { id title } column_values { ... } } } }`. Subitems are linked to parents via `bpkm:parentTask` edges. The sync engine should:
1. Fetch regular items from selected boards
2. Check if any items have subitems (query `subitems { id }`)
3. Fetch subitem details
4. Create subitem tasks with `bpkm:parentTask` edge to parent

**Pull sync flow for Monday.com (differs from Jira/Linear):**
1. Auth check
2. Read selected boards from settings
3. For each board: read column mapping config from settings
4. For each board: `get_all_board_items(board_id)` → paginated items with groups
5. For each item: `build_task_properties(item, column_mapping, status_map, priority_map, board_id)`
6. Resolve assignee via PersonMatcher (if `assignee_user_id` returned)
7. Set `taskGroup` from `item["group"]["title"]` (not from column value)
8. Classify as create/update via `_find_existing_task(graph, slug)`
9. Content comparison for change detection (no `updated_at` field)
10. Phase 1: submit create commands
11. Phase 2: discover IRIs, submit body+edge commands
12. Phase 3: subitem→parentTask edges
13. Store sync timestamp

**Group handling is item-level, not column-level:**
The roadmap says "Board groups appear as taskGroup values". Monday.com groups are NOT columns — they're organizational sections within a board (like "Sprint 1", "Backlog"). Each item belongs to exactly one group. The group info is at `item["group"]["title"]`. The sync engine should set `bpkm:taskGroup` from the group title directly, bypassing the column mapping entirely.

### Build Order

1. **Column mapping UI routes + templates** (highest risk, novel work) — Build the column mapping configuration routes and templates first. This is the only novel pattern in the slice. Proves the settings flow works: board columns discovered → type-filtered dropdowns → mapping saved to state → label mapping configured. Once this works, the sync engine just reads the stored config.

2. **Extend MondayClient for groups** — Add `group { id title }` to get_board_items query. Quick, low-risk, but blocks sync engine work.

3. **Sync engine** — Clone Jira pattern with Monday.com specifics: per-board iteration, stored column mapping config, group→taskGroup from item.group (not column), subitem→parentTask edges. This is the largest file but follows an established pattern exactly.

4. **Tests** — Unit tests for sync engine (mock clients), column mapping routes (mock state/settings/client). Tests should be written alongside or immediately after each of the above.

### Verification Approach

- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py tests/test_monday_column_mapping.py -v` — new S02 tests
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` — all Monday tests (S01 + S02) together, should total 427+
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — syntax check
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — syntax check after route additions
- Verify all 7 expected Python files exist in `apps/monday-sync/services/` (4 from S01 + sync_engine.py = 5 services + __init__.py)
- Verify column mapping template renders dropdowns filtered by column type
- Verify pull_sync creates Task objects with correct properties from stored mapping

## Constraints

- **htmx template URLs must use `/app/monday-sync/` prefix** — per KNOWLEDGE.md. All htmx hx-post/hx-get attributes in templates must be prefixed.
- **Settings stored as JSON strings** — StateClient/SettingsClient only store string values. Column mapping config must be JSON-serialized.
- **Column mapping is per-board** — Different boards have different column schemas. Stored as `column_mapping_{board_id}` in settings.
- **No `updated_at` filter** — Monday.com items don't have a reliable updated_at in the items query. Change detection must use content comparison against stored bpkm values (compare slug-looked-up properties with newly-built properties), or rely solely on `lastSyncedAt` timestamp.
- **Bulk commands bypass SDK** — Must POST directly to `/api/commands/bulk` via `ctx.commands._client` to bypass IRI prefix enforcement (same as Jira/Linear pattern).

## Common Pitfalls

- **Group data is NOT in column_values** — The `group { id title }` field must be added to the items GraphQL query. It's a peer of `column_values`, not a column value. The current `get_board_items` query is missing it. If forgotten, all items will have no taskGroup.
- **settings_str is a JSON string, not a dict** — `get_board_columns()` returns `settings_str` as a raw JSON string. Must parse it with `json.loads()` before extracting label names. Empty or malformed `settings_str` should be handled gracefully.
- **Status label mapping must include the empty string** — In Monday.com, an empty status label (`""`) means "not started". The mapping UI should show this as "Default / Not Started" and map it to "todo".
- **Subitem board IDs are different** — Subitems live on a separate auto-generated board, not the parent board. The `get_board_items` query for the parent board won't include subitems. Need a separate query or an `items(ids: [...]) { subitems { ... } }` approach.
- **Column IDs are opaque strings, not human-readable** — Column IDs like `"status"`, `"date4"`, `"people_col"` are board-specific. The UI must show column `title` to the user but store the column `id` in the mapping.
- **Multiple boards: each needs its own mapping** — If user selects boards A and B, they might have completely different columns. The mapping config must be per-board. The UI should show one mapping form per board, or navigate board-by-board.

## Open Risks

- **Large board performance** — Boards with 1000+ items will require many paginated queries. The `get_all_board_items` wrapper already handles this with MAX_PAGINATION_PAGES=50 (5000 items max). Content comparison for change detection adds CPU overhead but is purely local.
- **Subitem API complexity budget** — Querying subitems alongside parent items may hit complexity limits. If the subitem query is too expensive, the fallback is to skip subitems and document the limitation.
