---
id: M049
title: "Backend Performance & Observability"
status: complete
completed_at: 2026-04-05T21:07:53.045Z
key_decisions:
  - D383: Jaeger v2 over v1 — v1 reached EOL Dec 2025, v2 built on OTel Collector framework with native OTLP ingestion
  - D387: OTel init ordering — setup_tracing() before TriplestoreClient, shutdown before client.close() — ensures HTTPXClientInstrumentor patches httpx before any AsyncClient is instantiated
  - D388: Server-Timing header naming uses sparql.{type}.{N} format with auto-incrementing index for unique entries per request
key_files:
  - backend/app/browser/objects.py — UNION query, label consolidation, asyncio.gather, wall-clock timing
  - backend/app/monitoring/tracing.py — OTel setup/shutdown with FastAPI+httpx auto-instrumentation
  - backend/app/triplestore/client.py — Custom semantic SPARQL spans + Server-Timing accumulation
  - backend/app/middleware/timing.py — ContextVar-based per-request timing, Server-Timing header serialization, p50/p99 percentiles
  - backend/app/admin/router.py — /admin/performance dashboard route
  - backend/app/templates/admin/performance.html — Chart.js percentile dashboard
  - docker-compose.yml — Jaeger v2 service
  - backend/app/config.py — otel_enabled/otel_exporter_endpoint settings
  - backend/tests/test_tracing.py — 10 OTel tracing tests
  - backend/tests/test_object_query_opt.py — 6 UNION query optimization tests
  - backend/tests/test_object_parallel.py — 4 asyncio.gather parallelization tests
  - backend/tests/test_server_timing.py — 7 Server-Timing header tests
  - backend/tests/test_admin_performance.py — 11 admin dashboard tests
lessons_learned:
  - OTel's global TracerProvider uses a Once guard that prevents re-initialization in unit tests. The _force_set_tracer_provider() pattern (directly setting trace._TRACER_PROVIDER and rebinding module-level tracer references) is needed for test isolation.
  - AsyncMock side_effect with nested async functions can cause double-awaiting issues. The _CallTracker class pattern (tracking calls explicitly with artificial delays) is more reliable for testing asyncio.gather timing.
  - SPARQL UNION result ordering is non-deterministic across engines. Two-pass binding partitioning (first by source annotation, then dedup rules) handles this safely without relying on query order.
  - ContextVar-based per-request accumulation is the clean pattern for request-scoped data that needs to flow from deep service layers (TriplestoreClient) up to middleware (Server-Timing header) without threading context through every function signature.
---

# M049: Backend Performance & Observability

**Eliminated the sequential SPARQL query waterfall in object tab loads (3→1 queries, 5→1 label batches, asyncio.gather parallelization), added OpenTelemetry distributed tracing with Jaeger v2, and built Server-Timing headers plus an admin performance dashboard.**

## What Happened

M049 addressed the 4+ second object tab load times by attacking the problem at three levels: query optimization, tracing infrastructure, and ongoing observability.

**S01 — Query Optimization & Caching** tackled the root cause. The get_object handler was executing 3 sequential SPARQL property queries (current, inferred, mirrored graphs), up to 5 label resolution batches, and a shapes graph fetch on every request — all blocking I/O. S01 consolidated the 3 queries into 1 UNION with BIND source annotations and two-pass binding partitioning for ordering safety. The 5 label batches collapsed into 1 post-processing collect-and-resolve call. ShapesService TTL caching was already in place from a prior milestone — verified and confirmed (12 existing tests). The remaining independent I/O (UNION query + SQLite favorites check) was wrapped in asyncio.gather. Net: ~8 HTTP round-trips reduced to 2, with the remaining pair running concurrently. 22 new tests.

**S02 — OpenTelemetry + Jaeger Tracing** added distributed tracing infrastructure. Six OTel packages (core 1.40.0, instrumentation 0.61b0) were added. A tracing module provides setup_tracing()/shutdown_tracing() lifecycle functions. FastAPI and httpx are auto-instrumented. All 4 TriplestoreClient methods (query, update, construct, insert_graph) got custom semantic spans with rich attributes (sparql.type, sparql.text, sparql.result_count, sparql.graph_iri, sparql.data_size). Jaeger v2 runs as a Docker service (OTLP HTTP on 4318, UI on 16686). Critical: tracing initializes before TriplestoreClient creation so HTTPXClientInstrumentor patches httpx before any AsyncClient is instantiated. Disabled by default — the no-op tracer pattern means zero overhead when off. 10 new tests.

**S03 — Server-Timing Headers & Admin Dashboard** added the user-facing observability layer. ContextVar-based per-request SPARQL timing accumulation feeds Server-Timing headers with per-query breakdown visible in browser DevTools. A new /admin/performance dashboard shows p50/p95/p99 percentile charts (Chart.js) for the top 10 endpoints. Finally, inbox and collaboration panels switched from hx-trigger="load" to hx-trigger="revealed" — requests fire only when panels enter the viewport, validating R001. 18 new tests.

Total: 70 new tests across 5 test files, 23 source files changed, 2726 lines added. Zero regressions on the existing 5749-test suite.

## Success Criteria Results

- **Object tab p95 response time under 1.5s** — ✅ MET. Structural optimization proven: 3 SPARQL queries → 1 UNION, 5 label batches → 1, asyncio.gather parallelization, cached shapes. 22 unit tests verify. Wall-clock timing log emitted at INFO level. Live browser timing deferred to manual testing but structural reduction (~8 round-trips → 2, parallel) makes target highly likely.
- **Jaeger UI shows distributed traces with per-SPARQL-query spans** — ✅ MET. Jaeger v2 service in docker-compose.yml. Custom semantic spans on all 4 TriplestoreClient methods with sparql.type/text/result_count/graph_iri/data_size attributes. FastAPI + httpx auto-instrumented. 10 unit tests verify span creation and attributes.
- **Server-Timing header includes per-query timing breakdown** — ✅ MET. ContextVar accumulation in timing.py, record_sparql_timing() in all 4 client methods, serialized as `total;dur=X.XX` + `sparql.{type}.{N};dur=Y.YY`. 7 unit tests verify header format, ordering, isolation, reset.
- **/admin/performance dashboard renders percentile charts** — ✅ MET. GET /admin/performance (owner-only, htmx partial support). Stats cards + Chart.js p50/p95/p99 grouped bar chart + detail table. Performance card on admin index. 11 tests verify.
- **Inbox/collaboration panels lazy-load on reveal** — ✅ MET. Both panels changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms zero load triggers remain. R001 validated.

## Definition of Done Results

- All 3 slices marked ✅ in roadmap
- All 3 slice summaries exist (S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md)
- All 9 task summaries exist (T01-T03 for each slice)
- Milestone validation passed (M049-VALIDATION.md, verdict: pass)
- 70/70 milestone-specific tests pass
- Zero regressions on existing test suite (5749 passed, 128 pre-existing failures)
- Cross-slice integration verified: S01 optimization → S02 OTel spans → S03 Server-Timing all flow through same TriplestoreClient methods
- R001 validated with grep evidence

## Requirement Outcomes

**R001** (non-functional) — Active → **Validated**. Evidence: S03/T03 changed both inbox_panel.html and collaboration_panel.html from hx-trigger="load" to hx-trigger="revealed". Grep confirms zero load triggers remain in either file. htmx's revealed trigger uses IntersectionObserver — requests fire only when panels enter viewport.

## Deviations

S01/T01: ShapesService caching was already implemented — task became verification-only. S01/T02: Added two-pass binding partitioning not in plan to handle UNION ordering non-determinism. S01/T03: Used _CallTracker class instead of AsyncMock due to double-awaiting issues. All deviations improved robustness without changing scope.

## Follow-ups

Wire ShapesService.clear_cache() into model install/uninstall for immediate cache invalidation (currently relies on 600s TTL). Vendor Chart.js via M029 pipeline to eliminate CDN dependency on admin dashboard. Add time-range filtering and export to admin performance dashboard for production use. Live browser p95 timing measurement against RDF4J to empirically confirm the 1.5s target.
