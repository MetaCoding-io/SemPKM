# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** Phase 5: Data Browsing and Visualization -- In Progress.

## Current Position

Phase: 5 of 6 (Data Browsing and Visualization)
Plan: 3 of 3 in current phase
Status: Plan 05-03 Complete -- Graph View and Workspace Integration
Last activity: 2026-02-22 -- Completed 05-03 Graph View and Workspace Integration

Progress: [███████████████████] 95%

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: 5min
- Total execution time: 1.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Core Data Foundation | 4 | 23min | 6min |
| 2. Semantic Services | 2 | 9min | 5min |
| 3. Mental Model System | 3 | 24min | 8min |
| 4. Admin Shell and Object Creation | 4 | 19min | 5min |
| 5. Data Browsing and Visualization | 2 | 11min | 6min |
| 6. User and Team Management | 3 | 16min | 5min |

**Recent Trend:**
- Last 5 plans: 8min, 3min, 5min, 4min, 6min
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
- [03-01]: Copied _rdf_term_to_sparql into registry.py to avoid cross-module coupling between models and services
- [03-01]: Remote @context URL detection reads raw JSON before rdflib parsing to prevent Docker fetch failures
- [03-01]: Triple-by-triple SPARQL INSERT DATA serialization (not N-Triples) per Research Pitfall 2
- [03-02]: All JSON-LD uses inline @context only — no remote URLs for Docker compatibility
- [03-02]: Standard vocabularies (FOAF, DC, Schema.org, SKOS) for well-known properties; bpkm: for model-specific
- [03-02]: SPARQL queries in view specs use full IRIs since stored as string literals
- [03-02]: Seed data uses bpkm:seed- prefixed IRIs to distinguish from user data
- [03-03]: Seed data materialized via EventStore.commit() outside model graph transaction for event sourcing consistency
- [03-03]: Starter model path hardcoded to /app/models/basic-pkm (container mount path)
- [03-03]: Seed materialization failure treated as warning, not install failure
- [04-01]: Jinja2Blocks configured at module level in main.py, stored on app.state.templates for router access
- [04-01]: Shell router included LAST after API routers so /api/* routes take precedence
- [04-01]: Sidebar uses fixed positioning with 220px width, responsive collapse to icons at 768px
- [04-01]: Active nav link highlighting via JS listening to htmx:pushedIntoHistory events
- [04-02]: ShapesService fetches entire shapes graph via CONSTRUCT then traverses with rdflib Python API, not complex SPARQL
- [04-02]: WebhookService uses delete-all/re-insert pattern for atomic updates
- [04-02]: Command-to-event mapping: object.create/patch/body.set -> object.changed, edge.create/patch -> edge.changed
- [04-02]: validation.completed webhook deferred to future queue callback mechanism
- [06-01]: String(20) for role columns instead of Enum to avoid SQLite/PostgreSQL dialect differences
- [06-01]: render_as_batch=True in Alembic env.py for SQLite ALTER Table compatibility
- [06-01]: RDF4J port removed from Docker Compose host mapping (security hardening)
- [06-01]: Auto-generated secret key path persisted to data volume
- [06-02]: Naive UTC datetimes (_utcnow helper) for SQLite datetime comparison compatibility
- [06-02]: Setup token is random secrets.token_urlsafe, not signed -- stored on disk, string-compared
- [06-02]: Logout revokes session in DB via token deletion, not just cookie clearing
- [06-02]: Magic link verify auto-creates member user for passwordless first-login
- [04-03]: Admin router uses named Jinja2 blocks (model_table, webhook_list) for htmx partial swap targets
- [04-03]: Webhook event types defined as constant list in router for template checkbox rendering
- [04-03]: Admin router included before shell router so /admin/* routes take precedence
- [04-04]: Browser router registered before shell router; /browser/ endpoint moved from shell to browser router
- [04-04]: Tab state managed entirely client-side in sessionStorage per research anti-pattern guidance
- [04-04]: Split.js sizes persisted in localStorage for cross-session pane size persistence
- [04-04]: Command palette entries added dynamically as tree children load via htmx:afterSwap listener
- [04-04]: Nav tree uses Jinja2 include for reusable template; tree children loaded lazily via htmx GET
- [06-03]: EVENT_PERFORMED_BY optional in EventStore.commit() for backward compatibility with system operations
- [06-03]: User IRI constructed as urn:sempkm:user:{uuid} by calling router, not by EventStore
- [05-01]: SPARQL WHERE clause extraction via regex brace-depth counting for count query and pagination recomposition
- [05-01]: Table rows deduplicated by ?s to handle OPTIONAL cross-product results per Research Pitfall 5
- [05-01]: Views router prefix /browser/views included before browser_router for route specificity
- [05-03]: Separate JSON data endpoint for graph view (/data suffix) -- Cytoscape.js requires visible container before init
- [05-03]: Tableau 10 palette for auto-assigned node colors via type IRI hash, with model sempkm:nodeColor override
- [05-03]: View tabs use view: prefix namespace in sessionStorage to prevent collision with object IRI keys
- [05-03]: View toolbar hides filter input for graph views since graph shows full CONSTRUCT results

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 6 added: User and team management for multi-tenant cloud readiness

### Blockers/Concerns

- Phase 1 research flag: Event sourcing in RDF triplestores is a novel architecture -- benchmarking strategy needed during planning
- Phase 5 research flag: Cytoscape.js + React integration with SPARQL CONSTRUCT results needs pattern research

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 05-03-PLAN.md (Graph View and Workspace Integration)
Resume file: None
