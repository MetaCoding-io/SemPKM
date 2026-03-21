---
id: T01
parent: S04
milestone: M029
provides:
  - TimingMiddleware with Server-Timing header on every response
  - Per-path request timing stats with in-memory accumulation (capped at 1000 samples/path)
  - get_timing_report() function computing avg/max/min/p95/count/total per path
  - Admin endpoint GET /api/admin/timing-report (owner-only)
  - Slow request logging at INFO level (>100ms threshold)
key_files:
  - backend/app/middleware/__init__.py
  - backend/app/middleware/timing.py
  - backend/app/main.py
  - backend/tests/test_timing_middleware.py
key_decisions:
  - Auth override in tests uses get_current_user dependency override (not require_role) because require_role is a factory that returns a new callable each invocation, making identity-based dependency_overrides matching impossible
patterns_established:
  - TimingMiddleware registered as last add_middleware call in main.py (outermost layer)
  - Admin API router pattern for middleware-associated endpoints — router defined in same module as middleware, included separately in main.py
observability_surfaces:
  - Server-Timing response header on every HTTP response (format: total;dur=X.XX)
  - INFO log lines for slow requests (>100ms) with method/path/status/duration
  - GET /api/admin/timing-report returns JSON with top_endpoints, total_requests, collection_period_seconds
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Implement timing middleware with top-5 report endpoint

**Added TimingMiddleware with Server-Timing header, slow-request logging, per-path stats accumulation, and admin timing report endpoint**

## What Happened

Created `backend/app/middleware/` package with `TimingMiddleware` following the existing `BaseHTTPMiddleware` pattern from `PostHogErrorMiddleware`. The middleware uses `time.monotonic()` for duration measurement, adds `Server-Timing: total;dur=X.XX` header to every response, logs all requests at DEBUG level and slow requests (>100ms) at INFO level, and accumulates per-path timing stats in an in-memory dict capped at 1000 samples per path.

The `get_timing_report(top_n=5)` function computes avg/max/min/p95/count/total_ms per path, sorted by avg_ms descending. An admin endpoint at `GET /api/admin/timing-report` (owner-only via `require_role("owner")`) exposes the report as JSON with `top_endpoints`, `total_requests`, and `collection_period_seconds`.

The middleware is registered as the last `add_middleware()` call in `main.py`, making it the outermost layer that captures total request processing time. The timing router is included alongside the existing admin router.

## Verification

- All 20 timing middleware tests pass covering: Server-Timing header presence and format, stats accumulation, report structure and computation, p95 accuracy, avg/total correctness, stats reset, max samples cap, admin endpoint JSON schema, and slow request logging behavior
- Full backend test suite: 2751 passed, 5 deselected (pre-existing worktree path issue in jira sync engine tests unrelated to this change)
- Diagnostic import check confirms `get_timing_report()` returns empty list on fresh state
- LSP import errors are Pyright venv-resolution artifacts in the worktree — all imports resolve at runtime

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_timing_middleware.py -v` | 0 | ✅ pass | 0.8s |
| 2 | `python -m pytest tests/ -x --deselect tests/test_jira_sync_engine.py::TestComputeStatus` | 0 | ✅ pass | 12.2s |
| 3 | `python -c "from app.middleware.timing import get_timing_report, reset_timing_stats; ..."` | 0 | ✅ pass | <1s |

## Diagnostics

- **Server-Timing header:** `curl -sI /api/health | grep Server-Timing` shows `Server-Timing: total;dur=X.XX`
- **Slow request logs:** Check INFO-level logs for lines matching `Slow request: METHOD /path STATUS DURATIONms`
- **Timing report:** `curl /api/admin/timing-report` (with owner auth) returns JSON with accumulated per-endpoint stats
- **Test isolation:** Call `reset_timing_stats()` to clear all accumulated data
- **Stats inspection:** Import `_timing_stats` from `app.middleware.timing` for raw access to the per-path duration lists

## Deviations

None.

## Known Issues

- Pre-existing: `tests/test_jira_sync_engine.py::TestComputeStatus` (5 tests) fails in worktree due to `sync_engine` import path resolution picking up `apps/linear-sync/services/sync_engine.py` instead of the jira version. Passes on main checkout. Not caused by this change.
- `pytest-timeout` plugin not installed, so `--timeout=30` flag from slice plan is unsupported. Tests run without timeout enforcement.

## Files Created/Modified

- `backend/app/middleware/__init__.py` — empty package init for new middleware directory
- `backend/app/middleware/timing.py` — TimingMiddleware class, per-path stats accumulation, get_timing_report() function, reset_timing_stats(), and admin timing report router
- `backend/app/main.py` — added import for TimingMiddleware and timing_router, registered middleware as outermost layer, included timing router
- `backend/tests/test_timing_middleware.py` — 20 unit tests covering header, stats, report, cap, admin endpoint, and logging
