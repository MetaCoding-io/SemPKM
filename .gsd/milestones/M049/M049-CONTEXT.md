---
depends_on: []
---

# M049: Backend Performance & Observability

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Profile and fix the 4+ second object load times discovered during the feature tour. Set up distributed tracing infrastructure (Jaeger/OpenTelemetry) for ongoing performance visibility. The backend is the bottleneck — Network tab shows 4.07s "Waiting for server response" on individual htmx partial requests.

## Why This Milestone

Every interaction in the Object Browser feels sluggish. Opening an object, switching tabs, loading views — all take 4+ seconds. This is the single highest-impact improvement possible: it affects every user action. The TimingMiddleware from M029 exists but doesn't provide granular per-query breakdown needed to identify which SPARQL queries are slow.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open an object tab in under 1 second (down from 4+ seconds)
- See Server-Timing headers on all htmx responses showing SPARQL query time breakdown
- Access a /admin/performance dashboard showing request latency percentiles and slow query log

### Entry point / environment

- Entry point: http://localhost:4000 (browser) + Jaeger UI at http://localhost:16686
- Environment: Docker Compose dev stack + Jaeger container
- Live dependencies involved: RDF4J triplestore, SQLite

## Completion Class

- Contract complete means: Jaeger traces visible for object-tab requests, p95 object load under 1.5s measured by E2E timing
- Integration complete means: all htmx partial endpoints emit Server-Timing headers with per-query breakdown
- Operational complete means: Jaeger service running in docker-compose.yml, traces persisted

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Open an object tab — Jaeger trace shows full breakdown (SPARQL queries, template render, middleware)
- Object tab loads in under 1.5 seconds (measured via browser Network tab)
- Secondary panels (comments, inbox, collaboration) load lazily — not fetched until expanded
- /admin/performance shows p50/p95/p99 latency for the last hour

## Risks and Unknowns

- **Root cause unclear** — the 4s could be one slow query or 10 sequential 400ms queries. Profiling first, then fix.
- **RDF4J query plans** — may need triplestore-level optimization (indexes, query rewriting) that's harder to control
- **OpenTelemetry integration** — FastAPI + httpx + RDF4J HTTP client chain needs instrumentation at each layer
- **Lazy loading trade-off** — panels that load lazily may feel janky when expanded. Need to balance.

## Existing Codebase / Prior Art

- `backend/app/monitoring/middleware.py` — TimingMiddleware from M029 adds Server-Timing header. Currently only tracks total request time, not per-query breakdown.
- `backend/app/triplestore/client.py` — TriplestoreClient.query() is the choke point for all SPARQL reads. Instrumentation goes here.
- `backend/app/services/labels.py` — LabelService has TTL cache (300s, 64 entries). May not cover all object-tab label lookups.
- `backend/app/browser/objects.py` — object tab endpoint makes multiple sequential SPARQL queries (properties, body, edges, labels).
- `backend/app/browser/workspace.py` — workspace htmx endpoints for comments, inbox, lint panels.

## Relevant Requirements

- PERF-01 (M002): Event detail N+1 fix — established the batched query pattern
- PERF-02 through PERF-10 (M029): Frontend performance — this milestone is the backend counterpart

## Scope

### In Scope

- **Jaeger/OpenTelemetry setup** — add opentelemetry-sdk, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-httpx to deps. Jaeger container in docker-compose.yml. Trace context propagation through TriplestoreClient.
- **SPARQL query profiling** — instrument TriplestoreClient.query() and .update() with span timing. Tag spans with query type (object-tab, comments, labels, etc.)
- **Identify and fix top 5 slowest query paths** for object tab loading
- **Lazy-load secondary panels** — comments, inbox, collaboration panels should not fetch until the user expands them (currently all fire on object tab open via hx-trigger="load")
- **Server-Timing headers** — extend TimingMiddleware to include per-SPARQL-query timing in the header
- **Performance dashboard** — extend /admin/timing-report with percentile charts

### Out of Scope / Non-Goals

- Frontend bundle performance (already addressed in M029)
- Full APM platform (Datadog, New Relic) — Jaeger is sufficient for self-hosted
- Database (SQLite) query optimization — the bottleneck is SPARQL, not SQL

## Technical Constraints

- OpenTelemetry must not add measurable overhead to request latency
- Jaeger must be optional — app works fine without it (traces go nowhere)
- Lazy loading must not break the existing hx-trigger patterns

## Integration Points

- `docker-compose.yml` — Jaeger service (jaegertracing/all-in-one)
- `backend/app/main.py` — OpenTelemetry instrumentation setup in lifespan
- `backend/app/triplestore/client.py` — span creation around HTTP calls to RDF4J
- `backend/app/browser/objects.py` — object tab query optimization
- `backend/app/templates/browser/workspace.html` — lazy loading hx-trigger changes

## Open Questions

- Should we also profile the triplestore itself (RDF4J query execution time vs HTTP overhead)? May need RDF4J server-side logging.
- Is there a query plan / explain mechanism in RDF4J we can use?
