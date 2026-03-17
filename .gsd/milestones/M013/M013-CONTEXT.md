# M013: API Surface for External Clients

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Expose a clean JSON API layer for external clients (browser extension, mobile apps, third-party integrations) to discover instance capabilities, query available types with their SHACL shapes, and find related objects by context. Four new endpoints: `/.well-known/sempkm` (instance discovery), `GET /api/types` (available types with labels/icons/models), `GET /api/shapes/{type_iri}` (SHACL property shapes as JSON), and `POST /api/context-query` (find related objects given page metadata).

## Why This Milestone

SemPKM's existing API is designed for the htmx frontend — HTML fragment responses, template-rendered forms, session-cookie auth. External clients need JSON responses, structured type metadata, and capability discovery. The browser extension (M014) needs all four endpoints, but they're independently useful for any integration: MCP server, mobile app, Raycast extension, Alfred workflow, etc.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Hit `/.well-known/sempkm` and get a JSON capability manifest (version, available endpoints, auth methods)
- Query `GET /api/types` to see all available types from installed Mental Models with labels, icons, model attribution, and type hierarchy
- Query `GET /api/shapes/{type_iri}` to get SHACL property shapes as structured JSON (field names, types, constraints, groups, helptext, order)
- POST to `/api/context-query` with a URL/title/keywords and get back related objects from the knowledge graph

### Entry point / environment

- Entry point: `http://localhost:3000/api/` and `http://localhost:3000/.well-known/sempkm`
- Environment: Docker Compose
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: all 4 endpoints return well-structured JSON matching their OpenAPI schemas, handle edge cases (unknown type, no matches), and have unit tests
- Integration complete means: endpoints work with real triplestore data, shapes match what the SHACL form generator uses, context-query returns relevant results against real object data
- Operational complete means: endpoints work with both API key and session auth

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `curl /.well-known/sempkm` returns JSON with version, endpoints, and capabilities
- `curl /api/types` returns all types from installed models with labels, icons, and model names
- `curl /api/shapes/urn:sempkm:model:basic-pkm:Note` returns PropertyShape JSON matching the existing SHACL form fields
- `POST /api/context-query` with `{"url": "https://example.com"}` returns objects that have that URL as a property value
- All endpoints work with both API key auth (Authorization: Bearer) and session cookie auth

## Risks and Unknowns

- **Shape JSON serialization** — ShapesService currently returns Python dataclasses consumed by Jinja2 templates. Serializing to JSON requires either Pydantic models or custom serialization. The property shape structure (groups, constraints, choices) is non-trivial.
- **Context-query relevance** — Matching page metadata to graph objects is fuzzy. URL matching is straightforward; title/keyword matching via FTS may return noise. Need sensible ranking.
- **Auth for external clients** — API key auth exists but may need refinement for header-based bearer tokens from browser extensions (CORS considerations).

## Existing Codebase / Prior Art

- `backend/app/services/shapes.py` — ShapesService._extract_node_shape() returns PropertyShape dataclasses
- `backend/app/views/service.py` — ViewSpecService with ShapesService integration
- `backend/app/auth/router.py` — API token generation and verification
- `backend/app/browser/search.py` — FTS search endpoint
- `.gsd/design/BROWSER-EXTENSION-DESIGN.md` — Endpoint specifications and data flow

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New: API-01 (well-known discovery), API-02 (types endpoint), API-03 (shapes endpoint), API-04 (context-query endpoint)

## Scope

### In Scope

- `GET /.well-known/sempkm` — instance discovery JSON
- `GET /api/types` — all types with labels, icons, model attribution
- `GET /api/shapes/{type_iri}` — SHACL shapes as structured JSON (fields, groups, constraints, helptext)
- `POST /api/context-query` — related objects by URL, title, keywords
- OpenAPI documentation for all endpoints
- API key (Bearer token) auth support on all endpoints
- CORS headers for browser extension access
- Unit tests for all endpoints

### Out of Scope / Non-Goals

- GraphQL API
- WebSocket subscriptions
- Bulk object creation API (existing POST /api/commands is sufficient)
- Rate limiting on new endpoints (can add later)

## Technical Constraints

- JSON responses only (no HTML fragments)
- Must work with existing auth infrastructure (session + API key)
- CORS must allow browser extension origin
- Shapes JSON must accurately reflect what the SHACL form generator uses

## Integration Points

- **ShapesService** — property shape extraction for /api/shapes
- **LabelService** — label resolution for /api/types
- **IconService** — icon data for /api/types
- **FTS (LuceneSail)** — keyword matching in context-query
- **TriplestoreClient** — SPARQL queries for context-query URL/property matching
- **Auth** — API key verification for external client access

## Open Questions

- **Context-query scope** — Should it search only literal values (URL, title matches) or also traverse edges (objects linked to matching objects)? Current thinking: literal matches only for v1, edge traversal later.
- **CORS policy** — Allow all origins (Access-Control-Allow-Origin: *) or require extension to register? Current thinking: allow all for local instances, configurable for cloud.
