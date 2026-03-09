# Requirements: SemPKM v2.6

**Defined:** 2026-03-09
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.6 Requirements

Requirements for v2.6 Power User & Collaboration. Each maps to roadmap phases.

### SPARQL Interface

- [ ] **SPARQL-01**: SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs
- [ ] **SPARQL-02**: User's SPARQL query history is persisted server-side and accessible across devices
- [ ] **SPARQL-03**: User can save a SPARQL query with a name and description
- [ ] **SPARQL-04**: User can share a saved query with other users (read-only)
- [ ] **SPARQL-05**: SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs
- [ ] **SPARQL-06**: SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models
- [ ] **SPARQL-07**: User can promote a saved query to a named view browsable in the nav tree

### Collaboration & Federation

- [ ] **FED-01**: Events can be serialized as RDF Patch format (A/D operations)
- [ ] **FED-02**: API endpoint exports event patches since a given sequence number
- [ ] **FED-03**: User can register a remote SemPKM instance for sync
- [ ] **FED-04**: Named graph sync pulls patches from remote instance and applies via EventStore
- [ ] **FED-05**: Sync prevents infinite loops via syncSource tagging on federation-originated events
- [ ] **FED-06**: Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles
- [ ] **FED-07**: User can send a notification (e.g. shared concept) to a remote instance's LDN inbox
- [ ] **FED-08**: User can view and act on received LDN notifications in the workspace
- [ ] **FED-09**: Incoming federation requests are authenticated via HTTP Signatures against WebID public keys
- [ ] **FED-10**: Collaboration UI shows registered remote instances, sync status, and incoming changes

### User Custom VFS (MountSpec)

- [ ] **VFS-01**: MountSpec RDF vocabulary defines declarative directory structures
- [ ] **VFS-02**: User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat)
- [ ] **VFS-03**: VFS provider dispatches to the correct strategy based on mount path prefix
- [ ] **VFS-04**: Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes
- [ ] **VFS-05**: Mount management UI in Settings for creating, editing, and deleting mounts

### VFS Browser UX

- [ ] **VFSX-01**: VFS browser shows clickable breadcrumb path navigation
- [ ] **VFSX-02**: VFS browser shows side-by-side view for open files with raw content and rendered markdown preview
- [ ] **VFSX-03**: VFS browser file operations are polished (consistent icons, loading states)

### Object Browser UI

- [ ] **OBUI-01**: Nav tree header has a refresh button to reload the object list
- [ ] **OBUI-02**: Nav tree header has a plus button to jump to the create new object flow
- [ ] **OBUI-03**: User can select multiple objects via shift-click in the nav tree
- [ ] **OBUI-04**: User can bulk delete selected objects
- [ ] **OBUI-05**: Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type

### Bug Fixes

- [ ] **FIX-01**: Event log diffs render correctly for all operation types
- [ ] **FIX-02**: Lint dashboard controls display at correct width on all viewports

### Spatial Canvas

- [ ] **CANV-01**: Spatial canvas has snap-to-grid alignment
- [ ] **CANV-02**: Spatial canvas shows edge labels between connected nodes
- [ ] **CANV-03**: Spatial canvas has keyboard navigation support
- [ ] **CANV-04**: User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk
- [ ] **CANV-05**: Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Collaboration (deferred)

- **FED-11**: Real-time collaborative editing via CRDT (build when ecosystem ready)

### VFS (deferred)

- **VFS-06**: Bidirectional VFS sync with conflict resolution

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| SPARQL UPDATE as write surface | Bypasses event sourcing — all writes must go through Command API |
| Full ActivityPub federation | AP is designed for social media; LDN is simpler and sufficient |
| Full SOLID pod compatibility | WAC and container model are extensive; WebID + LDN is sufficient |
| Custom SPARQL UI replacing Yasgui | Extend Yasgui with plugins rather than replacing it |
| Complex per-graph SPARQL ACLs | Simple 3-role gating is sufficient for self-hosted PKM |
| Real-time collaborative editing | CRDT for RDF triples is unsolved; async collaboration first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPARQL-01 | — | Pending |
| SPARQL-02 | — | Pending |
| SPARQL-03 | — | Pending |
| SPARQL-04 | — | Pending |
| SPARQL-05 | — | Pending |
| SPARQL-06 | — | Pending |
| SPARQL-07 | — | Pending |
| FED-01 | — | Pending |
| FED-02 | — | Pending |
| FED-03 | — | Pending |
| FED-04 | — | Pending |
| FED-05 | — | Pending |
| FED-06 | — | Pending |
| FED-07 | — | Pending |
| FED-08 | — | Pending |
| FED-09 | — | Pending |
| FED-10 | — | Pending |
| VFS-01 | — | Pending |
| VFS-02 | — | Pending |
| VFS-03 | — | Pending |
| VFS-04 | — | Pending |
| VFS-05 | — | Pending |
| VFSX-01 | — | Pending |
| VFSX-02 | — | Pending |
| VFSX-03 | — | Pending |
| OBUI-01 | — | Pending |
| OBUI-02 | — | Pending |
| OBUI-03 | — | Pending |
| OBUI-04 | — | Pending |
| OBUI-05 | — | Pending |
| FIX-01 | — | Pending |
| FIX-02 | — | Pending |
| CANV-01 | — | Pending |
| CANV-02 | — | Pending |
| CANV-03 | — | Pending |
| CANV-04 | — | Pending |
| CANV-05 | — | Pending |

**Coverage:**
- v2.6 requirements: 37 total
- Mapped to phases: 0
- Unmapped: 37 ⚠️

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after initial definition*
