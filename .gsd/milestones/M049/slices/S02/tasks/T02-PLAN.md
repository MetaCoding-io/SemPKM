---
estimated_steps: 87
estimated_files: 3
skills_used: []
---

# T02: Create tracing module, wire lifespan, and instrument TriplestoreClient

Core implementation task. Creates the OTel tracing module, wires it into the FastAPI lifespan (before TriplestoreClient creation), and adds custom semantic spans to all 4 main TriplestoreClient methods.

## Steps

1. Create `backend/app/monitoring/tracing.py` with two functions:

   **`setup_tracing(app: FastAPI) -> TracerProvider | None`:**
   - Import settings from `app.config`
   - If `settings.otel_enabled` is False, log at DEBUG level and return None
   - Create a `Resource` with `service.name="sempkm-api"` and `service.version=settings.app_version`
   - Create `TracerProvider(resource=resource)`
   - Create `OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)`
   - Create `BatchSpanProcessor(exporter)` and add to provider
   - Call `trace.set_tracer_provider(provider)`
   - Call `FastAPIInstrumentor.instrument_app(app, excluded_urls="api/health,api/monitoring")` — this excludes health check and monitoring endpoints from creating traces
   - Call `HTTPXClientInstrumentor().instrument()` — this auto-instruments ALL httpx.AsyncClient instances globally, including TriplestoreClient._client
   - Log at INFO level: "OpenTelemetry tracing initialized, exporting to {endpoint}"
   - Return the provider

   **`shutdown_tracing(provider: TracerProvider | None) -> None`:**
   - If provider is None, return immediately
   - Call `provider.shutdown()` to flush any buffered spans
   - Log at INFO level: "OpenTelemetry tracing shut down"

   **Key imports:**
   ```python
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
   from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
   ```

2. Wire tracing into `backend/app/main.py` lifespan:
   - Add import at top: `from app.monitoring.tracing import setup_tracing, shutdown_tracing`
   - **CRITICAL ORDERING**: Call `setup_tracing(app)` BEFORE the `TriplestoreClient(...)` creation (currently at ~line 150). Place it right after `init_posthog()` (around line 147). The HTTPXClientInstrumentor must be called before any httpx.AsyncClient is created.
   - Store result: `app.state.tracer_provider = setup_tracing(app)`
   - In the shutdown block (after line 565, before `await client.close()`), add: `shutdown_tracing(app.state.tracer_provider)`

3. Add custom span instrumentation to `backend/app/triplestore/client.py`:
   - Add import at top: `from opentelemetry import trace`
   - Add module-level tracer: `tracer = trace.get_tracer("sempkm.triplestore")`
   - Wrap the 4 main methods with `tracer.start_as_current_span()`. When `otel_enabled` is False, `trace.get_tracer()` returns a no-op tracer — all span operations become no-ops with ~1μs overhead. No conditional logic needed.

   **For `query()`:**
   ```python
   async def query(self, sparql: str) -> dict:
       with tracer.start_as_current_span("sparql.query") as span:
           span.set_attribute("sparql.type", "SELECT")
           span.set_attribute("sparql.text", sparql[:500])
           resp = await self._client.post(
               self._repo_url,
               data={"query": sparql},
               headers={"Accept": "application/sparql-results+json"},
           )
           resp.raise_for_status()
           result = resp.json()
           span.set_attribute("sparql.result_count",
               len(result.get("results", {}).get("bindings", [])))
           return result
   ```

   **For `update()`:** span name `"sparql.update"`, attribute `sparql.type="UPDATE"`, `sparql.text=sparql[:500]`. No result_count.

   **For `construct()`:** span name `"sparql.construct"`, attribute `sparql.type="CONSTRUCT"`, `sparql.text=sparql[:500]`. No result_count (returns bytes).

   **For `insert_graph()`:** span name `"sparql.insert_graph"`, attributes `sparql.type="INSERT_GRAPH"`, `sparql.graph_iri=graph_iri`, `sparql.data_size=len(turtle_data)`. Don't log turtle_data content (could be large).

   **Do NOT instrument** `is_healthy()`, `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`, `transaction_update()`, `transaction_query()`, or `close()` — the httpx auto-instrumentation already covers the HTTP level for these, and they don't need semantic SPARQL attributes.

## Must-Haves

- [ ] `backend/app/monitoring/tracing.py` exists with setup_tracing and shutdown_tracing
- [ ] FastAPIInstrumentor and HTTPXClientInstrumentor activated in setup_tracing
- [ ] Health/monitoring URLs excluded from tracing
- [ ] setup_tracing called BEFORE TriplestoreClient in lifespan
- [ ] shutdown_tracing called in lifespan shutdown block
- [ ] Custom spans on query/update/construct/insert_graph with semantic attributes
- [ ] No conditional otel_enabled checks in client.py — relies on no-op tracer

## Verification

- `cd backend && .venv/bin/python -c "from app.monitoring.tracing import setup_tracing, shutdown_tracing; print('OK')"` prints OK
- `cd backend && .venv/bin/python -c "from app.triplestore.client import TriplestoreClient; print('OK')"` prints OK
- `grep -n 'setup_tracing' backend/app/main.py` shows the call exists before TriplestoreClient creation
- `grep -n 'shutdown_tracing' backend/app/main.py` shows the call in the shutdown block
- `grep -q 'start_as_current_span' backend/app/triplestore/client.py` exits 0

## Observability Impact

- Signals added: OTel spans for every FastAPI request and every SPARQL operation, with semantic attributes (sparql.type, sparql.text, sparql.result_count, sparql.graph_iri, sparql.data_size)
- How a future agent inspects this: Jaeger UI at localhost:16686, search for service="sempkm-api"
- Failure state exposed: BatchSpanProcessor logs export failures; Jaeger unavailability is silent (app continues working)

## Inputs

- `backend/pyproject.toml` — OTel packages must be installed (from T01)
- `backend/app/config.py` — otel_enabled and otel_exporter_endpoint settings (from T01)
- `backend/app/main.py` — lifespan function to wire into
- `backend/app/triplestore/client.py` — SPARQL methods to instrument
- `backend/app/monitoring/__init__.py` — existing package to add module to

## Expected Output

- `backend/app/monitoring/tracing.py` — new OTel setup/shutdown module
- `backend/app/main.py` — lifespan wired with setup_tracing/shutdown_tracing
- `backend/app/triplestore/client.py` — 4 methods instrumented with custom spans

## Inputs

- `backend/pyproject.toml`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/triplestore/client.py`
- `backend/app/monitoring/__init__.py`

## Expected Output

- `backend/app/monitoring/tracing.py`
- `backend/app/main.py`
- `backend/app/triplestore/client.py`

## Verification

cd backend && .venv/bin/python -c "from app.monitoring.tracing import setup_tracing, shutdown_tracing; print('OK')" && .venv/bin/python -c "from app.triplestore.client import TriplestoreClient; print('OK')" && grep -q 'setup_tracing' app/main.py && grep -q 'start_as_current_span' app/triplestore/client.py
