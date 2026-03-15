---
status: complete
started: 2026-03-15
completed: 2026-03-15
---
# S02 Summary: Views Rethink & VFS Scope Fixes

## What Was Done

Three interconnected fixes to make the explorer tree and VFS scoping usable at scale.

### 1. Explorer Tree Consolidation

Rewrote `/browser/views/explorer` endpoint to group ViewSpecs by model, then by type:
- Before: 31+ flat entries, one per ViewSpec (e.g., "Notes Table", "Notes Cards", "Notes Graph" all separate)
- After: Model folders → type entries. Each type appears once; carousel tab bar handles renderer switching
- Resolved model display names via `LabelService`
- Rewrote `views_explorer.html` template for nested model → type structure

### 2. Duplicate Route Cleanup

Removed 3 duplicate route definitions from `views/router.py`:
- `/explorer` (line 468, dead — first match at line 68 wins)
- `/menu` (line 507, dead — first match at line 134 wins)
- `/available` (line 565, dead — first match at line 49 wins)
- Router: 594 → 507 lines

### 3. VFS Scope Fixes

**Frontend:** Fixed scope dropdown fetch URL from `/api/sparql/queries` (404) → `/api/sparql/saved?include_shared=true`. Added optgroup rendering for My Queries / Model Queries / Shared.

**Backend:** `build_scope_filter()` now accepts `resolved_query_text` parameter. Added `_extract_where_body()` to parse SPARQL WHERE clauses. Added `_resolve_saved_query_text()` async helper to look up query text from triplestore. Both mount endpoints now resolve `saved_query_id` before building scope filter.

**WebDAV:** Left as-is (sync context can't do async query resolution). Documented as limitation.

## Files Modified (6) + New (2)

- `backend/app/views/router.py` — rewritten explorer, removed duplicates
- `backend/app/templates/browser/views_explorer.html` — model-grouped template
- `frontend/static/js/workspace.js` — fixed fetch URL, optgroup rendering
- `backend/app/vfs/strategies.py` — `build_scope_filter` + `_extract_where_body`
- `backend/app/browser/workspace.py` — `_resolve_saved_query_text` + wired to callers
- `backend/app/vfs/mount_collections.py` — documented WebDAV limitation
- `backend/tests/test_vfs_scope.py` (new, 10 tests)
- `.gsd/milestones/M006/slices/S02/S02-PLAN.md` (new)

## Verification

- 558 tests pass (10 new)
- Zero conflict markers
