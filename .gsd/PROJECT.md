# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

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

### Validated (v2.5)

<!-- Shipped and confirmed valuable in v2.5. -->

- ✓ UICL-01: VFS browser markdown preview renders at correct font size — v2.5
- ✓ UICL-02: VFS browser content free of unwanted underline styling — v2.5
- ✓ UICL-03: UI polish pass — tab type icons, sidebar accent, helptext validation, keyboard shortcuts — v2.5
- ✓ OBSI-01: User can upload Obsidian vault ZIP for scanning — v2.5
- ✓ OBSI-02: Scan results show file count, detected types, frontmatter keys, link targets, and tags — v2.5
- ✓ OBSI-03: Interactive mapping of Obsidian note categories to Mental Model types — v2.5
- ✓ OBSI-04: Frontmatter key to RDF property mapping per type — v2.5
- ✓ OBSI-05: Preview of mapped objects before committing import — v2.5
- ✓ OBSI-06: Batch import creates objects with bodies, properties, and edges via Command API — v2.5
- ✓ OBSI-07: Wiki-links and tags resolved to edges between imported objects — v2.5
- ✓ WBID-01: Each user has a WebID URI (e.g. `https://instance/users/alice#me`) — v2.5
- ✓ WBID-02: Dereferencing WebID URI returns RDF profile document — v2.5
- ✓ WBID-03: Content negotiation serves Turtle, JSON-LD, or HTML — v2.5
- ✓ WBID-04: Profile page includes `rel="me"` links for fediverse verification — v2.5
- ✓ WBID-05: Server generates Ed25519 key pair per user, stores encrypted — v2.5
- ✓ WBID-06: Public key published in WebID profile document — v2.5
- ✓ IAUTH-01: Server exposes `rel="indieauth-metadata"` for client discovery — v2.5
- ✓ IAUTH-02: OAuth2 authorization code flow with mandatory PKCE — v2.5
- ✓ IAUTH-03: Token endpoint issues access tokens after code exchange — v2.5
- ✓ IAUTH-04: Token endpoint supports verification/introspection — v2.5
- ✓ IAUTH-05: Consent screen showing requesting app and requested scopes — v2.5
- ✓ DOCS-01: User guide covers all features shipped since v2.0 — v2.5
- ✓ DOCS-02: Each major feature has dedicated user guide page — v2.5
- ✓ DOCS-03: Existing pages updated to reflect current UI state — v2.5

### Validated (v2.6)

<!-- Shipped and confirmed valuable in v2.6. -->

- ✓ SPARQL Interface — permissions, autocomplete, IRI pills, server-side history, saved/shared queries, named queries as views — v2.6
- ✓ Collaboration & Federation — RDF Patch, named graph sync, LDN notifications, federated WebID auth, collaboration UI — v2.6
- ✓ User Custom VFS (MountSpec) — declarative vocabulary, 5 directory strategies, SHACL frontmatter writes, management UI — v2.6
- ✓ VFS Browser UX Polish — navigation, preview pane, breadcrumbs, file operations — v2.6
- ✓ Object Browser UI Improvements — refresh/plus icons, multi-select, contextual delete, edge inspector, view filtering — v2.6
- ✓ Event Log Fixes — missing diffs, rendering issues — v2.6
- ✓ Lint Dashboard Fixes — layout width, walkthrough improvements — v2.6
- ✓ Spatial Canvas UI Improvements — snap-to-grid, edge labels, keyboard nav, bulk drag-drop, wiki-link edges — v2.6

### Validated (M002 — Hardening & Polish)

<!-- Validated during M002 hardening milestone (2026-03-12). -->

- ✓ SEC-01–05: Security hardening — rate-limited auth, conditional token logging, owner-only event console, SPARQL regex escaping, BASE_NAMESPACE docs — M002
- ✓ COR-01–03: Correctness fixes — stable validation hash, SPARQL string-literal-safe scoping, per-spec source_model attribution — M002
- ✓ TEST-01–04: Backend test foundation — pytest infrastructure with 130 unit tests covering SPARQL escaping, IRI validation, auth tokens, scoping edge cases — M002
- ✓ REF-01: Browser router refactored from 1956-line monolith to 8 domain sub-modules with zero behavior change — M002
- ✓ DEP-01–02: Dependency pinning — ~= compatible release pins, uv.lock committed — M002
- ✓ PERF-01: Event detail N+1 user lookup replaced with batched WHERE IN query — M002
- ✓ FED-11–13: Federation fixes — Sync Now auto-discovery, dual-instance docker-compose, 8-step E2E test — M002
- ✓ OBSI-08–10: Ideaverse Pro 2.5 vault imported (895 objects, 1767 edges), wiki-links and frontmatter verified — M002

### Validated (M003 — Workspace UX & Knowledge Organization)

<!-- Shipped and confirmed in M003. -->

- ✓ Explorer mode dropdown: switchable navigation strategies (by-type, by-hierarchy, by-tag, VFS mounts) — M003
- ✓ Tag system fix (comma-separated → individual triples) + tag pills with # prefix + tag explorer mode — M003
- ✓ Per-user favorites with SQL storage, star toggle, FAVORITES explorer section — M003
- ✓ Threaded collaborative comments on objects via RDF EventStore — M003
- ✓ Ontology viewer: TBox Explorer, ABox Browser, RBox Legend — M003
- ✓ Gist 14.0.0 loaded as upper ontology foundation, mental model alignment — M003
- ✓ In-app class creation (name, icon, parent, properties → OWL + SHACL) via Ontology Viewer — M003
- ✓ Admin model detail real stats and Chart.js charts — M003 (chart htmx loading bug fixed post-M003)
- ✓ E2E test coverage gap fill: 82 spec files total — M003

### Validated (M004 — Ontology & Type System Completion)

<!-- Shipped and confirmed in M004 (2026-03-14). -->

- ✓ PROP-01: In-app property creation (ObjectProperty and DatatypeProperty) from RBox tab — M004
- ✓ PROP-02: Property editing (rename, change domain/range) from RBox and Custom section — M004
- ✓ PROP-03: Property deletion with confirmation — M004
- ✓ TYPE-05: Class editing (rename, icon, parent, properties, SHACL shape replacement) — M004
- ✓ TYPE-06: Class deletion with instance-count and subclass-count warnings — M004
- ✓ TYPE-07: Custom section on Mental Models page listing user types/properties — M004
- ✓ TAB-01: Create-new-object opens fresh dockview tab — M004
- ✓ User guide: 6 new sections in chapter 10 covering all M004 features — M004
- ✓ Unit test coverage: 114 ontology tests, 386 total backend tests — M004

### Validated (M005 — Platform Polish & Foundation)

<!-- Shipped and confirmed in M005 (2026-03-14). -->

- ✓ Query SQL→RDF migration: saved queries, history, sharing, promotion stored as RDF — M005
- ✓ Operations log with PROV-O vocabulary (prov:Activity, prov:startedAtTime, prov:wasAssociatedWith) — M005
- ✓ Hierarchical tag tree: `/`-delimited nesting at arbitrary depth in By Tag explorer — M005
- ✓ Tag autocomplete: type-ahead suggestions in edit forms with frequency ordering — M005
- ✓ Model schema refresh: POST endpoint updates artifact graphs without uninstall — M005
- ✓ Design docs: PROV-O alignment, views rethink, VFS v2 design refinement — M005
- ✓ E2E test coverage: 5 new Playwright tests for M005 features — M005
- ✓ User guide: 4 chapters updated (workspace, objects, models, debugging) — M005

### Validated (M006 — Dashboards, Workflows & Platform Alignment)

<!-- Shipped and confirmed in M006 (2026-03-15). -->

- ✓ PROV-O migration: all event/comment/query predicates renamed to PROV-O equivalents (6 predicates, 13 files, idempotent migration script) — M006
- ✓ Explorer tree consolidated: ViewSpecs grouped by model (~5 entries instead of 31+ flat), duplicate routes removed — M006
- ✓ VFS scope dropdown fixed: correct fetch URL, optgroup rendering, saved query resolution wired — M006
- ✓ Dashboard subsystem: DashboardSpec model, CSS Grid rendering (5 layouts, 6 block types), builder UI, explorer section — M006
- ✓ Cross-view context filtering: parameterized SPARQL VALUES injection, dashboardContextChanged event chain, row selection → filtered re-fetch — M006
- ✓ Workflow subsystem: WorkflowSpec model, stepper runner UI, builder UI, explorer section — M006
- ✓ Delete UI for both dashboards and workflows with explorer integration — M006
- ✓ 93 new unit tests across 7 test files (641 total), zero regressions — M006

### Validated (M007 — Generic Views, VFS Completion & Polish)

<!-- Shipped and confirmed in M007 (2026-03-16). -->

- ✓ VIEW-01–05: Generic views — 3 generic ViewSpec entries (Table/Cards/Graph) with SHACL-driven dynamic columns, type filter pills, carousel integration, explorer consolidation (flat entries + Saved Views folder) — M007
- ✓ VFS-07–12: VFS completion — type filter with VALUES clause, scopeQuery IRI alignment with migration, preview scope resolution (async/sync), path contract docs + 26 tests, composable strategy chains (up to 3 levels), filename templates with variable expansion — M007
- ✓ UIPOL-01: UI polish — Lucide sidebar chevrons, always-visible OBJECTS buttons, DASHBOARDS/WORKFLOWS header plus-buttons, normalized inference button, accent Ontology Viewer, horizontal relationships graph — M007
- ✓ DOCS-04: User guide Chapter 28 covering dashboards and workflows, 6 glossary entries — M007
- ✓ 120 new unit tests (761 total), zero regressions — M007

### Validated (M008 — Spatial Canvas)

<!-- Shipped and confirmed in M008 (2026-03-16). -->

- ✓ CANVAS-01: Resizable canvas nodes with free drag handles, width/height stored per-node — M008
- ✓ CANVAS-02: Property flip on canvas object nodes (SHACL-derived table, inline rendering) — M008
- ✓ CANVAS-03: Live view and dashboard embeds on canvas (dual-layer rendering, iframe persistence) — M008
- ✓ CANVAS-04: SPARQL query and object read embeds on canvas — M008
- ✓ CANVAS-05: Embed add UX (toolbar picker + drag from explorer) — M008
- ✓ E2E tests: 5 Playwright spec files covering canvas API, resize, UI, property flip, and embeds — M008
- ✓ User guide Chapter 27 updated with resize, property flip, live embeds documentation + glossary entries — M008

### Validated (M011 — Mental Models Expansion)

<!-- Shipped and confirmed in M011 (2026-03-17). -->

- ✓ MODEL-01: basic-pkm v2.0 with Task and Milestone types (6 types total, overdue-task SHACL-AF warning, 18 ViewSpecs, 6 SavedQueries) — M011
- ✓ MODEL-02: Personal CRM with Contact/Company/Interaction/Deal (SHACL-AF inference + validation, pipeline views, 12 seed objects) — M011
- ✓ MODEL-03: Zettelkasten+ with 5 note types (provenance chain, argumentation links, 3 validation rules) — M011
- ✓ MODEL-04: Research Workflow with 5 types (confidence levels, evidence tracking, 4 validation rules, Evidence Map graph) — M011
- ✓ Cross-model coexistence verified (10 offline tests, 0 namespace collisions, graph merge clean) — M011
- ✓ E2E Docker lifecycle for all 4 models (install → create → form render → inference → lint) — M011
- ✓ User guide Chapter 29 (608 lines, 15 glossary entries) documenting all 4 models — M011

### Validated (M012 — Workspace & Event Log Polish)

<!-- Shipped and confirmed in M012 (2026-03-17). -->

- ✓ EVTLOG-01–03: Event log labels, helptext tooltips, autocomplete for filter fields — M012
- ✓ BDIFF-01–03: Body.diff incremental storage and rendering with backward compat — M012
- ✓ PERSONA-01–05: Workspace personas — CRUD, sidebar selector, command palette, layout/positions/mode save and restore — M012
- ✓ 12 E2E Playwright tests + user guide Chapter 15 updated + Chapter 30 (personas) + glossary — M012

### Validated (M013 — API Surface for External Clients)

<!-- Shipped and confirmed in M013 (2026-03-17). -->

- ✓ API-01: Well-known instance discovery endpoint (`GET /.well-known/sempkm`) — M013
- ✓ API-02: Types endpoint with labels, icons, and model attribution (`GET /api/types`) — M013
- ✓ API-03: SHACL shapes endpoint as structured JSON (`GET /api/shapes/{type_iri}`) — M013
- ✓ API-04: Context-query endpoint for related objects (`POST /api/context-query`) — M013
- ✓ API-05: Dual-auth dependency (session cookie + Bearer API token) — M013
- ✓ API-06: CORS headers for browser extension access (nginx) — M013
- ✓ API-07: nginx Authorization header forwarding on `/api/` — M013
- ✓ API-08: API surface user guide Chapter 31 with 3 glossary entries — M013
- ✓ 62 unit tests + 7 E2E Playwright tests across all endpoints — M013

### Validated (M009 — App Platform + M010 — RSS Reader App)

<!-- Shipped and confirmed in M009 (2026-03-18) and M010 (2026-03-18). -->

- ✓ APP-01–14: App platform — manifest validation, subprocess lifecycle (crash recovery, auto-start), App SDK with scoped clients, IPC over unix domain socket, permission enforcement, task scheduler, 3-level frontend integration (standalone pages, workspace contributions, object renderers), admin monitoring portal, bulk EventStore, browserVisible field, database migrations, Docker/nginx integration — M009
- ✓ RSS-01: Feed subscription + polling — RSS/Atom/JSON Feed by URL, configurable poll interval, bulk EventStore article ingestion, per-feed error tracking — M010
- ✓ RSS-02: Reader UI — split-pane layout (feed sidebar, article list, reading pane), clean typography, star toggle, mark read/unread — M010
- ✓ RSS-03: Custom Article renderer — replaces default SHACL form when opening article from object browser — M010
- ✓ RSS-05: OPML import — upload file to create multiple subscriptions, categories preserved as tags — M010
- ✓ RSS-06: Workspace contributions — Unread/Starred views, Related Articles right pane, command palette entries — M010
- ✓ RSS-07: rss-feeds Mental Model — Article, FeedSubscription types with OWL/SHACL/ViewSpecs — M010
- ✓ RSS-08: Feed content extraction — feed discovery from website URLs, trafilatura full content extraction, fallback to summaries — M010
- ✓ 663-line Playwright E2E spec (58 assertions, 15 phases), Chapter 32 user guide (305 lines), 4 glossary entries — M010

### Validated (M014 — Browser Extension Phase 1)

<!-- Shipped and confirmed in M014 (2026-03-18). -->

- ✓ EXT-01: Extension popup capture with type selector grouped by model, save flow via SemPKMClient — M014
- ✓ EXT-02: SHACL-driven dynamic forms (10 property types, groups, multi-value, skip paths, helptext) — M014
- ✓ EXT-03: Auto-population from page metadata (title, URL, selected text) via chrome.scripting.executeScript — M014
- ✓ EXT-04: Relationship picker with search-as-you-type, type filtering, two-step save (object.create → edge.create) — M014
- ✓ EXT-05: Context menu "Save to SemPKM" with session storage bridge to popup — M014
- ✓ EXT-06: Schema.org JSON-LD auto-fill (Person→Contact, Article→Note, cross-namespace property mapping) — M014
- ✓ EXT-07: Extension settings page with connection test, type selector, capture behavior toggles — M014
- ✓ EXT-08: Alt+S keyboard shortcut in both Chrome and Firefox manifests — M014
- ✓ EXT-09: Success/error toast feedback, connection status indicator, loading states — M014
- ✓ EXT-10: Cross-browser compatibility (Chrome MV3 + Firefox WebExtension via dual manifests) — M014
- ✓ EXT-11: Backend Bearer token auth via require_role_or_api on POST /api/commands (10 unit tests) — M014
- ✓ EXT-12: User guide Chapter 32 (12 sections), 2 glossary entries, README TOC — M014
- ✓ EXT-13: 3 Playwright E2E tests for extension capture flow with persistent context fixture — M014

### Validated (M015 — Browser Extension Phase 2)

<!-- Shipped and confirmed in M015 (2026-03-18). -->

- ✓ EXT-15: Knowledge sidebar opens via Alt+K showing grouped results from context query — M015
- ✓ EXT-16: Open action navigates to SemPKM object in new tab — M015
- ✓ EXT-17: Link to this page action creates schema:url edge — M015
- ✓ EXT-19: Auto-context toggle in settings controls badge/check behavior — M015
- ⊘ EXT-14: Badge count (partial — same pipeline as sidebar, badge API inaccessible from tests) — M015
- ⊘ EXT-18: Add Evidence (partial — code review confirmed, content script selection not E2E testable) — M015
- ⊘ EXT-20: URL→results cache (partial — 23 unit tests prove LRU logic, not E2E exercised) — M015
- ⊘ EXT-21: Cross-browser (partial — Chromium E2E passes, Firefox manifest syntax-checked only) — M015
- ✓ 4 Playwright E2E tests, Chapter 33 user guide (257 lines), 3 glossary entries — M015

### Validated (M016 — Linear Sync App)

<!-- Shipped and confirmed in M016 (2026-03-18). -->

- ✓ SYNC-01: Linear OAuth and API key authentication — both methods implemented and unit-tested — M016
- ✓ SYNC-02: Pull sync — Linear issues to bpkm:Task with full field mapping (status, priority, assignee, labels, due date, effort, URL) — M016
- ✓ SYNC-03: Push sync — change detection, reverse field mapping, issueUpdate mutations, loop prevention — M016
- ✓ SYNC-04: Settings UI — team selection, sync direction toggle, poll interval, Sync Now button — M016
- ✓ SYNC-05: Admin sync history — platform Task History + settings page sync stats — M016
- ✓ SYNC-06: Person matching — email-based SPARQL lookup with creation on miss — M016
- ✓ SYNC-07: Provider icon and external link on synced tasks — M016
- ✓ 189 unit tests across 6 test files, mock Linear API server, Playwright E2E test (11 phases), Chapter 34 user guide — M016

### Validated (M017 — GitHub Issues Sync App)

<!-- Shipped and confirmed in M017 (2026-03-18). -->

- ✓ GH-01: GitHub PAT authentication — store/verify/disconnect/masked preview, 15 unit tests — M017
- ✓ GH-02: Pull sync — GitHub issues to bpkm:Task with status/labels/assignee/body/URL field mapping, 68 unit tests — M017
- ✓ GH-03: PR sync + issue linking — PRs as bpkm:Task with "github-pr" provider, timeline API edge creation, 32 unit tests — M017
- ✓ GH-04: Push sync — SPARQL change detection, reverse field mapping, PATCH API, loop prevention, 33 unit tests — M017
- ✓ GH-05: Settings UI — repo selection, sync direction, poll interval, sync stats, 15 unit tests — M017
- ✓ GH-06: Person matching — email/login SPARQL lookup with LRU cache, 10 unit tests — M017
- ✓ GH-07: E2E + docs — mock GitHub REST API (9 selftest), 12-phase Playwright E2E (partial), Chapter 35 user guide — M017
- ✓ 204 unit tests across 5 test files, mock REST API server, Playwright E2E test (12 phases), Chapter 35 user guide — M017

### Validated (M023 — Jira Sync App)

<!-- Shipped and confirmed in M023 (2026-03-19). -->

- ✓ JIRA-01: ADF→Markdown conversion — 95 unit tests proving all 12+ ADF node types — M023
- ✓ JIRA-02: Markdown→ADF reverse conversion — line-by-line state machine for push sync — M023
- ✓ JIRA-03: statusCategory-based status normalization — new→todo, indeterminate→in-progress, done→done — M023
- ✓ JIRA-04: Priority mapping — 8 Jira names → 4 bpkm values with reverse maps — M023
- ✓ JIRA-05: Jira REST API client — JQL search, pagination, error hierarchy — M023
- ✓ JIRA-06: API token authentication — email + token + site URL, Basic auth header — M023
- ✓ JIRA-07: Person matching — accountId→email API call + SPARQL lookup + LRU cache — M023
- ✓ JIRA-08: Pull sync — Jira issues → bpkm:Task with full field mapping — M023
- ✓ JIRA-09: Epic→Milestone mapping — with child task linking via parent.key/customfield_10014 — M023
- ✓ JIRA-10: Push sync — title/description/priority changes push to Jira — M023
- ✓ JIRA-11: Issue links — Blocks→bpkm:dependsOn edges with inward-only dedup — M023
- ✓ JIRA-12: E2E tests + user guide — mock server (12 selftest), 12-phase E2E, Chapter 36 — M023
- ✓ 385 unit tests across 6 test files, mock Jira REST API server, Playwright E2E test, Chapter 36 user guide — M023

### Validated (M024 — Monday.com Sync App)

<!-- Shipped and confirmed in M024 (2026-03-20). -->

- ✓ Monday.com Sync app: configurable column mapping UI, bidirectional sync with LoopGuard echo prevention — M024
- ✓ API token authentication, board discovery, column schema discovery with settings_str parsing — M024
- ✓ Pull sync: items → bpkm:Task with groups as taskGroup, subitems as parentTask, dependencies as dependsOn — M024
- ✓ Push sync: reverse column mapping with per-column-type JSON format, change_multiple_column_values mutations — M024
- ✓ Status/priority label mapping from Monday.com custom labels to bpkm enum values — M024
- ✓ LoopGuard TTL cache module preventing push→poll echo loops in bidirectional mode — M024
- ✓ Mock Monday.com GraphQL server (12-check selftest), 13-phase Playwright E2E test — M024
- ✓ User guide Chapter 37 (393 lines), 3 glossary entries, appendix MONDAY_API_URL — M024
- ✓ 607 unit tests across 7 test files, all passing in <1s — M024

### Validated (M025 — Hosted Demo Instance)

<!-- Shipped and confirmed in M025 (2026-03-20). -->

- ✓ DEMO_MODE anonymous access: synthetic guest user bypass in all three auth dependencies, no DB access — M025
- ✓ Setup wizard bypass: /api/auth/status returns setup_complete=true in demo mode — M025
- ✓ Read-only enforcement: nginx default-deny POST/PUT/DELETE/PATCH → 403 JSON via error_page 495 pattern — M025
- ✓ docker-compose.demo.yml: 3-service demo stack on ports 3902/8902 with DEMO_MODE=true — M025
- ✓ 74 sample objects across 4 Mental Models with 12 cross-model edges and 10 rich markdown bodies — M025
- ✓ 7-step Driver.js demo tour with auto-navigation, restart button, localStorage completion tracking — M025
- ✓ Pre-built demo dashboard with sidebar-main layout and cross-view context filtering — M025
- ✓ Dismissible CTA banner with slide-up animation, GitHub install link, localStorage persistence — M025
- ✓ Caddy reverse proxy for automatic HTTPS via Let's Encrypt — M025
- ✓ Periodic reset script (5-phase) with cron configuration documentation — M025
- ✓ 14 backend unit tests + 9 E2E Playwright tests (4 read-only + 5 full-flow) — M025
- ✓ User guide Chapter 38, DEMO_MODE in Appendix A, 2 glossary entries — M025
- ✓ 10 DEMO requirements validated (DEMO-01 through DEMO-10) — M025

### Validated (M039 — RDF Data Import & API Documentation Cleanup)

<!-- Shipped and confirmed in M039 (2026-03-22). -->

- ✓ IMPORT-01: RDF paste/upload UI — sidebar entry, command palette entry, 3-step wizard with dockview tab — M039
- ✓ IMPORT-02: Parse + format detection — JSON-LD, Turtle, N-Triples via 3-tier heuristic, 29 unit tests — M039
- ✓ IMPORT-03: SHACL validation preview — pyshacl against installed shapes, grouped by focus node — M039
- ✓ IMPORT-04: Event-sourced import — Operations from rdflib triples, per-subject and bulk commit — M039
- ✓ IMPORT-05: Blank node skolemization — urn:sempkm:import:{uuid} URIs, 5 unit tests — M039
- ✓ IMPORT-06: IRI collision detection — batch SPARQL VALUES against urn:sempkm:current — M039
- ✓ IMPORT-07: SSE progress events — import_progress/import_complete/import_error via EventSource — M039
- ✓ API-09: Redoc tag cleanup — all 10 routers tagged, zero "default" routes — M039

### Validated (M034 — Task Planning, Time-Blocking & Calendar UX)

<!-- Shipped and confirmed in M034 (2026-03-22). -->

- ✓ PLAN-01: Task time-blocking — scheduledStart/scheduledEnd/estimatedDuration on TaskShape (basic-pkm v2.2.0) — M034
- ✓ PLAN-02: Editable calendar — drag-to-reschedule, resize duration, click-to-create with persistence — M034
- ✓ PLAN-03: External drag to calendar — kanban-to-calendar drop scheduling at target time — M034
- ✓ PLAN-04: Timeline/Gantt view — Frappe Gantt with dependency arrows, zoom levels, drag-to-reschedule — M034
- ✓ PLAN-05: Recurring tasks — RRULE expansion, virtual calendar instances, recurrence editor UI — M034
- ✓ PLAN-06: Task templates — RDF CRUD with batch instantiation, command palette integration — M034
- ✓ PLAN-07: PPV review workflows — 4 seeded WorkflowSpecs with per-name idempotency — M034
- ✓ PLAN-08: Composable planning — calendar + kanban side by side with shared scope context — M034
- ✓ PLAN-09: Calendar shows tasks and events together with color coding — M034
- ✓ PLAN-10: Timeline project-scoped filtering via saved queries — M034

### Validated (M035 — AI Copilot & LLM Test Harness)

<!-- Shipped and confirmed in M035 (2026-03-23). -->

- ✓ AI-01: Copilot chat UI — streaming SSE, markdown rendering, IRI object pills, lazy-loaded panel — M035
- ✓ AI-02: Schema-aware SPARQL generation — installed model SHACL shapes as system prompt context, parse+predicate validation, self-correction loop (2 retries) — M035
- ✓ AI-03: Query approval flow — approve/edit/reject/retry controls, inline SPARQL display, execution with formatted prose results — M035
- ✓ AI-04: Graph context injection — 1-hop neighborhood SPARQL, token-budgeted serialization (2000 tokens), active object tracking via sempkm:tab-activated — M035
- ✓ AI-05: Conversation persistence — SQLAlchemy models (copilot_conversations + copilot_messages), CRUD service, auto-create/load/save, conversation selector UI — M035
- ✓ AI-06: AI personas — 4 built-in personas (General Assistant, Research Assistant, Project Manager, Writing Coach), CRUD, lazy seeding, system prompt templates with slot variables — M035
- ✓ AI-07: Object creation from chat — JSON block detection in SSE stream, confirmation card, Command API dispatch — M035
- ✓ AI-08: Mock LLM test harness — SSE streaming mock server with 5-route pattern matching, 12-check selftest, Docker service in test stack — M035
- ✓ AI-09: Ollama integration tests — docker-compose.test-ollama.yml with model cache volume, GPU passthrough opt-in — M035
- ✓ AI-10: Cloud test tier — CostTracker with token accumulation, budget cap ($1.00 default), cost reporting — M035
- ✓ 139 backend unit tests + 5 E2E Playwright test cases, all passing — M035

### Validated (M036 — Business Planning Mental Models & Custom Renderers)

<!-- Shipped and confirmed in M036 (2026-03-23). -->

- ✓ BIZ-01: business-planning model archive — 5-file JSON-LD structure, 34 OWL classes, 2822 RDF triples, manifest validates, E2E install — M036
- ✓ BIZ-02: Quadrant renderer full vertical — SHACL-driven axis detection, 2×2 CSS Grid, drag-to-reclassify with RDF property updates, 28 unit tests — M036
- ✓ BMC 9-box poster renderer — 10-column CSS Grid, inline editing with debounced saves, 31 unit tests — M036
- ✓ OKR progress bars — current/target computation (clamped 0–100%), grouped by Objective, 25 unit tests — M036
- ✓ Decision Matrix weighted scoring — Σ(weight × score) auto-ranking, 26 unit tests — M036
- ✓ 11 extended frameworks (SWOT, Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas, BCG, Ansoff, Stakeholder, Risk) using existing renderers — M036
- ✓ Cross-model edges (bp:relatedTask → bpkm:Task, bp:relatedGoalOutcome → ppv:GoalOutcome) — M036
- ✓ E2E Playwright spec covering model install → 4 custom renderers → SPARQL query — M036
- ✓ User guide section documenting all 15 frameworks in chapter 39 — M036

### Validated (M030 — Data Quality Linting & Lint UX)

<!-- Shipped and confirmed in M030 (2026-03-21). -->

- ✓ LINT-08: Validation pipeline fix — model_shapes_loader loads rules graphs, ValidationService passes advanced=True, M011 rules fire in production — M030
- ✓ LINT-09: Comma-in-tags data quality rule (sh:Warning) — 2 pytest + E2E — M030
- ✓ LINT-10: Empty body data quality rule (sh:Info) for basic-pkm + zettelkasten — 3 pytest + E2E — M030
- ✓ LINT-11: Concept no definition rule (sh:Info) — 2 pytest — M030
- ✓ LINT-12: Titleless objects rule (sh:Warning) with type-namespace scoping — 3 pytest — M030
- ✓ LINT-13: Orphan objects rule (sh:Info) — 2 pytest — M030
- ✓ LINT-14: Duplicate URL rule (sh:Info) — 2 pytest — M030
- ✓ LINT-15: Stale project rule (sh:Info) — 2 pytest — M030
- ✓ LINT-16: PPV ActionItem no project rule (sh:Warning) — 2 pytest — M030
- ✓ LINT-17: PPV Project no goal rule (sh:Warning) — 2 pytest — M030
- ✓ LINT-18: Suppress lint results by rule type — 59 unit tests + E2E — M030
- ✓ LINT-19: Dismiss individual lint results — 59 unit tests + E2E — M030
- ✓ LINT-20: Named lint filter presets — 59 unit tests + E2E — M030

### Validated (M029 — Frontend Performance & Build Pipeline)

<!-- Shipped and confirmed in M029 (2026-03-20). -->

- ✓ esbuild build pipeline: vendor bundle + page-specific bundles + minified app JS/CSS + content-hashed filenames + manifest.json + .gz pre-compressed siblings — M029
- ✓ All 18 CDN dependencies vendored locally — app works fully offline after initial page load — M029
- ✓ Jinja2 asset_url filter with conditional CDN/local loading, multi-path manifest search — M029
- ✓ Multi-stage Docker build (Node.js → nginx) with shared volume for cross-container manifest access — M029
- ✓ nginx gzip compression (gzip_static for pre-compressed, gzip_proxied any for dynamic) — M029
- ✓ Three-tier HTTP cache strategy (immutable for hashed, no-cache+ETag for auth, no-store for dev) — M029
- ✓ CSS code-splitting via Jinja2 block inheritance — 19 non-workspace templates exclude ~227KB workspace CSS — M029
- ✓ TimingMiddleware with Server-Timing header, slow request logging, timing-report admin endpoint — M029
- ✓ ConditionalGetMiddleware with ETag-based 304 Not Modified on JSON API responses — M029
- ✓ Lighthouse desktop performance median 80 (FCP 984ms, LCP 2585ms, TBT 15ms) — M029
- ✓ QUIC/HTTP/3 decision documented (D277 — deferred) — M029
- ✓ 9 PERF requirements (PERF-02 through PERF-10) registered and validated — M029

### Validated (M018 — Google Calendar Sync)

<!-- Shipped in M018 (2026-03-18). Code recovered from worktree 2026-03-21. -->

- ✓ bpkm:Event type in basic-pkm v2.1.0 (OWL class, 20 properties, SHACL EventShape, 3 ViewSpecs, 2 SavedQueries, 4 seed instances) — M018
- ✓ Google Calendar sync app with OAuth 2.0, calendar list selection, pull sync, push sync (RSVP), recurrence handling, settings UI — M018
- ✓ E2E mock Google Calendar API server, Playwright E2E spec, Chapter 36 user guide — M018 ⚠️ recovered from worktree

### Validated (M019 — Todoist Sync)

<!-- Shipped in M019 (2026-03-19). Full app recovered from worktree 2026-03-21. -->

- ✓ Todoist Sync app — PAT auth, pull/push sync, project selection, 6 services, 3 templates — M019 ⚠️ recovered from worktree
- ✓ 6 test files (auth, client, field_mapper, person_matcher, sync_engine, push_sync) — M019 ⚠️ recovered from worktree
- ✓ E2E mock Todoist API, Playwright E2E spec, Chapter 37 user guide — M019 ⚠️ recovered from worktree

### Validated (M020 — Outlook Calendar Sync)

<!-- Shipped in M020 (2026-03-19). Full app recovered from worktree 2026-03-21. -->

- ✓ Outlook Calendar sync app — Microsoft OAuth 2.0, multi-tenant, pull/push sync, calendar selection — M020 ⚠️ recovered from worktree
- ✓ 5 test files (auth, client, field_mapper, person_matcher, sync_engine) — M020 ⚠️ recovered from worktree
- ✓ E2E mock Outlook API, Playwright E2E spec, Chapter 38 user guide — M020 ⚠️ recovered from worktree

### Validated (M021 — CalDAV Calendar Sync)

<!-- Shipped in M021 (2026-03-19). Full app recovered from worktree 2026-03-21. -->

- ✓ CalDAV Calendar sync app — HTTP Basic auth, PROPFIND discovery chain, pull/push sync — M021 ⚠️ recovered from worktree
- ✓ 5 test files (auth, client, field_mapper, person_matcher, sync_engine) — M021 ⚠️ recovered from worktree
- ✓ E2E mock CalDAV server, Playwright E2E spec, Chapter 39 user guide — M021 ⚠️ recovered from worktree

### Validated (M022 — Asana Sync)

<!-- Shipped in M022 (2026-03-19). Full app recovered from worktree 2026-03-21. -->

- ✓ Asana Sync app — dual OAuth/PAT auth, configurable field mapping, "configure before sync" UX — M022 ⚠️ recovered from worktree
- ✓ 5 test files (auth, client, field_mapper, person_matcher, sync_engine) — M022 ⚠️ recovered from worktree
- ✓ E2E mock Asana API, Playwright E2E spec, Chapter 40 user guide — M022 ⚠️ recovered from worktree

### Validated (M027 — Notion Import)

<!-- Shipped in M027 (2026-03-19). Executor/tests/docs recovered from worktree 2026-03-21. -->

- ✓ Notion workspace ZIP import wizard — 7-step flow with SSE progress — M027
- ✓ NotionScanner, NotionImportExecutor, 2 template partials — M027 ⚠️ executor recovered from worktree
- ✓ Playwright E2E spec, recreated notion-export.zip fixture, Chapter 39 user guide — M027 ⚠️ recovered from worktree

### Validated (M028 — Browser Extension AI Features)

<!-- Shipped in M028 (2026-03-19). AI endpoints/tests/docs recovered from worktree 2026-03-21. -->

- ✓ 6 AI backend endpoints (claim detection, matching, suggestions, summarization, LLM stream, status) — M028 ⚠️ recovered from worktree
- ✓ Extension AI Insights sidebar section with progressive rendering — M028
- ✓ 4 test files, mock LLM API server, Playwright E2E spec, Chapter 40 user guide — M028 ⚠️ recovered from worktree

### Future Candidates

<!-- Tracked for future milestones. See .gsd/QUEUE.md for full queue and .gsd/REQUIREMENTS.md for deferred requirements. -->

**Notion Import** (NOTION-01) — researched
- Notion workspace import wizard (ZIP first, API later), mirroring Obsidian pattern
- Research: `.planning/notion-import-research.md`

**MCP Server** (MCP-01)
- AI agent access to SemPKM via Model Context Protocol

**Dockview Phase B & Theming**
- Flexible panel layout: dockview-core Phase B (sidebar panels into dockview)
- Model-provided default layouts in Mental Model manifest
- Full theming system (CSS variable token sets, user-selectable themes, model-contributed themes)

**Low-Code & Workflows**
- Low-code UI builder (compose basic components tied to SemPKM actions)
- Minimal workflow orchestration (orchestrated forms/views, not n8n)

**Spatial Canvas Upgrade** (CANVAS-01–05) — shipped (M008)
- Resizable nodes with free drag handles, width/height stored per-node
- Property flip on object nodes (SHACL-derived properties table, inline)
- Live view/dashboard/SPARQL/object embeds as resizable iframes
- Toolbar picker + drag-from-explorer for adding embeds
- E2E Playwright tests + Chapter 27 user guide update

**App Platform** (APP-01–14) — complete (M009)
- Sandboxed app platform: manifest validation, subprocess lifecycle, App SDK, 3-level frontend integration
- Platform-owned task scheduler, permission enforcement, admin monitoring portal
- Bulk EventStore extension, browserVisible field on Mental Model types
- Design: `.gsd/design/APP-PLATFORM-DESIGN.md`

**RSS Reader App** (RSS-01–08) — complete (M010, depends on M009)
- First app on the platform: RSS/Atom feed reader with feed subscription, polling, reader UI, OPML import
- rss-feeds Mental Model, custom object renderer, workspace contributions, command palette actions
- Playwright E2E spec (663 lines, 58 assertions) + Chapter 32 user guide (305 lines)

**Mental Models Expansion** (MODEL-01–04) — complete (M011)
- S01 complete: basic-pkm v2.0 with Task + Milestone types, 10-test acceptance suite, all 3 key risks retired
- S02 complete: Personal CRM with Contact/Company/Interaction/Deal, SHACL-AF inference+validation, 12 seed objects
- S03 complete: Zettelkasten+ with 5 note types, provenance chain, argumentation links
- S04 complete: Research Workflow with 5 types, 4 SHACL-AF validation rules, Evidence Map graph view
- S05 complete: Cross-model verification (10 pytest tests), E2E Playwright test (Docker lifecycle), Chapter 29 user guide (608 lines, 15 glossary entries)
- Design: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md`

**Workspace & Event Log Polish** — complete (M012)
- S01 complete: Event log labels, helptext tooltips, autocomplete for filter fields
- S02 complete: Body.diff incremental storage and rendering
- S03 complete: Workspace personas — CRUD, sidebar selector, command palette, layout/positions/mode save and restore
- S04 complete: 12 E2E Playwright tests + user guide Chapter 15 updated (4 sections) + Chapter 30 (personas) + glossary

**API Surface for External Clients** — complete (M013)
- S01 complete: Dual-auth dependency (session cookie + Bearer token), CORS headers, nginx Authorization forwarding, `/.well-known/sempkm` discovery endpoint
- S02 complete: `GET /api/types` (all installed model types with labels/icons/model attribution), `GET /api/shapes/{type_iri}` (SHACL property shapes as JSON)
- S03 complete: `POST /api/context-query` (URL + keyword matching with deduplication), 7 E2E Playwright tests, Chapter 31 user guide, 62 unit tests total

**Browser Extension Phase 1** — complete (M014)
- Chrome/Firefox extension: smart structured capture with SHACL forms, schema.org ingestion, relationship picker
- Backend auth fix (require_role_or_api), extension scaffold, SHACL form renderer (10 property types)
- Content script extraction, schema.org auto-fill, context menu "Save to SemPKM", Alt+S keyboard shortcut
- Reference picker with search-as-you-type, two-step save (object.create → edge.create)
- 3 Playwright E2E tests, Chapter 32 user guide, Firefox manifest, admin API key management
- 13 EXT requirements validated

**Browser Extension Phase 2** — complete (M015, depends on M014)
- Knowledge context overlay: sidebar showing related objects while browsing, badge count, in-context actions (Open, Link, Add Evidence)
- Context Overlay settings in options page, 4 E2E tests, Chapter 33 user guide

**Integration Sync Apps** — complete (M016–M024, depend on M009)
- Linear Sync (M016) — complete (2026-03-18): first bidirectional sync app, OAuth/API key auth, pull sync (Linear→bpkm:Task), push sync, settings UI, admin sync history, 150 unit tests, E2E Playwright test, Chapter 34 user guide
- GitHub Issues Sync (M017) — complete (2026-03-18): second sync app, PAT auth, issue+PR pull sync with timeline-based edge linking, push sync with loop prevention, 204 unit tests, mock REST API server, E2E test (partial — platform issue), Chapter 35 user guide
- Google Calendar Sync (M018) — complete (2026-03-18): OAuth 2.0, calendar selection, pull/push sync, recurrence handling. ⚠️ E2E/docs recovered from worktree 2026-03-21.
- Todoist Sync (M019) — complete (2026-03-19): PAT auth, pull/push sync, project selection, 6 test files. ⚠️ Full app recovered from worktree 2026-03-21.
- Outlook Calendar (M020) — complete (2026-03-19): Microsoft OAuth 2.0, multi-tenant support, 5 test files. ⚠️ Full app recovered from worktree 2026-03-21.
- CalDAV Calendar (M021) — complete (2026-03-19): HTTP Basic auth, PROPFIND discovery, 5 test files. ⚠️ Full app recovered from worktree 2026-03-21.
- Asana Sync (M022) — complete (2026-03-19): dual OAuth/PAT auth, configurable field mapping, 5 test files. ⚠️ Full app recovered from worktree 2026-03-21.
- Jira Sync (M023) — complete (2026-03-19): ADF↔Markdown, statusCategory normalization, Epic→Milestone, 385 unit tests, Chapter 36 user guide
- Monday.com Sync (M024) — complete (2026-03-20): configurable column mapping, LoopGuard echo prevention, 607 unit tests, Chapter 37 user guide
- Design: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`

**Hosted Demo Instance** — complete (M025, 2026-03-20)
- Pre-populated public instance with guided tour, sample data, read-only access
- DEMO_MODE anonymous access, nginx write-blocking, 74 sample objects across 4 Mental Models
- 7-step Driver.js tour, demo dashboard, CTA banner, Caddy SSL, periodic reset cron
- E2E Playwright test, Chapter 38 user guide, 3 DEMO requirements validated

**Homepage & Messaging Rewrite** — complete (M026, 2026-03-20)
- Outcome-focused homepage, 3 persona landing pages, competitive positioning, fresh screenshots, Lighthouse 0.99

**Notion Import** — complete (M027, 2026-03-19)
- Notion workspace ZIP import wizard — 7-step flow (upload → scan → type mapping → property mapping → relation mapping → preview → execute)
- NotionScanner with CSV parsing, Notion ID stripping, 8-type column inference, cross-DB relation detection
- Two-pass import executor: CSV→RDF objects, then cross-database relation resolution via title matching
- SSE progress broadcasting during execution
- ⚠️ Executor, templates, test, E2E spec, and docs recovered from worktree 2026-03-21. E2E fixture recreated.

**Browser Extension Phase 3 — AI Features** — complete (M028, 2026-03-19)
- 6 AI backend endpoints (claim detection, matching, relationship suggestion, summarization, LLM streaming, status)
- Extension sidebar AI Insights section with progressive rendering
- Mock LLM API server for E2E testing
- ⚠️ AI endpoint, 4 test files, E2E mock server, E2E spec, and docs recovered from worktree 2026-03-21.

**Frontend Performance & Build Pipeline** — complete (M029, 2026-03-20)
- esbuild build pipeline, all 18 CDN deps vendored locally, gzip compression, immutable HTTP caching, CSS code-splitting, backend timing/ETag middleware, Lighthouse desktop 80, QUIC/HTTP/3 deferred

**Data Quality Linting & Lint UX** — complete (M030, 2026-03-21)
- Fixed broken SHACL-AF validation pipeline (model_shapes_loader loads rules, advanced=True)
- 10 new data quality rules across 4 models (comma-in-tags, empty body, titleless, orphan, duplicate URL, stale project, PPV broken chain, concept no definition, claim no rationale)
- Lint filter system: suppress rule types, dismiss individual results, named presets with SQLite persistence
- 13 REST API endpoints, lint panel dismiss/suppress UI, preset selector, settings management
- 24 per-rule pytest + 59 filter unit tests + 7 E2E Playwright tests, Chapter 14 user guide updated

**Feature Tour Bug Hunt & Polish** — queued (M048–M056, 2026-04-05)

65 issues found during interactive feature tour across sections 1–5 (Mental Models, Object CRUD, Workspace, Views, Business Planning). Organized into 9 milestones:

- **M048: Critical Bug Fixes** (P0, no deps) — model installer partial loading diagnosis, object.delete command, diff-based save, broken table/cards views, missing dcterms:created, Docker permissions
- **M049: Backend Performance & Observability** (P1, no deps) — Jaeger/OpenTelemetry, SPARQL profiling, lazy panel loading, 4s→<1.5s object load target
- **M050: View System Rework** (P1, depends M048) — pills→dropdown, smart type filtering, responsive sizing, save flow, view variants removal
- **M051: Workspace UX Improvements** (P2, no deps) — autocomplete dismiss, stale text, explorer hover actions, persona/layout UX, refresh button
- **M052: UI Design System & Polish** (P2, depends M048+M050) — type-colored accents, zebra striping, kanban card density, writing-surface body editor
- **M053: Model Marketplace** (P3, depends M048) — cloud-hosted model registry, in-app browse/install
- **M054: Explorer Composable Filter/Group/Sort** (P3, depends M051) — stackable filter/group/sort layers, multiple OBJECTS panels
- **M055: Browser History & Tab Recovery** (P3, depends M051) — URL integration, back/forward, undo close tab
- **M056: Ontology Visualization Overhaul** (P3, depends M048) — layered graph, full TBox, multi-model filtering, persistent graph

**Ongoing / cross-cutting**
- Backlinks panel (incoming references for any object)
- Edge model enhancements: edge inspector panel, inline wiki-link creation
- JSON-LD export for objects/collections
- AI Copilot (chat about data, SPARQL generation, graph context, conversation persistence, AI personas, object creation from chat) — complete (M035)
- pgvector / semantic search (deferred until keyword FTS validated in v2.2)

**Task Planning, Time-Blocking & Calendar UX** — complete (M034, 2026-03-22)
- Editable calendar: drag-to-reschedule, resize duration, click-to-create with FullCalendar interactive mode
- Task time-blocking: scheduledStart/scheduledEnd/estimatedDuration on bpkm:Task (basic-pkm v2.2.0)
- Timeline/Gantt view: Frappe Gantt with dependency arrows, zoom levels, drag-to-reschedule
- Kanban-to-calendar drag scheduling with composable scope propagation
- Recurring tasks: RRULE expansion into virtual calendar instances, recurrence editor UI
- Task templates: RDF CRUD with batch instantiation, command palette integration
- PPV review workflows: 4 seeded WorkflowSpecs (Weekly/Monthly/Quarterly/Yearly)
- 99 unit tests + 8 E2E tests. User guide docs gap — no chapters written.

**AI Copilot & LLM Test Harness** — complete (M035, 2026-03-23)
- S01 delivered: AI Copilot chat panel with SSE streaming, schema-aware SPARQL generation, query approval flow (approve/edit/reject), self-correction retry, markdown rendering, clickable object pills, 48 unit tests
- S02 delivered: Graph context injection (1-hop neighborhood SPARQL, token-budgeted serialization, active object tracking), conversation persistence (SQLAlchemy models, Alembic migration 016, CRUD service + REST endpoints, auto-create/load/save in chat flow, frontend conversation selector), 35 unit tests
- S03 delivered: AI persona system (4 built-in personas, CRUD service, migration 017, REST endpoints, system prompt injection with slot variables, persona selector dropdown), object creation from chat (JSON block detection in SSE stream, confirmation card UI, Command API dispatch), 56 unit tests
- S04 delivered: 3-tier LLM test harness — mock server with SSE streaming and 5-route pattern matching (12-check selftest), 5-test copilot E2E Playwright spec, Ollama compose variant, cloud tier cost tracker with budget cap ($1.00 default)
- Total: 139 backend unit tests + 5 E2E test cases across 4 slices
- M028 AI endpoints wired into main.py alongside new copilot router

**Business Planning Mental Models & Custom Renderers** — complete (M036)
- `business-planning` model archive: 32 types across 15 frameworks (Eisenhower, SWOT, BMC, OKR, Decision Matrix, Porter, PESTLE, BCG, Ansoff, Stakeholder Map, Risk Matrix, Balanced Scorecard, RACI, Value Chain, Lean Canvas)
- 4 custom visual renderers: 2×2 quadrant (6 frameworks), 9-box canvas (BMC), progress bars (OKR), weighted scoring tables (Decision Matrix)
- Cross-model edges: bp:relatedTask → bpkm:Task, bp:relatedGoalOutcome → ppv:GoalOutcome, bp:relatedProject → bpkm:Project
- E2E Playwright tests cover model install, object creation, all 4 custom renderers, SPARQL queries
- User guide chapter 39 section 5 documents all frameworks with type reference tables
- All frameworks stored as typed RDF for AI copilot queryability

**User Context & Mobile App** — complete (M037, 2026-03-23)
- Backend Context API with SSE streaming, TTL-based staleness, ContextBroadcast fan-out, workspace sidebar indicator
- Auto-persona rules engine with priority-ordered AND-condition evaluation, Settings UI CRUD + test-against-current-context
- Expo SDK 55 React Native mobile app: API client, onboarding, context dashboard, geofencing, calendar, activity detection
- Geofence zone CRUD API + mobile MapView management, background task with expo-location
- FCM push notifications via firebase-admin with context-aware suppression (calendar_busy, quiet hours, disabled types)
- 12-test integration suite proving full loop: context update → rule evaluation → persona switch → notification dispatch/suppression
- 184 backend tests (172 unit/router + 12 integration), user guide Chapter 48 (386 lines)

**Personal Media Scheduler App** — complete (M038, 2026-03-23)
- Daily media queue: podcasts, YouTube, Spotify scheduled by context and configurable rules
- media-scheduler Mental Model (MediaSource, MediaItem, MediaCategory) with SHACL shapes and ViewSpecs
- Podcast RSS polling via feedparser with conditional GET and dedup, YouTube Data API v3 with quota tracking, Spotify OAuth 2.0 with PKCE and playlist discovery
- Schedule rules engine with AND-matching conditions (location, activity, time period, time range) + daily plan generator with time-slot allocation
- Context SSE subscription consuming M037 stream with 120s debounce (immediate for location_zone), exponential backoff reconnect
- Entry status tracking (completed/skipped/saved) in Today view with htmx actions
- Mobile Now Playing card with deep links to Spotify/YouTube/podcast native apps
- Stats dashboard: hours by category, top 10 sources, weekly trends (Chart.js CDN lazy-load)
- 414 unit tests across 30+ test classes, E2E Playwright spec (14 phases), user guide Chapter 49
- 36 source files, 14,063 lines added

**RDF Data Import & API Documentation Cleanup** — complete (M039, 2026-03-22)
- RDF import wizard: paste/upload JSON-LD/Turtle/N-Triples → SHACL preview → event-sourced import
- Format detection, subject extraction, blank node skolemization, IRI collision detection, SSE progress
- OpenAPI tag cleanup: all routers tagged, zero "default" routes in /redoc
- 29 unit tests, sidebar + command palette integration

**Code Quality Audit** — complete (M041, 2026-03-23)
- Systematic audit of 117,474 LOC across 442 files producing M041-RECOMMENDATIONS.md (1,034 lines, 84 findings, 17 quality dimensions)
- Backend (40 findings): module structure, readability, error handling, logging, type safety, SPARQL construction, async patterns, FastAPI patterns
- Frontend (21 findings): JS structure, DOM/event patterns, CSS architecture, template hygiene, htmx consistency
- Cross-cutting (23 findings): dead code, duplication, test coverage gaps, tech debt
- Top 10 prioritized by runtime risk: #1 SPARQL injection (131 f-string sites), #2 silent exceptions (26 blocks), #3 auth test coverage (0%), #4 unhandled fetch() (67 calls), #5 views/service.py 3,663-line god module
- Linting recommendations: ruff + ESLint + Stylelint configs, ~2hr setup, ~100 auto-fixable issues
- Pure analysis milestone — no source code changes, feeds a future execution milestone

**Security Audit — OWASP & Backend Hardening** — complete (M042)
- 44 findings across all 10 OWASP Top 10:2021 categories (9 High, 14 Medium, 13 Low, 8 Info)
- 33 SPARQL modules classified (5 confirmed-exploitable, 4 likely-exploitable, 24 safe)
- Backend hardening: secret management, session lifecycle, API tokens, debug endpoints, federation auth, file handling
- Infrastructure: nginx headers, Docker security, deployment hardening
- CDN dependency inventory with SRI/version pin status
- Prioritized Top 10 remediation list with effort estimates (19–35h total)
- Deliverable: `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` — ready for user review and remediation scoping

**Security Hardening — Injection, Auth & Access Control Fixes** — complete (M043, 2026-03-25)
- Closed all actionable findings from the M042 security audit across 4 slices (S05 E2E regression suite not executed)
- SPARQL injection: centralized SPARQLBuilder module (safe_iri, safe_literal, sparql_escape_string, values_clause, triple_pattern), all 17 modules migrated from 9 scattered escape functions, 18 exploit regression tests using exact M042 audit payloads
- Access control: authentication added to 6 unprotected app endpoints, setup endpoint guarded, CORS consolidated to FastAPI only (nginx/Caddy CORS removed), HTTP security headers (CSP, X-Frame-Options, etc.) on all proxy layers
- Auth hardening: single-use magic links (UsedMagicToken model), fine-grained API token scopes with scope_required() enforced on SPARQL/commands/copilot, session management (revoke-all, 10-session cap, daily cleanup), no-SMTP restriction
- Rate limiting: 6 endpoint groups (SPARQL 60/min, copilot 20/min, token creation 5/min, commands 20/min, magic-link 5/min, verify 10/min), custom handler with WARNING logging
- SecurityAuditLog table with log_security_event() helper wired to 6 auth operations, global error disclosure protection
- Startup misconfiguration warnings (demo_mode on non-localhost, cookie_secure mismatch)
- 3 Alembic migrations (022–024), docs/security-model.md (123 lines), 227 M043-specific tests, 52 files changed (+3977/-373 lines)

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
- Mobile native app — delivered in M037 (Expo/React Native mobile app with geofencing, calendar, activity detection, push notifications)
- Full ontology editor — M004 completed full CRUD for classes and properties; Protege still needed for advanced OWL authoring (TYPE-03 deferred)

## Current State

**In progress: M048 Critical Bug Fixes (2026-04-05)** — S01 ✅ (Table/Cards views + creation timestamps), S02 ✅ (Diff-based save), S03 ✅ (Object Delete UI with inbound edge cleanup + 3-surface delete), S04 ⬜ (Docker permissions + model loading)

**Latest shipped: M047 PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System (2026-04-05)**
- Manifest v2 format: optional `manifest_version` field, `dashboards`/`workflows` entrypoints, backward-compatible with all 8 v1 models
- source_model column on dashboard_specs/workflow_specs for model-sourced surface tracking, with install/uninstall/refresh lifecycle
- PPV ontology expanded: PillarScore (1-10 scoring linked to Pillar + WeeklyReview), GuidingPrinciples (values anchor), 15 enriched review reflection fields across all 4 review types, 4 new ViewSpecs, SHACL-AF date denorm rule
- 5 TBox dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) and 5 TBox workflows (Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review) ship with PPV model
- dashboard_name→UUID resolution at install time for cross-referencing between dashboards and workflows
- Seed data expanded to 35 instances/12 types with GuidingPrinciples + PillarScore instances + enriched review fields
- E2E lifecycle test, user guide chapter 50, 150 unit tests, 7 decisions (D376–D382)
- seed.py trimmed from 5 workflows to 1 generic — PPV review workflows now model-sourced

M045 shipped: SSRF guard (4 code paths), federation integrity (SHA-256 hash + namespace filtering), model install/uninstall audit events, non-root Docker containers (UID 1000, no-new-privileges, cap-drop ALL across 6 compose files), ZIP bomb protection, weak SECRET_KEY startup rejection, per-app JWT key isolation via HMAC-SHA256, Caddyfile HSTS + CSP cleanup. Complete 44-finding disposition table in docs/security-model.md.

**Latest shipped: M044 Frontend Code Quality Execution (2026-03-25) — 6 slices, 175 files changed, net -587 lines. Centralized fetch wrapper (167 callers), event leak fixes, window.SemPKM namespace (228 exports), 100% CSS theme adoption, template deduplication, convention documentation. S07 E2E regression suite not executed.**

**What shipped in M044:**
- Centralized fetch wrapper: `window.apiFetch()` in `api-fetch.js` wrapping native fetch with structured error handling ({status, body, response}), AbortError catching, 401 redirect, toast fallback. All 167 callers across 36 files migrated with {silent:true}. 1 raw-fetch exemption (auth.js /api/auth/me).
- Event listener & timer leak fixes: dispose() methods on all 3 dockview content renderers (object-editor, view-panel, special-panel). Calendar anonymous listeners → named handlers with balanced remove. Canvas 7 window/document listeners cleaned via unbindEvents(). Federation badge interval cleared on beforeunload. Dead _cytoscapeInstances code removed.
- Window namespace consolidation: all cross-IIFE globals migrated from window.X to window.SemPKM.X. 228 exports across 26 JS files, 52 templates updated, 40 E2E test files updated, 157 backward-compat shims created then removed.
- CSS theme completion: 100% variable adoption (0 standalone hex, 0 standalone rgba outside theme.css). ~45 new tokens including ~15 decorative primitives. color-mix() for transparency. 66 dark-mode override blocks eliminated. Breakpoints standardized to 600px/768px.
- Template hygiene: all 10 .append() and 7 namespace() hacks eliminated via Python-side pre-computation in 7 view functions. 5 shared importer partials replacing 10 Notion/Obsidian duplicates. Guide page 375→79 lines via GUIDE_SECTIONS data-driven loop.
- Console cleanup & conventions: 37 console.log→SemPKM.debug() (localStorage-gated). docs/FRONTEND-CONVENTIONS.md (370 lines, 8 sections).
- 3 key decisions (D369 fetch wrapper, D370 namespace strategy, D371 CSS full conversion)
- Gap: S07 E2E regression suite was not executed — static verification only

**What shipped in M043:**
- Centralized SPARQLBuilder module: safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), triple_pattern() — all 17 modules migrated from 9 scattered escape functions
- 18 exploit regression tests using exact payloads from M042 audit findings (F-006 through F-010)
- Authentication added to 6 unprotected app endpoints, setup endpoint guarded with setup_mode check
- CORS consolidated to FastAPI CORSMiddleware — all nginx/Caddy CORS directives removed
- HTTP security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) on nginx.conf, nginx.demo.conf, Caddyfile.cloud
- Single-use magic links via UsedMagicToken model with SHA-256 hash storage
- Fine-grained API token scopes: scope_required() dependency factory enforced on SPARQL, commands, copilot endpoints
- Session management: POST /api/auth/sessions/revoke-all, 10-session cap with oldest eviction, daily async cleanup
- No-SMTP magic links restricted to existing/invited users
- Rate limits on 6 endpoint groups via slowapi decorators with custom WARNING logging handler
- SecurityAuditLog table with log_security_event() helper wired to 6 auth operations
- Global exception handler eliminating error disclosure (generic 500 responses, full traceback logged)
- Startup warnings for demo_mode + non-localhost, cookie_secure mismatches
- docs/security-model.md (123 lines) documenting shared-data model, auth flows, scopes, rate limits
- 3 Alembic migrations (022–024), 52 source files changed, +3977/-373 lines

**What shipped in M037:**
- Backend Context API: POST /api/context/update, GET /api/context/current, GET /api/context/stream (SSE). ContextService with TTL-based staleness (15 min default). ContextBroadcast SSE fan-out.
- Auto-persona rules engine: ContextRule model, RulesEngine.evaluate() with AND-condition first-match-wins by priority, 5-endpoint CRUD API, Settings UI panel with test-against-current
- Expo SDK 55 React Native mobile app (`mobile/`): TypeScript API client, onboarding with connection test, context dashboard, zone management with MapView, geofencing background task, calendar+activity+time-period detection, push notification handler
- Geofence zone CRUD API: 4-endpoint REST with Pydantic validation, mobile MapView with Circle overlays and ZoneEditor modal
- Push notifications via firebase-admin FCM: should_suppress() with 5-check pipeline (master toggle, type enabled, calendar_busy, quiet hours with midnight-spanning), context-aware dispatch on zone changes and calendar_busy→free transitions, no-op without Firebase credentials
- Workspace sidebar context indicator consuming SSE stream with staleness fallback
- 4 Alembic migrations (018–021), 14 backend source files, 19 mobile TypeScript files
- 184 backend tests (172 unit/router + 12 integration), user guide Chapter 48 (386 lines)
- 16 CTX requirements validated, 3 deferred (offline queue, multi-device conflict UI, version checking)

**What shipped in M040:**
- User guide Chapter 7 expanded to cover all 7 renderers: Table, Cards, Graph, Kanban, Calendar, Timeline/Gantt, Map
- Calendar View docs include recurring tasks (RRULE editor, EXDATE), cross-view drag, composable planning pattern
- Timeline/Gantt View docs cover date field detection, zoom levels, dependency arrows, drag-to-reschedule
- Map View docs cover geo field detection, OpenStreetMap tiles, marker clusters, chunked loading
- Chapter 28 expanded with Task Templates (REST API, command palette, batch instantiation) and Review Workflows (5 seeded workflows, stepper UI, customization)
- 8 new glossary entries in Appendix D
- 9 orphaned guide chapters renumbered to unique chapters 39–47 and integrated into all 3 nav files
- 27 broken cross-references fixed across 9 files
- Three-file nav sync verified and drift issues fixed (duplicate entries removed, missing entries added)
- User guide now has 47 numbered chapters + 6 appendices, zero collisions, zero broken cross-references
- Resolves the docs gap flagged in M039 ("⚠️ no docs/guide chapters written for M034 features")

**What shipped in M039:**
- RDF data import wizard: paste or upload JSON-LD, Turtle, N-Triples → 3-step flow (input → preview → import)
- Format detection via 3-tier heuristic (manual override → file extension → content analysis)
- Subject extraction with label precedence, top-level heuristic, blank node skolemization to `urn:sempkm:import:{uuid}`
- SHACL validation preview grouped by focus node, IRI collision detection against `urn:sempkm:current`
- Event-sourced import via Operation/EventStore (per-subject ≤10, bulk chunks of 500)
- SSE progress broadcasting (import_progress/import_complete/import_error)
- Sidebar entry, command palette entry, dockview tab integration
- OpenAPI tag cleanup: all 10 previously-untagged APIRouter constructors now have `tags=` — zero "default" routes in /redoc
- Recurring tasks: python-dateutil RRULE expansion into virtual calendar events (max 52 per task, ±6 month window), EXDATE exclusions, synthetic IDs ({iri}__recurrence__{isodate}), dashed border + ↻ prefix rendering
- Recurrence editor: IIFE with presets (daily/weekdays/weekly/biweekly/monthly/custom), custom RRULE builder (frequency/interval/day checkboxes/end conditions), EXDATE date picker, human-readable summary
- Task templates: TaskTemplateService with RDF CRUD in urn:sempkm:task-templates named graph, REST API, batch instantiation via @slot: references through command dispatch, command palette "Create from Template" with dynamic API children
- PPV review workflows: 4 seed WorkflowSpecs (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency, 4 palette launcher commands with name-based lookup
- 7 key decisions (D303–D309), 99 unit tests across 6 files, 8 E2E tests across 3 specs

**What shipped in M033:**
- Instance config system: `InstanceConfig` Pydantic model with atomic file persistence (`data/.instance-config.json`), config priority chain (env var > instance config > default), startup namespace warning
- Two-step setup wizard (deployment mode selection → account creation) eliminating dangerous `example.org` default
- Cloud deployment via `docker-compose.cloud.yml` + Caddy auto-TLS (`Caddyfile.cloud`)
- Isometric 2.5D graph layout: CSS 3D perspective transform with monkey-patched Cytoscape coordinate correction and DOMMatrix-based popover positioning
- Lucide SVG icon toggle on graph nodes with memoized data URI pipeline and localStorage persistence
- Calendar view: FullCalendar 6.x with SHACL-based `_detect_date_fields()` dual heuristic, month/week/day switching, event click → open object tab
- Map view: Leaflet + MarkerCluster with SHACL-based `_detect_geo_fields()`, three instructive empty states, ResizeObserver for dockview panel resize
- Federated SPARQL console: SERVICE clause detection, endpoint URL autocomplete, mirror button, debounced info banner, admin allowlist management with file-based persistence
- App catalog: `AppManifestSchema` extended with category/features/readme, workspace catalog routes with searchable card grid, admin detail redesigned catalog-first, "Browse Catalog" sidebar entry
- 6 key decisions (D297–D302), 136 unit tests, 10 E2E tests

**What shipped in M032:**
- Dashboard widget palette expanded from 6 to 10 block types: form-group, stat-card, chart, heading added
- Form-group block: multi-object creation with SHACL sub-forms, `@slot:name` IRI resolution in batch commands, edge wiring
- Stat-card block: live SPARQL scalar queries with accent color, icon, and label
- Chart block: lazy Chart.js CDN loading, bar/line/pie visualization from SPARQL query results (`?label` + `?value` columns)
- Heading block: configurable h1-h4 with optional subtitle and alignment
- Fixed markdown block (marked.js + DOMPurify via `<script type="text/plain">`) and sparql-result block (live SPARQL table execution)
- Builder config forms for all 4 new block types with dynamic slot/edge management for form-group
- Frontend JS widget activation: `_executeSparqlWidgets()`, `_initChartBlocks()`, `_renderMarkdownBlocks()` hooked into htmx:afterSettle
- E2E Playwright spec (4 test cases) for stat-card, chart, heading, and multi-block rendering
- User guide chapter 28 rewritten with all 10 block types, GridStack layout, data widgets, form groups
- 2 key decisions (D295 SQLite JSON storage, D296 Python type hints for config schema)

**What shipped in M031:**
- Carousel tab bar fully removed — explorer sidebar is sole view selector (VIEW-08)
- View toolbar with saved query scope dropdown and model-declared variant dropdown (VIEW-09)
- Multiple view instances as separate tabs with independent scopes (VIEW-10)
- Saved Views folder with CRUD operations (VIEW-11)
- Saved queries in explorer sidebar, canvas embed, and VFS browser (SQ-01, SQ-02, SQ-03)
- Kanban renderer with SHACL-driven status columns and HTML5 drag-drop (VIEW-12)
- SPARQL IRI pill fix (28 specific sub-namespaces), dynamic prefix shortening, graph visualization tab (SPARQL-09/10/11)
- TBox property tooltips, admin model graph full-viewport with edge tooltips (ONTO-04/05/06)
- Full-height views via .view-flex-column, graph popover z-index fix (VIEW-13/14)
- Dashboard/workflow builder help text on all fields (DBUIX-01), IRI autocomplete via class-search/object-search endpoints (DBUIX-02), workflow view step simplification (DBUIX-03), idempotent seed data (DBUIX-04)
- E2E Playwright tests covering all 6 major features (S07/T01), stale carousel tests retired
- User guide chapters 7, 21, and 28 updated for all new features (S07/T02)
- 88 unit tests, 11 decisions (D284–D294)

**What shipped in M030 (Data Quality Linting & Lint UX):**
- Validation pipeline fix: `model_shapes_loader()` loads rules graphs alongside shapes, `ValidationService.validate()` passes `advanced=True` — all 11 existing M011 SHACL-AF rules now fire in production for the first time
- 10 new SHACL-AF SPARQLConstraint data quality rules across 4 models: comma-in-tags, empty body (basic-pkm + zettelkasten), concept no definition, titleless objects, orphan objects, duplicate URL, stale project, PPV broken chain (2 shapes), claim no rationale
- Cross-model rules scoped via `FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:"))` — fires only for basic-pkm types
- Lint filter system with SQLite persistence: 3 tables (lint_suppressions, lint_dismissals, lint_presets) via Alembic migration 015
- 13 REST API endpoints for lint filter CRUD (suppress/dismiss/preset operations)
- Server-side Python post-filtering with over-fetch re-pagination when filters active
- Lint panel dismiss buttons (×) on warnings/infos, dashboard suppress buttons (eye-off), preset selector dropdown
- Lint settings management UI with collapsible sections for suppressions/dismissals/presets CRUD
- 24 per-rule pytest tests + 59 lint filter unit tests + 7 E2E Playwright tests
- User guide Chapter 14 updated with 5 new sections (139 lines) + 4 glossary entries
- 13 LINT requirements validated (LINT-08 through LINT-20), 6 key decisions (D278–D283)

**What shipped in M029 (Frontend Performance & Build Pipeline):**
- esbuild build pipeline: `frontend/build.js` producing vendor bundle, page-specific bundles, minified app JS/CSS, content-hashed filenames, manifest.json, and .gz pre-compressed siblings (0.8s full build)
- All 18 CDN dependencies vendored locally via `frontend/package.json` — app works fully offline after initial page load
- Jinja2 `asset_url` filter with conditional CDN/local loading (manifest presence = production mode)
- Multi-stage `frontend/Dockerfile` (Node.js build → nginx serve) with Docker shared volume for cross-container manifest access
- nginx gzip compression: `gzip_static on` for pre-compressed assets, `gzip_proxied any` for dynamic responses
- Three-tier HTTP cache strategy: immutable for hashed assets, no-cache + ETag for auth HTML, no-store for dev files
- CSS code-splitting via Jinja2 `{% block page_css %}` — 19 non-workspace templates exclude ~227KB workspace CSS
- TimingMiddleware with Server-Timing header, slow request logging, per-path stats, `/api/admin/timing-report` endpoint (20 unit tests)
- ConditionalGetMiddleware with ETag-based 304 Not Modified on JSON API responses (16 unit tests)
- Lighthouse desktop performance: median 80 (range 74-81), up from estimated ~40-60; FCP 984ms, LCP 2585ms, TBT 15ms, CLS 0.094
- QUIC/HTTP/3 deferred (D277) — nginx:stable-alpine lacks HTTP/3 module, minimal benefit for self-hosted
- 9 PERF requirements (PERF-02 through PERF-10) registered and validated
- 9 key decisions (D267-D277) documented

**What shipped in M026 (Homepage & Messaging Rewrite):**
- Outcome-focused homepage rewrite replacing technology-first messaging ("Semantics-Native PKM built on RDF/SHACL/SPARQL") with user-value-first copy
- 3 persona landing pages: "Coming from Obsidian", "Coming from Notion", "Starting Fresh" — each with tailored messaging, feature comparisons, and migration-specific CTAs
- Competitive comparison table positioning SemPKM vs Obsidian/Notion/Tana/Capacities
- "Domain Kits" framing for Mental Models (no ontology jargon above the fold)
- Shared CSS design system (docs/styles.css) with responsive breakpoints, dark theme, animated hero graph
- "Try the Demo" CTA linking to M025 hosted demo instance, "Self-host" CTA linking to Docker quickstart docs
- 5 fresh screenshots from demo stack (workspace overview, explorer types, command palette, spatial canvas, object read)
- Deferred Google Fonts loading (media="print" onload pattern) — Lighthouse mobile performance 0.99
- Complete SEO tags: meta descriptions, OG tags with absolute og:image URLs, JSON-LD structured data (Organization + WebSite) on all 4 pages
- Responsive layout verified at 375px, 768px, 1200px+ — no horizontal overflow, hamburger menu at mobile, full nav at desktop
- All internal links verified working, HTML well-formed, CNAME preserved for GitHub Pages

**What shipped in M025 (Hosted Demo Instance):**
- Pre-populated, publicly accessible SemPKM demo instance removing Docker as the #1 conversion barrier
- DEMO_MODE anonymous access: synthetic guest user bypass in auth dependencies, no DB access, no login page
- Read-only enforcement via nginx default-deny: POST/PUT/DELETE/PATCH → 403 JSON at nginx layer
- docker-compose.demo.yml: 3-service demo stack on ports 3902/8902 with DEMO_MODE=true
- 74 interconnected sample objects across 4 Mental Models (basic-pkm, CRM, zettelkasten, research) with 12 cross-model edges and 10 rich markdown bodies
- 7-step Driver.js demo tour auto-starting on first visit, covering explorer, graph, object view, validation, canvas, dashboard, and CTA
- Pre-built demo dashboard with sidebar-main layout and cross-view context filtering (deterministic UUID shared between JS and Python)
- Dismissible "Try SemPKM" CTA banner with GitHub install link, slide-up animation, localStorage persistence
- Caddy reverse proxy for automatic HTTPS via Let's Encrypt (Caddyfile)
- Periodic reset cron via reset-demo.sh (5-phase: down → build → health → seed → verify, 120s timeout)
- 14 backend unit tests for demo mode auth bypass
- 9 E2E Playwright tests across 2 spec files (4 read-only + 5 full-flow) in demo project
- User guide Chapter 38 (~329 lines) with deployment instructions, DEMO_MODE in Appendix A, 2 glossary entries
- 10 DEMO requirements validated (DEMO-01 through DEMO-10), 8 key decisions (D244–D253)

**What shipped in M024 (Monday.com Sync App):**
- Monday.com Sync bidirectional sync app — 9th task provider integration on the App Platform
- Single API token authentication with StateClient storage and connection verification
- MondayClient GraphQL client with cursor pagination, complexity tracking, and 4-level error hierarchy (MondayApiError, MondayAuthError, MondayRateLimitError, MondayComplexityError)
- User-configurable column mapping: type-filtered dropdowns mapping board columns to bpkm properties (D228 pattern from Asana, refined here)
- Status/priority label mapping: custom Monday.com labels (e.g., "Working on it") → bpkm enum values via settings_str JSON parsing
- Per-board mapping storage (D242): independent column and label configs for multi-board sync
- Pull sync: Monday.com items → bpkm:Task with groups as taskGroup (D243: from item.group, not column_values), subitems linked via parentTask, dependencies as dependsOn edges
- Push sync: SPARQL change detection → reverse column mapping → change_multiple_column_values mutations with per-column-type JSON format
- LoopGuard echo prevention (D241): in-memory TTL cache (30s default) preventing push→poll infinite loops
- Tag column → bpkm:tags mapping with batch tag ID resolution via get_tags() API
- Person matcher: Monday.com user_id → SPARQL email lookup → Person creation on miss with LRU cache
- Mock Monday.com GraphQL server (697 lines, 12-check selftest, 10 query shapes) wired as Docker test stack service
- Playwright E2E test (13 phases) covering full install → auth → column mapping → label mapping → sync → verify → push lifecycle
- User guide Chapter 37 (393 lines) with column mapping walkthrough, label mapping, LoopGuard docs, troubleshooting
- 607 unit tests across 7 test files (auth, client, field_mapper, person_matcher, sync_engine, loop_guard, app_routes)
- 3 glossary entries (Column Mapping, LoopGuard, Monday.com Sync), appendix MONDAY_API_URL
- 15 MON requirements covered (MON-01 through MON-15), 3 key decisions (D241, D242, D243)

**What shipped in M023 (Jira Sync App):**
- Jira Cloud bidirectional sync app with API token authentication (email + token + site URL)
- ADF↔Markdown converter handling 12 common Atlassian Document Format node types with reverse direction for push
- statusCategory-based status normalization (new→todo, indeterminate→in-progress, done→done)
- Priority mapping (8 Jira priority names → 4 bpkm values with reverse maps)
- Pull sync: Jira issues → bpkm:Task with full field mapping (sprint→taskGroup, components/labels→tags, assignee via accountId resolution)
- Epic→Milestone mapping with child task linking
- Issue links: Blocks→bpkm:dependsOn edges with inward-only dedup
- Push sync: title/description/priority changes push to Jira (no status transitions per D237)
- JQL-based filtered sync with user-provided JQL queries
- Settings UI: project selection, JQL filter, sync direction, poll interval, Sync Now
- Mock Jira REST API server with 12-check selftest
- Playwright E2E test (12 phases covering full lifecycle)
- User guide Chapter 36 with field mapping tables, statusCategory explanation, ADF conversion notes
- 385+ combined unit tests across all Jira sync services
- 12 JIRA requirements validated (JIRA-01 through JIRA-12)
- 22 offline validation tests, EVENT-01 requirement validated

**What shipped in M017 (GitHub Issues Sync App):**
- Second bidirectional sync app on the App Platform — GitHub Issues + PRs to bpkm:Task objects
- PAT authentication (D206: no OAuth App for v1, matching M016's API key approach)
- GitHubClient REST client with Link-header pagination, rate-limit checking, typed exception hierarchy
- Pull sync: GitHub issues → bpkm:Task with status (open→todo, closed→done, not_planned→cancelled), labels→tags, assignee mapped to Person, milestone→project, body as markdown, external URL/ID
- PR sync: PRs appear as bpkm:Task with `externalProvider: "github-pr"` distinction
- PR-to-issue edge linking via GitHub Timeline API cross-referenced events (D208), creating bpkm:dependsOn edges
- Push sync: SPARQL change detection, reverse field mapping, GitHub PATCH API, lastSyncedAt loop prevention
- Settings UI with repo selection, sync direction (pull-only/bidirectional), poll interval dropdown
- PersonMatcher with email-first + login-fallback SPARQL resolution (adapted from M016)
- 204 unit tests across 5 test files (client 41, field mapper 55, auth 20, person matcher 10, sync engine 78)
- Mock GitHub REST API server (6 endpoints, 9-point selftest, Docker healthcheck)
- 12-phase Playwright E2E test (phases 0-2 pass, 3+ blocked by pre-existing app subprocess startup issue)
- Chapter 35 user guide (34 headings, field mapping tables, PR-to-issue linking, troubleshooting)
- Two pre-existing platform bugs fixed: browser/apps.py registry attribute access, workspace-layout.js app-page routing
- 7 GH requirements validated (GH-01 through GH-07)

**What shipped in M016 (Linear Sync App):**
- First bidirectional task provider sync app on the App Platform — connecting Linear issues to bpkm:Task objects
- OAuth and API key authentication with workspace discovery and team selection
- Pull sync: Linear issues → bpkm:Task objects with full field mapping (status, priority, assignee, labels, due date, effort, estimate, URL)
- Push sync: detect local task changes and write back to Linear, with loop prevention via lastSyncedAt comparison
- Settings page with team/project selection, sync direction toggle, poll interval configuration
- Admin detail page showing sync run history with timestamps, direction, counts, and status
- 150 unit tests covering field mapping, IRI minting, status/priority normalization, change detection, push sync, person matching
- Mock Linear GraphQL API server for E2E testing (canned responses for 6 query types)
- Playwright E2E test covering full install → configure → poll → verify → cleanup lifecycle (11 phases)
- User guide Chapter 34 (12 sections, ~250 lines) with field mapping tables, troubleshooting
- 4 glossary entries (Bidirectional Sync, Linear Sync, Pull Sync, Push Sync)
- Fixed htmx template routing through app proxy (pre-existing S02 bug caught by E2E testing)

**What shipped in M015 (Browser Extension Phase 2 — Knowledge Context Overlay):**
- Knowledge sidebar (Alt+K) showing related SemPKM objects while browsing any page, grouped by match type (URL > title > keyword)
- Badge count on extension icon showing number of related objects, cached per URL via in-memory LRU (max 100)
- Three in-context actions: Open (new tab to SemPKM object), Link to this page (creates schema:url edge), Add Evidence (captures highlighted text, creates linked Evidence object)
- Context Overlay settings in options page: autoCheckContext toggle, contextCheckDelay (ms), contextTimeout (ms)
- Chrome Side Panel API integration with Firefox sidebar_action compatibility via dual manifests
- Client-side result ranking (URL match > title match > keyword match, top 10)
- Service worker context pipeline with debounce, timeout, and cache management
- 4 Playwright E2E tests proving sidebar results, Open action, Link action with SPARQL edge verification
- User guide Chapter 33 (257 lines), 3 glossary entries (Context Badge, Context Overlay, Knowledge Sidebar)
- 8 requirements registered (EXT-14–EXT-21): 4 validated, 4 partial (badge API inaccessible, evidence capture manual-only, cache unit-tested, Firefox manifest-only)

**What shipped in M014 (Browser Extension Phase 1):**
- Chrome MV3 browser extension (`extension/` directory) with popup capture UI, options page, service worker
- Firefox WebExtension compatibility via `manifest.firefox.json` (95% shared codebase)
- `require_role_or_api(*roles)` factory enabling Bearer token auth on `POST /api/commands` (10 unit tests)
- Admin API key management page at `/admin/api-keys` (create, list, delete with one-time plaintext display)
- SHACL form renderer (`shacl-renderer.js`, 588 lines) handling 10 standard property types with groups, multi-value, validation
- Content script page data extractor (title, URL, selection, schema.org JSON-LD) via `chrome.scripting.executeScript`
- Schema.org → SemPKM type suggestion and property mapping (Person→Contact, Article→Note, Organization→Company)
- Reference picker with search-as-you-type, type filtering, two-step save (object.create → edge.create)
- Context menu "Save to SemPKM" with session storage bridge to popup
- Alt+S keyboard shortcut in both Chrome and Firefox manifests
- 3 Playwright E2E tests with custom persistent context fixture (Chromium-only)
- User guide Chapter 32 (12 sections, 25 headings), 2 glossary entries (API Token, Browser Extension)
- 13 EXT requirements validated, all extension JS files CSP-compliant (zero inline handlers)

**What shipped in M011 (Mental Models Expansion):**
- 4 complete .sempkm-model archives expanding the lineup from 3 to 6+ user-facing models — zero platform code changes (D149)
- basic-pkm v2.0: Task and Milestone types added to existing Project/Person/Note/Concept (6 types total, 197/815/144/179/35 triples)
- Personal CRM v1.0: Contact, Company, Interaction, Deal types with pipeline views and SHACL-AF inference (170/405/81/141/31 triples)
- Zettelkasten+ v1.0: FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote with provenance chain and argumentation links (132/399/60/125/31 triples)
- Research Workflow v1.0: Paper, Claim, Evidence, ResearchQuestion, Argument with confidence levels and evidence tracking (230/535/81/175/39 triples)
- 11 SHACL-AF validation rules across all models (overdue tasks, stale contacts, unprocessed notes, unsupported claims, etc.)
- 39 ViewSpecs + 21 SavedQueries + 20 Lucide icon entries + 55 seed objects
- 20 offline pytest tests (basic-pkm v2 + cross-model validation) in <1s
- E2E Playwright test proving Docker install → create → form render → inference → lint lifecycle
- User guide Chapter 29 (608 lines) with field references, relationship diagrams, 15 glossary entries

**What shipped in M008 (Spatial Canvas):**
- Resizable canvas nodes via corner/edge drag handles with grid snapping, min constraints, and width/height persistence
- Property flip on object nodes — SHACL-derived property table via lightweight /api/canvas/properties endpoint, inline rendering
- Live iframe embeds for views, dashboards, SPARQL results, and object read views via dual-layer rendering architecture
- base_embed.html minimal template and ?embed=1 query param across 4 endpoint families
- Toolbar "Embed" picker with tabbed selection (Views/Dashboards/Queries) + explorer drag-drop
- Max 8 simultaneous iframe embeds enforced
- Canvas document schema extended with nodeType, embedConfig, width, height, showProperties fields
- 69 new unit tests (830+ total), 5 E2E Playwright spec files (94 total)
- Chapter 27 updated with 3 new feature sections + 2 glossary entries

**What shipped in M007 (Generic Views, VFS Completion & Polish):**
- 3 generic views (Table/Cards/Graph) with SHACL-driven dynamic columns replacing per-type explorer tree
- Type filter pills for cross-type filtering with localStorage persistence
- Carousel tab bar showing model-declared view variants when type selected
- Explorer consolidation: flat entries + Saved Views folder (no per-model/per-type folders)
- VFS type filter with VALUES clause AND-composed with scope, multi-select UI
- VFS scopeQuery predicate with full IRI storage and migration (from savedQueryId)
- VFS preview endpoint resolving saved query scope, HTTP 404 on missing
- VFS path contract documentation with 26 unit tests
- VFS composable strategy chains (up to 3 levels, cumulative scope narrowing, chain builder UI with presets)
- VFS filename templates with {title}/{date}/{type}/{id} variable expansion
- UI polish: Lucide sidebar chevrons, always-visible OBJECTS buttons, DASHBOARDS/WORKFLOWS header plus-buttons, normalized inference button, accent Ontology Viewer, horizontal relationships graph
- User guide Chapter 28 (dashboards/workflows), 6 glossary entries
- 120 new unit tests (761 total), all 13 active requirements validated

**What shipped in M005 (Platform Polish & Foundation):**
- Query SQL→RDF migration: saved queries, history, sharing, promotion stored as RDF in triplestore
- Operations log with PROV-O vocabulary: admin UI at /admin/ops-log with filter and pagination
- Hierarchical tag tree: `/`-delimited tags nest at arbitrary depth in By Tag explorer
- Tag autocomplete: type-ahead suggestions in edit forms with frequency ordering
- Model schema refresh: POST endpoint updates ontology/shapes/views/rules without uninstall
- Design docs: PROV-O alignment, views rethink, VFS v2 design refinement
- E2E test coverage: 5 new Playwright tests across 3 spec files
- User guide: 4 chapters updated with new feature documentation

**Previous milestones:** M032 Block-Based Custom UI Builder (2026-03-22), M031 Views Overhaul (2026-03-21), M030 Data Quality Linting & Lint UX (2026-03-21), M029 Frontend Performance & Build Pipeline (2026-03-20), M026 Homepage & Messaging Rewrite (2026-03-20), M025 Hosted Demo Instance (2026-03-20), M024 Monday.com Sync App (2026-03-20), M023 Jira Sync App (2026-03-19), M017 GitHub Issues Sync App (2026-03-18), M016 Linear Sync App (2026-03-18), M015 Browser Extension Phase 2 (2026-03-18), M014 Browser Extension Phase 1 (2026-03-18), M013 API Surface for External Clients (2026-03-17), M012 Workspace & Event Log Polish (2026-03-17), M011 Mental Models Expansion (2026-03-17), M008 Spatial Canvas (2026-03-16), M007 Generic Views, VFS Completion & Polish (2026-03-16), M006 Dashboards, Workflows & Platform Alignment (2026-03-15), M005 Platform Polish & Foundation (2026-03-14), M004 Ontology & Type System Completion (2026-03-14), M003 Workspace UX & Knowledge Organization (2026-03-12), M002 Hardening & Polish (2026-03-12), v2.6 (2026-03-12), v2.5 (2026-03-09), v2.4 (2026-03-06), v2.3 (2026-03-03), v2.2–v2.1 (2026-03-01), v2.0 (2026-03-01), v1.0 (2026-02-23)

**Latest shipped: M044 Frontend Code Quality Execution (2026-03-25) — 6 slices, 175 files changed, net -587 lines. Centralized fetch wrapper, window.SemPKM namespace, 100% CSS theme adoption, template deduplication, convention documentation.**

**What shipped in M013 (API Surface for External Clients):**
- `GET /.well-known/sempkm` discovery endpoint with version, endpoints, auth methods, capabilities
- `GET /api/types` returning all installed model types with labels, Lucide icons, icon colors, and model attribution
- `GET /api/shapes/{type_iri}` returning SHACL property shapes as structured JSON (properties, groups, constraints, helptext)
- `POST /api/context-query` with URL matching (SPARQL FILTER) + keyword/title matching (FTS/LuceneSail), deduplication, and type/label enrichment
- `get_current_user_or_api` dual-auth FastAPI dependency (session cookie + Bearer API token)
- nginx Authorization header forwarding and CORS headers on `/api/` and `/.well-known/` routes
- 62 unit tests in test_api_surface.py covering all endpoints, auth, edge cases, and graceful degradation
- 7 E2E Playwright tests exercising all four endpoints through Docker Compose
- User guide Chapter 31 documenting the full API surface with request/response examples, auth, CORS, error handling
- 3 glossary entries (API Surface, Context Query, Instance Discovery)
- 8 requirements validated (API-01 through API-08)

## Context

**Current state (M024 complete 2026-03-20):**
- ~60k source LOC (52k Python, 8k JS) + CSS, HTML/Jinja2, JSON-LD
- 6 Mental Models: basic-pkm v2.0, ppv, gist, crm v1.0, zettelkasten v1.0, research v1.0 (24 files across 4 model directories)
- Tech stack: FastAPI + RDF4J (LuceneSail) + htmx/vanilla-web + SQLAlchemy (SQLite/PostgreSQL) + wsgidav + a2wsgi + Driver.js + Cytoscape.js + CodeMirror + dockview-core + Alembic + Yasgui CDN + ninja-keys + owlrl + pyshacl + mf2py + http-message-signatures + slowapi
- Docker Compose deployment: 3 services (api, triplestore, frontend/nginx) + federation test compose (2 instances)
- 58 phases, 80 plans completed across v1.0–v2.6; M002 (7 slices) + M003 (10 slices) + M004 (5 slices) + M005 (9 slices) + M006 (7 slices) + M007 (5 slices) + M008 (4 slices) + M011 (5 slices) + M012 (4 slices) + M013 (3 slices) + M014 (5 slices) + M015 (3 slices) + M016 (4 slices) + M017 (4 slices) + M023 (4 slices) + M024 (4 slices) milestones complete
- Backend test suite: 1225+ pytest unit tests, <5s, no Docker dependency
- E2E test suite: 98 Playwright spec files covering all shipped features
- Browser extension: `extension/` directory with Chrome MV3 + Firefox manifests, 11 JS modules (~2.5k LOC), 7 E2E tests (3 capture + 4 context overlay), 23 unit tests
- All dependencies pinned (~= compatible release) with uv.lock committed
- Browser router refactored into 8 domain sub-modules (was 1956-line monolith)
- Query storage migrated from SQL to RDF (4 SQL tables dropped)
- 3 design docs produced: PROV-O alignment, views rethink, VFS v2
- 2 new domain modules: dashboard/, workflow/ (SQLAlchemy + CRUD + builder UI)
- Generic views infrastructure: 3 ViewSpec entries, SHACL column discovery, type filter pills
- VFS v2 complete (except write support): type filter, scopeQuery IRI, composable chains, filename templates
- Spatial canvas: resizable nodes, property flip, live iframe embeds with dual-layer rendering
- API surface: 4 JSON endpoints for external clients with dual-auth, CORS, and 62 unit tests
- Browser extension Phase 1+2: Chrome MV3 + Firefox, 11 JS modules (~2.5k LOC), SHACL form renderer, schema.org mapper, reference picker, context sidebar with badge + grouped results + actions, 7 E2E tests, 23 unit tests
- Linear Sync app: first bidirectional sync app on App Platform — OAuth/API key auth, pull/push sync, field mapping, admin history, 150 unit tests, E2E test with mock API, Chapter 34 user guide
- GitHub Issues Sync app: second sync app — PAT auth, issue+PR pull sync with timeline-based edge linking, push sync with loop prevention, 204 unit tests, mock REST API server, E2E test (partial), Chapter 35 user guide
- Jira Sync app: bidirectional sync with ADF↔Markdown conversion, statusCategory normalization, Epic→Milestone mapping, issue link edges, push sync, 385 unit tests, mock REST API server, E2E test, Chapter 36 user guide
- Monday.com Sync app: bidirectional sync with configurable column mapping, label mapping, LoopGuard echo prevention, GraphQL complexity tracking, 607 unit tests, mock GraphQL server, 13-phase E2E test, Chapter 37 user guide

**Worktree data loss incident (2026-03-21):** GSD worktree isolation mode (`taskIsolation.mode: worktree`) caused source code loss across 8 milestones (M009, M010, M018–M022, M027, M028). Code was built in `.gsd/worktrees/<MID>/` but only `.gsd/` artifacts were committed to main. When worktrees were cleaned up, ~115 source files became dangling git objects. All files were recovered from dangling commits on 2026-03-21 and committed to main. Worktree mode is now permanently disabled (`taskIsolation.mode: none`). See KNOWLEDGE.md Rules R01–R03 and Lesson K003. Each affected milestone summary has a "Worktree Recovery" section documenting what was lost and recovered.

**Known tech debt:**
- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (module-level + lifespan) — harmless for SQLite
- Seed data has both inverse sides pre-populated (owl:inverseOf produces 0 new triples with current data)
- Edge duplication in triplestore (~16x per reified edge) — pre-existing in event store materialization pipeline
- Firefox E2E auth fixture flaking — intermittent "Magic link request did not return a token" failures
- Federation patches endpoint requires session auth but is called server-to-server without credentials — needs HTTP Signature verification
- M003 docs coverage addressed (7 guide chapters updated post-M003)
- Tag migration (/admin/migrate-tags) must be manually triggered after upgrade from pre-M003
- All 10 M003 slice summaries are doctor-created placeholders (task summaries are authoritative)
- SHACL shapes not auto-updated when property domain/range changes (D075) — acceptable but may confuse users
- Malformed xsd:dateTime literals from Obsidian import (non-fatal rdflib warnings) — see .gsd/design/KNOWN-BACKEND-ERRORS.md
- Validation report store returns HTTP 415 from RDF4J (validation works, report not persisted) — see .gsd/design/KNOWN-BACKEND-ERRORS.md
- Comment author UUID format mismatch (RDF dashed vs SQL undashed) — fixed post-M003 but pattern may recur
- **DashboardSpec/WorkflowSpec in SQLite JSON** — model-layer concepts that should be RDF named graphs (queryable, federable). Migration planned for follow-up.
- **Ephemeral workflow runs** — v1 progress is in-memory JS only. Run history persistence planned for follow-up.
- **App template htmx URLs hardcode app_id** — connect.html/connect_status.html use `/app/linear-sync/` prefix. SDK should inject this via Jinja2 global. Future apps with htmx forms will need the same fix.
- **Markdown block renders raw text** — not rendered HTML in v1 dashboards
- ViewSpecService's query_service param is optional (None default) — if not passed, user views silently return empty
- basic-pkm archive JSON parsing was fixed in M011/S01 (v2.0.0 upgrade) — refresh_artifacts now works correctly
- htmx target-aware block rendering in ops log uses manual HX-Target dispatch — fragile if new htmx consumers added
- SQL→RDF query migration must be manually run (POST /admin/migrate-queries) before applying Alembic 010

**Design references:**
- v0.3 design documents in `orig_specs/` (vision, specifications, decision log, schemas)
- `semantic-stack` reference project for triplestore Docker deployment
- `.planning/DECISIONS.md` — canonical v2.2 architecture reference (legacy, pre-migration)
- `.gsd/DECISIONS.md` — full decision corpus extracted during GSD-2 migration
- `.gsd/design/PROV-O-ALIGNMENT.md` — PROV-O predicate audit and migration plan
- `.gsd/design/VIEWS-RETHINK.md` — generic views with SHACL columns and query scope binding
- `.gsd/design/VFS-V2-DESIGN.md` — VFS v2 implementation guide with path contract

## Standing Requirements (every phase)

These apply to every plan, no exceptions. Executor must check both gates before writing the SUMMARY.

- **E2E tests**: Any new or changed user-visible behavior must have Playwright tests added or updated in `e2e/tests/`. Tests must pass against the running stack.
- **User guide docs**: Any user-visible feature added or changed must be reflected in `docs/guide/` (user guide pages). Create new pages or update existing pages as needed. **This is a planning-time requirement, not an afterthought** — every slice plan that adds user-visible features MUST include a dedicated docs task (typically the final task before or alongside E2E tests). If skipped (e.g. pure backend fix, refactor, test-only slice), state the reason explicitly in the slice plan and SUMMARY.

### Enforcement

During **roadmap planning**, every milestone that ships user-visible features MUST include two trailing coverage slices:
1. **E2E Test Coverage** slice — audits and fills test gaps across all shipped features
2. **User Guide Docs** slice — writes/updates `docs/guide/` pages for all new features

These are planned at roadmap time (not bolted on later) and depend on nothing, so they can run after any feature slice completes. This mirrors the M003 pattern where S10 caught E2E gaps — but extends it to docs.

During **slice planning**, the planner must also:
1. Check whether the slice adds or changes user-visible features
2. If yes, include an explicit task for updating `docs/guide/` (new page or existing page update)
3. The docs task should be planned with the same rigor as implementation tasks — specify which pages to create/update and what content to cover

The trailing docs slice acts as a safety net. Individual slice docs tasks are the first line of defense.

During **milestone completion**, the reviewer must:
1. Verify every user-visible feature has corresponding docs coverage
2. Document any gaps explicitly in the milestone summary
3. A milestone with docs gaps should note `verification_result: passed-with-gaps` (not `passed`)

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

| htmx page navigation for tool pages | Tool pages (Import Vault) should be htmx full-page navigation, not dockview tabs | ✓ Good — consistent with VFS browser pattern |
| Separate KDF salt per encryption domain | WebID keys and LLM keys use separate Fernet derivation domains | ✓ Good — key compromise isolation |
| Username immutable after creation | WebID URIs must be stable; links stored as JSON in Text column | ✓ Good — URI stability guaranteed |
| Standalone HTML profile page | WebID profile doesn't extend base.html; content negotiation via Accept + ?format= | ✓ Good — lightweight, works for RDF clients |
| Inline SVG for canvas icons | Avoids Lucide re-scan overhead on dynamic canvas nodes | ✓ Good — instant render, no async dependency |
| Custom MIME types for drag-drop | text/iri and text/label in dataTransfer for nav-tree-to-canvas DnD | ✓ Good — clean data channel, no parsing needed |
| SSE race condition fix for imports | Serve saved import_result.json when SSE broadcast closes before client connects | ✓ Good — reliable import status delivery |
| Unified CodeMirror theme via CSS vars | Single theme using CSS variables instead of dual dark/light CodeMirror themes | ✓ Good — auto-adapts to theme toggle |

---
*Last updated: 2026-04-05 after M047 complete (PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System. Manifest v2 format, source_model lifecycle, PillarScore + GuidingPrinciples types, 5 dashboards, 5 workflows, 150 tests, 7 decisions.)*
