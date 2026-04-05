---
id: T03
parent: S01
milestone: M049
key_files:
  - backend/app/browser/objects.py
  - backend/tests/test_object_parallel.py
key_decisions:
  - Used _CallTracker pattern for async delay testing with call counting instead of AsyncMock side_effect
duration: 
verification_result: passed
completed_at: 2026-04-05T20:15:09.280Z
blocker_discovered: false
---

# T03: Parallelized SPARQL property query and SQLite favorites check via asyncio.gather, added wall-clock timing log

**Parallelized SPARQL property query and SQLite favorites check via asyncio.gather, added wall-clock timing log**

## What Happened

Identified two independent I/O operations in get_object — the UNION SPARQL property query (RDF4J) and the favorites SQLite check — and wrapped them in asyncio.gather() using nested async helpers. Added time.perf_counter() instrumentation logging total handler wall-clock time at INFO level. Created test_object_parallel.py with _CallTracker helper introducing 0.15s delays to prove parallel execution completes in under 0.25s (vs 0.30s sequential). All 22 slice-specific tests pass.

## Verification

4/4 parallel tests pass (timing, both-ops-called, log emitted, log value). 6/6 T02 UNION tests pass. 12/12 T01 cache tests pass. Full suite has only pre-existing failures unrelated to this work.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_object_parallel.py -v` | 0 | ✅ pass | 1200ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_object_query_opt.py -v` | 0 | ✅ pass | 700ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py -v` | 0 | ✅ pass | 1400ms |

## Deviations

Used _CallTracker class instead of AsyncMock side_effect due to double-awaiting issues with nested async mock functions.

## Known Issues

3 pre-existing test failures in suite (test_ai_endpoints, test_app_views_commands, test_asana_sync_engine) — unrelated to this work.

## Files Created/Modified

- `backend/app/browser/objects.py`
- `backend/tests/test_object_parallel.py`
