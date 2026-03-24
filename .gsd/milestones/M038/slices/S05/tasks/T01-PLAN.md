---
estimated_steps: 5
estimated_files: 2
skills_used:
  - test
---

# T01: Context subscription service with SSE client, debounce, and reconnect

**Slice:** S05 — Context-Driven Adaptation + Mobile
**Milestone:** M038

## Description

Create `context_service.py` — the SSE subscription client that connects to the platform's context stream and triggers plan re-generation on context changes. This is the first app to maintain a persistent SSE subscription from inside the App SDK. The service handles SSE text-protocol parsing, debounced re-evaluation (2 minutes default, immediate for location_zone changes per D349), exponential-backoff reconnection, and concurrent-generation protection via `asyncio.Lock`.

The platform SSE endpoint is `GET /api/context/stream` and emits events in format:
```
event: context_update
data: {"location_zone": "office", "activity": "working", ...}

```
(blank line terminates each event)

The platform client is obtained via `ctx._get_platform_client()` which returns an `httpx.AsyncClient` with `base_url` set to the platform URL and auth headers pre-configured.

## Steps

1. **Create `apps/media-scheduler/services/context_service.py`** with module-level state variables:
   - `_listener_task: asyncio.Task | None` — the background SSE listener
   - `_debounce_task: asyncio.Task | None` — current debounce timer
   - `_last_context: dict` — most recent context from SSE
   - `_plan_lock: asyncio.Lock` — prevents concurrent `generate_plan()` calls
   - `_reconnect_count: int` — reconnection counter
   - `_last_event_at: str | None` — ISO timestamp of last SSE event
   - `_connected: bool` — SSE connection status flag

2. **Implement SSE parsing and event dispatch:**
   - `parse_sse_lines(lines: list[str]) -> tuple[str | None, dict | None]` — extracts `event` and `data` from SSE text lines. Returns `(event_type, parsed_data_dict)` or `(None, None)` if incomplete.
   - `_on_context_event(ctx, context_data: dict)` — async handler: stores `_last_context`, checks if `location_zone` changed (compare with previous context), if yes call `_trigger_regeneration(ctx)` immediately, otherwise start/restart debounce timer.
   - `_debounce_regenerate(ctx)` — async: `await asyncio.sleep(120)`, then `_trigger_regeneration(ctx)`.
   - `_trigger_regeneration(ctx)` — async: acquires `_plan_lock`, calls `generate_plan(ctx, context_override=_last_context)`, logs result summary.

3. **Implement SSE listener with reconnect:**
   - `_listen_sse(ctx)` — async loop: gets `httpx.AsyncClient` from `ctx._get_platform_client()`, opens `client.stream("GET", "/api/context/stream")`, reads lines, parses SSE events, dispatches to `_on_context_event`. On connection error: log, increment `_reconnect_count`, sleep with exponential backoff (`min(2 ** _reconnect_count, 300)` seconds), retry. Reset `_reconnect_count` on successful connection.

4. **Implement lifecycle management:**
   - `start_context_listener(ctx) -> asyncio.Task` — creates `_plan_lock` if needed, spawns `_listen_sse(ctx)` as `asyncio.create_task`, stores in `_listener_task`, returns it.
   - `stop_context_listener()` — cancels `_listener_task` and `_debounce_task` if they exist, resets state.
   - `get_context_subscription_status() -> dict` — returns `{connected, last_event_at, debounce_pending, reconnect_count}`.

5. **Add ~45 tests to `backend/tests/test_media_scheduler.py`** covering:
   - SSE line parsing: single event, multi-line data, missing event/data, non-JSON data, empty lines (~6 tests)
   - Debounce logic: fires after timeout, cancels on new event, restarts timer, immediate for location_zone change (~10 tests)
   - Reconnect: backoff calculation, counter reset on success, max backoff cap (~5 tests)
   - Plan trigger: acquires lock, calls generate_plan with context_override, logs result (~6 tests)
   - Listener lifecycle: start creates task, stop cancels task, status reports correctly (~6 tests)
   - Concurrent generation: lock prevents overlapping calls (~3 tests)
   - Error handling: SSE parse error logged not raised, connection error triggers reconnect, generate_plan error caught (~5 tests)
   - Edge cases: empty context, location_zone None→value, value→same value (~4 tests)

   Use standard `unittest.mock.AsyncMock` for `ctx`, `ctx._get_platform_client()`, and `generate_plan`. Use `asyncio.wait_for` with short timeouts in tests to avoid hangs.

   **Import pattern:** Follow the existing `importlib` fallback pattern in test file. The context_service must use the same `try/except ModuleNotFoundError` + importlib fallback for importing `generate_plan` from `plan_service`.

## Must-Haves

- [ ] `parse_sse_lines()` correctly extracts event type and JSON data from SSE text
- [ ] Debounce timer fires after 120 seconds of no new events
- [ ] Location zone changes trigger immediate regeneration (not debounced)
- [ ] Reconnect with exponential backoff on SSE connection loss (max 300s)
- [ ] `asyncio.Lock` prevents concurrent `generate_plan()` calls
- [ ] `start_context_listener()` spawns background task, `stop_context_listener()` cancels it
- [ ] `get_context_subscription_status()` reports connection state
- [ ] 45+ new tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "context" -v` — all context tests pass
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/context_service.py').read())"` — clean
- `grep -c "def test_" backend/tests/test_media_scheduler.py` — total ≥ 366 (321 existing + 45 new)

## Observability Impact

- Signals added: `context_service` logger with events for SSE connect, disconnect, reconnect (with count), debounce fire/cancel, plan generation trigger + result, lock contention warning
- How a future agent inspects this: call `get_context_subscription_status()` to see `{connected, last_event_at, debounce_pending, reconnect_count}`
- Failure state exposed: `_reconnect_count` > 0 signals connection problems; `last_event_at` going stale signals SSE stream died

## Inputs

- `apps/media-scheduler/services/plan_service.py` — `generate_plan(ctx, context_override=...)` function signature and import pattern
- `apps/media-scheduler/services/rules_service.py` — `evaluate_rules(rules, context)` for understanding context dict shape
- `backend/app/context/router.py` — SSE event format (`event: context_update\ndata: {json}\n\n`)
- `backend/app/lint/broadcast.py` — `SSEEvent.format()` for reference wire format
- `backend/sdk/sempkm_app_sdk/context.py` — `_get_platform_client()` returns `httpx.AsyncClient` with base_url + auth
- `backend/tests/test_media_scheduler.py` — existing test file to append to (321 tests, ~3633 lines)

## Expected Output

- `apps/media-scheduler/services/context_service.py` — new file (~200 lines) with SSE client, debounce, reconnect, lifecycle management
- `backend/tests/test_media_scheduler.py` — ~45 new test functions appended
