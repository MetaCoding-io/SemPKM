# T03: 10-bug-fixes-and-cleanup-architecture 03

**Slice:** S10 — **Milestone:** M001

## Description

Implement the htmx cleanup architecture and design the editor group data model.

Purpose: Every time a user navigates between tabs, htmx swaps DOM content without destroying CodeMirror, Split.js, and Cytoscape instances attached to the old DOM. This causes memory leaks and duplicate gutters/listeners over repeated navigation. This plan establishes a centralized cleanup registry that `htmx:beforeCleanupElement` invokes before DOM removal, then registers all three library types in it. Additionally, it produces a design document for the editor group data model needed by Phase 14.

Output: Cleanup architecture preventing resource leaks, plus an editor group data model design document.

## Must-Haves

- [ ] "Navigating between tabs 30+ times does not accumulate duplicate event listeners, Split.js gutters, or CodeMirror instances"
- [ ] "htmx:beforeCleanupElement fires and invokes registered teardown functions before DOM removal"
- [ ] "CodeMirror .destroy(), Split.js .destroy(), and Cytoscape .destroy() are called on cleanup"
- [ ] "An editor group data model design document exists describing the WorkspaceLayout class for Phase 14"

## Files

- `frontend/static/js/cleanup.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/base.html`
- `.planning/phases/10-bug-fixes-and-cleanup-architecture/EDITOR-GROUPS-DESIGN.md`
