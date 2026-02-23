---
phase: 01-core-data-foundation
plan: 02
subsystem: rdf
tags: [rdflib, namespaces, iri-minting, jsonld, event-sourcing, named-graphs, sparql-update, transactions]

# Dependency graph
requires:
  - phase: 01-core-data-foundation/01
    provides: TriplestoreClient with async SPARQL query/update and transaction support
provides:
  - SEMPKM namespace definitions (urn:sempkm:) and standard RDF vocabulary re-exports
  - IRI minting functions (mint_object_iri, mint_edge_iri, mint_event_iri)
  - JSON-LD serialization with SemPKM context (graph_to_jsonld, triples_to_jsonld)
  - EventStore.commit() for atomic event graph creation + current state materialization
  - Operation dataclass for bundling write operations
  - SPARQL builder helpers for INSERT DATA, DELETE WHERE, DELETE/INSERT/WHERE
affects: [01-03, 01-04, all-command-handlers]

# Tech tracking
tech-stack:
  added: []
  patterns: [event-sourcing-named-graphs, immutable-event-graphs, eager-materialization, atomic-event-state-transaction]

key-files:
  created:
    - backend/app/rdf/__init__.py
    - backend/app/rdf/namespaces.py
    - backend/app/rdf/iri.py
    - backend/app/rdf/jsonld.py
    - backend/app/events/__init__.py
    - backend/app/events/models.py
    - backend/app/events/store.py
  modified:
    - backend/app/triplestore/client.py
    - docker-compose.yml

key-decisions:
  - "Dev volume mount for backend/app source in docker-compose.yml for live code reload"
  - "Raw SPARQL body with Content-Type: application/sparql-update for RDF4J transaction updates (not form-encoded)"

patterns-established:
  - "EventStore.commit() wraps event creation + materialization in single RDF4J transaction"
  - "Operation dataclass separates event data triples from materialization actions"
  - "SPARQL INSERT DATA with GRAPH clause for scoped named graph writes"
  - "IRI minting: {namespace}/{Type}/{slug-or-uuid} for objects, {namespace}/Edge/{uuid} for edges, urn:sempkm:event:{uuid} for events"

requirements-completed: [CORE-01, CORE-02]

# Metrics
duration: 5min
completed: 2026-02-21
---

# Phase 1 Plan 02: Event Store and RDF Core Summary

**RDF namespace/IRI/JSON-LD utilities and event-sourcing engine with immutable named graphs and atomic current state materialization via RDF4J transactions**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-21T08:44:48Z
- **Completed:** 2026-02-21T08:50:06Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- RDF core utilities: SEMPKM namespace, standard vocab re-exports, CURRENT_GRAPH_IRI, COMMON_PREFIXES
- IRI minting with configurable namespace: object IRIs (slug/UUID), edge IRIs (UUID), event IRIs (URN)
- JSON-LD serialization with local SemPKM context (7 prefixes, never references external URLs)
- EventStore.commit() atomically creates immutable event named graph and materializes current state in single RDF4J transaction
- Batch operations support: multiple Operations produce one event graph with combined metadata
- Full integration test against running RDF4J triplestore confirms event graphs, current state, and graph isolation

## Task Commits

Each task was committed atomically:

1. **Task 1: RDF namespace definitions, IRI minting, and JSON-LD utilities** - `dfcd02b` (feat)
2. **Task 2: Event store with immutable event graphs and eager current state materialization** - `7e3b281` (feat)

## Files Created/Modified
- `backend/app/rdf/__init__.py` - RDF package init
- `backend/app/rdf/namespaces.py` - SEMPKM, DATA, SCHEMA namespaces, CURRENT_GRAPH_IRI, COMMON_PREFIXES
- `backend/app/rdf/iri.py` - mint_object_iri, mint_edge_iri, mint_event_iri functions
- `backend/app/rdf/jsonld.py` - SEMPKM_CONTEXT, graph_to_jsonld, triples_to_jsonld
- `backend/app/events/__init__.py` - Events package init
- `backend/app/events/models.py` - Event vocabulary constants (EVENT_TYPE, EVENT_TIMESTAMP, etc.)
- `backend/app/events/store.py` - EventStore class with commit(), Operation/EventResult dataclasses, SPARQL builders
- `backend/app/triplestore/client.py` - Fixed transaction_update to use raw SPARQL with Content-Type header
- `docker-compose.yml` - Added dev volume mount for backend/app source

## Decisions Made
- Added `./backend/app:/app/app:ro` volume mount to docker-compose.yml so code changes are reflected immediately without rebuilding the Docker image. This is a standard development workflow pattern.
- Fixed TriplestoreClient.transaction_update to send raw SPARQL body with `Content-Type: application/sparql-update` instead of form-encoded data. RDF4J transaction endpoints require this format (unlike the non-transactional statements endpoint which accepts form-encoded).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed RDF4J transaction update content type**
- **Found during:** Task 2 (EventStore integration test)
- **Issue:** TriplestoreClient.transaction_update used form-encoded data which RDF4J transaction endpoints reject with 406 (Not Acceptable). The error message was "Could not read SPARQL update string from body."
- **Fix:** Changed to raw SPARQL body with `Content-Type: application/sparql-update` header, matching the RDF4J REST API specification for transaction-scoped updates.
- **Files modified:** backend/app/triplestore/client.py
- **Verification:** EventStore integration test passes, event graphs and current state correctly created
- **Committed in:** 7e3b281 (Task 2 commit)

**2. [Rule 3 - Blocking] Added dev volume mount for backend source code**
- **Found during:** Task 1 (verification)
- **Issue:** Docker container had stale code because backend source is baked into the image at build time; new rdf/ and events/ directories were not visible inside the container.
- **Fix:** Added `./backend/app:/app/app:ro` volume mount to the api service in docker-compose.yml for live code access during development.
- **Files modified:** docker-compose.yml
- **Verification:** All imports and tests work inside the running container without rebuild
- **Committed in:** dfcd02b (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correct operation. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RDF core utilities (namespaces, IRI minting, JSON-LD) ready for use by command handlers in Plan 01-03
- EventStore ready to receive Operations from command handlers (object.create, object.patch, etc.)
- Operation dataclass provides clean interface for command handlers to specify data triples and materialization actions
- SPARQL builder helpers available for constructing complex update patterns
- Ready for Plan 01-03: Command API (Pydantic schemas, dispatcher, 5 command handlers)

## Self-Check: PASSED

All 9 created/modified files verified present. Both task commits (dfcd02b, 7e3b281) verified in git log.

---
*Phase: 01-core-data-foundation*
*Completed: 2026-02-21*
