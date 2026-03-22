---
estimated_steps: 4
estimated_files: 3
skills_used:
  - test
---

# T04: Wire virtual event rendering in calendar and write E2E test

**Slice:** S04 — Recurring Tasks & RRULE Expansion
**Milestone:** M034

## Description

Connect the backend RRULE expansion (T02) to the calendar frontend (calendar.js) so virtual recurring events are visually distinct and click-to-open correctly routes to the master task. Write an E2E Playwright test that creates a recurring task via the API and verifies multiple instances appear on the calendar.

## Steps

1. **Edit `frontend/static/js/calendar.js`** — Two changes in the FullCalendar config:

   **a) `eventClassNames` callback** — Currently checks `extendedProps.sourceType` for Task/Event. Add a check for `extendedProps.isVirtual`:
   ```javascript
   eventClassNames: function (arg) {
     var ep = arg.event.extendedProps || {};
     var classes = [];
     if (ep.sourceType === 'task' || ep.sourceType === 'Task') classes.push('fc-event-task');
     if (ep.sourceType === 'event' || ep.sourceType === 'Event') classes.push('fc-event-event');
     if (ep.isVirtual) classes.push('fc-event-recurring');
     return classes;
   }
   ```

   **b) `eventClick` callback** — Currently opens `extendedProps.iri`. For virtual events, open `extendedProps.masterIri` instead:
   ```javascript
   eventClick: function (info) {
     var ep = info.event.extendedProps || {};
     var iri = ep.masterIri || ep.iri;  // virtual events point to master
     var title = info.event.title || '';
     if (iri && typeof openTab === 'function') {
       openTab(iri, title);
     }
   }
   ```

2. **Add CSS for recurring events in `frontend/static/css/views.css`**:
   ```css
   /* Recurring event visual indicator */
   .fc-event-recurring {
     border-style: dashed !important;
   }
   .fc-event-recurring .fc-event-title::before {
     content: '↻ ';
   }
   ```
   The dashed border + ↻ prefix provides clear visual distinction without requiring complex SVG. The `!important` is needed to override FullCalendar's inline border styles.

3. **Write `e2e/tests/02-views/recurring-tasks.spec.ts`** — Following the pattern from `calendar-view.spec.ts`:
   - Import auth fixtures, selectors, helpers
   - Test: "recurring task shows virtual instances on calendar"
     - Create a task via the commands API (`POST /api/commands`) with:
       - `object.create` for a Task with `dcterms:title`, `bpkm:scheduledStart` (set to a known day, e.g. next Monday), `bpkm:scheduledEnd` (1 hour later), `bpkm:recurrenceRule` = `FREQ=WEEKLY;COUNT=4`
     - Navigate to `/browser/`, open calendar view
     - Switch to the monthly view to see multiple weeks
     - Count FullCalendar events matching the task title — should be >= 2 (the master + at least one virtual)
     - Verify at least one event has the `.fc-event-recurring` CSS class
   - Test: "clicking virtual event opens master task"
     - Reuse the task from above
     - Click on a virtual instance (one with `.fc-event-recurring`)
     - Verify the object tab opens with the master task's IRI

4. **Verify full stack** — Run the E2E test against the Docker stack. The test exercises: schema (recurrenceRule property on Task), backend (RRULE expansion in calendar data endpoint), and frontend (virtual event rendering + click routing).

## Must-Haves

- [ ] Virtual events get `fc-event-recurring` CSS class
- [ ] Virtual events display with dashed border and ↻ indicator
- [ ] Clicking virtual event opens master task (uses masterIri)
- [ ] E2E test creates recurring task and verifies multiple calendar instances
- [ ] E2E test verifies recurring visual indicator (`.fc-event-recurring` class)

## Verification

- `npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts` — all pass
- Visual check: recurring events have dashed border and ↻ prefix on calendar

## Inputs

- `frontend/static/js/calendar.js` — existing calendar module with eventClassNames and eventClick handlers
- `frontend/static/css/views.css` — existing view styles
- `e2e/tests/02-views/calendar-view.spec.ts` — existing calendar E2E test for pattern reference
- `e2e/fixtures/auth.ts` — auth fixture imports
- `e2e/helpers/selectors.ts` — SEL.views.calendar selector
- `e2e/helpers/dockview.ts` — openGenericViewTab helper
- `backend/app/views/service.py` — T02's RRULE expansion (produces virtual events in calendar data)

## Expected Output

- `frontend/static/js/calendar.js` — updated eventClassNames and eventClick for virtual events
- `frontend/static/css/views.css` — `.fc-event-recurring` styles
- `e2e/tests/02-views/recurring-tasks.spec.ts` — E2E test file for recurring task calendar rendering

## Observability Impact

- **New signal:** `fc-event-recurring` CSS class on virtual calendar events — visible in DOM inspector and usable by E2E selectors
- **Changed signal:** `eventClick` handler now logs via `openTab` using `masterIri` for virtual events instead of `iri` — observable in dockview tab title showing master task name
- **Inspection:** Count recurring events: `document.querySelectorAll('.fc-event-recurring').length` in browser console
- **Failure visibility:** If RRULE expansion returns no virtual events, zero `.fc-event-recurring` elements appear. If `masterIri` is missing from extendedProps, clicking a virtual event opens nothing (existing null-check prevents errors).
