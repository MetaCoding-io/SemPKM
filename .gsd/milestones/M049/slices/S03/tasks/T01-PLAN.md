---
estimated_steps: 21
estimated_files: 3
skills_used: []
---

# T01: Add per-query Server-Timing header via ContextVar accumulation

## Description

Add request-scoped SPARQL timing accumulation using `contextvars.ContextVar` so the `Server-Timing` response header includes per-query breakdown entries alongside the existing total.

## Steps

1. Read `backend/app/middleware/timing.py` and `backend/app/triplestore/client.py` to confirm current state.
2. In `timing.py`, add `from contextvars import ContextVar` and create `_sparql_timings: ContextVar[list[tuple[str, float]]] = ContextVar('_sparql_timings', default=None)`. Export a helper `record_sparql_timing(name: str, duration_ms: float)` that appends to the list if the var is set.
3. In `TimingMiddleware.dispatch()`, before `call_next()`: set the ContextVar to an empty list via `token = _sparql_timings.set([])`. After `call_next()`: read the accumulated list, serialize each entry as `sparql.N;dur=X.XX` (1-indexed), append to the existing `total;dur=Y.YY` Server-Timing value. Reset the ContextVar via `_sparql_timings.reset(token)` in a finally block.
4. In `client.py`, import `time` and `record_sparql_timing` from `app.middleware.timing`. In each of the 4 span methods (`query`, `update`, `construct`, `insert_graph`), wrap the HTTP call with `time.monotonic()` before/after, compute `duration_ms`, and call `record_sparql_timing(span_name, duration_ms)`. The span_name should match the OTel span name (e.g. `sparql.query`, `sparql.update`).
5. Create `backend/tests/test_server_timing.py` with tests:
   - Test that Server-Timing header contains `total;dur=` (baseline)
   - Test that after mocking TriplestoreClient methods to call `record_sparql_timing`, the header contains numbered `sparql.N;dur=` entries
   - Test that ContextVar is properly reset between requests (no leaking)

## Must-Haves

- [ ] ContextVar reset in finally block to prevent cross-request leaking
- [ ] Incrementing index for unique Server-Timing entry names
- [ ] No import cycle between timing.py and client.py
- [ ] record_sparql_timing is a no-op if ContextVar is None (not set)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v` — all tests pass
- `rg 'ContextVar' backend/app/middleware/timing.py` — confirms ContextVar usage
- `rg 'record_sparql_timing' backend/app/triplestore/client.py` — confirms client integration
- `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v` — 32 S01+S02 regression tests pass

## Inputs

- ``backend/app/middleware/timing.py` — existing TimingMiddleware with Server-Timing: total;dur=X`
- ``backend/app/triplestore/client.py` — existing OTel-instrumented SPARQL client with 4 span methods`

## Expected Output

- ``backend/app/middleware/timing.py` — extended with ContextVar, record_sparql_timing(), per-query Server-Timing serialization`
- ``backend/app/triplestore/client.py` — extended with time.monotonic() + record_sparql_timing() calls in each span method`
- ``backend/tests/test_server_timing.py` — new unit tests for Server-Timing header content and ContextVar isolation`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v
