---
phase: 37-global-lint-data-model-api
plan: 02
subsystem: api
tags: [sse, eventsource, shacl, validation, lint, nginx, htmx, real-time]

requires:
  - phase: 37-global-lint-data-model-api
    plan: 01
    provides: "LintService, structured result triples, /api/lint/* endpoints"
provides:
  - "SSE broadcast manager with asyncio.Queue fan-out"
  - "/api/lint/stream SSE endpoint for real-time validation events"
  - "Lint panel with SSE-driven updates (no polling)"
  - "Per-object lint results via LintService structured triples"
  - "Old /api/validation/* endpoints removed"
affects: [38-global-lint-dashboard-ui]

tech-stack:
  added: []
  patterns: [sse-fan-out-broadcast, eventsource-htmx-bridge, trigger-source-attribution]

key-files:
  created:
    - backend/app/lint/broadcast.py
  modified:
    - backend/app/lint/router.py
    - backend/app/lint/service.py
    - backend/app/validation/queue.py
    - backend/app/main.py
    - backend/app/dependencies.py
    - backend/app/browser/router.py
    - backend/app/templates/browser/lint_panel.html
    - frontend/nginx.conf
    - e2e/tests/04-validation/lint-panel.spec.ts

key-decisions:
  - "Used StreamingResponse with text/event-stream instead of fastapi.sse (not available without sse-starlette)"
  - "Single global SSE stream with client-side filtering (dashboard and per-object panel share one stream)"
  - "30s keepalive timeout to prevent connection drops through nginx proxy"
  - "EventSource reconnects automatically (browser built-in), no manual reconnect logic needed"

patterns-established:
  - "SSE fan-out: LintBroadcast with asyncio.Queue per subscriber, put_nowait with QueueFull discard"
  - "EventSource-htmx bridge: SSE event triggers htmx.ajax() to re-fetch content"
  - "Trigger source attribution: validation jobs carry trigger_source through to SSE events"

requirements-completed: [LINT-01, LINT-02]

duration: 5min
completed: 2026-03-05
---

# Phase 37 Plan 02: SSE Real-time Push & Lint Panel Migration Summary

**SSE broadcast for instant validation updates replacing 10s polling, lint panel migrated to structured result triples, old validation API removed**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T03:30:00Z
- **Completed:** 2026-03-05T03:35:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- LintBroadcast fan-out manager delivers validation_complete events to all SSE subscribers
- Lint panel updates within 1-2s of validation completion (down from 10s polling)
- Per-object lint panel queries structured result triples via LintService (single source of truth)
- Old /api/validation/* endpoints fully removed from the app router
- nginx SSE proxy configured with buffering disabled for /api/lint/stream

## Task Commits

Each task was committed atomically:

1. **Task 1: SSE broadcast manager + stream endpoint + validation queue wiring** - `d6cb8c0` (feat)
2. **Task 2: Lint panel migration + old validation router removal** - `1d452dd` (feat)

## Files Created/Modified
- `backend/app/lint/broadcast.py` - SSE broadcast manager with asyncio.Queue fan-out and keepalive
- `backend/app/lint/router.py` - Added /stream SSE endpoint with auth and keepalive heartbeat
- `backend/app/lint/service.py` - Added get_results_for_object() for per-object structured queries
- `backend/app/validation/queue.py` - Added trigger_source field to ValidationJob
- `backend/app/main.py` - Created LintBroadcast, wired SSE publish, removed validation_router
- `backend/app/dependencies.py` - Added get_lint_broadcast dependency
- `backend/app/browser/router.py` - Migrated get_lint() from raw SPARQL to LintService
- `backend/app/templates/browser/lint_panel.html` - Replaced hx-trigger polling with EventSource SSE
- `frontend/nginx.conf` - Added /api/lint/stream SSE proxy location block
- `e2e/tests/04-validation/lint-panel.spec.ts` - Updated to verify SSE behavior instead of polling

## Decisions Made
- Used StreamingResponse with text/event-stream media type instead of EventSourceResponse from fastapi.sse (sse-starlette not installed, matches existing LLM streaming pattern)
- Single global SSE stream (/api/lint/stream) -- both per-object lint panel and future global dashboard subscribe to the same stream
- 30s keepalive timeout with comment heartbeat to prevent nginx/proxy from closing idle connections
- EventSource auto-reconnect is handled by browser built-in behavior, no manual reconnect logic needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used StreamingResponse instead of fastapi.sse.EventSourceResponse**
- **Found during:** Task 1 (SSE broadcast manager)
- **Issue:** Plan specified `from fastapi.sse import EventSourceResponse, ServerSentEvent` but fastapi.sse module does not exist (requires sse-starlette package which is not installed)
- **Fix:** Used `fastapi.responses.StreamingResponse` with `media_type="text/event-stream"`, matching the existing LLM streaming pattern in the codebase
- **Files modified:** backend/app/lint/broadcast.py, backend/app/lint/router.py
- **Verification:** Import succeeds, SSE stream works correctly
- **Committed in:** d6cb8c0 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential adaptation -- same SSE behavior achieved using available libraries. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SSE infrastructure ready for Phase 38 global lint dashboard UI
- Dashboard can subscribe to same /api/lint/stream endpoint
- All lint data flows through structured result triples (single source of truth)

---
*Phase: 37-global-lint-data-model-api*
*Completed: 2026-03-05*
