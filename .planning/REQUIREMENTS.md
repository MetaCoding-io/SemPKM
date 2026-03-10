# Requirements: SemPKM v2.6

**Defined:** 2026-03-09
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.6 Requirements

Requirements for v2.6 Power User & Collaboration. Each maps to roadmap phases.

### SPARQL Interface

- [x] **SPARQL-01**: SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs
- [x] **SPARQL-02**: User's SPARQL query history is persisted server-side and accessible across devices
- [x] **SPARQL-03**: User can save a SPARQL query with a name and description
- [x] **SPARQL-04**: User can share a saved query with other users (read-only)
- [x] **SPARQL-05**: SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs
- [x] **SPARQL-06**: SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models
- [x] **SPARQL-07**: User can promote a saved query to a named view browsable in the nav tree
- [ ] **SPARQL-08**: Ensure user cannot modify the graph via SPARQL, as we still want all writes to go thru the Command API

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

- [x] **VFS-01**: MountSpec RDF vocabulary defines declarative directory structures
- [x] **VFS-02**: User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat)
- [x] **VFS-03**: VFS provider dispatches to the correct strategy based on mount path prefix
- [x] **VFS-04**: Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes
- [x] **VFS-05**: Mount management UI in Settings for creating, editing, and deleting mounts

### VFS Browser UX

- [x] **VFSX-01**: VFS browser shows side-by-side view for open files with raw content and rendered markdown preview
- [x] **VFSX-02**: VFS browser file operations are polished (consistent icons, loading states)
- [x] **VFSX-03**: VFS browser has inline help about connecting the user's OS to the WebDAV endpoint

### Object Browser UI

- [x] **OBUI-01**: Nav tree header has a refresh button to reload the object list
- [x] **OBUI-02**: Nav tree header has a plus button to jump to the create new object flow
- [x] **OBUI-03**: User can select multiple objects via shift-click in the nav tree
- [x] **OBUI-04**: User can bulk delete selected objects
- [x] **OBUI-05**: Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type

### Bug Fixes

- [x] **FIX-01**: Event log diffs render correctly for all operation types
- [x] **FIX-02**: Lint dashboard controls display at correct width on all viewports

### Spatial Canvas

- [x] **CANV-01**: Spatial canvas has snap-to-grid alignment
- [x] **CANV-02**: Spatial canvas shows edge labels between connected nodes
- [x] **CANV-03**: Spatial canvas has keyboard navigation support
- [x] **CANV-04**: User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk. Wait for **OBUI-03** to be implemented
- [x] **CANV-05**: Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas, with a different color than rdf links

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
| Complex per-graph SPARQL ACLs | Simple 3-role gating is sufficient for self-hosted PKM |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPARQL-01 | Phase 52 | Complete |
| SPARQL-02 | Phase 53 | Complete |
| SPARQL-03 | Phase 53 | Complete |
| SPARQL-04 | Phase 54 | Complete |
| SPARQL-05 | Phase 53 | Complete |
| SPARQL-06 | Phase 53 | Complete |
| SPARQL-07 | Phase 54 | Complete |
| SPARQL-08 | Phase 54 | Pending |
| FED-01 | Phase 58 | Pending |
| FED-02 | Phase 58 | Pending |
| FED-03 | Phase 58 | Pending |
| FED-04 | Phase 58 | Pending |
| FED-05 | Phase 58 | Pending |
| FED-06 | Phase 58 | Pending |
| FED-07 | Phase 58 | Pending |
| FED-08 | Phase 58 | Pending |
| FED-09 | Phase 58 | Pending |
| FED-10 | Phase 58 | Pending |
| VFS-01 | Phase 56 | Complete |
| VFS-02 | Phase 56 | Complete |
| VFS-03 | Phase 56 | Complete |
| VFS-04 | Phase 56 | Complete |
| VFS-05 | Phase 56 | Complete |
| VFSX-01 | Phase 55 | Complete |
| VFSX-02 | Phase 55 | Complete |
| VFSX-03 | Phase 55 | Complete |
| OBUI-01 | Phase 55 | Complete |
| OBUI-02 | Phase 55 | Complete |
| OBUI-03 | Phase 55 | Complete |
| OBUI-04 | Phase 55 | Complete |
| OBUI-05 | Phase 55 | Complete |
| FIX-01 | Phase 52 | Complete |
| FIX-02 | Phase 52 | Complete |
| CANV-01 | Phase 57 | Complete |
| CANV-02 | Phase 57 | Complete |
| CANV-03 | Phase 57 | Complete |
| CANV-04 | Phase 57 | Complete |
| CANV-05 | Phase 57 | Complete |

**Coverage:**
- v2.6 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-10 — added VFSX-03 (WebDAV inline help), traceability updated*
