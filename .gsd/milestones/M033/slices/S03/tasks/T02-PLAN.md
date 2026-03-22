---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: Frontend — template, CSS, explorer entry, and workspace.js integration

**Slice:** S03 — Calendar View
**Milestone:** M033

## Description

Create the calendar view frontend: the Jinja2 template that lazy-loads FullCalendar 6.x from CDN and renders the calendar grid, dark mode CSS overrides, the explorer sidebar entry, and the workspace.js label registration. Follow the kanban view template and explorer entry as the direct pattern.

## Steps

1. **Create `backend/app/templates/browser/calendar_view.html`**:
   - Use `view-flex-column` wrapper (same as kanban_view.html)
   - Include `browser/type_filter_pills.html` when `is_generic` is true
   - Include `browser/view_toolbar.html`
   - Empty state: if `error_message` is defined, show `<div class="view-empty-state"><p>{{ error_message }}</p></div>`
   - Calendar container: `<div id="calendar-container" class="calendar-container" data-testid="calendar-view"></div>`
   - Inline `<script>` block that:
     - Reads `calendar_data_url` from template context (via `{{ calendar_data_url | tojson }}`)
     - Lazy-loads FullCalendar 6.1.17 global bundle from jsDelivr CDN
     - On script load, fetches the data URL with `credentials: 'include'`
     - Initializes `new FullCalendar.Calendar()` with:
       - `initialView: 'dayGridMonth'`
       - `headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }`
       - `events: data.events`
       - `eventClick` handler: extract `info.event.extendedProps.iri` and `info.event.title`, call `openTab(iri, title)` if available
       - `height: '100%'` so it fills the flex container
     - Calls `cal.render()`

2. **Add calendar CSS to `frontend/static/css/views.css`**:
   - `.calendar-container` with `flex: 1; min-height: 0; overflow: auto;` (same flex-child pattern as `.graph-container-wrapper`, `.kanban-board`)
   - Dark mode overrides inside `[data-theme="dark"] .fc { ... }` using FullCalendar 6 CSS variables:
     - `--fc-border-color: var(--color-border)`
     - `--fc-page-bg-color: var(--color-bg)`
     - `--fc-neutral-bg-color: var(--color-bg-secondary)`
     - `--fc-list-event-hover-bg-color: var(--color-bg-hover)`
     - `--fc-today-bg-color: rgba(var(--accent-rgb), 0.08)`
     - `--fc-event-bg-color: var(--color-accent)`
     - `--fc-event-border-color: var(--color-accent)`
     - `--fc-event-text-color: #fff`
   - Light mode: `.fc` with `--fc-event-bg-color: var(--color-accent); --fc-event-border-color: var(--color-accent); --fc-event-text-color: #fff;`

3. **Add Calendar View entry in `backend/app/templates/browser/views_explorer.html`**:
   - Add after the Kanban View entry, before the Saved Views folder
   - Follow the exact same HTML pattern as the Kanban View `<a>` element
   - Use `&#128197;` (📅) or `&#9670;` as the icon
   - `onclick="openGenericViewTab('calendar'); return false;"`
   - `ondragstart` with `label:'Calendar View'` and `url:'/browser/views/generic/calendar?embed=1'`

4. **Add `calendar` label to workspace.js**:
   - At line ~3474, add `calendar: 'Calendar View'` to the `var labels = { table: ..., card: ..., graph: ..., kanban: ... }` dict

## Must-Haves

- [ ] `calendar_view.html` renders FullCalendar with month/week/day switching
- [ ] Event click calls `openTab(iri, title)`
- [ ] `data-testid="calendar-view"` on the calendar container
- [ ] Dark mode FullCalendar overrides work (no white-on-white text)
- [ ] Calendar View appears in explorer sidebar between Kanban and Saved Views
- [ ] `openGenericViewTab('calendar')` works from the sidebar entry

## Verification

- Start dev stack, navigate to workspace, click Calendar View in sidebar → panel opens with FullCalendar
- Select Event or Project type → see events on grid
- Switch month/week/day → views change
- Click an event → object tab opens
- Toggle dark mode → calendar renders with correct dark theme

## Inputs

- `backend/app/views/router.py` — T01's calendar branch providing template context (`calendar_data_url`, `error_message`, `is_generic`, etc.)
- `backend/app/views/service.py` — T01's `execute_calendar_query()` providing the JSON data
- `backend/app/templates/browser/kanban_view.html` — template pattern to follow
- `backend/app/templates/browser/views_explorer.html` — existing sidebar entries to add after
- `frontend/static/js/workspace.js` — labels dict at ~line 3474
- `frontend/static/css/views.css` — existing view CSS for flex-child patterns

## Expected Output

- `backend/app/templates/browser/calendar_view.html` — new template file
- `frontend/static/css/views.css` — modified with calendar container + dark mode overrides
- `backend/app/templates/browser/views_explorer.html` — modified with Calendar View entry
- `frontend/static/js/workspace.js` — modified with `calendar` label

## Observability Impact

- **CDN load failures:** Console error `[calendar] failed to load FullCalendar CDN` with visible "Failed to load calendar library" empty state in the UI.
- **Data fetch failures:** Console error `[calendar] data fetch failed: <err>` with visible "Failed to load calendar data" empty state.
- **Empty states:** Three distinct states visible in HTML: (1) "Select a type to use Calendar View" (no type selected), (2) "Select a type with date properties to use Calendar View" (type has no dates), (3) "Failed to load calendar data" (fetch error). Each identifiable via `view-empty-state` class.
- **Calendar rendering:** FullCalendar's `.fc` container is inspectable in DOM; the `data-testid="calendar-view"` attribute on `#calendar-container` enables test automation discovery.
- **Event click tracing:** `eventClick` handler logs nothing on success (standard `openTab` call), but `openTab` not being defined would silently no-op rather than crash.
