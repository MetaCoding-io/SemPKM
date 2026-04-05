---
id: T01
parent: S02
milestone: M050
key_files:
  - frontend/static/css/views.css
key_decisions:
  - Replaced three direct-property override blocks with eight FC6 custom properties in the [data-theme="dark"] .fc block
duration: 
verification_result: passed
completed_at: 2026-04-05T21:43:26.769Z
blocker_discovered: false
---

# T01: Added 8 FC6 button custom properties to dark mode .fc block and removed 3 redundant direct-property override selectors for visible calendar nav icons

**Added 8 FC6 button custom properties to dark mode .fc block and removed 3 redundant direct-property override selectors for visible calendar nav icons**

## What Happened

FullCalendar 6's .fc-button-primary reads color from --fc-button-text-color. The existing dark mode fix set color directly on .fc .fc-button, but FC6's custom-property rule won at specificity, leaving nav icons invisible. Added all 8 --fc-button-* custom properties to the [data-theme="dark"] .fc block, which FC6 reads natively. Removed the three now-redundant direct-property override blocks (.fc-button, .fc-button:hover, .fc-button-active) since the custom properties handle all states.

## Verification

Ran grep checks confirming all 3 key custom properties present (fc-button-text-color, fc-button-bg-color, fc-button-active-text-color). Verified no remaining direct-property override blocks via grep for [data-theme="dark"] .fc .fc-button returning zero matches. All 8 custom properties confirmed in the dark mode .fc block.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'fc-button-text-color' frontend/static/css/views.css` | 0 | ✅ pass | 50ms |
| 2 | `grep -c 'fc-button-bg-color' frontend/static/css/views.css` | 0 | ✅ pass | 50ms |
| 3 | `grep -c 'fc-button-active-text-color' frontend/static/css/views.css` | 0 | ✅ pass | 50ms |
| 4 | `grep -n '[data-theme="dark"] .fc .fc-button' frontend/static/css/views.css` | 1 | ✅ pass (no matches = direct overrides removed) | 50ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/views.css`
