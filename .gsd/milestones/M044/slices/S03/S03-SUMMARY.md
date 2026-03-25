---
id: S03
parent: M044
milestone: M044
provides:
  - window.SemPKM namespace object — all cross-IIFE exports consolidated under this single global
  - Pattern for S04-S06: any new cross-IIFE references must use window.SemPKM.X
requires:
  - slice: S01
    provides: apiFetch() in api-fetch.js — S03 migrated its export to window.SemPKM.apiFetch
  - slice: S02
    provides: registerCleanup()/runCleanup() in cleanup.js — S03 migrated those exports to window.SemPKM namespace
affects:
  - S04
  - S05
  - S06
  - S07
key_files:
  - frontend/static/js/api-fetch.js
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/graph.js
  - frontend/static/js/federation.js
  - frontend/static/js/editor.js
  - frontend/static/js/canvas.js
  - frontend/static/js/calendar.js
  - frontend/static/js/copilot.js
  - frontend/static/js/sparql-console.js
  - backend/app/templates/browser/object_tab.html
  - backend/app/templates/forms/object_form.html
  - backend/app/templates/browser/settings_page.html
  - backend/app/templates/browser/workspace.html
  - e2e/helpers/dockview.ts
  - e2e/tests/02-views/graph-interaction.spec.ts
  - e2e/tests/50-demo/demo-full-flow.spec.ts
key_decisions:
  - D370: All custom globals migrate from window.X to window.SemPKM.X with three-phase rollout (shims → template migration → shim removal). Namespace bootstrapped in api-fetch.js.
  - Double-underscore globals (__canvasDragPayload, __calendarDragPayload) migrated to SemPKM namespace for template-JS consistency, reversing initial decision to leave them
  - Test-only window globals (__lastOpenTabIri, __scopeEventFired, _injectedInstanceUrl) left on bare window — test instrumentation, not app API surface
patterns_established:
  - window.SemPKM namespace pattern: all new cross-IIFE exports MUST use window.SemPKM.X = ..., never bare window.X = ...
  - Template onclick pattern: SemPKM.functionName() for all custom functions, typeof SemPKM.X === 'function' for guards
  - E2E evaluate pattern: (window as any).SemPKM.functionName instead of (window as any).functionName
  - Namespace bootstrap at top of earliest-loading custom JS file (api-fetch.js): window.SemPKM = window.SemPKM || {}
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M044/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M044/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M044/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T19:54:29.753Z
blocker_discovered: false
---

# S03: Window Namespace Consolidation

**All ~213 cross-IIFE window globals consolidated under window.SemPKM namespace across 25 JS files, 52 templates, and 40 E2E test files — zero bare custom globals remain.**

## What Happened

Three-phase migration executed as planned:

**T01 — JS file migration with shims:** Migrated all ~213 `window.X =` export assignments across 26 JS files to `window.SemPKM.X =`. Namespace object `window.SemPKM = window.SemPKM || {}` bootstrapped in api-fetch.js (the earliest-loading custom script). Added 157 backward-compat shim lines (`window.X = window.SemPKM.X`) at end of each file's export block so templates and E2E tests continued working during migration. All internal cross-IIFE references (typeof guards, window.X() calls) also updated. Three correctness fixes applied post-migration: restored `window.dockview` (third-party, not ours), kept `_sempkmSkipLayoutSave` in old form for template compat (deferred to T02), added sync writes in `initWorkspaceLayout()` for reassigned references.

**T02 — Template migration:** Updated 52 Jinja2 templates across three categories: (1) ~70+ onclick/onchange/oninput/onsubmit handlers from bare `openTab(...)` to `SemPKM.openTab(...)`, (2) ~50 inline `<script>` exports from `window.X = function` to `window.SemPKM.X = function`, (3) ~20 typeof guards from `typeof window.X` to `typeof SemPKM.X`. Also migrated internal state references (`__canvasDragPayload`, `_tabMeta`, `_dockview`, `_sempkmSkipLayoutSave`, `_sempkmRefreshTimer`, `_sempkmCmdListener`) — reversing T01's decision to leave double-underscore globals unmigrated, since templates writing to them needed consistency with JS readers. Covered significantly more templates than planned (~52 vs ~20 estimated).

**T03 — E2E migration + shim removal:** Updated all `(window as any).X` references to `(window as any).SemPKM.X` across 40 E2E test files (~100+ references, significantly more than the planned ~6 files). Removed all 157 backward-compat shim lines from 20 JS files. Discovered and migrated one missed global (`__calendarDragPayload` in calendar.js/kanban.js). Test-only instrumentation globals (`__lastOpenTabIri`, `__scopeEventFired`, `_injectedInstanceUrl`) left on bare window since they're test harness, not app APIs.

**Post-completion fix:** Fixed a duplicate-content bug in `graph-interaction.spec.ts` where T03's file write concatenated the file content instead of replacing it, causing TypeScript compilation errors. Removed the duplicate block, leaving the correct SemPKM-namespaced version.

## Verification

All slice-level verification checks pass:

1. **Zero non-SemPKM custom window globals in JS:** `rg 'window.[a-zA-Z_]\w* =' frontend/static/js/ | grep -v 'window.SemPKM' | grep -v exclusions` returns 0 lines.
2. **JS syntax check:** `node --check` on all 32 JS files — zero failures.
3. **Zero custom window.X onclick handlers in templates:** `rg 'onclick=.*window.' backend/app/templates/ | grep -v browser-builtins` returns only 7 lines — all either `window.SemPKM.*` or `window.SemPKMCanvas.*` (explicitly out of scope).
4. **Zero bare window globals in E2E tests:** `rg 'window.[a-z]\w+' e2e/ -g '*.ts' | grep -v SemPKM/builtins` returns 0 lines.
5. **Zero typeof guard remnants:** `rg 'typeof window.[a-z]\w+ ==' backend/app/templates/ | grep -v allowed-exceptions` returns 0 lines.
6. **Zero backward-compat shim lines:** `rg '^\s*window.[a-zA-Z_]\w+\s*=\s*(window.)?SemPKM.' frontend/static/js/` returns 0 lines.
7. **E2E TypeScript compilation:** `npx tsc --noEmit` shows zero errors in any S03-modified file. Pre-existing errors in 15 unrelated test files are untouched.
8. **Namespace bootstrap present:** `rg 'window.SemPKM = window.SemPKM' frontend/static/js/api-fetch.js` confirms initialization.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

1. T02 migrated ~52 templates vs ~20 planned — thorough audit found many more templates with cross-IIFE references.
2. T03 updated 40 E2E files with ~100+ references vs ~6 files planned — the real codebase had far more window.X evaluate() calls.
3. T02 reversed T01's decision to leave double-underscore globals (`__canvasDragPayload`) unmigrated — templates writing to them needed consistent namespace.
4. Post-completion fix: removed duplicate content in graph-interaction.spec.ts introduced by T03's file write operation.

## Known Limitations

1. Pre-existing TypeScript errors in 15 E2E test files (sparql-advanced, docs-navigation, llm-config, invite-flow, etc.) — unrelated to namespace changes.
2. Pre-existing bug: workspace-layout.js calls bare `loadRightPaneSection` which was never defined (workspace.js exports `refreshRightPaneSection`). Not introduced by this migration.
3. Existing concatenated-name globals (`SemPKMSettings`, `SemPKMLayouts`, `SemPKMCanvas`) left as-is per plan — they're already namespaced by naming convention and touching them would require migrating their dedicated JS files and all template references for no collision benefit.
4. `_sempkm` prefix is now redundant under the `SemPKM` namespace (e.g., `SemPKM._sempkmGraph`) — cosmetic cleanup deferred.

## Follow-ups

1. S07 E2E regression suite will prove the namespace migration doesn't break runtime behavior.
2. Optional cosmetic rename: strip `_sempkm` prefix from globals now under the SemPKM namespace (e.g., `SemPKM._sempkmGraph` → `SemPKM._graph`).
3. Fix pre-existing bug: `loadRightPaneSection` undefined reference in workspace-layout.js line ~360.

## Files Created/Modified

- `frontend/static/js/api-fetch.js` — Namespace bootstrap (window.SemPKM = window.SemPKM || {}), migrated apiFetch/showToast exports to SemPKM
- `frontend/static/js/workspace.js` — Migrated ~40 exports (openTab, openViewTab, refreshRightPaneSection, etc.) to SemPKM namespace
- `frontend/static/js/workspace-layout.js` — Migrated ~30 exports (initWorkspaceLayout, addObjectPanel, etc.) + internal state vars to SemPKM
- `frontend/static/js/graph.js` — Migrated _sempkmGraph, initGraphView, destroyGraph to SemPKM
- `frontend/static/js/federation.js` — Migrated initFederation, destroyFederation to SemPKM
- `frontend/static/js/editor.js` — Migrated initEditor, markDirty, destroyEditor exports to SemPKM
- `frontend/static/js/tutorials.js` — Migrated initTutorials to SemPKM
- `frontend/static/js/canvas.js` — Migrated SemPKMCanvas setup + __canvasDragPayload to SemPKM
- `frontend/static/js/calendar.js` — Migrated calendar functions + __calendarDragPayload to SemPKM
- `frontend/static/js/cleanup.js` — Migrated registerCleanup/runCleanup to SemPKM
- `frontend/static/js/sidebar.js` — Migrated sidebar functions to SemPKM
- `frontend/static/js/theme.js` — Migrated theme functions to SemPKM
- `frontend/static/js/settings.js` — Migrated settings functions to SemPKM
- `frontend/static/js/named-layouts.js` — Migrated SemPKMLayouts setup to SemPKM-aware guards
- `frontend/static/js/markdown-render.js` — Migrated renderMarkdownBody/renderMarkdownFromUrl to SemPKM
- `frontend/static/js/column-prefs.js` — Migrated column preference functions to SemPKM
- `frontend/static/js/bmc.js` — Migrated BMC view functions to SemPKM
- `frontend/static/js/okr.js` — Migrated OKR view functions to SemPKM
- `frontend/static/js/quadrant.js` — Migrated quadrant view functions to SemPKM
- `frontend/static/js/decision-matrix.js` — Migrated decision matrix view functions to SemPKM
- `frontend/static/js/kanban.js` — Migrated kanban functions + __canvasDragPayload/__calendarDragPayload to SemPKM
- `frontend/static/js/recurrence-editor.js` — Migrated initRecurrenceEditor/initExdateEditor to SemPKM
- `frontend/static/js/vfs-browser.js` — Migrated VFS browser functions to SemPKM
- `frontend/static/js/context-indicator.js` — Migrated context indicator functions to SemPKM
- `frontend/static/js/copilot.js` — Migrated copilot functions to SemPKM
- `frontend/static/js/sparql-console.js` — Migrated SPARQL console functions to SemPKM
- `backend/app/templates/browser/object_tab.html` — Migrated onclick handlers + inline script exports to SemPKM
- `backend/app/templates/browser/object_tab_app.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/object_read.html` — Migrated typeof guards + onclick to SemPKM
- `backend/app/templates/browser/object_embed.html` — Migrated typeof guards to SemPKM
- `backend/app/templates/browser/workspace.html` — Migrated typeof guards + inline script calls to SemPKM
- `backend/app/templates/forms/object_form.html` — Migrated 5 inline script exports + onclick handlers to SemPKM
- `backend/app/templates/forms/_field.html` — Migrated typeof guards for recurrence/editor to SemPKM
- `backend/app/templates/browser/settings_page.html` — Migrated 5 settings exports to SemPKM
- `backend/app/templates/browser/event_log.html` — Migrated 2 event functions to SemPKM
- `backend/app/templates/browser/_context_rules.html` — Migrated 6 inline functions to SemPKM
- `backend/app/templates/browser/dashboard_builder.html` — Migrated 7 builder functions to SemPKM
- `backend/app/templates/browser/workflow_builder.html` — Migrated 7 builder functions to SemPKM
- `backend/app/templates/browser/workflow_runner.html` — Migrated inline function to SemPKM
- `backend/app/templates/components/_sidebar.html` — Migrated _sempkmSkipLayoutSave to SemPKM namespace
- `backend/app/templates/browser/_setting_input.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/_llm_settings.html` — Migrated inline export to SemPKM
- `backend/app/templates/browser/_webid_settings.html` — Migrated 7 inline functions to SemPKM
- `backend/app/templates/browser/_notification_preferences.html` — Migrated 4 inline functions to SemPKM
- `backend/app/templates/browser/okr_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/bmc_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/cards_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/kanban_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/quadrant_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/decision_matrix_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/table_view.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/lint_dashboard.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/ref_tooltip.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/partials/shared_nav_content.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/saved_queries_explorer.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/tag_tree_objects.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/graph_view.html` — Migrated typeof guards to SemPKM
- `backend/app/templates/browser/my_views.html` — Migrated 2 inline exports + typeof guards to SemPKM
- `backend/app/templates/browser/view_toolbar.html` — Migrated inline export + typeof guard to SemPKM
- `backend/app/templates/browser/docs_page.html` — Migrated typeof guards to SemPKM
- `backend/app/templates/browser/docs_viewer.html` — Migrated typeof guards to SemPKM
- `backend/app/templates/guide_article.html` — Migrated typeof guards to SemPKM
- `backend/app/templates/components/_tabs.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/admin/sparql.html` — Migrated inline references to SemPKM
- `backend/app/templates/admin/models.html` — Migrated 2 inline functions to SemPKM
- `backend/app/templates/browser/ontology/abox_instances.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/ontology/edit_class_form.html` — Migrated 5 inline functions to SemPKM
- `backend/app/templates/browser/ontology/create_property_form.html` — Migrated 2 inline functions to SemPKM
- `backend/app/templates/browser/ontology/edit_property_form.html` — Migrated inline function to SemPKM
- `backend/app/templates/browser/search_suggestions.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/tree_children.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/views_explorer.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/type_picker.html` — Migrated typeof guards + onclick to SemPKM
- `backend/app/templates/browser/tag_tree_folder.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/mount_tree_objects.html` — Migrated onclick handlers to SemPKM
- `backend/app/templates/browser/dashboard_explorer.html` — Migrated inline export to SemPKM
- `backend/app/templates/browser/workflow_explorer.html` — Migrated inline export to SemPKM
- `backend/app/templates/browser/dashboard_form_group.html` — Migrated drag payload to SemPKM
- `e2e/helpers/dockview.ts` — Migrated window.SemPKM references for openTab, addObjectPanel, etc.
- `e2e/tests/02-views/graph-interaction.spec.ts` — Migrated to SemPKM namespace + fixed duplicate content bug
- `e2e/tests/02-views/cross-view-drag.spec.ts` — Migrated __calendarDragPayload to SemPKM
- `e2e/tests/03-navigation/split-panes.spec.ts` — Migrated to SemPKM namespace
- `e2e/tests/03-navigation/named-layouts.spec.ts` — Migrated to SemPKM namespace
- `e2e/tests/50-demo/demo-full-flow.spec.ts` — Migrated startDemoTour and other globals to SemPKM
