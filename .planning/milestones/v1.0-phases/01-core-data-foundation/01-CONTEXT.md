# Phase 1: Core Data Foundation - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Event-sourced RDF data path with triplestore, command API, materialized state, and SPARQL reads. Users can deploy SemPKM via docker-compose and the system can persist, materialize, and query RDF data. Includes a dev console frontend for testing. Semantic services (labels, prefixes, SHACL) and real UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Event model
- One event graph per API request (batch of commands shares a single named graph)
- Rich metadata per event: timestamp, operation type, affected IRIs, human-readable description
- Eager materialization: current state graph is updated on each commit, not reconstructed on read
- Events are immutable for v1, but graph naming should be designed to support future archival/compaction without breaking references

### Command API contract
- RPC-style single endpoint: POST /api/commands with `{command: 'object.create', params: {...}}`
- JSON-LD payloads throughout (both request and response)
- Batch support: accept an array of commands in a single request
- All-or-nothing transaction semantics: entire batch succeeds or entire batch rolls back, no partial commits

### Object identity
- IRI pattern: `{namespace}/{Type}/{slug-or-uuid}` (e.g., `https://example.org/data/Person/alice` or `https://example.org/data/Note/550e8400-...`)
- Client can provide a slug; system falls back to UUID if not provided
- User-configurable base namespace (default provided, user can set their own domain for future federation)
- Type is fixed at creation and encoded in the IRI path; type changes are not allowed (create a new object instead)
- Edges are first-class resources with their own IRIs (enables edge annotations, metadata, and versioning in later phases)

### Frontend bootstrap
- Dev console: SPARQL query box + command form for manual testing, plus health/status page with version info
- htmx + vanilla JS from the start (aligns with Phase 4 admin portal stack)
- Served from a separate container (e.g., nginx), not from FastAPI directly
- SPARQL query box auto-injects common prefixes (rdf:, rdfs:, sempkm:, etc.)

### Claude's Discretion
- Docker Compose service configuration and networking details
- RDF4J repository type and configuration
- FastAPI project structure and internal architecture
- Event graph IRI naming scheme (within the archival-compatible constraint)
- Error response format and HTTP status code mapping
- Dev console visual design and layout

</decisions>

<specifics>
## Specific Ideas

- IRI minting combines namespace + type + user-provided slug, with UUID fallback — prioritizes human-readable IRIs when possible
- Dev console serves double duty: proves the stack works AND provides a manual testing surface during development
- JSON-LD throughout keeps the system semantically coherent from API boundary to triplestore

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-data-foundation*
*Context gathered: 2026-02-21*
