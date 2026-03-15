---
estimated_steps: 8
estimated_files: 6
---

# T02: Wire hierarchical tree into endpoints, templates, and CSS

**Slice:** S03 — Hierarchical Tag Tree
**Milestone:** M005

## Description

Connect the `build_tag_tree()` pure function to the live explorer UI. Modify the `_handle_by_tag()` handler to pass flat SPARQL results through the tree builder and render root-level folders. Extend the `tag_children` endpoint to support prefix-based sub-folder queries alongside exact-match object queries. Create a recursive sub-folder template. Add missing `tree-count-badge` CSS. Update existing tests.

## Steps

1. **Import and wire `build_tag_tree` in `_handle_by_tag()`:**
   - Import `build_tag_tree` from `app.browser.tag_tree`
   - Keep existing SPARQL query unchanged
   - After getting bindings, build `tag_values = [{"value": ..., "count": ...}]` list (already done)
   - Pass through `build_tag_tree(tag_values)` to get root-level nodes
   - Pass root nodes (not flat folders) to the updated `tag_tree.html` template

2. **Extend `tag_children` endpoint with `prefix` parameter:**
   - Add `prefix: str | None = None` query parameter
   - When `prefix` is provided:
     - Run SPARQL with `FILTER(STRSTARTS(?tagValue, "{escaped_prefix}/"))` to get all descendant tags
     - Pass results through `build_tag_tree(tag_values, prefix=prefix)`
     - If result nodes have `has_children=True`, render `tag_tree_folder.html` (sub-folders)
     - If result nodes have `has_children=False`, render them as leaf entries that expand to objects
     - Mix both: render a list of sub-folders and leaf-tag entries together
   - When only `tag` is provided: keep existing exact-match behavior unchanged
   - When neither `tag` nor `prefix`: return 400

3. **Update `tag_tree.html` for hierarchical root nodes:**
   - Change loop variable from `folders` to `nodes` (or keep `folders` — match template context)
   - Render each root node as a `.tree-node` with:
     - `hx-get="/browser/explorer/tag-children?prefix={{ node.prefix | urlencode }}"` for folder nodes with children
     - `hx-get="/browser/explorer/tag-children?tag={{ node.prefix | urlencode }}"` for leaf nodes (no children, direct objects only)
     - Count badge showing `total_count`
   - Nodes with both `has_children` AND `direct_count > 0`: render as expandable folder (children query returns sub-folders + direct objects)

4. **Create `tag_tree_folder.html` for recursive sub-folder rendering:**
   - Template receives `nodes` (sub-folders/leaf tags) context
   - Sub-folder nodes get `hx-get` with `prefix` for deeper expansion
   - Leaf tag nodes get `hx-get` with `tag` for object expansion
   - Follows `.tree-node` + `.tree-children` pattern for `initTreeToggle()` compatibility
   - Use `tag` icon for leaf tags, `folder` icon for folders with children
   - Include count badge on each node

5. **Handle mixed sub-folder + leaf rendering in `tag_children` prefix response:**
   - When expanding prefix `garden`, the response may contain:
     - Sub-folders: `cultivate` (has_children=True)
     - Leaf tags: `roses` (has_children=False, the tag `garden/roses` has direct objects)
     - Direct objects: objects tagged exactly `garden` (if direct_count > 0)
   - Template renders sub-folders first, then leaf tags, then direct objects (if any)
   - For direct objects: include an inline SPARQL fetch or a separate `hx-get` with `tag=garden`

6. **Add `.tree-count-badge` CSS in workspace.css:**
   - Style similar to `.abox-count-badge` (small pill with muted colors)
   - Place in the explorer tree section of workspace.css

7. **Update `test_tag_explorer.py`:**
   - Add test that `_handle_by_tag` source now calls `build_tag_tree`
   - Add test that `tag_children` accepts `prefix` parameter
   - Existing tests should still pass (handler signature unchanged)

8. **Browser verification (manual):**
   - Start Docker stack
   - Open workspace, select "By Tag" mode
   - Verify root nodes render as folders with counts
   - Expand a folder → verify sub-folders or objects load
   - Verify flat tags (no `/`) still work

## Must-Haves

- [ ] `_handle_by_tag()` uses `build_tag_tree()` for root-level grouping
- [ ] `tag_children` supports `prefix` parameter for sub-folder queries
- [ ] `tag_children` still supports `tag` parameter for exact-match object queries (backward compat)
- [ ] Templates use `.tree-node` + `.tree-children` pattern for `initTreeToggle()` compat
- [ ] Count badges display with proper CSS styling
- [ ] All existing tests still pass

## Verification

- `cd backend && python -m pytest tests/test_tag_explorer.py tests/test_tag_tree_builder.py -v` — all pass
- Browser: "By Tag" explorer shows hierarchical folders that expand into sub-folders or objects

## Inputs

- `backend/app/browser/tag_tree.py` — `build_tag_tree()` pure function from T01
- `backend/app/browser/workspace.py` — existing `_handle_by_tag()` and `tag_children` endpoints
- `backend/app/templates/browser/tag_tree.html` — current flat tag template
- `backend/app/templates/browser/tag_tree_objects.html` — existing object leaf template (unchanged)
- `backend/app/templates/browser/hierarchy_children.html` — reference pattern for recursive tree nodes
- `frontend/static/css/workspace.css` — reference `.abox-count-badge` for style pattern

## Expected Output

- `backend/app/browser/workspace.py` — modified `_handle_by_tag()` and `tag_children()`
- `backend/app/templates/browser/tag_tree.html` — updated for hierarchical root nodes
- `backend/app/templates/browser/tag_tree_folder.html` — new recursive sub-folder template
- `frontend/static/css/workspace.css` — `.tree-count-badge` CSS rule added
- `backend/tests/test_tag_explorer.py` — extended with hierarchy-related tests

## Observability Impact

- **Log signal changed:** `_handle_by_tag()` log message now says `"%d root nodes"` (was `"%d tag folders"`) — reflects hierarchical grouping instead of flat listing
- **New log signal:** `tag_children` prefix path logs `"Tag children for prefix '%s': %d sub-nodes, %d direct objects"` — shows sub-folder expansion details
- **Existing log preserved:** `tag_children` tag path still logs `"Tag children for '%s': %d objects"` — backward-compatible
- **New error response:** `tag_children` with no params returns HTTP 400 `"Missing required parameter: tag or prefix"` (was `"Missing required parameter: tag"`)
- **Inspection:** Browser network tab shows `/explorer/tag-children?prefix=...` requests for folder expansion alongside existing `?tag=...` requests for leaf expansion
- **Failure state:** Empty prefix returns "No tags found" in the template; SPARQL errors surface via existing `_execute_sparql_select` error handling
