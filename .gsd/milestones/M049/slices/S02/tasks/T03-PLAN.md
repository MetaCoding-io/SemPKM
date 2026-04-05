---
estimated_steps: 75
estimated_files: 1
skills_used: []
---

# T03: Unit tests for tracing infrastructure

Write unit tests proving the tracing infrastructure works correctly: setup/shutdown lifecycle, custom TriplestoreClient spans with attributes, and no regressions on existing tests.

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

## Inputs

- `backend/app/monitoring/tracing.py`
- `backend/app/triplestore/client.py`
- `backend/tests/test_shapes_cache.py`
- `backend/tests/test_object_query_opt.py`
- `backend/tests/test_object_parallel.py`

## Expected Output

- `backend/tests/test_tracing.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_tracing.py -v && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v
