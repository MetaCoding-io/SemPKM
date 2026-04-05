# S02: OpenTelemetry + Jaeger Tracing — UAT

**Milestone:** M049
**Written:** 2026-04-05T20:41:17.868Z

# S02 UAT: OpenTelemetry + Jaeger Tracing

## Preconditions
- Docker Compose dev stack running (`docker compose up -d`)
- Backend venv installed with OTel packages (`cd backend && uv sync`)
- `OTEL_ENABLED=true` in environment (default in docker-compose.yml)

---

## Test 1: Tracing disabled by default in local dev (no Docker)

**Steps:**
1. Run `cd backend && .venv/bin/python -c "from app.config import settings; print(settings.otel_enabled)"`
2. Observe output

**Expected:** Prints `False` — tracing is off by default when OTEL_ENABLED env var is not set.

---

## Test 2: OTel packages importable

**Steps:**
1. Run `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter; from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor; from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor; print('All 5 OTel modules OK')"`

**Expected:** Prints "All 5 OTel modules OK" with no ImportError.

---

## Test 3: Tracing module setup/shutdown lifecycle

**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_tracing.py::TestSetupTracing -v`
2. Run `cd backend && .venv/bin/python -m pytest tests/test_tracing.py::TestShutdownTracing -v`

**Expected:** All 4 lifecycle tests pass — disabled returns None, enabled returns TracerProvider, None shutdown is safe, provider shutdown calls flush.

---

## Test 4: Custom SPARQL spans with semantic attributes

**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_tracing.py::TestTriplestoreClientSpans -v`

**Expected:** All 6 span tests pass:
- query → span "sparql.query" with sparql.type="SELECT", sparql.text present, sparql.result_count=0
- update → span "sparql.update" with sparql.type="UPDATE"
- construct → span "sparql.construct" with sparql.type="CONSTRUCT"
- insert_graph → span "sparql.insert_graph" with sparql.graph_iri and sparql.data_size
- Long query text truncated to ≤500 chars
- Result count reflects actual SPARQL bindings count

---

## Test 5: Jaeger v2 service in Docker Compose

**Steps:**
1. Run `docker compose config --services | grep jaeger`
2. Run `grep -A8 'jaeger:' docker-compose.yml`

**Expected:**
- jaeger service listed
- Image is `jaegertracing/jaeger:2`
- Ports 16686 (UI) and 4318 (OTLP HTTP) mapped
- MEMORY_MAX_TRACES=10000
- mem_limit: 512m
- Connected to sempkm network

---

## Test 6: Tracing wired into FastAPI lifespan at correct position

**Steps:**
1. Run `grep -n 'setup_tracing\|TriplestoreClient(' backend/app/main.py | head -5`
2. Run `grep -n 'shutdown_tracing\|await client.close' backend/app/main.py | head -5`

**Expected:**
- setup_tracing line number < TriplestoreClient line number (init before client)
- shutdown_tracing line number < client.close() line number (flush spans before closing HTTP)

---

## Test 7: No regressions on S01 optimization tests

**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v`

**Expected:** All 22 tests pass — shapes cache TTL, union query optimization, deduplication, async parallelization, timing logs all unaffected by tracing additions.

---

## Test 8: Jaeger UI accessible (Docker stack running)

**Precondition:** `docker compose up -d` with jaeger service running

**Steps:**
1. Open browser to `http://localhost:16686`
2. Check for Jaeger UI

**Expected:** Jaeger search page renders. Service dropdown may be empty if no requests have been traced yet.

---

## Edge Cases

### E1: App runs normally when Jaeger is unreachable
With `OTEL_ENABLED=true` but Jaeger container stopped, the app should start and serve requests normally. BatchSpanProcessor silently drops spans when the exporter endpoint is unreachable.

### E2: No-op tracer overhead when disabled
With `OTEL_ENABLED=false`, TriplestoreClient span operations use the no-op tracer. Overhead is ~1μs per span creation — functionally zero impact on query performance.

### E3: SPARQL text truncation prevents large query logging
A 10KB SPARQL query should have sparql.text attribute truncated to exactly 500 characters in the span, preventing trace storage bloat.
