# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### SEC-01 — Auth endpoints have per-IP rate limiting
- Class: compliance/security
- Status: active
- Description: `/api/auth/magic-link` and `/api/auth/verify` enforce per-IP rate limits to prevent enumeration and brute-force attacks.
- Why it matters: Without rate limiting, an attacker can enumerate valid emails via timing or brute-force magic link tokens (10-minute window).
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Magic link tokens expire after 10 minutes. slowapi or fastapi-limiter are candidates.

### SEC-02 — Magic link token not logged when SMTP is configured
- Class: compliance/security
- Status: active
- Description: When SMTP is configured and email delivery succeeds, the magic link token is not written to the application log.
- Why it matters: In production with SMTP, the plaintext token in logs defeats the purpose of email-based auth.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Currently `logger.info("Magic link token for %s: %s", ...)` runs unconditionally at auth/router.py:133.

### SEC-03 — Event console requires owner role
- Class: compliance/security
- Status: active
- Description: The `/events` debug endpoint requires `require_role("owner")`, matching the SPARQL console.
- Why it matters: The event console exposes raw command execution — should not be accessible to member/guest roles.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: SPARQL console already uses `require_role("owner")`. Event console uses `get_current_user`.

### SEC-04 — SPARQL filter text properly escaped against regex injection
- Class: compliance/security
- Status: active
- Description: User-provided filter text in SPARQL REGEX clauses is fully escaped to prevent regex injection or unexpected query behavior.
- Why it matters: Currently only `\` and `"` are escaped. Other SPARQL/regex special characters could alter query semantics.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S01
- Supporting slices: M002/S03
- Validation: unmapped
- Notes: Affects `views/service.py` filter text handling. Unit tests in S03 will cover the escaping function.

### SEC-05 — base_namespace deployment documented with production guidance
- Class: operability
- Status: active
- Description: Deployment documentation explains that `BASE_NAMESPACE` must be set to a real domain for production, with consequences of using the `example.org` default.
- Why it matters: If deployed without overriding, all object IRIs collide with other instances using the default.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: config.py defaults to `https://example.org/data/`.

### COR-01 — Validation report IRI uses stable hash
- Class: core-capability
- Status: active
- Description: `validation/report.py` uses a deterministic hash (e.g. `hashlib.sha256`) instead of Python's `hash()` for the fallback validation IRI.
- Why it matters: `hash()` is randomized across processes since Python 3.3. Validation reports become unreachable across restarts if the fallback path is hit.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: unmapped
- Notes: Line 175 in validation/report.py.

### COR-02 — scope_to_current_graph handles FROM/GRAPH in string literals
- Class: core-capability
- Status: active
- Description: `scope_to_current_graph()` does not falsely detect FROM/GRAPH keywords inside SPARQL string literals or comments.
- Why it matters: A query with these words inside string literals would incorrectly be treated as already scoped, skipping graph injection.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S02
- Supporting slices: M002/S03
- Validation: unmapped
- Notes: Affects sparql/client.py. Unit tests in S03 will cover edge cases.

### COR-03 — source_model attributed correctly with multiple models installed
- Class: core-capability
- Status: active
- Description: `ViewSpecService` correctly attributes `source_model` to the originating model even when multiple models are installed.
- Why it matters: Currently falls back to empty string when >1 model is installed, losing view provenance.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: unmapped
- Notes: views/service.py line 189. Needs per-spec model graph matching.

### TEST-01 — Backend pytest infrastructure exists with conftest and fixtures
- Class: quality-attribute
- Status: active
- Description: `backend/tests/` directory exists with conftest.py, async fixtures for triplestore client, event store, and database session.
- Why it matters: Zero backend unit tests exist. This establishes the foundation for all future backend testing.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: unmapped
- Notes: pyproject.toml already has pytest and pytest-asyncio in dev dependencies.

### TEST-02 — SPARQL serialization/escaping has unit tests
- Class: quality-attribute
- Status: active
- Description: Unit tests cover `_serialize_rdf_term()`, SPARQL string escaping, and `scope_to_current_graph()` including edge cases (literals with special chars, string literals containing SPARQL keywords).
- Why it matters: SPARQL generation is the most injection-sensitive code path. Untested escaping is a correctness and security risk.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Covers events/store.py serialization and sparql/client.py scoping.

### TEST-03 — IRI validation has unit tests
- Class: quality-attribute
- Status: active
- Description: Unit tests cover `_validate_iri()` with valid IRIs (https, urn), invalid IRIs (injection chars, relative paths), and edge cases.
- Why it matters: IRI validation is the primary defense against SPARQL injection from user-controlled URL path segments.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Covers browser/router.py `_validate_iri()`.

### TEST-04 — Auth token logic has unit tests
- Class: quality-attribute
- Status: active
- Description: Unit tests cover magic link token creation, verification, expiry, and setup token lifecycle.
- Why it matters: Auth token logic is security-critical and currently untested.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Covers auth/tokens.py.

### REF-01 — Browser router split into domain sub-routers with zero behavior change
- Class: quality-attribute
- Status: active
- Description: The 1956-line `browser/router.py` is split into sub-routers by domain (settings, objects, events, search, LLM, etc.) with all existing E2E tests passing unchanged.
- Why it matters: The monolith makes navigation, testing, and modification increasingly costly. Sub-routers enable focused work per domain.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: unmapped
- Notes: Zero behavior change required. All routes keep the same URL paths.

### DEP-01 — pyproject.toml dependency versions pinned
- Class: operability
- Status: active
- Description: All dependencies in `pyproject.toml` use exact or compatible-release pins instead of bare `>=` floors.
- Why it matters: Bare version floors allow silent breaking changes on fresh installs or CI rebuilds.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Currently all deps specify `>=` only.

### DEP-02 — uv.lock committed to source control
- Class: operability
- Status: active
- Description: `uv.lock` (or equivalent lockfile) is committed and respected in Docker builds for reproducible installs.
- Why it matters: Ensures all environments install identical dependency versions.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: No lockfile currently exists.

### PERF-01 — Event detail user lookup batched
- Class: quality-attribute
- Status: active
- Description: Event log detail endpoint batches user display name lookups instead of issuing one SQL query per event.
- Why it matters: N+1 query pattern causes linear SQL traffic growth with event count.
- Source: research (CONCERNS.md)
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Currently loops through unique user IRIs with one SELECT each.

### FED-11 — Sync Now button auto-discovers remote URL from shared graph metadata
- Class: core-capability
- Status: active
- Description: The Sync Now button works without requiring the user to manually provide a remote instance URL. The endpoint auto-discovers remote URLs from shared graph member metadata in the federation RDF graph.
- Why it matters: This is a blocking bug — Sync Now always returns HTTP 400 because federation.js sends an empty remote_instance_url.
- Source: execution (Phase 58 verification gap)
- Primary owning slice: M002/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Per CONTEXT.md design: "no separate register remote step — remotes derived from shared graphs."

### FED-12 — Federation dual-instance docker-compose for E2E testing
- Class: quality-attribute
- Status: active
- Description: A `docker-compose.federation-test.yml` spins up two complete SemPKM instances (separate triplestores, databases, ports) for testing federation flows.
- Why it matters: Federation cannot be tested with a single instance. Two real instances are needed to verify sync, LDN, and HTTP Signatures.
- Source: user
- Primary owning slice: M002/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Based on existing docker-compose.test.yml pattern. Instances need different BASE_NAMESPACE values.

### FED-13 — Federation E2E test covers invite → accept → sync flow
- Class: quality-attribute
- Status: active
- Description: A Playwright E2E test exercises the full federation flow: instance A invites instance B to a shared graph, B accepts, A creates an object in the shared graph, B syncs and sees it.
- Why it matters: Federation is the most complex cross-instance feature. Without E2E coverage, regressions are invisible.
- Source: user
- Primary owning slice: M002/S06
- Supporting slices: none
- Validation: unmapped
- Notes: May need API-level setup steps since federation involves two browser sessions.

### OBSI-08 — Ideaverse Pro 2.5 vault imports successfully
- Class: core-capability
- Status: active
- Description: The Ideaverse Pro 2.5 vault (905 .md files) uploads, scans, maps, and imports through the import wizard without errors.
- Why it matters: The import wizard was built with a small test fixture. A real 905-note vault is the stress test.
- Source: user
- Primary owning slice: M002/S07
- Supporting slices: none
- Validation: unmapped
- Notes: ZIP file already in repo root. Manual user-driven import.

### OBSI-09 — Wiki-links in imported notes resolve to edges between objects
- Class: core-capability
- Status: active
- Description: After importing the Ideaverse vault, wiki-links between notes are resolved to `dcterms:references` edges connecting the imported objects.
- Why it matters: Wiki-link resolution is the core value of importing an Obsidian vault — without it, the knowledge graph has no connections.
- Source: user
- Primary owning slice: M002/S07
- Supporting slices: none
- Validation: unmapped
- Notes: Two-pass executor: Pass 1 creates objects, Pass 2 resolves wiki-links. User verifies in Relations panel and graph view.

### OBSI-10 — Frontmatter from imported notes maps to RDF properties
- Class: core-capability
- Status: active
- Description: Frontmatter keys mapped during the import wizard appear as RDF properties on the imported objects.
- Why it matters: Frontmatter is how Obsidian users structure metadata. If it doesn't carry over, the import loses structured data.
- Source: user
- Primary owning slice: M002/S07
- Supporting slices: none
- Validation: unmapped
- Notes: User maps frontmatter keys to RDF predicates in the mapping step.

## Validated

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
| SEC-01 | compliance/security | active | M002/S01 | none | unmapped |
| SEC-02 | compliance/security | active | M002/S01 | none | unmapped |
| SEC-03 | compliance/security | active | M002/S01 | none | unmapped |
| SEC-04 | compliance/security | active | M002/S01 | M002/S03 | unmapped |
| SEC-05 | operability | active | M002/S01 | none | unmapped |
| COR-01 | core-capability | active | M002/S02 | none | unmapped |
| COR-02 | core-capability | active | M002/S02 | M002/S03 | unmapped |
| COR-03 | core-capability | active | M002/S02 | none | unmapped |
| TEST-01 | quality-attribute | active | M002/S03 | none | unmapped |
| TEST-02 | quality-attribute | active | M002/S03 | none | unmapped |
| TEST-03 | quality-attribute | active | M002/S03 | none | unmapped |
| TEST-04 | quality-attribute | active | M002/S03 | none | unmapped |
| REF-01 | quality-attribute | active | M002/S04 | none | unmapped |
| DEP-01 | operability | active | M002/S05 | none | unmapped |
| DEP-02 | operability | active | M002/S05 | none | unmapped |
| PERF-01 | quality-attribute | active | M002/S05 | none | unmapped |
| FED-11 | core-capability | active | M002/S06 | none | unmapped |
| FED-12 | quality-attribute | active | M002/S06 | none | unmapped |
| FED-13 | quality-attribute | active | M002/S06 | none | unmapped |
| OBSI-08 | core-capability | active | M002/S07 | none | unmapped |
| OBSI-09 | core-capability | active | M002/S07 | none | unmapped |
| OBSI-10 | core-capability | active | M002/S07 | none | unmapped |
| MCP-01 | core-capability | deferred | none | none | unmapped |
| ADMIN-01 | admin/support | deferred | none | none | unmapped |
| ADMIN-02 | admin/support | deferred | none | none | unmapped |
| FED-CRDT | core-capability | out-of-scope | none | none | n/a |
| FED-AUTO | core-capability | out-of-scope | none | none | n/a |
| FED-FEDI | integration | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 22
- Mapped to slices: 22
- Validated: 38 (from M001)
- Deferred: 3
- Out of scope: 3
- Unmapped active requirements: 0
