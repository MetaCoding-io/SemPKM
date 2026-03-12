# T03: 15-settings-system-and-node-type-icons 03

**Slice:** S15 — **Milestone:** M001

## Description

Build the node type icon system: an IconService that reads manifest icon/color declarations, a /browser/icons JSON endpoint, and updated rendering in the explorer tree, editor tab bar, and graph view. Mental Models (basic-pkm) contribute icon and color declarations in their manifest.yaml.

Purpose: ICON-01/02/03 require type-specific visual identity throughout the workspace. The manifest extension from Plan 15-01 enables model-contributed declarations; this plan wires them into the three render paths.
Output: Explorer tree shows Lucide icons with colors, editor tabs show type icons, graph nodes use type-appropriate shapes/colors, basic-pkm manifest declares icons for its types.

## Must-Haves

- [ ] "Object explorer tree shows a Lucide icon (not an emoji) next to each type and object leaf"
- [ ] "Types declared in basic-pkm/manifest.yaml with icons field render their specific icon and color in the tree"
- [ ] "Types without a manifest icon declaration render a neutral circle icon in var(--color-text-faint)"
- [ ] "Editor tabs for typed objects show the type icon before the object label"
- [ ] "Graph view applies type-appropriate colors (already existed) and shape differentiation per type"
- [ ] "Mental model manifest.yaml can declare icons: list with type/icon/color per context (tree/graph/tab)"
- [ ] "Lucide icons in htmx-swapped tree content are initialized via scoped createIcons call"

## Files

- `backend/app/services/icons.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/nav_tree.html`
- `backend/app/templates/browser/tree_children.html`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
- `models/basic-pkm/manifest.yaml`
