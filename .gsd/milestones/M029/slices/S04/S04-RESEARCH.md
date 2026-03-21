# S04 — Backend Performance & HTTP Cache Headers — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S04 adds request timing middleware, identifies the top-5 slowest endpoints, and adds ETag-based conditional GET support to appropriate API responses. The codebase has 288 route handlers across ~20 router files, one existing middleware (`PostHogErrorMiddleware` in `backend/app/monitoring/middleware.py`) using `BaseHTTPMiddleware`, and zero HTTP cache headers on any API or browser endpoint — the only `Cache-Control` headers are `no-cache` on SSE streaming responses. The VFS layer (`resources.py`, `mount_resource.py`) already implements ETags via wsgidav, but this is WebDAV-only and not relevant to FastAPI responses.

This is straightforward work: a timing middleware that logs request durations and aggregates a top-N report, plus an ETag middleware or per-endpoint helper for JSON API responses. No new libraries needed — Python's `hashlib` and `time` module plus FastAPI's response headers are sufficient. The timing middleware follows the exact same `BaseHTTPMiddleware` pattern as the existing `PostHogErrorMiddleware`.

## Recommendation

**Timing middleware:** Add `backend/app/middleware/timing.py` with a `TimingMiddleware` class extending `BaseHTTPMiddleware`. Log `method path status_code duration_ms` at INFO level for requests exceeding a configurable threshold (e.g., 100ms), DEBUG for all. Store per-path timing data in an in-memory dict for the top-5 report. Register in `main.py` via `app.add_middleware(TimingMiddleware)`. Include a one-time admin endpoint (`GET /api/admin/timing-report`) or CLI script to dump the top-5 slowest. The `Server-Timing` response header is a low-cost addition that makes timings visible in browser DevTools.

**ETag support on JSON API endpoints:** Add a lightweight ETag middleware that intercepts GET responses with `application/json` content type, computes a weak ETag from the response body hash, checks `If-None-Match`, and returns 304 when matched. This covers `/api/types`, `/api/shapes/*`, `/api/health`, `/api/sparql` (GET), and `/.well-known/sempkm` without modifying any individual endpoint. HTML template responses (which include session-specific data, CSRF tokens, etc.) should be excluded — ETags on HTML would cause stale content issues.

**ETag scope:** Only JSON API responses under `/api/` and `/.well-known/` get ETags. Browser routes (`/browser/*`), SSE streams, and write endpoints (POST/PUT/DELETE/PATCH) are excluded. The middleware approach is preferred over per-endpoint modification because it covers all current and future JSON API endpoints with zero code changes per route.

## Implementation Landscape

### Key Files

- `backend/app/monitoring/middleware.py` — Existing `PostHogErrorMiddleware` using `BaseHTTPMiddleware`. Reference pattern for the new timing middleware. Located in `monitoring/` not `middleware/` — the roadmap says `backend/app/middleware/timing.py` but keeping both in `monitoring/` is more consistent with current structure.
- `backend/app/main.py` — Middleware registration (lines 537-560). `app.add_middleware(...)` calls. New middlewares register here. Has ~30 router includes. The existing middleware order is: SlowAPI → PostHog → CORS.
- `backend/app/api/router.py` — The `/api/types`, `/api/shapes/{type_iri}`, `/api/context-query`, and `/.well-known/sempkm` endpoints. All return Pydantic models → JSON. These are the primary ETag candidates.
- `backend/app/sparql/router.py` — `GET /api/sparql` returns `JSONResponse` with SPARQL results. A second ETag candidate, though SPARQL results change frequently.
- `backend/app/health/router.py` — `GET /api/health` returns a dict (JSON). Low-value for ETag (health changes on every poll), but timing middleware captures it.
- `backend/app/config.py` — `Settings` class via `pydantic_settings`. Could add a `timing_threshold_ms: int = 100` setting, but a constant in the middleware is simpler for a one-time profiling feature.

### New Files

- `backend/app/middleware/__init__.py` — Empty init for new middleware package.
- `backend/app/middleware/timing.py` — `TimingMiddleware` class: records `time.monotonic()` before/after `call_next`, logs slow requests, accumulates top-N stats, adds `Server-Timing` header.
- `backend/app/middleware/etag.py` — `ConditionalGetMiddleware` class: for GET requests to JSON API paths, compute weak ETag from response body SHA-256, check `If-None-Match`, return 304 or add `ETag` + `Cache-Control: no-cache` headers.
- `backend/tests/test_timing_middleware.py` — Unit tests for timing middleware (request logging, threshold filtering, stats accumulation, Server-Timing header).
- `backend/tests/test_etag_middleware.py` — Unit tests for ETag middleware (ETag generation, 304 response on If-None-Match match, non-API paths excluded, POST requests excluded, non-JSON excluded).

### Build Order

**Task 1: Timing middleware** — Create `backend/app/middleware/timing.py` with `TimingMiddleware`. Register in `main.py`. Verify via Docker logs showing request timings. This is the lowest-risk deliverable and produces the top-5 report immediately.

**Task 2: Top-5 slowest endpoint report** — Run the Docker stack, exercise key pages (workspace load, object open, nav tree expand, SPARQL query, admin pages), then extract the top-5 from middleware stats. Document in a slice summary or report file. Could be a simple admin endpoint or a log dump.

**Task 3: ETag/conditional GET middleware** — Create `backend/app/middleware/etag.py` with `ConditionalGetMiddleware`. Register in `main.py`. Test with `curl -H "If-None-Match: <etag>"` against `/api/types`. Write unit tests proving 304 behavior.

**Task 4: Unit tests** — Tests for both middlewares. The timing middleware tests verify logging and header behavior. The ETag tests verify 304 responses, path filtering, and method filtering.

### Verification Approach

1. **Timing middleware:** `docker compose logs api | grep "timing"` shows request durations. `curl -sI http://localhost:8000/api/health | grep Server-Timing` shows the header.
2. **Top-5 report:** Hit `/api/admin/timing-report` or check the structured log output after exercising the app.
3. **ETag on JSON API:**
   ```bash
   # First request — gets ETag
   ETAG=$(curl -sI http://localhost:8000/api/types -H "Cookie: ..." | grep -i ETag | awk '{print $2}' | tr -d '\r')
   # Second request — should return 304
   curl -sI http://localhost:8000/api/types -H "Cookie: ..." -H "If-None-Match: $ETAG"
   ```
4. **Non-API paths excluded:** `curl -sI http://localhost:8000/browser/ -H "Cookie: ..."` should NOT have an ETag header.
5. **Unit tests:** `cd backend && python -m pytest tests/test_timing_middleware.py tests/test_etag_middleware.py -v`

## Constraints

- **`BaseHTTPMiddleware` and streaming responses:** `BaseHTTPMiddleware` wraps the entire response body, which breaks SSE/streaming. The ETag middleware must detect `StreamingResponse` and skip it. The existing `PostHogErrorMiddleware` has the same constraint (it only catches exceptions, doesn't read the body).
- **ETag on HTML would be wrong:** Browser routes return session-specific HTML (user name in header, CSRF tokens, active persona indicator). ETags on these would serve stale personalized content to the wrong user. Only JSON API paths are safe.
- **Middleware ordering:** FastAPI middleware executes in reverse registration order (last registered = outermost). Timing should be outermost (registers last) to capture total request time including other middleware overhead. ETag should be inside timing (registers before timing) so the timing header appears even on 304 responses.
- **`time.monotonic()` not `time.time()`:** Wall-clock time can jump on NTP sync. `time.monotonic()` is the correct choice for duration measurement — already used throughout the codebase (`ontology/service.py`, `obsidian/scanner.py`, `apps/scheduler.py`).
- **In-memory stats are per-worker:** If uvicorn runs multiple workers, each has its own timing stats dict. For a single-user self-hosted app this is fine. The top-5 report is a one-time analysis, not a permanent monitoring dashboard.

## Common Pitfalls

- **`BaseHTTPMiddleware` reads the full response body for ETag computation** — This doubles memory for large responses. Mitigate by only computing ETags for responses under a size threshold (e.g., 1MB) and only for JSON content types. SPARQL results returning 10K rows would be skipped.
- **Weak vs strong ETags** — Use weak ETags (`W/"hash"`) because the response may vary by encoding (gzip applied by nginx downstream). Strong ETags require byte-for-byte identical responses, which can't be guaranteed when nginx adds compression.
- **`If-None-Match: *`** — The HTTP spec says `If-None-Match: *` matches any resource that exists. The middleware should handle this edge case (return 304 if the resource has any ETag).
- **304 must preserve headers** — A 304 response must include `ETag`, `Cache-Control`, and `Vary` headers from the original response. Don't return a bare 304.

## Open Risks

- **`BaseHTTPMiddleware` performance** — Starlette's `BaseHTTPMiddleware` has a known issue where it creates a new `anyio.TaskGroup` per request, adding ~0.1ms overhead. For 288 routes this is negligible, but worth noting. The alternative (pure ASGI middleware) is more complex and not worth it for a one-time profiling feature.
- **Top-5 accuracy depends on exercising all routes** — If some slow endpoints aren't hit during the profiling session, they won't appear in the report. The report should note which routes were exercised and how many total requests were captured.
