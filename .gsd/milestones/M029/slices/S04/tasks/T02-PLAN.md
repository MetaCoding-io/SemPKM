---
estimated_steps: 6
estimated_files: 3
---

# T02: Implement ETag conditional GET middleware for JSON API responses

**Slice:** S04 — Backend Performance & HTTP Cache Headers
**Milestone:** M029

## Description

Create a `ConditionalGetMiddleware` that computes weak ETags on JSON API responses and returns 304 Not Modified when the client sends a matching `If-None-Match` header. This directly delivers requirement PERF-09 (backend cache headers).

The middleware intercepts only GET requests to `/api/` and `/.well-known/` paths with `application/json` content type. It skips streaming responses, non-GET methods, non-JSON content, large responses (>1MB), and all browser/HTML routes. This scope prevents stale content issues with session-specific HTML (CSRF tokens, user info) while enabling efficient caching for the API surface used by the browser extension and frontend AJAX calls.

**Relevant skill:** `test` — for generating comprehensive unit tests matching existing project conventions.

## Steps

1. **Create `backend/app/middleware/etag.py`** with:
   - `ConditionalGetMiddleware(BaseHTTPMiddleware)` with `dispatch()` method:
     - Skip immediately if `request.method != "GET"`
     - Skip if path doesn't start with `/api/` and doesn't start with `/.well-known/`
     - Call `response = await call_next(request)`
     - Skip if response is `StreamingResponse` (check `isinstance`)
     - Skip if content-type doesn't contain `application/json`
     - Read response body: `body = b"".join([chunk async for chunk in response.body_iterator])`
     - Skip if `len(body) > 1_048_576` (1MB) — rebuild response from body and return
     - Compute `hashlib.sha256(body).hexdigest()[:16]`
     - Create weak ETag: `etag = f'W/"{hash_hex}"'`
     - Check `request.headers.get("if-none-match")`:
       - If it equals the computed ETag OR equals `*`, return `Response(status_code=304)` with headers: `ETag`, `Cache-Control: no-cache`, `Vary: Accept, Authorization`
     - Otherwise, return new `Response(content=body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)` with added `ETag`, `Cache-Control: no-cache`, and `Vary: Accept, Authorization` headers
   - Important: When reading the body from `response.body_iterator`, the original response becomes consumed. Must create a new `Response` object with the read body.

2. **Register in `backend/app/main.py`**:
   - Add import: `from app.middleware.etag import ConditionalGetMiddleware`
   - Add `app.add_middleware(ConditionalGetMiddleware)` — BEFORE the `TimingMiddleware` registration (so timing wraps ETag and captures total time including 304 responses)
   - The ordering in `main.py` should be: `...existing middleware... → ConditionalGetMiddleware → TimingMiddleware` (TimingMiddleware added last = outermost)

3. **Create `backend/tests/test_etag_middleware.py`** with unit tests using a minimal FastAPI test app:
   - Create a test FastAPI app with routes:
     - `GET /api/test` returning `JSONResponse({"data": "hello"})`
     - `GET /api/test-dynamic` returning `JSONResponse({"time": str(time.time())})` (changes each call)
     - `GET /browser/page` returning `HTMLResponse("<html>page</html>")`
     - `POST /api/test` returning `JSONResponse({"created": True})`
     - `GET /api/stream` returning `StreamingResponse` with JSON content type
     - `GET /.well-known/sempkm` returning `JSONResponse({"version": "1.0"})`
   - Test cases:
     - **ETag present on JSON API GET**: GET `/api/test` → response has `ETag` header matching `W/"..."` pattern
     - **ETag is consistent**: Two identical GET `/api/test` → same ETag value
     - **ETag changes when body changes**: GET `/api/test-dynamic` twice → different ETags
     - **304 on If-None-Match match**: GET `/api/test` → get ETag → GET `/api/test` with `If-None-Match: <etag>` → 304 status, no body, ETag/Cache-Control/Vary headers preserved
     - **200 on If-None-Match mismatch**: GET `/api/test` with `If-None-Match: W/"wrong"` → 200 with body
     - **Non-API path excluded**: GET `/browser/page` → no ETag header
     - **POST excluded**: POST `/api/test` → no ETag header
     - **Streaming response excluded**: GET `/api/stream` → no ETag header
     - **Well-known path included**: GET `/.well-known/sempkm` → has ETag header
     - **If-None-Match: * returns 304**: GET `/api/test` (to establish resource exists), then GET with `If-None-Match: *` → 304
     - **304 response has required headers**: verify ETag, Cache-Control, Vary all present on 304
     - **Cache-Control is no-cache**: verify Cache-Control header value is exactly `no-cache`

4. **Run tests**: `cd backend && python -m pytest tests/test_etag_middleware.py -v`

5. **Run full suite**: `cd backend && python -m pytest tests/ -x --timeout=30` to verify no regressions

6. **Check LSP diagnostics** on `backend/app/middleware/etag.py` and `backend/app/main.py` — no type errors

## Must-Haves

- [ ] Weak ETag header (`W/"..."`) added to GET JSON responses on `/api/` and `/.well-known/` paths
- [ ] `If-None-Match` match returns 304 with ETag, Cache-Control, Vary headers preserved
- [ ] `If-None-Match: *` returns 304 per HTTP spec
- [ ] Non-API paths, POST/PUT/DELETE, streaming responses, and non-JSON excluded
- [ ] Large responses (>1MB) excluded from ETag computation
- [ ] `Cache-Control: no-cache` header on all ETag-bearing responses
- [ ] Middleware registered in `main.py` inside timing middleware (added before TimingMiddleware)
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_etag_middleware.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -x --timeout=30` — no regressions in full suite
- Check LSP diagnostics on new files — no type errors

## Observability Impact

- **New response headers:** `ETag` (weak, `W/"..."` format), `Cache-Control: no-cache`, `Vary: Accept, Authorization` on all GET JSON API responses under `/api/` and `/.well-known/`.
- **304 responses:** When `If-None-Match` matches, 304 Not Modified is returned with no body — visible in Server-Timing stats via TimingMiddleware and in standard HTTP access logs.
- **Inspection:** `curl -sI /api/types | grep -iE 'etag|cache-control|vary'` shows all three headers. Follow-up `curl -sI -H 'If-None-Match: <etag>' /api/types` returns 304.
- **Failure visibility:** Middleware silently skips non-qualifying requests (non-GET, non-JSON, streaming, large, non-API paths) — no error logs. If ETag computation fails, the response passes through unmodified.
- **Metrics impact:** 304 responses are faster (no body serialization cost). TimingMiddleware captures them in its per-path stats, so `/api/admin/timing-report` reflects the speedup.

## Inputs

- `backend/app/middleware/__init__.py` — package created by T01
- `backend/app/main.py` — T01 already added TimingMiddleware registration; this task adds ConditionalGetMiddleware before it
- `backend/app/monitoring/middleware.py` — reference for BaseHTTPMiddleware pattern

## Expected Output

- `backend/app/middleware/etag.py` — ConditionalGetMiddleware class
- `backend/app/main.py` — modified with ETag middleware registration (before timing)
- `backend/tests/test_etag_middleware.py` — comprehensive unit tests
