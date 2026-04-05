---
id: S02
parent: M050
milestone: M050
provides:
  - Clean view toolbar — no View Variants dropdown, visible calendar dark mode nav, dismissible timeline popups
requires:
  - slice: S01
    provides: Smart type dropdown replacing 37-pill type bar
affects:
  - S03
key_files:
  - frontend/static/css/views.css
  - backend/app/templates/browser/timeline_view.html
key_decisions:
  - Replaced 3 direct-property FC dark mode override blocks with 8 FC6 custom properties — lets FC6 read colors natively instead of fighting specificity
  - Used gantt.hide_popup() Frappe Gantt built-in API for dismiss, with document-level listeners + registerCleanup matching the established dockview cleanup pattern
patterns_established:
  - (none)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M050/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M050/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T21:46:25.679Z
blocker_discovered: false
---

# S02: Toolbar Cleanup + View Polish

**Fixed calendar dark mode nav icon visibility via FC6 custom properties and added Escape/click-outside dismiss for timeline Gantt popups.**

## What Happened

Two targeted CSS/JS polish fixes for the view system.

**T01 — Calendar dark mode nav icons:** FullCalendar 6's `.fc-button-primary` reads icon color from `--fc-button-text-color`, not from a direct `color` property. The existing dark mode override set `color` directly on `.fc .fc-button`, but FC6's custom-property rule won the specificity battle, leaving prev/next nav icons invisible in dark mode. Fixed by adding all 8 `--fc-button-*` custom properties to the `[data-theme="dark"] .fc` block, which FC6 reads natively. Removed three now-redundant direct-property override blocks (`.fc-button`, `.fc-button:hover`, `.fc-button-active`).

**T02 — Timeline popup dismiss:** Frappe Gantt 1.2.2's `.popup-wrapper` has no built-in dismiss mechanism — clicking another bar is the only way to close it. Added two document-level event listeners inside the `initTimeline()` callback: a click handler that calls `gantt.hide_popup()` when clicking outside `.popup-wrapper` and `.bar-wrapper`, and a keydown handler that dismisses on Escape when the popup is visible. Both listeners are cleaned up via `window.registerCleanup('timeline-container', ...)` for dockview panel lifecycle, matching the established pattern from calendar.js and canvas.js.

## Verification

All slice-level checks passed:
- `grep -c 'fc-button-text-color' frontend/static/css/views.css` → 1 ✅
- `grep -c 'fc-button-bg-color' frontend/static/css/views.css` → 1 ✅
- `grep -c 'fc-button-active-text-color' frontend/static/css/views.css` → 1 ✅
- `grep -n '[data-theme="dark"] .fc .fc-button'` → no matches (direct overrides removed) ✅
- `grep -c 'hide_popup' backend/app/templates/browser/timeline_view.html` → 2 ✅
- `grep -c 'Escape' backend/app/templates/browser/timeline_view.html` → 2 ✅
- `grep -c 'registerCleanup' backend/app/templates/browser/timeline_view.html` → 2 ✅

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/css/views.css` — Added 8 FC6 button custom properties to dark mode .fc block, removed 3 redundant direct-property override selectors
- `backend/app/templates/browser/timeline_view.html` — Added click-outside and Escape dismiss handlers for Frappe Gantt popup with dockview registerCleanup
