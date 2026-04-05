---
id: T01
parent: S03
milestone: M049
key_files:
  - backend/app/middleware/timing.py
  - backend/app/triplestore/client.py
  - backend/tests/test_server_timing.py
key_decisions:
  - Used name.N format (sparql.query.1) for Server-Timing entry names to keep entries unique when same span type called multiple times per request
duration: 
verification_result: passed
completed_at: 2026-04-05T20:53:53.687Z
blocker_discovered: false
---

# T01: Added ContextVar-based SPARQL timing accumulation so Server-Timing header includes per-query breakdown entries alongside request total

**Added ContextVar-based SPARQL timing accumulation so Server-Timing header includes per-query breakdown entries alongside request total**

## What Happened

Added _sparql_timings ContextVar to timing.py with a record_sparql_timing(name, duration_ms) helper. The middleware initializes the ContextVar before call_next() and resets it in a finally block. Accumulated entries are serialized as sparql.query.1;dur=X.XX into the Server-Timing header. Instrumented all 4 triplestore client span methods (query, update, construct, insert_graph) with time.monotonic() timing and record_sparql_timing() calls. Created 7 tests covering header content, ContextVar isolation, exception safety, and no-op behavior outside request context.

## Verification

7/7 new Server-Timing tests pass. 32/32 S01+S02 regression tests pass. grep confirms ContextVar usage in timing.py and record_sparql_timing integration in client.py.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v` | 0 | ✅ pass | 3400ms |
| 2 | `rg 'ContextVar' backend/app/middleware/timing.py` | 0 | ✅ pass | 100ms |
| 3 | `rg 'record_sparql_timing' backend/app/triplestore/client.py` | 0 | ✅ pass | 100ms |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v` | 0 | ✅ pass | 9100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/middleware/timing.py`
- `backend/app/triplestore/client.py`
- `backend/tests/test_server_timing.py`
