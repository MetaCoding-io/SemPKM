---
id: T02
parent: S02
milestone: M034
provides:
  - timeline_view.html Jinja2 template with Frappe Gantt CDN integration, lazy loading, drag-to-reschedule, click-to-open
  - Timeline dark mode CSS overrides and status-based bar coloring (bar-done, bar-active, bar-blocked)
  - Timeline entry in views explorer sidebar with canvas drag-drop support
  - "timeline" label in openGenericViewTab() labels map
key_files:
  - backend/app/templates/browser/timeline_view.html
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
key_decisions:
  - Reused calendar PATCH endpoint (/browser/views/calendar/patch) for drag-to-reschedule rather than creating a timeline-specific endpoint — same payload shape, same date-field detection
  - Set container_height to 'auto' so Frappe Gantt grows to fit all tasks within the flex-column layout instead of a fixed pixel height
  - Dependencies array from backend joined with comma-separator for Frappe Gantt v1.2.2 format (expects string, not array)
patterns_established:
  - CDN lazy-load pattern for Frappe Gantt follows same structure as FullCalendar in calendar_view.html — check global, create script tag, onload callback
  - Console logging prefix convention [timeline] matches [calendar] for consistent DevTools filtering
observability_surfaces:
  - Console log "[timeline] rendered with N tasks, M dependencies" on successful init
  - Console log "[timeline] reschedule: <iri>" on drag-to-reschedule with PATCH outcome
  - Console error "[timeline] data fetch failed: <err>" on network failure
  - In-container error states for CDN failure, fetch failure, and empty results
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Frontend timeline template, CSS, explorer wiring

**Created timeline_view.html with Frappe Gantt CDN integration, dark mode CSS, explorer sidebar entry, and workspace.js label wiring**

## What Happened

Created `timeline_view.html` following the calendar_view.html IIFE+CDN pattern. The template:
- Wraps content in `.view-flex-column` with type filter pills and view toolbar includes
- Shows error_message or empty-state when no date fields/type selected
- Lazy-loads Frappe Gantt v1.2.2 JS and CSS from jsdelivr CDN
- Fetches timeline JSON from the `timeline_data_url` context variable
- Transforms backend task objects (joining dependency arrays into comma-separated strings for Frappe Gantt format)
- Initializes Gantt with `view_mode_select: true`, `readonly_progress: true`, `scroll_to: 'today'`, `today_button: true`
- `on_date_change` POSTs to `/browser/views/calendar/patch` with `{iri, start, end}` for drag-to-reschedule
- `on_click` calls `openTab(task.id, task.name)` to open the object in a dockview tab
- Handles three failure modes: CDN load failure, fetch failure, zero tasks

Added 15 CSS rules to views.css: `.timeline-container` flex sizing, status-based bar coloring (`.bar-done`, `.bar-active`, `.bar-blocked`), popup z-index for dockview, and 9 dark mode overrides for Frappe Gantt SVG elements (grid background, header, bar labels, text, arrows, ticks, today highlight, bar progress, hover state).

Added Timeline View entry to views_explorer.html between Calendar and Map, with `draggable="true"` + `ondragstart` for canvas drag-drop and `onclick="openGenericViewTab('timeline')"`.

Added `timeline: 'Timeline View'` to the labels map in workspace.js `openGenericViewTab()`.

## Verification

- `grep -q "timeline" frontend/static/js/workspace.js` — PASS
- `grep -q "timeline" backend/app/templates/browser/views_explorer.html` — PASS
- `test -f backend/app/templates/browser/timeline_view.html` — PASS
- `grep -q "timeline-container" frontend/static/css/views.css` — PASS
- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` — 15/15 passed (no regressions)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "timeline" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "timeline" backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 3 | `test -f backend/app/templates/browser/timeline_view.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q "timeline-container" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` | 0 | ✅ pass | 3.4s |

## Diagnostics

- Filter browser DevTools console with `[timeline]` to see lifecycle events (init, render, reschedule, errors)
- `data-testid="timeline-view"` on the container div for E2E test targeting
- Three visible error states: "Failed to load timeline library." (CDN failure), "Failed to load timeline data." (fetch failure), "No tasks with dates found" (empty results)
- Frappe Gantt popup z-index set to 10000 in CSS — should escape most dockview stacking contexts

## Deviations

None — implementation follows the task plan. Used `container_height: 'auto'` (not in plan) to let Gantt auto-size within the flex container, which is better than a fixed height.

## Known Issues

- Frappe Gantt popup may still be trapped in dockview stacking context despite z-index 10000 — the KNOWLEDGE.md "Popovers inside dockview panels must escape stacking context via document.body" pattern applies. If popup appears clipped, the `popup` option in Gantt config would need a custom function that appends to document.body. Not worth pre-optimizing since the default popup is informational only.
- E2E test (`timeline.spec.ts`) does not exist yet — T03 will create it.

## Files Created/Modified

- `backend/app/templates/browser/timeline_view.html` — New Jinja2 template with Frappe Gantt CDN integration
- `frontend/static/css/views.css` — Appended timeline container styles, status bar coloring, and dark mode overrides
- `backend/app/templates/browser/views_explorer.html` — Added Timeline View entry between Calendar and Map
- `frontend/static/js/workspace.js` — Added `timeline: 'Timeline View'` to openGenericViewTab labels map
- `.gsd/milestones/M034/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section per pre-flight check
