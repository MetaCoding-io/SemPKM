---
estimated_steps: 7
estimated_files: 5
skills_used: []
---

# T01: Extract calendar.js, add external drop handler, enrich kanban drag data

**Slice:** S03 — Cross-View Drag & Composable Planning
**Milestone:** M034

## Description

The calendar view currently uses an inline `<script>` IIFE (~100 lines) in `calendar_view.html` with no external reference to the FullCalendar instance. This makes it impossible to call `refetchEvents()` from other views or add the droppable external-drop handler cleanly. Kanban cards only carry `data-iri` in their drag payload, missing the title needed to display a meaningful calendar event on drop.

This task: (1) extracts the calendar script to `frontend/static/js/calendar.js`, (2) adds FullCalendar `droppable: true` + `drop` callback using the `window.__calendarDragPayload` side-channel pattern from canvas.js, (3) enriches kanban drag data with `text/iri`, `text/label`, and the same side-channel, (4) adds `sempkm:command-executed` listener for automatic calendar refresh.

**Key pattern reference — canvas.js side-channel (line ~465-545):**
The existing canvas drop handler reads from `window.__canvasDragPayload` as the primary data source, with `dataTransfer.getData('text/iri')` as fallback. Kanban and explorer tree `dragstart` handlers set this side-channel. Calendar should follow the identical pattern but use `window.__calendarDragPayload` (or reuse `__canvasDragPayload` since only one drop target is active at a time). The research recommends a dedicated `__calendarDragPayload` variable.

**Key constraint:** Explorer tree drag (`tree_children.html`) already sets `text/iri`, `text/label`, and `window.__canvasDragPayload`. We should NOT change the tree drag source — just ensure the calendar drop handler can read from it. For kanban, we need to ADD the same data pattern.

## Steps

1. **Create `frontend/static/js/calendar.js`** — Extract the entire inline `<script>` IIFE from `calendar_view.html` into a new file. Refactor to export `window.initCalendar = function(containerId, dataUrl) { ... }` that creates the FullCalendar instance and stores it as `window._sempkmCalendar`. Keep the CDN lazy-load logic. Keep `patchCalendarEvent()` as a module-private helper. The existing `editable`, `selectable`, `eventDrop`, `eventResize`, `select`, and `eventClassNames` options remain unchanged.

2. **Add `droppable: true` and `drop` callback** in calendar.js. The `drop(info)` callback should:
   - Read from `window.__calendarDragPayload` first (set by kanban/tree dragstart), then fall back to `info.draggedEl.dataset.iri`
   - Extract `iri` and `title` from the payload
   - Compute `scheduledStart` from `info.dateStr` (FullCalendar provides this)
   - Compute `scheduledEnd` as `info.date` + 1 hour (default duration). Use `new Date(info.date.getTime() + 3600000).toISOString()`
   - POST to `/browser/views/calendar/patch` with `{ iri, start: scheduledStart, end: scheduledEnd }`
   - On success: call `calendar.addEvent({ id: iri, title: title, start: scheduledStart, end: scheduledEnd, extendedProps: { iri: iri, sourceType: 'Task' }, classNames: ['fc-event-task'] })` for immediate display
   - On success: dispatch `sempkm:command-executed` and show toast
   - On failure: show error toast
   - Clear `window.__calendarDragPayload = null` after reading
   - Log `[calendar] external drop: <iri> start=<start> end=<end>` for diagnostics

3. **Add `sempkm:command-executed` listener** in calendar.js — after creating the FullCalendar instance, register `document.addEventListener('sempkm:command-executed', function() { if (window._sempkmCalendar) window._sempkmCalendar.refetchEvents(); })` so external mutations (kanban status change, object edit, etc.) refresh the calendar.

4. **Update `calendar_view.html`** — Replace the entire `<script>...</script>` block with:
   ```html
   <script src="/static/js/calendar.js"></script>
   <script>
   if (typeof initCalendar === 'function') {
       initCalendar('calendar-container', {{ calendar_data_url | tojson }});
   }
   </script>
   ```

5. **Enrich kanban drag data** — In `kanban.js` `onDragStart`:
   - Read `card.dataset.iri` and `card.dataset.title` (or `card.querySelector('.kanban-card-title').textContent`)
   - Set `e.dataTransfer.setData('text/iri', iri)` in addition to existing `text/plain`
   - Set `e.dataTransfer.setData('text/label', title)`
   - Set `window.__calendarDragPayload = { iri: iri, title: title }`

6. **Add `data-title` to kanban card template** — In `kanban_view.html`, change the `.kanban-card` div to include `data-title="{{ item.label }}"`.

7. **Add CSS for external drop visual feedback** — In `views.css`, add a `.calendar-drop-active` class with a subtle highlight border/background. In calendar.js, toggle this class on the calendar container during `dragover`/`dragleave` events (register native listeners on `#calendar-container`).

## Must-Haves

- [ ] `frontend/static/js/calendar.js` exists and exports `window.initCalendar(containerId, dataUrl)`
- [ ] `window._sempkmCalendar` reference to the FullCalendar instance is set after initialization
- [ ] FullCalendar config includes `droppable: true` and a `drop` callback
- [ ] Drop callback reads from `window.__calendarDragPayload` side-channel, computes start/end, POSTs to `/browser/views/calendar/patch`
- [ ] Drop callback calls `calendar.addEvent()` for immediate visual feedback on success
- [ ] `sempkm:command-executed` listener triggers `calendar.refetchEvents()`
- [ ] Kanban `dragstart` sets `text/iri`, `text/label`, and `window.__calendarDragPayload`
- [ ] Kanban card template has `data-title="{{ item.label }}"`
- [ ] `calendar_view.html` inline script replaced with `<script src="/static/js/calendar.js">` + init call
- [ ] Existing calendar functionality (drag-to-reschedule, resize, click-to-create, color coding) is preserved

## Verification

- `test -f frontend/static/js/calendar.js` — file exists
- `grep -q "droppable.*true" frontend/static/js/calendar.js` — droppable enabled
- `grep -q "__calendarDragPayload" frontend/static/js/calendar.js` — side-channel read
- `grep -q "window._sempkmCalendar" frontend/static/js/calendar.js` — instance exported
- `grep -q "refetchEvents" frontend/static/js/calendar.js` — auto-refresh wired
- `grep -q "text/iri" frontend/static/js/kanban.js` — kanban sets IRI MIME type
- `grep -q "__calendarDragPayload" frontend/static/js/kanban.js` — kanban sets side-channel
- `grep -q "data-title" backend/app/templates/browser/kanban_view.html` — title data attr
- `grep -q "calendar.js" backend/app/templates/browser/calendar_view.html` — external script ref
- No inline FullCalendar init in calendar_view.html (only the short init call): `! grep -q "new FullCalendar.Calendar" backend/app/templates/browser/calendar_view.html`

## Observability Impact

- Signals added: `[calendar] external drop:` console log on every external drop with IRI + start/end
- How a future agent inspects this: `window._sempkmCalendar` in browser console; `document.addEventListener('sempkm:command-executed', e => console.log('refresh'))` to verify event flow
- Failure state exposed: Toast "Failed to schedule" on PATCH error; `[calendar] external drop failed:` console.error with error details

## Inputs

- `backend/app/templates/browser/calendar_view.html` — current inline script to extract
- `frontend/static/js/kanban.js` — current drag handlers to enrich
- `backend/app/templates/browser/kanban_view.html` — card template to add data-title
- `frontend/static/js/canvas.js` — reference for `__canvasDragPayload` side-channel pattern (read-only)
- `frontend/static/css/views.css` — existing calendar CSS classes

## Expected Output

- `frontend/static/js/calendar.js` — new file, extracted + enhanced calendar module
- `frontend/static/js/kanban.js` — modified with enriched drag data
- `backend/app/templates/browser/calendar_view.html` — modified, inline script replaced
- `backend/app/templates/browser/kanban_view.html` — modified, data-title added
- `frontend/static/css/views.css` — modified, drop zone visual feedback CSS
