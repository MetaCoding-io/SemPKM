---
id: T01
parent: S14
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# T01: 14-split-panes-and-bottom-panel 01

**# Phase 14 Plan 01: WorkspaceLayout Foundation Summary**

## What Happened

# Phase 14 Plan 01: WorkspaceLayout Foundation Summary

WorkspaceLayout class with EditorGroup data model, Split.js destroy-and-recreate strategy, sessionStorage migration from sempkm_open_tabs to sempkm_workspace_layout, multi-group DOM structure, and full workspace.js delegation wiring.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create workspace-layout.js | a9c26b9 | frontend/static/js/workspace-layout.js (new, 637 lines) |
| 2 | Wire workspace.js, restructure HTML/CSS | 9ae2a9c | workspace.js, workspace.css, workspace.html, base.html |

## What Was Built

**workspace-layout.js (637 lines):**
- `WorkspaceLayout` class: addGroup (max 4), removeGroup (redistributes tabs to left neighbor), moveTab (cross-group), addTabToGroup, removeTabFromGroup, setActiveGroup, save, static restore
- `migrateTabState()`: converts sempkm_open_tabs + sempkm_active_tab to sempkm_workspace_layout on first load
- `recreateGroupSplit()`: destroys Split.js, clears editorPane.innerHTML, creates group DOM (editor-group > group-tab-bar + group-editor-area), creates new Split.js with gutterClass:'gutter-editor-groups' when groups.length > 1, restores content
- `renderGroupTabBar()`: builds tab HTML with draggable="true" and data-tab-id/data-group-id attributes (stub for Plan 02 DnD)
- `loadTabInGroup()`: htmx.ajax to #editor-area-{groupId}; detects view: prefix for view tabs
- `splitRight()`: addGroup() + duplicates active tab into new group
- `getActiveEditorArea()`: returns #editor-area-{activeGroupId}
- Window exports: _workspaceLayout, getActiveEditorArea, splitRight, setActiveGroup, initWorkspaceLayout, switchTabInGroup, closeTabInGroup, renderGroupTabBar, loadTabInGroup

**workspace.html restructure:**
- editor-pane now has classes `workspace-pane editor-column`
- Contains `editor-groups-container` div wrapping initial `group-1` DOM
- Old `#tab-bar` / `#editor-area` removed; replaced by `#tab-bar-group-1` / `#editor-area-group-1`
- `#bottom-panel-slot` placeholder added (Plan 03 implementation)

**workspace.js delegation:**
- openTab/closeTab/switchTab delegate to window._workspaceLayout
- All htmx targets use window.getActiveEditorArea() (no #editor-area references)
- Ctrl+\\ reassigned to splitRight; Ctrl+J stub; Ctrl+1-4 group focus
- Command palette: 'toggle-sidebar' entry replaced by 'split-right' entry
- init() calls window.initWorkspaceLayout() instead of old restoreTabState()

**workspace.css additions:**
- .editor-column (flex-direction: column)
- .editor-groups-container (display: flex, flex: 1)
- .editor-group (flex-direction: column, transition: flex 150ms ease-out)
- .group-tab-bar (mirrors .tab-bar-workspace; position: relative for Plan 02 drop indicators)
- .group-editor-area (flex: 1, overflow: auto, padding: 16px)
- .editor-group-active > .group-tab-bar (border-top: 2px solid var(--color-accent))
- .gutter.gutter-horizontal.gutter-editor-groups (1px VS Code style with ::after hit-target expansion)

## Decisions Made

1. **Ctrl+\\ = Split Right** (not sidebar toggle): CONTEXT.md and research both specify this reassignment; sidebar remains on Ctrl+B (Phase 12 decision).
2. **workspace-layout.js as separate module**: workspace.js was already 1024 lines; new module is cleaner per RESEARCH.md recommendation.
3. **gutterSize: 1 with CSS ::after**: Fixes Pitfall 2 — 1px visible gutter but 9px pointer target (4px each side).
4. **Tab normalization (both .id and .iri)**: Old tabs from migration only have .iri; new code uses .id as primary key; both set on addTabToGroup.
5. **Duplicate tabs in splitRight**: Per CONTEXT.md: "Duplicate objects are allowed — the same object can be open in multiple groups independently."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added tab normalization for .id/.iri compatibility**
- **Found during:** Task 1 (addTabToGroup implementation)
- **Issue:** Old sessionStorage tabs have only `.iri` field; new code uses `.id` as primary key; mixing old and new tab objects would break tab lookups
- **Fix:** In addTabToGroup, always set both `.id = tab.iri` and `.iri = tab.id` if either is missing; all internal lookups use `(t.id || t.iri)`
- **Files modified:** frontend/static/js/workspace-layout.js
- **Commit:** a9c26b9

**2. [Rule 1 - Bug] Removed `renderTabs()` delegation stub**
- **Found during:** Task 2 analysis
- **Issue:** The plan called for `renderTabs()` to delegate to `renderGroupTabBar` for active group; but the old `renderTabs()` references `#tab-bar` which no longer exists. Instead of adding a stub that would reference a non-existent element, the function was not included in the new workspace.js (it was only called from internal tab management functions which now all use renderGroupTabBar directly)
- **Fix:** Removed renderTabs() entirely; all tab rendering now goes through window.renderGroupTabBar(group) in workspace-layout.js
- **Files modified:** frontend/static/js/workspace.js
- **Commit:** 9ae2a9c

## Self-Check

Files exist check:
- frontend/static/js/workspace-layout.js: FOUND
- frontend/static/css/workspace.css (contains .editor-groups-container): FOUND
- backend/app/templates/browser/workspace.html (contains editor-column): FOUND

Commits exist check:
- a9c26b9: FOUND
- 9ae2a9c: FOUND

## Self-Check: PASSED
