# M049: Backend Performance & Observability

## Vision
Fix the 4+ second object tab load times by optimizing the sequential SPARQL query waterfall, adding ShapesService caching, and establishing OpenTelemetry/Jaeger tracing infrastructure for ongoing performance visibility.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Query Optimization & Caching | high — combined sparql query may not optimize well on rdf4j; fallback is asyncio.gather parallelization | — | ✅ | Open 5 different objects in the browser. Each tab loads in under 1.5 seconds (Network tab timing). Before/after timing comparison captured. |
| S02 | OpenTelemetry + Jaeger Tracing | medium — new dependencies (otel sdk, jaeger container) may have unexpected interaction with existing middleware or docker networking | S01 | ⬜ | Open an object tab. Navigate to Jaeger UI at localhost:16686. Find the trace for the request showing FastAPI → TriplestoreClient → RDF4J span breakdown with timing for each SPARQL query. |
| S03 | Server-Timing Headers & Admin Dashboard | low — extends existing timingmiddleware and admin template patterns | S01, S02 | ⬜ | Open an object tab. In browser DevTools Network tab, inspect the response headers — Server-Timing shows per-query breakdown. Navigate to /admin/performance — Chart.js percentile charts render with real data. Collapse then expand the inbox panel — network request fires only on expand. |
