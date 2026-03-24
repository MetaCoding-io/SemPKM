---
id: T04
parent: S01
milestone: M037
provides:
  - Context indicator in workspace sidebar showing location/activity/time with real-time SSE updates
  - "Context unknown" stale state with dimmed styling when no context or SSE disconnected
key_files:
  - frontend/static/js/context-indicator.js
  - frontend/static/css/context-indicator.css
  - backend/app/templates/browser/workspace.html
key_decisions:
  - Placed indicator between pane-header and pane-content in #nav-pane rather than inside pane-content, keeping it fixed while explorer sections scroll
  - Used chip-based layout with dot separators for compact multi-facet display in narrow sidebar
patterns_established:
  - SSE EventSource pattern for frontend real-time updates — connect on DOMContentLoaded, listen for named events, fall back to stale state on error
  - Icon-to-context mapping convention — LOCATION_ICON, ACTIVITY_ICONS, TIME_ICONS objects in context-indicator.js for extending with new context facets
observability_surfaces:
  - "#context-indicator" element with "context-stale" class indicates connection/staleness state — inspectable in DevTools
  - EventSource('/api/context/stream') visible in browser Network tab as persistent text/event-stream connection
  - Console warning "[context-indicator] Failed to parse SSE data" on malformed events
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Workspace sidebar context indicator with SSE

**Added real-time context indicator to workspace sidebar with SSE-driven location/activity/time chips and stale-state fallback**

## What Happened

Created three files and modified the workspace template:

1. **context-indicator.css** — Compact flex-based bar with `.context-stale` dimming (opacity 0.5), Lucide icon sizing via CSS with `flex-shrink:0` per CLAUDE.md rules, chip layout with dot separators, and text truncation for narrow sidebar.

2. **context-indicator.js** — Self-contained IIFE that on DOMContentLoaded: (a) fetches `GET /api/context/current` for initial state, (b) opens `EventSource('/api/context/stream')` for live updates. Maps context fields to Lucide icons (map-pin for location, footprints/car/armchair for activity, sunrise/briefcase/sunset/moon for time period, calendar for events). Falls back to "Context unknown" with stale styling when context is null, stale, or SSE disconnects.

3. **workspace.html** — Added `#context-indicator` div between pane-header and pane-content in `#nav-pane`, CSS link in `{% block head %}`, JS script in `{% block scripts %}`.

Verified live behavior: POSTed context updates via curl, confirmed indicator updated in real-time from "Context unknown" → "office · Stationary · Work" → "home · Walking · Evening" with correct icons.

## Verification

All task-level and slice-level checks pass:

- Both files exist (context-indicator.js + context-indicator.css)
- Indicator present in workspace template (HTML, JS link, CSS link)
- 28/28 unit tests pass (13 service + 15 router)
- POST /api/context/update returns 200 with context JSON
- GET /api/context/current returns context with `is_stale` field
- POST without auth returns 401
- Context indicator visible in browser sidebar with real-time SSE updates
- IIFE pattern confirmed (no global pollution)
- Icons sized via CSS with `flex-shrink:0`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f frontend/static/js/context-indicator.js && test -f frontend/static/css/context-indicator.css` | 0 | ✅ pass | <1s |
| 2 | `grep -q "context-indicator" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 3 | `grep -q "context-indicator.js" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q "context-indicator.css" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` | 0 | ✅ pass | 0.74s |
| 6 | `curl -X POST /api/context/update` (with auth cookie) | 200 | ✅ pass | <1s |
| 7 | `curl /api/context/current` (with auth cookie, grep is_stale) | 0 | ✅ pass | <1s |
| 8 | `curl -X POST /api/context/update` (no auth) | 401 | ✅ pass | <1s |
| 9 | Browser visual: context indicator visible, SSE updates received | — | ✅ pass | — |

## Diagnostics

- Open browser DevTools → Elements → find `#context-indicator`. Presence of `.context-stale` class indicates stale/disconnected state.
- Network tab: look for `context/stream` SSE connection (type: eventsource). If absent or errored, indicator will be in stale state.
- Console: `[context-indicator]` prefix on SSE parse failures.
- POST `curl -X POST /api/context/update -H "Content-Type: application/json" -d '{"location_zone":"office"}' -b <cookie>` to test live indicator update.

## Deviations

- Plan suggested `<i data-lucide="radar" style="width:12px;height:12px;">` in the template HTML, but per CLAUDE.md rules, removed inline styles — CSS handles icon sizing.
- Added `{% block scripts %}` override to workspace.html instead of placing the script tag inside `{% block content %}`, which is cleaner and ensures the script loads after all other workspace JS.

## Known Issues

- Chip labels truncate with ellipsis in the narrow sidebar (~180px wide). This is intentional — the icons provide the primary signal, and labels are readable on hover/wider layouts.

## Files Created/Modified

- `frontend/static/js/context-indicator.js` — IIFE with SSE connection, context rendering, icon mapping, stale fallback (new)
- `frontend/static/css/context-indicator.css` — Compact indicator styles with chip layout, stale dimming, Lucide icon sizing (new)
- `backend/app/templates/browser/workspace.html` — Added #context-indicator element, CSS link, JS script tag
- `.gsd/milestones/M037/slices/S01/tasks/T04-PLAN.md` — Added Observability Impact section per pre-flight requirement
