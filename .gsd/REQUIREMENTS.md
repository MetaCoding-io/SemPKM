# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

(No active requirements — all M003 requirements validated.)

## Validated

### EXP-01 — Explorer mode dropdown with switchable navigation strategies
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S01

EXPLORER_MODES registry with by-type, hierarchy, by-tag handlers + mount: prefix dispatch in workspace.py. E2E spec: explorer-mode-switching.spec.ts.

### EXP-02 — By-type mode (current behavior) as default explorer mode
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S01

_handle_by_type() handler delegates to nav_tree.html. /browser/nav-tree kept for backwards compat.

### EXP-03 — Hierarchy mode via dcterms:isPartOf with arbitrary nesting depth
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S02

_handle_hierarchy() queries dcterms:isPartOf roots; /explorer/children for lazy expansion. Unit tests: test_hierarchy_explorer.py.

### EXP-04 — VFS mount specs visible as explorer modes
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S03

mount:{uuid} options in explorer dropdown; _handle_mount dispatches to 5 VFS strategies. E2E spec: vfs-explorer.spec.ts.

### EXP-05 — VFS explorer shows full rich objects with same click-to-open behavior
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S03

VFS mount tree leaves use same handleTreeLeafClick/openTab as by-type tree. Objects rendered with labels and type icons.

### TAG-01 — Tag parsing fix: comma-separated schema:keywords split into individual triples
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

split_tag_values() on save in object_patch.py; /admin/migrate-tags endpoint; seed data updated to arrays. Unit tests: test_tag_splitting.py.

### TAG-02 — Tags render as pills with # prefix in object view and properties panel
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

Tag pill CSS in workspace.css; tag_tree.html with # prefix. E2E spec: tag-explorer.spec.ts.

### TAG-03 — Tag explorer mode in explorer dropdown
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

_handle_by_tag() handler with UNION SPARQL across bpkm:tags and schema:keywords. Unit tests: test_tag_explorer.py.

### TAG-04 — Hierarchical tag tree with `/`-delimited nesting
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M005/S03

Tags with `/` delimiters render as nested tree nodes at arbitrary depth in By Tag explorer. `build_tag_tree()` pure function groups flat tag data into hierarchical nodes. `tag_children` endpoint extended with `prefix` parameter for lazy sub-folder loading. 61 unit tests (28 tree builder + 33 explorer).

### TAG-05 — Tag autocomplete in edit forms
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M005/S04

Tag input fields in edit forms offer autocomplete with existing tag values from the graph. `GET /browser/tag-suggestions?q=<prefix>` endpoint queries both `bpkm:tags` and `schema:keywords` via SPARQL UNION, returns frequency-ordered HTML suggestions (LIMIT 30). `_field.html` macro detects tag properties and renders `.tag-autocomplete-field` wrapper with htmx-driven dropdown. `addMultiValue()` cloning supports tag autocomplete fields. 22 unit tests.

### FAV-01 — Per-user favorites: star/unstar objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S05

UserFavorite SQL model; /favorites/toggle; star button on objects; Alembic migration 009. E2E spec: favorites.spec.ts.

### FAV-02 — FAVORITES collapsible section in explorer pane
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S05

FAVORITES section above OBJECTS in workspace.html; /favorites/list; HX-Trigger favoritesRefreshed auto-refresh.

### CMT-01 — Threaded collaborative comments on objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S06

sempkm:Comment RDF vocabulary; comment.create/reply/delete via EventStore; threaded via replyTo. E2E spec: comments.spec.ts.

### CMT-02 — Comment panel in object view with author attribution and timestamps
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S06

comments_section.html with author badges (batch-resolved from SQL), relative timestamps, reply forms, recursive comment_thread.html partial.

### ONTO-01 — TBox Explorer: unified class hierarchy across all installed models
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

TBox tree via /ontology/tbox with cross-graph FROM clause aggregation (gist + model + user-types). E2E spec: ontology-viewer.spec.ts confirms gist classes visible.

### ONTO-02 — ABox Browser: instances grouped by type with counts
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

ABox tab via /ontology/abox; types with instance counts > 0; drill-down via /ontology/abox/instances.

### ONTO-03 — RBox Legend: property reference with domains, ranges, and characteristics
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

RBox tab via /ontology/rbox; object + datatype properties with domains and ranges in rbox_legend.html.

### GIST-01 — Gist 14.0.0 loaded as foundation ontology in named graph
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

gistCore14.0.0.ttl bundled in backend/ontologies/gist/; loaded into urn:sempkm:ontology:gist via batched INSERT DATA. CC BY 4.0.

### GIST-02 — Mental model classes aligned to gist hierarchy
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

basic-pkm: Project→gist:Task, Person→gist:Person, Note→gist:FormattedContent, Concept→gist:KnowledgeConcept. ppv: Project→gist:Task.

### TYPE-01 — In-app class creation: name, icon, parent class, basic properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S08

"+ Create Class" button on Ontology Viewer page renders full form (name, icon picker, parent selector, property editor). POST /ontology/create-class endpoint. Verified in live browser 2026-03-13.

### TYPE-02 — Created classes generate valid OWL class + SHACL shape
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S08

OntologyService.create_class() generates OWL class + SHACL NodeShape in urn:sempkm:user-types graph. Discoverable by ShapesService. Verified form + endpoint exist in live browser 2026-03-13.

### ADMIN-01 — Model detail page stats: avg connections, last modified, growth trend
- Status: validated
- Class: admin/support
- Source: execution (code TODO)
- Primary Slice: M003/S09

SPARQL-computed avg_connections, last_modified, growth_trend in model_detail.html. E2E spec: admin-model-detail.spec.ts.

### ADMIN-02 — Model detail page charts: sparkline, activity, link distribution
- Status: validated
- Class: admin/support
- Source: execution (code TODO)
- Primary Slice: M003/S09

Chart.js 4.4 CDN; growth sparkline (8-week) + link distribution (5-bucket histogram). Lazy init on flip transitionend.

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

### PROP-01 — In-app property creation (ObjectProperty and DatatypeProperty)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S01

OntologyService.create_property() creates OWL ObjectProperty or DatatypeProperty with rdfs:label, rdfs:domain, rdfs:range in urn:sempkm:user-types graph. POST /browser/ontology/create-property endpoint with form-based UI on RBox tab. Unit tests: test_class_creation.py.

### PROP-02 — Property editing (rename, change domain/range)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S03

OntologyService.edit_property() updates label, domain, and range via DELETE/INSERT SPARQL. Accessible from both RBox tab and Custom section on Mental Models. PUT /browser/ontology/edit-property endpoint.

### PROP-03 — Property deletion with confirmation
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S02

OntologyService.delete_property() removes all triples for a user-created property. DELETE /browser/ontology/delete-property endpoint with user-types IRI guard. Unit tests: test_class_creation.py.

### TYPE-05 — Class editing (rename, icon, parent, add/remove properties, SHACL shape update)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S01

OntologyService.edit_class() updates label, icon, color, parent, and properties — replaces SHACL NodeShape via full shape regeneration. POST /browser/ontology/edit-class endpoint with edit_class_form.html modal.

### TYPE-06 — Class deletion with instance-count warnings and confirmation
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S02

OntologyService.delete_class() removes OWL class + SHACL shape triples. GET /browser/ontology/delete-class-check endpoint shows instance/subclass counts with confirmation dialog. DELETE /browser/ontology/delete-class endpoint with user-types IRI guard. Unit tests: test_class_creation.py.

### TYPE-07 — Custom section on Mental Models page listing user types/properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S03

OntologyService.list_user_types() queries user-types graph for classes and properties. Mental Models page renders "Custom" section with edit/delete actions inline. Accessible from /browser/mental-models.

### TAB-01 — Create-new-object opens fresh dockview tab
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S04

Fixed openTab() in workspace.js to always open create-new-object in a fresh dockview tab instead of overwriting the active tab. Preserves user's current view.

### LOG-01 — Operations log with PROV-O vocabulary in admin UI
- Status: validated
- Class: admin/support
- Source: user
- Primary Slice: M005/S02

OperationsLogService with log_activity(), list_activities(), get_activity(), count_activities(). PROV-O vocabulary (prov:Activity, prov:startedAtTime, prov:endedAtTime, prov:wasAssociatedWith, prov:used) in urn:sempkm:ops-log named graph. Admin UI at /admin/ops-log with filter and cursor-based pagination. Model install/remove, inference, and validation instrumented with fire-and-forget logging. Unit tests: test_ops_log.py (35 tests).

### MIG-01 — Model schema refresh without uninstall
- Status: validated
- Class: admin/support
- Source: user
- Primary Slice: M005/S05

`POST /admin/models/{model_id}/refresh-artifacts` endpoint updates ontology, shapes, views, and rules graphs from disk without touching seed graph or user data. Transactional CLEAR+INSERT with rollback on failure. Admin UI "Refresh" button on model list and detail pages. ViewSpec cache invalidation. Ops log integration (`model.refresh` activity type). Unit tests: test_model_refresh.py (21 tests).

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
| EXP-01 | core-capability | validated | M003/S01 | M003/S02, S03, S04 | EXPLORER_MODES registry + E2E |
| EXP-02 | core-capability | validated | M003/S01 | none | _handle_by_type handler |
| EXP-03 | core-capability | validated | M003/S02 | none | hierarchy mode + lazy expand |
| EXP-04 | core-capability | validated | M003/S03 | none | mount:{uuid} dispatch + E2E |
| EXP-05 | core-capability | validated | M003/S03 | none | rich objects in mount trees |
| TAG-01 | core-capability | validated | M003/S04 | none | split_tag_values + migration |
| TAG-02 | core-capability | validated | M003/S04 | none | tag pill CSS + # prefix |
| TAG-03 | core-capability | validated | M003/S04 | none | by-tag mode + UNION SPARQL |
| TAG-04 | core-capability | validated | M005/S03 | none | hierarchical `/` nesting + 61 tests |
| TAG-05 | core-capability | validated | M005/S04 | none | tag autocomplete + 22 tests |
| FAV-01 | core-capability | validated | M003/S05 | none | SQL table + toggle + E2E |
| FAV-02 | core-capability | validated | M003/S05 | none | FAVORITES section + auto-refresh |
| CMT-01 | core-capability | validated | M003/S06 | none | RDF comments + EventStore + E2E |
| CMT-02 | core-capability | validated | M003/S06 | none | threaded display + author badges |
| ONTO-01 | core-capability | validated | M003/S07 | none | TBox cross-graph hierarchy + E2E |
| ONTO-02 | core-capability | validated | M003/S07 | none | ABox instance counts + drill-down |
| ONTO-03 | core-capability | validated | M003/S07 | none | RBox property reference table |
| GIST-01 | core-capability | validated | M003/S07 | M003/S08 | gistCore14.0.0 loaded in named graph |
| GIST-02 | core-capability | validated | M003/S07 | none | rdfs:subClassOf in basic-pkm + ppv |
| TYPE-01 | core-capability | validated | M003/S08 | none | Create Class form on Ontology Viewer, verified 2026-03-13 |
| TYPE-02 | core-capability | validated | M003/S08 | none | OWL + SHACL generation, verified 2026-03-13 |
| ADMIN-01 | admin/support | validated | M003/S09 | none | SPARQL-computed stats |
| ADMIN-02 | admin/support | validated | M003/S09 | none | Chart.js sparkline + histogram |
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
| PROP-01 | core-capability | validated | M004/S01 | none | create_property service + endpoint |
| PROP-02 | core-capability | validated | M004/S03 | none | edit_property service + endpoint |
| PROP-03 | core-capability | validated | M004/S02 | none | delete_property service + endpoint |
| TYPE-05 | core-capability | validated | M004/S01 | none | edit_class with SHACL shape replacement |
| TYPE-06 | core-capability | validated | M004/S02 | none | delete_class with instance warnings |
| TYPE-07 | core-capability | validated | M004/S03 | none | Custom section on Mental Models |
| TAB-01 | core-capability | validated | M004/S04 | none | fresh dockview tab for new objects |
| LOG-01 | admin/support | validated | M005/S02 | none | PROV-O ops log + admin UI + 35 tests |
| MIG-01 | admin/support | validated | M005/S05 | none | refresh_artifacts endpoint + admin UI + 21 tests |
| TYPE-03 | core-capability | deferred | none | none | unmapped |
| TYPE-04 | core-capability | deferred | none | none | unmapped |
| MCP-01 | core-capability | deferred | none | none | unmapped |
| NOTION-01 | core-capability | deferred | none | none | unmapped |
| FED-CRDT | core-capability | out-of-scope | none | none | n/a |
| FED-AUTO | core-capability | out-of-scope | none | none | n/a |
| FED-FEDI | integration | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 0
- Validated: 92 (38 from M001 + 22 from M002 + 21 from M003 + 7 from M004 + 4 from M005)
- Deferred: 4
- Out of scope: 3
- Unmapped active requirements: 0
