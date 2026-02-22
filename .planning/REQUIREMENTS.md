# Requirements: SemPKM

**Defined:** 2026-02-21
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Data Layer

- [x] **CORE-01**: System persists all writes as immutable events stored in RDF named graphs within the triplestore
- [x] **CORE-02**: System materializes a current graph state projection derived from the event log
- [x] **CORE-03**: RDF4J triplestore is deployed and configured via Docker Compose
- [x] **CORE-04**: User can execute SPARQL queries against the current graph state via a read endpoint
- [x] **CORE-05**: System provides a command API for writes: object.create, object.patch, body.set, edge.create, edge.patch

### SHACL Validation & Forms

- [x] **SHCL-01**: System runs SHACL validation asynchronously after each commit (non-blocking UI)
- [ ] **SHCL-02**: User can see validation results in a lint panel showing violations and warnings per object
- [x] **SHCL-03**: User can create objects via forms auto-generated from SHACL shapes (sh:property, sh:order, sh:group, sh:name, sh:datatype, sh:class, sh:in, sh:defaultValue)
- [x] **SHCL-04**: User can edit existing objects via the same SHACL-driven forms
- [x] **SHCL-05**: System persists immutable SHACL validation reports tied to each commit
- [ ] **SHCL-06**: Violations block conformance-required operations (publish/export); warnings do not block any operations

### Mental Models

- [x] **MODL-01**: User can install a Mental Model from a .sempkm-model archive via the admin UI
- [x] **MODL-02**: User can remove an installed Mental Model via the admin UI
- [x] **MODL-03**: User can view a list of installed Mental Models with name, version, and description
- [x] **MODL-04**: System validates manifest.yaml against schema on install (modelId, version, entrypoints, exports)
- [x] **MODL-05**: System validates ID uniqueness, namespacing rules, and reference integrity on install
- [x] **MODL-06**: A starter Mental Model (Basic PKM) ships with the system providing Projects, People, Notes, and Concepts with shapes, views, and seed data

### Object Browser / IDE

- [x] **VIEW-01**: User can browse objects in a table view with sortable columns, filtering, and pagination
- [x] **VIEW-02**: User can browse objects in a cards view with summary display and optional grouping
- [ ] **VIEW-03**: User can view objects and relationships in a 2D graph with semantic-aware styling (node color by type, edge style by predicate)
- [ ] **VIEW-04**: User can view a single object's details on an object page (properties, body, related objects)
- [x] **VIEW-05**: User can work in an IDE-style workspace with resizable panes and tabs
- [x] **VIEW-06**: User can navigate and execute commands via a command palette and keyboard shortcuts
- [x] **VIEW-07**: System executes view specs (SPARQL query + renderer type + layout config) to render views

### Object Management

- [ ] **OBJ-01**: User can create new objects by selecting a type and filling out a SHACL-driven form
- [ ] **OBJ-02**: User can edit an object's properties through its SHACL-driven form
- [ ] **OBJ-03**: User can write and edit an object's Markdown body via an embedded editor

### Infrastructure Services

- [x] **INFR-01**: System resolves IRIs to human-readable labels using the label precedence chain (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback)
- [x] **INFR-02**: System provides a prefix registry merging model-provided, user-override, and built-in prefix mappings for QName rendering across the UI

### Administration

- [x] **ADMN-01**: User can deploy SemPKM via docker-compose up with all services (FastAPI backend, RDF4J triplestore, frontend)
- [x] **ADMN-02**: User can manage Mental Models (install/remove/list) through an admin portal built with htmx/vanilla web
- [x] **ADMN-03**: User can configure simple outbound webhooks that fire on events (object.changed, edge.changed, validation.completed)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Dashboards

- **DASH-01**: User can view parameterized dashboards composed of panels (objectSelf, view, lintSummary, markdown)
- **DASH-02**: System maps object types to default dashboards via a type-based dashboard registry
- **DASH-03**: User can switch dashboards via "Open with..." menu

### Advanced Content

- **CONT-01**: User can create typed edges inline with wiki-link-speed UX
- **CONT-02**: User can inspect edge details (type, annotations, provenance) in an edge inspector panel
- **CONT-03**: User can tag objects with SKOS concepts
- **CONT-04**: User can see backlinks (incoming references) for any object in a panel

### Query & Search

- **QRYS-01**: User can write and execute SPARQL queries in a dedicated editor with syntax highlighting and prefix injection
- **QRYS-02**: User can search across objects with full-text search (separate index, not triplestore-native)

### Export & Interop

- **EXPO-01**: User can export objects/collections as JSON-LD
- **EXPO-02**: System generates read-only filesystem projection (markdown + sidecars) for Obsidian interop
- **EXPO-03**: Cross-model embedding with explicit export control (private-by-default)

### Publishing

- **PUBL-01**: User can publish selected objects via outbound ActivityPub
- **PUBL-02**: User can export shape-governed subsets to SOLID pods

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Read/write filesystem round-trip | Bidirectional sync is one of the hardest distributed systems problems — v2 |
| Mental Model migrations | Requires complex version management tooling — v2+ |
| User-defined schema overrides | Would require migration story first — v2+ |
| Offline/multi-device sync | Requires distributed event log reconciliation — v2+ |
| Embedded n8n workflow engine | Scope explosion; simple webhooks are sufficient for v1 — v2+ |
| Advanced webhook delivery (DLQ, signing, ordering) | Over-engineering for single-user v1 — v3 |
| 3D graph visualization | Experimental, 2D is sufficient — deferred |
| Multi-user auth / permissions | Single-user v1; design data model to not preclude it later |
| SPARQL UPDATE as external write surface | Bypasses event sourcing, breaks audit trail — by design |
| Timeline / calendar renderers | Not core to semantic knowledge value proposition — v1.1/v2 |
| AI/LLM integration | Moving target; SemPKM's moat is semantic structure, not AI — v2+ |
| Ontology editor | SemPKM consumes ontologies via Mental Models; Protege for authoring |
| Mobile native app | Web-first; responsive design and eventual PWA instead |
| Real-time collaborative editing | Requires CRDT/OT — v2+ at earliest |
| Bidirectional ActivityPub sync | Uni-directional first, then add inbound — v2+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 1 | Complete |
| CORE-05 | Phase 1 | Complete |
| SHCL-01 | Phase 2 | Complete |
| SHCL-02 | Phase 4 | Pending |
| SHCL-03 | Phase 4 | Complete |
| SHCL-04 | Phase 4 | Complete |
| SHCL-05 | Phase 2 | Complete |
| SHCL-06 | Phase 4 | Pending |
| MODL-01 | Phase 3 | Complete |
| MODL-02 | Phase 3 | Complete |
| MODL-03 | Phase 3 | Complete |
| MODL-04 | Phase 3 | Complete |
| MODL-05 | Phase 3 | Complete |
| MODL-06 | Phase 3 | Complete |
| VIEW-01 | Phase 5 | Complete |
| VIEW-02 | Phase 5 | Complete |
| VIEW-03 | Phase 5 | Pending |
| VIEW-04 | Phase 4 | Pending |
| VIEW-05 | Phase 4 | Complete |
| VIEW-06 | Phase 4 | Complete |
| VIEW-07 | Phase 5 | Complete |
| OBJ-01 | Phase 4 | Pending |
| OBJ-02 | Phase 4 | Pending |
| OBJ-03 | Phase 4 | Pending |
| INFR-01 | Phase 2 | Complete |
| INFR-02 | Phase 2 | Complete |
| ADMN-01 | Phase 1 | Complete |
| ADMN-02 | Phase 4 | Complete |
| ADMN-03 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation*
