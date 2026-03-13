# M003: Workspace UX & Knowledge Organization — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

## Project Description

M003 overhauls how users navigate, organize, and understand their knowledge in SemPKM. The explorer panel gains a mode dropdown to switch between different organizational strategies (by-type, by-hierarchy, by-tag, by-VFS-mount). The ontology becomes visible through dedicated TBox/ABox/RBox views rooted at gist 14.0.0. Users can create new classes through the UI. Objects gain threaded comments, per-user favorites, and proper tag handling.

## Why This Milestone

The workspace explorer currently shows objects in a single flat-by-type view. Users with hundreds of objects have no way to navigate by hierarchy, tag, date, or custom organization without switching to the VFS browser (which shows flat markdown, not rich objects). Tags from seed data are stored as comma-separated strings instead of individual triples. The ontology is completely invisible — users can't see how their types relate, what properties exist, or how mental models connect. There's no way to create new types without editing model packages by hand.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Switch the explorer between by-type, by-hierarchy, by-tag, and VFS-mount organization modes
- See objects organized by dcterms:isPartOf parent/child hierarchy with arbitrary nesting
- See VFS mount specs rendered as object trees in the explorer (not just flat files)
- See tags as individual # pills, browse objects by tag in the explorer
- Star objects and find them in a dedicated FAVORITES explorer section
- Add threaded comments on any object, visible to all users
- Browse the full ontology (TBox class hierarchy, ABox instances, RBox properties) in the workspace
- See how their mental model classes fit into the gist upper ontology hierarchy
- Create a new class (name, icon, parent class, basic properties) through the UI
- See real stats and charts on admin model detail pages

### Entry point / environment

- Entry point: `http://localhost:3000` (workspace browser)
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, gist 14.0.0 OWL (downloaded and loaded)

## Completion Class

- Contract complete means: Explorer modes switch correctly, SPARQL queries return correct tree structures, tags are individual triples, favorites persist per-user, comments are stored and displayed with threading, ontology views render class/instance/property data, class creation generates valid OWL+SHACL
- Integration complete means: VFS mount specs drive both WebDAV file organization AND explorer object trees, gist classes appear in TBox alongside mental model classes, created classes are usable for object creation
- Operational complete means: All features work in Docker Compose stack with existing mental models installed

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User installs a mental model, creates objects, switches explorer to hierarchy mode and sees parent/child nesting
- User creates a VFS mount with by-tag strategy and sees the same organization in both the VFS browser and the explorer
- User opens the ontology viewer and sees their mental model classes descending from gist classes
- User creates a new class through the UI and creates an object of that type

## Risks and Unknowns

- **Gist 14.0.0 loading** — gist is ~100 classes/properties. Loading into RDF4J as a named graph and querying across it alongside mental model graphs needs SPARQL federation or cross-graph queries. Risk: query complexity.
- **VFS strategy reuse for explorer** — The VFS strategies module has SPARQL builders but they're designed for WebDAV collection responses, not htmx tree rendering. Risk: may need adaptation layer.
- **Class creation → SHACL shape generation** — Auto-generating valid SHACL shapes from a UI form is non-trivial. The shape must integrate with the existing form generation pipeline. Risk: edge cases in property constraints.
- **Mental model ↔ gist alignment** — Mapping existing mental model classes to gist hierarchy requires manual alignment. Risk: choosing wrong gist parent classes.
- **Comment threading in RDF** — RDF doesn't have native threading. Need to model reply-to relationships. Risk: query performance for deeply nested threads.

## Existing Codebase / Prior Art

- `backend/app/vfs/strategies.py` — 5 directory strategies (flat, by-type, by-date, by-tag, by-property) with SPARQL query builders. Reusable for explorer modes.
- `backend/app/vfs/mount_service.py` — MountDefinition dataclass, CRUD for mount specs in RDF. Lists user mounts.
- `backend/app/vfs/mount_collections.py` — Dispatches to strategy queries. Adapter layer between mounts and WebDAV collections.
- `backend/app/templates/browser/workspace.html` — Explorer pane with OBJECTS section (nav_tree.html include), VIEWS, MY VIEWS sections.
- `backend/app/templates/browser/nav_tree.html` — Current by-type tree: type nodes with lazy-loaded children via htmx.
- `backend/app/templates/browser/tree_children.html` — Leaf nodes for objects within a type group.
- `backend/app/templates/admin/model_detail.html` — Has TODO placeholders at lines ~203 and ~233 for stats and charts.
- `backend/app/templates/admin/model_ontology_diagram.html` — Cytoscape.js graph of model relationships. Reference for ontology rendering.
- `backend/app/services/models.py` — ModelService with `get_model_detail()`. Admin data source.
- `backend/app/obsidian/executor.py` — Lines 181-205: tag extraction from Obsidian imports. Tags stored as individual `schema:keywords` triples via `_resolve_predicate("schema:keywords")`.
- `models/basic-pkm/manifest.yaml` — Model manifest structure with icons, entrypoints, entailment config.
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL class definitions for basic-pkm model. Reference for class structure.
- `.planning/ontology-viewer-research.md` — Full research on ontology tools, gist fit, TBox/ABox/RBox strategy.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- EXP-01 through EXP-05 — Explorer mode infrastructure and VFS integration
- TAG-01 through TAG-03 — Tag parsing fix and tag explorer
- FAV-01, FAV-02 — Per-user favorites
- CMT-01, CMT-02 — Threaded comments
- ONTO-01 through ONTO-03 — Ontology viewer (TBox/ABox/RBox)
- GIST-01, GIST-02 — Gist foundation ontology
- TYPE-01, TYPE-02 — In-app class creation
- ADMIN-01, ADMIN-02 — Model detail stats and charts

## Scope

### In Scope

- Explorer mode dropdown replacing OBJECTS section content
- By-type mode (current behavior preserved as default)
- By-hierarchy mode (dcterms:isPartOf, arbitrary depth, lazy expand)
- VFS mount specs as explorer modes (reusing strategy SPARQL)
- Tag parsing fix (comma-separated → individual triples)
- Tag pill rendering with # prefix
- By-tag explorer mode
- Per-user favorites (SQL storage, star button, FAVORITES section)
- Threaded collaborative comments (RDF storage, comment panel)
- TBox Explorer (unified class hierarchy across models + gist)
- ABox Browser (instances by type with counts)
- RBox Legend (property reference with domains/ranges)
- Gist 14.0.0 loaded as foundation ontology
- Mental model classes aligned to gist hierarchy
- In-app class creation (name, icon, parent class, basic properties → OWL + SHACL)
- Admin model detail stats (avg connections, last modified, growth trend)
- Admin model detail charts (sparkline, link distribution)

### Out of Scope / Non-Goals

- Full SHACL shape editor with advanced constraints (TYPE-03 — later milestone)
- Mental model export/packaging from user-created types (TYPE-04 — later milestone)
- Automatic gist alignment suggestions via LLM
- Ontology editing of installed models (read-only for model-provided classes)
- Property hierarchy editing
- Real-time collaborative comment editing

## Technical Constraints

- Frontend: htmx + vanilla JS — no React. All new views follow htmx partial rendering pattern.
- Charting: lightweight library compatible with htmx (Chart.js or similar, agent's discretion)
- Gist: pin to 14.0.0, load as named graph, CC BY 4.0 attribution required
- Comments: RDF storage in triplestore (not SQL) — stays in the knowledge graph
- Favorites: SQL storage per-user (like auth/sessions) — not RDF, because this is user preference not knowledge
- Class creation: must generate OWL class triples + SHACL NodeShape that integrates with existing form generation pipeline

## Integration Points

- **RDF4J triplestore** — gist loaded as named graph; class hierarchy queries span gist + model graphs + current graph
- **VFS strategies module** — SPARQL builders reused for explorer modes, adapted for htmx tree rendering
- **MountService** — list user mounts to populate explorer dropdown
- **ShapesService** — created classes must produce shapes that ShapesService can discover for form generation
- **IconService** — created classes need icon metadata
- **EventStore** — comments stored via event-sourced writes (comment.create, comment.reply operations)
- **LabelService** — all new tree nodes need label resolution

## Open Questions

- **Comment operations** — Should comments go through the existing Command API (new operation types) or a separate comment API? Current thinking: new operations (comment.create, comment.reply, comment.delete) through EventStore for consistency and auditability.
- **Gist graph name** — `urn:sempkm:gist` or `urn:gist:core`? Current thinking: `urn:sempkm:ontology:gist` to namespace under sempkm.
- **Class creation graph** — Where do user-created classes live? Current thinking: `urn:sempkm:user-types` named graph, separate from model graphs.
- **Tag migration** — Should we write a one-time migration to split existing comma-separated tag literals? Current thinking: yes, as part of the tag fix slice.
