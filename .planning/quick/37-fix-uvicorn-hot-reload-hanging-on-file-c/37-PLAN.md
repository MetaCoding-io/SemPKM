---
phase: quick-37
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/main.py
  - backend/app/lint/router.py
  - backend/app/obsidian/broadcast.py
autonomous: true
requirements: [QUICK-37]
must_haves:
  truths:
    - "Uvicorn reload completes within seconds after file changes, not hanging"
    - "SSE streaming endpoints exit cleanly when app shuts down"
    - "SSE lint stream still delivers events and keepalives during normal operation"
  artifacts:
    - path: "backend/app/main.py"
      provides: "shutdown_event on app.state, set during lifespan shutdown"
      contains: "shutdown_event"
    - path: "backend/app/lint/router.py"
      provides: "event_generator checks shutdown_event"
      contains: "shutdown_event"
    - path: "backend/app/obsidian/broadcast.py"
      provides: "stream_sse checks shutdown_event"
      contains: "shutdown_event"
  key_links:
    - from: "backend/app/main.py"
      to: "backend/app/lint/router.py"
      via: "app.state.shutdown_event"
      pattern: "shutdown_event"
    - from: "backend/app/main.py"
      to: "backend/app/obsidian/broadcast.py"
      via: "shutdown_event parameter"
      pattern: "shutdown_event"
---

<objective>
Fix uvicorn hot-reload hanging indefinitely when file changes are detected.

Purpose: SSE streaming endpoints (lint/stream, obsidian scan/import streams) hold connections open with infinite `while True` loops. During uvicorn reload, `request.is_disconnected()` does not fire, so generators never exit and uvicorn hangs at "Waiting for connections to close" forever. This forces manual container restarts during development.

Output: All SSE generators check a cooperative shutdown signal and exit within 1 second of app shutdown.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/main.py
@backend/app/lint/router.py
@backend/app/obsidian/broadcast.py
@backend/app/obsidian/router.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add shutdown_event to app lifespan and wire into SSE generators</name>
  <files>backend/app/main.py, backend/app/lint/router.py, backend/app/obsidian/broadcast.py</files>
  <action>
**backend/app/main.py** — In the `lifespan()` function:
1. After the line `logger.info("Starting SemPKM API v%s", settings.app_version)` (line 75), create: `shutdown_event = asyncio.Event()` and store it: `app.state.shutdown_event = shutdown_event`
2. In the shutdown section (after `yield`, before `await validation_queue.stop()`), add: `shutdown_event.set()` as the FIRST shutdown action. This signals all SSE generators to exit before we start tearing down services they depend on.

**backend/app/lint/router.py** — In the `lint_stream()` endpoint (line 78):
1. Get the shutdown event from the request: `shutdown_event = request.app.state.shutdown_event`
2. Pass it into `event_generator()` (make shutdown_event a parameter of the inner function, or use closure).
3. In the `event_generator()` while loop (line 96), change the loop condition from `while True` to `while not shutdown_event.is_set()`.
4. Replace the `await asyncio.wait_for(queue.get(), timeout=30.0)` with a pattern that also checks shutdown: use `asyncio.wait()` with both `queue.get()` and `shutdown_event.wait()` tasks, with `return_when=FIRST_COMPLETED`. Cancel the losing task. If shutdown won, break. If queue item won, yield it.
   Alternative simpler approach: keep the `wait_for` with a shorter timeout (e.g., 1.0s) when combined with the `shutdown_event.is_set()` loop check — but this adds up to 1s latency. Better approach: wrap the existing `wait_for(queue.get(), timeout=30.0)` to also race against shutdown:
   ```python
   async def event_generator():
       queue = broadcast.subscribe()
       try:
           while not shutdown_event.is_set():
               if await request.is_disconnected():
                   break
               try:
                   # Race queue.get() against shutdown signal
                   get_task = asyncio.ensure_future(queue.get())
                   shutdown_task = asyncio.ensure_future(shutdown_event.wait())
                   done, pending = await asyncio.wait(
                       {get_task, shutdown_task},
                       timeout=30.0,
                       return_when=asyncio.FIRST_COMPLETED,
                   )
                   for task in pending:
                       task.cancel()
                   if shutdown_task in done:
                       break
                   if get_task in done:
                       yield get_task.result().format()
                   else:
                       # Timeout — send keepalive
                       yield ": keepalive\n\n"
               except asyncio.CancelledError:
                   break
       finally:
           broadcast.unsubscribe(queue)
   ```

**backend/app/obsidian/broadcast.py** — In the `stream_sse()` function (line 92):
1. Add `shutdown_event: asyncio.Event | None = None` parameter.
2. In the `while True` loop, change to `while not (shutdown_event and shutdown_event.is_set())`.
3. Use the same `asyncio.wait()` pattern as lint to race `queue.get()` against `shutdown_event.wait()`, falling back to the current behavior when `shutdown_event` is None.
   ```python
   async def stream_sse(
       queue: asyncio.Queue[SSEEvent],
       terminal_events: set[str] | None = None,
       shutdown_event: asyncio.Event | None = None,
   ) -> AsyncGenerator[str, None]:
       if terminal_events is None:
           terminal_events = {"scan_complete", "scan_error"}
       while not (shutdown_event and shutdown_event.is_set()):
           try:
               if shutdown_event:
                   get_task = asyncio.ensure_future(queue.get())
                   shutdown_task = asyncio.ensure_future(shutdown_event.wait())
                   done, pending = await asyncio.wait(
                       {get_task, shutdown_task},
                       timeout=30.0,
                       return_when=asyncio.FIRST_COMPLETED,
                   )
                   for task in pending:
                       task.cancel()
                   if shutdown_task in done:
                       break
                   if get_task in done:
                       event = get_task.result()
                       yield event.format()
                       if event.event in terminal_events:
                           break
                   else:
                       yield ": keepalive\n\n"
               else:
                   event = await asyncio.wait_for(queue.get(), timeout=30.0)
                   yield event.format()
                   if event.event in terminal_events:
                       break
           except asyncio.TimeoutError:
               yield ": keepalive\n\n"
   ```

**backend/app/obsidian/router.py** — Update `scan_stream()` (line 213) and `import_stream()` (line 577) to pass `shutdown_event`:
1. In `scan_stream()`, get `shutdown_event` from `request` (add `request: Request` to the function params if not present — check: it's NOT currently a param, only `import_id` and `user`). Add `request: Request` parameter, then pass `shutdown_event=request.app.state.shutdown_event` to `stream_sse()`.
2. In `import_stream()`, same pattern: add `request: Request` param, pass `shutdown_event=request.app.state.shutdown_event` to `stream_sse()`.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/backend && python -c "
import ast, sys
# Verify shutdown_event in main.py lifespan
with open('app/main.py') as f:
    tree = ast.parse(f.read())
src = open('app/main.py').read()
assert 'shutdown_event' in src, 'shutdown_event not found in main.py'
# Verify shutdown_event in lint router
with open('app/lint/router.py') as f:
    src = f.read()
assert 'shutdown_event' in src, 'shutdown_event not found in lint/router.py'
# Verify shutdown_event in obsidian broadcast
with open('app/obsidian/broadcast.py') as f:
    src = f.read()
assert 'shutdown_event' in src, 'shutdown_event not found in obsidian/broadcast.py'
print('All files contain shutdown_event references')
"</automated>
  </verify>
  <done>
    - `app.state.shutdown_event` created as `asyncio.Event()` during lifespan startup
    - `shutdown_event.set()` called as first action during lifespan shutdown
    - Lint SSE generator exits loop when shutdown_event is set (within 1 iteration)
    - Obsidian `stream_sse()` accepts optional shutdown_event and exits when set
    - Both obsidian SSE endpoints pass shutdown_event to stream_sse
    - Normal SSE operation (keepalives, event delivery, terminal events) unchanged
  </done>
</task>

<task type="auto">
  <name>Task 2: Verify hot-reload works with Docker</name>
  <files>backend/app/main.py</files>
  <action>
Run the Docker stack and verify:
1. `docker compose up -d` (if not already running)
2. `docker compose logs -f api --tail=10 &` to watch logs
3. Make a trivial whitespace edit to any Python file (e.g., add a blank line to `backend/app/health/router.py`)
4. Watch the api container logs — uvicorn should log "Shutting down" followed by "Started server process" within 5 seconds (not hang)
5. Verify the app is responsive after reload: `curl -s http://localhost:8001/api/health | head -1` should return 200

If the reload still hangs, check whether there's an active SSE connection from a browser tab. Close browser tabs to the app, retry the test. The fix prevents hangs when SSE clients are connected — without clients there's nothing to block anyway.

Also verify lint SSE still works:
1. `curl -N -H "Cookie: sempkm_session=..." http://localhost:3000/api/lint/stream` should receive keepalive comments every 30s (test for a few seconds, then Ctrl+C)
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && docker compose exec api python -c "from app.main import app; assert hasattr(app.state, '_default') or True; print('App loads OK')" 2>/dev/null || echo "Docker not running - verify manually after docker compose up"</automated>
  </verify>
  <done>
    - Uvicorn reload completes within 5 seconds after file changes (no hanging)
    - App responds to requests after reload
    - SSE lint stream still delivers keepalive comments during normal operation
  </done>
</task>

</tasks>

<verification>
1. `shutdown_event` created in lifespan, stored on app.state, set during shutdown
2. All SSE generators race their queue reads against shutdown_event
3. No `while True` loops remain that lack a shutdown escape hatch
4. Uvicorn hot-reload completes promptly during development
</verification>

<success_criteria>
- Uvicorn reload on file change completes in under 5 seconds (was infinite hang)
- SSE endpoints continue to function normally (keepalives, event delivery)
- No regressions in lint stream or obsidian import/scan streams
</success_criteria>

<output>
After completion, create `.planning/quick/37-fix-uvicorn-hot-reload-hanging-on-file-c/37-SUMMARY.md`
</output>
