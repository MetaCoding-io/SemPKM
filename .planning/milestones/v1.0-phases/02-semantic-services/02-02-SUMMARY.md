---
phase: 02-semantic-services
plan: 02
subsystem: api
tags: [shacl, pyshacl, validation, asyncio-queue, rdflib, named-graphs, polling-endpoint]

# Dependency graph
requires:
  - phase: 01-core-data-foundation
    provides: TriplestoreClient, EventStore, FastAPI lifespan, rdflib namespaces
  - phase: 02-semantic-services
    plan: 01
    provides: PrefixRegistry, LabelService, pyshacl dependency installed
provides:
  - ValidationService with pyshacl.validate() via asyncio.to_thread() and report storage as named graphs
  - AsyncValidationQueue with FIFO sequential processing and queue coalescing
  - ValidationReport parser for W3C SHACL reports with three severity tiers
  - GET /api/validation/latest polling endpoint with in-memory cache
  - GET /api/validation/{event_id} per-event report endpoint
  - TriplestoreClient.construct() for SPARQL CONSTRUCT queries
  - Async validation trigger after every command commit (non-blocking)
affects: [03-mental-models, 04-ui-forms, 05-browsing-visualization]

# Tech tracking
tech-stack:
  added: []
  patterns: [async validation queue with coalescing, validation report as named graphs, SPARQL CONSTRUCT for data fetch, in-memory report cache for fast polling]

key-files:
  created:
    - backend/app/validation/__init__.py
    - backend/app/validation/report.py
    - backend/app/validation/queue.py
    - backend/app/validation/router.py
    - backend/app/services/validation.py
  modified:
    - backend/app/triplestore/client.py
    - backend/app/commands/router.py
    - backend/app/main.py
    - backend/app/dependencies.py

key-decisions:
  - "Queue coalescing for rapid edits: drain pending jobs and validate only the latest (full re-validation makes intermediates obsolete)"
  - "In-memory latest_report cache on AsyncValidationQueue for sub-millisecond polling without triplestore hit"
  - "Empty shapes loader returns synthetic conforms=True until Phase 3 provides real SHACL shapes"
  - "Validation reports stored in two locations: full pyshacl report in per-report named graph, summary triples in shared urn:sempkm:validations graph"

patterns-established:
  - "Async background worker pattern: asyncio.Queue + create_task() worker started/stopped in FastAPI lifespan"
  - "Non-blocking post-commit trigger: enqueue() after EventStore.commit() returns, HTTP response unblocked"
  - "Named graph storage for immutable reports: each validation report gets urn:sempkm:validation:{uuid}"
  - "SPARQL CONSTRUCT via construct() method: text/turtle Accept header, rdflib Graph.parse() for results"

requirements-completed: [SHCL-01, SHCL-05]

# Metrics
duration: 5min
completed: 2026-02-21
---

# Phase 2 Plan 2: SHACL Validation Engine Summary

**Async SHACL validation engine with pyshacl, queue coalescing, named graph report storage, and polling endpoints**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-21T19:26:36Z
- **Completed:** 2026-02-21T19:31:33Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- ValidationService running pyshacl.validate() via asyncio.to_thread() with SPARQL CONSTRUCT data fetch and named graph report storage
- AsyncValidationQueue with FIFO sequential processing, queue coalescing (drains pending jobs, validates only latest), and in-memory report cache
- ValidationReport parser extracting W3C SHACL results with three severity tiers (Violation, Warning, Info) and per-property detail
- Every command commit triggers non-blocking async validation via queue enqueue
- Polling endpoints: GET /api/validation/latest (in-memory cache + triplestore fallback) and GET /api/validation/{event_id}
- TriplestoreClient.construct() method for SPARQL CONSTRUCT returning raw Turtle bytes

## Task Commits

Each task was committed atomically:

1. **Task 1: SHACL validation engine with async queue, report parsing, and triplestore CONSTRUCT** - `4371589` (feat)
2. **Task 2: Wire validation into command flow, add polling endpoint, update lifespan** - `b7b7c71` (feat)

## Files Created/Modified
- `backend/app/validation/__init__.py` - Empty package init for validation module
- `backend/app/validation/report.py` - ValidationReport, ValidationResult, ValidationReportSummary dataclasses with from_pyshacl() parser and to_summary_triples() generator
- `backend/app/validation/queue.py` - AsyncValidationQueue with FIFO processing, queue coalescing, and in-memory latest_report cache
- `backend/app/validation/router.py` - GET /api/validation/latest and GET /api/validation/{event_id} endpoints
- `backend/app/services/validation.py` - ValidationService orchestrating CONSTRUCT fetch, pyshacl.validate(), and report storage; empty_shapes_loader default
- `backend/app/triplestore/client.py` - Added construct() method for SPARQL CONSTRUCT queries
- `backend/app/commands/router.py` - Added validation_queue dependency and enqueue() call after commit
- `backend/app/main.py` - Wired ValidationService and AsyncValidationQueue into lifespan startup/shutdown, registered validation router
- `backend/app/dependencies.py` - Added get_validation_queue and get_validation_service dependency functions

## Decisions Made
- Queue coalescing drains pending jobs and validates only the latest, per research Pitfall 4 (rapid edits scenario)
- In-memory latest_report property on AsyncValidationQueue avoids triplestore hit for the common polling case
- Empty shapes loader returns synthetic conforms=True with zero results until Phase 3 installs real SHACL shapes
- Validation reports stored in two named graphs: full pyshacl report in urn:sempkm:validation:{uuid}, summary triples in shared urn:sempkm:validations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Validation engine is complete and triggers on every command commit
- Phase 3 (Mental Models) will provide the real shapes_loader callable to replace empty_shapes_loader
- Polling endpoints ready for Phase 4 UI consumption
- All validation infrastructure testable via curl/API

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 02-semantic-services*
*Completed: 2026-02-21*
