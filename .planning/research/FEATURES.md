# Feature Landscape: Semantic PKM / RDF Knowledge Management

**Domain:** Semantic Personal Knowledge Management (PKM with RDF/SHACL core)
**Researched:** 2026-02-21
**Confidence:** MEDIUM (based on training data knowledge of PKM tools and semantic web ecosystem; no live web verification available)

## Competitive Landscape Context

SemPKM sits at the intersection of two worlds:

1. **Consumer PKM tools** (Obsidian, Notion, Roam Research, Logseq, Capacities, Tana, Anytype) -- users expect frictionless note-taking, linking, and browsing. These tools compete on speed, aesthetics, and "just works."

2. **Semantic/ontology tools** (Protege, TopBraid Composer/EDG, PoolParty, Semantic MediaWiki, LinkedDataHub, Metaphactory) -- power users expect standards compliance, SPARQL, ontology management, and data governance. These tools compete on expressiveness and enterprise capability.

SemPKM's thesis is that Mental Models bridge these worlds: the semantic rigor of RDF/SHACL becomes invisible behind installable experiences. This means table-stakes features must satisfy the PKM crowd's UX expectations, while differentiators come from the semantic core that no consumer PKM tool offers.

---

## Table Stakes

Features users expect from any modern PKM tool. Missing = product feels incomplete and users leave for Obsidian/Notion/Logseq.

### Content Creation and Editing

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Rich text / Markdown editing | Every PKM tool has this; it is the primary interaction | Med | SemPKM's `body.set` stores one markdown body per object. Need a good editor (CodeMirror, ProseMirror, or similar). |
| Object/note creation with minimal friction | Obsidian: Cmd+N, done. Notion: /command, done. Users expect sub-second creation. | Low | SHACL-driven forms must not add friction to creation. Default values and minimal required fields are critical. |
| Inline linking / wiki-links | `[[Page Name]]` linking is the defining PKM interaction since Roam popularized it in 2019. | Med | SemPKM creates edges. The linking UX must feel as fast as wiki-links even though it creates first-class Edge resources underneath. |
| Search (full-text + structured) | Users expect instant search across all content. Obsidian, Notion, Roam all have fast search. | Med | SPARQL powers structured queries, but users also need simple text search without writing SPARQL. Need a search bar that "just works." |
| Tags / labels / categories | Basic organizational primitive in every PKM tool | Low | In SemPKM this maps naturally to RDF types and SKOS concepts. The UX must make tagging as easy as typing `#tag`. |
| Keyboard shortcuts / command palette | Obsidian's Cmd+P command palette is expected by power users. "IDE-grade" demands this. | Med | Already in SemPKM spec. |
| Undo / version history | Users expect to be able to undo mistakes and see previous versions | Med | Event sourcing gives this "for free" architecturally, but UX to browse history and revert is separate work. |

### Content Browsing and Navigation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| List/table view of objects | Notion's database views set the standard. Users expect to see their data as sortable/filterable tables. | Med | SemPKM has table renderer. Must support sort, filter, pagination. |
| Card/gallery view | Notion, Capacities, Tana offer card layouts. Visual browsing is expected for certain content types. | Med | SemPKM has cards renderer. |
| Graph visualization (2D) | Obsidian's graph view is iconic for PKM. Users expect to see connections visually. | High | Already in spec. Semantic-aware styling (node color by type, edge style by predicate) is key differentiator over Obsidian's generic graph. |
| Backlinks / incoming references | Roam and Obsidian made backlinks a PKM standard. "What links to this?" is essential. | Low | Trivially queryable in RDF. The UX panel matters -- show context, not just a list. |
| Breadcrumb / navigation trail | Users expect to know where they are and how they got there | Low | Standard UI pattern. |
| Recent items / quick access | Users return to recently viewed items constantly | Low | Track in session state. |

### Data Organization

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Type system / object types | Notion databases, Tana supertags, Capacities object types -- typed data is expected in modern PKM. | Med | SemPKM's RDF types + SHACL shapes provide this natively. The UX must make types discoverable and easy to use. |
| Custom properties / fields per type | Notion properties, Obsidian properties (YAML), Tana fields -- users expect to define what data an object holds. | Med | SHACL shapes define this. In v1, shapes come from Mental Models, not user customization. This is a deliberate constraint that must be communicated clearly. |
| Bookmarks / favorites / pinned items | Quick access to frequently used objects | Low | Simple metadata flag. |

### Import and Export

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Data export (JSON-LD, Markdown) | Users refuse lock-in. Export is a trust signal. | Med | JSON-LD export is in spec. Markdown projection provides this. |
| Basic import (at least paste/manual entry) | Users need to get existing data in. Perfect import is not expected in v1, but some path is required. | Med | Listed as open question in v0.3. At minimum, manual object creation via forms. CSV import is highly desirable for v1. |

### System Administration

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Installation / setup that works | Self-hosted Docker apps must "just docker-compose up" | Med | Already planned via Docker. |
| Model/plugin management UI | Obsidian settings, Notion integrations -- users expect a UI to manage extensions. | Med | Mental Model manager is in spec. Install/remove/list. |
| System health / status | Self-hosted apps need basic health indicators | Low | Admin portal in spec. |

---

## Differentiators

Features that set SemPKM apart from both consumer PKM tools and semantic tools. These create competitive advantage and are the reason SemPKM exists.

### Mental Models (Core Differentiator)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Installable Mental Models** | No other PKM tool has "install a domain experience." Obsidian has themes/plugins but not complete knowledge domain bundles. This is SemPKM's killer feature. | High | Bundle: ontology + shapes + views + projections. This is the bridge between semantic rigor and consumer UX. |
| **Instant structured experiences from install** | Eliminates blank-page syndrome. Install "Research Papers" model, immediately get forms, views, and dashboards for papers, authors, citations. | High | Depends on model quality. The starter model (Basic PKM) must be excellent. |
| **Model marketplace / community models** | Network effects -- community creates domain models. Like Obsidian's plugin ecosystem, but for knowledge domains. | High | v1 only needs "install from file." Marketplace is v2+. But the format must be designed for this future. |
| **Cross-model composition with export control** | Models can share views/dashboards explicitly. Private-by-default prevents accidental coupling. No other tool has modular, composable knowledge schemas. | Med | Already well-spec'd. |

### Semantic Power Under Consumer UX

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **SHACL-driven auto-generated forms** | Forms auto-generated from shapes -- no manual form building. When a model defines a shape, the create/edit UI appears automatically. No consumer PKM does this. | High | The SHACL UI profile is well-defined. The implementation quality determines whether this feels magical or clunky. |
| **Typed relationships (first-class edges)** | Obsidian links are untyped. Notion relations are database-scoped. SemPKM edges are typed, annotatable, and inspectable. This enables "Why is X related to Y?" not just "X links to Y." | High | sempkm:Edge with optional simple-triple projection. The UX for creating typed edges must be as easy as wiki-links. |
| **SHACL validation as assistive linting** | Like an IDE linter for your knowledge. No consumer PKM validates data structure. Shows "your Project is missing a status" as guidance, not punishment. | Med | Async validation + lint panel. Violations gate conformance ops only. This is the right UX decision -- validation helps but never blocks editing. |
| **SPARQL-powered views** | Views backed by real queries. Obsidian Dataview is close but uses a custom query language. SemPKM uses the standard (SPARQL). Enables queries impossible in consumer tools. | Med | The gap is UX: most PKM users cannot write SPARQL. Mental Models provide pre-built views, and eventually a visual query builder could help. |
| **Semantic graph visualization** | Not just "nodes and edges" like Obsidian. Nodes styled by RDF type, edges styled by predicate, filterable by semantic criteria. | High | This is where SemPKM's graph view can dramatically outperform Obsidian's generic blob. |
| **Standards-based data (RDF/JSON-LD)** | Data is never locked in. It is actual Linked Data. Interoperable with the entire semantic web ecosystem. No consumer PKM offers this. | Low | This is an architectural choice, not a feature to build -- but it must be communicated as a value proposition. |

### Dashboards and Workspace Composition

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Parameterized dashboards** | Open a Project and see: overview, related tasks, timeline, lint summary -- all in one workspace. Not just a page, but a composed workspace. Notion has database views; SemPKM has full dashboard composition. | High | Distinct from object rendering. Panel types: objectSelf, view, lintSummary, markdown. |
| **Type-based dashboard registry** | "Open a Person and this dashboard appears." Mental Models define default dashboards per type. Automatic, zero-config for end users. | Med | Registry mapping: class/type to dashboard ID. "Open with..." for switching. |

### Event Sourcing and Automation

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Full event history / audit trail** | Every change is an immutable event. Complete audit trail. No consumer PKM offers this (version history is partial at best). | Med | Event log is the canonical truth. UX to browse the event log is separate and can be basic in v1. |
| **Webhook-based automation** | Trigger external workflows on knowledge changes. "When a new Project is created, notify Slack." Obsidian has no native automation; Notion has limited API. | Med | Simple outbound webhooks in v1. The power comes from pairing with n8n or similar. |

### Interoperability

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Filesystem projection (read-only)** | Open your RDF knowledge graph in Obsidian as markdown files. Bridge between SemPKM and the entire markdown-tool ecosystem. | High | Deferred past initial v1 per PROJECT.md. IRI-to-path mapping + sidecars. This is a strong differentiator when delivered. |
| **JSON-LD export** | Standards-based export. Interoperable with any JSON-LD consumer. | Low | In v1 scope. |
| **Prefix registry / QName resolution** | Professional semantic web UX: IRIs rendered as readable QNames, SPARQL editor gets auto-prefixes. Bridges the gap between raw RDF and usability. | Med | Well-spec'd. Necessary for the "semantic power under consumer UX" promise. |

---

## Anti-Features

Features to explicitly NOT build. These are tempting but wrong for SemPKM.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **General-purpose Markdown editor competing with Obsidian/Typora** | SemPKM is not a text editor. Competing on Markdown editing quality is a losing game against dedicated tools. | Embed a good editor component (CodeMirror 6 or ProseMirror), keep it solid but not the focus. The value is structured knowledge, not text editing. |
| **SPARQL UPDATE as external write surface** | Bypasses event sourcing, breaks audit trail, creates consistency nightmares. | Command API only. SPARQL is read-only. This is a firm architectural decision. |
| **User-defined schemas / ontology editor in v1** | Protege is an ontology editor. SemPKM is a knowledge tool that uses ontologies. Building an ontology editor is a massive scope explosion and alienates non-semantic-web users. | Mental Models provide schemas. v2+ can add user property overrides. Recommend Protege for advanced model authoring. |
| **Multi-user collaboration in v1** | Collaboration adds auth, permissions, conflict resolution, real-time sync. Each one is a major project. v1 is single-user. | Design data model to not preclude multi-user later, but do not build it. |
| **Bidirectional sync (ActivityPub, SOLID, filesystem)** | Bidirectional sync with conflict resolution is one of the hardest problems in distributed systems. | v1 is outbound-only. Read-only projections. Build the uni-directional path first. |
| **AI/LLM integration as a core feature** | Notion, Obsidian, and Roam are all adding AI. Tempting, but AI features are a moving target and SemPKM's differentiator is semantic structure, not AI. | Keep the architecture AI-friendly (structured data is ideal for LLM consumption), but do not build AI features in v1. Mental Models + RDF is the moat, not AI. |
| **Real-time collaborative editing** | Google Docs style collaboration requires CRDT/OT, conflict resolution, presence indicators. Enormous complexity. | Single-user v1. Event sourcing provides a foundation for eventual multi-user, but not v1. |
| **Mobile native app** | Requires separate codebase, offline sync, different UX paradigm. | Web-first, responsive design. Mobile can come later as PWA. |
| **Full-text indexing in the triplestore** | Triplestores have limited full-text search. Building a search engine inside the triplestore is fighting the tool. | Use a separate lightweight search index (e.g., SQLite FTS, Tantivy, or simple in-memory index) for text search. SPARQL handles structured queries. |
| **Complex permission / ACL system** | Enterprise feature that adds massive complexity. Single-user v1 does not need it. | Single-user auth (token or basic auth). Design data model to not preclude permissions later. |
| **Kanban / calendar / timeline views in v1** | High complexity renderers that are not core to the "semantic knowledge" value proposition. Every tool has Kanban; it is not differentiating. | Defer to v1.1/v2 as specified. Table, cards, graph, form, object, dashboard are the v1 renderers. |

---

## Feature Dependencies

```
SHACL Engine (validation) ──────────┐
                                     ├──> SHACL-driven Forms
SHACL UI Profile (sh:property, etc) ┘

RDF Triplestore + SPARQL ──────────> View Execution (queries)
                                     ├──> Table Renderer
                                     ├──> Cards Renderer
                                     ├──> Graph Renderer
                                     └──> Object Renderer

Command API (writes) ──────────────> Object Creation
                                     ├──> Edge Creation
                                     └──> Body Editing

Event Log ─────────────────────────> Version History
                                     ├──> Webhook Notifications
                                     └──> Materialized Current State

Mental Model Format ───────────────> Mental Model Manager (install/remove)
                                     ├──> Model Validation
                                     ├──> View/Dashboard Registry
                                     └──> Prefix Registry

Label Service + Prefix Registry ───> All UI Rendering (human-readable IRIs)

SHACL-driven Forms + Command API ──> Object Create/Edit UX (the core loop)

View Execution + Renderers ────────> Dashboards (compose panels)

Materialized State + SPARQL ───────> All Read Operations
```

### Critical Path (what blocks everything else)

```
1. RDF Triplestore + SPARQL endpoint (foundation)
2. Event Log + Command API (write path)
3. Materialized Current State (read path)
4. Label Service + Prefix Registry (usable rendering)
5. SHACL Engine (validation + form generation)
6. Mental Model format + installer (content delivery)
7. Core Renderers (table, form, object at minimum)
8. IDE Shell (workspace to put it all in)
```

### Secondary Dependencies

```
Graph Renderer ──> requires good force-layout library + semantic styling rules
Dashboards ──> requires view execution + at least 2 panel types working
Backlinks panel ──> requires SPARQL reverse-link query (trivial once SPARQL works)
Search ──> requires separate text index OR SPARQL regex (regex is slow; index is better)
Webhooks ──> requires event log (must be working first)
JSON-LD Export ──> requires materialized state + serialization library
Filesystem Projection ──> requires materialized state + IRI-path mapping
```

---

## Feature Comparison Matrix: SemPKM vs. Competitors

| Feature | Obsidian | Notion | Roam | Logseq | Tana | Protege | TopBraid | SemPKM (planned) |
|---------|----------|--------|------|--------|------|---------|----------|-----------------|
| Markdown editing | Strong | Medium | Weak | Strong | No | No | No | Medium (embedded) |
| Typed objects | Weak (YAML) | Strong | Weak | Weak | Strong | Strong | Strong | Strong (RDF) |
| Typed relationships | No | Limited | No | No | Limited | Strong | Strong | Strong (edges) |
| Graph view | Basic | No | Basic | Basic | No | Complex | Complex | Semantic-aware |
| Schema validation | No | No | No | No | Partial | Strong | Strong | Strong (SHACL) |
| Installable domain bundles | Plugins (code) | Templates | No | No | No | No | No | Mental Models |
| SPARQL / semantic queries | No | No | Datalog | No | No | Yes | Yes | Yes |
| Data portability | High (files) | Low | Low | High (files) | Low | High (RDF) | High (RDF) | High (RDF + files) |
| Automation hooks | Limited | Limited | No | No | No | No | Yes | Webhooks |
| Assistive validation | No | No | No | No | Partial | Yes (strict) | Yes (strict) | Yes (assistive) |
| IDE-grade workspace | Yes | No | No | Partial | No | Yes | Yes | Yes (planned) |
| Offline / local-first | Yes | No | No | Yes | No | Yes | No | Yes (self-hosted) |

---

## MVP Recommendation

### Prioritize (v1 Must-Ship)

1. **Object creation via SHACL-driven forms** -- This is the "wow in 10 minutes" moment. Install model, create object via auto-generated form. If this is clunky, nothing else matters.
2. **Table and cards views** -- Users need to see their data. These are the two most useful views for day-to-day use.
3. **Inline linking / edge creation** -- PKM without linking is not PKM. Typed edges are the differentiator, but the linking UX must feel wiki-link fast.
4. **Search (basic)** -- Users must be able to find things. Even a simple prefix-match search is acceptable for v1 if SPARQL-powered search is available for power users.
5. **Mental Model install/list/remove** -- The delivery mechanism for the entire experience.
6. **Starter Mental Model (Basic PKM)** -- Projects, People, Notes, Concepts. Must be polished. The first model IS the product for most users.
7. **Graph view (2D, basic)** -- Iconic PKM feature. Even a basic force-directed graph with type-based coloring is compelling.
8. **Backlinks panel** -- Expected in PKM. Trivial to implement once SPARQL works.
9. **SHACL lint panel** -- Key differentiator. "Your Project is missing a status" is immediately useful guidance.
10. **Object page / dashboard (at least one working)** -- Users need somewhere to land when they open an object.

### Defer from v1 (despite being in vision doc)

- **Filesystem projection**: Already deferred in PROJECT.md. Deliver it in v1.1. The core create/browse/explore loop does not require it.
- **ActivityPub / SOLID publishing**: Already deferred in PROJECT.md. Export as JSON-LD is sufficient for v1 data portability.
- **3D graph**: Experimental. 2D graph is sufficient and simpler.
- **Model marketplace / discovery**: v1 just needs file-based install. Community discovery is v2+.
- **Timeline / calendar renderers**: Deferred to v1.1/v2 as specified.
- **Import from other tools**: Nice to have, but manual object creation via forms is the v1 path. CSV import is a high-value v1.1 feature.
- **Event log browsing UI**: Event sourcing powers the architecture, but a full event history browser is not essential for v1 UX. Basic "last modified" indicator is sufficient.

### Sequence Rationale

The v1 experience must achieve the "wow in 10 minutes" success criterion:

**Install SemPKM -> Install a Mental Model -> Create objects via forms -> See tables/cards/graph views -> Linting guides structure**

This means the critical path is: triplestore -> event log -> command API -> materialized state -> SHACL engine -> mental model installer -> forms -> renderers -> IDE shell. Everything else is secondary.

---

## Gap Analysis: What SemPKM Must Solve That Competitors Have Not

1. **The SPARQL usability gap**: Power users want SPARQL; broad PKM users do not know it. Mental Models pre-build views, but eventually a visual query builder or "smart filters" UI would bridge this.

2. **The ontology authoring gap**: Who creates Mental Models? v1 assumes developers/semantic web experts create models that broad users consume. This is the right choice for v1, but the model creation toolchain (using Protege + packaging tools) must be documented.

3. **The performance perception gap**: Triplestores and SPARQL can be slow for simple operations. The materialized state helps, but the UI must feel snappy. Aggressive caching and optimistic UI updates are essential.

4. **The learning curve gap**: RDF terminology (IRI, triple, predicate) leaks through in error messages, URIs, debug panels. The label service and prefix registry help, but every user-facing surface must prefer human labels over technical identifiers.

---

## Sources

- SemPKM PROJECT.md and vision.md (primary project context)
- SemPKM spec documents (mental model format, SHACL UI profile, views, dashboards, events, etc.)
- Training data knowledge of Obsidian, Notion, Roam Research, Logseq, Tana, Capacities, Anytype feature sets (MEDIUM confidence -- based on knowledge through early 2025, features may have changed)
- Training data knowledge of Protege, TopBraid, PoolParty, Semantic MediaWiki capabilities (MEDIUM confidence -- based on knowledge through early 2025)
- Training data knowledge of SHACL, RDF, SPARQL standards and ecosystem (HIGH confidence -- standards change slowly)

**Confidence notes:**
- Feature categorization (table stakes vs differentiators): HIGH confidence. The PKM market expectations are well-established and stable.
- Competitive feature comparison: MEDIUM confidence. Specific product features may have changed since training data cutoff. Obsidian, Notion, and Roam core features are stable; newer tools (Tana, Capacities) evolve faster.
- Complexity estimates: MEDIUM confidence. Based on general software engineering judgment and the SemPKM architecture; actual complexity depends on implementation details.
- Anti-feature recommendations: HIGH confidence. These are principled architectural decisions aligned with the project's stated constraints.
