---
id: S02
parent: M049
milestone: M049
provides:
  - OTel tracing infrastructure (setup_tracing/shutdown_tracing API)
  - Jaeger v2 Docker service on sempkm network
  - SPARQL semantic span attributes for downstream analysis
  - otel_enabled/otel_exporter_endpoint config settings
requires:
  - slice: S01
    provides: Optimized object query path that tracing spans will measure
affects:
  - S03
key_files:
  - backend/app/monitoring/tracing.py
  - backend/app/main.py
  - backend/app/triplestore/client.py
  - backend/app/config.py
  - backend/tests/test_tracing.py
  - backend/pyproject.toml
  - backend/uv.lock
  - docker-compose.yml
key_decisions:
  - D383: Jaeger v2 over v1 — v1 reached EOL Dec 2025, v2 built on OTel Collector framework
  - D387: OTel init ordering — setup_tracing() before TriplestoreClient, shutdown before client.close()
patterns_established:
  - No-op tracer pattern: when otel_enabled=False, trace.get_tracer() returns no-op tracer — all span operations become zero-cost. No conditional checks needed in instrumented code.
  - Semantic SPARQL span attributes: sparql.type, sparql.text (truncated 500), sparql.result_count, sparql.graph_iri, sparql.data_size — consistent schema across all 4 TriplestoreClient methods.
  - OTel test pattern: _force_set_tracer_provider() + InMemorySpanExporter + SimpleSpanProcessor for capturing and asserting span attributes in unit tests without Jaeger.
observability_surfaces:
  - OTel spans for every FastAPI request (auto-instrumented, excludes health/monitoring)
  - OTel spans for every httpx HTTP call (auto-instrumented via HTTPXClientInstrumentor)
  - Custom semantic spans: sparql.query, sparql.update, sparql.construct, sparql.insert_graph with SPARQL-specific attributes
  - Jaeger UI at localhost:16686 for trace visualization (service name: sempkm-api)
  - BatchSpanProcessor logs export failures — Jaeger unavailability is silent (app continues working)
drill_down_paths:
  - .gsd/milestones/M049/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M049/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M049/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T20:41:17.868Z
blocker_discovered: false
---

# S02: OpenTelemetry + Jaeger Tracing

**Added OpenTelemetry distributed tracing with Jaeger v2 backend, instrumenting FastAPI requests and all 4 TriplestoreClient SPARQL methods with semantic span attributes, plus 10 unit tests.**

## What Happened

Three tasks delivered a complete distributed tracing infrastructure:

**T01 — Dependencies & Configuration:** Added 6 OpenTelemetry packages (core 1.40.0, instrumentation 0.61b0 — same release train) to pyproject.toml. Added `otel_enabled` (default False) and `otel_exporter_endpoint` settings to the config class. Added Jaeger v2 service to docker-compose.yml (OTLP HTTP on 4318, UI on 16686, 512MB mem limit) and wired OTEL_ENABLED/OTEL_EXPORTER_ENDPOINT env vars to the api service.

**T02 — Tracing Module & Instrumentation:** Created `backend/app/monitoring/tracing.py` with `setup_tracing()` and `shutdown_tracing()` functions. setup_tracing() creates a TracerProvider with OTLP/HTTP BatchSpanProcessor, instruments FastAPI (excluding health/monitoring URLs), and globally instruments httpx. Critical ordering: setup_tracing() is called at lifespan line 144, before TriplestoreClient creation at line 147, so HTTPXClientInstrumentor patches httpx before any AsyncClient is instantiated. shutdown_tracing() is called before client.close() to flush buffered spans while connections are alive. Added custom spans to all 4 main TriplestoreClient methods (query, update, construct, insert_graph) with semantic attributes: sparql.type, sparql.text (truncated to 500 chars), sparql.result_count, sparql.graph_iri, sparql.data_size. No conditional otel_enabled checks in client.py — the no-op tracer pattern means span operations cost ~1μs when tracing is disabled.

**T03 — Unit Tests:** Created 10 tests across 3 classes covering setup/shutdown lifecycle (disabled returns None, enabled returns TracerProvider, None shutdown is safe), all 4 TriplestoreClient span types with attribute verification via InMemorySpanExporter, text truncation at 500 chars, and result count reflecting SPARQL bindings. Key test engineering: built `_force_set_tracer_provider()` helper to bypass OTel's Once guard and re-bind module-level tracers between tests. All 22 S01 regression tests pass (shapes cache, query optimization, parallelization).

## Verification

All slice verification checks pass:

1. `cd backend && .venv/bin/python -m pytest tests/test_tracing.py -v` — 10/10 tests pass (0.42s)
2. `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v` — 22/22 tests pass (1.36s), zero regressions
3. `cd backend && uv lock --check` — lockfile consistent (exit 0)
4. `cd backend && .venv/bin/python -c "from app.monitoring.tracing import setup_tracing, shutdown_tracing; print('OK')"` — OK
5. `cd backend && .venv/bin/python -c "from app.triplestore.client import TriplestoreClient; print('OK')"` — OK
6. `cd backend && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"` — OK
7. `grep -q 'jaeger' docker-compose.yml` — exit 0
8. `grep -q 'OTEL_ENABLED' docker-compose.yml` — exit 0
9. `grep -q 'start_as_current_span' backend/app/triplestore/client.py` — exit 0
10. `grep -q 'setup_tracing' backend/app/main.py` — exit 0

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Minor: OTel package versions resolved to 1.40.0/0.61b0 (latest compatible with ~=1.31/~=0.52b0 pins). InMemorySpanExporter import path differs from plan. T03 required _force_set_tracer_provider() helper not anticipated in the plan to handle OTel global state between tests. None of these changed scope or outcomes.

## Known Limitations

Jaeger is not yet running in production — only in the Docker Compose dev stack. Tracing is disabled by default (otel_enabled=False). The test stack (docker-compose.test.yml) does not include Jaeger. E2E verification of the Jaeger UI with real traces is deferred to manual/integration testing.

## Follow-ups

S03 will add Server-Timing headers and an admin performance dashboard that consume the same OTel spans.

## Files Created/Modified

- `backend/pyproject.toml` — Added 6 OpenTelemetry packages to dependencies
- `backend/uv.lock` — Regenerated lockfile with OTel packages
- `backend/app/config.py` — Added otel_enabled and otel_exporter_endpoint settings
- `docker-compose.yml` — Added Jaeger v2 service and OTEL env vars on api service
- `backend/app/monitoring/tracing.py` — New OTel setup/shutdown module with FastAPI+httpx instrumentation
- `backend/app/main.py` — Wired setup_tracing/shutdown_tracing into lifespan
- `backend/app/triplestore/client.py` — Added custom semantic spans to query/update/construct/insert_graph
- `backend/tests/test_tracing.py` — 10 unit tests covering tracing lifecycle, all 4 span types, truncation, result counts
