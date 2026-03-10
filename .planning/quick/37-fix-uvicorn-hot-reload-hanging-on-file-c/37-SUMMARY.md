---
phase: quick-37
plan: 01
subsystem: api
tags: [uvicorn, sse, asyncio, hot-reload, signal-handling]

# Dependency graph
requires: []
provides:
  - "Cooperative shutdown signal (app.state.shutdown_event) for SSE generators"
  - "Signal-handler-based shutdown so event fires before uvicorn waits for connections"
affects: [lint-stream, obsidian-import, obsidian-scan]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Signal-chained shutdown event for SSE generator cleanup"]

key-files:
  created: []
  modified:
    - backend/app/main.py
    - backend/app/lint/router.py
    - backend/app/obsidian/broadcast.py
    - backend/app/obsidian/router.py

key-decisions:
  - "Signal handler (SIGTERM/SIGINT) sets shutdown_event before uvicorn waits for connections, avoiding lifespan deadlock"
  - "asyncio.wait() races queue.get() against shutdown_event.wait() for sub-second generator exit"
  - "Chained signal handlers preserve uvicorn's own shutdown behavior"

patterns-established:
  - "SSE shutdown pattern: race asyncio.wait({get_task, shutdown_task}) with return_when=FIRST_COMPLETED"
  - "Signal chaining: capture prev handler, call it after custom logic"

requirements-completed: [QUICK-37]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Quick Task 37: Fix Uvicorn Hot-Reload Hanging Summary

**Cooperative shutdown signal via SIGTERM/SIGINT handler breaks SSE generator deadlock during uvicorn reload**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T05:34:04Z
- **Completed:** 2026-03-10T05:39:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- SSE generators (lint stream, obsidian scan/import streams) now exit within 1 iteration when app shuts down
- Uvicorn hot-reload completes in seconds instead of hanging indefinitely
- Normal SSE operation (keepalives, event delivery, terminal events) unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Add shutdown_event to app lifespan and wire into SSE generators** - `4e3805e` (fix)
2. **Task 2: Verify hot-reload works with Docker + fix signal handler approach** - `e6b33bd` (fix)

## Files Created/Modified
- `backend/app/main.py` - Added asyncio.Event shutdown signal, SIGTERM/SIGINT handler that sets it before uvicorn waits for connections
- `backend/app/lint/router.py` - Lint SSE generator races queue.get() against shutdown_event via asyncio.wait()
- `backend/app/obsidian/broadcast.py` - stream_sse() accepts optional shutdown_event parameter, races queue.get() against it
- `backend/app/obsidian/router.py` - scan_stream() and import_stream() pass request.app.state.shutdown_event to stream_sse()

## Decisions Made
- **Signal handler over lifespan-only approach:** Uvicorn waits for all connections to close BEFORE calling lifespan shutdown. Setting shutdown_event only in lifespan creates a deadlock (generators wait for event, uvicorn waits for generators). Signal handlers fire immediately on SIGTERM/SIGINT, before uvicorn starts waiting.
- **Chained signal handlers:** Previous signal handlers (uvicorn's own) are captured and called after setting the event, so uvicorn's shutdown sequence still proceeds normally.
- **asyncio.wait() over shorter timeouts:** Using asyncio.wait() with FIRST_COMPLETED provides sub-second exit rather than polling with short timeouts (which would add latency to normal keepalive behavior).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lifespan shutdown_event.set() deadlocks with uvicorn**
- **Found during:** Task 2 (Docker verification)
- **Issue:** Plan specified setting shutdown_event after `yield` in lifespan, but uvicorn's shutdown sequence waits for all response generators to finish BEFORE calling lifespan __aexit__. This creates a deadlock: generators wait for the event, uvicorn waits for generators.
- **Fix:** Install SIGTERM/SIGINT signal handlers during startup that set shutdown_event immediately when the signal arrives (before uvicorn starts waiting for connections). Chain to previous handlers so uvicorn still receives the signal.
- **Files modified:** backend/app/main.py
- **Verification:** Two consecutive hot-reloads with active SSE connections both completed in seconds
- **Committed in:** e6b33bd

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- without it the entire feature would not work. No scope creep.

## Issues Encountered
- Pre-existing `task_done() called too many times` error in validation queue during shutdown -- out of scope, does not affect reload completion. Logged to deferred items.

## Next Phase Readiness
- Hot-reload works reliably with active SSE connections
- No blockers

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both commits (4e3805e, e6b33bd) found in git log
- All 4 files contain shutdown_event references

---
*Quick Task: 37*
*Completed: 2026-03-10*
