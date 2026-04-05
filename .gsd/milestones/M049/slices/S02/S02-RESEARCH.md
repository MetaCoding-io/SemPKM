# S02: OpenTelemetry + Jaeger Tracing — Research

**Slice risk:** medium — new dependencies (OTel SDK, Jaeger container) may interact with existing middleware or Docker networking
**Depth:** Targeted — known technology (OpenTelemetry), new to this codebase, moderate integration complexity

---

## Summary

Clean integration. No OTel or Jaeger references exist anywhere in the codebase. The `TriplestoreClient` (4 async methods: `query`, `update`, `construct`, `insert_graph`) is the single gateway for all SPARQL I/O — instrumenting it covers every triplestore interaction. The existing `monitoring/` package is the natural home for OTel setup. Jaeger v2 (latest: 2.16.0) is a drop-in Docker service. The main risk is dependency version alignment across OTel packages — they must all be from the same release train.

## Requirements Owned or Supported

No active requirements are owned by S02. The slice establishes tracing infrastructure that S03 consumes for Server-Timing headers and the admin dashboard.

---

## Implementation Landscape

### 1. Python Dependencies (all from 0.61b0 release train, March 2026)

| Package | Purpose | Size Impact |
|---------|---------|-------------|
| `opentelemetry-api` | Core tracing API (trace, context) | ~200KB |
| `opentelemetry-sdk` | TracerProvider, BatchSpanProcessor, Resource | ~300KB |
| `opentelemetry-exporter-otlp-proto-http` | OTLP HTTP exporter to Jaeger (no grpcio dep) | ~100KB |
| `opentelemetry-instrumentation-fastapi` | Auto-instrumentation: creates spans per HTTP request | ~50KB |
| `opentelemetry-instrumentation-httpx` | Auto-instrumentation: creates spans per httpx call | ~50KB |
| `opentelemetry-semantic-conventions` | Standard attribute names | ~50KB |

**Critical constraint:** All `opentelemetry-instrumentation-*` packages must be from the same release (0.61b0) and all `opentelemetry-api`/`opentelemetry-sdk` from the matching core release. Version mismatch causes import errors. Pin with `~=` to the minor.

**Build impact:** Adding to `pyproject.toml` requires `uv lock` regeneration + Docker image rebuild. Volume mounts don't help here — dependencies must be in the image.

### 2. Jaeger v2 Docker Service

Jaeger v1 reached EOL December 31, 2025. Jaeger v2 is built on the OpenTelemetry Collector framework and natively ingests OTLP.

```yaml
# docker-compose.yml addition
jaeger:
  image: jaegertracing/jaeger:2
  ports:
    - "16686:16686"   # Jaeger UI
    - "4317:4317"     # OTLP gRPC receiver
    - "4318:4318"     # OTLP HTTP receiver
  environment:
    MEMORY_MAX_TRACES: "10000"
  mem_limit: 512m
  networks:
    - sempkm
```

**Key points:**
- Image tag `2` (not `latest`) pins to v2.x without needing exact patch version
- In-memory storage is appropriate for dev — no persistence config needed
- `MEMORY_MAX_TRACES: 10000` caps memory usage
- Jaeger is **not** a dependency of any other service — no `depends_on` needed
- Ports 4317/4318 only need host exposure for debugging; inter-container communication uses Docker DNS (`jaeger:4318`)

### 3. Integration Points in Existing Code

#### 3.1 Settings — `backend/app/config.py`

Add two fields to the `Settings` class:

```python
# OpenTelemetry tracing (optional — app works without Jaeger)
otel_enabled: bool = False
otel_exporter_endpoint: str = "http://jaeger:4318/v1/traces"
```

Default `otel_enabled: False` ensures the app works unchanged without Jaeger. Docker Compose sets `OTEL_ENABLED=true` in the api service environment.

#### 3.2 OTel Setup Module — `backend/app/monitoring/tracing.py` (new file)

Single module containing:
- `setup_tracing(app: FastAPI) -> TracerProvider | None` — creates TracerProvider, BatchSpanProcessor, OTLPSpanExporter, calls `FastAPIInstrumentor.instrument_app(app)` and `HTTPXClientInstrumentor().instrument()`
- `shutdown_tracing(provider: TracerProvider | None)` — calls `provider.shutdown()` to flush buffered spans
- Returns `None` when `otel_enabled` is False — caller stores on `app.state.tracer_provider`

The `HTTPXClientInstrumentor` auto-instruments all `httpx.AsyncClient` instances globally — this covers the `TriplestoreClient._client` without modifying `client.py` for outbound HTTP spans.

#### 3.3 Custom Spans — `backend/app/triplestore/client.py`

While httpx auto-instrumentation captures HTTP-level spans, we need semantic SPARQL spans with query metadata. Add `tracer.start_as_current_span()` around each of the 4 main methods:

```python
from opentelemetry import trace

tracer = trace.get_tracer("sempkm.triplestore")

async def query(self, sparql: str) -> dict:
    with tracer.start_as_current_span("sparql.query") as span:
        span.set_attribute("sparql.type", "SELECT")
        span.set_attribute("sparql.text", sparql[:500])  # truncate for safety
        resp = await self._client.post(...)
        result = resp.json()
        span.set_attribute("sparql.result_count",
            len(result.get("results", {}).get("bindings", [])))
        return result
```

**Important:** When `otel_enabled` is False, `trace.get_tracer()` returns a no-op tracer. The `start_as_current_span` calls become no-ops with near-zero overhead (~1μs). No conditional logic needed in client code.

#### 3.4 Lifespan Integration — `backend/app/main.py`

In the `lifespan()` function:
- **After** `app = FastAPI(...)` (or early in lifespan before any services use httpx): call `setup_tracing(app)`, store result on `app.state.tracer_provider`
- **In shutdown block** (before `client.close()`): call `shutdown_tracing(app.state.tracer_provider)`

The `HTTPXClientInstrumentor().instrument()` must be called **before** any `httpx.AsyncClient` is created. In this codebase, `TriplestoreClient.__init__` creates `httpx.AsyncClient()`. So `setup_tracing()` must run before `TriplestoreClient(...)` in the lifespan. This is the one ordering constraint.

#### 3.5 Docker Compose Environment — `docker-compose.yml`

Add to the `api` service `environment` block:

```yaml
OTEL_ENABLED: ${OTEL_ENABLED:-true}
OTEL_EXPORTER_ENDPOINT: ${OTEL_EXPORTER_ENDPOINT:-http://jaeger:4318/v1/traces}
```

Default to `true` in the compose stack since Jaeger is available. Users without Jaeger can set `OTEL_ENABLED=false`.

### 4. Middleware Interaction

Current middleware chain (outermost first): `TimingMiddleware` → `ConditionalGetMiddleware` → `_WellKnownCORSMiddleware` → `CORSMiddleware` → `PostHogErrorMiddleware` → `SlowAPIMiddleware`

`FastAPIInstrumentor.instrument_app(app)` inserts an `OpenTelemetryMiddleware` (ASGI) that wraps the `ServerErrorMiddleware`. This is **inside** the user-added middleware chain. So the span tree is:

```
OTel root span (HTTP request)
  └─ TimingMiddleware wraps the full request
  └─ httpx spans (one per triplestore call)
    └─ sparql.query custom span (with query metadata)
```

This means the OTel root span captures the same timing as `TimingMiddleware`. No conflict.

### 5. Excluded URLs

Health checks and static asset endpoints should not create traces. Configure via `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` env var or `FastAPIInstrumentor.instrument_app(app, excluded_urls="api/health,api/monitoring")`. The regex-based exclusion prevents Jaeger from filling up with noise.

---

## Recommendation

### Task Decomposition

**T01 — Dependencies + Jaeger Docker service** (~20min)
- Add 6 OTel packages to `pyproject.toml` dependencies
- Regenerate `uv.lock` (`cd backend && uv lock`)
- Add `otel_enabled` and `otel_exporter_endpoint` to Settings class
- Add Jaeger service to `docker-compose.yml`
- Add `OTEL_ENABLED` env var to api service
- **Verify:** `uv lock` succeeds, `python -c "from opentelemetry import trace"` works in venv

**T02 — OTel setup module + lifespan integration** (~30min)
- Create `backend/app/monitoring/tracing.py` with `setup_tracing()` and `shutdown_tracing()`
- Integrate into `main.py` lifespan (before TriplestoreClient creation, after Settings)
- Wire `FastAPIInstrumentor.instrument_app(app)` and `HTTPXClientInstrumentor().instrument()`
- Configure excluded URLs (health, monitoring, static)
- Store `tracer_provider` on `app.state` for shutdown cleanup
- **Verify:** Unit tests import without error, app starts with `OTEL_ENABLED=false`

**T03 — Custom SPARQL spans on TriplestoreClient** (~20min)
- Add `tracer = trace.get_tracer("sempkm.triplestore")` to `client.py`
- Wrap `query()`, `update()`, `construct()`, `insert_graph()` with `start_as_current_span()`
- Set span attributes: `sparql.type`, `sparql.text` (truncated), `sparql.result_count` (for query)
- **Verify:** Unit tests for TriplestoreClient still pass, span attributes set correctly

**T04 — Integration test with Jaeger** (~20min)
- Docker rebuild and startup with Jaeger
- Hit object tab endpoint, verify traces appear in Jaeger UI at localhost:16686
- Confirm span tree: FastAPI request → httpx call → sparql.query custom span
- Capture screenshot/evidence of working trace
- **Verify:** Jaeger UI shows `sempkm-api` service with SPARQL query spans

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OTel package version conflicts | Low | Build fails | Pin all to same release train (~0.61b0) |
| HTTPXClientInstrumentor timing vs TriplestoreClient creation | Medium | No outbound spans | Call setup_tracing() before TriplestoreClient() in lifespan |
| Jaeger container doesn't start | Low | No traces (app still works) | In-memory storage, minimal config |
| OTel adds measurable latency | Very Low | Performance regression | BatchSpanProcessor is async, ~1μs per span creation |

### Natural Seams

- T01 is pure config/dependency work — no Python logic
- T02 is the core integration — creates the tracing module and wires it into the app
- T03 adds semantic richness to the auto-instrumented spans — can be tested independently
- T04 is integration verification — needs Docker running

T01 → T02 is strictly ordered (deps must exist before import). T03 depends on T02 (needs tracer module pattern). T04 depends on all three.

---

## Relevant Existing Code

| File | What It Does | How S02 Touches It |
|------|-------------|-------------------|
| `backend/app/config.py` | Settings class | Add `otel_enabled`, `otel_exporter_endpoint` |
| `backend/app/main.py` | Lifespan + middleware | Call `setup_tracing()` before TriplestoreClient creation, `shutdown_tracing()` in teardown |
| `backend/app/triplestore/client.py` | SPARQL gateway (4 methods) | Add custom span instrumentation |
| `backend/app/monitoring/` | Existing monitoring package | Add `tracing.py` module |
| `backend/pyproject.toml` | Dependencies | Add 6 OTel packages |
| `backend/uv.lock` | Lockfile | Regenerated by `uv lock` |
| `docker-compose.yml` | Service definitions | Add Jaeger service + OTEL env vars |
| `backend/Dockerfile` | Image build | No changes (rebuilt for new deps via `uv sync`) |

---

## Pitfalls

1. **HTTPXClientInstrumentor must be called before any httpx.AsyncClient instantiation.** If called after, existing client instances won't be instrumented. In this codebase, TriplestoreClient creates its httpx.AsyncClient in `__init__`. The lifespan creates TriplestoreClient early. So `setup_tracing()` must be the very first thing in the lifespan.

2. **Don't use `opentelemetry-exporter-otlp-proto-grpc`.** It pulls in `grpcio` (~50MB) with complex C++ build requirements. The HTTP exporter (`opentelemetry-exporter-otlp-proto-http`) is sufficient for a single-instance dev app.

3. **SPARQL text in span attributes must be truncated.** Some queries are 2KB+. OTel span attributes have a default max of 128 characters (configurable). Truncate to ~500 chars with a comment marker.

4. **The `trace.get_tracer()` no-op behavior is the key to "optional" tracing.** When no TracerProvider is configured (OTEL_ENABLED=false), all span operations are no-ops. No conditional `if otel_enabled:` wrappers needed in business code.

5. **`uv.lock` must be regenerated after adding packages.** The Dockerfile uses `uv sync --frozen` which refuses to install if the lockfile doesn't match `pyproject.toml`. Forgetting to regenerate the lock breaks the Docker build.

---

## Relevant Skills

- `bobmatnyc/claude-mpm-skills@opentelemetry` (312 installs) — OpenTelemetry guidance. Not essential given the straightforward integration pattern, but available if needed.
  Install: `npx skills add bobmatnyc/claude-mpm-skills@opentelemetry`
