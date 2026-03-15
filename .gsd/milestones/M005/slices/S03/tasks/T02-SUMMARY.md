---
id: T02
parent: S03
milestone: M005
provides:
  - Hierarchical tag tree wired into explorer UI with endpoint, template, and CSS integration
key_files:
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/tag_tree.html
  - backend/app/templates/browser/tag_tree_folder.html
  - frontend/static/css/workspace.css
  - backend/tests/test_tag_explorer.py
key_decisions:
  - Prefix mode in tag_children also fetches direct objects for the exact prefix value (handles tags that are both leaf and folder)
  - Folder nodes use folder icon, leaf tag nodes use tag icon with # prefix in label
  - SPARQL for prefix mode uses OR filter (STRSTARTS || exact match) to get both descendants and direct-tagged objects in one query
patterns_established:
  - tag_tree_folder.html renders both sub-folder nodes and leaf tag nodes with same tree-node/tree-children pattern for initTreeToggle() compatibility
  - tree-count-badge CSS class for count pills in explorer tree (margin-left:auto pushes to right edge)
observability_surfaces:
  - logger.debug("By-tag explorer: %d root nodes", ...) in _handle_by_tag
  - logger.debug("Tag children for prefix '%s': %d sub-nodes, %d direct objects", ...) in tag_children prefix path
  - HTTP 400 with "Missing required parameter: tag or prefix" when neither param provided
duration: 35m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Wire hierarchical tree into endpoints, templates, and CSS

**Connected `build_tag_tree()` pure function to live explorer UI: `_handle_by_tag()` returns hierarchical root nodes, `tag_children` supports prefix-based sub-folder expansion, new recursive template and count badge CSS added.**

## What Happened

1. Imported `build_tag_tree` in `workspace.py` and modified `_handle_by_tag()` to pass flat SPARQL results through the tree builder before rendering. Template context changed from `folders` to `nodes`.

2. Extended `tag_children` endpoint with optional `prefix` parameter. When `prefix` is provided: runs SPARQL with `STRSTARTS` filter to get all descendant tags, passes through `build_tag_tree(tag_values, prefix=prefix)`, and renders `tag_tree_folder.html`. Also fetches direct objects tagged with the exact prefix value when applicable. When only `tag` is provided: existing exact-match behavior preserved unchanged. When neither: returns 400.

3. Updated `tag_tree.html` to render hierarchical root nodes — folder nodes (has_children) get `hx-get` with `prefix` param and folder icon, leaf nodes get `hx-get` with `tag` param and tag icon with `#` prefix.

4. Created `tag_tree_folder.html` for recursive sub-folder rendering — same pattern as root template, plus a section for direct objects tagged with the parent prefix.

5. Added `.tree-count-badge` CSS rule in workspace.css matching `.abox-count-badge` style with `margin-left: auto` to push badges to the right edge.

6. Extended `test_tag_explorer.py` with `TestHandlerUsesBuildTagTree` (3 tests) and `TestTagChildrenPrefixParameter` (9 tests) test classes.

## Verification

- `python -m pytest tests/test_tag_explorer.py tests/test_tag_tree_builder.py -v` — **61/61 passed** (33 explorer + 28 tree builder)
- Browser: "By Tag" mode shows hierarchical folders with counts
  - `architect` (9) → expands to `#build` (7), `#renovate` (2)
  - `garden` (39) → expands to `#cultivate` (12), `#plant` (13), `#probe` (1), `#question` (5), `#repot` (3)
  - `#architecture` (leaf, 3) → expands to show 3 tagged objects with type icons
  - Flat tags (no `/`) still work as before
- Failure path: `/explorer/tag-children?prefix=nonexistent` → "No tags found" (no crash)
- Missing params: `/explorer/tag-children` → HTTP 400 "Missing required parameter: tag or prefix"
- browser_assert: 4/4 checks passed (tag-folder visible, tree-count-badge visible, garden text, architect text)

### Slice-level verification status:
- ✅ `python -m pytest tests/test_tag_tree_builder.py -v` — 28/28 pass
- ✅ `python -m pytest tests/test_tag_explorer.py -v` — 33/33 pass
- ✅ Browser: "By Tag" mode shows hierarchical folders, expanding shows sub-folders or objects
- ✅ Failure-path: nonexistent prefix returns empty folder list (no crash)

## Diagnostics

- Runtime: `logger.debug` in `_handle_by_tag` shows root node count; `tag_children` prefix path logs sub-node and direct object counts
- Network: browser dev tools shows `/explorer/tag-children?prefix=...` and `?tag=...` requests
- Error: SPARQL failures surface via `_execute_sparql_select` (logs warning, returns empty list → "No tags found")

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/workspace.py` — imported `build_tag_tree`, modified `_handle_by_tag()` to use tree builder, extended `tag_children()` with `prefix` parameter
- `backend/app/templates/browser/tag_tree.html` — rewritten for hierarchical root nodes with folder/tag icons
- `backend/app/templates/browser/tag_tree_folder.html` — new recursive sub-folder template
- `frontend/static/css/workspace.css` — added `.tree-count-badge` CSS rule
- `backend/tests/test_tag_explorer.py` — extended with hierarchy and prefix parameter tests
- `.gsd/milestones/M005/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section
