# M003: Workspace UX & Knowledge Organization

**Vision:** Transform SemPKM's flat object explorer into a multi-mode knowledge navigator — users switch between type, hierarchy, tag, and VFS-driven views. The ontology becomes visible and editable. Objects gain comments, favorites, and proper tag handling. Admin gets real analytics.

## Success Criteria

- Explorer dropdown switches between at least 4 organization modes and each renders correct object trees
- Objects display parent/child hierarchy via dcterms:isPartOf with lazy-expanding arbitrary depth
- VFS mount specs appear as selectable explorer modes showing full rich objects (not flat files)
- Tags stored as individual triples, displayed as #-prefixed pills, browsable via tag explorer mode
- Per-user favorites section in explorer shows starred objects
- Threaded comments on any object with author attribution, visible to all users
- Ontology viewer shows TBox class hierarchy (gist + mental models), ABox instances by type, RBox property reference
- User can create a new class with name, icon, parent, and properties — then create objects of that type
- Admin model detail shows real computed stats and visual charts

## Key Risks / Unknowns

- Gist 14.0.0 loading and cross-graph class hierarchy queries — query complexity across named graphs
- VFS strategy SPARQL reuse for explorer tree rendering — adaptation gap between WebDAV collections and htmx trees
- Class creation → valid SHACL shape generation — must integrate with existing form generation pipeline
- Comment threading model in RDF — query performance for nested threads

## Proof Strategy

- Gist cross-graph queries → retire in S07 by proving unified class hierarchy renders across gist + model graphs
- VFS strategy reuse → retire in S03 by proving mount specs drive explorer trees with full objects
- SHACL generation from UI → retire in S08 by proving created class produces working forms via ShapesService
- Comment threading → retire in S06 by proving threaded comments render with 3+ nesting levels

## Verification Classes

- Contract verification: pytest unit tests for SPARQL queries, tag parsing, comment operations; Playwright E2E for explorer modes, favorites, comments, ontology views
- Integration verification: VFS mount spec drives both WebDAV and explorer; gist + models render in unified hierarchy; created classes usable for object creation
- Operational verification: all features work in Docker Compose stack with existing mental models
- UAT / human verification: ontology hierarchy correctness requires human judgment on gist alignment

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 9 slice deliverables are complete and verified
- Explorer mode dropdown works with by-type, by-hierarchy, by-tag, and at least one VFS mount mode
- VFS strategies drive both WebDAV file access and explorer object trees
- Gist 14.0.0 is loaded and visible in TBox hierarchy alongside mental model classes
- User can create a class through the UI and create objects of that type with auto-generated forms
- Tags, favorites, and comments all persist across sessions
- Admin model detail shows real computed stats and charts (not placeholders)
- Success criteria re-checked against live Docker Compose stack
- E2E tests cover all new user-visible features
- User guide docs updated for all new features

## Requirement Coverage

- Covers: EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, TAG-01, TAG-02, TAG-03, FAV-01, FAV-02, CMT-01, CMT-02, ONTO-01, ONTO-02, ONTO-03, GIST-01, GIST-02, TYPE-01, TYPE-02, ADMIN-01, ADMIN-02
- Partially covers: none
- Leaves for later: TYPE-03 (full shape editor), TYPE-04 (model export), MCP-01, NOTION-01
- Orphan risks: none

## Slices

- [x] **S01: Explorer Mode Infrastructure** `risk:medium` `depends:[]`
  > After this: Explorer has a working dropdown that switches between "By Type" (current behavior) and placeholder modes — the tree re-renders via htmx on mode change.

- [x] **S02: Hierarchy Explorer Mode** `risk:medium` `depends:[S01]`
  > After this: User switches to "By Hierarchy" mode and sees objects nested by dcterms:isPartOf with lazy-expanding arbitrary depth. Root objects (no parent) appear at top level.

- [x] **S03: VFS-Driven Explorer Modes** `risk:medium` `depends:[S01]`
  > After this: Each user-created VFS mount appears as a selectable explorer mode. Objects are organized by the mount's directory strategy (by-date, by-tag, by-property, flat) and clicking opens the full object tab — not a flat file.

- [x] **S04: Tag System Fix & Tag Explorer** `risk:medium` `depends:[S01]`
  > After this: Comma-separated schema:keywords values are split into individual triples. Tags render as #-prefixed pills in object views. "By Tag" mode in the explorer groups objects by tag with counts.

- [x] **S05: Favorites System** `risk:low` `depends:[S01]`
  > After this: Star button on objects toggles per-user favorites. FAVORITES collapsible section in explorer shows all starred objects with quick navigation.

- [x] **S06: Threaded Object Comments** `risk:medium` `depends:[]`
  > After this: Users can add comments on any object. Comments are threaded (reply-to nesting), show author and timestamp, and are visible to all users on the instance.

- [x] **S07: Ontology Viewer & Gist Foundation** `risk:high` `depends:[]`
  > After this: Workspace has an ontology viewer with TBox Explorer (class hierarchy across gist + all models), ABox Browser (instances by type with counts), and RBox Legend (property domains/ranges). Gist 14.0.0 is loaded and fully visible in the hierarchy.

- [x] **S08: In-App Class Creation** `risk:high` `depends:[S07]`
  > After this: User creates a new class via form (name, icon, parent class, properties with datatypes). The class appears in the ontology viewer, and objects of that type can be created with auto-generated SHACL forms.

- [x] **S09: Admin Model Detail Stats & Charts** `risk:low` `depends:[]`
  > After this: Admin model detail page shows real computed stats (avg connections, last modified, growth trend) and visual charts (activity sparkline, link distribution) replacing the TODO placeholders.

- [x] **S10: E2E Test Coverage Gaps** `risk:low` `depends:[]`
  > After this: All shipped features have Playwright e2e test coverage — object/edge deletion, edge.patch, event undo, spatial canvas, bottom-panel SPARQL, admin model install/uninstall, rate limiting, LLM config, federation UI, SPARQL advanced features, pagination, tooltips, edge provenance, markdown rendering, health check, column preferences, sidebar panel drag-drop, graph node interaction, and all 27 existing canvas stubs are implemented.

## Boundary Map

### S01 → S02, S03, S04, S05

Produces:
- Explorer mode dropdown UI component with mode switching via htmx
- `/browser/explorer/tree?mode={mode}` endpoint pattern returning mode-specific tree HTML
- `explorer_modes` registry (Python dict/enum mapping mode IDs to handler functions)
- htmx swap target `#explorer-tree-body` for mode content replacement
- By-type mode handler (refactored current nav_tree logic)

Consumes:
- nothing (first slice in explorer chain)

### S02 → (terminal)

Produces:
- `hierarchy` mode handler registered in explorer_modes
- `/browser/explorer/tree?mode=hierarchy` returning isPartOf-organized tree
- `/browser/explorer/children?parent={iri}` for lazy child expansion
- SPARQL queries for root objects (no isPartOf parent) and children of a given parent

Consumes from S01:
- Explorer mode dropdown and `#explorer-tree-body` swap target
- Mode handler registration pattern

### S03 → (terminal)

Produces:
- Dynamic `mount:{mount_id}` mode entries in explorer dropdown (one per VFS mount)
- `/browser/explorer/tree?mode=mount&mount_id={id}` returning mount-strategy-organized tree
- Adapter layer bridging VFS strategy SPARQL builders to htmx tree rendering
- Full object click-through (same as by-type tree leaf behavior)

Consumes from S01:
- Explorer mode dropdown and mode handler registration
- Dynamic mode injection into dropdown

### S04 → (terminal)

Produces:
- Tag parsing middleware: comma-separated → individual triples on property save
- One-time migration script for existing comma-separated tag data
- Tag pill CSS component with # prefix
- `by-tag` mode handler in explorer with tag folders showing object counts
- `/browser/explorer/tree?mode=by-tag` returning tag-grouped tree

Consumes from S01:
- Explorer mode dropdown and mode handler registration

### S05 → (terminal)

Produces:
- `user_favorites` SQL table (user_id, object_iri, created_at)
- `/browser/favorites/toggle` endpoint (POST, returns updated star state)
- Star button component on object views
- FAVORITES collapsible section in explorer pane (separate from OBJECTS section)
- `/browser/favorites/list` endpoint returning favorited objects as tree HTML

Consumes from S01:
- Explorer pane structure (adds new section below OBJECTS)

### S06 → (terminal)

Produces:
- Comment RDF vocabulary: `sempkm:Comment` type, `sempkm:commentBody`, `sempkm:commentOn`, `sempkm:replyTo`, `sempkm:commentedBy`, `sempkm:commentedAt`
- EventStore operations: `comment.create`, `comment.reply`, `comment.delete`
- `/browser/object/{iri}/comments` endpoint (GET comments, POST new comment)
- Comment panel UI in object view (threaded display, reply form, timestamps, author badges)
- SPARQL queries for threaded comment retrieval (recursive reply chains)

Consumes:
- nothing (independent of explorer chain)

### S07 → S08

Produces:
- Gist 14.0.0 loaded in `urn:sempkm:ontology:gist` named graph
- Mental model → gist `rdfs:subClassOf` alignment triples
- Ontology viewer workspace view (new dockview panel type or sidebar view)
- TBox Explorer: collapsible class hierarchy tree via htmx (gist → model classes)
- ABox Browser: instance list grouped by type with counts
- RBox Legend: property table with domain, range, characteristics
- `/browser/ontology/tbox` endpoint returning class hierarchy HTML
- `/browser/ontology/abox?class={iri}` endpoint returning instances
- `/browser/ontology/rbox` endpoint returning property reference HTML
- SPARQL queries for cross-graph class hierarchy (spanning gist + model + user-type graphs)

Consumes:
- nothing (independent of explorer chain)

### S08 → (terminal)

Produces:
- Class creation form UI (name, icon picker, parent class selector, property editor)
- `/browser/ontology/create-class` endpoint (POST, creates OWL class + SHACL shape)
- OWL class triple generation (rdfs:Class, rdfs:subClassOf, rdfs:label, icon metadata)
- SHACL NodeShape generation (sh:targetClass, sh:property for each field)
- User-created types stored in `urn:sempkm:user-types` named graph
- Created classes discoverable by ShapesService for form generation
- Created classes appear in type picker and ontology viewer

Consumes from S07:
- Ontology viewer for browsing/selecting parent classes
- TBox hierarchy data for parent class picker
- Gist + model class IRIs for subClassOf targets

### S09 → (terminal)

Produces:
- SPARQL aggregate queries for avg connections, last modified, growth trend per model
- Chart.js (or similar) integration for sparkline and link distribution charts
- Updated `get_model_detail()` returning computed stats
- Replaced TODO placeholders in `model_detail.html` with real data and charts

Consumes:
- nothing (independent)

### S10 → (terminal)

Produces:
- ~20 new e2e spec files filling all identified coverage gaps
- Implemented tests replacing all 27 `test.skip()` stubs in 17-spatial-canvas
- Complete e2e coverage map: every shipped backend route and UI feature has at least one e2e test

Consumes:
- nothing (independent, test-only — no production code changes)
