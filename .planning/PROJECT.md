# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and projections into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and a hybrid frontend: htmx/vanilla web for the admin shell and a React-based IDE workspace for the interactive Object Browser.

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

- [ ] Event-sourced write path with events stored as RDF in named graphs within the triplestore
- [ ] Materialized current graph state projected from the event log
- [ ] RDF triplestore (Blazegraph/RDF4J via Docker, building on semantic-stack reference)
- [ ] SPARQL endpoint for reads
- [ ] Minimal command API for writes (object.create, object.patch, body.set, edge.create, edge.patch)
- [ ] SHACL async validation with lint UI (violations gate conformance operations, warnings are guidance)
- [ ] SHACL-driven form generation from shapes (sh:property, sh:order, sh:group, sh:name, etc.)
- [ ] Mental Model manager — install/remove/list models from `.sempkm-model` archives
- [ ] Mental Model manifest validation (schema, ID namespacing, reference integrity, export policy)
- [ ] Starter Mental Model (Basic PKM: Projects, People, Notes, Concepts)
- [ ] IDE-grade Object Browser in React (resizable panes, tabs, command palette, keyboard-first)
- [ ] Core renderers: object page, form, table, cards, graph (2D)
- [ ] Dashboards: parameterized panels, type-based registry, panel types (objectSelf, view, lintSummary, markdown)
- [ ] View spec execution (SPARQL query + renderer + layout config + optional params)
- [ ] Prefix registry and QName resolution (model-provided, user overrides, SemPKM defaults)
- [ ] Label service (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback)
- [ ] Edge model: first-class Edge resources (sempkm:Edge) with optional simple-triple projection
- [ ] Admin portal (htmx/vanilla web): model management, webhook config, system status
- [ ] Simple outbound webhooks for event notifications (best-effort delivery)
- [ ] Basic publishing/export: JSON-LD export

### Out of Scope

- Read/write filesystem projections — v2 (read-only projection is also deferred past initial v1)
- Mental Model migrations and user overrides — v2+
- Offline/multi-device sync — v2+
- Embedded n8n workflow engine — v2+
- Advanced webhook delivery/security (DLQ, signing, strict ordering) — v3
- Bidirectional ActivityPub — v2+
- SOLID export/publish — deferred (not in initial v1 scope)
- ActivityPub outbound publishing — deferred past initial v1
- Timeline/calendar renderers — v1.1/v2
- 3D graph visualization — experimental, deferred
- Multi-user auth — v1 is single-user
- SPARQL UPDATE as external write surface — by design

## Context

- Extensive v0.3 design documents exist in `orig_specs/` covering the full vision, specifications, decision log, schemas, and a starter Mental Model — these are reference material, not the final implementation spec
- The user has an existing project `semantic-stack` (https://github.com/MetaCoding-io/semantic-stack/) providing a Docker Compose setup with Blazegraph, RDF4J, WebVOWL and other RDF tools — this is the reference for the triplestore deployment
- The vision document captures decisions from deep design sessions with ChatGPT — all confirmed decisions are in `orig_specs/docs/decisions/v0.3.md`
- Core architectural decisions are settled: event sourcing canonical, edges as first-class resources, SHACL drives UI, dashboards are distinct and parameterized, views/dashboards namespaced by modelId, private-by-default cross-model embedding
- Open v0.3 questions (non-blocking for v1): RDF store portability promises, projection refresh strategy, import UX

## Constraints

- **Backend**: Python + FastAPI — modern async setup
- **Frontend shell**: htmx + vanilla web for admin portal and application shell
- **Frontend IDE**: React application for the interactive Object Browser (embedded in the htmx shell)
- **Triplestore**: Blazegraph or RDF4J, deployed via Docker (from semantic-stack reference)
- **Events**: Stored as RDF in named graphs within the triplestore (triplestore-native event sourcing)
- **Deployment**: Self-hosted web application (Docker-based)
- **Auth**: Single-user for v1
- **Standards**: RDF, SPARQL 1.1, SHACL Core (pragmatic subset), JSON-LD for export

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Event sourcing as canonical truth | Supports automation, auditability, future sync strategies | — Pending |
| Edges as first-class resources (sempkm:Edge) | UX needs stable edge identity for inspection, annotation, provenance | — Pending |
| SHACL subset drives UI (forms + linting) | SHACL already encodes field structure, constraints, severity, layout hints | — Pending |
| Triplestore-native event storage | Events as RDF named graphs, keeping everything in one data layer | — Pending |
| htmx shell + React IDE (iframe) | Simple admin with htmx, rich IDE experience with React where needed | — Pending |
| FastAPI backend | Modern Python async framework, OpenAPI docs, Pydantic models | — Pending |
| Filesystem projection deferred | Focus v1 on the core create/browse/explore loop first | — Pending |
| Private-by-default cross-model embedding | Explicit exports prevent accidental coupling between Mental Models | — Pending |
| Violations gate conformance ops only | SHACL is assistive (linting), not punitive — users can always edit | — Pending |

---
*Last updated: 2026-02-21 after initialization*
