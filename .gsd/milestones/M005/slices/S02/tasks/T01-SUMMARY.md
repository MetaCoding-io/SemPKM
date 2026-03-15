---
id: T01
parent: S02
milestone: M005
provides:
  - OperationsLogService with log_activity(), list_activities(), get_activity(), count_activities()
  - PROV-O vocabulary constants for ops logging
  - Unit test suite validating SPARQL generation
key_files:
  - backend/app/services/ops_log.py
  - backend/tests/test_ops_log.py
key_decisions:
  - Used raw IRI strings (not rdflib Namespace objects) matching QueryService pattern
  - SYSTEM_ACTOR_IRI defined locally as string "urn:sempkm:system" rather than importing URIRef from events/models.py (service uses raw strings, not rdflib)
  - Activity IRI pattern is urn:sempkm:ops-log:{uuid} — separates ops log resources from event store resources
patterns_established:
  - OperationsLogService follows QueryService pattern exactly — raw SPARQL, _esc(), _now_iso(), TriplestoreClient
  - Cursor-based pagination via FILTER(?startedAt < cursor) + LIMIT N+1 for next-page detection
  - _binding_to_dict() static method for SPARQL JSON binding → Python dict conversion
observability_surfaces:
  - logger.info("Logged ops activity: %s") on every successful log_activity() call
  - All data queryable via SPARQL against urn:sempkm:ops-log named graph
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Build OperationsLogService with unit tests

**Created OperationsLogService with 4 methods and 35 passing unit tests covering SPARQL generation, escaping, pagination, and result parsing.**

## What Happened

Built `backend/app/services/ops_log.py` following the QueryService pattern from `query_service.py`. The service has:

- `log_activity()` — builds SPARQL INSERT DATA with prov:Activity type, PROV-O timestamps, actor association, optional prov:used, optional status/error triples. Defaults actor to `urn:sempkm:system`.
- `list_activities()` — cursor-paginated SELECT with optional activity_type filter. Uses LIMIT N+1 pattern to detect next page.
- `get_activity()` — single-resource SELECT by IRI. Collects prov:used IRIs from multiple result rows.
- `count_activities()` — SELECT COUNT with optional type filter.

All methods use raw SPARQL strings with `_esc()` for safe literal inclusion, `_now_iso()` for timestamps, and `_dt()` for xsd:dateTime typed literals.

Unit tests mock TriplestoreClient and assert on the SPARQL strings passed to `update()`/`query()`.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_ops_log.py -v` — **35/35 tests pass**
- Escaping tests: backslash, single quote, newline, tab, carriage return, combined, plain string
- INSERT DATA strings all contain `GRAPH <urn:sempkm:ops-log>` wrapper
- Cursor filter construction verified for timestamp-based pagination
- Activity type filter, limit+1, next-cursor detection all covered

### Slice-level verification status (T01 is first of 3 tasks):
- ✅ `backend/tests/test_ops_log.py` — unit tests pass (35/35)
- ⬜ Docker stack browser verification — not yet (T03)
- ⬜ `grep -rn "ops_log"` instrumentation — not yet (T02)

## Diagnostics

- All ops log data lives in named graph `urn:sempkm:ops-log` — queryable via SPARQL console
- Each `log_activity()` call emits `INFO "Logged ops activity: {type}"` to Python logger
- Service raises on triplestore errors — callers implement fire-and-forget wrapping

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/ops_log.py` — new; complete OperationsLogService with 4 methods
- `backend/tests/test_ops_log.py` — new; 35 unit tests covering SPARQL generation, escaping, pagination, result parsing
- `.gsd/milestones/M005/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section
