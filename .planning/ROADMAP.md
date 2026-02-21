# Roadmap: SemPKM

## Overview

SemPKM delivers a semantics-native personal knowledge management platform through five phases that follow the architecture's strict dependency order: triplestore foundation, then semantic services (labels, prefixes, SHACL), then the Mental Model packaging system, then the first user-facing surfaces (admin shell + SHACL-driven forms + IDE workspace), and finally data browsing and graph visualization. The critical path targets the "wow in 10 minutes" experience: install SemPKM, install a Mental Model, create objects via auto-generated forms, browse in table/graph views, and see SHACL linting guidance. Each phase delivers a complete, verifiable capability that unlocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Data Foundation** - Event-sourced RDF data path with triplestore, command API, materialized state, and SPARQL reads (completed 2026-02-21)
- [ ] **Phase 2: Semantic Services** - Label resolution, prefix registry, and async SHACL validation engine
- [ ] **Phase 3: Mental Model System** - Install, validate, and manage Mental Model archives; ship the starter Basic PKM model
- [ ] **Phase 4: Admin Shell and Object Creation** - First user-facing surfaces: admin portal, IDE workspace, SHACL-driven forms, object pages, and lint panel
- [ ] **Phase 5: Data Browsing and Visualization** - Table, cards, and graph renderers with view spec execution completing the create/browse/explore loop

## Phase Details

### Phase 1: Core Data Foundation
**Goal**: Users can deploy SemPKM and the system can persist, materialize, and query RDF data through an event-sourced write path
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, ADMN-01
**Success Criteria** (what must be TRUE):
  1. User can run docker-compose up and all services (FastAPI backend, RDF4J triplestore, frontend) start and become healthy
  2. System persists writes as immutable event named graphs and materializes a current graph state from the event log
  3. User can create objects and edges through the command API (object.create, object.patch, body.set, edge.create, edge.patch) and see them reflected in the current state
  4. User can execute SPARQL SELECT queries against the current graph state and receive correct results
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Infrastructure and triplestore foundation (Docker Compose, FastAPI skeleton, RDF4J repo auto-creation)
- [x] 01-02-PLAN.md — Event store and RDF core (namespaces, IRI minting, JSON-LD, event graphs, current state materialization)
- [x] 01-03-PLAN.md — Command API (Pydantic schemas, dispatcher, 5 command handlers, POST /api/commands endpoint)
- [x] 01-04-PLAN.md — SPARQL read endpoint and dev console (query scoping, htmx UI with SPARQL box and command form)

### Phase 2: Semantic Services
**Goal**: The system resolves IRIs to human-readable labels, manages prefix mappings, and validates data against SHACL shapes asynchronously after every commit
**Depends on**: Phase 1
**Requirements**: INFR-01, INFR-02, SHCL-01, SHCL-05
**Success Criteria** (what must be TRUE):
  1. System resolves any IRI to a human-readable label using the precedence chain (dcterms:title, rdfs:label, skos:prefLabel, schema:name, IRI fallback) with batch resolution and caching
  2. System provides a prefix registry that merges model-provided, user-override, and built-in prefix mappings for QName rendering
  3. System runs SHACL validation asynchronously after each commit without blocking the write path
  4. System persists immutable SHACL validation reports tied to each commit as named graphs
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Prefix registry and label resolution service (three-layer prefix lookup, SPARQL COALESCE batch labels, TTLCache, LOV import)
- [ ] 02-02-PLAN.md — Async SHACL validation engine and reports (pyshacl queue worker, immutable report named graphs, polling endpoint, command commit trigger)

### Phase 3: Mental Model System
**Goal**: Users can install domain experiences as Mental Model archives that bundle ontologies, shapes, views, and seed data into the system
**Depends on**: Phase 2
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04, MODL-05, MODL-06
**Success Criteria** (what must be TRUE):
  1. User can install a Mental Model from a .sempkm-model archive and the system loads its ontology, shapes, views, and seed data into the triplestore
  2. User can remove an installed Mental Model and its artifacts are cleaned up
  3. User can view a list of installed Mental Models showing name, version, and description
  4. System rejects Mental Model archives that fail manifest schema validation, ID namespacing rules, or reference integrity checks
  5. A starter Mental Model (Basic PKM) ships with the system providing Projects, People, Notes, and Concepts with shapes, views, and seed data
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Admin Shell and Object Creation
**Goal**: Users can manage the system through an admin portal and create, edit, and inspect objects through SHACL-driven forms in an IDE-style workspace with validation feedback
**Depends on**: Phase 3
**Requirements**: ADMN-02, ADMN-03, SHCL-02, SHCL-03, SHCL-04, SHCL-06, OBJ-01, OBJ-02, OBJ-03, VIEW-04, VIEW-05, VIEW-06
**Success Criteria** (what must be TRUE):
  1. User can manage Mental Models (install, remove, list) through an htmx-based admin portal
  2. User can configure outbound webhooks that fire on events (object.changed, edge.changed, validation.completed) through the admin portal
  3. User can create a new object by selecting a type and filling out a form auto-generated from SHACL shapes (respecting sh:property, sh:order, sh:group, sh:name, sh:datatype, sh:class, sh:in, sh:defaultValue)
  4. User can edit an existing object's properties and Markdown body through SHACL-driven forms and an embedded editor
  5. User can view a single object's details (properties, body, related objects) on an object page with human-readable labels
  6. User can work in an IDE-style workspace with resizable panes, tabs, and a command palette with keyboard shortcuts
  7. User can see SHACL validation results in a lint panel showing violations and warnings per object, where violations block conformance-required operations (export) but warnings never block
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Data Browsing and Visualization
**Goal**: Users can browse, filter, and explore their knowledge through table, cards, and graph views powered by executable view specs
**Depends on**: Phase 4
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-07
**Success Criteria** (what must be TRUE):
  1. User can browse objects in a table view with sortable columns, filtering, and pagination
  2. User can browse objects in a cards view with summary display and optional grouping
  3. User can view objects and relationships in a 2D graph with semantic-aware styling (node color by type, edge style by predicate) and interactive exploration
  4. System executes view specs (SPARQL query + renderer type + layout config) to render views, enabling Mental Models to define custom browsing experiences
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Data Foundation | 4/4 | Complete    | 2026-02-21 |
| 2. Semantic Services | 0/2 | Planned | - |
| 3. Mental Model System | 0/0 | Not started | - |
| 4. Admin Shell and Object Creation | 0/0 | Not started | - |
| 5. Data Browsing and Visualization | 0/0 | Not started | - |

---
*Roadmap created: 2026-02-21*
*Last updated: 2026-02-21 after Phase 2 planning*
