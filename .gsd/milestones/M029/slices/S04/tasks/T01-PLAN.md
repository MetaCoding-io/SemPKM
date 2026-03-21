---
estimated_steps: 7
estimated_files: 4
---

# T01: Implement timing middleware with top-5 report endpoint

**Slice:** S04 — Backend Performance & HTTP Cache Headers
**Milestone:** M029

## Description

Create a `TimingMiddleware` that measures request durations, logs slow requests, adds `Server-Timing` headers, accumulates per-path timing statistics, and exposes a top-5 slowest endpoint report via an admin API endpoint. This directly delivers requirement PERF-08 (backend profiling).

The middleware follows the exact `BaseHTTPMiddleware` pattern used by the existing `PostHogErrorMiddleware` in `backend/app/monitoring/middleware.py`. Use `time.monotonic()` for duration measurement (not `time.time()` — monotonic is used throughout the codebase for performance measurement).

**Relevant skill:** `test` — for generating comprehensive unit tests matching existing project conventions.

## Steps

1. **Create `backend/app/middleware/__init__.py`** — empty file to make the middleware directory a Python package.

2. **Create `backend/app/middleware/timing.py`** with:
   - `TimingMiddleware(BaseHTTPMiddleware)` with `dispatch()` method:
     - Record `time.monotonic()` before `call_next(request)`
     - Compute `duration_ms` after response
     - Add `Server-Timing: total;dur={duration_ms:.2f}` response header
     - Log at DEBUG level: `f"{request.method} {request.url.path} {response.status_code} {duration_ms:.1f}ms"`
     - Log at INFO level if `duration_ms > 100` (threshold)
     - Call `_record_timing(request.url.path, duration_ms)` to accumulate stats
   - `_timing_stats: dict[str, list[float]]` module-level dict mapping path → list of durations
   - `_MAX_SAMPLES_PER_PATH = 1000` — cap the list to prevent unbounded memory growth
   - `_record_timing(path: str, duration_ms: float)` — append to list, trim if exceeding max
   - `get_timing_report(top_n: int = 5) -> list[dict]` — compute per-path stats:
     - `path`, `count`, `avg_ms`, `max_ms`, `min_ms`, `p95_ms`, `total_ms`
     - Sort by `avg_ms` descending, return top_n
     - p95 = `sorted(durations)[int(len(durations) * 0.95)]`
   - `reset_timing_stats()` — clear stats (useful for tests)

3. **Add admin timing report endpoint** — Create a small router or add to an existing admin router file. The research suggests this can be a lightweight endpoint. Check if there's an existing admin API router; if not, add the route directly in `timing.py` as an `APIRouter`:
   - `GET /api/admin/timing-report` — requires owner role (use `require_role("owner")` dependency from `app.auth.dependencies`)
   - Returns JSON: `{"top_endpoints": [...], "total_requests": N, "collection_period_seconds": float}`
   - Include `total_requests` (sum of all path counts) and approximate collection duration

4. **Register middleware in `backend/app/main.py`**:
   - Add import: `from app.middleware.timing import TimingMiddleware`
   - Add import for the timing router
   - Add `app.add_middleware(TimingMiddleware)` — this must be the LAST `add_middleware` call (FastAPI processes middleware in reverse registration order, so last = outermost = captures total request time)
   - Include the timing report router

5. **Create `backend/tests/test_timing_middleware.py`** with unit tests:
   - Create a minimal FastAPI test app with the middleware
   - Test: `Server-Timing` header present on response
   - Test: header format is `total;dur=X.XX` with valid float
   - Test: timing stats accumulate after requests
   - Test: `get_timing_report()` returns correct structure with avg/max/p95
   - Test: p95 computation is correct with known data
   - Test: stats reset works
   - Test: `_MAX_SAMPLES_PER_PATH` cap is enforced
   - Test: admin endpoint returns JSON with correct schema
   - Test: admin endpoint requires authentication (mock or skip if complex)
   - Use `reset_timing_stats()` in test fixtures to isolate tests

6. **Run tests**: `cd backend && python -m pytest tests/test_timing_middleware.py -v`

7. **Run full suite**: `cd backend && python -m pytest tests/ -x --timeout=30` to verify no regressions

## Must-Haves

- [ ] `TimingMiddleware` adds `Server-Timing` header to every response
- [ ] Slow requests (>100ms) logged at INFO level
- [ ] Per-path timing stats accumulated in memory with cap
- [ ] `get_timing_report(top_n)` computes avg/max/min/p95/count per path
- [ ] `GET /api/admin/timing-report` returns JSON report (owner-only)
- [ ] Middleware registered as outermost in `main.py`
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_timing_middleware.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -x --timeout=30` — no regressions in full suite
- Check LSP diagnostics on new files — no type errors

## Inputs

- `backend/app/monitoring/middleware.py` — reference implementation pattern for `BaseHTTPMiddleware` usage
- `backend/app/main.py` lines 535-560 — middleware registration site (SlowAPI → PostHog → CORS order)
- `backend/app/auth/dependencies.py` — `require_role("owner")` dependency for admin endpoint

## Expected Output

- `backend/app/middleware/__init__.py` — empty package init
- `backend/app/middleware/timing.py` — TimingMiddleware class + timing report router + stats functions
- `backend/app/main.py` — modified with new middleware registration and router include
- `backend/tests/test_timing_middleware.py` — comprehensive unit tests

## Observability Impact

- **New signal — `Server-Timing` response header:** Every HTTP response gains a `Server-Timing: total;dur=X.XX` header showing request processing duration in milliseconds. Agents and operators can inspect this with `curl -sI`.
- **New signal — slow-request log lines:** Requests exceeding 100ms emit INFO-level log entries with method, path, status code, and duration. All requests log at DEBUG level.
- **New inspection surface — `/api/admin/timing-report`:** Returns JSON with `top_endpoints` (avg_ms, max_ms, min_ms, p95_ms, count, total_ms per path), `total_requests`, and `collection_period_seconds`. Owner-only access.
- **Failure visibility:** If the middleware raises during `call_next`, the exception propagates normally (no swallowing). Stats accumulation failures are silent (append to in-memory list only).
- **How to inspect:** `curl -sI /api/health | grep Server-Timing` for header presence. `curl /api/admin/timing-report` (with auth) for accumulated stats. `reset_timing_stats()` clears state for test isolation.
