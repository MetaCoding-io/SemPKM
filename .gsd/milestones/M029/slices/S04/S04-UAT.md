# S04: Backend Performance & HTTP Cache Headers — UAT

**Milestone:** M029
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Both middlewares are unit-tested with 36 tests covering all paths. S05 performs Docker/curl runtime verification. No human-experience aspects.

## Preconditions

- Docker test stack running with `docker compose -f docker-compose.test.yml up -d`
- Owner user authenticated (for timing report endpoint)
- At least one GET request to `/api/types` or similar JSON API endpoint completed (to populate timing stats)

## Smoke Test

Run `curl -sI http://localhost:3901/api/health` and confirm the response includes a `Server-Timing: total;dur=` header.

## Test Cases

### 1. Server-Timing header present on all responses

1. `curl -sI http://localhost:3901/api/health`
2. Check response headers
3. **Expected:** `Server-Timing: total;dur=X.XX` header present with a positive numeric duration value

### 2. ETag header on JSON API GET responses

1. `curl -sI http://localhost:3901/api/types`
2. Check response headers
3. **Expected:** Response includes `ETag: W/"<16-char-hex>"`, `Cache-Control: no-cache`, and `Vary: Accept, Authorization` headers

### 3. Conditional GET returns 304 Not Modified

1. `curl -sI http://localhost:3901/api/types` — copy the ETag value
2. `curl -sI -H 'If-None-Match: W/"<copied-etag>"' http://localhost:3901/api/types`
3. **Expected:** Second request returns HTTP 304 with no body, preserving ETag, Cache-Control, and Vary headers

### 4. ETag changes when response body changes

1. `curl -sI http://localhost:3901/api/types` — note ETag
2. Install or remove a Mental Model to change the types list
3. `curl -sI http://localhost:3901/api/types` — note new ETag
4. **Expected:** ETag value differs between the two requests

### 5. Non-API paths excluded from ETag

1. `curl -sI http://localhost:3901/` (HTML page)
2. Check response headers
3. **Expected:** No `ETag` header present (nginx serves static files, not the ETag middleware)

### 6. Timing report endpoint returns stats

1. Make several requests to `/api/types` and `/api/health`
2. `curl -H 'Authorization: Bearer <owner-token>' http://localhost:3901/api/admin/timing-report`
3. **Expected:** JSON response with `top_endpoints` array (each entry has path, count, avg_ms, max_ms, min_ms, p95_ms, total_ms), `total_requests` count, and `collection_period_seconds`

### 7. Timing report requires owner auth

1. `curl -sI http://localhost:3901/api/admin/timing-report` (no auth)
2. **Expected:** HTTP 401 or 302 redirect (not 200)

### 8. Well-known path included in ETag processing

1. `curl -sI http://localhost:3901/.well-known/sempkm` (with auth)
2. **Expected:** Response includes `ETag` header (if authenticated and response is JSON)

### 9. POST requests excluded from ETag

1. `curl -sI -X POST http://localhost:3901/api/commands` (with auth, empty body)
2. Check response headers
3. **Expected:** No `ETag` header present (POST is excluded)

## Edge Cases

### If-None-Match: * wildcard

1. `curl -sI -H 'If-None-Match: *' http://localhost:3901/api/types`
2. **Expected:** HTTP 304 — wildcard matches any ETag per HTTP spec

### Slow request logging

1. Check application logs after making requests
2. **Expected:** Requests taking >100ms appear at INFO level with format `Slow request: METHOD /path STATUS DURATIONms`

### Large response body (>1MB)

1. If an API endpoint can return >1MB of JSON, request it
2. **Expected:** Response has no ETag header (excluded by size limit)

## Failure Signals

- Missing `Server-Timing` header on any response → TimingMiddleware not registered
- Missing `ETag` header on `/api/types` GET → ConditionalGetMiddleware not registered or not matching path
- 304 not returned when sending matching `If-None-Match` → ETag computation or comparison broken
- `/api/admin/timing-report` returns 404 → timing_router not included in main.py
- `/api/admin/timing-report` returns 200 without auth → role guard missing

## Requirements Proved By This UAT

- PERF-08 — request timing middleware with Server-Timing header, slow request logging, admin timing report
- PERF-09 — ETag-based conditional GET on JSON API responses, 304 Not Modified for unchanged resources

## Not Proven By This UAT

- Runtime performance impact of middleware on request latency (requires load testing)
- ETag behavior with concurrent writers (single-user app, low risk)
- Integration with browser/extension caching behavior (verified by S05 Lighthouse)

## Notes for Tester

- The timing report accumulates stats in memory — stats reset on process restart. Make some requests before checking the report.
- Pre-existing test failure in `test_jira_sync_engine.py::TestComputeStatus` is unrelated to S04 changes (import path issue in worktree).
- Both middlewares are transparent — they add headers but never block or modify request processing. Worst case failure mode is missing headers, not broken requests.
