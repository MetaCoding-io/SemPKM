# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** Phase 2: Semantic Services -- Complete. Phase 3 next.

## Current Position

Phase: 3 of 5 (Mental Models)
Plan: 0 of ? in current phase
Status: Phase 2 Complete
Last activity: 2026-02-21 -- Completed 02-02 SHACL Validation Engine

Progress: [███████░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 5min
- Total execution time: 0.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Core Data Foundation | 4 | 23min | 6min |
| 2. Semantic Services | 2 | 9min | 5min |

**Recent Trend:**
- Last 5 plans: 7min, 4min, 4min, 5min
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: RDF4J selected over Blazegraph (unmaintained since 2020) per research findings
- [Roadmap]: Dashboards (DASH-01/02/03), search, inline linking, and filesystem projection deferred to v2 -- not in v1 requirements
- [Roadmap]: 5-phase structure following strict architectural dependency order: triplestore -> semantic services -> Mental Models -> UI/forms -> browsing/visualization
- [01-01]: Host port 8001 for API (8000 occupied by Portainer)
- [01-01]: Config volume mount for RDF4J repo config instead of COPY in Dockerfile
- [01-01]: Sentinel triple pattern to prevent RDF4J empty graph deletion
- [01-02]: Dev volume mount for backend/app source in docker-compose.yml for live code reload
- [01-02]: Raw SPARQL body with Content-Type: application/sparql-update for RDF4J transaction updates
- [01-03]: Fixed EventStore materialization order: deletes before inserts for correct patch semantics
- [01-03]: Added rdflib Variable support to _serialize_rdf_term for SPARQL DELETE WHERE patterns
- [01-04]: FROM clause injection for SPARQL graph scoping (less intrusive than GRAPH clause wrapping)
- [01-04]: Hybrid htmx + vanilla JS for dev console (htmx for health polling, JS for SPARQL results and command dispatch)
- [02-01]: Four-layer prefix precedence: user > model > LOV > built-in (LOV added as separate layer)
- [02-01]: Lazy reverse map caching for compact() with invalidation on any layer mutation
- [02-01]: SPARQL FILTER(LANG() = "" || LANG() = "en") to accept both untagged and language-matched literals
- [02-01]: FROM <urn:sempkm:current> scoping in label SPARQL query for correct graph isolation
- [02-02]: Queue coalescing for rapid edits: drain pending jobs and validate only the latest
- [02-02]: In-memory latest_report cache on AsyncValidationQueue for fast polling
- [02-02]: Empty shapes loader returns synthetic conforms=True until Phase 3 provides real shapes
- [02-02]: Validation reports stored in two named graphs: per-report + shared summary graph

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1 research flag: Event sourcing in RDF triplestores is a novel architecture -- benchmarking strategy needed during planning
- Phase 5 research flag: Cytoscape.js + React integration with SPARQL CONSTRUCT results needs pattern research

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 02-02-PLAN.md (SHACL Validation Engine)
Resume file: None
