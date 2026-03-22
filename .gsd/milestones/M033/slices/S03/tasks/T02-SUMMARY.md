---
id: T02
parent: S03
milestone: M033
provides:
  - calendar_view.html template with lazy-loaded FullCalendar 6.1.17, CDN loading, data fetch, eventClick handler
  - Calendar CSS — .calendar-container flex child + dark mode FullCalendar overrides via CSS variables
  - Calendar View explorer sidebar entry with drag-drop support
  - "calendar" label in openGenericViewTab() for tab title resolution
key_files:
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
key_decisions:
  - Used FullCalendar CSS custom properties (--fc-*) for dark mode instead of overriding individual element styles — cleaner and forward-compatible with FullCalendar updates
  - Used --color-accent-subtle for today highlight instead of rgba(var(--accent-rgb), 0.08) because --accent-rgb doesn't exist in the theme system
patterns_established:
  - Calendar view follows the same view-flex-column + CDN-lazy-load + data-fetch pattern that could be reused for other third-party visualization views
observability_surfaces:
  - Console error "[calendar] failed to load FullCalendar CDN" on CDN failure
  - Console error "[calendar] data fetch failed" on API error
  - data-testid="calendar-view" on container for E2E automation
  - Three distinct empty states visible in DOM for no-type/no-dates/fetch-error
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Frontend — template, CSS, explorer entry, and workspace.js integration

**Built calendar view frontend: FullCalendar 6.x template with CDN lazy-loading, dark mode CSS overrides, explorer sidebar entry, and workspace.js label registration**

## What Happened

1. **`calendar_view.html`**: Replaced T01's skeleton with the full template. Uses `view-flex-column` wrapper, includes type filter pills and view toolbar. The inline `<script>` lazy-loads FullCalendar 6.1.17 from jsDelivr CDN, fetches event data from the backend's `/browser/views/generic/calendar/data` endpoint with `credentials: 'include'`, and initializes a FullCalendar.Calendar with `dayGridMonth`/`timeGridWeek`/`timeGridDay` view switching. The `eventClick` handler extracts `extendedProps.iri` and calls `openTab(iri, title)`. Error handling covers CDN load failure, data fetch failure, and missing container element.

2. **`views.css`**: Added `.calendar-container` with `flex: 1; min-height: 0; overflow: auto; padding: 12px` following the kanban/graph flex-child pattern. Light mode sets accent-colored events via `--fc-event-bg-color`. Dark mode overrides use FullCalendar's CSS custom properties (`--fc-border-color`, `--fc-page-bg-color`, `--fc-neutral-bg-color`, etc.) mapped to the theme's existing CSS variables. Additional dark mode rules cover button states, header text, and today highlight.

3. **`views_explorer.html`**: Added Calendar View entry after Kanban View, before Saved Views folder. Uses 📅 (`&#128197;`) icon, `onclick="openGenericViewTab('calendar')"`, and `ondragstart` with canvas drag payload for spatial canvas integration.

4. **`workspace.js`**: Added `calendar: 'Calendar View'` to the labels dict at line 3474, enabling tab title resolution for `openGenericViewTab('calendar')`.

## Verification

- **Unit tests**: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — 22/22 passed
- **Failure path**: `test_query_failure_returns_empty` — passed
- **Browser: sidebar entry**: Calendar View appears between Kanban View and Saved Views with 📅 icon
- **Browser: panel opens**: Clicking Calendar View opens a Generic View tab with type filter pills and "Select a type" empty state
- **Browser: FullCalendar renders**: Selecting Event Shape loads FullCalendar month grid with events ("Daily Standup", "Weekly Design Review", "Team Offsite")
- **Browser: view switching**: month → week → day all work; headings update correctly ("March 2026" → "Mar 22 – 28, 2026" → "March 22, 2026")
- **Browser: event click**: Clicking "Daily Standup — SemPKM" event opens object tab showing full event properties
- **Browser: dark mode**: Toggling `data-theme="dark"` renders calendar with proper dark theme — no white-on-white text, accent-colored events, today highlight visible
- **Browser assertions**: `data-testid="calendar-view"` visible, `.fc` container visible, "Calendar View" text in sidebar — all pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.50s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py::TestExecuteCalendarQuery::test_query_failure_returns_empty -v` | 0 | ✅ pass | 0.45s |
| 3 | `browser_assert: data-testid="calendar-view" visible` | — | ✅ pass | — |
| 4 | `browser_assert: .fc container visible` | — | ✅ pass | — |
| 5 | `browser_assert: "Calendar View" text visible` | — | ✅ pass | — |
| 6 | `browser: event click → object tab opens` | — | ✅ pass | — |
| 7 | `browser: month/week/day view switching` | — | ✅ pass | — |
| 8 | `browser: dark mode rendering` | — | ✅ pass | — |

## Diagnostics

- **CDN failure**: Console error `[calendar] failed to load FullCalendar CDN` + visible "Failed to load calendar library" text in UI
- **Data fetch failure**: Console error `[calendar] data fetch failed: <err>` + visible "Failed to load calendar data" text in UI
- **Empty states**: Three distinct messages identify the state: "Select a type to use Calendar View" (no type), "Select a type with date properties to use Calendar View" (no dates), "Failed to load calendar data" (error)
- **DOM inspection**: `document.querySelector('[data-testid="calendar-view"]')` returns the calendar container; `document.querySelector('.fc')` returns the FullCalendar instance

## Deviations

- Used `--color-accent-subtle` for today highlight instead of `rgba(var(--accent-rgb), 0.08)` because `--accent-rgb` doesn't exist in the theme. The existing `--color-accent-subtle` provides the correct rgba value for both light and dark themes.
- Added extra dark mode rules for `.fc-button`, `.fc-button:hover`, `.fc-button-active`, `.fc-col-header-cell`, and `.fc-day-today` beyond what the plan specified, to ensure full dark theme coverage.

## Known Issues

- None

## Files Created/Modified

- `backend/app/templates/browser/calendar_view.html` — Full calendar view template with FullCalendar CDN lazy-loading, data fetch, and event click handler
- `frontend/static/css/views.css` — Added .calendar-container flex child, light mode event accent colors, and comprehensive dark mode FullCalendar overrides
- `backend/app/templates/browser/views_explorer.html` — Added Calendar View entry after Kanban View with 📅 icon and drag-drop support
- `frontend/static/js/workspace.js` — Added `calendar: 'Calendar View'` to labels dict
- `.gsd/milestones/M033/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section
