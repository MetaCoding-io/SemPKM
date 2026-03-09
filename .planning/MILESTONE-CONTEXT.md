# Milestone Context: v2.6

**Gathered:** 2026-03-09
**Previous milestone:** v2.5 Polish, Import & Identity (shipped 2026-03-09)

## Milestone Scope

One large milestone covering 8 feature areas:

### 1. SPARQL Interface (full sketch from roadmap)
- SPARQL permissions and policies (graph-scoped query execution per role)
- SPARQL autocomplete (prefix, class, property from ontologies/SHACL)
- IRI pills and editor enhancements (visual pill rendering, click-to-navigate)
- Server-side query history (searchable, filterable, cross-device)
- Saved queries and sharing (named, parameterized, publishable)
- Named queries as views (promote saved queries to object browser views)

### 2. Collaboration & Federation (full sketch from roadmap)
- RDF Patch change tracking (patch log, EventStore integration, replay)
- Named graph sync API (HTTP sync endpoints, conflict detection)
- Cross-instance notifications (LDN inbox, subscriptions, Webmention)
- Federated identity (WebID auth for incoming requests, named graph ACL)
- Collaboration UI (remote instances, sync status, incoming changes)
- Real-time collaboration (CRDT-based, build when ecosystem ready)

### 3. User Custom VFS (MountSpec)
- Declarative MountSpec vocabulary for user-created VFS views
- 5 directory strategies (flat, tag-groups, property-value, type-hierarchy, relationship-tree)
- SHACL-validated frontmatter writes
- Mount management UI

### 4. VFS Browser UX Polish
- Better navigation, preview pane, breadcrumbs
- File operations polish

### 5. Object Browser UI Improvements
- Refresh icon in left panel to reload objects
- Plus icon to jump to create new object flow
- Menu semantics: select, multi-select, contextual buttons (delete)
- Edge inspector panel (edge detail, inline wiki-link creation)
- View enhancements (better table/cards/graph filtering, sorting)

### 6. Event Log Fixes
- Missing diffs for certain event types
- Some events not rendering/showing up properly

### 7. Lint Dashboard Fixes
- Controls taking up 100% width (layout issue)
- Walkthrough-driven improvements (user needs to see it with data first)

### 8. Spatial Canvas UI Improvements
- Specific improvements TBD during discuss-phase/research

## Cleanup Done
- Removed "edit form helptext in SHACL types" todo (already implemented in basic-pkm and ppv models)
- Removed "Web Components for Models" from Potential Ideas in ROADMAP.md

## Notes
- Suggested version: v2.6
- This is a large milestone — expect 15-25+ phases
- SPARQL Interface and Collaboration have existing research in .planning/research/
- User Custom VFS has existing research in .planning/research/virtual-filesystem.md
