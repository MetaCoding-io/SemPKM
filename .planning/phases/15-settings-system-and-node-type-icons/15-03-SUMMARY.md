---
phase: 15-settings-system-and-node-type-icons
plan: "03"
subsystem: icons
tags: [icons, lucide, manifest, cytoscape, htmx]
dependency_graph:
  requires: [15-01]
  provides: [ICON-01, ICON-02, ICON-03]
  affects: [browser-router, nav-tree, graph-view, tab-bar]
tech_stack:
  added:
    - IconService (backend/app/services/icons.py)
    - GET /browser/icons JSON endpoint
    - window._sempkmIcons global (client-side icon cache)
  patterns:
    - Manifest-contributed icon declarations with IRI prefix expansion
    - Per-context (tree/graph/tab) icon/color/size resolution with fallback
    - iconToShape mapping: Lucide icon name -> Cytoscape node shape
    - Lucide createIcons scoped to swapped target for htmx re-init
key_files:
  created:
    - backend/app/services/icons.py
  modified:
    - backend/app/browser/router.py
    - backend/app/templates/browser/nav_tree.html
    - backend/app/templates/browser/tree_children.html
    - backend/app/templates/browser/object_tab.html
    - frontend/static/js/workspace-layout.js
    - frontend/static/js/graph.js
    - frontend/static/css/workspace.css
    - models/basic-pkm/manifest.yaml
decisions:
  - basic-pkm uses actual type names (Note/Concept/Project/Person) not plan examples (Source/Tag)
  - Lucide createIcons uses root: not nodes: API (matches sidebar.js pattern)
  - iconToShape covers all 4 basic-pkm icon types plus book-open/tag fallbacks
  - IconService creates fresh instance per request (consistent with SettingsService approach)
metrics:
  duration: "4 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 9
---

# Phase 15 Plan 03: Node Type Icon System Summary

Icon system implementation: IconService reads manifest icon/color declarations with prefix expansion, wired into explorer tree, editor tabs, and graph view shape differentiation.

## What Was Built

**IconService** (`backend/app/services/icons.py`): Reads `icons` from installed model manifests, expands prefixed type IRIs (e.g., `bpkm:Note` -> `urn:sempkm:model:basic-pkm:Note`), resolves per-context (tree/graph/tab) icon, color, and size with fallback to `circle` / `var(--color-text-faint)`.

**`/browser/icons` endpoint**: Returns `{tree: {...}, tab: {...}, graph: {...}}` JSON for all type IRIs. Consumed by `window._sempkmIcons` on workspace init for client-side graph shape lookups.

**Explorer tree icons**: `nav_tree.html` uses `data-lucide` `<i>` elements with per-type color from `type_icons` dict injected by workspace route. `tree_children.html` similarly uses `type_icon` dict from tree_children route. Both use fallback `circle` icon in faint color for unknown types.

**Editor tab icons**: `object_tab.html` inline script pushes `typeIcon`/`typeColor` into the `WorkspaceLayout` tab model, then re-renders the tab bar. `workspace-layout.js` `renderGroupTabBar()` inserts a `data-lucide` `<i>` element before the label for tabs that have `typeIcon` set.

**Graph shape differentiation**: `graph.js` `buildSemanticStyle()` applies `iconToShape` mapping from `window._sempkmIcons.graph` — `file-text->rectangle`, `lightbulb->diamond`, `book-open/folder-kanban->round-rectangle`, `user/tag->ellipse`.

**basic-pkm manifest**: Added `icons:` section for all 4 types: Note (file-text, #4e79a7), Concept (lightbulb, #f28e2b), Project (folder-kanban, #59a14f), Person (user, #76b7b2).

**Lucide re-init**: `workspace.js` `htmx:afterSwap` handler calls `lucide.createIcons({ root: target })` scoped to the swapped element for tree content. `workspace-layout.js` calls `lucide.createIcons({ root: tabBar })` after each tab bar rebuild.

## Deviations from Plan

**1. [Rule 1 - Bug] Actual basic-pkm types differ from plan examples**
- **Found during:** Task 1 step 6
- **Issue:** Plan listed Source/Tag as types but basic-pkm only has Project/Person/Note/Concept
- **Fix:** Used actual types from shapes file — Project (folder-kanban) and Person (user) instead of Source/Tag
- **Files modified:** models/basic-pkm/manifest.yaml

**2. [Rule 1 - Bug] Lucide API uses `root:` not `nodes:` parameter**
- **Found during:** Task 2 step 4
- **Issue:** Plan snippet used `lucide.createIcons({ nodes: [target] })` but sidebar.js uses `{ root: target }` (consistent with Lucide v0.575.0 API)
- **Fix:** Used `{ root: target }` in workspace.js htmx:afterSwap handler
- **Files modified:** frontend/static/js/workspace.js

**3. [Rule 2 - Missing functionality] sidebar.js already handles afterSwap Lucide re-init**
- **Found during:** Task 2 step 4
- **Issue:** sidebar.js already registers an htmx:afterSwap listener that calls `lucide.createIcons({ root: e.detail.target })`, covering tree children
- **Fix:** Added workspace.js handler anyway for defense-in-depth; both handlers are harmless when stacked

## Self-Check: PASSED

All required files exist:
- FOUND: backend/app/services/icons.py
- FOUND: backend/app/browser/router.py (with /icons endpoint, type_icons in workspace, type_icon in tree_children and get_object)
- FOUND: backend/app/templates/browser/nav_tree.html (contains data-lucide)
- FOUND: backend/app/templates/browser/tree_children.html (contains data-lucide)
- FOUND: models/basic-pkm/manifest.yaml (contains icons: field)

Commits:
- a46ea3b: feat(15-03): IconService, icon endpoint, nav tree and tab Lucide icons
- 7224262: feat(15-03): graph shape differentiation, tab icon render, icons fetch
