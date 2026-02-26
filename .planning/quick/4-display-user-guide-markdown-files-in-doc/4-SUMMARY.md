---
phase: quick-4
plan: 01
subsystem: documentation-ui
tags: [docs, markdown, htmx, workspace]
dependency_graph:
  requires: [18-01-PLAN (StaticFiles /docs/guide mount), 11-01-PLAN (marked.js + DOMPurify CDN)]
  provides: [in-tab markdown viewer for all 26 user guide files]
  affects: [browser/router.py, docs_page.html, workspace.css, markdown-render.js]
tech_stack:
  added: []
  patterns: [fetch + marked.js client-side rendering, htmx hx-get fragment swap, Lucide re-init after swap]
key_files:
  created:
    - backend/app/templates/browser/docs_viewer.html
  modified:
    - frontend/static/js/markdown-render.js
    - backend/app/browser/router.py
    - backend/app/templates/browser/docs_page.html
    - frontend/static/css/workspace.css
decisions:
  - "button elements (not a anchors) for chapter items to avoid anchor navigation fighting htmx"
  - "filename:path parameter type allows dot-containing filenames like 04-workspace-interface.md"
  - "{{ filename | tojson }} in template safely encodes filename as JS string literal"
  - "Lucide re-init before renderMarkdownFromUrl so back button arrow-left icon renders immediately"
metrics:
  duration: 2min
  tasks_completed: 3
  files_modified: 5
  completed_date: 2026-02-25
---

# Quick Task 4: Display User Guide Markdown Files in Docs Tab Summary

**One-liner:** In-tab markdown reader for all 27 user guide files using fetch + marked.js rendering, htmx back-navigation, with 20 chapters and 6 appendices listed in the Docs hub.

## What Was Implemented

Replaced the stub Documentation section in the Docs & Tutorials hub (`docs_page.html`) with a full chapter list where each chapter renders its markdown inline within the workspace tab via a dedicated viewer page.

### Task 1: `renderMarkdownFromUrl` function

Added `window.renderMarkdownFromUrl(url, targetId)` to `/home/james/Code/SemPKM/frontend/static/js/markdown-render.js` inside the existing IIFE. The function:

- Locates target element by ID, returns early if missing
- Sets loading state immediately (`<p class="docs-loading">Loading...</p>`)
- Fetches raw markdown via `fetch(url).then(r => r.text())`
- Renders via `getMarked().parse()` + `DOMPurify.sanitize()` (same pattern as `renderMarkdownBody`)
- Falls back to `target.textContent = rawText` if CDN not loaded
- Shows error message on fetch failure

### Task 2: Endpoint and viewer template

Added `GET /browser/docs/guide/{filename:path}` endpoint to `/home/james/Code/SemPKM/backend/app/browser/router.py` immediately after the existing `/docs` endpoint. The `filename:path` type allows filenames containing dots.

Created `/home/james/Code/SemPKM/backend/app/templates/browser/docs_viewer.html` with:
- Back button using `hx-get="/browser/docs"` targeting `closest .group-editor-area`
- `#docs-content` div with `markdown-body` class for rendered content
- Inline IIFE that re-initializes Lucide icons then calls `renderMarkdownFromUrl`

### Task 3: Chapter list and CSS

Replaced the stub Documentation section in `docs_page.html` with:
- **User Guide section**: 20 numbered chapters (buttons with `hx-get` targeting `closest .group-editor-area`) + 6 appendices (styled slightly smaller with `.docs-chapter-appendix`)
- **External References section**: ReDoc, Swagger, Health Check links (unchanged style)
- Interactive Tutorials section left completely unchanged

Appended CSS to `/home/james/Code/SemPKM/frontend/static/css/workspace.css`:
- `.docs-chapter-list` / `.docs-chapter-item` / `.docs-chapter-appendix` for the chapter list
- `.docs-viewer` / `.docs-viewer-header` / `.docs-back-btn` for the viewer layout
- `.docs-content` / `.docs-loading` / `.docs-error` for content states

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | dce7982 | feat(quick-4-01): add renderMarkdownFromUrl to markdown-render.js |
| 2    | 984822f | feat(quick-4-01): add /browser/docs/guide/{filename} endpoint and docs_viewer.html |
| 3    | dd4a563 | feat(quick-4-01): expand docs hub with full chapter list and viewer CSS |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- FOUND: `/home/james/Code/SemPKM/frontend/static/js/markdown-render.js`
- FOUND: `/home/james/Code/SemPKM/backend/app/browser/router.py`
- FOUND: `/home/james/Code/SemPKM/backend/app/templates/browser/docs_viewer.html`
- FOUND: `/home/james/Code/SemPKM/backend/app/templates/browser/docs_page.html`
- FOUND: `/home/james/Code/SemPKM/frontend/static/css/workspace.css`
- Commits dce7982, 984822f, dd4a563 all verified in git log
