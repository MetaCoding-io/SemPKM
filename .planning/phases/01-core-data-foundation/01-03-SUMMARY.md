---
phase: 01-core-data-foundation
plan: 03
subsystem: api
tags: [pydantic, discriminated-union, command-api, fastapi, rdf-triples, batch-commands, event-sourcing]

# Dependency graph
requires:
  - phase: 01-core-data-foundation/02
    provides: EventStore.commit() with Operation dataclass, IRI minting, SEMPKM namespace
provides:
  - Pydantic discriminated union for 5 command types (object.create, object.patch, body.set, edge.create, edge.patch)
  - Command dispatcher routing command strings to async handler functions
  - POST /api/commands endpoint accepting single and batch (array) payloads
  - All-or-nothing batch semantics via single EventStore.commit() call
  - Compact IRI resolution for property predicates (rdfs:label, schema:name, etc.)
  - Custom exception hierarchy mapping to HTTP status codes
affects: [01-04, phase-2-shacl, phase-3-mental-models, all-write-operations]

# Tech tracking
tech-stack:
  added: []
  patterns: [discriminated-union-dispatch, compact-iri-resolution, single-endpoint-rpc, batch-atomic-commands]

key-files:
  created:
    - backend/app/commands/__init__.py
    - backend/app/commands/schemas.py
    - backend/app/commands/dispatcher.py
    - backend/app/commands/exceptions.py
    - backend/app/commands/handlers/__init__.py
    - backend/app/commands/handlers/object_create.py
    - backend/app/commands/handlers/object_patch.py
    - backend/app/commands/handlers/body_set.py
    - backend/app/commands/handlers/edge_create.py
    - backend/app/commands/handlers/edge_patch.py
    - backend/app/commands/router.py
  modified:
    - backend/app/main.py
    - backend/app/events/store.py

key-decisions:
  - "Fixed EventStore materialization order: deletes before inserts to prevent variable patterns from matching newly-inserted values"
  - "Added rdflib Variable support to _serialize_rdf_term for SPARQL DELETE WHERE patterns"

patterns-established:
  - "Compact IRI resolution via COMMON_PREFIXES dict for predicate strings (rdfs:label -> full IRI)"
  - "Handler pattern: async function taking (params, base_namespace) returning Operation dataclass"
  - "Router accepts raw JSON body, parses as single command or list for batch support"
  - "Dispatcher uses lazy handler registration to avoid circular imports"

requirements-completed: [CORE-05]

# Metrics
duration: 7min
completed: 2026-02-21
---

# Phase 1 Plan 03: Command API Summary

**Pydantic discriminated union command dispatch with 5 handlers (object.create, object.patch, body.set, edge.create, edge.patch) and atomic batch POST /api/commands endpoint**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-21T08:54:04Z
- **Completed:** 2026-02-21T09:01:25Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Pydantic v2 discriminated union correctly routes all 5 command types via the `command` field discriminator
- POST /api/commands accepts both single command objects and batch arrays, normalizing to list internally
- All 5 command handlers produce correct RDF triples with compact IRI resolution for predicates
- Batch commands share a single event graph and execute atomically (all-or-nothing)
- Edges are first-class resources with own IRIs per user decision (sempkm:source, sempkm:target, sempkm:predicate)
- Error responses use Pydantic validation messages for invalid commands and proper HTTP status codes

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic command schemas and dispatcher** - `c0dacc0` (feat)
2. **Task 2: Command handlers and POST /api/commands endpoint** - `6f3d2c3` (feat)

## Files Created/Modified
- `backend/app/commands/__init__.py` - Commands package init
- `backend/app/commands/schemas.py` - Pydantic models: 5 param models, 5 command models, discriminated Command union, CommandResult, CommandResponse
- `backend/app/commands/dispatcher.py` - HANDLER_REGISTRY and dispatch() function with lazy handler import
- `backend/app/commands/exceptions.py` - CommandError, ObjectNotFoundError, InvalidCommandError, ConflictError
- `backend/app/commands/handlers/__init__.py` - Handlers package init
- `backend/app/commands/handlers/object_create.py` - Mint IRI, build type + property triples, compact IRI resolution
- `backend/app/commands/handlers/object_patch.py` - Delete/insert patterns for property updates using Variables
- `backend/app/commands/handlers/body_set.py` - Set sempkm:body with xsd:string datatype
- `backend/app/commands/handlers/edge_create.py` - Mint edge IRI, build source/target/predicate + annotation triples
- `backend/app/commands/handlers/edge_patch.py` - Update edge annotations (source/target/predicate immutable)
- `backend/app/commands/router.py` - POST /api/commands accepting single/batch, dispatching, committing via EventStore
- `backend/app/main.py` - Registered commands_router on the FastAPI app
- `backend/app/events/store.py` - Fixed materialization order (deletes before inserts), added Variable support

## Decisions Made
- Fixed EventStore materialization order to delete-before-insert. The original insert-then-delete order caused Variable-based delete patterns (like `?old_0`) to match newly-inserted values, effectively deleting the update. This is a correctness fix for any patch/update operation.
- Added rdflib Variable to the `_serialize_rdf_term` function since command handlers use Variables in materialize_deletes patterns for SPARQL DELETE WHERE queries.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed EventStore materialization order: deletes before inserts**
- **Found during:** Task 2 (object.patch verification via curl)
- **Issue:** `EventStore.commit()` performed INSERT DATA before DELETE WHERE. For patch operations, Variable patterns like `?old_0` matched both the old value AND the just-inserted new value, deleting both.
- **Fix:** Reversed materialization order: deletes execute first, then inserts. This ensures Variables only match pre-existing values.
- **Files modified:** backend/app/events/store.py
- **Verification:** object.patch now correctly updates values; "Alice Jones" persists in current state graph after patch
- **Committed in:** 6f3d2c3 (Task 2 commit)

**2. [Rule 3 - Blocking] Added Variable support to _serialize_rdf_term**
- **Found during:** Task 2 (handler implementation)
- **Issue:** `_serialize_rdf_term()` only handled URIRef, Literal, and BNode. Command handlers use `rdflib.Variable` in materialize_deletes patterns, which would raise ValueError.
- **Fix:** Added Variable check as first branch in _serialize_rdf_term, serializing as `?varname`.
- **Files modified:** backend/app/events/store.py
- **Verification:** DELETE WHERE queries correctly use `?old_0` syntax for variable patterns
- **Committed in:** 6f3d2c3 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correct operation of patch/update commands. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Command API fully functional: all 5 command types work through POST /api/commands
- Ready for Plan 01-04: SPARQL read endpoint and dev console
- EventStore correctly handles all operation types (create with inserts only, patch/set with deletes + inserts)
- Compact IRI resolution available for future use in query endpoints and UI

## Self-Check: PASSED

All 11 created files verified present. Both task commits (c0dacc0, 6f3d2c3) verified in git log.

---
*Phase: 01-core-data-foundation*
*Completed: 2026-02-21*
