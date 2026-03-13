---
id: T02
parent: S06
milestone: M003
provides:
  - Comments section in right-pane Details panel with threaded display
  - Jinja2 templates (comments_section.html partial, comment_thread.html recursive macro)
  - CSS styles for comment items, threading, reply forms, and action buttons
  - workspace.js integration for loading comments via loadRightPaneSection()
  - toggleReplyForm() JS function for inline reply forms
  - htmx afterSettle handler for Lucide icon re-initialization
  - _relative_time() and _add_can_delete() backend helpers for UI enrichment
key_files:
  - backend/app/templates/browser/partials/comments_section.html
  - backend/app/templates/browser/partials/comment_thread.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/workspace.html
  - backend/app/browser/comments.py
  - backend/app/browser/router.py
key_decisions:
  - Moved comments_router before objects_router in router.py to avoid FastAPI :path greedy route conflict
  - Relative time computed server-side in Python (_relative_time helper) rather than client-side JS
  - can_delete flag computed server-side based on user URI and role, passed in template context
  - htmx:afterSettle event listener added globally for Lucide icon re-initialization after htmx swaps
patterns_established:
  - Comments section uses same loadRightPaneSection() pattern as relations/lint with added hx-get dynamic URL and htmx.process() for htmx-aware partials
  - Recursive Jinja2 macro (render_comment) imported via {% from %} for threaded comment rendering
  - Thread indentation capped at 4 levels (80px) via min() Jinja2 filter
observability_surfaces:
  - Browser DevTools Network tab shows GET/POST/DELETE /browser/object/{iri}/comments requests
  - htmx commentsRefreshed events visible in htmx debug logging
  - #comments-content element contains rendered comment HTML
  - Failed section loads show "Failed to load content" error message
duration: 45m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Comment UI — Jinja2 templates, CSS, and workspace.js integration

**Built user-facing comment UI with threaded display, inline reply forms, delete actions, and htmx auto-refresh in the right-pane Details panel.**

## What Happened

Implemented the complete comment UI layer across 7 files:

1. **workspace.html** — Added `<details class="right-section" data-panel-name="comments">` block in the right pane after lint, with `hx-trigger="commentsRefreshed from:body"` for auto-refresh.

2. **comments_section.html** — Rewrote the T01 stub partial with proper structure: comment form (textarea + Post button via hx-post), comment count badge, comment list with empty state message ("No comments yet. Be the first to comment."), and import of the recursive thread macro.

3. **comment_thread.html** — New recursive Jinja2 macro `render_comment(comment, object_iri, level)` with: author name + relative timestamp, comment body with deleted styling, Reply button (toggleReplyForm), conditional Delete button (hx-delete with hx-confirm), inline reply form (hidden by default), and thread line connector for nested replies.

4. **workspace.js** — Extended `loadRightPaneSection()` with `comments` case (URL: `/browser/object/{iri}/comments`), added dynamic `hx-get` URL setting + `htmx.process()` for htmx-aware partials, added `lucide.createIcons()` after content injection, added `toggleReplyForm()` function, added global `htmx:afterSettle` listener for Lucide icon re-initialization, and added `loadRightPaneSection(iri, 'comments')` calls alongside relations/lint in all code paths.

5. **workspace-layout.js** — Added `loadRightPaneSection(panel.id, 'comments')` in the dockview `onDidActivePanelChange` handler alongside relations/lint.

6. **workspace.css** — Added complete comment styling: `.comment-item`, `.comment-meta`, `.comment-author`, `.comment-time`, `.comment-body` (with `.deleted` variant), `.comment-actions`, `.comment-action-btn` (with SVG sizing per CLAUDE.md: 14px, flex-shrink: 0, stroke: currentColor), `.comment-reply-form`, `.comment-submit-btn`, `.comment-thread-line`, `.comments-empty`, `.comments-count-badge`.

7. **Backend enrichment** — Added `_relative_time()`, `_add_relative_times()`, and `_add_can_delete()` helpers in comments.py. These compute human-readable timestamps ("just now", "2 hours ago") and delete permission flags server-side before template rendering.

8. **Router fix** — Moved `comments_router` before `objects_router` in `router.py` to prevent FastAPI's `:path` greedy matching from consuming `/comments` as part of the object IRI.

## Verification

- **Unit tests:** `backend/.venv/bin/python -m pytest tests/test_comments.py -v` — 30 passed (14 original + 16 new for _relative_time, _add_can_delete, _add_relative_times)
- **Browser verification:**
  - Comments section visible in right pane with empty state ✓
  - Posted a comment → appeared with author UUID prefix + "just now" timestamp ✓
  - Clicked Reply → inline form appeared → submitted reply → threaded display with indentation ✓
  - Deleted parent comment → body shows "[deleted]", author "Unknown", reply preserved ✓
  - commentsRefreshed htmx trigger causes auto-refresh after POST/DELETE ✓
  - Lucide icons (reply, trash-2) rendered as SVGs with correct sizing ✓
  - SVG flex-shrink: 0, stroke: currentColor verified via getComputedStyle ✓
- **Slice-level checks:**
  - `backend/tests/test_comments.py` — 30/30 passed ✓
  - `e2e/tests/21-comments/` — not yet created (T03 scope)

## Diagnostics

- Network tab: GET/POST/DELETE requests to `/browser/object/{iri}/comments` and `/browser/comments/{iri}`
- `#comments-content` element innerHTML shows rendered comment HTML
- `hx-get` attribute on `#comments-content` shows the dynamic URL for auto-refresh
- Comment form submissions trigger `commentsRefreshed` HX-Trigger for reload cycle

## Deviations

- **Router ordering fix**: comments_router must be included before objects_router in router.py due to FastAPI :path parameter greedy matching — not anticipated in the task plan
- **workspace-layout.js update**: Task plan only mentioned workspace.js, but dockview's onDidActivePanelChange handler also needed the comments loadRightPaneSection call
- **Backend helper additions**: Added _relative_time(), _add_can_delete(), _add_relative_times() to comments.py for server-side template enrichment — necessary for relative timestamps and delete button visibility

## Known Issues

- Author display shows UUID prefix (e.g. "3e2b4053") when user has no display_name set in the SQL users table — this is expected behavior, not a bug
- No E2E tests yet (T03 scope)

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — Added Comments section `<details>` block in right pane
- `backend/app/templates/browser/partials/comments_section.html` — Rewrote with proper structure, form, and macro import
- `backend/app/templates/browser/partials/comment_thread.html` — New recursive Jinja2 macro for threaded rendering
- `frontend/static/js/workspace.js` — Extended loadRightPaneSection, added toggleReplyForm, htmx:afterSettle listener
- `frontend/static/js/workspace-layout.js` — Added comments loading in dockview onDidActivePanelChange
- `frontend/static/css/workspace.css` — Added ~180 lines of comment-specific styles
- `backend/app/browser/comments.py` — Added _relative_time, _add_relative_times, _add_can_delete helpers
- `backend/app/browser/router.py` — Reordered router includes (comments before objects)
- `backend/tests/test_comments.py` — Added 16 tests for new helper functions
