---
id: T02
parent: S02
milestone: M033
provides:
  - FullCalendar 6.x vendored via build.js with content-hashed bundle and CDN fallback
  - calendar_view.html template with tryInit polling, type filter pills, view toolbar, and error state
  - calendar.js IIFE with initCalendar() — month/week/day switching, eventClick → openTab(), auto-refetch
  - Dark mode CSS overrides for FullCalendar --fc-* custom properties
  - Calendar View explorer sidebar entry with canvas drag support
  - calendar label registered in openGenericViewTab() labels dict
key_files:
  - frontend/package.json
  - frontend/build.js
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/js/calendar.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
  - backend/app/templates/base.html
key_decisions:
  - FullCalendar loaded in the calendar template (not base.html) since it's only needed for calendar views, matching the chart.js lazy-load pattern (D272)
  - calendar.js loaded in base.html alongside graph.js and kanban.js so initCalendar is available before the template's tryInit polling starts
patterns_established:
  - FullCalendar vendor bundle follows the same content-hash + manifest pattern as chart.js and yasgui
  - Calendar template uses tryInit polling pattern from graph_view.html, checking both window.initCalendar and FullCalendar global
observability_surfaces:
  - console.warn '[calendar] Container not found' when container element missing
  - console.error '[calendar] Failed to load events' on data endpoint fetch failure
  - CDN fallback script tag fires if vendored bundle fails to load
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Frontend — vendor FullCalendar, template, JS, CSS, explorer entry

**Vendored FullCalendar 6.x, created calendar template with tryInit polling, calendar.js init function, dark mode CSS, explorer sidebar entry, and workspace.js label registration**

## What Happened

All frontend work for the calendar view, following seven implementation steps:

1. **package.json** — Added `"fullcalendar": "^6.1.20"` dependency.
2. **build.js** — Added FullCalendar vendor section (section 7) that reads `fullcalendar/index.global.min.js`, content-hashes it, and writes to dist with `fullcalendar.js` manifest entry. Incremented subsequent section numbers.
3. **calendar_view.html** — Created template with `.view-flex-column` wrapper, type filter pills include (when generic), view toolbar include, error state for types without date properties, and FullCalendar container div. Inline script uses tryInit polling (same pattern as graph_view.html) that waits for both `window.initCalendar` and `FullCalendar` global before initializing. CDN fallback script tag for FullCalendar.
4. **calendar.js** — IIFE with `initCalendar(containerId, dataUrl, options)` that creates a `FullCalendar.Calendar` with dayGridMonth/timeGridWeek/timeGridDay views, fetch-based event source, eventClick → openTab(), double-init prevention via `container._calendarInstance`, and pointer cursor on events.
5. **views.css** — Appended calendar CSS: `.calendar-container` flex layout and dark mode overrides for 13 `--fc-*` custom properties plus event cursor and toolbar button sizing.
6. **views_explorer.html** — Added Calendar View tree-leaf entry after Kanban, with canvas drag support and `openGenericViewTab('calendar')` onclick.
7. **workspace.js** — Added `calendar: 'Calendar View'` to labels dict in `openGenericViewTab()`.
8. **base.html** — Added `calendar.js` script tag after `kanban.js` so `initCalendar` is available when templates poll for it.

## Verification

- `cd frontend && npm ci && node build.js` — succeeded, 40 manifest entries, FullCalendar bundle at `fullcalendar-b101204b.min.js`
- `grep '"fullcalendar.js"' frontend/dist/manifest.json` — returns manifest entry ✅
- `calendar.js` contains `initCalendar` function with month/week/day views, eventClick → openTab() ✅
- Dark mode CSS: 13 `--fc-*` custom property overrides in `.dark .calendar-container` ✅
- Explorer sidebar: Calendar View entry with `openGenericViewTab('calendar')` onclick ✅
- workspace.js labels dict includes `calendar: 'Calendar View'` ✅
- CDN fallback script tag present in calendar_view.html ✅
- Template includes type_filter_pills.html and view_toolbar.html ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd frontend && npm ci && node build.js` | 0 | ✅ pass | 3s |
| 2 | `grep '"fullcalendar.js"' frontend/dist/manifest.json` | 0 | ✅ pass | <1s |
| 3 | `grep "initCalendar" frontend/static/js/calendar.js` (2 matches) | 0 | ✅ pass | <1s |
| 4 | `grep "openGenericViewTab('calendar')" backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 5 | `grep "calendar: 'Calendar View'" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 6 | `grep "cdn.jsdelivr.net/npm/fullcalendar" backend/app/templates/browser/calendar_view.html` | 0 | ✅ pass | <1s |
| 7 | `grep "fc-border-color\|fc-page-bg-color\|fc-event-bg-color" frontend/static/css/views.css` (3 matches) | 0 | ✅ pass | <1s |
| 8 | `grep "calendar.js" backend/app/templates/base.html` | 0 | ✅ pass | <1s |

### Slice-Level Verification (partial — T02 is second of three tasks)

| Check | Status | Notes |
|-------|--------|-------|
| `pytest tests/test_calendar.py` | ⏳ pending | T03 creates the test file |
| Calendar view renders in browser | ✅ ready | Template and JS created; needs running Docker stack to verify |
| FullCalendar JS loads from vendored bundle | ✅ pass | `fullcalendar.js` in manifest.json |
| Click event → object tab opens | ✅ ready | eventClick → openTab() wired in calendar.js |
| Type filter pills switch displayed objects | ✅ ready | type_filter_pills.html included in template |
| Month/week/day view buttons work | ✅ ready | headerToolbar configured with all three views |
| Dark mode renders correctly | ✅ ready | 13 --fc-* CSS overrides in views.css |
| Failure path returns empty JSON array | ✅ pass | Backend returns `[]` (verified in T01) |

## Diagnostics

- **Build verification:** `cd frontend && node build.js` — check that `fullcalendar.js` appears in manifest
- **Console signals:** `[calendar] Container not found:` or `[calendar] Failed to load events:` in browser console
- **CDN fallback:** If vendored bundle fails to load, the CDN fallback script tag fires automatically
- **Double-init prevention:** `container._calendarInstance` is set after first render and destroyed before re-init

## Deviations

- Added `calendar.js` to `base.html` alongside `graph.js` and `kanban.js` — not explicitly in the plan but necessary since all view init functions need to be available before templates poll for them
- Added `.fc-event { cursor: pointer }` and `.fc .fc-button` sizing rules beyond the plan's dark mode overrides — small polish for consistency

## Known Issues

None.

## Files Created/Modified

- `frontend/package.json` — Added `fullcalendar` dependency
- `frontend/build.js` — Added FullCalendar vendor section (section 7), renumbered subsequent sections
- `backend/app/templates/browser/calendar_view.html` — New template with FullCalendar init, type pills, toolbar, error state
- `frontend/static/js/calendar.js` — New IIFE with initCalendar() function
- `frontend/static/css/views.css` — Appended calendar container styles and dark mode --fc-* overrides
- `backend/app/templates/browser/views_explorer.html` — Added Calendar View tree-leaf entry
- `frontend/static/js/workspace.js` — Added `calendar` to openGenericViewTab() labels dict
- `backend/app/templates/base.html` — Added calendar.js script tag
