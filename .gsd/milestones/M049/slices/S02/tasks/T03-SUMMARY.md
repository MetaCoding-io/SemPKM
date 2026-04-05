---
id: T03
parent: S02
milestone: M049
key_files:
  - backend/tests/test_tracing.py
key_decisions:
  - Used _force_set_tracer_provider() to bypass OTel Once guard and re-bind module-level tracers between tests
duration: 
verification_result: passed
completed_at: 2026-04-05T20:39:03.626Z
blocker_discovered: false
---

# T03: Created 10 unit tests for OTel tracing infrastructure covering setup/shutdown lifecycle, all 4 TriplestoreClient span types, text truncation, and result count attributes

**Created 10 unit tests for OTel tracing infrastructure covering setup/shutdown lifecycle, all 4 TriplestoreClient span types, text truncation, and result count attributes**

## What Happened

Wrote backend/tests/test_tracing.py with 10 test cases in 3 classes: TestSetupTracing (disabled returns None, enabled returns TracerProvider with instrumentation), TestShutdownTracing (None is safe no-op, provider shutdown works), and TestTriplestoreClientSpans (query/update/construct/insert_graph span names and attributes, text truncation at 500 chars, result_count reflects bindings). Key challenge was OTel's global state — set_tracer_provider() uses a Once guard blocking re-setting, and concrete Tracers are permanently bound to their provider. Built _force_set_tracer_provider() helper that resets the Once flag, clears _TRACER_PROVIDER, and re-binds the module-level tracer in client.py.

## Verification

All 10 new tests pass (pytest tests/test_tracing.py -v). All 22 existing S01 regression tests pass (test_shapes_cache, test_object_query_opt, test_object_parallel). All 9 slice-level verification checks pass including lockfile consistency, OTel imports, config settings, Jaeger in compose, and instrumentation grep checks.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_tracing.py -v` | 0 | ✅ pass | 420ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py -v` | 0 | ✅ pass | 1270ms |
| 3 | `cd backend && uv lock --check` | 0 | ✅ pass | 100ms |
| 4 | `grep -q 'setup_tracing' backend/app/main.py` | 0 | ✅ pass | 10ms |
| 5 | `grep -q 'start_as_current_span' backend/app/triplestore/client.py` | 0 | ✅ pass | 10ms |

## Deviations

InMemorySpanExporter import path differs from plan (in_memory_span_exporter vs in_memory). Required _force_set_tracer_provider() helper not anticipated in plan to handle OTel global state between tests.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_tracing.py`
