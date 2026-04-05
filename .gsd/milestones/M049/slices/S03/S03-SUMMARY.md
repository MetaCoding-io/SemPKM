---
id: S03
parent: M049
milestone: M049
provides:
  - Server-Timing per-query breakdown for SPARQL profiling
  - Admin performance dashboard with percentile charts
  - Lazy-loaded panel pattern via htmx revealed trigger
requires:
  - slice: S01
    provides: TimingMiddleware and get_timing_report() infrastructure
  - slice: S02
    provides: OTel tracing spans in TriplestoreClient that Server-Timing entries parallel
affects:
  []
key_files:
  - backend/app/middleware/timing.py
  - backend/app/triplestore/client.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/performance.html
  - backend/app/templates/admin/index.html
  - backend/app/templates/browser/partials/inbox_panel.html
  - backend/app/templates/browser/partials/collaboration_panel.html
  - backend/tests/test_server_timing.py
  - backend/tests/test_admin_performance.py
key_decisions:
  - D388: Server-Timing header naming uses sparql.{type}.{N} format with auto-incrementing index for unique entries per request
patterns_established:
  - ContextVar-based per-request accumulation pattern: initialize before call_next(), collect during request, serialize into response header, reset in finally block
  - Admin dashboard template pattern: stats cards + Chart.js CDN chart + detail table, owner-only route with htmx block_name support
  - htmx revealed trigger for lazy-loading non-critical panels — fires on viewport entry via IntersectionObserver
observability_surfaces:
  - Server-Timing header with per-query SPARQL breakdown visible in browser DevTools Network tab
  - /admin/performance dashboard with p50/p95/p99 percentile charts for top-10 endpoints
drill_down_paths:
  - .gsd/milestones/M049/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M049/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M049/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T21:02:11.951Z
blocker_discovered: false
---

# S03: Server-Timing Headers & Admin Dashboard

**Added per-query Server-Timing header breakdown, admin performance dashboard with Chart.js percentile charts, and lazy-loaded inbox/collaboration panels.**

## What Happened

Three tasks delivered the final observability and performance layer for M049.

T01 added ContextVar-based SPARQL timing accumulation to `timing.py`. A `_sparql_timings` ContextVar is initialized before each request and reset in a finally block. All 4 TriplestoreClient span methods (`query`, `update`, `construct`, `insert_graph`) now wrap their HTTP calls with `time.monotonic()` and call `record_sparql_timing()`. The Server-Timing header includes both the request total (`total;dur=X.XX`) and per-query entries (`sparql.query.1;dur=Y.YY`, `sparql.update.2;dur=Z.ZZ`). The helper is a no-op when called outside request context (ContextVar not set), preventing errors in background tasks or tests.

T02 extended `get_timing_report()` with p50 and p99 percentile computation alongside the existing p95. Added GET `/admin/performance` (owner-only, htmx partial support via `block_name="content"`). The template renders stats cards (total requests, collection period, unique endpoints), a Chart.js grouped bar chart with p50/p95/p99 bars per endpoint (top 10 by avg latency), and a detail table with all stats. A Performance card was added to the admin index page. 11 tests cover route access, auth, template rendering, empty state, htmx partial, and percentile accuracy.

T03 was a two-line edit: inbox panel changed from `hx-trigger="load, every 60s"` to `hx-trigger="revealed, every 60s"`, and collaboration panel from `hx-trigger="load"` to `hx-trigger="revealed"`. htmx's `revealed` trigger uses IntersectionObserver — requests fire only when the panel enters the viewport, not on every page load. This validates requirement R001.

## Verification

70/70 tests pass across all M049 test files: 7 test_server_timing, 11 test_admin_performance, 12 test_shapes_cache, 7 test_object_query_opt, 4 test_object_parallel, 10 test_tracing, 20 test_timing_middleware. Grep confirms: ContextVar in timing.py, record_sparql_timing in client.py, p50_ms and p99_ms in timing.py, performance card in admin index, performance.html template exists, revealed triggers in both panel partials, no load triggers remain.

## Requirements Advanced

None.

## Requirements Validated

- R001 — Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 test setup required registering custom Jinja2 filters (asset_url, dict_without, urlencode, compact_iri) from template_helpers.py because base.html uses them. This was a test-infrastructure detail, not a functional deviation.

## Known Limitations

Server-Timing entries use in-memory ContextVar — no persistence. The admin performance dashboard shows in-memory timing stats that reset on server restart. Chart.js loaded via CDN (cdn.jsdelivr.net) — dashboard breaks if CDN is unavailable. The M029 vendor pipeline could absorb Chart.js to eliminate this dependency.

## Follow-ups

Consider vendoring Chart.js via the M029 pipeline to eliminate CDN dependency on the performance dashboard. Consider adding time-range filtering and export to the performance dashboard for production use.

## Files Created/Modified

- `backend/app/middleware/timing.py` — Added ContextVar-based _sparql_timings accumulation, record_sparql_timing() helper, Server-Timing header serialization with per-query entries, p50_ms and p99_ms in get_timing_report()
- `backend/app/triplestore/client.py` — Added time.monotonic() timing + record_sparql_timing() calls in all 4 span methods (query, update, construct, insert_graph)
- `backend/app/admin/router.py` — Added GET /admin/performance route (owner-only, htmx block_name support)
- `backend/app/templates/admin/performance.html` — New admin performance dashboard template with stats cards, Chart.js bar chart, and detail table
- `backend/app/templates/admin/index.html` — Added Performance card linking to /admin/performance
- `backend/app/templates/browser/partials/inbox_panel.html` — Changed hx-trigger from load to revealed
- `backend/app/templates/browser/partials/collaboration_panel.html` — Changed hx-trigger from load to revealed
- `backend/tests/test_server_timing.py` — New — 7 tests for ContextVar timing accumulation and Server-Timing header
- `backend/tests/test_admin_performance.py` — New — 11 tests for admin performance route, auth, template rendering, percentiles
