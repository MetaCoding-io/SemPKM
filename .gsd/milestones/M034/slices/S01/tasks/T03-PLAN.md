---
estimated_steps: 5
estimated_files: 2
skills_used:
  - frontend-design
---

# T03: Make FullCalendar editable with drag/resize/select handlers and task/event color coding

**Slice:** S01 — Editable Calendar & Task Time-Blocking
**Milestone:** M034

## Description

Transform the read-only calendar template into an interactive planning surface. Enable FullCalendar's editable/selectable modes, wire up event handlers for drag-to-reschedule, resize-to-change-duration, and click-to-create, and add CSS color coding to distinguish Tasks from Events.

FullCalendar 6.1.17 (already loaded from CDN) includes the interaction plugin in the standard `index.global.min.js` bundle — no additional CDN script is needed. The `editable`, `selectable`, `eventDrop`, `eventResize`, and `select` options are all available out of the box.

Key API surfaces:
- The PATCH endpoint (from T02) is at `POST /browser/views/calendar/patch` with body `{iri, scheduledStart?, scheduledEnd?}`.
- The `openTab()` JS function (already global) opens an object tab by IRI.
- The `openCreateForm()` or workspace's create-object functionality should be used for click-to-create. Check `workspace.js` for the correct API — likely `window.openCreateObjectTab()` or similar.
- The `showToast()` function (already global) shows feedback messages.

## Steps

1. In `backend/app/templates/browser/calendar_view.html`, modify the FullCalendar initialization:
   - Add `editable: true` — enables drag-to-reschedule for all events.
   - Add `selectable: true` — enables click-and-drag to select time ranges.
   - Add `eventStartEditable: true` — explicitly allow event start time changes.
   - Add `eventDurationEditable: true` — explicitly allow event duration changes via resize.

2. Add `eventDrop` handler:
   ```javascript
   eventDrop: function(info) {
       var iri = info.event.extendedProps && info.event.extendedProps.iri;
       if (!iri) return;
       var payload = { iri: iri, scheduledStart: info.event.startStr };
       if (info.event.end) payload.scheduledEnd = info.event.endStr;
       fetch('/browser/views/calendar/patch', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           credentials: 'include',
           body: JSON.stringify(payload)
       }).then(function(r) {
           if (!r.ok) throw new Error('Patch failed: ' + r.status);
           if (typeof showToast === 'function') showToast('Task rescheduled');
           document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
       }).catch(function(err) {
           console.error('[calendar] eventDrop patch failed:', err);
           info.revert();
           if (typeof showToast === 'function') showToast('Failed to reschedule');
       });
   }
   ```

3. Add `eventResize` handler (same pattern as eventDrop but updates end time):
   ```javascript
   eventResize: function(info) {
       var iri = info.event.extendedProps && info.event.extendedProps.iri;
       if (!iri) return;
       var payload = { iri: iri, scheduledStart: info.event.startStr };
       if (info.event.end) payload.scheduledEnd = info.event.endStr;
       fetch('/browser/views/calendar/patch', { ... same as above ... })
       .catch(function(err) { info.revert(); ... });
   }
   ```

4. Add `select` handler for click-to-create:
   ```javascript
   select: function(info) {
       // Open create form for Task type, passing selected dates as query params
       if (typeof window.showCreateFormForType === 'function') {
           window.showCreateFormForType(
               'urn:sempkm:model:basic-pkm:Task', 'Task'
           );
       }
       // Store selected dates in a session variable for the form to pick up
       window._calendarSelectedDates = {
           scheduledStart: info.startStr,
           scheduledEnd: info.endStr
       };
   }
   ```
   The `showCreateFormForType(typeIri, typeLabel)` function exists on `window` (see `workspace.js` line ~3561). It opens a dockview panel and loads `/browser/objects/new?type=...` via htmx. Pre-filling dates from the calendar selection is a nice-to-have for a future iteration — for now, opening the Task create form on click-to-select is the core behavior. The `window._calendarSelectedDates` stash can be read by a future form enhancement.

5. Add CSS color coding in `frontend/static/css/views.css`:
   - Use FullCalendar's `eventClassNames` callback to assign `.fc-event-task` or `.fc-event-event` based on `event.extendedProps.sourceType`.
   - Add CSS rules:
     ```css
     .fc-event-task { background-color: #10b981 !important; border-color: #10b981 !important; }
     .fc-event-event { background-color: #8b5cf6 !important; border-color: #8b5cf6 !important; }
     ```
   - Ensure good contrast in both light and dark themes (white text on both colors).
   - NOTE: The backend already sets `backgroundColor`/`borderColor` per-event in the merged response. The CSS classes are a fallback and provide hover/active states. The inline colors from the backend take precedence for base coloring.

## Must-Haves

- [ ] FullCalendar initialized with editable:true and selectable:true
- [ ] eventDrop handler persists new start/end via POST to /browser/views/calendar/patch
- [ ] eventResize handler persists new duration via the same endpoint
- [ ] select handler triggers task creation with pre-filled dates
- [ ] info.revert() called on PATCH failure (optimistic UI with rollback)
- [ ] CSS classes for task vs event color coding added to views.css

## Verification

- Load `http://localhost:3901/browser/views/generic?renderer=calendar&type=urn:sempkm:model:basic-pkm:Event` in browser — events should show resize handles on hover and be draggable
- Check browser console for no JS errors during calendar init
- Verify CSS: `.fc-event-task` and `.fc-event-event` rules exist in views.css

## Inputs

- `backend/app/templates/browser/calendar_view.html` — existing read-only calendar template
- `frontend/static/css/views.css` — existing calendar CSS section
- `backend/app/views/router.py` — T02's PATCH endpoint at `/browser/views/calendar/patch`

## Expected Output

- `backend/app/templates/browser/calendar_view.html` — editable FullCalendar with drag/resize/select handlers
- `frontend/static/css/views.css` — task/event color coding CSS classes

## Observability Impact

- **Console signals:** `[calendar] drop:` / `[calendar] resize:` / `[calendar] select range:` logged on each interaction with IRI and date details. `[calendar] ... persisted, event_iri:` on successful PATCH. `[calendar] ... patch failed:` on error with full error object.
- **Optimistic rollback:** `info.revert()` called on PATCH failure — the event snaps back to its original position, and a toast shows "Failed to save — reverted".
- **DOM signals:** `.fc-event-task` and `.fc-event-event` CSS classes on calendar event elements indicate type classification; inspectable via browser DevTools.
- **Network inspection:** POST to `/browser/views/calendar/patch` visible in Network tab with `{iri, start, end}` payload; response includes `{ok, event_iri}` on success or `{error}` on failure.
- **Custom event:** `sempkm:command-executed` dispatched after successful PATCH — triggers sidebar/event-log refresh listeners.
