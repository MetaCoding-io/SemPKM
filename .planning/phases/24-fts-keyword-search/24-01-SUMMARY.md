---
phase: 24-fts-keyword-search
plan: 01
subsystem: search
tags: [lucene, rdf4j, lucene-sail, fts, sparql, full-text-search]

# Dependency graph
requires: []
provides:
  - LuceneSail-wrapped NativeStore repository config in sempkm-repo.ttl
  - lucene_index Docker volume for persistent Lucene index at /var/rdf4j/lucene
  - SearchService class with search() async method returning list[SearchResult]
  - get_search_service FastAPI dependency injection function
affects: [24-02, 28]

# Tech tracking
tech-stack:
  added: [rdf4j-sail-lucene-5.0.1, lucene-core-8.9.0]
  patterns: [LuceneSail SPARQL magic predicate search:matches, graph-scoped FTS]

key-files:
  created:
    - backend/app/services/search.py
  modified:
    - config/rdf4j/sempkm-repo.ttl
    - docker-compose.yml
    - backend/app/dependencies.py
    - backend/app/main.py

key-decisions:
  - "Used RDF4J 5.x unified namespace config properties (config:lucene.indexDir, config:delegate) verified against actual container-generated config"
  - "Omitted reindexQuery from LuceneSail config — not a supported RDF4J 5.x config property; graph scoping done at query time via GRAPH clause"
  - "Used absolute path /var/rdf4j/lucene for Lucene index directory with separate Docker named volume"

patterns-established:
  - "LuceneSail FTS pattern: SPARQL search:matches with search:query, search:score, search:snippet predicates"
  - "Graph-scoped FTS: Wrap search:matches in GRAPH <urn:sempkm:current> to exclude event graphs"
  - "Reindex existing data after LuceneSail activation: export graph, clear, reimport (LuceneSail only indexes at write time)"

requirements-completed: [FTS-01]

# Metrics
duration: 11min
completed: 2026-03-01
---

# Phase 24 Plan 01: LuceneSail FTS Configuration + SearchService Summary

**RDF4J LuceneSail wrapping NativeStore with persistent Docker volume and SearchService returning scored FTS results via SPARQL magic predicates**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-01T05:21:00Z
- **Completed:** 2026-03-01T05:32:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Verified LuceneSail JAR (rdf4j-sail-lucene-5.0.1.jar) and Lucene core JAR (lucene-core-8.9.0.jar) present in eclipse/rdf4j-workbench:5.0.1 container
- Configured sempkm-repo.ttl with LuceneSail wrapping NativeStore using RDF4J 5.x unified namespace config properties
- Added lucene_index named Docker volume mounted at /var/rdf4j/lucene
- Implemented SearchService with SPARQL FTS query scoped to urn:sempkm:current graph
- Reindexed existing data (91 triples) via export-clear-reimport cycle; verified FTS returns scored results

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify LuceneSail JAR and configure sempkm-repo.ttl + Docker volume** - `ec77053` (feat)
2. **Task 2: Implement SearchService and wire dependency injection** - `d2a5d03` (feat)

## Files Created/Modified
- `config/rdf4j/sempkm-repo.ttl` - LuceneSail-wrapped NativeStore repo config with delegate pattern
- `docker-compose.yml` - Added lucene_index named volume and mount at /var/rdf4j/lucene on triplestore service
- `backend/app/services/search.py` - SearchService class with FTS_QUERY SPARQL template and SearchResult dataclass
- `backend/app/dependencies.py` - Added get_search_service dependency injection function
- `backend/app/main.py` - Wire SearchService instantiation into lifespan, stored as app.state.search_service

## LuceneSail Configuration Details

**JAR files confirmed present:**
- `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/rdf4j-sail-lucene-5.0.1.jar`
- `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/rdf4j-sail-lucene-api-5.0.1.jar`
- `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/lucene-core-8.9.0.jar`

**Actual Turtle property names used (verified from container-generated config):**
- `config:sail.type "openrdf:LuceneSail"` — sail type identifier
- `config:lucene.indexDir "/var/rdf4j/lucene"` — absolute path to Lucene index
- `config:delegate [...]` — wraps NativeStore as delegate sail

**reindexQuery:** Omitted. Not a supported RDF4J 5.x config property. The plan's template used `lucene:reindexQuery` but the actual RDF4J 5.x LuceneSail config namespace is `tag:rdf4j.org,2023:config/` with `config:lucene.*` properties. Graph scoping is done at SPARQL query time via `GRAPH <urn:sempkm:current>`.

**SearchService SPARQL pattern:** Uses `search:matches` magic predicate with `search:query`, `search:score`, and `search:snippet` sub-predicates. Results deduplicated by IRI with label resolution across dcterms:title, rdfs:label, skos:prefLabel, schema:name, foaf:name.

## Decisions Made
- Used RDF4J 5.x unified namespace config properties (config:lucene.indexDir, config:delegate) verified by creating a test LuceneSail repo through the workbench and inspecting the generated config.ttl
- Omitted reindexQuery from config (not a standard RDF4J 5.x config property); graph scoping is done at SPARQL query time
- Used absolute path /var/rdf4j/lucene for Lucene index directory backed by a separate Docker named volume for persistence
- Performed export-clear-reimport of urn:sempkm:current graph to populate Lucene index with existing data (LuceneSail only indexes at write time)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] LuceneSail config property names differed from plan template**
- **Found during:** Task 1 (Step B - Update sempkm-repo.ttl)
- **Issue:** Plan used `lucene:indexDir` with a separate `lucene:` prefix namespace, but RDF4J 5.x uses `config:lucene.indexDir` under the unified `tag:rdf4j.org,2023:config/` namespace
- **Fix:** Created test LuceneSail repo via workbench, inspected generated config.ttl, used exact property names from container
- **Files modified:** config/rdf4j/sempkm-repo.ttl
- **Verification:** Triplestore restarted and repo recreated with correct LuceneSail config
- **Committed in:** ec77053

**2. [Rule 3 - Blocking] Stale repo lock after restart prevented API startup**
- **Found during:** Task 1 (Step D - Restart to apply config)
- **Issue:** `docker compose restart` left stale lock file causing RepositoryLockedException, preventing API startup
- **Fix:** Full `docker compose down && docker compose up -d` to clear all locks
- **Files modified:** None (operational fix)
- **Verification:** API started successfully, health check passed

**3. [Rule 3 - Blocking] Existing data not in Lucene index after LuceneSail activation**
- **Found during:** Task 1 verification
- **Issue:** LuceneSail only indexes data at write time; 91 existing triples written before LuceneSail activation were not indexed
- **Fix:** Exported urn:sempkm:current graph as N-Quads, cleared graph, reimported — triggering Lucene indexing of all triples
- **Files modified:** None (data operation)
- **Verification:** FTS query for "knowledge" returns 5 hits across persons, projects, concepts

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All auto-fixes necessary for correct LuceneSail operation. No scope creep.

## Issues Encountered
- RDF4J LuceneSail `search:reindex "true"` magic triple did not trigger full reindex in RDF4J 5.0.1 — used export-clear-reimport as workaround
- `docker compose restart` for triplestore can leave stale repository locks; full stop-start cycle required for clean state

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SearchService is wired and available via `get_search_service` dependency injection
- LuceneSail indexes all new writes automatically
- Ready for Plan 24-02 to add the search API endpoint and UI components
- Note: After any bulk data import that bypasses the API, a reindex via export-clear-reimport of the current graph may be needed

## Self-Check: PASSED

- All created files verified present on disk
- Both task commits (ec77053, d2a5d03) verified in git log

---
*Phase: 24-fts-keyword-search*
*Completed: 2026-03-01*
