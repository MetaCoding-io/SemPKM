---
estimated_steps: 29
estimated_files: 5
skills_used: []
---

# T02: Backend config-driven tree rendering endpoint

Add the `/browser/explorer/config-tree` endpoint that accepts explorer config params and returns a grouped, sorted HTML tree using the query composition engine from T01.

**Slice context:** T01 built the query engine and config-options API. This task builds the endpoint that renders the actual explorer tree HTML. T03 builds the frontend config builder. T04 wires them together.

## Steps

1. Create `backend/app/templates/browser/explorer_config_tree.html` template:
   - If groups exist: render folder nodes (like mount_tree.html pattern) with group label, item count, and expand-on-click via htmx
   - Each folder: `<div class='tree-node'>` with folder icon + group label + count badge
   - Folder children loaded lazily via `hx-get='/browser/explorer/config-children?group_value=X&...'` with `hx-trigger='click once'`
   - If no groups (flat list): render object leaf nodes directly (like tree_children.html pattern)
   - Empty state: 'No objects match this configuration'

2. Create `backend/app/templates/browser/explorer_config_children.html` template:
   - Render sorted object leaf nodes within a group (same structure as tree_children.html: iri, label, type icon, click-to-open-tab)

3. Add `GET /browser/explorer/config-tree` endpoint to workspace.py:
   - Query params: `type_filter`, `group_by`, `sort_by`, `sort_order` (all optional)
   - Build ExplorerConfig from params
   - If group_by is set: run `build_group_folders_query()` to get folder data, render explorer_config_tree.html with folders
   - If no group_by: run `build_explorer_query()` to get flat sorted objects, render explorer_config_tree.html with objects
   - Resolve labels via LabelService, icons via IconService

4. Add `GET /browser/explorer/config-children` endpoint:
   - Query params: `type_filter`, `group_by`, `group_value`, `sort_by`, `sort_order`
   - Build scoped SPARQL: filter by type + filter by group value + sort
   - Return explorer_config_children.html with sorted objects for that group

5. Add tests to `backend/tests/test_explorer_config.py` (extend from T01):
   - Test config-tree endpoint returns HTML with folder nodes when group_by is set
   - Test config-children endpoint returns objects filtered by group value

**Key constraints:**
- Object leaf nodes must use the same click-to-open-tab pattern as existing tree: `onclick='openTab("iri")'`
- Use `get_hidden_types()` to exclude internal types
- Label resolution: use LabelService.resolve_batch() for object labels
- Icon resolution: use IconService.get_type_icon() for object type icons

## Inputs

- ``backend/app/browser/explorer_config.py` — ExplorerConfig, build_explorer_query(), build_group_folders_query() from T01`
- ``backend/app/templates/browser/mount_tree.html` — folder node HTML pattern to follow`
- ``backend/app/templates/browser/tree_children.html` — object leaf node HTML pattern to follow`
- ``backend/app/templates/browser/nav_tree.html` — type node pattern for reference`
- ``backend/app/browser/workspace.py` — existing endpoint patterns, _execute_sparql_select, _bindings_to_objects helpers`

## Expected Output

- ``backend/app/templates/browser/explorer_config_tree.html` — grouped tree template with folder nodes and lazy-load children`
- ``backend/app/templates/browser/explorer_config_children.html` — sorted object nodes within a group`
- ``backend/app/browser/workspace.py` — config-tree and config-children endpoints added`
- ``backend/tests/test_explorer_config.py` — extended with endpoint response tests`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py -v
