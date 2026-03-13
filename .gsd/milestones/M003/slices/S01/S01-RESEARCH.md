# S01: Explorer Mode Infrastructure — Research

**Date:** 2026-03-12

## Summary

S01 adds a mode dropdown to the OBJECTS section of the explorer pane, enabling users to switch between organizational strategies (by-type, by-hierarchy, by-tag, VFS mounts). The current by-type tree is refactored into a mode handler and becomes the default. The explorer tree body is an htmx swap target that re-renders on mode change.

The existing codebase is well-structured for this. The OBJECTS section (`#section-objects`) in `workspace.html` already has a header with action buttons and a body containing `nav_tree.html`. The `workspace.py` sub-router has clean `/nav-tree` and `/tree/{type_iri}` endpoints. VFS strategies in `strategies.py` provide reusable SPARQL builders. The main work is: (1) add a dropdown to the OBJECTS header, (2) create a new `/browser/explorer/tree?mode={mode}` endpoint pattern, (3) refactor the current nav-tree logic into the `by-type` mode handler, and (4) establish the mode registry pattern for downstream slices.

The risk is medium — no new external dependencies, no schema changes, no data migrations. The primary complexity is in the htmx wiring (dropdown changes must trigger tree re-render while preserving existing behaviors like multi-select, drag-drop, and lazy expansion).

## Recommendation

**Approach: Mode registry + htmx swap on dropdown change**

1. **Mode registry** — Python dict mapping mode IDs (`"by-type"`, `"by-hierarchy"`, `"by-tag"`, `"mount:{id}"`) to async handler functions. Each handler returns an htmx partial (tree HTML). Start with `by-type` as the only real handler; others return placeholder content. Downstream slices register their handlers.

2. **Dropdown UI** — Add a `<select>` element (or custom dropdown) to the OBJECTS section header. Use `hx-get="/browser/explorer/tree?mode={value}"` with `hx-target="#explorer-tree-body"` and `hx-swap="innerHTML"`. The dropdown triggers on `change` event.

3. **Swap target** — Rename the existing `explorer-section-body` div inside `#section-objects` to `#explorer-tree-body` (or add it as an ID). This becomes the stable htmx swap target for all modes.

4. **By-type handler** — Extract the existing `nav_tree` endpoint logic into a handler function. The handler queries `ShapesService.get_types()` and renders `nav_tree.html`. The `/browser/nav-tree` endpoint continues to work for `refreshNavTree()` backwards compatibility.

5. **Endpoint pattern** — Single new endpoint `GET /browser/explorer/tree?mode={mode}` dispatches to the registry. For VFS mounts, mode is `mount:{mount_id}`. The endpoint validates the mode and returns 400 for unknown modes.

6. **JS integration** — `refreshNavTree()` in `workspace.js` must be updated to respect the current mode (read it from the dropdown value and hit the mode-aware endpoint). Multi-select, drag-drop, and `handleTreeLeafClick` continue to work because tree-leaf/tree-node CSS classes stay the same.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| SPARQL query building for tree modes | `backend/app/vfs/strategies.py` | 18 query builder functions covering flat, by-type, by-date, by-tag, by-property — reuse in S03/S04 |
| Type list for by-type tree | `ShapesService.get_types()` | Already queries SHACL shapes for available types |
| Icon resolution per type | `IconService.get_icon_map("tree")` / `get_type_icon()` | Used in current nav_tree, carry forward |
| Label resolution batch | `LabelService.resolve_batch()` | TTL-cached, used in current tree_children |
| Async mount listing | `mount_router.py list_mounts()` async pattern | Same SPARQL as SyncMountService but async — reuse for populating dropdown with VFS mounts |
| htmx swap pattern | Existing `hx-get`/`hx-target`/`hx-swap` on workspace sections | VIEWS and MY VIEWS sections use the same pattern |

## Existing Code and Patterns

- `backend/app/browser/workspace.py` — Contains `nav_tree()` endpoint (returns type nodes), `tree_children()` (returns objects per type), and `workspace()` (renders full workspace with types context). The `nav_tree` function is the by-type handler to refactor.
- `backend/app/templates/browser/workspace.html` — OBJECTS section at lines 11-29: `explorer-section-header` with action buttons, `explorer-section-body` containing `{% include "browser/nav_tree.html" %}`. The dropdown goes into the header, the body becomes the mode swap target.
- `backend/app/templates/browser/nav_tree.html` — Type nodes with `hx-get="/browser/tree/{type_iri}"` for lazy child loading. This template stays as-is for the by-type mode.
- `backend/app/templates/browser/tree_children.html` — Leaf nodes with `handleTreeLeafClick`, drag-and-drop, tooltips. Reusable by all modes (any mode that shows objects uses the same leaf template).
- `frontend/static/js/workspace.js` — `refreshNavTree()` at line 1128 targets `#section-objects .explorer-section-body`. Must be updated to pass the current mode. Multi-select at lines 985-1120 targets `#section-objects .tree-leaf[data-iri]` — works as-is since tree-leaf class is consistent across modes.
- `frontend/static/css/workspace.css` — Explorer section styles at lines 78-170, tree node/leaf styles at lines 185-300. No changes needed; new modes reuse the same CSS classes.
- `backend/app/browser/router.py` — Coordinator that includes `workspace_router`. New explorer endpoint goes in `workspace.py` (or a new `explorer.py` sub-router if the file gets too large).
- `backend/app/vfs/mount_router.py` lines 193-245 — Async `list_mounts()` with full SPARQL pattern. Reusable for populating the mode dropdown with VFS mount entries.

## Constraints

- **htmx + vanilla JS only** — No React, no build step. All new UI follows the Jinja2 partial + htmx swap pattern.
- **Backwards compatibility** — `refreshNavTree()` is called from `bulkDeleteSelected()`, `handleTreeLeafClick` (via openTab), and after object creation. All must continue working.
- **`#section-objects` DOM ID** — Hardcoded in workspace.js at 11 locations for multi-select, bulk delete, tooltip init, and selection badge. The ID must not change.
- **tree-leaf/tree-node CSS classes** — Used by CSS, JS event handlers, and E2E test selectors. All modes must emit the same structural CSS classes.
- **`data-testid="nav-section"` and `data-testid="nav-item"`** — Used by E2E tests (`selectors.ts`). Mode-specific trees must preserve these testids for type nodes and leaf nodes.
- **Lazy expansion via `hx-get` + `hx-trigger="click once"`** — The by-type tree uses click-once to lazy-load children. Other modes may need different expansion patterns (S02 hierarchy needs recursive lazy expand) but the click-expand UX should feel consistent.
- **Explorer section drag-and-drop** — `[data-panel-name]` + `draggable="true"` on section headers enables panel reordering. The OBJECTS section must stay draggable.
- **ShapesService availability** — `get_types()` is async and injected via `Depends()`. The mode dispatcher must have access to the same DI chain.

## Common Pitfalls

- **Dropdown event vs htmx trigger** — A `<select>` with `hx-get` on `hx-trigger="change"` works, but the URL must include the selected value. Use `hx-vals` or build the URL dynamically via `hx-get` with JS (`hx-on::config-request`). The simplest htmx-native approach: `<select hx-get="/browser/explorer/tree" hx-include="this" name="mode" hx-target="#explorer-tree-body" hx-trigger="change">`. This sends `?mode=by-type` automatically.
- **Initial load race** — On workspace load, the OBJECTS body is rendered server-side via `{% include "browser/nav_tree.html" %}`. With the mode system, the initial tree should still be server-rendered (not require a separate htmx fetch) to avoid a flash of empty content. Keep the `{% include %}` for the default mode.
- **refreshNavTree() mode awareness** — Current `refreshNavTree()` unconditionally fetches `/browser/nav-tree`. After the refactor, it must read the dropdown's current value and hit `/browser/explorer/tree?mode={value}` instead. If the dropdown doesn't exist yet (e.g., no models installed), fall back to the current endpoint.
- **Lucide icon re-initialization** — After htmx swaps tree content, `lucide.createIcons()` must be called. The current `refreshNavTree()` already does this. The htmx `afterSwap` event handler should also handle it for dropdown-triggered swaps.
- **Command palette type entries** — `refreshNavTree()` also calls `_addTypeCreateEntries(ninja)` to populate the command palette. This must still work when mode changes — type create entries should always be available regardless of current explorer mode.

## Open Risks

- **Mode persistence across page reloads** — If the user selects "By Tag" and reloads the page, the dropdown resets to "By Type" (default). Should mode be persisted in localStorage? This is a UX decision — suggest persisting in localStorage and reading it on workspace init to set the dropdown value and trigger the htmx load. Low risk but needs a decision.
- **VFS mount mode count** — Users could create many mounts. The dropdown could get long. Consider grouping VFS mounts under an "optgroup" or limiting display. Low risk for S01 (placeholders only), real for S03.
- **Multi-select across mode switch** — If the user has objects selected in by-type mode and switches to by-tag mode, the selection set (`selectedIris`) may reference IRIs not visible in the new tree. `clearSelection()` should be called on mode change.

## Requirements Coverage

| Requirement | How S01 Addresses It |
|-------------|---------------------|
| EXP-01 | Primary owner — delivers the dropdown, mode switching, htmx re-render |
| EXP-02 | Primary owner — by-type becomes the default mode handler, current behavior preserved |

Downstream slices that consume S01's output:
- S02 (EXP-03): Registers `hierarchy` handler in mode registry
- S03 (EXP-04, EXP-05): Registers `mount:{id}` handlers, injects dynamic dropdown entries
- S04 (TAG-03): Registers `by-tag` handler

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (198 installs) | available — not installed |
| FastAPI | `wshobson/agents@fastapi-templates` (6.2K installs) | available — not installed |

Both are general-purpose skills. The project's existing patterns are well-established and consistent — installing these is optional. The htmx skill could be useful if complex htmx interactions arise in later slices.

## Sources

- Current nav tree implementation: `backend/app/browser/workspace.py`, `backend/app/templates/browser/nav_tree.html`
- VFS strategies SPARQL builders: `backend/app/vfs/strategies.py`
- Async mount listing pattern: `backend/app/vfs/mount_router.py` lines 193-245
- Explorer CSS structure: `frontend/static/css/workspace.css` lines 78-300
- Workspace JS nav tree logic: `frontend/static/js/workspace.js` lines 985-1140
- E2E nav tree selectors: `e2e/helpers/selectors.ts`
- htmx `hx-include` for `<select>`: htmx docs — `hx-include="this"` includes the element's value in the request
