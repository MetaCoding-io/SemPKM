---
estimated_steps: 30
estimated_files: 5
skills_used: []
---

# T02: Create admin performance dashboard with Chart.js percentile charts

## Description

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

## Inputs

- ``backend/app/middleware/timing.py` — get_timing_report() with p95_ms (T01 may have already modified this file)`
- ``backend/app/admin/router.py` — existing admin routes with templates_response helper`
- ``backend/app/templates/admin/index.html` — existing admin portal with dashboard-cards div`

## Expected Output

- ``backend/app/middleware/timing.py` — get_timing_report() extended with p50_ms and p99_ms`
- ``backend/app/admin/router.py` — new GET /admin/performance route`
- ``backend/app/templates/admin/performance.html` — new Chart.js dashboard template`
- ``backend/app/templates/admin/index.html` — Performance card added to dashboard-cards`
- ``backend/tests/test_admin_performance.py` — route access test`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_admin_performance.py -v && grep -q 'performance' backend/app/templates/admin/index.html && test -f backend/app/templates/admin/performance.html
