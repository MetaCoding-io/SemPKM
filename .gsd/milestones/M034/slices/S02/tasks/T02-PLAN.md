---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: Frontend timeline template, CSS, explorer wiring

**Slice:** S02 — Timeline / Gantt View
**Milestone:** M034

## Description

Create the Jinja2 template that loads Frappe Gantt from CDN, fetches timeline JSON data, renders task bars with dependency arrows, and handles drag-to-reschedule. Add dark mode CSS overrides. Wire the Timeline entry into the explorer sidebar and workspace.js label map.

## Steps

1. **Create `backend/app/templates/browser/timeline_view.html`** following the `calendar_view.html` IIFE+CDN pattern:
   - Wrap in `.view-flex-column` div for full-height layout.
   - Include `type_filter_pills.html` and `view_toolbar.html` (same as calendar/map).
   - If `error_message` is set, show `.view-empty-state` with the error text and stop.
   - If `date_fields` is truthy, render the timeline container: `<div id="timeline-container" class="timeline-container" data-testid="timeline-view"></div>`.
   - IIFE script block:
     - CDN URLs: `https://cdn.jsdelivr.net/npm/frappe-gantt@1.2.2/dist/frappe-gantt.umd.js` (JS) and `https://cdn.jsdelivr.net/npm/frappe-gantt@1.2.2/dist/frappe-gantt.css` (CSS — inject as `<link>` if not already present).
     - Lazy-load pattern: check `typeof Gantt !== 'undefined'`, if not, create script tag, onload → init. Same pattern as FullCalendar CDN load in calendar_view.html.
     - Fetch `timeline_data_url` (from Jinja context via `{{ timeline_data_url | tojson }}`), parse JSON.
     - Transform tasks: each task object `{id, name, start, end, progress, dependencies, custom_class}` maps directly to Frappe Gantt format. Dates are already YYYY-MM-DD from backend.
     - If zero tasks, show empty state: `<div class="view-empty-state"><p>No tasks with dates found</p></div>` and skip Gantt init.
     - Init: `new Gantt('#timeline-container', tasks, { ... })` with config:
       - `view_mode: 'Week'`
       - `view_mode_select: true`
       - `view_modes: ['Day', 'Week', 'Month', 'Year']`
       - `bar_height: 30`
       - `readonly_progress: true` (no progress drag)
       - `scroll_to: 'today'`
       - `today_button: true`
       - `on_date_change: function(task, start, end)` — POST to `/browser/views/calendar/patch` with `{iri: task.id, start: formatDate(start), end: formatDate(end)}`. Use `credentials: 'include'`. Log success/failure.
       - `on_click: function(task)` — call `window.openTab(task.id, task.name)` to open the object in a tab.
     - Helper `formatDate(d)` — if Date object, format as ISO string. If already string, pass through.
   - Call `lucide.createIcons()` at the end for toolbar icons.

2. **Add dark mode CSS overrides** to `frontend/static/css/views.css`:
   - `.timeline-container` — `flex: 1; min-height: 0; overflow: auto;` (full-height in `.view-flex-column`).
   - `[data-theme="dark"] .gantt-container` — `background: var(--color-surface);`
   - `[data-theme="dark"] .gantt .grid-background` — `fill: var(--color-surface);`
   - `[data-theme="dark"] .gantt .grid-header` — `fill: var(--color-surface-raised);`
   - `[data-theme="dark"] .gantt .bar-label` — `fill: var(--color-text);`
   - `[data-theme="dark"] .gantt .lower-text, [data-theme="dark"] .gantt .upper-text` — `fill: var(--color-text-muted);`
   - `[data-theme="dark"] .gantt .arrow` — `stroke: var(--color-text-muted);`
   - Status-based bar coloring: `.bar-done .bar-progress { fill: var(--color-success); }`, `.bar-active .bar-progress { fill: var(--color-accent); }`, `.bar-blocked .bar-progress { fill: var(--color-danger); }`
   - `.gantt .popup-wrapper` — ensure popup z-index works within dockview panel.

3. **Add Timeline entry to `backend/app/templates/browser/views_explorer.html`**:
   - Copy the Calendar View `<a>` element pattern. Use `onclick="openGenericViewTab('timeline'); return false;"`.
   - Icon: `&#128202;` (bar chart emoji) or a suitable Unicode glyph.
   - Label: "Timeline View".
   - Add `draggable="true"` + `ondragstart` for canvas drag-drop (same pattern as other entries).
   - Position: after Calendar View, before Map View.

4. **Add timeline label to `frontend/static/js/workspace.js`**:
   - In the `openGenericViewTab()` function, add `timeline: 'Timeline View'` to the `labels` object.

## Must-Haves

- [ ] Frappe Gantt loads from CDN and renders task bars
- [ ] Dependency arrows display between linked tasks
- [ ] Drag-to-reschedule fires POST to `/browser/views/calendar/patch` with correct payload
- [ ] Click on task bar opens the object tab via `openTab()`
- [ ] Zoom level selector works (Day/Week/Month/Year)
- [ ] Empty state shown when no tasks have dates
- [ ] Dark mode CSS overrides applied
- [ ] Timeline entry in views explorer sidebar
- [ ] `openGenericViewTab('timeline')` resolves correct tab label

## Verification

- Open Docker stack (`docker compose up`), navigate to workspace, click Timeline View in explorer → Frappe Gantt renders
- Install basic-pkm model with seed data → timeline shows seed tasks (those with dueDate)
- Toggle dark mode → chart colors respect theme variables
- `grep -q "timeline" frontend/static/js/workspace.js` confirms label added
- `grep -q "timeline" backend/app/templates/browser/views_explorer.html` confirms explorer entry

## Inputs

- `backend/app/views/router.py` — T01 added timeline renderer blocks that pass `timeline_data_url` and context to template
- `backend/app/views/service.py` — T01 added `execute_timeline_query()` returning `{tasks: [...]}` JSON
- `backend/app/templates/browser/calendar_view.html` — pattern reference for IIFE+CDN+fetch structure
- `backend/app/templates/browser/views_explorer.html` — existing entries to copy pattern from
- `frontend/static/js/workspace.js` — `openGenericViewTab()` labels map
- `frontend/static/css/views.css` — existing view styles (`.view-flex-column`, dark mode patterns for other views)

## Expected Output

- `backend/app/templates/browser/timeline_view.html` — new Jinja2 template with Frappe Gantt integration
- `frontend/static/css/views.css` — dark mode overrides + timeline container styles appended
- `backend/app/templates/browser/views_explorer.html` — Timeline View entry added
- `frontend/static/js/workspace.js` — `timeline: 'Timeline View'` added to labels map

## Observability Impact

- **Console logging:** IIFE logs `[timeline] rendered with N tasks, M dependencies` on successful init, `[timeline] no tasks to render` for empty state, `[timeline] data fetch failed: <error>` on network failure, and `[timeline] reschedule: <iri>` on drag-to-reschedule attempts
- **Custom events:** Fires `sempkm:command-executed` after successful PATCH (same as calendar view) — downstream event log refreshes pick this up
- **Failure visibility:** CDN load failure renders in-container error state (`Failed to load timeline library.`); fetch failure renders `Failed to load timeline data.`; empty results render `No tasks with dates found`
- **Inspection:** Browser DevTools console filter `[timeline]` shows all lifecycle events
