---
id: T04
parent: S04
milestone: M034
provides:
  - fc-event-recurring CSS class on virtual calendar events
  - masterIri-based click routing for virtual events
  - E2E test proving recurring tasks render as multiple calendar instances
key_files:
  - frontend/static/js/calendar.js
  - frontend/static/css/views.css
  - e2e/tests/02-views/recurring-tasks.spec.ts
  - backend/app/templates/browser/calendar_view.html
  - backend/app/templates/forms/_field.html
key_decisions:
  - Fixed pre-existing /static/js/ → /js/ path bug and calendar.js lazy-load race condition in template
patterns_established:
  - Use lazy-load script pattern (createElement + onload) for JS loaded via htmx swap — inline <script src> tags race with subsequent inline scripts
observability_surfaces:
  - DOM inspector: document.querySelectorAll('.fc-event-recurring').length shows virtual event count
  - openTab intercept: window.__lastOpenTabIri in browser console after clicking virtual event
duration: 1.5h
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T04: Wire virtual event rendering in calendar and write E2E test

**Added fc-event-recurring CSS class and masterIri click routing for virtual calendar events, with E2E tests proving recurring tasks render as multiple calendar instances**

## What Happened

Three frontend changes and one E2E test file:

1. **calendar.js** — Extended `eventClassNames` to add `fc-event-recurring` class when `extendedProps.isVirtual` is true. Extended `eventClick` to use `extendedProps.masterIri` (falling back to `extendedProps.iri`) so clicking a virtual recurring event opens the master task.

2. **views.css** — Added `.fc-event-recurring` styles: dashed border and `↻ ` prefix on event titles.

3. **calendar_view.html** — Fixed two pre-existing bugs that prevented calendar.js from loading:
   - Path: `/static/js/calendar.js` → `/js/calendar.js` (nginx serves `/js/` but has no `/static/` location)
   - Race condition: inline `<script src>` tag loaded asynchronously via htmx swap, but the subsequent inline script ran before the external script finished. Replaced with lazy-load pattern (createElement + onload callback).

4. **_field.html** — Fixed same `/static/js/` → `/js/` path for recurrence-editor.js (T03's files had the same bug).

5. **recurring-tasks.spec.ts** — Two E2E tests:
   - "recurring task shows virtual instances on calendar": Creates a FREQ=WEEKLY;COUNT=4 task via API, opens merged calendar, verifies ≥2 events with task title and ≥1 with `.fc-event-recurring` class
   - "clicking virtual event opens master task": Creates recurring task, intercepts `openTab`, clicks virtual event filtered by title, verifies opened IRI matches master

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` — 24/24 pass
- `cd e2e && npx playwright test tests/02-views/recurring-tasks.spec.ts --project=chromium` — 2/2 pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` | 0 | ✅ pass | 2.9s |
| 2 | `cd e2e && npx playwright test tests/02-views/recurring-tasks.spec.ts --project=chromium` | 0 | ✅ pass | 24.4s |

## Diagnostics

- Virtual event count: `document.querySelectorAll('.fc-event-recurring').length` in browser console
- Check if calendar.js loads: nginx log should show `/js/calendar.js` → 200 (not 404)
- Check masterIri routing: intercept `openTab` via `window.openTab = function(iri, title) { console.log('[test]', iri); originalOpenTab(iri, title); }`
- Backend RRULE expansion: check server logs for `execute_calendar_query: type=... events=N (real=M virtual=V)`

## Deviations

1. **Calendar uses merged mode in E2E tests** — Plan suggested setting `localStorage` to Task type. In practice, Task type triggered `_detect_date_fields` which couldn't find date fields in the htmx-swapped context. Merged mode (no type filter) always renders the calendar with both Events and Tasks, which is the actual default user experience.

2. **Fixed pre-existing calendar.js loading bugs** — Not in the plan but required for any calendar functionality to work. The `/static/js/calendar.js` path returned 404 from nginx, and the `<script src>` tag raced with the inline init script during htmx swaps.

3. **Click verification uses openTab intercept instead of panel DOM inspection** — Dockview panel selectors were unreliable for detecting newly-opened tabs. Intercepting `window.openTab` provides a direct, reliable assertion that the correct IRI was passed.

## Known Issues

- The existing `calendar-view.spec.ts` tests (from M033) also fail due to the same `/static/js/calendar.js` 404 bug that existed before this task. The template fix in this task resolves it for all calendar views.

## Files Created/Modified

- `frontend/static/js/calendar.js` — Added fc-event-recurring class for virtual events, masterIri click routing
- `frontend/static/css/views.css` — Added .fc-event-recurring dashed border and ↻ prefix styles
- `e2e/tests/02-views/recurring-tasks.spec.ts` — E2E tests for recurring task calendar rendering and click behavior
- `backend/app/templates/browser/calendar_view.html` — Fixed JS path and lazy-load race condition
- `backend/app/templates/forms/_field.html` — Fixed recurrence-editor.js path from /static/js/ to /js/
- `.gsd/milestones/M034/slices/S04/tasks/T04-PLAN.md` — Added Observability Impact section
