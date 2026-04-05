---
id: T02
parent: S02
milestone: M049
key_files:
  - backend/app/monitoring/tracing.py
  - backend/app/main.py
  - backend/app/triplestore/client.py
key_decisions:
  - Placed shutdown_tracing before client.close() so buffered spans flush while httpx connections are still alive
duration: 
verification_result: passed
completed_at: 2026-04-05T20:32:39.990Z
blocker_discovered: false
---

# T02: Created OTel tracing module with FastAPI+httpx auto-instrumentation and custom SPARQL spans on query/update/construct/insert_graph methods

**Created OTel tracing module with FastAPI+httpx auto-instrumentation and custom SPARQL spans on query/update/construct/insert_graph methods**

## What Happened

Created backend/app/monitoring/tracing.py with setup_tracing() and shutdown_tracing() functions. setup_tracing() creates a TracerProvider with OTLP/HTTP exporter, instruments FastAPI (excluding health/monitoring endpoints), and globally instruments httpx. Wired into FastAPI lifespan at line 144 (before TriplestoreClient at line 147) for correct instrumentation ordering. Added custom span instrumentation to all 4 main TriplestoreClient methods with semantic SPARQL attributes. No conditional otel_enabled checks in client.py — relies on no-op tracer when disabled.

## Verification

All 10 verification checks pass: tracing module imports OK, TriplestoreClient imports OK, setup_tracing precedes TriplestoreClient in lifespan, shutdown_tracing in shutdown block, start_as_current_span in client.py, uv lock consistent, OTel SDK importable, settings.otel_enabled exists, jaeger and OTEL_ENABLED in docker-compose.yml.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.monitoring.tracing import setup_tracing, shutdown_tracing; print('OK')"` | 0 | ✅ pass | 500ms |
| 2 | `cd backend && .venv/bin/python -c "from app.triplestore.client import TriplestoreClient; print('OK')"` | 0 | ✅ pass | 500ms |
| 3 | `grep -n 'setup_tracing' backend/app/main.py` | 0 | ✅ pass | 50ms |
| 4 | `grep -n 'shutdown_tracing' backend/app/main.py` | 0 | ✅ pass | 50ms |
| 5 | `grep -q 'start_as_current_span' backend/app/triplestore/client.py` | 0 | ✅ pass | 50ms |
| 6 | `cd backend && uv lock --check` | 0 | ✅ pass | 900ms |
| 7 | `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` | 0 | ✅ pass | 500ms |
| 8 | `cd backend && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"` | 0 | ✅ pass | 500ms |
| 9 | `grep -q 'jaeger' docker-compose.yml` | 0 | ✅ pass | 50ms |
| 10 | `grep -q 'OTEL_ENABLED' docker-compose.yml` | 0 | ✅ pass | 50ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/monitoring/tracing.py`
- `backend/app/main.py`
- `backend/app/triplestore/client.py`
