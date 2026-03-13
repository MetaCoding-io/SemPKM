# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

<!-- No active requirements. All M002 requirements validated. -->

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

backend/uv.lock exists and committed.

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

### SPARQL-01 — SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs

### SPARQL-02 — User's SPARQL query history is persisted server-side and accessible across devices
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User's SPARQL query history is persisted server-side and accessible across devices

### SPARQL-03 — User can save a SPARQL query with a name and description
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User can save a SPARQL query with a name and description

### SPARQL-04 — User can share a saved query with other users (read-only)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can share a saved query with other users (read-only)

### SPARQL-05 — SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs

### SPARQL-06 — SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models

### SPARQL-07 — User can promote a saved query to a named view browsable in the nav tree
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can promote a saved query to a named view browsable in the nav tree

### SPARQL-08 — Ensure user cannot modify the graph via SPARQL, as we still want all writes to go thru the Command API
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Ensure user cannot modify the graph via SPARQL, as we still want all writes to go thru the Command API

### FED-01 — Events can be serialized as RDF Patch format (A/D operations)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Events can be serialized as RDF Patch format (A/D operations)

### FED-02 — API endpoint exports event patches since a given sequence number
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

API endpoint exports event patches since a given sequence number

### FED-03 — User can register a remote SemPKM instance for sync
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can register a remote SemPKM instance for sync

### FED-04 — Named graph sync pulls patches from remote instance and applies via EventStore
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Named graph sync pulls patches from remote instance and applies via EventStore

### FED-05 — Sync prevents infinite loops via syncSource tagging on federation-originated events
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Sync prevents infinite loops via syncSource tagging on federation-originated events

### FED-06 — Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles

### FED-07 — User can send a notification (e.g. shared concept) to a remote instance's LDN inbox
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can send a notification (e.g. shared concept) to a remote instance's LDN inbox

### FED-08 — User can view and act on received LDN notifications in the workspace
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can view and act on received LDN notifications in the workspace

### FED-09 — Incoming federation requests are authenticated via HTTP Signatures against WebID public keys
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Incoming federation requests are authenticated via HTTP Signatures against WebID public keys

### FED-10 — Collaboration UI shows registered remote instances, sync status, and incoming changes
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Collaboration UI shows registered remote instances, sync status, and incoming changes

### VFS-01 — MountSpec RDF vocabulary defines declarative directory structures
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

MountSpec RDF vocabulary defines declarative directory structures

### VFS-02 — User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat)

### VFS-03 — VFS provider dispatches to the correct strategy based on mount path prefix
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

VFS provider dispatches to the correct strategy based on mount path prefix

### VFS-04 — Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes

### VFS-05 — Mount management UI in Settings for creating, editing, and deleting mounts
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Mount management UI in Settings for creating, editing, and deleting mounts

### VFSX-01 — VFS browser shows side-by-side view for open files with raw content and rendered markdown preview
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser shows side-by-side view for open files with raw content and rendered markdown preview

### VFSX-02 — VFS browser file operations are polished (consistent icons, loading states)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser file operations are polished (consistent icons, loading states)

### VFSX-03 — VFS browser has inline help about connecting the user's OS to the WebDAV endpoint
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser has inline help about connecting the user's OS to the WebDAV endpoint

### OBUI-01 — Nav tree header has a refresh button to reload the object list
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a refresh button to reload the object list

### OBUI-02 — Nav tree header has a plus button to jump to the create new object flow
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a plus button to jump to the create new object flow

### OBUI-03 — User can select multiple objects via shift-click in the nav tree
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can select multiple objects via shift-click in the nav tree

### OBUI-04 — User can bulk delete selected objects
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can bulk delete selected objects

### OBUI-05 — Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type

### FIX-01 — Event log diffs render correctly for all operation types
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Event log diffs render correctly for all operation types

### FIX-02 — Lint dashboard controls display at correct width on all viewports
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Lint dashboard controls display at correct width on all viewports

### CANV-01 — Spatial canvas has snap-to-grid alignment
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has snap-to-grid alignment

### CANV-02 — Spatial canvas shows edge labels between connected nodes
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas shows edge labels between connected nodes

### CANV-03 — Spatial canvas has keyboard navigation support
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has keyboard navigation support

### CANV-04 — User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk. Wait for **OBUI-03** to be implemented
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk.

### CANV-05 — Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas, with a different color than rdf links
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas, with a different color than rdf links

## Deferred

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

### ADMIN-01 — Model detail page stats (avg connections, growth trend)
- Class: admin/support
- Status: deferred
- Description: Admin model detail page shows computed stats: average connections per node, last modified date, growth trend.
- Why it matters: Gives model administrators insight into knowledge graph health and activity.
- Source: execution (code TODO)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: TODO comment in model_detail.html:203.

### ADMIN-02 — Model detail page charts (sparkline, activity, link distribution)
- Class: admin/support
- Status: deferred
- Description: Admin model detail page shows visual charts: sparkline of activity, recent activity log, link distribution.
- Why it matters: Visual analytics for model health monitoring.
- Source: execution (code TODO)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: TODO comment in model_detail.html:233.

### NOTION-01 — Notion workspace import wizard
- Class: core-capability
- Status: deferred
- Description: Interactive import flow for Notion workspace exports (ZIP first, API later). Databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation as DashboardSpec objects.
- Why it matters: Notion is the most common PKM tool users migrate from. Structured import preserves their knowledge graph.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/notion-import-research.md`. Mirrors Obsidian wizard pattern with added Classify and Relation Mapping steps.

### ONTO-01 — Ontology viewer with TBox/ABox/RBox separation
- Class: core-capability
- Status: deferred
- Description: Integrated ontology visualization — TBox Explorer (class hierarchy across mental models), ABox Browser (instances by type), RBox Legend (property reference). Purpose-built views, not an embedded generic editor.
- Why it matters: Users can't currently see the schema landscape across installed mental models or understand how their data relates to the ontology.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/ontology-viewer-research.md`. Cytoscape.js for graph views, htmx trees for hierarchy.

### ONTO-02 — Gist upper ontology as foundation
- Class: core-capability
- Status: deferred
- Description: Gist 14.0.0 loaded as foundation ontology. Mental model classes aligned to gist hierarchy (e.g. basic-pkm:Note rdfs:subClassOf gist:IntellectualProperty). Enables cross-model hierarchy browsing.
- Why it matters: Provides a shared conceptual backbone so classes from different mental models have meaningful common ancestors.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/ontology-viewer-research.md`. CC BY 4.0 license. Pin to 14.0.0, update deliberately.

### UX-01 — Object hierarchy via dcterms:isPartOf
- Class: core-capability
- Status: deferred
- Description: Objects nestable in explorer by parent/child relationships (e.g. Project containing Action Items), not just by type.
- Why it matters: Hierarchical organization is a natural way to structure knowledge — flat type lists don't capture containment.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Explore connection to VFS spec or as parallel navigation axis.

### UX-02 — Tag explorer panel
- Class: core-capability
- Status: deferred
- Description: Dedicated view/panel for browsing and navigating by `schema:keywords` tags. Tag counts, click to filter, possibly tag hierarchy.
- Why it matters: Tags are a cross-cutting navigation axis orthogonal to types and hierarchy.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: none

### UX-03 — Object comments via rdfs:comment
- Class: core-capability
- Status: deferred
- Description: Users can add comments/annotations to any object. Threaded or flat discussion.
- Why it matters: Enables lightweight collaboration and personal annotation without editing the object itself.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: none

### UX-04 — Favorites and favorites view
- Class: core-capability
- Status: deferred
- Description: Users can star/favorite objects. Dedicated favorites view for quick access to frequently used items.
- Why it matters: Quick access to high-traffic objects without searching or navigating the tree.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: none

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
| SEC-01 | compliance/security | validated | M002/S01 | none | slowapi rate limiting, HTTP 429 verified |
| SEC-02 | compliance/security | validated | M002/S01 | none | conditional token logging |
| SEC-03 | compliance/security | validated | M002/S01 | none | require_role("owner") on event console |
| SEC-04 | compliance/security | validated | M002/S01 | M002/S03 | escape_sparql_regex + 19 unit tests |
| SEC-05 | operability | validated | M002/S01 | none | deployment docs section |
| COR-01 | core-capability | validated | M002/S02 | none | hashlib.sha256 in report.py |
| COR-02 | core-capability | validated | M002/S02 | M002/S03 | _strip_sparql_strings + 6 unit tests |
| COR-03 | core-capability | validated | M002/S02 | none | GRAPH ?g source_model query |
| TEST-01 | quality-attribute | validated | M002/S03 | none | conftest.py + 130 tests |
| TEST-02 | quality-attribute | validated | M002/S03 | none | test_rdf_serialization + test_sparql_utils |
| TEST-03 | quality-attribute | validated | M002/S03 | none | test_iri_validation |
| TEST-04 | quality-attribute | validated | M002/S03 | none | test_auth_tokens |
| REF-01 | quality-attribute | validated | M002/S04 | none | 8 sub-modules, 33 routes preserved |
| DEP-01 | operability | validated | M002/S05 | none | ~= pins in pyproject.toml |
| DEP-02 | operability | validated | M002/S05 | none | uv.lock committed |
| PERF-01 | quality-attribute | validated | M002/S05 | none | batched WHERE IN query |
| FED-11 | core-capability | validated | M002/S06 | none | discover_remote_instance_url |
| FED-12 | quality-attribute | validated | M002/S06 | none | docker-compose.federation-test.yml |
| FED-13 | quality-attribute | validated | M002/S06 | none | 8-step Playwright E2E test |
| OBSI-08 | core-capability | validated | M002/S07 | none | 895 objects imported |
| OBSI-09 | core-capability | validated | M002/S07 | none | 1767 wiki-link edges |
| OBSI-10 | core-capability | validated | M002/S07 | none | frontmatter properties in UI |
| MCP-01 | core-capability | deferred | none | none | unmapped |
| ADMIN-01 | admin/support | deferred | none | none | unmapped |
| ADMIN-02 | admin/support | deferred | none | none | unmapped |
| NOTION-01 | core-capability | deferred | none | none | unmapped |
| ONTO-01 | core-capability | deferred | none | none | unmapped |
| ONTO-02 | core-capability | deferred | none | none | unmapped |
| UX-01 | core-capability | deferred | none | none | unmapped |
| UX-02 | core-capability | deferred | none | none | unmapped |
| UX-03 | core-capability | deferred | none | none | unmapped |
| UX-04 | core-capability | deferred | none | none | unmapped |
| FED-CRDT | core-capability | out-of-scope | none | none | n/a |
| FED-AUTO | core-capability | out-of-scope | none | none | n/a |
| FED-FEDI | integration | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 0
- Validated: 60 (38 from M001 + 22 from M002)
- Deferred: 10
- Out of scope: 3
- Unmapped active requirements: 0
- Unmapped active requirements: 0
