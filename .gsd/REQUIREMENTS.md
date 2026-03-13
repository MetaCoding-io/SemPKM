# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### EXP-01 — Explorer mode dropdown with switchable navigation strategies
- Class: core-capability
- Status: active
- Description: The OBJECTS section in the explorer pane has a dropdown that switches between different organizational modes. Selecting a mode re-renders the tree via htmx.
- Why it matters: Users need multiple ways to navigate knowledge — flat-by-type is insufficient for large collections.
- Source: user
- Primary owning slice: M003/S01
- Supporting slices: M003/S02, M003/S03, M003/S04
- Validation: unmapped
- Notes: Dropdown replaces OBJECTS section content in-place. Modes include by-type, by-hierarchy, by-tag, and VFS mounts.

### EXP-02 — By-type mode (current behavior) as default explorer mode
- Class: core-capability
- Status: active
- Description: The current by-type tree (type nodes with lazy-loaded object children) is preserved as the default explorer mode.
- Why it matters: Existing behavior must not regress when the mode system is added.
- Source: user
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Refactored from hardcoded into a mode handler.

### EXP-03 — Hierarchy mode via dcterms:isPartOf with arbitrary nesting depth
- Class: core-capability
- Status: active
- Description: Explorer hierarchy mode shows objects nested by dcterms:isPartOf parent/child relationships with lazy-expanding arbitrary depth.
- Why it matters: Hierarchical organization is a natural way to structure knowledge — flat type lists don't capture containment.
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: unmapped
- Notes: Root objects (no isPartOf parent) appear at top level. No hard depth limit.

### EXP-04 — VFS mount specs visible as explorer modes
- Class: core-capability
- Status: active
- Description: Each user-created VFS mount appears as a selectable mode in the explorer dropdown. Objects are organized by the mount's directory strategy.
- Why it matters: VFS specs are a powerful organizational vocabulary — they should drive the explorer, not just WebDAV file access.
- Source: user
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Reuses VFS strategy SPARQL builders adapted for htmx tree rendering.

### EXP-05 — VFS explorer shows full rich objects with same click-to-open behavior
- Class: core-capability
- Status: active
- Description: Clicking an object in a VFS-organized explorer mode opens the full object tab, same as clicking in the by-type view.
- Why it matters: The VFS spec changes organization, not behavior — users expect full object access regardless of navigation mode.
- Source: user
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Objects are rich (iri, label, type icon), not flat markdown filenames.

### TAG-01 — Tag parsing fix: comma-separated schema:keywords split into individual triples
- Class: core-capability
- Status: active
- Description: When schema:keywords values contain comma-separated lists, they are split into individual RDF triples on save. A one-time migration fixes existing data.
- Why it matters: Comma-separated tag strings can't be queried individually — they break tag-based filtering and navigation.
- Source: user
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: unmapped
- Notes: Affects seed data from base mental model. Obsidian import already splits correctly.

### TAG-02 — Tags render as pills with # prefix in object view and properties panel
- Class: core-capability
- Status: active
- Description: schema:keywords values display as styled pill components with a # prefix character.
- Why it matters: Tags should be visually distinct from other properties — pills with # are the standard PKM convention.
- Source: user
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: unmapped
- Notes: Each tag is a separate pill, not a comma-separated string.

### TAG-03 — Tag explorer mode in explorer dropdown
- Class: core-capability
- Status: active
- Description: Explorer has a "By Tag" mode that groups objects by their schema:keywords tags, with tag counts.
- Why it matters: Tags are a cross-cutting navigation axis orthogonal to types and hierarchy.
- Source: user
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: unmapped
- Notes: Builds on VFS by-tag strategy SPARQL.

### FAV-01 — Per-user favorites: star/unstar objects
- Class: core-capability
- Status: active
- Description: Users can toggle a star/favorite on any object. Favorites are per-user (stored in SQL, not RDF).
- Why it matters: Quick access to high-traffic objects without searching or navigating the tree.
- Source: user
- Primary owning slice: M003/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Star button visible on object views.

### FAV-02 — FAVORITES collapsible section in explorer pane
- Class: core-capability
- Status: active
- Description: A FAVORITES collapsible section in the explorer pane shows all starred objects for the current user.
- Why it matters: Favorites need a persistent, always-accessible surface in the workspace.
- Source: user
- Primary owning slice: M003/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Separate section from OBJECTS, not a mode in the dropdown.

### CMT-01 — Threaded collaborative comments on objects
- Class: core-capability
- Status: active
- Description: Users can add threaded comments on any object. Comments support reply-to nesting, are visible to all users, and stored in the RDF knowledge graph.
- Why it matters: Enables lightweight collaboration and annotation without editing the object itself.
- Source: user
- Primary owning slice: M003/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Stored via EventStore operations for consistency and auditability.

### CMT-02 — Comment panel in object view with author attribution and timestamps
- Class: core-capability
- Status: active
- Description: Object view includes a comment panel showing threaded comments with author names, timestamps, and reply actions.
- Why it matters: Comments need a usable UI surface with clear attribution.
- Source: user
- Primary owning slice: M003/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Threaded (reply-to nesting), not flat list.

### ONTO-01 — TBox Explorer: unified class hierarchy across all installed models
- Class: core-capability
- Status: active
- Description: Ontology viewer shows a TBox Explorer with the full class hierarchy spanning gist upper ontology and all installed mental models. Gist classes fully visible.
- Why it matters: Users can't currently see the schema landscape across installed mental models or understand how their data types relate.
- Source: user
- Primary owning slice: M003/S07
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/ontology-viewer-research.md`. Collapsible tree, gist classes on equal footing.

### ONTO-02 — ABox Browser: instances grouped by type with counts
- Class: core-capability
- Status: active
- Description: Ontology viewer includes an ABox Browser showing instances grouped by their RDF type with per-type counts.
- Why it matters: Users need to see what data they have and how it's distributed across types.
- Source: user
- Primary owning slice: M003/S07
- Supporting slices: none
- Validation: unmapped
- Notes: Clicking a class shows its instances. Navigation to object tabs.

### ONTO-03 — RBox Legend: property reference with domains, ranges, and characteristics
- Class: core-capability
- Status: active
- Description: Ontology viewer includes an RBox Legend showing all properties with their domains, ranges, and characteristics (transitive, symmetric, etc.).
- Why it matters: Users need to understand what relationships are available and how they connect types.
- Source: user
- Primary owning slice: M003/S07
- Supporting slices: none
- Validation: unmapped
- Notes: Grouped by object properties vs datatype properties.

### GIST-01 — Gist 14.0.0 loaded as foundation ontology in named graph
- Class: core-capability
- Status: active
- Description: Gist 14.0.0 OWL ontology loaded into RDF4J as a named graph, queryable via SPARQL.
- Why it matters: Provides a shared conceptual backbone so classes from different mental models have meaningful common ancestors.
- Source: user
- Primary owning slice: M003/S07
- Supporting slices: M003/S08
- Validation: unmapped
- Notes: Pin to 14.0.0, update deliberately. CC BY 4.0 license. Namespace: `https://w3id.org/semanticarts/ns/ontology/gist/`.

### GIST-02 — Mental model classes aligned to gist hierarchy
- Class: core-capability
- Status: active
- Description: Mental model classes have rdfs:subClassOf relationships to appropriate gist classes (e.g. bpkm:Note rdfs:subClassOf gist:IntellectualProperty).
- Why it matters: Without alignment, gist is just another isolated ontology. Alignment enables cross-model hierarchy browsing.
- Source: user
- Primary owning slice: M003/S07
- Supporting slices: none
- Validation: unmapped
- Notes: Manual alignment for existing models. Future models can declare alignment in their ontology.

### TYPE-01 — In-app class creation: name, icon, parent class, basic properties
- Class: core-capability
- Status: active
- Description: Users can create a new RDF class through a form UI — specifying name, icon, parent class (from ontology), and properties with datatypes.
- Why it matters: Users should be able to extend their knowledge schema without editing model packages or writing OWL by hand.
- Source: user
- Primary owning slice: M003/S08
- Supporting slices: none
- Validation: unmapped
- Notes: Created classes stored in `urn:sempkm:user-types` named graph.

### TYPE-02 — Created classes generate valid OWL class + SHACL shape
- Class: core-capability
- Status: active
- Description: When a user creates a class, the system generates OWL class triples and a SHACL NodeShape that integrates with the existing form generation pipeline.
- Why it matters: Created types must be first-class citizens — usable for object creation with auto-generated forms.
- Source: user
- Primary owning slice: M003/S08
- Supporting slices: none
- Validation: unmapped
- Notes: Must be discoverable by ShapesService. Must appear in type picker for object creation.

### ADMIN-01 — Model detail page stats: avg connections, last modified, growth trend
- Class: admin/support
- Status: active
- Description: Admin model detail page shows computed stats replacing the TODO placeholders: average connections per node, last modified date, growth trend.
- Why it matters: Gives model administrators insight into knowledge graph health and activity.
- Source: execution (code TODO)
- Primary owning slice: M003/S09
- Supporting slices: none
- Validation: unmapped
- Notes: TODO comment in model_detail.html:~203.

### ADMIN-02 — Model detail page charts: sparkline, activity, link distribution
- Class: admin/support
- Status: active
- Description: Admin model detail page shows visual charts replacing the placeholder bars: activity sparkline, link distribution visualization.
- Why it matters: Visual analytics for model health monitoring.
- Source: execution (code TODO)
- Primary owning slice: M003/S09
- Supporting slices: none
- Validation: unmapped
- Notes: TODO comment in model_detail.html:~233. Lightweight chart library (agent's choice).

## Validated

### SEC-01 — Auth endpoints have per-IP rate limiting
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

slowapi rate limiting: 5/min on magic-link, 10/min on verify. HTTP 429 after limit exceeded.

### SEC-02 — Magic link token not logged when SMTP is configured
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

Token logging conditional on SMTP not configured or SMTP delivery failure fallback.

### SEC-03 — Event console requires owner role
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

require_role("owner") on event_console_page in debug/router.py.

### SEC-04 — SPARQL filter text properly escaped against regex injection
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

escape_sparql_regex() in sparql/utils.py escapes 14 metacharacters. 19 unit tests.

### SEC-05 — base_namespace deployment documented with production guidance
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

Namespace Configuration section in docs/guide/20-production-deployment.md.

### COR-01 — Validation report IRI uses stable hash
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

hashlib.sha256 in validation/report.py replaces non-deterministic hash().

### COR-02 — scope_to_current_graph handles FROM/GRAPH in string literals
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

_strip_sparql_strings() preprocessor removes string literals before keyword detection. 6 unit tests.

### COR-03 — source_model attributed correctly with multiple models installed
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

GRAPH ?g with VALUES clause constraining graph IRIs for per-spec model attribution.

### TEST-01 — Backend pytest infrastructure exists with conftest and fixtures
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

backend/tests/conftest.py with fixtures; 130 tests in <3s.

### TEST-02 — SPARQL serialization/escaping has unit tests
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

test_rdf_serialization.py and test_sparql_utils.py cover serialization, escaping, and scoping edge cases.

### TEST-03 — IRI validation has unit tests
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S03

test_iri_validation.py covers valid IRIs, invalid IRIs, injection chars, and edge cases.

### TEST-04 — Auth token logic has unit tests
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

test_auth_tokens.py covers creation, verification, expiry (max_age_seconds=0), setup token lifecycle.

### REF-01 — Browser router split into domain sub-routers with zero behavior change
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S04

8 sub-modules, 33 routes preserved, route audit matches pre-refactor count.

### DEP-01 — pyproject.toml dependency versions pinned
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

All 24 dependencies use ~= compatible release pins.

### DEP-02 — uv.lock committed to source control
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

uv.lock exists and committed.

### PERF-01 — Event detail user lookup batched
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

Single WHERE IN query via resolve_user_names() replaces N+1 loop.

### FED-11 — Sync Now button auto-discovers remote URL from shared graph metadata
- Status: validated
- Class: core-capability
- Source: execution (Phase 58 verification gap)
- Primary Slice: M002/S06

discover_remote_instance_url() auto-resolves from federation graph metadata.

### FED-12 — Federation dual-instance docker-compose for E2E testing
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S06

docker-compose.federation-test.yml with two complete instances (ports 3911/3912).

### FED-13 — Federation E2E test covers invite → accept → sync flow
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S06

8-step Playwright E2E test in federation-sync.spec.ts passes in ~2s.

### OBSI-08 — Ideaverse Pro 2.5 vault imports successfully
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

895 objects created, 1767 edges, 29.9s import time from Ideaverse Pro 2.5 ZIP.

### OBSI-09 — Wiki-links in imported notes resolve to edges between objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

1767 dcterms:references edges from wiki-link resolution. Verified in Relations panel.

### OBSI-10 — Frontmatter from imported notes maps to RDF properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

Mapped keys (created, source, title, noteType) visible as RDF properties in workspace UI.

### SPARQL-01 — SPARQL queries are gated by role
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs.

### SPARQL-02 — User's SPARQL query history is persisted server-side
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User's SPARQL query history is persisted server-side and accessible across devices.

### SPARQL-03 — User can save a SPARQL query with a name and description
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User can save a SPARQL query with a name and description.

### SPARQL-04 — User can share a saved query with other users
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can share a saved query with other users (read-only).

### SPARQL-05 — SPARQL result IRIs display as labeled pills
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs.

### SPARQL-06 — SPARQL editor provides ontology-aware autocomplete
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models.

### SPARQL-07 — User can promote a saved query to a named view
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can promote a saved query to a named view browsable in the nav tree.

### SPARQL-08 — SPARQL is read-only (no graph modification)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

User cannot modify the graph via SPARQL — all writes go through the Command API.

### FED-01 — Events serialized as RDF Patch format
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Events can be serialized as RDF Patch format (A/D operations).

### FED-02 — API endpoint exports event patches since sequence number
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

API endpoint exports event patches since a given sequence number.

### FED-03 — User can register a remote SemPKM instance for sync
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can register a remote SemPKM instance for sync.

### FED-04 — Named graph sync pulls patches from remote
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Named graph sync pulls patches from remote instance and applies via EventStore.

### FED-05 — Sync prevents infinite loops via syncSource tagging
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Sync prevents infinite loops via syncSource tagging on federation-originated events.

### FED-06 — Server exposes LDN inbox endpoint
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles.

### FED-07 — User can send notification to remote LDN inbox
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can send a notification (e.g. shared concept) to a remote instance's LDN inbox.

### FED-08 — User can view and act on received LDN notifications
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can view and act on received LDN notifications in the workspace.

### FED-09 — Incoming federation requests authenticated via HTTP Signatures
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Incoming federation requests are authenticated via HTTP Signatures against WebID public keys.

### FED-10 — Collaboration UI shows sync status
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Collaboration UI shows registered remote instances, sync status, and incoming changes.

### VFS-01 — MountSpec RDF vocabulary defines declarative directory structures
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

MountSpec RDF vocabulary defines declarative directory structures.

### VFS-02 — User can create a mount with 5 directory strategies
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat).

### VFS-03 — VFS provider dispatches to correct strategy
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

VFS provider dispatches to the correct strategy based on mount path prefix.

### VFS-04 — YAML frontmatter edits map back to RDF via SHACL
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes.

### VFS-05 — Mount management UI in Settings
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Mount management UI in Settings for creating, editing, and deleting mounts.

### VFSX-01 — VFS browser side-by-side view
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser shows side-by-side view for open files with raw content and rendered markdown preview.

### VFSX-02 — VFS browser polished file operations
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser file operations are polished (consistent icons, loading states).

### VFSX-03 — VFS browser inline help
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser has inline help about connecting the user's OS to the WebDAV endpoint.

### OBUI-01 — Nav tree refresh button
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a refresh button to reload the object list.

### OBUI-02 — Nav tree plus button
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a plus button to jump to the create new object flow.

### OBUI-03 — Multi-select via shift-click in nav tree
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can select multiple objects via shift-click in the nav tree.

### OBUI-04 — Bulk delete selected objects
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can bulk delete selected objects.

### OBUI-05 — Relationship edge inspector
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type.

### FIX-01 — Event log diffs render correctly
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Event log diffs render correctly for all operation types.

### FIX-02 — Lint dashboard controls at correct width
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Lint dashboard controls display at correct width on all viewports.

### CANV-01 — Spatial canvas snap-to-grid
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has snap-to-grid alignment.

### CANV-02 — Spatial canvas edge labels
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas shows edge labels between connected nodes.

### CANV-03 — Spatial canvas keyboard navigation
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has keyboard navigation support.

### CANV-04 — Bulk drag-drop to canvas
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk.

### CANV-05 — Wiki-link edges on canvas
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas, with a different color than RDF links.

## Deferred

### TYPE-03 — Full SHACL shape editor with advanced constraints
- Class: core-capability
- Status: deferred
- Description: UI for editing SHACL shapes with advanced constraints — cardinality, patterns, value ranges, conditional shapes.
- Why it matters: Power users and model authors need fine-grained control over data validation rules.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Builds on TYPE-01/TYPE-02 class creation. Later milestone.

### TYPE-04 — Mental model export from user-created types
- Class: core-capability
- Status: deferred
- Description: Package user-created types, shapes, and views into a .sempkm-model archive for sharing.
- Why it matters: Users who create custom types should be able to share their mental models with others.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Depends on TYPE-01/TYPE-02. Later milestone.

### MCP-01 — MCP server for AI agent access to SemPKM
- Class: core-capability
- Status: deferred
- Description: MCP server exposing object browse/search, SPARQL query, graph traversal, and write operations to AI agents.
- Why it matters: Enables AI models to directly interact with the knowledge base via standardized tool-use protocol.
- Source: user (pending todo)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Future milestone. See .planning/todos/pending/2026-03-10-build-mcp-server-for-ai-agent-access-to-sempkm.md for full spec.

### NOTION-01 — Notion workspace import wizard
- Class: core-capability
- Status: deferred
- Description: Interactive import flow for Notion workspace exports (ZIP first, API later). Databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation.
- Why it matters: Notion is the most common PKM tool users migrate from. Structured import preserves their knowledge graph.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/notion-import-research.md`. Mirrors Obsidian wizard pattern.

## Out of Scope

### FED-CRDT — CRDT-based real-time sync
- Class: core-capability
- Status: out-of-scope
- Description: Replace last-write-wins conflict resolution with CRDT-based real-time sync.
- Why it matters: No production Python CRDT-for-RDF library exists yet (NextGraph alpha, W3C CG standardizing).
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Data model designed to accommodate CRDT replacement later.

### FED-AUTO — Automatic sync polling
- Class: core-capability
- Status: out-of-scope
- Description: Background job polling remote instances on interval for automatic sync.
- Why it matters: Manual "Sync Now" is sufficient for current usage. Data model supports future automation.
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Deferred per Phase 58 CONTEXT.md.

### FED-FEDI — Fediverse ActivityPub interop
- Class: integration
- Status: out-of-scope
- Description: Legacy cavage HTTP Signatures + RSA for Mastodon/ActivityPub compatibility.
- Why it matters: Only needed if fediverse interop becomes a goal. SemPKM-to-SemPKM uses RFC 9421.
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Would require RSA key support alongside existing Ed25519.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| EXP-01 | core-capability | active | M003/S01 | M003/S02, S03, S04 | unmapped |
| EXP-02 | core-capability | active | M003/S01 | none | unmapped |
| EXP-03 | core-capability | active | M003/S02 | none | unmapped |
| EXP-04 | core-capability | active | M003/S03 | none | unmapped |
| EXP-05 | core-capability | active | M003/S03 | none | unmapped |
| TAG-01 | core-capability | active | M003/S04 | none | unmapped |
| TAG-02 | core-capability | active | M003/S04 | none | unmapped |
| TAG-03 | core-capability | active | M003/S04 | none | unmapped |
| FAV-01 | core-capability | active | M003/S05 | none | unmapped |
| FAV-02 | core-capability | active | M003/S05 | none | unmapped |
| CMT-01 | core-capability | active | M003/S06 | none | unmapped |
| CMT-02 | core-capability | active | M003/S06 | none | unmapped |
| ONTO-01 | core-capability | active | M003/S07 | none | unmapped |
| ONTO-02 | core-capability | active | M003/S07 | none | unmapped |
| ONTO-03 | core-capability | active | M003/S07 | none | unmapped |
| GIST-01 | core-capability | active | M003/S07 | M003/S08 | unmapped |
| GIST-02 | core-capability | active | M003/S07 | none | unmapped |
| TYPE-01 | core-capability | active | M003/S08 | none | unmapped |
| TYPE-02 | core-capability | active | M003/S08 | none | unmapped |
| ADMIN-01 | admin/support | active | M003/S09 | none | unmapped |
| ADMIN-02 | admin/support | active | M003/S09 | none | unmapped |
| SEC-01 | compliance/security | validated | M002/S01 | none | slowapi rate limiting |
| SEC-02 | compliance/security | validated | M002/S01 | none | conditional token logging |
| SEC-03 | compliance/security | validated | M002/S01 | none | require_role on event console |
| SEC-04 | compliance/security | validated | M002/S01 | M002/S03 | escape_sparql_regex + 19 tests |
| SEC-05 | operability | validated | M002/S01 | none | deployment docs section |
| COR-01 | core-capability | validated | M002/S02 | none | hashlib.sha256 in report.py |
| COR-02 | core-capability | validated | M002/S02 | M002/S03 | _strip_sparql_strings + 6 tests |
| COR-03 | core-capability | validated | M002/S02 | none | GRAPH ?g source_model query |
| TEST-01 | quality-attribute | validated | M002/S03 | none | conftest.py + 130 tests |
| TEST-02 | quality-attribute | validated | M002/S03 | none | test_rdf_serialization + test_sparql_utils |
| TEST-03 | quality-attribute | validated | M002/S03 | none | test_iri_validation |
| TEST-04 | quality-attribute | validated | M002/S03 | none | test_auth_tokens |
| REF-01 | quality-attribute | validated | M002/S04 | none | 8 sub-modules, 33 routes |
| DEP-01 | operability | validated | M002/S05 | none | ~= pins in pyproject.toml |
| DEP-02 | operability | validated | M002/S05 | none | uv.lock committed |
| PERF-01 | quality-attribute | validated | M002/S05 | none | batched WHERE IN query |
| FED-11 | core-capability | validated | M002/S06 | none | discover_remote_instance_url |
| FED-12 | quality-attribute | validated | M002/S06 | none | docker-compose.federation-test.yml |
| FED-13 | quality-attribute | validated | M002/S06 | none | 8-step Playwright E2E test |
| OBSI-08 | core-capability | validated | M002/S07 | none | 895 objects imported |
| OBSI-09 | core-capability | validated | M002/S07 | none | 1767 wiki-link edges |
| OBSI-10 | core-capability | validated | M002/S07 | none | frontmatter properties in UI |
| TYPE-03 | core-capability | deferred | none | none | unmapped |
| TYPE-04 | core-capability | deferred | none | none | unmapped |
| MCP-01 | core-capability | deferred | none | none | unmapped |
| NOTION-01 | core-capability | deferred | none | none | unmapped |
| FED-CRDT | core-capability | out-of-scope | none | none | n/a |
| FED-AUTO | core-capability | out-of-scope | none | none | n/a |
| FED-FEDI | integration | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 21
- Mapped to slices: 21
- Validated: 60 (38 from M001 + 22 from M002)
- Deferred: 4
- Out of scope: 3
- Unmapped active requirements: 0
