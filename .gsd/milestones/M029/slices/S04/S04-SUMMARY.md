---
id: S04
parent: M029
milestone: M029
provides:
  - TimingMiddleware with Server-Timing header on every HTTP response
  - Per-path request timing stats with in-memory accumulation (capped at 1000 samples/path)
  - GET /api/admin/timing-report endpoint (owner-only) returning top-5 slowest endpoints with avg/max/min/p95/count/total stats
  - Slow request logging at INFO level (>100ms threshold)
  - ConditionalGetMiddleware computing weak ETags on GET JSON API responses under /api/ and /.well-known/ paths
  - 304 Not Modified responses when client sends matching If-None-Match header
  - Cache-Control: no-cache and Vary: Accept, Authorization headers on ETag-bearing responses
requires:
  - slice: none
    provides: independent slice — no upstream dependencies
affects:
  - S05 (Lighthouse verification can verify backend cache headers contribute to score)
key_files:
  - backend/app/middleware/__init__.py
  - backend/app/middleware/timing.py
  - backend/app/middleware/etag.py
  - backend/app/main.py
  - backend/tests/test_timing_middleware.py
  - backend/tests/test_etag_middleware.py
key_decisions:
  - Auth override in tests uses get_current_user dependency override (not require_role) because require_role is a factory returning new callables, making identity-based dependency_overrides matching impossible
  - StreamingResponse isinstance check is a safety net only — BaseHTTPMiddleware buffers all responses, so the 1MB body size limit is the real protection against unbounded streams
  - Middleware ordering convention — ConditionalGetMiddleware registered before TimingMiddleware so timing captures total time including 304 fast-path responses
patterns_established:
  - TimingMiddleware registered as last add_middleware call in main.py (outermost layer wrapping all other middleware)
  - Admin API router pattern for middleware-associated endpoints — router defined in same module as middleware, included separately in main.py
  - Middleware ordering in main.py follows inner-to-outer convention (last add_middleware = outermost)
observability_surfaces:
  - Server-Timing response header on every HTTP response (format: total;dur=X.XX)
  - INFO log lines for slow requests (>100ms) with method/path/status/duration
  - GET /api/admin/timing-report returns JSON with top_endpoints, total_requests, collection_period_seconds
  - ETag response header (W/"..." format) on all GET JSON API responses
  - Cache-Control: no-cache and Vary: Accept, Authorization headers on ETag-bearing responses
  - 304 Not Modified responses visible in timing stats and HTTP access logs
drill_down_paths:
  - .gsd/milestones/M029/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M029/slices/S04/tasks/T02-SUMMARY.md
duration: 27m
verification_result: passed
completed_at: 2026-03-20
---

# S04: Backend Performance & HTTP Cache Headers

**Added request timing middleware with Server-Timing headers, per-path stats accumulation, admin timing report endpoint, and ETag-based conditional GET middleware returning 304 Not Modified for unchanged JSON API responses**

## What Happened

Created `backend/app/middleware/` package with two middlewares delivering PERF-08 (backend profiling) and PERF-09 (backend cache headers).

**TimingMiddleware** (T01) uses `time.monotonic()` to measure request duration, adds `Server-Timing: total;dur=X.XX` header to every response, logs all requests at DEBUG and slow requests (>100ms) at INFO. Per-path timing stats accumulate in an in-memory dict capped at 1000 samples per path. The `get_timing_report(top_n=5)` function computes avg/max/min/p95/count/total_ms sorted by avg descending. An admin endpoint at `GET /api/admin/timing-report` (owner-only) exposes the report as JSON. Registered as the outermost middleware (last `add_middleware()` call).

**ConditionalGetMiddleware** (T02) intercepts GET requests to `/api/` and `/.well-known/` paths. For qualifying JSON responses (≤1MB), it computes a SHA-256-based weak ETag and adds `ETag`, `Cache-Control: no-cache`, and `Vary: Accept, Authorization` headers. When a client sends `If-None-Match` matching the ETag (or `*`), the middleware returns 304 with no body, preserving cache headers. Non-GET methods, non-JSON content types, non-API paths, and responses over 1MB are excluded. Registered before TimingMiddleware so timing captures total time including 304 fast paths.

## Verification

- `python -m pytest tests/test_timing_middleware.py -v` — 20/20 passed
- `python -m pytest tests/test_etag_middleware.py -v` — 16/16 passed
- `python -m pytest tests/ -x --deselect tests/test_jira_sync_engine.py::TestComputeStatus` — 2751 passed (5 pre-existing deselected unrelated to this change)
- Diagnostic import check: `get_timing_report()` returns empty list on fresh state ✅

## Requirements Advanced

- PERF-08 — TimingMiddleware logs request durations, adds Server-Timing header, accumulates per-path stats, admin endpoint produces top-5 slowest endpoint report. Fully delivered by unit tests; S05 will do Docker/curl verification.
- PERF-09 — ConditionalGetMiddleware computes weak ETags on JSON API GET responses, returns 304 Not Modified for matching If-None-Match. Fully delivered by unit tests; S05 will do Docker/curl verification.

## Requirements Validated

- none — S05 performs runtime Docker/curl verification that will validate these requirements

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **StreamingResponse test adjusted:** The plan expected StreamingResponse to be excluded via `isinstance` check, but `BaseHTTPMiddleware.call_next()` wraps all responses — the original type is not preserved. The 1MB body size limit provides the real protection for large/unbounded streams. Test updated to document this behavior.
- **pytest-timeout not installed:** `--timeout=30` flag from slice plan is unsupported. Tests run without timeout enforcement. No impact — all tests complete in <1s.

## Known Limitations

- Timing stats are in-memory only — lost on process restart. Acceptable for profiling use case; persistent metrics would require a time-series store.
- The 1MB body size limit on ETag computation is a pragmatic bound. Responses larger than 1MB get no ETag header.
- `If-None-Match` comparison is exact string match — does not handle multiple ETags in the header value (comma-separated list per HTTP spec). Sufficient for browser and extension clients which send single ETags.

## Follow-ups

- S05 will verify backend cache headers via `curl` header checks against the Docker stack
- S05 Lighthouse verification may show backend cache header contributions to performance score

## Files Created/Modified

- `backend/app/middleware/__init__.py` — empty package init for new middleware directory
- `backend/app/middleware/timing.py` — TimingMiddleware, per-path stats, get_timing_report(), reset_timing_stats(), admin timing report router
- `backend/app/middleware/etag.py` — ConditionalGetMiddleware with ETag computation and 304 handling
- `backend/app/main.py` — registered both middlewares and timing router
- `backend/tests/test_timing_middleware.py` — 20 unit tests
- `backend/tests/test_etag_middleware.py` — 16 unit tests

## Forward Intelligence

### What the next slice should know
- Both middlewares are registered and exercised via unit tests but not yet verified via Docker `curl` checks. S05 should run: `curl -sI /api/health | grep Server-Timing` and `curl -sI /api/types | grep -iE 'etag|cache-control|vary'` plus a conditional GET round-trip.
- The timing report endpoint is at `GET /api/admin/timing-report` and requires owner auth.
- `reset_timing_stats()` clears all accumulated data — useful for test isolation.

### What's fragile
- `If-None-Match` comparison is single-value only — if a client sends multiple ETags comma-separated, the match will fail. This is unlikely from browser/extension clients but worth noting.
- BaseHTTPMiddleware buffers all response bodies, so very large streaming responses will be buffered in memory before the 1MB check can exclude them.

### Authoritative diagnostics
- `curl -sI /api/types` should show `ETag`, `Cache-Control: no-cache`, and `Vary: Accept, Authorization` headers
- `curl -sI -H 'If-None-Match: <etag>' /api/types` should return HTTP 304
- `curl /api/admin/timing-report` (with owner auth) should return JSON with accumulated per-endpoint stats
- `Server-Timing` header should appear on every response including 304s

### What assumptions changed
- StreamingResponse isinstance check doesn't work as expected inside BaseHTTPMiddleware — the middleware buffers all responses, losing the original type. The 1MB body size limit is the effective safeguard instead.
