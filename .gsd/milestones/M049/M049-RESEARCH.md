# M049: Backend Performance & Observability — Research

**Gathered:** 2026-04-05
**Status:** Ready for planning

---

## 1. Root Cause Analysis: The Object Tab Waterfall

The 4+ second object load time has a clear, measurable root cause: **10 sequential `await` calls** in the `get_object` endpoint (`backend/app/browser/objects.py:101-435`), each blocking on I/O before the next can start.

### Sequential Await Chain (Critical Path)

| # | Line | Operation | Est. Time | Notes |
|---|------|-----------|-----------|-------|
| 1 | 132 | `client.query(props_sparql)` — current graph | ~200-400ms | HTTP POST to RDF4J |
| 2 | 168 | `client.query(inferred_props_sparql)` — inferred graph | ~200-400ms | Identical pattern, different graph |
| 3 | 199 | `client.query(mirrored_props_sparql)` — mirrored graph | ~200-400ms | Identical pattern, different graph |
| 4 | 223 | `shapes_service.get_form_for_type()` | ~400-800ms | **Internally does 2 SPARQL queries** (model list + CONSTRUCT) + rdflib parsing. **NO CACHING.** |
| 5 | 258 | `label_service.resolve_batch(ref_iris)` | ~100-300ms | Cold cache = SPARQL query |
| 6 | 259 | `label_service.resolve_batch(type_class_iris)` | ~100-300ms | Cold cache = SPARQL query |
| 7 | 276 | `label_service.resolve_batch(iris_to_resolve)` | ~100-300ms | Cold cache = SPARQL query |
| 8 | 292 | `label_service.resolve_batch(inferred_iris)` | ~100-300ms | Cold cache = SPARQL query |
| 9 | 305 | `label_service.resolve_batch(mirrored_iris)` | ~100-300ms | Cold cache = SPARQL query |
| 10 | 331 | `db.execute()` — favorites SQL | ~5-10ms | SQLite, fast |

**Conservative total: ~1.7-3.6 seconds** just in the primary endpoint. And this is only the *first* of three parallel requests the browser makes:

### Additional Requests (Browser-Triggered on Tab Open)

- **`/browser/apps/right-pane-sections`** — 1 SPARQL query (type resolution) + template render
- **`/browser/relations/{iri}`** — 2 sequential SPARQL queries (outbound + inbound edges, each with 3 UNION clauses across 3 graphs) + 1 label batch
- **`/browser/lint/{iri}`** — lint service query
- **`/browser/object/{iri}/comments`** — comments query
- **`/api/federation/inbox-partial`** — federation inbox (hx-trigger="load")
- **`/api/federation/collab-partial`** — collaboration panel (hx-trigger="load")

The workspace template fires **inbox** and **collaboration** panel loads immediately on page load (`hx-trigger="load"`), not on object tab activation. These are always-loaded, not object-contextual.

### Key Bottleneck: ShapesService Has No Caching

`ShapesService.get_form_for_type()` calls `get_node_shapes()` → `_fetch_shapes_graph()` which:
1. Queries model registry for installed model IDs (1 SPARQL query)
2. CONSTRUCTs entire shapes graph from all model shape graphs (1 large SPARQL query)
3. Parses Turtle response into rdflib Graph
4. Traverses all NodeShapes to extract forms

This is ~400-800ms per call and **happens on every object tab load**. The `LabelService` and `ViewSpecService` both have TTL caches — ShapesService is the only major service without one.

---

## 2. Optimization Opportunities (Ranked by Impact)

### 2.1 Combine 3 Graph Queries into 1 (saves ~400-800ms)

Current: 3 sequential queries, one per graph (current, inferred, mirrored).

```sparql
-- COMBINED QUERY (replaces 3 separate queries):
SELECT ?g ?p ?o WHERE {
  VALUES ?g { <urn:sempkm:current> <urn:sempkm:inferred> <urn:sempkm:mirrored> }
  GRAPH ?g { <{decoded_iri}> ?p ?o }
}
```

Python-side partitioning by `?g` value is trivial. This eliminates 2 HTTP round trips to RDF4J.

### 2.2 Add TTL Cache to ShapesService (saves ~400-800ms)

Mirror the pattern from `LabelService` (`TTLCache(maxsize=4096, ttl=300)`). Cache the entire `list[NodeShapeForm]` result from `get_node_shapes()`. Invalidate on model install/uninstall (same as `ViewSpecService`).

### 2.3 Consolidate 5 Label Batches into 1-2 (saves ~200-800ms)

Currently 5 sequential `resolve_batch()` calls. The label cache helps on warm lookups, but on cold start or TTL expiry, each triggers a SPARQL query. Pre-collect all IRIs upfront, then call `resolve_batch()` once.

The challenge: some IRI sets depend on the shape/form data (ref_iris need `prop.target_class`), so the first properties query + shapes lookup must complete first. But the 5 label calls themselves can be collapsed:

```python
all_iris = set(ref_iris) | set(type_class_iris) | set(iris_to_resolve) | set(inferred_iris_to_resolve) | set(mirrored_iris_to_resolve)
all_labels = await label_service.resolve_batch(list(all_iris))
```

### 2.4 Parallelize Independent I/O with asyncio.gather (saves ~200-400ms)

After the combined graph query returns, shape lookup and label resolution are independent:

```python
form, all_labels, fav_result = await asyncio.gather(
    shapes_service.get_form_for_type(type_iri),
    label_service.resolve_batch(all_iris),
    db.execute(fav_query),
)
```

Pattern already established: `asyncio.gather` used in `ontology/service.py` (line 1732), `rdf_import/router.py` (line 124).

### 2.5 Combine Outbound + Inbound Relations into 1 Query (saves ~200-400ms)

The relations endpoint (`/browser/relations/{iri}`) runs 2 separate SPARQL queries. These can be merged with BIND for direction:

```sparql
SELECT ?dir ?predicate ?target ?source WHERE {
  {
    GRAPH ?g { <IRI> ?predicate ?target . FILTER(isIRI(?target)) }
    BIND("out" AS ?dir)
  } UNION {
    GRAPH ?g { ?target ?predicate <IRI> . FILTER(isIRI(?target)) }
    BIND("in" AS ?dir)
  }
  VALUES ?g { <current> <inferred> <mirrored> }
}
```

### 2.6 Lazy-Load Right Pane Panels (saves full HTTP round trips)

Inbox and collaboration panels fire `hx-trigger="load"` at workspace load time. These should be:
- `hx-trigger="revealed"` (loads only when `<details>` is opened) OR
- Loaded only when an object tab is active

---

## 3. Observability Infrastructure

### 3.1 Jaeger v2 (Not v1)

**Critical finding:** Jaeger v1 reached end-of-life December 31, 2025. Jaeger v2 is the current release (latest: 2.16.0), built on the OpenTelemetry Collector framework. The Docker image is now `jaegertracing/jaeger:latest` (not `jaegertracing/all-in-one`).

Key ports:
- 16686: Jaeger UI
- 4317: OTLP gRPC receiver
- 4318: OTLP HTTP receiver

Docker Compose addition:

```yaml
jaeger:
  image: jaegertracing/jaeger:latest
  ports:
    - "16686:16686"
    - "4317:4317"
    - "4318:4318"
  networks:
    - sempkm
```

### 3.2 OpenTelemetry Python SDK

Required packages:
- `opentelemetry-api` — core tracing API
- `opentelemetry-sdk` — TracerProvider, SpanProcessor
- `opentelemetry-instrumentation-fastapi` — automatic span creation per request
- `opentelemetry-instrumentation-httpx` — automatic spans for httpx HTTP calls (TriplestoreClient uses httpx.AsyncClient)
- `opentelemetry-exporter-otlp-proto-http` — OTLP HTTP exporter to Jaeger (lighter than gRPC, no grpcio dependency)

Setup in `main.py` lifespan:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

resource = Resource.create({"service.name": "sempkm-api"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://jaeger:4318/v1/traces")
))
trace.set_tracer_provider(provider)

# Auto-instrument FastAPI and httpx
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
```

### 3.3 Must Be Optional

The app must work without Jaeger running. The `BatchSpanProcessor` drops spans silently on connection failure (by design). Use an env var `OTEL_ENABLED=true/false` to control whether instrumentation is set up.

### 3.4 Custom Spans for SPARQL Queries

The `httpx` auto-instrumentation captures HTTP calls but doesn't tag them semantically. We need custom spans on `TriplestoreClient.query()`:

```python
tracer = trace.get_tracer("sempkm.triplestore")

async def query(self, sparql: str) -> dict:
    with tracer.start_as_current_span("sparql.query") as span:
        span.set_attribute("sparql.type", "SELECT")
        span.set_attribute("sparql.text", sparql[:200])  # truncate
        result = await self._client.post(...)
        span.set_attribute("sparql.result_count", len(result.get("results", {}).get("bindings", [])))
        return result
```

---

## 4. Existing Infrastructure to Reuse

### 4.1 TimingMiddleware (backend/app/middleware/timing.py)

Already provides:
- Total request timing via `Server-Timing` header
- Slow request logging (>100ms threshold)
- In-memory per-path timing statistics
- Admin API at `GET /api/admin/timing-report` (owner-only)

**Enhancement needed:** Add per-SPARQL-query breakdown to Server-Timing header:
```
Server-Timing: total;dur=1234.56, sparql.props;dur=345.67, sparql.shapes;dur=456.78, sparql.labels;dur=234.56
```

### 4.2 ETag Middleware (backend/app/middleware/etag.py)

Already in the middleware chain. No changes needed.

### 4.3 LabelService TTL Cache Pattern

Established caching pattern: `TTLCache(maxsize=4096, ttl=300)` with cache-check → miss collection → batch SPARQL → cache-fill. Use this same pattern for ShapesService.

### 4.4 asyncio.gather Pattern

Used in 4 places across the codebase. Well-established.

---

## 5. Risks and Mitigations

### 5.1 Combined SPARQL Query Performance

**Risk:** RDF4J may not optimize a GRAPH-variable query (`VALUES ?g { ... } GRAPH ?g { ... }`) as well as 3 separate fixed-graph queries.

**Mitigation:** Benchmark both approaches. If the combined query is slower, use `asyncio.gather` to parallelize the 3 separate queries instead.

### 5.2 ShapesService Cache Invalidation

**Risk:** Stale SHACL forms after model install/uninstall if cache isn't properly invalidated.

**Mitigation:** Follow ViewSpecService pattern — invalidate cache in model install/uninstall code paths. The existing 300s TTL provides a safety net.

### 5.3 OpenTelemetry Overhead

**Risk:** Span creation and export adds latency.

**Mitigation:** `BatchSpanProcessor` batches exports (default 5s interval, 512 max queue). The API is lightweight (<1μs per span start). Auto-instrumentation for FastAPI adds ~50μs per request. Negligible compared to 4s baseline.

### 5.4 Jaeger Container Resource Usage

**Risk:** Jaeger all-in-one with in-memory storage consumes RAM for trace data.

**Mitigation:** In-memory storage is appropriate for dev. Set `--memory.max-traces=10000` to cap memory. Docker `mem_limit: 512m` as safety.

### 5.5 right_pane_sections.html Template Missing

**Finding:** The template `browser/right_pane_sections.html` is referenced by `apps.py:187` but doesn't exist on disk. This endpoint likely 500s. Either it was never created or was lost in a merge. Needs investigation — may be a latent bug contributing to right-pane load issues.

---

## 6. Boundary Contracts

### 6.1 TriplestoreClient Instrumentation

The `TriplestoreClient` is the single gateway for all SPARQL operations. Instrumenting `query()`, `update()`, and `construct()` with OTel spans automatically covers every triplestore interaction across the entire app. This is the highest-leverage instrumentation point.

### 6.2 Server-Timing Header Contract

Current: `Server-Timing: total;dur=1234.56`
Target: `Server-Timing: total;dur=1234.56, db.sparql;dur=890.12, db.sql;dur=12.34`

The breakdown should use a request-scoped list that accumulates SPARQL timings, then gets serialized into the header by the middleware.

### 6.3 Admin Performance Dashboard

Extends existing `/api/admin/timing-report` JSON endpoint with an HTML admin page at `/admin/performance`. Chart.js is already bundled (used in model detail charts from M003).

---

## 7. Slice Boundary Recommendations

### Slice 1: Profile & Fix (Highest Risk, Highest Impact)
- Combine 3 graph queries into 1
- Add TTL cache to ShapesService
- Consolidate 5 label batches into 1
- Parallelize with asyncio.gather
- **Proof:** Object tab load time measured before/after

### Slice 2: OpenTelemetry + Jaeger Infrastructure
- Add Jaeger v2 to docker-compose.yml
- Add OTel SDK dependencies
- Instrument FastAPI (auto), httpx (auto), TriplestoreClient (custom spans)
- Configure OTEL_ENABLED env var
- **Proof:** Jaeger UI shows traces for object-tab requests

### Slice 3: Server-Timing Enhancement + Admin Dashboard
- Extend TimingMiddleware with per-query breakdown
- Build /admin/performance HTML page with Chart.js percentile charts
- Lazy-load right pane panels (inbox, collaboration)
- **Proof:** Browser Network tab shows per-query Server-Timing; admin page renders

---

## 8. Candidate Requirements

### Table Stakes (from milestone description)
- Object tab loads in under 1.5s (measured via browser Network tab or E2E timing)
- Jaeger traces visible for object-tab requests
- /admin/performance shows p50/p95/p99 latency

### Candidate New Requirements
- **PERF-11:** ShapesService TTL cache with model-install invalidation — prevents the #1 per-request bottleneck from recurring
- **PERF-12:** SPARQL query consolidation pattern — combine multi-graph queries where possible
- **PERF-13:** Server-Timing per-query breakdown — all htmx endpoints emit granular timing
- **PERF-14:** Jaeger/OTel optional infrastructure — app works with or without Jaeger container
- **PERF-15:** Right-pane lazy loading — non-object-contextual panels use `hx-trigger="revealed"` not `hx-trigger="load"`

### Out of Scope (confirmed)
- Frontend bundle optimization (already done in M029)
- SQLite query optimization (not the bottleneck)
- Full APM platform (Jaeger is sufficient for self-hosted)

---

## 9. Technology Notes

### Jaeger v2 vs v1
Jaeger v1 reached EOL Dec 31, 2025. Use `jaegertracing/jaeger:latest` (v2), not `jaegertracing/all-in-one` (v1). v2 natively ingests OTLP without additional configuration flags.

### OTLP HTTP vs gRPC
Use `opentelemetry-exporter-otlp-proto-http` (not grpc). HTTP avoids the `grpcio` dependency which adds ~50MB to the Docker image and has complex build requirements. HTTP performance is sufficient for a single-instance dev app.

### Available Skills
- `bobmatnyc/claude-mpm-skills@opentelemetry` (312 installs) — OpenTelemetry guidance
- `thebushidocollective/han@fastapi-async-patterns` (546 installs) — FastAPI async patterns (may help with gather/concurrency patterns)

Neither is essential — the OTel Python SDK docs and established codebase patterns provide sufficient guidance.

---

## 10. What Should Be Proven First

**Slice 1 (Profile & Fix) must come first.** The query consolidation and caching fixes are pure backend changes with no new dependencies. They can be benchmarked immediately with the existing TimingMiddleware. If the combined SPARQL query approach doesn't work well on RDF4J, the fallback (asyncio.gather with 3 separate queries) is equally viable. This de-risks the entire milestone.

Slice 2 (OTel/Jaeger) introduces new dependencies and Docker services. It should follow Slice 1 so we can validate that the traces show the *improved* performance, not just diagnose the old problem.

Slice 3 (Server-Timing + Dashboard) depends on both Slice 1 (optimized queries to time) and Slice 2 (trace infrastructure to display). Natural final slice.
