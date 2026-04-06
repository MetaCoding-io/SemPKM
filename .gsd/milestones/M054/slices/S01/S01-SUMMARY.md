---
id: S01
parent: M054
milestone: M054
provides:
  - ExplorerConfig dataclass and query composition engine for S02 persistence
  - Config-options API endpoint for S02 preset builder
  - Explorer config panel UI pattern for S02 multi-panel support
  - window.SemPKM.refreshExplorerTree() for external callers to re-render
requires:
  []
affects:
  - S02
key_files:
  - backend/app/browser/explorer_config.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/explorer_config_tree.html
  - backend/app/templates/browser/explorer_config_children.html
  - backend/app/templates/browser/explorer_config_panel.html
  - frontend/static/js/explorer-config.js
  - frontend/static/css/explorer-config.css
  - frontend/static/js/workspace.js
  - backend/tests/test_explorer_config.py
  - backend/tests/test_explorer_modes.py
key_decisions:
  - D400: Reuse VFS strategies.py query builders with new composition layer
  - D401: Dedicated explorer_config.py module with ExplorerConfig dataclass + config-options API
  - prop: prefix stripping in ExplorerConfig.__post_init__ — single backend responsibility boundary
  - Config-children filters in Python after full query rather than separate group-scoped SPARQL
  - Removed EXPLORER_MODE_KEY localStorage entirely — config system supersedes it
patterns_established:
  - ExplorerConfig dataclass as composable SPARQL query specification — filter/group/sort layers compose independently
  - Config-options API pattern: endpoint returns available options from SHACL introspection for frontend dropdowns
  - Lazy-loaded config panel with cached options — fetch once on first open, reuse for subsequent interactions
  - prop: prefix convention for type-specific properties in config dropdowns (distinguishes from built-in options)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M054/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M054/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M054/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M054/slices/S01/tasks/T04-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T04:47:35.820Z
blocker_discovered: false
---

# S01: Composable Explorer with Config Builder

**Replaced the flat OBJECTS dropdown with a composable explorer supporting independent filter (by type), group-by (type/tag/property), and sort (label/date/property) layers — rendering grouped trees with sorted items via SPARQL query composition.**

## What Happened

Built the composable explorer in four tasks spanning backend query engine, tree rendering endpoints, frontend config builder UI, and workspace integration.

**T01 — Query Engine & Config Options API:** Created `explorer_config.py` with `ExplorerConfig` dataclass and two SPARQL query composition functions: `build_explorer_query()` (produces SELECT with filter/group/sort layers) and `build_group_folders_query()` (produces folder-level group values with counts). Label resolution reuses `_LABEL_OPTIONALS`/`_LABEL_COALESCE` from strategies.py — zero duplication. All IRI interpolation uses `safe_iri()`. Added `GET /browser/explorer/config-options` endpoint returning types (from ShapesService), built-in group/sort options, and per-type SHACL properties with `preferred_group` flags for enum-like (`sh:in`) properties. 20 unit tests.

**T02 — Tree Rendering Endpoints:** Created two HTML templates (`explorer_config_tree.html` for grouped folders or flat objects, `explorer_config_children.html` for sorted leaf nodes) and two workspace endpoints (`GET /explorer/config-tree` and `GET /explorer/config-children`). Folders lazy-load children via htmx `hx-get` with config params forwarded as query string. Config-children endpoint filters in Python after running the full explorer query rather than composing a separate group-scoped SPARQL — simpler and reuses existing query builder. 6 additional endpoint tests.

**T03 — Frontend Config Builder:** Created `explorer-config.js` IIFE module exporting `initExplorerConfig`, `applyExplorerConfig`, `resetExplorerConfig`, `refreshExplorerTree`, and `toggleExplorerConfig` to `window.SemPKM`. Config options fetched lazily on first panel open and cached in module scope. Type selection dynamically updates group-by and sort dropdowns with type-specific properties prefixed with `prop:` to distinguish from built-in options. Created `explorer-config.css` with collapsible panel, summary bar, and compact config rows using theme tokens via `color-mix()`. Created `explorer_config_panel.html` Jinja2 partial.

**T04 — Integration & Old Dropdown Removal:** Replaced `select#explorer-mode-select` with a gear-icon configure button in workspace.html. Updated `refreshNavTree()` to delegate to the config system. Removed `EXPLORER_MODE_KEY` localStorage handling and `initExplorerMode`/`initExplorerMountOptions` functions. Added persona backward compat: `by-tag` maps to `group_by=tag`. Fixed critical `prop:` prefix stripping bug by adding `__post_init__` cleanup to ExplorerConfig — the frontend sends `prop:http://...` values that need the prefix stripped before SPARQL interpolation. Added config selectors to E2E `selectors.ts`. 42 total tests pass.

## Verification

42/42 backend tests pass across test_explorer_config.py (30 tests: 6 config defaults, 12 query builder, 6 group folders, 6 endpoint tests) and test_explorer_modes.py (12 tests: 8 registry, 4 config endpoint registration). Static assets served at 200 from nginx. All key exports verified in explorer-config.js. Browser verification confirmed end-to-end flow: config panel opens, dropdowns populate from API, grouped tree renders with status folders and sorted items, reset restores default tree.

## Requirements Advanced

- R009 — ShapesService.get_types() strips ' Shape' suffixes and explorer config tree uses clean labels from label resolution — no raw model IDs in the tree
- R010 — ExplorerConfig supports composable filter/group/sort layers with 30 unit tests proving SPARQL generation for all combinations. Browser verification confirmed type-filtered, grouped, sorted tree rendering.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02: Config-children endpoint filters in Python after running full explorer query rather than composing a separate group-scoped SPARQL query — simpler and avoids duplicating query composition logic. T03: Added toggleExplorerConfig() export not in original plan — needed by gear button for panel collapse/expand. Sort order uses HTML entities (↑↓) instead of Lucide icons for compactness. T04: Added prop: prefix stripping in ExplorerConfig.__post_init__ — necessary integration fix not in original plan. Removed EXPLORER_MODE_KEY localStorage entirely rather than mapping old values.

## Known Limitations

E2E tests using SEL.explorer.modeSelect (19-explorer-modes, 20-tags, 20-vfs-explorer, 24-tag-hierarchy) will fail because the select element was removed. The legacy /browser/explorer/tree?mode=X endpoint still exists for backward compat but is no longer wired to the UI. Config is not persisted server-side yet — that's S02 scope.

## Follow-ups

S02 will add server-side config persistence, named configs, multi-panel support, and presets. E2E specs referencing the removed explorer mode dropdown need updating.

## Files Created/Modified

- `backend/app/browser/explorer_config.py` — New module: ExplorerConfig dataclass + build_explorer_query() + build_group_folders_query() + get_config_options()
- `backend/app/browser/workspace.py` — Added 3 endpoints: GET /explorer/config-options, GET /explorer/config-tree, GET /explorer/config-children
- `backend/app/templates/browser/explorer_config_tree.html` — New template: grouped folder tree or flat object list for config-tree endpoint
- `backend/app/templates/browser/explorer_config_children.html` — New template: sorted leaf nodes within a group for config-children endpoint
- `backend/app/templates/browser/explorer_config_panel.html` — New template: config builder panel with filter/group/sort dropdowns
- `backend/app/templates/browser/workspace.html` — Replaced explorer mode dropdown with gear-icon configure button, included config panel partial
- `frontend/static/js/explorer-config.js` — New IIFE module: config state management, API fetching, htmx tree re-rendering
- `frontend/static/css/explorer-config.css` — New CSS: collapsible config panel, summary bar, config rows with theme tokens
- `frontend/static/js/workspace.js` — Updated refreshNavTree to delegate to config system, removed old explorer mode code
- `backend/tests/test_explorer_config.py` — 30 unit tests: config defaults, query builder, group folders, endpoint integration
- `backend/tests/test_explorer_modes.py` — 12 tests: registry validation + config endpoint registration checks
- `e2e/helpers/selectors.ts` — Added config panel selectors for future E2E tests
