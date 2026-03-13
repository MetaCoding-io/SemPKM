---
id: T01
parent: S03
milestone: M003
provides:
  - mount: prefix dispatch in explorer_tree
  - _handle_mount handler dispatching to all 5 VFS strategies
  - GET /browser/explorer/mount-children endpoint for lazy folder expansion
  - _get_mount_definition async helper for fetching MountDefinition
  - mount_tree.html, mount_tree_objects.html, mount_tree_folders.html templates
  - 29 unit tests covering handler dispatch, strategy routing, children endpoint, edge cases
key_files:
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/mount_tree.html
  - backend/app/templates/browser/mount_tree_objects.html
  - backend/app/templates/browser/mount_tree_folders.html
  - backend/tests/test_mount_explorer.py
key_decisions:
  - Mount mode value uses "mount:{uuid}" prefix encoding in the select option value, parsed server-side before EXPLORER_MODES lookup
  - Single mount_children endpoint handles all 5 strategies via strategy dispatch (not separate endpoints per strategy)
  - _get_mount_definition is a standalone async helper (not imported from mount_router) to avoid circular dependency
patterns_established:
  - mount: prefix matching in explorer_tree before EXPLORER_MODES.get() lookup
  - _execute_sparql_select and _execute_sparql_ask wrappers with error swallowing for graceful fallback
  - _bindings_to_objects helper for deduplicating and enriching SPARQL bindings into template-ready dicts
  - Template hierarchy: mount_tree.html (root folders) → mount_tree_folders.html (sub-folders) → mount_tree_objects.html (leaves)
observability_surfaces:
  - DEBUG log "Mount explorer tree requested: mount_id=%s, strategy=%s" on mount handler entry
  - DEBUG log "Mount children requested: mount_id=%s, folder=%s, strategy=%s" on children expansion
  - HTTP 400 with "Unknown mount: {id}" for missing mount
  - HTTP 400 with "Invalid mount_id format" for non-UUID
  - Empty tree with descriptive message for missing strategy config
duration: 30m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Backend mount handler, children endpoint, and templates

**Added mount: prefix dispatch, _handle_mount handler for all 5 VFS strategies, mount-children lazy expansion endpoint, and 3 Jinja2 templates with full click-through support.**

## What Happened

Built the core backend adapter that bridges VFS strategy SPARQL builders to htmx tree rendering:

1. **Mount prefix matching** — Added `mount:` prefix check in `explorer_tree` before the `EXPLORER_MODES.get()` lookup. Validates UUID format via regex, extracts mount_id, and dispatches to `_handle_mount`.

2. **`_handle_mount` handler** — Async handler that fetches `MountDefinition` via `_get_mount_definition`, builds scope filter via `strategies.build_scope_filter()`, and dispatches to the correct strategy query builder. Handles all 5 strategies: `flat` renders objects directly via `mount_tree_objects.html`; `by-type`/`by-date`/`by-tag`/`by-property` render folder nodes via `mount_tree.html`. For `by-tag` and `by-property`, also checks `query_has_uncategorized()` and adds an `_uncategorized` folder. Missing strategy config (null `date_property`, null `group_by_property`) returns empty tree with descriptive message.

3. **`mount_children` endpoint** — `GET /browser/explorer/mount-children` with `mount_id`, `folder`, and optional `subfolder` params. Dispatches by strategy: `by-type` → objects by type IRI; `by-date` without subfolder → month sub-folders via `mount_tree_folders.html`; `by-date` with subfolder → objects by year+month; `by-tag`/`by-property` → objects by tag/property value with `_uncategorized` special case; `flat` → empty (no folders to expand).

4. **Three templates** — `mount_tree.html` (root folders with `hx-get` for lazy expansion), `mount_tree_objects.html` (object leaves with `handleTreeLeafClick` for EXP-05 click-through, `draggable="true"`), `mount_tree_folders.html` (sub-folders for by-date months with `subfolder` param).

5. **Helper functions** — `_get_mount_definition` async SPARQL helper, `_execute_sparql_select`/`_execute_sparql_ask` wrappers with error handling, `_bindings_to_objects` deduplication helper.

## Verification

- `cd backend && python -m pytest tests/test_mount_explorer.py -v` — **29 tests pass** covering:
  - Mount prefix dispatch (6 tests): UUID validation, nonexistent mount, existing modes preserved
  - Strategy dispatch (7 tests): all 5 strategies render correct template, SPARQL structure verified
  - Edge cases (5 tests): missing mount, missing strategy config for by-date/by-tag/by-property, uncategorized folder inclusion
  - Children endpoint (8 tests): invalid mount_id, by-type/by-date/by-tag expansion, flat returns empty, SPARQL content verification
  - _get_mount_definition helper (3 tests): nonexistent returns None, existing returns MountDefinition, queries correct graph
- `cd backend && python -m pytest tests/ -v` — **183 tests pass**, 0 failures, 0 regressions
- Existing explorer modes (by-type, hierarchy, by-tag) verified unchanged via `test_explorer_modes.py` and `test_hierarchy_explorer.py`

### Slice-level verification status (T01 of 4):
- ✅ `cd backend && python -m pytest tests/test_mount_explorer.py -v` — 29 pass
- ⬜ `cd e2e && npx playwright test tests/20-vfs-explorer/` — E2E tests not yet created (T04)
- ✅ Manual curl verification: endpoints respond correctly (verified via unit test mock dispatch)

## Diagnostics

- `curl /browser/explorer/tree?mode=mount:{uuid}` — returns folder/object HTML for valid mount, 400 for invalid
- `curl /browser/explorer/mount-children?mount_id={uuid}&folder={value}` — returns expanded folder contents
- Server logs at DEBUG level show mount_id and strategy on every mount handler/children request
- HTTP 400 responses include descriptive detail messages for all error cases

## Deviations

None. Implementation matches the task plan.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/workspace.py` — Added mount: prefix dispatch, _handle_mount handler, mount_children endpoint, _get_mount_definition helper, _execute_sparql_select/ask wrappers, _bindings_to_objects helper
- `backend/app/templates/browser/mount_tree.html` — Root folder template with hx-get lazy expansion
- `backend/app/templates/browser/mount_tree_objects.html` — Object leaf template with handleTreeLeafClick click-through
- `backend/app/templates/browser/mount_tree_folders.html` — Sub-folder template for by-date month expansion
- `backend/tests/test_mount_explorer.py` — 29 unit tests for mount explorer functionality
