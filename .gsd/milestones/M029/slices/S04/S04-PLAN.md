# S04: Backend Performance & HTTP Cache Headers

**Goal:** Add request timing middleware that logs durations and produces a top-5 slowest endpoint report, plus ETag-based conditional GET on JSON API responses returning 304 Not Modified for unchanged resources.
**Demo:** `curl -sI /api/health` shows `Server-Timing` header with request duration. `curl -sI /api/types` returns an `ETag` header; a follow-up request with `If-None-Match: <etag>` returns `304 Not Modified`. Admin endpoint `/api/admin/timing-report` shows accumulated per-endpoint timing stats.

## Must-Haves

- `TimingMiddleware` logs request durations at DEBUG (all) and INFO (>100ms threshold), adds `Server-Timing` response header
- In-memory per-path timing stats accumulated for top-N analysis
- `GET /api/admin/timing-report` returns JSON with top-5 slowest endpoints (avg, max, count, p95)
- `ConditionalGetMiddleware` computes weak ETags on GET responses with `application/json` content type under `/api/` and `/.well-known/` paths
- `If-None-Match` header match returns 304 with correct headers preserved (ETag, Cache-Control, Vary)
- Non-API paths, non-GET methods, streaming responses, and non-JSON content types are excluded from ETag processing
- Both middlewares registered in `main.py` with correct ordering (timing outermost)
- Unit tests for both middlewares covering happy paths, edge cases, and exclusion rules

## Proof Level

- This slice proves: integration (middleware registered and exercised via unit tests with real Starlette test client)
- Real runtime required: no (unit tests sufficient; S05 does Docker/curl verification)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_timing_middleware.py -v` — all pass
- `cd backend && python -m pytest tests/test_etag_middleware.py -v` — all pass
- `cd backend && python -m pytest tests/ -x --timeout=30` — full suite still passes (no regressions)
- `cd backend && python -c "from app.middleware.timing import get_timing_report, reset_timing_stats; reset_timing_stats(); r = get_timing_report(); assert isinstance(r, list), f'Expected list, got {type(r)}'; print('timing report OK: empty list on fresh state')"` — diagnostic import and empty-state check

## Observability / Diagnostics

- Runtime signals: INFO-level log lines for slow requests (`method path status_code duration_ms`), `Server-Timing` response header on every request
- Inspection surfaces: `GET /api/admin/timing-report` returns JSON with per-endpoint timing stats (avg_ms, max_ms, count, p95_ms, total_ms)
- Failure visibility: Timing middleware logs exceptions via standard logger; ETag middleware skips gracefully on any hashing error
- Redaction constraints: none — no PII in timing data or ETags

## Integration Closure

- Upstream surfaces consumed: `backend/app/monitoring/middleware.py` (pattern reference), `backend/app/main.py` (middleware registration site)
- New wiring introduced in this slice: two `app.add_middleware()` calls in `main.py`, one new admin API route
- What remains before the milestone is truly usable end-to-end: S05 (Lighthouse verification, curl header checks, E2E test run, QUIC/HTTP3 decision)

## Tasks

- [x] **T01: Implement timing middleware with top-5 report endpoint** `est:1h`
  - Why: Delivers PERF-08 — request timing visibility and top-5 slowest endpoint identification. The timing middleware follows the exact `BaseHTTPMiddleware` pattern already used by `PostHogErrorMiddleware`.
  - Files: `backend/app/middleware/__init__.py`, `backend/app/middleware/timing.py`, `backend/app/main.py`, `backend/tests/test_timing_middleware.py`
  - Do: Create `backend/app/middleware/` package. Implement `TimingMiddleware` using `BaseHTTPMiddleware` with `time.monotonic()` for duration measurement. Log at DEBUG for all requests, INFO for requests exceeding 100ms threshold. Add `Server-Timing: total;dur=X.XX` response header. Accumulate per-path timing stats in an in-memory dict (path → list of durations, capped at 1000 per path). Create a `get_timing_report(top_n=5)` function that computes avg/max/p95/count/total per path. Add `GET /api/admin/timing-report` endpoint (owner-only) returning the report as JSON. Register middleware in `main.py` as outermost (added last). Write unit tests covering: request timing logged, Server-Timing header present, slow request threshold logging, stats accumulation, report computation, admin endpoint auth.
  - Verify: `cd backend && python -m pytest tests/test_timing_middleware.py -v`
  - Done when: All timing middleware tests pass, `Server-Timing` header appears on test responses, admin report endpoint returns valid JSON with timing stats.

- [x] **T02: Implement ETag conditional GET middleware for JSON API responses** `est:1h`
  - Why: Delivers PERF-09 — HTTP cache headers on API responses enabling 304 Not Modified for unchanged resources. Reduces bandwidth for repeat API calls from the browser extension and frontend.
  - Files: `backend/app/middleware/etag.py`, `backend/app/main.py`, `backend/tests/test_etag_middleware.py`
  - Do: Implement `ConditionalGetMiddleware` using `BaseHTTPMiddleware`. For GET requests to paths starting with `/api/` or `/.well-known/`: read response body, compute SHA-256 hash, create weak ETag (`W/"hash[:16]"`), add `ETag` and `Cache-Control: no-cache` headers. Check incoming `If-None-Match` header — if it matches, return 304 with ETag/Cache-Control/Vary headers preserved (no body). Skip: non-GET methods, non-JSON content types, streaming responses (`StreamingResponse`), response bodies over 1MB, paths outside `/api/` and `/.well-known/`. Handle `If-None-Match: *` per HTTP spec. Register in `main.py` before timing middleware (so timing wraps it). Write unit tests covering: ETag header generated on JSON API response, 304 on If-None-Match match, ETag changes when response body changes, non-API paths excluded, POST/PUT/DELETE excluded, streaming responses excluded, non-JSON content type excluded, large response excluded, `If-None-Match: *` handling, 304 preserves required headers.
  - Verify: `cd backend && python -m pytest tests/test_etag_middleware.py -v`
  - Done when: All ETag middleware tests pass, GET `/api/*` responses include ETag header, conditional GET returns 304, non-API paths have no ETag.

## Files Likely Touched

- `backend/app/middleware/__init__.py`
- `backend/app/middleware/timing.py`
- `backend/app/middleware/etag.py`
- `backend/app/main.py`
- `backend/tests/test_timing_middleware.py`
- `backend/tests/test_etag_middleware.py`
