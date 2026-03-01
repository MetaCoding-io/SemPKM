# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, and multi-renderer data browsing (table, cards, graph).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Requirements

### Validated

<!-- Shipped and confirmed valuable in v1.0. -->

- ✓ Event-sourced write path with immutable events as RDF named graphs — v1.0
- ✓ Materialized current graph state from event log — v1.0
- ✓ RDF4J triplestore via Docker Compose — v1.0
- ✓ SPARQL endpoint for reads with automatic graph scoping — v1.0
- ✓ Command API (object.create, object.patch, body.set, edge.create, edge.patch) — v1.0
- ✓ Async SHACL validation with lint panel (violations gate conformance ops) — v1.0
- ✓ SHACL-driven form generation from shapes — v1.0
- ✓ Mental Model manager (install/remove/list from .sempkm-model archives) — v1.0
- ✓ Mental Model manifest validation (schema, ID namespacing, reference integrity) — v1.0
- ✓ Starter Mental Model: Basic PKM (Projects, People, Notes, Concepts) — v1.0
- ✓ IDE-style workspace (Split.js panes, tabs, command palette, keyboard shortcuts) — v1.0
- ✓ Core renderers: object page, SHACL forms, table, cards, graph (2D) — v1.0
- ✓ View spec execution (SPARQL query + renderer + layout config) — v1.0
- ✓ Prefix registry and QName resolution (4-layer: user > model > LOV > built-in) — v1.0
- ✓ Label service (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback) — v1.0
- ✓ Admin portal (htmx): model management, webhook config, system status — v1.0
- ✓ Simple outbound webhooks (object.changed, edge.changed, validation.completed) — v1.0
- ✓ Passwordless multi-user auth (setup wizard, magic links, session-based) — v1.0
- ✓ RBAC: owner/member/guest roles with server-side enforcement — v1.0
- ✓ Event provenance: performed_by + performed_by_role on every user write — v1.0
- ✓ SQL data layer for auth (SQLite local, PostgreSQL cloud-ready) — v1.0

### Validated (v2.0)

<!-- Shipped and confirmed valuable in v2.0. -->

- ✓ Bug fixes: body content loading, editor editability, autocomplete dropdown, views explorer loading — v2.0
- ✓ Read-only object view (styled properties + rendered Markdown body) with CSS 3D flip to edit mode — v2.0
- ✓ Resizable body text area in edit mode (Split.js vertical gutter + maximize toggle) — v2.0
- ✓ VS Code-style split panes (HTML5 drag-and-drop, up to 4 editor groups) — v2.0
- ✓ Bottom panel infrastructure (SPARQL/Event Log/AI Copilot tabbed panel, Ctrl+J) — v2.0
- ✓ Collapsible sidebar with reorganized navigation (Admin, Meta, Apps, Debug) — v2.0
- ✓ VS Code-style user menu at bottom of sidebar (logout, settings, theme toggle) — v2.0
- ✓ Styled 403 permission panel with Lucide lock icon and navigation buttons — v2.0
- ✓ Dark mode with tri-state toggle (system/light/dark), anti-FOUC, 35+ CSS token system — v2.0
- ✓ Global settings system (layered: system < model < user; VS Code-style two-column UI) — v2.0
- ✓ Node type icons in graph view and object explorer (IconService, manifest-declared) — v2.0
- ✓ Event log explorer (timeline, filter chips, inline diffs, undo via compensating events) — v2.0
- ✓ LLM connection configuration (Fernet-encrypted key, SSE streaming proxy) — v2.0
- ✓ Driver.js guided tours (Welcome 10-step, Create Object htmx-gated) with Docs hub page — v2.0
- ✓ Rounded tab styling (8px border-radius, recessed bar, teal accent) — v2.0

### Active

<!-- v2.1: Architecture Decision Gate — formalizing completed research + tech debt -->

- [ ] DEC-01: FTS/vector search approach committed (RDF4J LuceneSail, config, query API, phased plan)
- [ ] DEC-02: SPARQL UI approach committed (Zazuko Yasgui CDN embed, YASR plugin strategy)
- [ ] DEC-03: VFS technology committed (wsgidav + a2wsgi, MountSpec MVP vocab, client compat matrix)
- [ ] DEC-04: UI shell architecture committed (Dockview-core, Split.js migration plan, CSS token vocab)
- [ ] SYN-01: DECISIONS.md created (cross-cutting decisions, v2.2 phase structure, tech debt schedule)
- [ ] TECH-01: Alembic migration runner at startup (replaces create_all)
- [ ] TECH-02: SMTP email delivery (magic links sent via real email, not console)
- [ ] TECH-03: Session cleanup job (purge expired sessions)
- [ ] TECH-04: ViewSpecService TTL cache (reduce SPARQL queries per view lookup)

### Future Candidates

<!-- Tracked for future milestones. See .planning/research/future-milestones.md for full breakdown. -->

<!-- Full breakdown with dependency map and parallelization strategy: .planning/research/future-milestones.md -->

**v2.1 — Research & Architecture Decisions** (parallel research phases)
- Full-text search + vector store research (RDF stores with FTS, OpenSearch, pgvector, etc.)
- SPARQL interface research (Zazuko Yasgui, modern tooling, embed vs. iframe vs. mimic)
- Virtual filesystem WebDAV MVP (research at .planning/research/virtual-filesystem.md)
- UI shell architecture: theming + flexible panel layout (current arch handles this — see decision log)

**v2.2 — Data Discovery & Search**
- Full-text indexing implementation (technology from v2.1 research)
- SPARQL interface integration (beautiful, autocomplete, object pills, saved queries, history)
- Virtual filesystem MVP (read-only WebDAV mount, MountSpec vocabulary, Markdown+frontmatter rendering)

**v2.3 — Shell & Navigation**
- Dashboards / named layouts (Bases equivalent — user-defined, model-provided named panel arrangements)
- Flexible panel layout (GoldenLayout or similar for drag-to-dock panel rearrangement)
- Full theming system (CSS variable token sets, user-selectable themes, model-contributed themes)
- App launcher concept (object browser as primary "app"; SPARQL interface, etc. as installable apps)

**v2.4 — Low-Code & Workflows**
- Low-code UI builder (compose basic components tied to SemPKM actions; Notion + Airflow inspired)
- Minimal workflow orchestration (orchestrated forms/views, not n8n; e.g. CRM onboarding: add client → add project → add invoice → log success)
- SMTP integration for magic link delivery
- Cookie secure=True for production deployment
- Session cleanup job

**Ongoing / cross-cutting**
- Backlinks panel (incoming references for any object)
- Edge model enhancements: edge inspector panel, inline wiki-link creation
- JSON-LD export for objects/collections
- AI Copilot (chat about data, SPARQL generation, writing assistance, relationship suggestions)
- CONCERNS.md tech debt: EventStore DI, label cache invalidation, datetime timezone, CORS, Alembic migration runner

### Out of Scope

- Read/write filesystem projections — v2 (read-only projection also deferred)
- Mental Model migrations and user overrides — v2+
- Offline/multi-device sync — v2+
- Advanced webhook delivery/security (DLQ, signing, strict ordering) — v3
- Bidirectional ActivityPub — v2+
- SOLID export/publish — deferred
- Timeline/calendar renderers — v2+
- 3D graph visualization — experimental, deferred
- SPARQL UPDATE as external write surface — by design (bypasses event sourcing)
- Real-time collaborative editing — CRDT/OT complexity, v2+ at earliest
- Mobile native app — web-first, responsive design and eventual PWA
- Ontology editor — consume via Mental Models; use Protege for authoring

## Current Milestone: v2.1 Architecture Decision Gate

**Goal:** Formalize the 4 completed architectural research tracks into committed decision artifacts and resolve medium-priority tech debt.

**Target features:**
- DEC: Commit and annotate all 4 research documents (FTS, SPARQL UI, VFS, UI shell)
- SYN: Produce consolidated DECISIONS.md with v2.2 implementation guidance
- TECH: Alembic migration runner, SMTP delivery, session cleanup, ViewSpecService cache

## Context

**Current state (v2.0 shipped 2026-03-01):**
- ~119k source LOC across Python, JavaScript, CSS, HTML/Jinja2, JSON-LD
- Tech stack: FastAPI + RDF4J + htmx/vanilla-web + SQLAlchemy (SQLite) + Driver.js + Cytoscape.js + CodeMirror + Split.js
- Docker Compose deployment: 3 services (api, triplestore, frontend/nginx)
- 19 phases, 27 plans, 53 tasks, ~360 commits

**Design references:**
- v0.3 design documents in `orig_specs/` (vision, specifications, decision log, schemas)
- `semantic-stack` reference project for triplestore Docker deployment

**Known tech debt:**
- Cookie secure=False (local dev only — production config deferred)
- SMTP deferred (magic link tokens logged to console)
- Dual SQLAlchemy engine instances (module-level + lifespan) — harmless for SQLite
- `empty_shapes_loader` dead code in validation service
- Bottom panel SPARQL/AI Copilot tabs are placeholder stubs
- Edit form helptext property not yet in SHACL types (pending todo)

## Standing Requirements (every phase)

These apply to every plan, no exceptions. Executor must check both gates before writing the SUMMARY.

- **E2E tests**: Any new or changed user-visible behavior must have Playwright tests added or updated in `e2e/tests/`. Tests must pass against the running stack.
- **User guide docs**: Any user-visible feature added or changed must be reflected in `docs/` (user guide, tutorials). Create new pages if needed. If skipped (e.g. pure backend fix), state the reason explicitly in the SUMMARY.

## Constraints

- **Backend**: Python + FastAPI (async, Pydantic models, OpenAPI docs)
- **Frontend**: htmx + vanilla JavaScript throughout (admin, workspace, views)
- **Triplestore**: RDF4J 5.x, deployed via Docker (internal only, no host port exposure)
- **Auth database**: SQLAlchemy async ORM (SQLite local, PostgreSQL for cloud)
- **Events**: Stored as RDF in named graphs within the triplestore (triplestore-native event sourcing)
- **Deployment**: Self-hosted Docker Compose (3 services)
- **Auth**: Passwordless (setup token local, magic links cloud), session-based cookies
- **Standards**: RDF, SPARQL 1.1, SHACL Core (pragmatic subset), JSON-LD for models

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Event sourcing as canonical truth | Supports automation, auditability, future sync strategies | ✓ Good — immutable events enable provenance tracking, audit trail |
| Edges as first-class resources (sempkm:Edge) | UX needs stable edge identity for inspection, annotation, provenance | ✓ Good — clean edge CRUD, minted IRIs |
| SHACL subset drives UI (forms + linting) | SHACL already encodes field structure, constraints, severity, layout hints | ✓ Good — auto-generated forms from shapes, lint panel with violations/warnings |
| Triplestore-native event storage | Events as RDF named graphs, keeping everything in one data layer | ✓ Good — atomic transactions, no separate event store |
| htmx throughout (no React) | Simpler architecture, htmx + vanilla JS sufficient for all UI needs | ✓ Good — eliminated iframe complexity, consistent stack |
| RDF4J over Blazegraph | Blazegraph unmaintained since 2020; RDF4J actively maintained | ✓ Good — stable, well-documented API |
| FastAPI backend | Modern Python async framework, OpenAPI docs, Pydantic models | ✓ Good — clean async patterns, dependency injection |
| Passwordless auth with magic links | Zero-friction UX, no password management complexity | ✓ Good — setup wizard + auto-login for local dev |
| SQLite for local auth, PostgreSQL for cloud | Dual-database strategy for zero-config local and scalable cloud | ✓ Good — Alembic migrations work for both |
| Violations gate conformance ops only | SHACL is assistive (linting), not punitive — users can always edit | ✓ Good — export/publish blocked, saves always allowed |
| Filesystem projection deferred | Focus v1 on the core create/browse/explore loop first | ✓ Good — avoided scope creep, v1 loop is complete |
| Private-by-default cross-model embedding | Explicit exports prevent accidental coupling between Mental Models | — Pending (not yet exercised with multiple models) |

---
*Last updated: 2026-03-01 after v2.1 milestone started*
