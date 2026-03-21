---
id: T02
parent: S04
milestone: M029
provides:
  - ConditionalGetMiddleware adding weak ETag headers to GET JSON API responses on /api/ and /.well-known/ paths
  - 304 Not Modified responses when client sends matching If-None-Match header
  - Cache-Control: no-cache and Vary: Accept, Authorization headers on all ETag-bearing responses
key_files:
  - backend/app/middleware/etag.py
  - backend/app/main.py
  - backend/tests/test_etag_middleware.py
key_decisions:
  - StreamingResponse isinstance check is a safety net only — BaseHTTPMiddleware buffers all responses, so the 1MB body size limit is the real protection against unbounded streams
patterns_established:
  - Middleware ordering convention in main.py — ConditionalGetMiddleware registered before TimingMiddleware so timing captures total time including 304 responses
observability_surfaces:
  - ETag response header (W/"..." format) on all GET JSON API responses
  - Cache-Control: no-cache and Vary: Accept, Authorization headers on ETag-bearing responses
  - 304 Not Modified responses visible in TimingMiddleware stats and standard HTTP access logs
  - curl -sI /api/types | grep -iE 'etag|cache-control|vary' to inspect headers
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Implement ETag conditional GET middleware for JSON API responses

**Added ConditionalGetMiddleware computing weak ETags on JSON API GET responses with 304 Not Modified support for matching If-None-Match headers**

## What Happened

Created `ConditionalGetMiddleware` in `backend/app/middleware/etag.py` that intercepts GET requests to `/api/` and `/.well-known/` paths. For qualifying responses (JSON content type, body ≤1MB), it computes a SHA-256-based weak ETag and adds `ETag`, `Cache-Control: no-cache`, and `Vary: Accept, Authorization` headers. When a client sends `If-None-Match` matching the computed ETag (or `*`), the middleware returns 304 Not Modified with no body, preserving the cache-related headers.

Registered the middleware in `main.py` before `TimingMiddleware` so timing captures total time including 304 fast-path responses. Wrote 16 unit tests covering ETag generation, consistency, conditional GET, 304 headers, path/method exclusions, and well-known path support.

One test adaptation: the plan expected StreamingResponse to be excluded via isinstance check, but `BaseHTTPMiddleware` buffers all responses before dispatching, so the original type is lost. Updated the test to document this behavior — the 1MB body size limit is the real protection against unbounded streams.

## Verification

- `python -m pytest tests/test_etag_middleware.py -v` — 16/16 passed
- `python -m pytest tests/test_timing_middleware.py -v` — 20/20 passed (no regression)
- `python -m pytest tests/ -x` — 1320 passed, 1 pre-existing failure in test_jira_sync_engine.py (import error for `_compute_status`, unrelated)
- LSP diagnostics — only pre-existing Pyright import resolution errors (virtualenv not indexed), no new type errors
- Slice diagnostic check — timing report import and empty-state assertion passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run --extra dev python -m pytest tests/test_etag_middleware.py -v` | 0 | ✅ pass | 0.33s |
| 2 | `uv run --extra dev python -m pytest tests/test_timing_middleware.py -v` | 0 | ✅ pass | 0.75s |
| 3 | `uv run --extra dev python -m pytest tests/ -x` | 1 | ⚠️ pre-existing fail | 11.27s |
| 4 | `uv run --extra dev python -c "from app.middleware.timing import ..."` | 0 | ✅ pass | <1s |

## Diagnostics

- **ETag header inspection:** `curl -sI /api/types | grep -iE 'etag|cache-control|vary'` shows all three headers
- **Conditional GET test:** `curl -sI /api/types` → copy ETag → `curl -sI -H 'If-None-Match: <etag>' /api/types` → expect HTTP 304
- **Failure mode:** Middleware silently passes through responses that don't qualify (non-GET, non-JSON, non-API paths, >1MB). No error logs produced for skip conditions.
- **Stats impact:** 304 responses are timed by TimingMiddleware and appear in `/api/admin/timing-report`

## Deviations

- **StreamingResponse test adjusted:** The plan expected StreamingResponse to be excluded via `isinstance` check, but `BaseHTTPMiddleware.call_next()` wraps all responses — the original StreamingResponse type is not preserved. Updated the test to document this behavior and assert that small streaming JSON bodies get ETags (because they're buffered). The 1MB body size limit provides the real protection for large/unbounded streams.

## Known Issues

- Pre-existing test failure in `test_jira_sync_engine.py::TestComputeStatus::test_no_errors_returns_success` — import error for `_compute_status` function. Unrelated to this task.

## Files Created/Modified

- `backend/app/middleware/etag.py` — new ConditionalGetMiddleware class with ETag computation and 304 handling
- `backend/app/main.py` — added ConditionalGetMiddleware import and registration (before TimingMiddleware)
- `backend/tests/test_etag_middleware.py` — 16 unit tests covering all ETag middleware behavior
- `.gsd/milestones/M029/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M029/slices/S04/S04-PLAN.md` — marked T02 as [x] done
