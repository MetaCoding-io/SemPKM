# S01: Composable Explorer with Config Builder

**Goal:** Replace the flat OBJECTS dropdown with a composable explorer where users configure filter (by type), group-by (by property value), and sort (by label/date/property) — rendering a grouped tree with sorted items within each group.
**Demo:** After this: User opens explorer → clicks Configure → selects type filter (Tasks), group-by (Status), sort (Due Date) → tree renders tasks grouped by status with sorted items within each group

## Tasks
- [x] **T01: Created ExplorerConfig dataclass with composable SPARQL query builder and config-options JSON endpoint for the explorer config UI** — Create the backend foundation: an ExplorerConfig dataclass, a query composition engine that builds SPARQL from filter/group/sort layers, and a config-options API endpoint.

**Slice context:** This is S01 of M054 — replacing the flat OBJECTS dropdown with composable filter/group/sort. This task builds the engine; T02 builds the tree-rendering endpoint; T03 builds the frontend config builder; T04 wires everything together.

**Architecture (D400):** Reuse VFS strategies.py query builders with a new composition layer.

## Steps

1. Create `backend/app/browser/explorer_config.py` with:
   - `ExplorerConfig` dataclass: `type_filter: str | None` (type IRI), `group_by: str | None` (property IRI or special values 'type', 'tag'), `sort_by: str | None` (property IRI or special values 'label', 'created'), `sort_order: str` ('asc'/'desc', default 'asc')
   - `build_explorer_query(config: ExplorerConfig) -> str` function that composes SPARQL:
     - Base: `SELECT ?iri ?label ?typeIri ?groupValue ?groupLabel ?sortValue` from current graph
     - Filter layer: if type_filter set, add `?iri a <type_filter_iri>`
     - Group layer: if group_by is 'type', bind `?groupValue` to `?typeIri` and `?groupLabel` to type local name; if group_by is 'tag', query `bpkm:tags`/`schema:keywords`; if group_by is a property IRI, query that property's values
     - Sort layer: if sort_by is 'label', ORDER BY ?label; if sort_by is 'created', ORDER BY dcterms:created; if sort_by is a property IRI, OPTIONAL bind that property and ORDER BY it
     - Always include label resolution using `_LABEL_OPTIONALS` and `_LABEL_COALESCE` from strategies.py
   - `build_group_folders_query(config: ExplorerConfig) -> str | None` — returns a query for folder-level groups (distinct group values + counts), or None if no grouping configured

2. Create `GET /browser/explorer/config-options` endpoint in workspace.py:
   - Returns JSON with: `types` (from ShapesService.get_types with hidden types excluded), `properties` (from ShapesService — for each type, list groupable/sortable properties with path IRI and label), `sort_options` (built-in: label, created; plus type-specific date/enum properties)
   - This endpoint powers the config builder dropdowns in T03

3. Create `backend/tests/test_explorer_config.py` with unit tests:
   - Test `build_explorer_query` with no config (all objects, sorted by label)
   - Test with type_filter only (produces `?iri a <type>` constraint)
   - Test with group_by='type' (produces groupValue/groupLabel bindings)
   - Test with group_by=property IRI (produces OPTIONAL property binding)
   - Test with sort_by='created' + sort_order='desc' (produces ORDER BY DESC)
   - Test with combined filter+group+sort (all layers compose correctly)
   - Test `build_group_folders_query` returns correct folder query or None

**Key constraints:**
- Import `_LABEL_OPTIONALS`, `_LABEL_COALESCE` from `app.vfs.strategies` — do NOT duplicate
- Use `CURRENT_GRAPH` from `app.rdf.namespaces`
- Use `safe_iri()` from `app.sparql.builder` for any IRI interpolation (Knowledge pattern 12)
- Filter out `rdfs:Resource` type from results
- Properties for grouping: use ShapesService.get_node_shapes() → iterate PropertyShape objects, expose those with `in_values` (enum-like) as preferred group candidates, and all others as available
  - Estimate: 2h
  - Files: backend/app/browser/explorer_config.py, backend/app/browser/workspace.py, backend/tests/test_explorer_config.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py -v
- [x] **T02: Added config-tree and config-children endpoints that render grouped/sorted explorer HTML from ExplorerConfig query composition** — Add the `/browser/explorer/config-tree` endpoint that accepts explorer config params and returns a grouped, sorted HTML tree using the query composition engine from T01.

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
  - Estimate: 2h
  - Files: backend/app/browser/workspace.py, backend/app/browser/explorer_config.py, backend/app/templates/browser/explorer_config_tree.html, backend/app/templates/browser/explorer_config_children.html, backend/tests/test_explorer_config.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py -v
- [x] **T03: Created explorer-config.js module, CSS, and template partial for the composable explorer config builder panel** — Build the config builder panel UI and a new JS module that manages explorer configuration state, populates the builder dropdowns from the config-options API, and triggers tree re-renders.

**Slice context:** T01+T02 built the backend. This task builds the frontend config panel. T04 wires it into the workspace and replaces the old dropdown.

## Steps

1. Create `frontend/static/js/explorer-config.js` (IIFE pattern, exports to `window.SemPKM`):
   - `initExplorerConfig()` — called once on workspace load:
     - Fetch `/browser/explorer/config-options` to populate type/property/sort dropdowns
     - Bind event listeners on config selects
     - Store current config in module-scoped variable
   - `applyExplorerConfig()` — read current dropdown values, build query params, trigger htmx fetch of `/browser/explorer/config-tree?type_filter=X&group_by=Y&sort_by=Z&sort_order=asc` into `#explorer-tree-body`
   - `resetExplorerConfig()` — clear all selectors, reload default by-type tree
   - `refreshExplorerTree()` — re-apply current config (called after object CRUD)
   - Export: `window.SemPKM.initExplorerConfig`, `window.SemPKM.applyExplorerConfig`, `window.SemPKM.refreshExplorerTree`

2. Create `frontend/static/css/explorer-config.css`:
   - `.explorer-config-panel` — collapsible panel below the OBJECTS header, above the tree body
   - Three rows: Filter (type select), Group By (property select), Sort (property select + asc/desc toggle)
   - Compact styling matching workspace.css explorer theme (dark background, small text, subtle borders)
   - Apply/Reset buttons at bottom
   - Collapsed state: slim bar showing current config summary (e.g. 'Tasks → by Status → Due Date ↑')
   - Expanded state: full form with dropdowns

3. Create `backend/app/templates/browser/explorer_config_panel.html` partial:
   - Config builder form with three `<select>` elements:
     - Type filter: populated from config-options API types list, includes 'All Types' default
     - Group by: populated from config-options API properties for selected type, includes 'None' default; special entries 'By Type', 'By Tag' always available
     - Sort by: 'Label' (default), 'Date Created', plus type-specific properties
   - Sort order toggle button (asc/desc)
   - Apply button triggers `applyExplorerConfig()`
   - Configure toggle button (gear icon) in the OBJECTS header to expand/collapse

4. Wire the type filter dropdown to dynamically update the group-by and sort options:
   - When type changes → fetch properties for that type from config-options → repopulate group-by and sort dropdowns
   - Use `apiFetch()` from `api-fetch.js` (Knowledge pattern 13)

**Key constraints:**
- Follow IIFE pattern matching workspace.js, copilot.js
- Use `apiFetch()` for all fetch calls (Knowledge pattern 13)
- Size Lucide icons via CSS with flex-shrink:0 (CLAUDE.md rule)
- CSS colors use theme tokens via color-mix() (Knowledge pattern 14)
- No inline styles on SVGs (CLAUDE.md rule)
  - Estimate: 2h
  - Files: frontend/static/js/explorer-config.js, frontend/static/css/explorer-config.css, backend/app/templates/browser/explorer_config_panel.html
  - Verify: test -f frontend/static/js/explorer-config.js && test -f frontend/static/css/explorer-config.css && test -f backend/app/templates/browser/explorer_config_panel.html && rg 'SemPKM.initExplorerConfig' frontend/static/js/explorer-config.js && rg 'SemPKM.applyExplorerConfig' frontend/static/js/explorer-config.js && rg 'SemPKM.refreshExplorerTree' frontend/static/js/explorer-config.js && rg 'apiFetch' frontend/static/js/explorer-config.js
- [ ] **T04: Integration: wire config builder into workspace, replace old dropdown, verify end-to-end** — Wire the config builder into the workspace, replace the old explorer mode dropdown, update refreshNavTree to use the new config system, and verify the full flow works end-to-end.

**Slice context:** T01-T03 built all components. This task integrates them and proves the slice demo works.

## Steps

1. Update `backend/app/templates/browser/workspace.html`:
   - Replace the `<select id='explorer-mode-select'>` dropdown with a Configure button (gear icon) that toggles the config panel
   - Include the `explorer_config_panel.html` partial in the OBJECTS section body, above `explorer-tree-body`
   - Add `<link>` for explorer-config.css and `<script>` for explorer-config.js
   - Keep the existing header action buttons (refresh, new object, bulk delete)

2. Update `frontend/static/js/workspace.js`:
   - Replace `refreshNavTree()` implementation: if a config is active (any filter/group/sort set), call `SemPKM.applyExplorerConfig()` instead of the old htmx mode-based fetch
   - If no config is active, default to the by-type tree (backward compat)
   - Remove the `EXPLORER_MODE_KEY` localStorage handling and the `explorer-mode-select` change listener
   - Update persona switching: personas that saved `explorer_mode` should map to the new config system (by-type → default, by-tag → group_by=tag)
   - Call `SemPKM.initExplorerConfig()` in the workspace init sequence

3. Update `frontend/nginx.conf` if needed — verify `/js/explorer-config.js` and `/css/explorer-config.css` are served (they should be, since nginx serves `/js/` and `/css/` from the static mount)

4. Update `backend/tests/test_explorer_modes.py`:
   - Update tests to verify the new config-tree endpoint is registered
   - Add test that old modes still work for backward compatibility (hierarchy and by-tag are still valid via the config system)

5. Verify in browser:
   - Navigate to /browser/ → OBJECTS section shows Configure button instead of dropdown
   - Click Configure → config panel expands with type/group/sort selectors
   - Select type=Task → tree shows only tasks
   - Select group=Status → tree shows folder nodes per status value
   - Select sort=Due Date → items sorted within groups
   - Click Apply → tree updates
   - Click Reset → default by-type tree restored
   - R009: type labels in tree show clean names without ' Shape' suffix
   - R010: composable layers produce correct results

**Key constraints:**
- nginx serves `/js/` and `/css/` — use those paths, not `/static/js/` (Knowledge pattern about nginx paths)
- Don't break existing object-open-on-click behavior in the tree
- Persona explorer_mode backward compat: map old values to new config
  - Estimate: 2h
  - Files: backend/app/templates/browser/workspace.html, frontend/static/js/workspace.js, backend/tests/test_explorer_modes.py, frontend/static/js/explorer-config.js
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py tests/test_explorer_modes.py -v
