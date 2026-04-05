---
id: T02
parent: S03
milestone: M049
key_files:
  - backend/app/middleware/timing.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/performance.html
  - backend/app/templates/admin/index.html
  - backend/tests/test_admin_performance.py
key_decisions:
  - Used full-page render with real template engine in tests rather than mocking — catches template rendering issues like missing filters
duration: 
verification_result: passed
completed_at: 2026-04-05T20:58:54.330Z
blocker_discovered: false
---

# T02: Added /admin/performance dashboard with Chart.js grouped bar chart showing p50/p95/p99 latency percentiles for top-10 endpoints, plus detail table and stats cards

**Added /admin/performance dashboard with Chart.js grouped bar chart showing p50/p95/p99 latency percentiles for top-10 endpoints, plus detail table and stats cards**

## What Happened

Extended get_timing_report() with p50_ms and p99_ms fields. Added GET /admin/performance route (owner-only, htmx block_name="content" support). Created performance.html template with stats cards, Chart.js CDN bar chart, and detail table. Added Performance card to admin index. Wrote 11 tests covering route access, auth, template rendering (including custom Jinja2 filter registration), empty state, htmx partial, and percentile computation accuracy.

## Verification

11/11 test_admin_performance passed. 7/7 test_server_timing passed. 32/32 S01+S02 regression tests passed. 20/20 test_timing_middleware passed. Template exists, Performance card present in index, p50_ms and p99_ms confirmed in timing.py.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_admin_performance.py -v` | 0 | ✅ pass | 790ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v` | 0 | ✅ pass | 400ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v` | 0 | ✅ pass | 1460ms |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_timing_middleware.py -v` | 0 | ✅ pass | 660ms |
| 5 | `grep -q performance backend/app/templates/admin/index.html` | 0 | ✅ pass | 50ms |
| 6 | `test -f backend/app/templates/admin/performance.html` | 0 | ✅ pass | 10ms |
| 7 | `rg p50_ms backend/app/middleware/timing.py` | 0 | ✅ pass | 20ms |
| 8 | `rg p99_ms backend/app/middleware/timing.py` | 0 | ✅ pass | 20ms |

## Deviations

Test setup required registering custom Jinja2 filters (asset_url, dict_without, urlencode, compact_iri) from template_helpers.py because base.html uses them.

## Known Issues

None.

## Files Created/Modified

- `backend/app/middleware/timing.py`
- `backend/app/admin/router.py`
- `backend/app/templates/admin/performance.html`
- `backend/app/templates/admin/index.html`
- `backend/tests/test_admin_performance.py`
