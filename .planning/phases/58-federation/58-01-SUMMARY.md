---
phase: 58-federation
plan: 01
subsystem: api
tags: [rdf-patch, federation, event-store, sparql, namespaces]

# Dependency graph
requires:
  - phase: 52-sparql-security
    provides: EventStore with Operation dataclass and materialization
provides:
  - RDF Patch serialization/deserialization (serialize_patch, deserialize_patch)
  - Federation module structure (backend/app/federation/)
  - EventStore target_graph and sync_source parameters
  - Patch export API endpoint with syncSource filtering
  - LDP and AS namespace definitions
affects: [58-02, 58-03, 58-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [N-Triples quad serialization, syncSource loop prevention, graph-targeted materialization]

key-files:
  created:
    - backend/app/federation/__init__.py
    - backend/app/federation/patch.py
    - backend/app/federation/schemas.py
    - backend/app/federation/router.py
  modified:
    - backend/app/rdf/namespaces.py
    - backend/app/events/store.py
    - backend/app/main.py

key-decisions:
  - "RDF Patch _nt() serializer independent from _serialize_rdf_term() -- N-Triples format vs SPARQL format"
  - "BNodes skolemized to urn:skolem:{id} for cross-instance stability in patch serialization"
  - "Export endpoint treats all event data triples as inserts (event graph stores new state)"

patterns-established:
  - "Federation module: backend/app/federation/ with patch.py, schemas.py, router.py"
  - "Graph-targeted EventStore: target_graph parameter overrides CURRENT_GRAPH_IRI"
  - "SyncSource tagging: sempkm:syncSource predicate on events from remote origins"

requirements-completed: [FED-01, FED-02, FED-05]

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 58 Plan 01: RDF Patch & Event Sync Foundation Summary

**RDF Patch serialization with N-Triples quad format, EventStore graph targeting and syncSource loop prevention, and patch export API endpoint**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T01:14:04Z
- **Completed:** 2026-03-11T01:19:46Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- RDF Patch serialization converts Operations to spec-compliant A/D line format with quad graph component
- EventStore.commit() extended with target_graph and sync_source parameters (fully backward-compatible)
- GET /api/federation/patches/{graph_id} exports patches with syncSource anti-loop filtering
- LDP and AS namespaces registered in COMMON_PREFIXES for federation use

## Task Commits

Each task was committed atomically:

1. **Task 1: RDF Patch serialization, namespace extensions, EventStore graph targeting** - `241c387` (feat)
2. **Task 2: Patch export API endpoint with syncSource filtering** - `ed51e02` (feat)

_Note: Task 1 followed TDD cycle (RED: verified modules missing, GREEN: implemented and verified)_

## Files Created/Modified
- `backend/app/federation/__init__.py` - Federation module init
- `backend/app/federation/patch.py` - RDF Patch serialize/deserialize with _nt() N-Triples serializer
- `backend/app/federation/schemas.py` - PatchExportResponse and SharedGraphInfo Pydantic models
- `backend/app/federation/router.py` - GET /api/federation/patches/{graph_id} with SPARQL query and syncSource filter
- `backend/app/rdf/namespaces.py` - Added LDP, AS namespaces and COMMON_PREFIXES entries
- `backend/app/events/store.py` - Extended commit() with target_graph, sync_source params; adds sempkm:syncSource and sempkm:graphTarget triples
- `backend/app/main.py` - Registered federation_router

## Decisions Made
- RDF Patch `_nt()` function is separate from `_serialize_rdf_term()` in events/store.py because they serve different purposes: N-Triples format (angle brackets, no Variable support) vs SPARQL format (Variable as ?var, BNode as _:id)
- BNodes are skolemized to `urn:skolem:{id}` URIs in patch serialization to ensure cross-instance stability (RDF Patch requires stable identifiers)
- Export endpoint treats all non-metadata triples from event graphs as inserts, since event graphs store the "new state" snapshot

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Federation module structure established for Plans 02-04 to build on
- EventStore extensions ready for sync import (Plan 02) with graph targeting and syncSource tagging
- Patch export API ready for remote pull requests once HTTP Signature auth is added (Plan 03)

## Self-Check: PASSED

- All 7 files verified present on disk
- Both task commits (241c387, ed51e02) verified in git log

---
*Phase: 58-federation*
*Completed: 2026-03-11*
