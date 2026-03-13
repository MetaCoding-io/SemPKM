---
estimated_steps: 5
estimated_files: 5
---

# T02: Comment UI — Jinja2 templates, CSS, and workspace.js integration

**Slice:** S06 — Threaded Object Comments
**Milestone:** M003

## Description

Build the user-facing comment UI: a "Comments" section in the right-pane Details panel with threaded display, inline reply forms, and delete actions. Extends `loadRightPaneSection()` in workspace.js to load comments when an object is selected. Uses htmx for form submissions with `HX-Trigger: commentsRefreshed` for auto-refresh.

## Steps

1. **Add Comments section to workspace.html** — Insert a new `<details class="right-section" data-panel-name="comments">` block in the right pane `#right-content`, after the `lint` section and before the `{% include "browser/partials/inbox_panel.html" %}` line. Structure:
   ```html
   <details class="right-section" data-panel-name="comments" open>
     <summary class="right-section-header" draggable="true">
       <i data-lucide="grip-vertical" ...></i>
       <i data-lucide="chevron-right" class="right-section-chevron"></i>
       Comments
     </summary>
     <div class="right-section-body" id="comments-content"
          hx-trigger="commentsRefreshed from:body"
          hx-get=""
          hx-swap="innerHTML">
       <div class="right-empty">No object selected</div>
     </div>
   </details>
   ```
   The `hx-get` URL is dynamically set by JS when an object is loaded (same pattern as relations/lint).

2. **Create `comments_section.html` partial** — Template rendered by `GET /browser/object/{iri}/comments`. Contains:
   - Comment count in a small badge
   - New comment form: `<form>` with `<textarea>` (placeholder "Add a comment...") and "Post" submit button, using `hx-post="/browser/object/{iri}/comments"` with `hx-target="#comments-content"` and `hx-swap="innerHTML"`
   - Comment thread container: iterate over tree roots, include `comment_thread.html` macro for each
   - Empty state: "No comments yet. Be the first to comment." when count is 0

3. **Create `comment_thread.html` partial** — Recursive Jinja2 macro for rendering a comment and its replies:
   ```jinja2
   {% macro render_comment(comment, level) %}
   <div class="comment-item" style="margin-left: {{ [level * 20, 80] | min }}px" data-comment-iri="{{ comment.iri }}">
     <div class="comment-meta">
       <span class="comment-author">{{ comment.author_name }}</span>
       <span class="comment-time" title="{{ comment.timestamp }}">{{ comment.relative_time }}</span>
     </div>
     <div class="comment-body">{{ comment.body }}</div>
     <div class="comment-actions">
       <button class="comment-action-btn comment-reply-btn" onclick="toggleReplyForm(this)">
         <i data-lucide="reply"></i> Reply
       </button>
       {% if comment.can_delete %}
       <button class="comment-action-btn comment-delete-btn"
               hx-delete="/browser/comments/{{ comment.iri | urlencode }}"
               hx-target="#comments-content" hx-swap="innerHTML"
               hx-confirm="Delete this comment?">
         <i data-lucide="trash-2"></i>
       </button>
       {% endif %}
     </div>
     <div class="comment-reply-form" style="display:none">
       <form hx-post="/browser/object/{{ object_iri | urlencode }}/comments"
             hx-target="#comments-content" hx-swap="innerHTML">
         <input type="hidden" name="reply_to" value="{{ comment.iri }}">
         <textarea name="body" placeholder="Reply..." rows="2" required></textarea>
         <button type="submit" class="comment-submit-btn">Reply</button>
       </form>
     </div>
     {% if comment.replies %}
       <div class="comment-thread-line">
         {% for reply in comment.replies %}
           {{ render_comment(reply, level + 1) }}
         {% endfor %}
       </div>
     {% endif %}
   </div>
   {% endmacro %}
   ```
   Note: `can_delete` is true if the current user is the comment author or has owner role. `relative_time` computed in Python (e.g. "2 hours ago").

4. **Extend workspace.js `loadRightPaneSection()`** — Add `comments` case to the section URL routing:
   ```javascript
   } else if (section === 'comments') {
     url = '/browser/object/' + encodeURIComponent(objectIri) + '/comments';
   }
   ```
   Add `loadRightPaneSection(objectIri, 'comments')` alongside the existing `relations` and `lint` calls in all places where right-pane sections are loaded (object activation, tab switch, etc.). Also add a small `toggleReplyForm(btn)` function that shows/hides the `.comment-reply-form` sibling. Set the dynamic `hx-get` URL on `#comments-content` when the object IRI changes (for `commentsRefreshed` trigger to work).

5. **Add CSS styles** — In `frontend/static/css/workspace.css`, add comment-specific styles:
   - `.comment-item` — padding, margin-bottom for spacing
   - `.comment-meta` — flex row with author name (bold) and timestamp (muted, smaller)
   - `.comment-body` — body text with word-wrap
   - `.comment-body.deleted` — italic, muted color for "[deleted]" comments
   - `.comment-actions` — flex row with small action buttons
   - `.comment-action-btn` — unstyled button with icon, hover color change
   - `.comment-action-btn svg` — `width: 14px; height: 14px; flex-shrink: 0; stroke: currentColor` (per CLAUDE.md Lucide rules)
   - `.comment-reply-form` — indented form with textarea and submit button
   - `.comment-submit-btn` — small primary-style button
   - `.comment-thread-line` — thin left border for visual thread connection
   - `.comment-author` — font-weight bold, color text-primary
   - `.comment-time` — color text-muted, font-size smaller

## Must-Haves

- [ ] "Comments" section visible in right-pane Details panel
- [ ] Comments load via `loadRightPaneSection()` when object selected
- [ ] Threaded display with visual indentation (capped at 4 levels = 80px)
- [ ] Reply form toggles inline below target comment
- [ ] Delete button uses hx-delete with confirmation
- [ ] `commentsRefreshed` htmx trigger causes section to re-fetch
- [ ] Empty state shows "No comments yet" message
- [ ] Lucide icons sized via CSS with `flex-shrink: 0` (not inline styles)
- [ ] SVG icons use `stroke: currentColor` for color inheritance

## Verification

- Start Docker stack → open workspace → select an object → "Comments" section appears in right pane with empty state
- Post a comment → it appears with author name and relative timestamp
- Click Reply → inline form appears → submit reply → threaded display with indentation
- Delete a comment → body shows "[deleted]", replies preserved
- Switch to different object → comments reload for new object

## Observability Impact

- Signals added/changed: None (UI layer, no new backend signals)
- How a future agent inspects this: Browser DevTools Network tab shows `/browser/object/{iri}/comments` requests; `#comments-content` element contains rendered comment HTML; htmx `commentsRefreshed` events visible in htmx debug logging
- Failure state exposed: "Failed to load content" message in comments section if endpoint returns error (same pattern as relations/lint)

## Inputs

- `backend/app/browser/comments.py` — T01's GET/POST/DELETE endpoints (must exist and return correct HTML)
- `backend/app/templates/browser/workspace.html` — existing right-pane structure with relations and lint sections
- `frontend/static/js/workspace.js` — existing `loadRightPaneSection()` function
- `frontend/static/css/workspace.css` — existing `.right-section` styles

## Expected Output

- `backend/app/templates/browser/workspace.html` — updated with Comments section
- `backend/app/templates/browser/partials/comments_section.html` — new comment list + form partial
- `backend/app/templates/browser/partials/comment_thread.html` — new recursive thread rendering macro
- `frontend/static/js/workspace.js` — extended with comments section loading + reply form toggle
- `frontend/static/css/workspace.css` — comment-specific styles appended
