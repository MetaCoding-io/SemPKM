---
id: T02
parent: S02
milestone: M050
key_files:
  - backend/app/templates/browser/timeline_view.html
key_decisions:
  - Used gantt.hide_popup() API for popup dismissal — Frappe Gantt 1.x built-in method
  - Document-level listeners with registerCleanup matching calendar.js/canvas.js pattern
duration: 
verification_result: passed
completed_at: 2026-04-05T21:45:10.517Z
blocker_discovered: false
---

# T02: Added click-outside and Escape dismiss handlers for Frappe Gantt popup in timeline view with dockview cleanup registration

**Added click-outside and Escape dismiss handlers for Frappe Gantt popup in timeline view with dockview cleanup registration**

## What Happened

Added two document-level event listeners inside the initTimeline() .then() callback after the Gantt instantiation: a click-outside handler that dismisses the popup when clicking outside .popup-wrapper and .bar-wrapper, and an Escape keydown handler that dismisses when the popup is visible. Both are cleaned up via window.registerCleanup('timeline-container', ...) for dockview panel lifecycle.

## Verification

All task-level grep checks pass: hide_popup=2, Escape=2, registerCleanup=2. All slice-level checks pass: fc-button-text-color=1, fc-button-bg-color=1, fc-button-active-text-color=1.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'hide_popup' backend/app/templates/browser/timeline_view.html` | 0 | ✅ pass (2) | 100ms |
| 2 | `grep -c 'Escape' backend/app/templates/browser/timeline_view.html` | 0 | ✅ pass (2) | 100ms |
| 3 | `grep -c 'registerCleanup' backend/app/templates/browser/timeline_view.html` | 0 | ✅ pass (2) | 100ms |
| 4 | `grep -c 'fc-button-text-color' frontend/static/css/views.css` | 0 | ✅ pass (1) | 100ms |
| 5 | `grep -c 'fc-button-bg-color' frontend/static/css/views.css` | 0 | ✅ pass (1) | 100ms |
| 6 | `grep -c 'fc-button-active-text-color' frontend/static/css/views.css` | 0 | ✅ pass (1) | 100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/timeline_view.html`
