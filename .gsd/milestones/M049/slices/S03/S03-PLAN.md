# S03: Server-Timing Headers & Admin Dashboard

**Goal:** Add per-query Server-Timing header breakdown, an admin performance dashboard with Chart.js percentile charts, and lazy-load inbox/collaboration panels on reveal instead of page load.
**Demo:** After this: Open an object tab. In browser DevTools Network tab, inspect the response headers — Server-Timing shows per-query breakdown. Navigate to /admin/performance — Chart.js percentile charts render with real data. Collapse then expand the inbox panel — network request fires only on expand.

## Tasks
- [x] **T01: Added ContextVar-based SPARQL timing accumulation so Server-Timing header includes per-query breakdown entries alongside request total** — ## Description

Add request-scoped SPARQL timing accumulation using `contextvars.ContextVar` so the `Server-Timing` response header includes per-query breakdown entries alongside the existing total.

## Steps

1. Read `backend/app/middleware/timing.py` and `backend/app/triplestore/client.py` to confirm current state.
2. In `timing.py`, add `from contextvars import ContextVar` and create `_sparql_timings: ContextVar[list[tuple[str, float]]] = ContextVar('_sparql_timings', default=None)`. Export a helper `record_sparql_timing(name: str, duration_ms: float)` that appends to the list if the var is set.
3. In `TimingMiddleware.dispatch()`, before `call_next()`: set the ContextVar to an empty list via `token = _sparql_timings.set([])`. After `call_next()`: read the accumulated list, serialize each entry as `sparql.N;dur=X.XX` (1-indexed), append to the existing `total;dur=Y.YY` Server-Timing value. Reset the ContextVar via `_sparql_timings.reset(token)` in a finally block.
4. In `client.py`, import `time` and `record_sparql_timing` from `app.middleware.timing`. In each of the 4 span methods (`query`, `update`, `construct`, `insert_graph`), wrap the HTTP call with `time.monotonic()` before/after, compute `duration_ms`, and call `record_sparql_timing(span_name, duration_ms)`. The span_name should match the OTel span name (e.g. `sparql.query`, `sparql.update`).
5. Create `backend/tests/test_server_timing.py` with tests:
   - Test that Server-Timing header contains `total;dur=` (baseline)
   - Test that after mocking TriplestoreClient methods to call `record_sparql_timing`, the header contains numbered `sparql.N;dur=` entries
   - Test that ContextVar is properly reset between requests (no leaking)

## Must-Haves

- [ ] ContextVar reset in finally block to prevent cross-request leaking
- [ ] Incrementing index for unique Server-Timing entry names
- [ ] No import cycle between timing.py and client.py
- [ ] record_sparql_timing is a no-op if ContextVar is None (not set)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v` — all tests pass
- `rg 'ContextVar' backend/app/middleware/timing.py` — confirms ContextVar usage
- `rg 'record_sparql_timing' backend/app/triplestore/client.py` — confirms client integration
- `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v` — 32 S01+S02 regression tests pass
  - Estimate: 45m
  - Files: backend/app/middleware/timing.py, backend/app/triplestore/client.py, backend/tests/test_server_timing.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v
- [ ] **T02: Create admin performance dashboard with Chart.js percentile charts** — ## Description

Add a `/admin/performance` HTML page with Chart.js bar charts showing endpoint percentile timing data, fed by the existing `get_timing_report()` function with p50/p99 additions.

## Steps

1. Read `backend/app/middleware/timing.py` `get_timing_report()` to see current fields. Extend it to also compute `p50_ms` and `p99_ms` alongside existing `p95_ms`. Same percentile index computation pattern.
2. Add a new route in `backend/app/admin/router.py`:
   ```python
   @router.get("/performance")
   async def admin_performance(request: Request, user: User = Depends(require_role("owner"))):
   ```
   This route calls `get_timing_report(top_n=10)` and passes results + metadata (total_requests, collection_period_seconds) as template context.
3. Create `backend/app/templates/admin/performance.html` extending `base.html`:
   - Stats cards row: total requests, collection period, unique endpoints tracked
   - A bar chart (Chart.js via CDN `https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js`) showing grouped bars for p50/p95/p99 per endpoint (top 10)
   - A table below with all stats (path, count, avg, p50, p95, p99, max)
   - Use the `{% block content %}` pattern from other admin templates
   - Use htmx block_name="content" for sidebar navigation support
4. Add a Performance card to `backend/app/templates/admin/index.html` in the `dashboard-cards` div, matching the existing card style. Link to `/admin/performance` with htmx attributes.
5. Add a simple route test in `backend/tests/test_admin_performance.py`: mock the timing stats, hit GET /admin/performance, assert 200.

## Must-Haves

- [ ] get_timing_report() returns p50_ms and p99_ms in addition to existing fields
- [ ] /admin/performance requires owner role
- [ ] Chart.js loaded via CDN (no local file dependency)
- [ ] Admin index has a Performance card
- [ ] Template uses block_name="content" for htmx partial rendering

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_admin_performance.py -v` — route test passes
- `grep -q 'performance' backend/app/templates/admin/index.html` — card exists
- `test -f backend/app/templates/admin/performance.html` — template exists
- `rg 'p50_ms' backend/app/middleware/timing.py` — p50 computed
- `rg 'p99_ms' backend/app/middleware/timing.py` — p99 computed
  - Estimate: 45m
  - Files: backend/app/middleware/timing.py, backend/app/admin/router.py, backend/app/templates/admin/performance.html, backend/app/templates/admin/index.html, backend/tests/test_admin_performance.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_admin_performance.py -v && grep -q 'performance' backend/app/templates/admin/index.html && test -f backend/app/templates/admin/performance.html
- [ ] **T03: Lazy-load inbox and collaboration panels on reveal (R001)** — ## Description

Change the inbox and collaboration right-pane panels from `hx-trigger="load"` to `hx-trigger="revealed"` so they only fire HTTP requests when scrolled into view / expanded, not on every page load. This delivers requirement R001.

## Steps

1. Read `backend/app/templates/browser/partials/inbox_panel.html`. Change `hx-trigger="load, every 60s"` to `hx-trigger="revealed, every 60s"`. The `revealed` trigger fires when the element enters the viewport via IntersectionObserver. The `every 60s` continues independently after first reveal to keep the inbox fresh.
2. Read `backend/app/templates/browser/partials/collaboration_panel.html`. Change `hx-trigger="load"` to `hx-trigger="revealed"`.
3. Verify the changes are correct by grepping for the old and new patterns.

## Must-Haves

- [ ] Inbox panel: `hx-trigger="revealed, every 60s"` (not `load`)
- [ ] Collaboration panel: `hx-trigger="revealed"` (not `load`)
- [ ] No other htmx attributes changed

## Verification

- `grep 'hx-trigger' backend/app/templates/browser/partials/inbox_panel.html` — shows `revealed, every 60s`
- `grep 'hx-trigger' backend/app/templates/browser/partials/collaboration_panel.html` — shows `revealed`
- `! grep 'hx-trigger="load' backend/app/templates/browser/partials/inbox_panel.html` — no load trigger
- `! grep 'hx-trigger="load' backend/app/templates/browser/partials/collaboration_panel.html` — no load trigger
  - Estimate: 10m
  - Files: backend/app/templates/browser/partials/inbox_panel.html, backend/app/templates/browser/partials/collaboration_panel.html
  - Verify: grep 'revealed' backend/app/templates/browser/partials/inbox_panel.html && grep 'revealed' backend/app/templates/browser/partials/collaboration_panel.html && ! grep 'hx-trigger="load' backend/app/templates/browser/partials/inbox_panel.html && ! grep 'hx-trigger="load' backend/app/templates/browser/partials/collaboration_panel.html
