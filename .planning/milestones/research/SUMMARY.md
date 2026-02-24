# Project Research Summary

**Project:** SemPKM
**Domain:** Semantic Personal Knowledge Management (RDF/SHACL-based PKM tool)
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH

## Executive Summary

SemPKM is a self-hosted personal knowledge management tool that uses RDF, SHACL, and event sourcing as its data core — delivering the semantic rigor of tools like Protege behind a consumer PKM UX that rivals Obsidian and Notion. The central thesis is that installable "Mental Models" (bundles of ontology + shapes + views + projections) bridge these two worlds: users install a domain experience and get structured forms, semantic graph views, and SPARQL-backed queries without ever writing a triple. The recommended build approach is an event-sourced CQRS stack: FastAPI on Python 3.12 as the command/query mediator, RDF4J as the triplestore (selected over unmaintained Blazegraph), pySHACL for application-side validation, rdflib for graph construction, and a split frontend of htmx (admin shell) plus React 19 (IDE Object Browser). All versions have been verified against live package registries.

The architecture follows a strict five-tier dependency order: triplestore foundation → core data path (event sourcing + SPARQL) → semantic services (labels, prefixes, SHACL) → Mental Model system → presentation layer. This ordering is non-negotiable: each tier depends entirely on the one below it, and shortcuts will create integration failures that are expensive to unwind. The "wow in 10 minutes" user success criterion — install SemPKM, install a Mental Model, create objects via auto-generated forms, browse in table/graph views, see linting guidance — defines the critical path through every phase.

The dominant risk in this project is the Ontology Astronaut Trap: RDF complexity leaking into the user interface and making the product feel like an academic tool rather than a PKM app. This must be treated as a first-class constraint in every phase, not just a UI polish concern. Secondary risks are event sourcing impedance mismatch with RDF triplestores (novel architecture with limited prior art), SHACL being bent into a UI framework beyond its design intent, and the lack of a Mental Model versioning/migration story that will strand users on v1 schemas. All four of these pitfalls have clear mitigations, but they require architectural discipline from the first phase onward.

---

## Key Findings

### Recommended Stack

The stack is fully specified and version-verified. Python 3.12 + FastAPI + uv is the backend baseline. RDF4J 5.2.2 (Docker) is the triplestore — Blazegraph must be avoided as it has not been maintained since 2020. rdflib 7.6 handles all Python-side RDF construction; pySHACL 0.31 handles validation (run in a thread pool executor to avoid blocking FastAPI's async event loop). SPARQLWrapper 2.0 handles SPARQL endpoint communication. The frontend is intentionally split: htmx 2.0 for the server-rendered admin shell (model management, webhooks, system status) and React 19 + TypeScript 5.9 + Vite 7 for the IDE Object Browser embedded in an iframe. Cytoscape.js 3.33 handles graph visualization; CodeMirror 6 handles the SPARQL editor; TanStack Query + Zustand manage server and client state respectively.

**Core technologies:**
- **Python 3.12 + FastAPI 0.129 + uvicorn**: HTTP API framework — async-native, Pydantic-native, generates OpenAPI docs; uv replaces pip for deterministic installs
- **RDF4J 5.2.2 (Docker)**: Triplestore — actively maintained by Eclipse Foundation, full SPARQL 1.1, named graph support essential for event sourcing
- **rdflib 7.6**: RDF graph construction and serialization — Python-native, handles Turtle/JSON-LD/N-Triples/TriG without plugins
- **pySHACL 0.31**: SHACL validation — only production-grade Python SHACL validator; must be run async via thread pool
- **SPARQLWrapper 2.0**: SPARQL client — mediates all triplestore communication from FastAPI
- **React 19 + Vite 7 + TypeScript 5.9**: IDE Object Browser — required for IDE-grade UX (pane layout, command palette, graph viz); not replaceable with htmx for this surface
- **htmx 2.0 + Jinja2 3.1**: Admin shell — server-rendered, no JS build step, correct tool for model management forms
- **Cytoscape.js 3.33**: Graph visualization — richest styling API for type-based node/edge rendering; switch to react-force-graph-2d only if performance degrades with large graphs
- **Tailwind CSS 4.2 + Radix UI**: IDE styling — utility-first, accessible primitives, v4 requires no PostCSS configuration
- **ruff + mypy + pytest**: Development quality — ruff replaces flake8/black/isort, mypy catches RDF/IRI type confusion bugs

### Expected Features

SemPKM sits at the intersection of consumer PKM tools (Obsidian, Notion, Logseq) and semantic/ontology tools (Protege, TopBraid). Table-stakes features must match consumer PKM UX expectations; differentiators come from the semantic core.

**Must have (table stakes):**
- Object creation with minimal friction — SHACL-driven forms must feel as fast as Obsidian's Cmd+N; minimal required fields, smart defaults
- Inline linking / wiki-link UX — typed edge creation must feel as fast as `[[wiki-links]]` even though it creates first-class Edge resources
- Table and cards views — sortable, filterable list views are the primary data browsing surface
- Full-text + structured search — users need a search bar that "just works" without writing SPARQL
- Graph visualization (2D) — Obsidian's graph view is iconic; SemPKM's semantic-aware styling is the differentiator
- Backlinks panel — trivially queryable in RDF; the context display matters more than the list itself
- Mental Model install/list/remove — the primary packaging and delivery mechanism for all experiences
- Keyboard shortcuts and command palette — IDE-grade UX requirement; already in spec
- SHACL lint panel — key differentiator; assistive guidance ("Project is missing a Status"), never punitive

**Should have (competitive differentiators):**
- Installable Mental Models — no other PKM tool has domain experience bundles; this is the primary competitive moat
- SHACL-driven auto-generated forms — forms appear automatically from shape definitions; no other consumer PKM does this
- First-class typed edges — typed, annotatable, inspectable relationships vs. Obsidian's untyped links
- Semantic-aware graph visualization — node color by RDF type, edge style by predicate, semantic filter criteria
- Parameterized dashboards — composed workspace views per object type (Project dashboard = overview + tasks + timeline + lint)
- Webhook-based automation — trigger n8n/external workflows on knowledge changes
- JSON-LD export — standards-based, no vendor lock-in

**Defer (v2+):**
- Filesystem projection — already deferred in PROJECT.md; strong differentiator when delivered, not required for core loop
- ActivityPub / SOLID publishing — already deferred; JSON-LD export is sufficient for v1 data portability
- Model marketplace / community discovery — v1 just needs file-based install; marketplace is v2+ network effects
- Timeline / calendar / kanban renderers — not core to the semantic knowledge value proposition; defer to v1.1/v2
- CSV / tool import — manual object creation via forms is the v1 path; CSV import is high-value v1.1
- 3D graph, multi-user collaboration, mobile native app, AI/LLM integration — explicitly anti-featured for v1

**Critical anti-features (never build):**
- SPARQL UPDATE as external write surface — would bypass event sourcing entirely; Command API only
- User-defined schemas / ontology editor — scope explosion; recommend Protege for model authoring
- Synchronous validation blocking writes — contradicts assistive-not-punitive principle

### Architecture Approach

The architecture follows an event-sourced CQRS pattern adapted for RDF: all writes go through a Command API that produces immutable events stored as named graphs in RDF4J; all reads go through SPARQL queries against a materialized `sempkm:current` graph derived from replaying events. The write path returns immediately; post-commit work (SHACL validation, filesystem projection, webhook notifications) happens asynchronously. The triplestore is never accessed directly by the frontend — all access is mediated by the FastAPI backend. The Admin Shell (htmx) and Object Browser (React, embedded in iframe) are strictly separated, communicating via a typed postMessage protocol.

**Major components:**
1. **Command API** — accept write commands (object.create, object.patch, body.set, edge.create, edge.patch, edge.delete), produce immutable event named graphs, apply delta to materialized current-state graph
2. **SPARQL Proxy** — forward SPARQL SELECT queries from the React IDE to RDF4J; inject prefix context; queries are read-only (no SPARQL UPDATE from frontend)
3. **Event Producer** — build event RDF graphs from commands using rdflib, SPARQL INSERT into `sempkm:events/<eventId>` named graphs
4. **SHACL Engine** — async validation of affected resources against installed shapes; stores validation reports; drives lint panel; never blocks writes
5. **Mental Model Manager** — install/remove/list `.sempkm-model` archives; validates bundles; loads ontology + shapes into named graphs; registers views and dashboards; extracts prefix declarations
6. **Label Service** — resolve IRIs to human labels (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback); must batch-resolve and cache aggressively; the primary defense against the Ontology Astronaut Trap
7. **Prefix Registry** — merge model/user/built-in prefix mappings; QName resolution for SPARQL editor and power-user panels
8. **Projection Service** — incremental filesystem projection (only files for changed objects); `.md` + `.meta.json` + `.edges.json`; atomic file writes
9. **Webhook Dispatcher** — best-effort outbound HTTP POST on events; notification-only payloads (not data dumps)
10. **Admin Shell (htmx)** — server-rendered model management, webhook configuration, system status
11. **Object Browser (React IDE)** — workspace layout (react-resizable-panels), command palette (cmdk), all renderers (object, form, table, cards, graph, dashboard), SHACL lint panel, SPARQL editor (CodeMirror 6)

**Named graph partitioning (non-negotiable):**
```
sempkm:events/<eventId>         -- immutable event graph
sempkm:current                   -- materialized current state (mutable derived)
sempkm:shapes/<modelId>          -- SHACL shapes for installed model
sempkm:ontology/<modelId>        -- ontology triples for installed model
sempkm:validation/<reportId>     -- immutable validation report
```

### Critical Pitfalls

1. **Ontology Astronaut Trap** — RDF terminology leaks into the UI, product feels academic, non-technical users bounce. Avoid by: enforcing the label service everywhere (no IRI/QName in primary UI), writing `sh:name` values for humans not ontologists, never exposing SPARQL to casual users, user-testing with non-technical people starting in Phase 2.

2. **Event Sourcing Impedance Mismatch with RDF** — event log is a novel pattern in triplestores with no established best practices; named graphs may not scale to tens of thousands of events without compaction; projection rebuild latency may grow. Avoid by: benchmarking named graph count early (10K and 50K events), designing compaction strategy before Phase 1 ships, keeping materialization synchronous but targeted (delta only, not full rematerialization), never querying event graphs for normal operations.

3. **Blazegraph is Abandonware** — last release 2018, no security patches, Java version compatibility issues. Already resolved by stack research: use RDF4J 5.2.2 exclusively. Build a triplestore abstraction layer so the store is swappable via config change.

4. **SHACL-Driven UI Becomes a Straitjacket** — SHACL was designed for validation, not UI generation; using it for conditional fields, dynamic defaults, autocomplete, and rich widgets requires adding custom non-standard extensions. Avoid by: using SHACL as the data contract (fields, types, constraints, ordering), never as the UI contract; using view/dashboard YAML specs for UI-specific behavior (widget hints, conditional display, autocomplete sources); hardcapping the SHACL UI profile to the defined v1 subset.

5. **Mental Model Versioning Vacuum** — v1 defers migrations, but any model update becomes a breaking change for existing data. Avoid by: enforcing additive-only model evolution (new fields with `sh:minCount 0` only, never rename or remove properties), including `schemaVersion` in manifests, rejecting model updates with breaking changes, designing the format for future migration even if tooling comes in v2.

6. **Edge Resource Complexity Explosion** — first-class `sempkm:Edge` resources triple the graph size and make view SPARQL queries 3-4x longer. Avoid by: always maintaining the simple triple projection so view specs use natural triple patterns, building a query abstraction that handles Edge indirection transparently, benchmarking 1000 objects with 10 edges each in Phase 1.

---

## Implications for Roadmap

Based on the architecture's five-tier dependency structure, the feature critical path, and pitfall prevention requirements, the following phase structure is recommended.

### Phase 1: Core Data Foundation

**Rationale:** Everything else depends on the triplestore running, event sourcing working, and the read/write data paths functioning end-to-end. This is Tier 0 + Tier 1 from the architecture dependency analysis. No UI, no Mental Models — just the semantic data plumbing.

**Delivers:**
- RDF4J Docker setup with named graph schema and IRI conventions
- Command API: object.create, object.patch, body.set, edge.create, edge.patch, edge.delete
- Event Producer: rdflib graph construction → SPARQL INSERT into event named graphs
- Materialization: delta projection from events to `sempkm:current` graph
- SPARQL Proxy: forward SELECT queries to RDF4J, inject prefix context
- Edge model: `sempkm:Edge` with simple triple projection; query abstraction layer
- Triplestore abstraction layer: swap store via config, not code changes

**Addresses (from FEATURES.md):** Core data path required by all features.

**Avoids (from PITFALLS.md):** Blazegraph abandonware (RDF4J from day one); Event Sourcing Impedance Mismatch (benchmark named graphs and projection latency; design compaction strategy); Edge Resource Complexity (simple triple projection always maintained); SPARQL injection (IRI-only template substitution, no f-string SPARQL construction).

**Research flag:** Needs `/gsd:research-phase` for event sourcing performance benchmarking approach — this is a novel RDF architecture with limited prior art.

---

### Phase 2: Semantic Services + SHACL Engine

**Rationale:** Before any UI can render usable output, IRIs must resolve to human labels, prefixes must be manageable, and SHACL validation must be wired up. These are Tier 2 services that depend on Phase 1's data path but are independent of the Mental Model system and UI. Building them here also establishes the SHACL boundary before the form renderer is written.

**Delivers:**
- Label Service: batch IRI-to-label resolution with LRU cache; invalidation on object.changed events; handles multilingual labels, blank nodes, label hierarchy
- Prefix Registry: merge model/user/built-in prefixes; QName resolution; conflict detection between models
- SHACL Engine: async validation (thread pool executor); incremental (validate only changed resources); validation report storage as `sempkm:validation/<reportId>` named graphs; lint panel data API

**Addresses (from FEATURES.md):** SHACL lint panel (key differentiator); prefix QName display in power-user panels.

**Avoids (from PITFALLS.md):** Ontology Astronaut Trap (label service is the primary defense — must be correct before any list view); SHACL-UI Straitjacket (establish the SHACL validation vs. UI rendering boundary before form renderer is written); Label Resolution N+1 (batch resolver and cache must exist before table views are built).

**Research flag:** Standard patterns for SHACL engine and label service are well-specified in the project docs. Can skip `/gsd:research-phase`.

---

### Phase 3: Mental Model System

**Rationale:** Mental Models are the primary packaging mechanism for all user-facing domain experiences. They must be installable before any meaningful UI can be built, because the starter model (Basic PKM) is the first test case for forms, views, and dashboards. This is Tier 3, depending on the SHACL engine (Phase 2) and prefix registry (Phase 2).

**Delivers:**
- Bundle format parser: read `.sempkm-model` ZIP archives; extract manifest.yaml, ontology.ttl, shapes.ttl, view specs, seed data
- Bundle Validator: schema validation, ID uniqueness/namespacing, reference integrity, export policy, renderer compatibility, zip slip protection
- Mental Model Manager: install/remove/list; load ontology and shapes into named graphs; register views and dashboards; extract prefix declarations; load seed data; atomic install (all-or-nothing rollback on failure)
- Additive-only evolution enforcement: `schemaVersion` in manifests; reject breaking model updates
- Starter Mental Model (Basic PKM): Projects, People, Notes, Concepts — must be polished; this IS the first user-facing product

**Addresses (from FEATURES.md):** Mental Model install/list/remove; installable domain experiences (core differentiator); starter model for "wow in 10 minutes" criterion.

**Avoids (from PITFALLS.md):** Mental Model Versioning Vacuum (additive-only enforcement, schemaVersion, breaking change rejection); Mental Model Archive Security (zip slip protection, SPARQL/SHACL parsing before loading).

**Research flag:** Bundle format and validation rules are thoroughly specified in project docs. Standard patterns apply. Can skip `/gsd:research-phase`.

---

### Phase 4: Admin Shell + Core UI Foundation

**Rationale:** With the data path and Mental Model system working, the first user-facing surfaces can be built. The admin shell is straightforward (htmx + Jinja2, server-rendered); the React IDE foundation establishes the workspace layout, state management, and the first two renderers (object and form). The form renderer proves the SHACL-driven UI contract and represents the "wow in 10 minutes" moment when a user installs a Mental Model and sees a form appear automatically.

**Delivers:**
- Admin Shell (htmx): Model management UI (install/remove/list), webhook configuration, system status, health indicators; auto-install starter model on first launch
- React IDE foundation: Vite 7 + TypeScript 5.9 + Tailwind CSS 4.2 + Radix UI setup; workspace layout with react-resizable-panels; Zustand state (open tabs, active pane, selected object); TanStack Query (SPARQL result caching); command palette (cmdk)
- Object renderer: display a single object's properties with human-readable labels; backlinks panel
- Form renderer: SHACL-driven auto-generated create/edit forms; respects sh:name, sh:order, sh:group, sh:datatype, sh:minCount; optimistic UI (save immediately, show validation results async); SHACL lint panel (assistive, never blocking); human-readable violation messages via sh:message

**Addresses (from FEATURES.md):** Object creation with minimal friction (#1 MVP priority); SHACL lint panel; backlinks panel; admin/system management.

**Avoids (from PITFALLS.md):** Ontology Astronaut Trap (no IRIs/QNames in primary UI; validate with non-technical user testing in this phase); SHACL-UI Straitjacket (form renderer reads only defined v1 SHACL UI profile properties; UI-specific behavior lives in view YAML); UX pitfall of showing validation errors on empty creation (show hints on typing, violations only on save/publish).

**Research flag:** htmx + FastAPI integration is well-documented. React IDE architecture is standard. Can skip `/gsd:research-phase`.

---

### Phase 5: Data Browsing + Graph Visualization

**Rationale:** Users can create objects after Phase 4; now they need to browse and explore them. Table and cards renderers are the most-used daily views. Graph visualization is the iconic PKM differentiator that makes the semantic layer visible. The SPARQL editor serves power users and Mental Model authors. Together these complete the core create/browse/explore loop.

**Delivers:**
- Table renderer: TanStack Table; sort, filter, pagination; batch label resolution (never N+1); SPARQL SELECT → tabular display
- Cards renderer: visual card layout; maps SPARQL SELECT bindings to card layout
- Graph renderer: Cytoscape.js 3.33; force-directed layout; node color by RDF type; edge style by predicate; type-based semantic filtering; depth-bounded traversal (not full CONSTRUCT); interactive expansion
- Dashboard renderer: compose panels (objectSelf, view, lintSummary, markdown); type-based dashboard registry; "Open with..." switcher
- SPARQL editor: CodeMirror 6 with SPARQL mode; prefix auto-injection from registry; power-user / model author tool

**Addresses (from FEATURES.md):** Table and cards views (#2 MVP priority); graph visualization (#7 MVP priority); SPARQL-powered views (core differentiator); parameterized dashboards; type-based dashboard registry.

**Avoids (from PITFALLS.md):** Label Resolution N+1 (batch resolver mandatory before any list view); Unbounded SPARQL CONSTRUCT for graph visualization (always LIMIT; depth-bounded traversal; interactive expansion); graph visualization as default view (dashboard/object page is default; graph is power-user tool); SPARQL editor never exposed as a primary interface to casual users.

**Research flag:** Cytoscape.js integration with React and typed RDF data may benefit from `/gsd:research-phase` — specifically the pattern for mapping SPARQL CONSTRUCT results to Cytoscape's node/edge model with semantic styling.

---

### Phase 6: Search + Linking UX + Derived Services

**Rationale:** The core loop is functional after Phase 5. This phase adds the "glue" features that make day-to-day use feel complete: instant search (without writing SPARQL), wiki-link-style typed edge creation UX, and the derived services (filesystem projection, webhooks, JSON-LD export) that extend SemPKM into the broader tool ecosystem.

**Delivers:**
- Search: text index for body content (SQLite FTS or Tantivy; not full-text in triplestore); SPARQL-structured search for power users; unified search bar that "just works"
- Inline linking UX: wiki-link-speed typed edge creation; autocomplete for object search; typed relationship picker; creates `sempkm:Edge` resources via Command API
- JSON-LD export: serialize subsets of `sempkm:current` graph as JSON-LD; standards-based data portability
- Webhook Dispatcher: outbound HTTP POST on events; notification-only payloads; configurable via admin shell; best-effort delivery with retry
- Filesystem Projection Service: incremental projection (only changed objects); atomic file writes (temp + rename); `.md` + `.meta.json` + `.edges.json`; delete events clean up files; Obsidian interop

**Addresses (from FEATURES.md):** Search (#4 MVP priority); inline linking (#3 MVP priority); JSON-LD export; webhook automation; filesystem projection (strong differentiator).

**Avoids (from PITFALLS.md):** Full-text indexing in the triplestore (use separate text index; triplestores have poor FTS performance); Eager projection refresh on batch operations (debounce projection updates; single sweep after batch commits); Webhook payloads containing sensitive graph data (notification-only payloads, not data dumps); projection not cleaning up deleted object files.

**Research flag:** Full-text search implementation choice (SQLite FTS vs. Tantivy vs. other) may benefit from `/gsd:research-phase` to validate performance characteristics at PKM scale.

---

### Phase Ordering Rationale

- Phases 1-3 are strictly ordered by architectural dependency: triplestore before events, events before SHACL, SHACL before Mental Models. No shortcuts.
- Phases 4-5 are ordered by user value: admin + creation before browsing, because users must be able to create objects before they can browse them. Within Phase 4, object renderer before form renderer is also dependency-ordered (form renderer uses label service + SHACL engine built in Phases 2-3).
- Phase 6 is deliberately last because it contains the highest-risk items (novel search architecture, complex UX for inline linking) and the derived services (projection, webhooks) that are valuable but not required for the core loop. These should be built after the core loop is validated with real users.
- The "wow in 10 minutes" criterion (install → model → forms → views → lint) is first achievable at the end of Phase 5. Phases 1-4 incrementally build toward this milestone, with Phase 4 delivering the first meaningful user-facing moment (form renderer + starter model).

### Research Flags

**Phases likely needing `/gsd:research-phase` during planning:**
- **Phase 1 (Core Data Foundation):** Event sourcing in RDF triplestores is a novel architecture with limited prior art. Benchmarking strategy and named graph compaction approach need deeper research.
- **Phase 5 (Graph Visualization):** Cytoscape.js + React integration with SPARQL CONSTRUCT results and semantic styling requires concrete pattern research before implementation.
- **Phase 6 (Search):** Full-text search implementation choice (SQLite FTS vs. Tantivy) should be validated against PKM-scale performance requirements.

**Phases with standard patterns (skip `/gsd:research-phase`):**
- **Phase 2 (Semantic Services):** Label service and prefix registry are thoroughly specified in project docs. Standard Python service patterns apply.
- **Phase 3 (Mental Model System):** Bundle format and validation rules are fully specified. ZIP parsing and SPARQL/SHACL loading are standard operations.
- **Phase 4 (Admin Shell + Core UI):** htmx + FastAPI is well-documented; React IDE architecture uses standard patterns (Vite, Zustand, TanStack Query).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All Python/npm versions verified against live package registries (PyPI JSON API, npm registry) on 2026-02-21. RDF4J Docker image verified (5.2.2, pushed 2025-12-16). Triplestore selection (RDF4J over Blazegraph) is well-justified. |
| Features | MEDIUM-HIGH | Table stakes vs. differentiators analysis is HIGH confidence (PKM market expectations are stable). Competitive feature comparison is MEDIUM (specific product features may have changed since training data cutoff; Obsidian/Notion core features are stable). Anti-feature recommendations are HIGH (principled architectural decisions). |
| Architecture | MEDIUM-HIGH | Architecture is grounded in detailed project specs (vision.md, decision log v0.3, API spec, SHACL UI profile, event types). CQRS/event sourcing patterns are HIGH confidence (well-established). RDF-specific event sourcing is MEDIUM (novel, limited prior art). Blazegraph/RDF4J comparison is MEDIUM (training data). |
| Pitfalls | HIGH | Pitfalls derived from deep analysis of project specs + known semantic web ecosystem failure modes. RDF reification complexity and SHACL-UI limitations are well-documented. Blazegraph abandonment status is verified via Docker Hub API (last push 2020-04-02). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **RDF event sourcing performance**: The specific performance envelope of named-graph-based event sourcing in RDF4J at PKM scale (thousands of objects, tens of thousands of events) is not well-documented. Phase 1 must include concrete benchmarks as acceptance criteria (projection rebuild in <5s for 10K events; named graph queries <100ms for typical view).

- **pySHACL incremental validation performance**: pySHACL 0.31 performance on incremental (per-resource) validation vs. full-graph validation at 10K objects is unknown. Must validate in Phase 2 whether incremental validation stays within acceptable latency bounds for the async post-commit pipeline.

- **Edge resource query ergonomics**: The query abstraction that makes `?project ex:hasMember ?person` work transparently over `sempkm:Edge` resources needs concrete design work in Phase 1. The abstraction must be validated against all planned view types before Phase 5's renderers are built.

- **htmx + React iframe communication protocol**: The typed postMessage protocol between the htmx admin shell and React IDE needs concrete design in Phase 4. Avoid ad-hoc postMessage payloads — define a versioned message schema before building either side.

- **Mental Model authoring toolchain**: v1 assumes developers/semantic web experts create Mental Models using Protege + packaging tools. The documentation and workflow for this needs to be established alongside Phase 3 so the starter model can be tested and iterated on.

---

## Sources

### Primary (HIGH confidence — live-verified)
- **PyPI JSON API** (pypi.org/pypi/{package}/json) — all Python package versions (rdflib 7.6.0, FastAPI 0.129.0, pySHACL 0.31.0, SPARQLWrapper 2.0.0, Pydantic 2.12.5, uvicorn 0.41.0, httpx 0.28.1, and 20+ others)
- **npm registry** (registry.npmjs.org/{package}/latest) — all npm package versions (React 19.2.4, Vite 7.3.1, TypeScript 5.9.3, Zustand 5.0.11, TanStack Query 5.90.21, Cytoscape.js 3.33.1, CodeMirror 6.39.15, Tailwind CSS 4.2.0, and others)
- **Docker Hub API** — RDF4J Workbench 5.2.2 (pushed 2025-12-16), Blazegraph 2.1.5 (last pushed 2020-04-02, confirming abandonment)
- **SemPKM project specs** — vision.md, PROJECT.md, decision log v0.3, API spec overview, SHACL UI profile, gating policy, view/dashboard/projection/prefix/label/event/mental-model specs, starter-basic-pkm model

### Secondary (MEDIUM confidence — training data)
- **PKM competitive landscape** — Obsidian, Notion, Roam Research, Logseq, Tana, Capacities feature sets (accurate to early 2025; specific features may have evolved)
- **Semantic web tooling** — Protege, TopBraid, PoolParty, Semantic MediaWiki capabilities (stable tooling, high confidence)
- **W3C SHACL Core specification** — validation semantics, sh:property constraints, SHACL UI profile design (standards change slowly)
- **RDF4J and Blazegraph architecture** — internal architecture, named graph indexing, SPARQL 1.1 compliance characteristics

### Tertiary (LOW confidence — novel/needs validation)
- **RDF-specific event sourcing patterns** — limited prior art; benchmarking required to validate performance assumptions
- **pySHACL incremental validation performance** — library capabilities documented but performance at scale needs empirical testing
- **Cytoscape.js + React + SPARQL CONSTRUCT integration patterns** — requires concrete pattern validation during Phase 5 planning

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
