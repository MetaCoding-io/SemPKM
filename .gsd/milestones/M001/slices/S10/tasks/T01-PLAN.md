# T01: 10-bug-fixes-and-cleanup-architecture 01

**Slice:** S10 — **Milestone:** M001

## Description

Fix the body loading experience and editor editability issues.

Purpose: Opening an object tab currently has no loading indicator, the editor can fail silently, and CodeMirror may render with zero height due to Split.js timing. This plan replaces the fragile setInterval polling with a Promise-based flow, adds a visible loading skeleton, implements a 3-second timeout with textarea fallback, bumps CodeMirror to fix Chrome memory leaks, and ensures a 200px minimum height on the editor container.

Output: Reliable editor loading with visible feedback, graceful fallback, and correct sizing.

## Must-Haves

- [ ] "Opening an object tab shows a loading skeleton that shimmers while the CodeMirror module loads"
- [ ] "If the CodeMirror editor fails to load within 3 seconds, a fallback textarea appears with an informative message"
- [ ] "The CodeMirror editor is always editable regardless of Split.js initialization timing"
- [ ] "The editor section has at least 200px minimum height even before Split.js initializes"

## Files

- `frontend/static/js/editor.js`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
