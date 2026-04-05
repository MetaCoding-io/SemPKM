# S02: OpenTelemetry + Jaeger Tracing

**Goal:** Add OpenTelemetry distributed tracing with Jaeger backend, instrumenting FastAPI requests and TriplestoreClient SPARQL operations with custom spans.
**Demo:** After this: Open an object tab. Navigate to Jaeger UI at localhost:16686. Find the trace for the request showing FastAPI → TriplestoreClient → RDF4J span breakdown with timing for each SPARQL query.

## Tasks
- [x] **T01: Added 6 OpenTelemetry packages, Jaeger v2 Docker service, and otel_enabled/otel_exporter_endpoint config settings** — Pure dependency and configuration task — no Python application logic. Adds the 6 OpenTelemetry packages to pyproject.toml (all from the same 0.61b0 release train), regenerates the lock file, adds Jaeger v2 to docker-compose.yml, and adds otel_enabled/otel_exporter_endpoint settings to the config class.

## Steps

1. Add these packages to the `[project.dependencies]` section of `backend/pyproject.toml`:
   - `opentelemetry-api~=1.31`
   - `opentelemetry-sdk~=1.31`
   - `opentelemetry-exporter-otlp-proto-http~=1.31`
   - `opentelemetry-instrumentation-fastapi~=0.52b0`
   - `opentelemetry-instrumentation-httpx~=0.52b0`
   - `opentelemetry-semantic-conventions~=0.52b0`
   Note: Version pins may need adjustment based on what's available in PyPI. Use `uv lock` output to determine the correct compatible versions. The key constraint is all `opentelemetry-instrumentation-*` packages must be from the same release train, and all core packages from the matching release.

2. Run `cd backend && uv lock` to regenerate the lockfile. If version conflicts arise, adjust pins to the latest compatible set.

3. Run `cd backend && uv sync` to install into the local venv.

4. Add two new fields to the `Settings` class in `backend/app/config.py`:
   ```python
   # OpenTelemetry tracing (optional — app works without Jaeger)
   otel_enabled: bool = False
   otel_exporter_endpoint: str = "http://jaeger:4318/v1/traces"
   ```
   Place them after the existing `posthog_*` settings block (or at the end of the class before `model_config`).

5. Add Jaeger v2 service to `docker-compose.yml`:
   ```yaml
   jaeger:
     image: jaegertracing/jaeger:2
     ports:
       - "16686:16686"   # Jaeger UI
       - "4318:4318"     # OTLP HTTP receiver
     environment:
       MEMORY_MAX_TRACES: "10000"
     mem_limit: 512m
     networks:
       - sempkm
   ```
   Place it after the `frontend` service, before the `networks:` section.

6. Add OTEL environment variables to the `api` service's `environment` block in `docker-compose.yml`:
   ```yaml
   OTEL_ENABLED: ${OTEL_ENABLED:-true}
   OTEL_EXPORTER_ENDPOINT: ${OTEL_EXPORTER_ENDPOINT:-http://jaeger:4318/v1/traces}
   ```

7. Verify: `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` succeeds.

## Must-Haves

- [ ] All 6 OTel packages in pyproject.toml with compatible version pins
- [ ] `uv lock` succeeds without conflicts
- [ ] `otel_enabled` and `otel_exporter_endpoint` fields in Settings class
- [ ] Jaeger v2 service in docker-compose.yml on sempkm network
- [ ] OTEL_ENABLED and OTEL_EXPORTER_ENDPOINT env vars on api service

## Verification

- `cd backend && uv lock --check` exits 0 (lockfile consistent)
- `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` prints OK
- `cd backend && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"` prints OK
- `grep -q 'jaeger' docker-compose.yml` exits 0
- `grep -q 'OTEL_ENABLED' docker-compose.yml` exits 0

## Inputs

- `backend/pyproject.toml` — existing dependency list to extend
- `backend/app/config.py` — Settings class to add fields to
- `docker-compose.yml` — service definitions to extend

## Expected Output

- `backend/pyproject.toml` — updated with 6 OTel packages
- `backend/uv.lock` — regenerated lockfile
- `backend/app/config.py` — Settings class with otel_enabled and otel_exporter_endpoint
- `docker-compose.yml` — Jaeger service + OTEL env vars on api service
  - Estimate: 20m
  - Files: backend/pyproject.toml, backend/uv.lock, backend/app/config.py, docker-compose.yml
  - Verify: cd backend && uv lock --check && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')" && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"
- [x] **T02: Created OTel tracing module with FastAPI+httpx auto-instrumentation and custom SPARQL spans on query/update/construct/insert_graph methods** — Core implementation task. Creates the OTel tracing module, wires it into the FastAPI lifespan (before TriplestoreClient creation), and adds custom semantic spans to all 4 main TriplestoreClient methods.

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
  - Estimate: 35m
  - Files: backend/app/monitoring/tracing.py, backend/app/main.py, backend/app/triplestore/client.py
  - Verify: cd backend && .venv/bin/python -c "from app.monitoring.tracing import setup_tracing, shutdown_tracing; print('OK')" && .venv/bin/python -c "from app.triplestore.client import TriplestoreClient; print('OK')" && grep -q 'setup_tracing' app/main.py && grep -q 'start_as_current_span' app/triplestore/client.py
- [ ] **T03: Unit tests for tracing infrastructure** — Write unit tests proving the tracing infrastructure works correctly: setup/shutdown lifecycle, custom TriplestoreClient spans with attributes, and no regressions on existing tests.

## Steps

1. Create `backend/tests/test_tracing.py` with these test cases:

   **Test: setup_tracing returns None when disabled**
   - Patch `settings.otel_enabled = False`
   - Call `setup_tracing(mock_app)` where mock_app is a MagicMock with `state` attribute
   - Assert returns None
   - Assert `FastAPIInstrumentor.instrument_app` was NOT called

   **Test: setup_tracing returns TracerProvider when enabled**
   - Patch `settings.otel_enabled = True` and `settings.otel_exporter_endpoint = "http://localhost:4318/v1/traces"`
   - Create a mock FastAPI app with `state` attribute
   - Call `setup_tracing(mock_app)`
   - Assert returns a TracerProvider instance
   - Assert `FastAPIInstrumentor.instrument_app` was called with the app
   - Assert `HTTPXClientInstrumentor().instrument()` was called
   - Call `shutdown_tracing(provider)` to clean up

   **Test: shutdown_tracing handles None provider gracefully**
   - Call `shutdown_tracing(None)` — must not raise

   **Test: TriplestoreClient.query() creates span with correct attributes**
   - Use `opentelemetry.sdk.trace.export.in_memory` `InMemorySpanExporter` to capture spans
   - Set up a TracerProvider with InMemorySpanExporter
   - Create a TriplestoreClient and mock the httpx response
   - Call `client.query("SELECT ?s WHERE { ?s a <http://example.org/Foo> }")`
   - Assert a span named "sparql.query" was exported
   - Assert span attributes: `sparql.type=="SELECT"`, `sparql.text` starts with "SELECT", `sparql.result_count==0` (empty result)

   **Test: TriplestoreClient.update() creates span with correct attributes**
   - Same setup with InMemorySpanExporter
   - Call `client.update("INSERT DATA { ... }")`
   - Assert span named "sparql.update" with `sparql.type=="UPDATE"`

   **Test: TriplestoreClient.construct() creates span with correct attributes**
   - Same setup
   - Call `client.construct("CONSTRUCT { ... }")`
   - Assert span named "sparql.construct" with `sparql.type=="CONSTRUCT"`

   **Test: TriplestoreClient.insert_graph() creates span with correct attributes**
   - Same setup
   - Call `client.insert_graph("<s> <p> <o> .", "http://example.org/graph")`
   - Assert span named "sparql.insert_graph" with `sparql.type=="INSERT_GRAPH"`, `sparql.graph_iri=="http://example.org/graph"`, `sparql.data_size` is an integer > 0

   **Test: sparql.text is truncated to 500 characters**
   - Create a query string longer than 500 chars
   - Call `client.query(long_query)`
   - Assert `sparql.text` attribute length <= 500

   **Test: existing S01 tests still pass (regression check)**
   - Run `test_shapes_cache.py`, `test_object_query_opt.py`, `test_object_parallel.py` and verify all pass

2. For the span attribute tests, use the OTel SDK's `InMemorySpanExporter` pattern:
   ```python
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import SimpleSpanProcessor
   from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter
   from opentelemetry import trace

   exporter = InMemorySpanExporter()
   provider = TracerProvider()
   provider.add_span_processor(SimpleSpanProcessor(exporter))
   trace.set_tracer_provider(provider)
   # ... run code that creates spans ...
   spans = exporter.get_finished_spans()
   ```
   **IMPORTANT:** After each test, call `trace.set_tracer_provider(TracerProvider())` to reset global state, or use a fixture that does this.

3. For mocking httpx responses in TriplestoreClient tests, use `unittest.mock.AsyncMock` to patch `self._client.post`/`self._client.put` on the client instance. Return mock response objects with `.status_code=200`, `.json()` returning `{"results":{"bindings":[]}}`, `.content` returning `b""`, and `.raise_for_status()` as no-op.

## Must-Haves

- [ ] test_tracing.py with 8+ test cases covering setup/shutdown, all 4 client methods, truncation, and disabled mode
- [ ] Uses InMemorySpanExporter for span capture (no Jaeger dependency)
- [ ] Proper OTel global state cleanup between tests
- [ ] All new tests pass
- [ ] Existing S01 tests pass (zero regressions)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_tracing.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v` — zero regressions

## Inputs

- `backend/app/monitoring/tracing.py` — module to test (from T02)
- `backend/app/triplestore/client.py` — instrumented client to test (from T02)
- `backend/tests/test_shapes_cache.py` — existing test for regression check
- `backend/tests/test_object_query_opt.py` — existing test for regression check
- `backend/tests/test_object_parallel.py` — existing test for regression check

## Expected Output

- `backend/tests/test_tracing.py` — new test file with 8+ test cases
  - Estimate: 30m
  - Files: backend/tests/test_tracing.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_tracing.py -v && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v
