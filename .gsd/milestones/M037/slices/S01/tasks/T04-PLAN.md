---
estimated_steps: 4
estimated_files: 4
skills_used:
  - frontend-design
---

# T04: Workspace sidebar context indicator with SSE

**Slice:** S01 — Backend Context API & Workspace Indicator
**Milestone:** M037

## Description

Add a context indicator to the workspace sidebar that shows the user's current context (location zone, activity, time period, calendar event) and updates in real-time via SSE. When context is stale or absent, the indicator shows "Unknown" with muted styling. The indicator sits at the top of the sidebar nav-pane as a compact status bar.

## Steps

1. Create `frontend/static/css/context-indicator.css` with styles for the context indicator:
   - `.context-indicator` — compact bar at top of sidebar, below pane header. Uses `display:flex; align-items:center; gap:6px; padding:6px 12px;` with `border-bottom: 1px solid var(--color-border)`. Font size small (11px). Color `var(--color-text-muted)`.
   - `.context-indicator.context-stale` — muted/dimmed state (opacity 0.5 or desaturated).
   - `.context-indicator svg` — icon sizing: `width:12px; height:12px; flex-shrink:0; stroke:currentColor;` (per CLAUDE.md Lucide icon rules).
   - `.context-chip` — individual context facet (location, activity, time). Inline-flex with small gap. Truncate long text with `text-overflow:ellipsis`.
   - `.context-separator` — thin dot or bullet between chips.

2. Create `frontend/static/js/context-indicator.js` as a self-contained IIFE:
   - On `DOMContentLoaded`, find the `#context-indicator` element.
   - Call `fetch('/api/context/current', {credentials:'same-origin'})` to populate initial state.
   - Open `new EventSource('/api/context/stream')` for real-time updates.
   - On `context_update` SSE event: parse JSON data, update indicator chips (location icon + zone name, activity icon + label, time period, optional calendar event). Remove `context-stale` class.
   - On `context_stale` SSE event: add `context-stale` class, show "Unknown" text.
   - Render function `_renderContext(data)`: maps location_zone to Lucide icon name (map-pin for any zone), activity to icon (footprints for walking, car for driving, armchair for stationary, activity for unknown), time_period to icon (sun for morning, briefcase for work_hours, sunset for evening, moon for night). Shows chips only for non-null fields. If all fields null or `is_stale`, shows "Context unknown" with muted style.
   - On EventSource error: add `context-stale` class (SSE disconnected → stale).
   - Call `lucide.createIcons()` after updating indicator HTML to render any new Lucide icon placeholders.

3. Add the context indicator HTML to `backend/app/templates/browser/workspace.html`:
   - Inside `#nav-pane`, after the pane header div (the one with "EXPLORER" and close button) and before the first `explorer-section`, add:
     ```html
     <div class="context-indicator context-stale" id="context-indicator">
         <i data-lucide="radar" style="width:12px;height:12px;"></i>
         <span class="context-status">Context unknown</span>
     </div>
     ```
   - Add `<link rel="stylesheet" href="/css/context-indicator.css">` in the head/style area.
   - Add `<script src="/js/context-indicator.js"></script>` before the closing body tag (after workspace.js).

4. Test locally: build the Docker stack, log in, check that the context indicator appears in the sidebar. POST a context update via curl and verify the indicator updates in the browser. Verify that when no context exists, it shows "Context unknown" with stale styling.

## Must-Haves

- [ ] Context indicator visible in workspace sidebar between header and explorer sections
- [ ] Initial state loaded from GET /api/context/current on page load
- [ ] SSE EventSource connected to /api/context/stream for live updates
- [ ] Stale/disconnected state shows "Context unknown" with muted styling
- [ ] Lucide icons sized via CSS (not inline styles) with `flex-shrink:0` per CLAUDE.md rules
- [ ] IIFE pattern — no global namespace pollution

## Verification

- `test -f frontend/static/js/context-indicator.js && test -f frontend/static/css/context-indicator.css` — both files exist
- `grep -q "context-indicator" backend/app/templates/browser/workspace.html` — indicator present in template
- `grep -q "context-indicator.js" backend/app/templates/browser/workspace.html` — JS loaded
- `grep -q "context-indicator.css" backend/app/templates/browser/workspace.html` — CSS loaded

## Inputs

- `backend/app/templates/browser/workspace.html` — workspace template where indicator is added
- `backend/app/context/router.py` — API endpoints the indicator calls (created in T02)
- `frontend/static/css/workspace.css` — existing CSS patterns for sidebar styling
- `frontend/static/js/workspace.js` — existing JS patterns (IIFE, Lucide icons, EventSource usage if any)

## Expected Output

- `frontend/static/js/context-indicator.js` — context indicator IIFE with SSE connection
- `frontend/static/css/context-indicator.css` — compact indicator styles
- `backend/app/templates/browser/workspace.html` — modified with indicator HTML, CSS link, JS script tag
