# S10: Bug Fixes And Cleanup Architecture

**Goal:** Fix the body loading experience and editor editability issues.
**Demo:** Fix the body loading experience and editor editability issues.

## Must-Haves


## Tasks

- [x] **T01: 10-bug-fixes-and-cleanup-architecture 01** `est:2min`
  - Fix the body loading experience and editor editability issues.

Purpose: Opening an object tab currently has no loading indicator, the editor can fail silently, and CodeMirror may render with zero height due to Split.js timing. This plan replaces the fragile setInterval polling with a Promise-based flow, adds a visible loading skeleton, implements a 3-second timeout with textarea fallback, bumps CodeMirror to fix Chrome memory leaks, and ensures a 200px minimum height on the editor container.

Output: Reliable editor loading with visible feedback, graceful fallback, and correct sizing.
- [x] **T02: 10-bug-fixes-and-cleanup-architecture 02** `est:2min`
  - Fix the autocomplete dropdown clipping and views explorer lazy-load bugs.

Purpose: Reference property autocomplete dropdowns are clipped by `overflow-y: auto` on `.object-form-section`, making suggestions invisible or partially hidden. The views explorer section shows "Loading..." forever because `hx-trigger="click once"` only fires when the user clicks the section header. This plan fixes both issues.

Output: Fully visible autocomplete dropdowns and eagerly loaded views explorer tree.
- [x] **T03: 10-bug-fixes-and-cleanup-architecture 03** `est:2min`
  - Implement the htmx cleanup architecture and design the editor group data model.

Purpose: Every time a user navigates between tabs, htmx swaps DOM content without destroying CodeMirror, Split.js, and Cytoscape instances attached to the old DOM. This causes memory leaks and duplicate gutters/listeners over repeated navigation. This plan establishes a centralized cleanup registry that `htmx:beforeCleanupElement` invokes before DOM removal, then registers all three library types in it. Additionally, it produces a design document for the editor group data model needed by Phase 14.

Output: Cleanup architecture preventing resource leaks, plus an editor group data model design document.

## Files Likely Touched

- `frontend/static/js/editor.js`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
- `frontend/static/css/forms.css`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/forms/_field.html`
- `frontend/static/js/cleanup.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/base.html`
- `.planning/phases/10-bug-fixes-and-cleanup-architecture/EDITOR-GROUPS-DESIGN.md`
