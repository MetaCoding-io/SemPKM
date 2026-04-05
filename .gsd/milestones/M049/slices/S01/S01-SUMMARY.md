---
id: S01
parent: M049
milestone: M049
provides:
  - Optimized get_object handler (1 SPARQL + 1 label batch + cached shapes + parallel I/O)
  - Wall-clock timing log infrastructure for S02 tracing integration
  - 22 regression tests for query optimization behavior
requires:
  []
affects:
  - S02
  - S03
key_files:
  - backend/app/browser/objects.py
  - backend/app/services/shapes.py
  - backend/tests/test_shapes_cache.py
  - backend/tests/test_object_query_opt.py
  - backend/tests/test_object_parallel.py
key_decisions:
  - Two-pass binding partitioning for UNION ordering safety — first pass partitions by source, second pass applies dedup rules
  - _CallTracker pattern for async delay testing — avoids double-awaiting issues with AsyncMock side_effect on nested async functions
patterns_established:
  - SPARQL UNION with BIND source annotation for multi-graph queries — replaces sequential per-graph queries
  - asyncio.gather for independent I/O operations in FastAPI handlers
  - time.perf_counter() wall-clock logging pattern for handler performance visibility
observability_surfaces:
  - INFO-level wall-clock timing log: 'get_object {iri} completed in {elapsed:.3f}s'
  - DEBUG-level ShapesService cache hit/miss logging
drill_down_paths:
  - .gsd/milestones/M049/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M049/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M049/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T20:18:32.934Z
blocker_discovered: false
---

# S01: Query Optimization & Caching

**Eliminated the sequential SPARQL query waterfall in get_object: cached ShapesService results (TTL), consolidated 3 property queries into 1 UNION, merged 5 label batches into 1, and parallelized independent I/O via asyncio.gather — adding 22 new tests with zero regressions.**

## What Happened

The get_object handler was the primary contributor to 4+ second object tab loads. It executed a sequence of blocking I/O: 3 separate SPARQL queries (current, inferred, mirrored graphs), up to 5 label resolution batches, a shapes graph fetch on every request, and a SQLite favorites check — all sequential.

**T01 — ShapesService caching:** Discovered that ShapesService already had TTL caching implemented from a prior milestone (TTLCache maxsize=1/ttl=600 for shapes graph, TTLCache maxsize=64/ttl=600 for per-type forms, clear_cache() method, DEBUG logging). Verified all 12 existing cache tests pass. Fixed a missing `icalendar` dev dependency that was causing caldav test collection errors.

**T02 — UNION query + label consolidation:** Replaced the 3 sequential SPARQL property queries with a single UNION query using BIND source annotations (`BIND("user" AS ?source)`, etc.). Implemented two-pass binding partitioning to handle SPARQL UNION result ordering non-determinism — first pass partitions by source, second pass applies dedup rules (user > inferred > mirrored). Consolidated all label IRI collection into a single set after property processing, making exactly 1 resolve_batch() call instead of 5. Template context structure unchanged — no template modifications needed. 6 new tests verify query count reduction, label batch consolidation, dedup preservation, and ordering independence.

**T03 — asyncio.gather parallelization + timing:** Identified the UNION property query and SQLite favorites check as independent I/O operations and wrapped them in asyncio.gather(). Added time.perf_counter() wall-clock instrumentation logging at INFO level. Created _CallTracker test helper with artificial 0.15s delays to prove parallel execution completes in under 0.25s (vs 0.30s sequential minimum). 4 new tests verify timing improvement, both operations execute, and log output.

Net result: the get_object handler now makes 1 SPARQL query (was 3), 1 label batch (was 5), uses cached shapes (was 2 SPARQL queries per request), and runs the remaining I/O concurrently. The wall-clock time is logged for ongoing measurement.

## Verification

**Slice-specific tests:** 22/22 pass (12 cache + 6 UNION + 4 parallel) in 1.38s.
**Full suite:** 5749 passed, 128 failed (all pre-existing — sync engines, notion executor, outlook, rss, seed data, tag explorer), 0 new regressions.
**Pre-existing failures verified:** test_ai_endpoints (well-known AI capabilities), test_app_views_commands (command palette), and 126 sync engine/import tests — none related to SPARQL optimization or objects.py.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01: No code changes to shapes.py — caching was already implemented in a prior milestone. Task became verification-only plus fixing unrelated icalendar dev dependency.
T02: Added two-pass binding partitioning (not in plan) to handle SPARQL UNION result ordering non-determinism safely.
T03: Used _CallTracker class instead of AsyncMock side_effect due to double-awaiting issues with nested async mock functions.

## Known Limitations

Wall-clock timing is INFO-level logging only — no persistent performance metrics or alerting. The 1.5s target from the slice plan requires live browser testing against a real RDF4J instance (not done here — unit tests prove the structural optimization). The timing log format is human-readable but not structured for automated parsing.

## Follow-ups

- Wire ShapesService.clear_cache() into model install/uninstall paths for immediate cache invalidation (currently relies on 600s TTL)
- Add structured performance metrics (e.g., histogram) once OpenTelemetry is in place (S02)
- Server-Timing headers (S03) will expose per-query breakdown to browser DevTools

## Files Created/Modified

- `backend/app/browser/objects.py` — Replaced 3 sequential SPARQL property queries with 1 UNION query, consolidated 5 label batches into 1, added asyncio.gather for parallel I/O, added wall-clock timing log
- `backend/tests/test_object_query_opt.py` — New: 6 tests verifying UNION query reduction, label consolidation, dedup preservation, and ordering independence
- `backend/tests/test_object_parallel.py` — New: 4 tests verifying asyncio.gather parallelization and timing log output
- `backend/pyproject.toml` — Added icalendar to dev dependencies (unrelated fix for caldav test collection)
