---
id: T01
parent: S05
milestone: M038
provides:
  - context_service.py — SSE subscription client with debounce, reconnect, lifecycle management
  - 45 new tests for context subscription service
key_files:
  - apps/media-scheduler/services/context_service.py
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Module-level state pattern (consistent with plan_service, rules_service) over class-based service
  - _prev_context tracking for location_zone diff detection without external state store
patterns_established:
  - SSE client pattern for App SDK apps: _get_platform_client() + client.stream() + aiter_lines() + parse_sse_lines()
  - Debounce-with-immediate-override pattern: asyncio.create_task for debounce, cancel+direct-call for immediate triggers
observability_surfaces:
  - context_service logger: SSE connect/disconnect/reconnect with count, debounce fire/cancel, plan generation trigger + result, lock contention warning
  - get_context_subscription_status() returns {connected, last_event_at, debounce_pending, reconnect_count}
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Context subscription service with SSE client, debounce, and reconnect

**Created context_service.py with SSE client, 120s debounce (immediate for location_zone changes), exponential-backoff reconnect, and asyncio.Lock plan generation protection — 45 new tests all passing (366 total).**

## What Happened

Built `apps/media-scheduler/services/context_service.py` (~260 lines) implementing the full SSE subscription lifecycle:

1. **SSE parsing** — `parse_sse_lines()` extracts event type and JSON data from SSE wire format, handling multi-line data, comments, and malformed JSON gracefully.

2. **Debounce logic** — Non-location context changes start/restart a 120s debounce timer via `asyncio.create_task`. Location zone changes cancel any pending debounce and trigger immediate plan regeneration (per D349).

3. **Reconnect** — `_listen_sse()` runs an infinite loop with exponential backoff on connection errors (`min(2^count, 300)` seconds). Counter resets on successful connection.

4. **Concurrency protection** — `_trigger_regeneration()` acquires `_plan_lock` (asyncio.Lock) before calling `generate_plan(ctx, context_override=_last_context)`. Lock contention is logged as a warning.

5. **Lifecycle** — `start_context_listener(ctx)` spawns the background task; `stop_context_listener()` cancels listener + debounce and resets all state; `get_context_subscription_status()` returns inspection dict.

Added 45 tests across 7 test classes covering SSE parsing, debounce timing, reconnect backoff, plan trigger mechanics, lifecycle management, concurrent generation serialization, and error handling edge cases.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — **366 passed** in 1.18s
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "TestParseSSELines or TestDebounceLogic or TestReconnectLogic or TestPlanTrigger or TestListenerLifecycle or TestConcurrentGeneration or TestContextErrorHandling" -v` — **45 passed** in 1.06s
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/context_service.py').read())"` — clean parse
- `grep -c "def test_" backend/tests/test_media_scheduler.py` — returns 366 (≥ 366 required)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass | 1.18s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/context_service.py').read())"` | 0 | ✅ pass | <0.1s |
| 3 | `grep -c "def test_" backend/tests/test_media_scheduler.py` → 366 | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Runtime inspection:** Call `get_context_subscription_status()` → `{connected: bool, last_event_at: str|None, debounce_pending: bool, reconnect_count: int}`
- **Log grep:** `context_service.sse_connected`, `context_service.sse_connection_error`, `context_service.debounce_fired`, `context_service.plan_generation_completed`, `context_service.plan_lock_contention`
- **Failure indicator:** `reconnect_count > 0` signals SSE connection problems; `last_event_at` going stale (>5 min old) signals the stream died without error

## Deviations

- Added `_prev_context` module-level variable (not in plan) to enable clean location_zone diff detection without re-reading the old `_last_context` after overwrite.
- Used `asyncio.sleep(0)` in two tests to let task cancellation propagate — Python 3.14's asyncio doesn't process CancelledError within the same tick as `task.cancel()`.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/context_service.py` — New file (~260 lines): SSE client, debounce, reconnect, lifecycle management, inspection surface
- `backend/tests/test_media_scheduler.py` — Appended 45 test functions across 7 test classes; added `import asyncio` to imports
