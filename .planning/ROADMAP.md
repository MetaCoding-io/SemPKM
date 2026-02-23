# Roadmap: SemPKM

## Overview

SemPKM delivers a semantics-native personal knowledge management platform through five phases that follow the architecture's strict dependency order: triplestore foundation, then semantic services (labels, prefixes, SHACL), then the Mental Model packaging system, then the first user-facing surfaces (admin shell + SHACL-driven forms + IDE workspace), and finally data browsing and graph visualization. The critical path targets the "wow in 10 minutes" experience: install SemPKM, install a Mental Model, create objects via auto-generated forms, browse in table/graph views, and see SHACL linting guidance. Each phase delivers a complete, verifiable capability that unlocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Data Foundation** - Event-sourced RDF data path with triplestore, command API, materialized state, and SPARQL reads (completed 2026-02-21)
- [x] **Phase 2: Semantic Services** - Label resolution, prefix registry, and async SHACL validation engine
- [x] **Phase 3: Mental Model System** - Install, validate, and manage Mental Model archives; ship the starter Basic PKM model (completed 2026-02-22)
- [x] **Phase 4: Admin Shell and Object Creation** - First user-facing surfaces: admin portal, IDE workspace, SHACL-driven forms, object pages, and lint panel (completed 2026-02-22)
- [x] **Phase 5: Data Browsing and Visualization** - Table, cards, and graph renderers with view spec execution completing the create/browse/explore loop (completed 2026-02-22)
- [x] **Phase 6: User and Team Management** - Passwordless auth, owner/member/guest RBAC, event provenance, SQL data layer for multi-tenant cloud readiness (completed 2026-02-22)
- [x] **Phase 7: Route Protection and Provenance** - Gap closure: server-side auth on browser/views/admin routes, user provenance on browser writes
- [x] **Phase 8: Integration Bug Fixes** - Gap closure: validation.completed webhook dispatch, cards view URL mismatch fix (completed 2026-02-23)
- [x] **Phase 9: Provenance and Redirect Micro-Fixes** - Gap closure: API command path role provenance, invite acceptance ?next= redirect (completed 2026-02-23)

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
- [x] 02-01-PLAN.md — Prefix registry and label resolution service (three-layer prefix lookup, SPARQL COALESCE batch labels, TTLCache, LOV import)
- [x] 02-02-PLAN.md — Async SHACL validation engine and reports (pyshacl queue worker, immutable report named graphs, polling endpoint, command commit trigger)

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
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Model domain module (manifest schema, JSON-LD loader, archive validators, model registry SPARQL operations)
- [x] 03-02-PLAN.md — Basic PKM starter model (ontology with 4 types, SHACL shapes, view specs, seed data)
- [x] 03-03-PLAN.md — ModelService, API endpoints, and app wiring (install/remove/list pipelines, real shapes loader, auto-install)

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
**Plans**: 6 plans

Plans:
- [x] 04-01-PLAN.md — Dashboard shell, nginx routing, and Jinja2 template infrastructure
- [x] 04-02-PLAN.md — ShapesService (SHACL form metadata) and WebhookService (outbound event notifications)
- [x] 04-03-PLAN.md — Admin portal UI (model management table, webhook configuration)
- [x] 04-04-PLAN.md — IDE workspace layout (Split.js panes, tabs, navigation tree, command palette)
- [x] 04-05-PLAN.md — SHACL-driven form generation, type picker, create/edit object flows
- [x] 04-06-PLAN.md — Object page with Markdown editor, related objects, lint panel, conformance gating

### Phase 5: Data Browsing and Visualization
**Goal**: Users can browse, filter, and explore their knowledge through table, cards, and graph views powered by executable view specs
**Depends on**: Phase 4
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-07
**Success Criteria** (what must be TRUE):
  1. User can browse objects in a table view with sortable columns, filtering, and pagination
  2. User can browse objects in a cards view with summary display and optional grouping
  3. User can view objects and relationships in a 2D graph with semantic-aware styling (node color by type, edge style by predicate) and interactive exploration
  4. System executes view specs (SPARQL query + renderer type + layout config) to render views, enabling Mental Models to define custom browsing experiences
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — ViewSpecService and table view (view spec execution pipeline, sortable/filterable/paginated table renderer)
- [x] 05-02-PLAN.md — Cards view (flippable cards with CSS 3D flip, body snippets, property/relation back face, optional grouping)
- [x] 05-03-PLAN.md — Graph view and workspace integration (Cytoscape.js visualization, layout picker, view tabs, view menu, command palette)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Data Foundation | 4/4 | Complete    | 2026-02-21 |
| 2. Semantic Services | 2/2 | Complete    | 2026-02-21 |
| 3. Mental Model System | 3/3 | Complete    | 2026-02-22 |
| 4. Admin Shell and Object Creation | 6/6 | Complete    | 2026-02-22 |
| 5. Data Browsing and Visualization | 3/3 | Complete    | 2026-02-22 |
| 6. User and Team Management | 4/4 | Complete    | 2026-02-22 |
| 7. Route Protection and Provenance | 2/2 | Complete    | 2026-02-23 |
| 8. Integration Bug Fixes | 1/1 | Complete    | 2026-02-23 |
| 9. Provenance and Redirect Micro-Fixes | 1/1 | Complete | 2026-02-23 |

### Phase 6: User and Team Management for Multi-Tenant Cloud Readiness

**Goal:** Users can authenticate, manage roles (owner/member/guest), and control access so SemPKM supports multiple users per instance with passwordless login, session-based auth, and event provenance tracking
**Depends on:** Phase 5
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, RBAC-01, RBAC-02, RBAC-03, PROV-01, PROV-02, INFRA-01, INVITE-01
**Success Criteria** (what must be TRUE):
  1. User can claim a local instance via setup wizard (enter terminal token, become owner) with zero-friction first-run experience
  2. System authenticates users via passwordless magic links (cloud) or setup token (local) with session-based cookies
  3. Owner can invite members and guests, each with appropriate access level (owner: full, member: read+write, guest: read-only)
  4. All write endpoints require owner or member role; all read endpoints require authentication; health stays public
  5. Every user-initiated write event records which user performed the action (sempkm:performedBy provenance)
  6. SQL database (SQLite local, PostgreSQL cloud) stores user accounts, sessions, invitations, and instance config
  7. RDF4J triplestore port is not exposed to host; data volume persists across restarts
**Plans:** 4/4 plans complete

Plans:
- [x] 06-01-PLAN.md — SQL data layer and Docker infrastructure (ORM models, Alembic migrations, config expansion, Docker hardening)
- [x] 06-02-PLAN.md — Auth service, tokens, and setup wizard (itsdangerous tokens, session management, auth dependencies, setup flow, auth router)
- [x] 06-03-PLAN.md — Route protection and event provenance (auth middleware on all routes, RBAC enforcement, performedBy enrichment)
- [x] 06-04-PLAN.md — Auth UI pages (setup wizard, login, invitation acceptance pages with human verification checkpoint)

### Phase 7: Route Protection and Provenance
**Goal:** All browser, views, and admin HTML routes enforce server-side authentication and authorization; browser-originated writes record user provenance in event metadata
**Depends on:** Phase 6
**Requirements:** Closes integration gaps INT-01, INT-02, INT-03 from v1.0 audit
**Gap Closure:** Addresses missing server-side auth on browser/views/admin routes and missing performed_by on browser write endpoints
**Success Criteria** (what must be TRUE):
  1. All browser/* write endpoints (POST /browser/objects, POST /browser/objects/{iri}/save, POST /browser/objects/{iri}/body) require owner or member role via server-side dependency
  2. All browser/* and views/* read endpoints require authentication via get_current_user
  3. All admin/* endpoints require owner role via require_role("owner")
  4. Browser-originated writes pass performed_by user IRI to EventStore.commit()
  5. Unauthenticated direct HTTP requests to any protected route receive 401/403 (not just a JS redirect)
**Plans:** 2/2 plans complete

Plans:
- [x] 07-01-PLAN.md -- Auth error handling infrastructure (custom exception handler, 403 template, EventStore provenance extension, frontend ?next= redirect-back)
- [x] 07-02-PLAN.md -- Route protection and provenance wiring (auth deps on all 31 HTML endpoints, provenance on 3 browser write endpoints)

### Phase 8: Integration Bug Fixes
**Goal:** Fix remaining integration issues: wire validation.completed webhook dispatch and fix cards view URL mismatch
**Depends on:** Phase 7
**Requirements:** Closes ADMN-03 partial gap and VIEW-02 flow break from v1.0 audit
**Gap Closure:** Addresses validation.completed webhook never firing and workspace.js cards URL mismatch
**Success Criteria** (what must be TRUE):
  1. AsyncValidationQueue fires a completion callback after each validation run
  2. WebhookService dispatches validation.completed events to configured webhooks
  3. workspace.js openViewTab() uses correct URL path for cards view (/views/card/ singular)
  4. Opening a cards view from the command palette or workspace tab system renders correctly (no 404)
**Plans:** 1/1 plans complete

Plans:
- [x] 08-01-PLAN.md — Validation.completed webhook dispatch and cards view URL verification

### Phase 9: Provenance and Redirect Micro-Fixes
**Goal:** Close the 2 remaining low-severity integration gaps from the v1.0 re-audit: add performed_by_role to API command commit path and honor ?next= in invite acceptance redirect
**Depends on:** Phase 8
**Requirements:** Closes PROV-02-partial and AUTH-03-cosmetic from v1.0 re-audit
**Gap Closure:** Addresses missing role provenance on API commands and invite acceptance ?next= redirect
**Success Criteria** (what must be TRUE):
  1. POST /api/commands passes performed_by_role=user.role to EventStore.commit() (matching the pattern in browser/router.py)
  2. handleInviteAccept in auth.js reads ?next= parameter and redirects to the original URL after successful invitation acceptance
**Plans:** 1 plan

Plans:
- [x] 09-01-PLAN.md — API command provenance fix (performed_by_role) and invite ?next= redirect verification

---
*Roadmap created: 2026-02-21*
*Last updated: 2026-02-23 after phase 9 completion -- all v1.0 gap closures done*
