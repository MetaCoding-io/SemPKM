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

### Validated (v2.2)

<!-- Shipped and confirmed valuable in v2.2. -->

- ✓ FTS-01: Full-text keyword search across all literal values via RDF4J LuceneSail — v2.2
- ✓ FTS-02: Search results show object type, label, and matching text snippet — v2.2
- ✓ FTS-03: Keyword search integrated into Ctrl+K command palette — v2.2
- ✓ SPARQL-01: Embedded Yasgui SPARQL console in workspace bottom panel — v2.2
- ✓ SPARQL-02: SPARQL results display IRIs as clickable SemPKM object pill links — v2.2
- ✓ SPARQL-03: Query history and tabs preserved across sessions (localStorage) — v2.2
- ✓ VFS-01: WebDAV mount via wsgidav + a2wsgi bridge, objects browsable as files — v2.2
- ✓ VFS-02: Object bodies rendered as Markdown files with SHACL-derived frontmatter — v2.2
- ✓ VFS-03: API token auth + mount config accessible from Settings page — v2.2
- ✓ POLSH-01: Expander/collapse icons visible in sidebar tree in both light and dark themes — v2.2
- ✓ POLSH-02: User can drag sidebar panels between left/right sidebar, position persists — v2.2
- ✓ POLSH-03: Object-contextual panels show accent indicator; deactivate on non-object focus — v2.2
- ✓ POLSH-04: Playwright E2E test files for SPARQL console, FTS, and VFS — v2.2

### Validated (v2.1)

<!-- Shipped and confirmed valuable in v2.1. -->

- ✓ DEC-01: RDF4J LuceneSail committed as FTS approach — rationale documented, alternatives ruled out, v2.2 handoff written — v2.1
- ✓ DEC-02: `@zazuko/yasgui` v4.5.0 CDN embed committed as SPARQL UI — custom YASR renderer design, localStorage persistence — v2.1
- ✓ DEC-03: wsgidav + a2wsgi committed as VFS/WebDAV approach — FUSE ruled out, MountSpec MVP vocabulary defined — v2.1
- ✓ DEC-04: dockview-core committed over GoldenLayout — incremental Split.js migration plan (Phase A/B/C), CSS token expansion to ~91 tokens — v2.1
- ✓ SYN-01: DECISIONS.md created at .planning/DECISIONS.md — consolidated v2.2 architecture reference with Phases 23-27 sequencing — v2.1
- ✓ TECH-01: Alembic migration runner at startup (replaces create_all; asyncio.to_thread bridge for env.py) — v2.1
- ✓ TECH-02: SMTP email delivery for magic links (send_magic_link_email, console fallback, app_base_url config) — v2.1
- ✓ TECH-03: Session cleanup job (expired sessions purged on startup, non-zero count logged) — v2.1
- ✓ TECH-04: ViewSpecService TTL cache (300s TTL, 64 max entries, invalidation wired to model install/uninstall) — v2.1

### Validated (v2.3)

<!-- Shipped and confirmed valuable in v2.3. -->

- ✓ DOCK-01: Dockview Phase A migration — replace Split.js editor-pane area with dockview-core panels — v2.3
- ✓ DOCK-02: Named workspace layouts (user-defined save/restore via Command Palette) — v2.3
- ✓ VIEW-01: Object view redesign — markdown-first with properties hidden by default — v2.3
- ✓ VIEW-02: Carousel views — per-type manifest-declared view tab bar — v2.3
- ✓ FTS-04: FTS fuzzy search — typo-tolerant matching with user-controlled toggle — v2.3
- ✓ BUG-01: Group-by in concept cards view fixed — v2.3
- ✓ BUG-02: VFS Settings UI restored — v2.3
- ✓ BUG-03: Broken view switch buttons removed, replaced by carousel tab bar — v2.3
- ✓ TEST-01 through TEST-04: Full E2E test coverage for SPARQL, FTS, VFS, and v2.3 features — v2.3

### Validated (v2.4)

<!-- Shipped and confirmed valuable in v2.4. -->

- ✓ INF-01: OWL 2 RL inference — automatic inverse property materialization (owlrl, inferred named graph) — v2.4
- ✓ INF-02: SHACL-AF rules — Mental Models ship sh:TripleRule/sh:SPARQLRule, pyshacl advanced=True — v2.4
- ✓ LINT-01 through LINT-07: Global lint dashboard — filterable, sortable validation view with SSE auto-refresh, health badge — v2.4
- ✓ HELP-01: Edit form helptext — sempkm:editHelpText SHACL annotation, collapsible markdown — v2.4
- ✓ BUG-04 through BUG-10: Bug fix batch — accent bar, card borders, Firefox Ctrl+K, tab bleed, dark chevrons, concept search, flip card bleed-through — v2.4
- ✓ VFS-01: In-app VFS browser — dockview tab with tree navigation (model → type → objects) — v2.4
- ✓ TEST-05: E2E test coverage for v2.4 features (inference data flow, lint dashboard, helptext) — v2.4

### Active

<!-- Next milestone requirements will be defined via /gsd:new-milestone -->

(No active requirements — next milestone not yet planned)

### Future Candidates

<!-- Tracked for future milestones. -->

**v2.5+ — Dockview Phase B & Theming**
- Flexible panel layout: dockview-core Phase B (sidebar panels into dockview)
- Model-provided default layouts in Mental Model manifest
- Full theming system (CSS variable token sets, user-selectable themes, model-contributed themes)

**Future — Low-Code & Workflows**
- Low-code UI builder (compose basic components tied to SemPKM actions)
- Minimal workflow orchestration (orchestrated forms/views, not n8n)

**Ongoing / cross-cutting**
- Backlinks panel (incoming references for any object)
- Edge model enhancements: edge inspector panel, inline wiki-link creation
- JSON-LD export for objects/collections
- AI Copilot (chat about data, SPARQL generation, writing assistance)
- pgvector / semantic search (deferred until keyword FTS validated in v2.2)

### Out of Scope

- Read/write filesystem projections full sync — v2.3+ (VFS write MVP is v2.2)
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

## Current State

**Latest shipped: v2.4 Inference & Polish (2026-03-06)**

**What shipped in v2.4:**
- OWL 2 RL inference engine — owlrl materializes inverse/transitive triples into `urn:sempkm:inferred` graph
- SHACL-AF rules — Mental Models ship sh:TripleRule/sh:SPARQLRule, pyshacl advanced=True
- Global lint dashboard — filterable, sortable validation results with SSE auto-refresh and health badge
- Edit form helptext — sempkm:editHelpText SHACL annotation as collapsible markdown
- In-app VFS browser — dockview tab with tree navigation (model → type → objects)
- Bug fix batch — 7 fixes (accent bar, card borders, flip card, dark chevrons, concept search, Firefox Ctrl+K, tab bleed)
- E2E tests for all v2.4 features including full inference data flow test

**Next milestone:** Not yet planned — run `/gsd:new-milestone`

## Context

**Current state (v2.4 shipped 2026-03-06):**
- ~140k source LOC across Python, JavaScript, CSS, HTML/Jinja2, JSON-LD
- Tech stack: FastAPI + RDF4J (LuceneSail) + htmx/vanilla-web + SQLAlchemy (SQLite/PostgreSQL) + wsgidav + a2wsgi + Driver.js + Cytoscape.js + CodeMirror + dockview-core + Alembic + Yasgui CDN + ninja-keys + owlrl + pyshacl
- Docker Compose deployment: 3 services (api, triplestore, frontend/nginx)
- 43 phases, 95 plans completed across v1.0, v2.0, v2.1, v2.2, v2.3, v2.4

**Known tech debt:**
- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (module-level + lifespan) — harmless for SQLite
- Seed data has both inverse sides pre-populated (owl:inverseOf produces 0 new triples with current data)

**Design references:**
- v0.3 design documents in `orig_specs/` (vision, specifications, decision log, schemas)
- `semantic-stack` reference project for triplestore Docker deployment
- `.planning/DECISIONS.md` — canonical v2.2 architecture reference

## Standing Requirements (every phase)

These apply to every plan, no exceptions. Executor must check both gates before writing the SUMMARY.

- **E2E tests**: Any new or changed user-visible behavior must have Playwright tests added or updated in `e2e/tests/`. Tests must pass against the running stack.
- **User guide docs**: Any user-visible feature added or changed must be reflected in `docs/` (user guide, tutorials). Create new pages if needed. If skipped (e.g. pure backend fix), state the reason explicitly in the SUMMARY.

## Constraints

- **Backend**: Python + FastAPI (async, Pydantic models, OpenAPI docs)
- **Frontend**: htmx + vanilla JavaScript throughout (admin, workspace, views)
- **Triplestore**: RDF4J 5.x, deployed via Docker (internal only, no host port exposure)
- **Auth database**: SQLAlchemy async ORM (SQLite local, PostgreSQL for cloud) + Alembic migrations
- **Events**: Stored as RDF in named graphs within the triplestore (triplestore-native event sourcing)
- **Deployment**: Self-hosted Docker Compose (3 services)
- **Auth**: Passwordless (setup token local, magic links cloud), session-based cookies
- **Standards**: RDF, SPARQL 1.1, SHACL Core (pragmatic subset), JSON-LD for models

## UI Design Principles

### Contextual vs. Non-Contextual Views

Workspace panels and views fall into one of two categories:

**Contextual** — their content depends on what the user has currently focused. They show information *about* a specific object or result set. Examples: the Relations panel, the Lint panel, an object detail page. These should only display active content (and show their accent indicator) when the user's focus is on something that provides context — e.g. an open object tab. If focus shifts to a non-contextual view, they show a "no object selected" placeholder.

**Non-contextual** — their content is independent of user focus. Examples: Settings, the Docs tab, a table or card view browsing a query result set. A table view shows a collection; no single object is "chosen" until the user selects one. A graph view similarly has no selection until the user picks a node.

**Implementation rule:** The accent bar and panel content are driven by the *focused* tab, not by whether *any* object tab is open. Switching to Settings or a table view turns the accent off immediately. Only when an object tab is focused — or a graph node is explicitly selected — should the contextual panels activate.

This distinction must be preserved as new view types are added. Ask: "does this view inherently mean a specific object or result set is chosen?" If yes, it is contextual. If no, it is not.

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
| DEC-01: RDF4J LuceneSail for FTS | Zero new containers, SPARQL-native, ships with RDF4J 5.0.1 | ✓ Good — committed v2.1, implementation in Phase 24 |
| DEC-02: @zazuko/yasgui CDN embed | De facto standard, MIT-licensed, zero backend changes needed | ✓ Good — committed v2.1, implementation in Phase 23 |
| DEC-03: wsgidav + a2wsgi for VFS | Docker-compatible, HTTP-only, FUSE requires SYS_ADMIN (rejected) | ✓ Good — committed v2.1, read-only MVP in Phase 26 |
| DEC-04: dockview-core over GoldenLayout | GoldenLayout DOM reparenting breaks htmx handlers; dockview-core zero deps | ✓ Good — committed v2.1, Phase A migration in v2.3 |
| asyncio.to_thread for Alembic | env.py uses asyncio.run internally; nested event loop requires thread isolation | ✓ Good — Alembic running in production (v2.1) |
| LuceneSail config: RDF4J 5.x unified namespace | config:lucene.indexDir + config:delegate (not lucene: namespace); discovered from container-generated config.ttl | ✓ Good — FTS operational in v2.2 |
| Yasgui lazy init via tab click handler | Prevents JS errors when SPARQL panel is closed; init only on tab activation | ✓ Good — no console errors on workspace load |
| wsgidav begin_write/end_write hooks | write_data() does not exist in installed wsgidav version; begin/end hooks are correct API | ✓ Good — VFS write path operational in v2.2 |
| API token hard-delete revocation | Soft-delete (revoked_at) adds filter complexity; hard-delete is cleaner and immediate | ✓ Good — revocation instant, list queries clean |
| HTML5 drag-reorder for sidebar panels | No dockview needed for simple panel position swap; [data-panel-name] + [data-drop-zone] attributes, localStorage persistence | ✓ Good — lightweight, no dependency added |
| sempkm:tab-activated custom event | Decouples workspace.js from workspace-layout.js for contextual panel indicator; dispatched on openTab()/switchTabInGroup() | ✓ Good — clean separation, panel indicator works |

---
*Last updated: 2026-03-03 after v2.4 milestone start*
