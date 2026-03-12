# S41: Gap Closure Rules Flip Vfs

**Goal:** Wire the rules graph into model install and add validation enqueue after promote_triple.
**Demo:** Wire the rules graph into model install and add validation enqueue after promote_triple.

## Must-Haves


## Tasks

- [x] **T01: 41-gap-closure-rules-flip-vfs 01** `est:1min`
  - Wire the rules graph into model install and add validation enqueue after promote_triple.

Purpose: Close two INF-02 gaps -- (1) rules graph triples are loaded by the archive loader but never written to the triplestore during install_model, and (2) promoting an inferred triple commits to EventStore but never triggers re-validation.
Output: Two surgical code changes in models.py and inference/router.py.
- [x] **T02: 41-gap-closure-rules-flip-vfs 02** `est:2min`
  - Permanently fix the recurring flip card bleed-through bug and document the fix pattern.

Purpose: The CSS 3D flip card has broken 3 times due to `backface-visibility: hidden` being unreliable across browsers/GPU conditions. This plan adds `display: none` as a bulletproof second layer and changes the JS timeout from 300ms (midpoint) to 600ms (animation end) to prevent timing races. CLAUDE.md gets a pitfall section to prevent a 4th recurrence.
Output: CSS + JS fixes in workspace files, new CLAUDE.md section.
- [x] **T03: 41-gap-closure-rules-flip-vfs 03** `est:2min`
  - Add an in-app VFS browser view as a dockview tab accessible from the sidebar.

Purpose: Users currently need an external WebDAV client to browse the virtual filesystem. This plan adds a tree-view browser inside the workspace, following the established special-panel pattern (settings, docs, canvas). The tree shows installed models -> types -> objects, with click-to-open for objects.
Output: Backend route, template, sidebar entry, and JS tab function.

## Files Likely Touched

- `backend/app/services/models.py`
- `backend/app/inference/router.py`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
- `CLAUDE.md`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/vfs_browser.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
