---
phase: 02-semantic-services
plan: 01
subsystem: api
tags: [prefix-registry, label-resolution, sparql-coalesce, ttl-cache, cachetools, pyshacl, rdflib, lov]

# Dependency graph
requires:
  - phase: 01-core-data-foundation
    provides: TriplestoreClient, FastAPI lifespan, COMMON_PREFIXES, rdflib namespaces
provides:
  - PrefixRegistry with three-layer bidirectional prefix lookup (user > model > LOV > built-in)
  - LabelService with SPARQL COALESCE batch resolution and TTLCache
  - FastAPI dependency injection for PrefixRegistry and LabelService
  - LOV REST API import method for vocabulary prefix discovery
  - pyshacl and cachetools dependencies installed
affects: [03-mental-models, 04-ui-forms, 05-browsing-visualization]

# Tech tracking
tech-stack:
  added: [pyshacl 0.31.0, cachetools 7.0.1]
  patterns: [three-layer prefix registry, SPARQL COALESCE batch label resolution, TTLCache with explicit invalidation, language-aware FILTER]

key-files:
  created:
    - backend/app/services/__init__.py
    - backend/app/services/prefixes.py
    - backend/app/services/labels.py
  modified:
    - backend/pyproject.toml
    - backend/app/rdf/namespaces.py
    - backend/app/dependencies.py
    - backend/app/main.py

key-decisions:
  - "Four-layer prefix precedence: user > model > LOV > built-in (LOV added as separate layer below model)"
  - "Lazy reverse map caching for compact() with invalidation on any layer mutation"
  - "SPARQL FILTER(LANG() = '' || LANG() = 'en') to accept both untagged and language-matched literals"
  - "FROM <urn:sempkm:current> scoping in label SPARQL query for correct graph isolation"

patterns-established:
  - "Three-layer service pattern: services/ module with PrefixRegistry and LabelService as app.state singletons"
  - "SPARQL COALESCE batch resolution: VALUES clause + OPTIONAL + COALESCE for precedence chain"
  - "TTLCache invalidation: explicit invalidate(iris) after writes for consistency"

requirements-completed: [INFR-01, INFR-02]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 2 Plan 1: Prefix Registry and Label Resolution Summary

**Three-layer PrefixRegistry with bidirectional expand/compact and LabelService with SPARQL COALESCE batch resolution, TTLCache, and language-aware filtering**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T19:18:41Z
- **Completed:** 2026-02-21T19:23:19Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- PrefixRegistry with 11 built-in prefixes and four-layer precedence (user > model > LOV > built-in) with lazy reverse map caching
- LabelService resolving IRIs via SPARQL COALESCE batch queries with TTLCache (5min TTL, 4096 max) and language-aware FILTER
- IRI fallback chain: dcterms:title > rdfs:label > skos:prefLabel > schema:name > QName > truncated IRI
- FastAPI dependency injection for both services, wired into app lifespan
- Updated COMMON_PREFIXES with OWL, SH, FOAF, PROV namespace exports

## Task Commits

Each task was committed atomically:

1. **Task 1: PrefixRegistry with three-layer lookup, bidirectional expansion/compaction, and LOV import** - `4bab9b1` (feat)
2. **Task 2: LabelService with SPARQL COALESCE batch resolution, TTLCache, language preferences, and FastAPI wiring** - `6a69719` (feat)

## Files Created/Modified
- `backend/app/services/__init__.py` - Empty package init for services module
- `backend/app/services/prefixes.py` - PrefixRegistry class with BUILTIN dict, three instance layers, expand/compact, LOV import
- `backend/app/services/labels.py` - LabelService class with SPARQL COALESCE batch query, TTLCache, language prefs, IRI fallback
- `backend/pyproject.toml` - Added pyshacl>=0.31.0 and cachetools>=7.0 dependencies
- `backend/app/rdf/namespaces.py` - Added OWL, SH, FOAF, PROV imports and COMMON_PREFIXES entries
- `backend/app/dependencies.py` - Added get_prefix_registry and get_label_service dependency functions
- `backend/app/main.py` - Wired PrefixRegistry and LabelService creation into lifespan startup

## Decisions Made
- Added LOV as a fourth precedence layer (below model, above built-in) rather than merging LOV into built-in, keeping the separation clean for future re-sync
- Used lazy reverse map caching (built on first compact() call, invalidated on mutation) rather than eager rebuild for efficiency
- Used FILTER(LANG() = "" || LANG() = "en") pattern from research Pitfall 6 to handle both untagged and language-tagged literals
- Scoped label SPARQL query to FROM <urn:sempkm:current> for correct graph isolation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PrefixRegistry and LabelService are available via FastAPI dependency injection for all downstream phases
- pyshacl 0.31.0 is installed, ready for Plan 02 (SHACL validation engine)
- All 11 standard vocabulary prefixes registered and round-trip verified

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 02-semantic-services*
*Completed: 2026-02-21*
