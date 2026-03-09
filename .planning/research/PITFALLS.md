# Domain Pitfalls

**Domain:** v2.6 Power User & Collaboration -- SPARQL permissions, RDF sync/federation, MountSpec VFS, UI improvements
**Researched:** 2026-03-09
**Confidence:** HIGH for SPARQL permission scoping (codebase analysis + triplestore security docs); MEDIUM for RDF Patch/federation (W3C specs + limited real-world implementation reports); HIGH for VFS/MountSpec (codebase analysis + wsgidav docs); MEDIUM for LDN (W3C spec, sparse implementation experience reports)

---

## Critical Pitfalls

### Pitfall 1: SPARQL Permissions Bypass via `all_graphs=True` and Unscoped Query Patterns

**What goes wrong:**
The current SPARQL endpoint (`/api/sparql`) has an `all_graphs` query parameter that bypasses graph scoping entirely. Any authenticated user can pass `all_graphs=true` and read event graph data, including other users' provenance metadata, compensating events, and deleted object history. When SPARQL permissions are added, this existing bypass remains unless explicitly addressed. A "guest" user with SPARQL console access can see the full event history of every user's writes.

Separately, `scope_to_current_graph()` only injects `FROM` clauses -- it does not prevent users from writing `GRAPH ?g { ... }` patterns that enumerate all named graphs. A user can write `SELECT ?g WHERE { GRAPH ?g { ?s ?p ?o } } LIMIT 100` and discover every event graph IRI in the system, even when `all_graphs=false`.

**Why it happens:**
The scoping logic was designed for convenience (inject defaults), not security (enforce boundaries). It checks for `FROM` or `GRAPH <urn:sempkm:current>` in the query text but does not detect arbitrary `GRAPH ?variable` patterns. The `all_graphs` parameter was added for admin/debug use but has no role check -- any authenticated user can use it.

**Consequences:**
- Guest/member users can read event provenance (who edited what, when)
- Users can discover deleted objects via event graph contents
- Users can read inferred graph contents even if inference data should be filtered
- Full event history is a privacy leak in multi-user deployments

**Prevention:**
1. Gate `all_graphs=true` behind `require_role("owner")` immediately. This is a one-line fix in `sparql/router.py`.
2. For SPARQL permissions, do NOT attempt to parse and rewrite arbitrary SPARQL to enforce graph restrictions. This is a solved-hard problem (query rewriting is fragile, breaks with subqueries, and has edge cases with CONSTRUCT/DESCRIBE). Instead: proxy the query through RDF4J's own dataset restriction mechanism. RDF4J supports `default-graph-uri` and `named-graph-uri` parameters on its SPARQL endpoint -- set these server-side before forwarding the query, so the triplestore itself enforces the graph boundary.
3. Strip any user-supplied `FROM` / `FROM NAMED` clauses before forwarding. Users should not be able to override the server-enforced graph scope.

**Detection:**
- Audit log: any query containing `all_graphs=true` from a non-owner user
- Test: submit `SELECT ?g WHERE { GRAPH ?g { ?s ?p ?o } }` as a guest -- if it returns event graph IRIs, permissions are broken

**Phase to address:**
SPARQL Interface (permissions phase). Must be the FIRST sub-feature implemented before autocomplete, history, or saved queries -- everything else builds on a permission-safe SPARQL layer.

---

### Pitfall 2: RDF Patch / Named Graph Sync Creates Ghost Triples in Current State

**What goes wrong:**
SemPKM's write path is event-sourced: every mutation goes through `EventStore.commit()`, which creates an immutable event graph AND materializes changes into `urn:sempkm:current`. RDF Patch sync that writes directly to named graphs (bypassing EventStore) creates triples that exist in the triplestore but have no corresponding event. These "ghost triples" cause:
- Event log shows no record of the change
- Undo (compensating events) cannot reverse the change
- SHACL validation never runs on the synced data
- The lint dashboard shows a clean state for objects that may violate constraints

If sync writes to `urn:sempkm:current` directly, the materialized state diverges from the event history. If sync creates its own named graphs, those graphs are invisible to queries scoped to `urn:sempkm:current` unless the scoping logic is updated.

**Why it happens:**
RDF Patch is a transport format -- it describes graph-level ADD/DELETE operations. It has no concept of application-level events, SHACL validation, or materialization. Naively applying patches to the triplestore treats it as a dumb quad store, bypassing the entire application layer that makes SemPKM's data model work.

**Consequences:**
- Data integrity: materialized state diverges from event log
- Auditability: synced changes have no provenance
- Validation: synced objects skip SHACL, may violate shapes
- Undo: cannot undo synced changes via compensating events

**Prevention:**
RDF Patch ingestion MUST be translated into Command API operations, not applied as raw triplestore writes. The sync receiver should:
1. Parse the RDF Patch into add/delete triple sets
2. Group changes by affected object IRI
3. For each object, construct the appropriate Command API call (`object.create`, `object.patch`, `edge.create`, etc.)
4. Let EventStore.commit() handle materialization, provenance, and validation

This is slower than raw patch application but preserves all invariants. For bulk sync (initial federation setup), consider a "sync import" mode that batches operations into fewer events but still goes through EventStore.

If raw patch application is needed for performance (large datasets), create a dedicated `urn:sempkm:federated:{remote-id}` named graph per remote peer and update the graph scoping to include federated graphs. But this is a significant architectural expansion -- do not attempt it in v2.6.

**Detection:**
- Query: `SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o } }` vs total events materialized -- significant discrepancy means ghost triples exist
- Any triple in `urn:sempkm:current` that cannot be traced to an event graph

**Phase to address:**
Collaboration & Federation (RDF Patch phase). Design the patch-to-command translation layer BEFORE implementing any sync protocol. Validate with a round-trip test: create object locally, export as patch, delete locally, re-import patch, verify event log contains the re-creation.

---

### Pitfall 3: MountSpec Multiple Directory Strategies with Conflicting Paths

**What goes wrong:**
The current VFS has exactly one directory strategy: `/{model-id}/{type-label}/{filename}.md`. MountSpec introduces 5 strategies (e.g., by-type, by-tag, by-date, flat, custom SPARQL). When multiple strategies are active simultaneously, the same RDF object appears at multiple paths. WebDAV clients (Obsidian, VS Code, macOS Finder) cache directory listings and treat each path as a distinct file. Editing the same object via two different paths creates a write conflict: both PUTs arrive at the VFS write handler with different paths but the same object IRI, and whichever completes last wins silently.

Worse: wsgidav's lock manager uses the path as the lock key. A LOCK on `/by-type/Note/my-note.md` does not prevent writes to `/by-tag/research/my-note.md` -- they are different resources from wsgidav's perspective, even though they map to the same RDF object.

**Why it happens:**
The wsgidav `DAVProvider.get_resource_inst()` receives a path and returns a resource. The current implementation maps path segments to SPARQL queries. With multiple strategies, the mapping becomes many-to-one (many paths, one object). wsgidav has no concept of resource identity beyond the path -- it cannot know that two paths point to the same underlying object.

**Consequences:**
- Silent data loss: last-write-wins when editing via different strategy paths
- Lock bypass: locking one path does not lock the object at other paths
- Client confusion: rename/move in one strategy view has no effect in another
- Cache staleness: editing via one path does not invalidate the client's cache of the other path

**Prevention:**
1. Designate exactly ONE strategy as the "canonical path" for writes. All other strategies serve read-only virtual paths. This mirrors wsgidav's own virtual_dav_provider example where only the `by_key` path is writable and `by_tag`/`by_status` are read-only aliases.
2. In non-canonical strategy collections, override `create_empty_resource()` and `begin_write()` to raise `HTTP_FORBIDDEN` with a message directing users to the canonical path.
3. Store the canonical path in the MountSpec vocabulary so the VFS browser can show a "go to editable location" link for read-only aliases.
4. For the lock manager: inject a custom `LockManager` subclass that maps all path variants of an object to the same lock token using the object IRI as the lock key (not the path). This is non-trivial but necessary for correctness.

**Detection:**
- Test: mount two strategies, open the same object in both, edit in both, verify one edit is not silently lost
- Test: LOCK via one path, attempt PUT via another path to the same object, verify 423 Locked

**Phase to address:**
User Custom VFS (MountSpec). The canonical-path-is-writable rule must be established in the MountSpec vocabulary design before implementing any strategy beyond the existing by-type strategy.

---

### Pitfall 4: Federated WebID Auth Trusts Remote WebID Documents Without Verification

**What goes wrong:**
Federated WebID authentication works by: (1) remote user presents a WebID URI, (2) local server dereferences the WebID URI to fetch the profile document, (3) profile document contains a public key, (4) local server verifies the request was signed with the corresponding private key. The critical vulnerability: the local server fetches an RDF document from an arbitrary URL on the internet and trusts its contents to make authorization decisions. An attacker who controls a web server can host a fake WebID profile claiming to be any identity, and the local SemPKM instance will accept it.

Additionally, if the WebID URI is an `https://` URL on a domain the attacker controls, they can serve different profile documents to different requesters (MITM the verification step itself). The local server has no way to distinguish a legitimate WebID from a spoofed one without additional trust anchors.

**Why it happens:**
WebID-TLS was designed for a world where the TLS client certificate itself provided the trust anchor (the certificate is signed by a CA, and the WebID URI in the certificate's SAN field is the identity claim). When moving to HTTP Signatures (which SemPKM uses via Ed25519 keys), the TLS trust anchor is lost. The public key in the WebID document is self-asserted -- there is no CA chain to verify.

**Consequences:**
- Identity spoofing: attacker creates a WebID at `https://evil.example/alice#me` and claims to be "Alice"
- Privilege escalation: if the local instance grants permissions based on WebID URI patterns (e.g., "trust all users from `https://trusted-instance.example/`"), the attacker hosts a WebID on a similar-looking domain
- SSRF vector: the local server fetches arbitrary URLs during authentication, which can be pointed at internal services

**Prevention:**
1. Never grant permissions based solely on a WebID URI. Require an explicit "trust relationship" between instances: the local admin must configure a list of trusted remote instance base URLs. Only WebID URIs from trusted instances are accepted.
2. Implement SSRF protection on the WebID fetch: block private IP ranges, localhost, and link-local addresses. Use a dedicated HTTP client with strict timeouts (3s connect, 5s read) and no redirect following.
3. Cache fetched WebID profiles with a short TTL (5 minutes) and verify the public key matches on every request. If the key changes between cached fetches, reject the authentication and log a warning.
4. Consider using IndieAuth (which SemPKM already has) as the federation auth mechanism instead of raw WebID verification. IndieAuth provides an authorization code flow that verifies the remote user actually controls their identity endpoint -- it does not rely on trusting fetched documents.

**Detection:**
- Test: create a WebID at a test URL, attempt to authenticate against the local instance without being in the trusted list, verify rejection
- Monitor: log all WebID fetch URLs and alert on fetches to unusual domains

**Phase to address:**
Collaboration & Federation (federated WebID auth). The trusted instance allowlist must be implemented BEFORE any remote authentication is accepted. Do not ship "open federation" that trusts any WebID.

---

### Pitfall 5: SPARQL Saved/Shared Queries Execute with Sharer's Implicit Permissions

**What goes wrong:**
When saved queries are shared between users, the query executes in the context of the user who runs it, not the user who created it. This sounds correct -- but the query text itself may contain hardcoded graph URIs, IRI patterns, or `all_graphs=true` flags that were valid for the sharer's permission level but not for the runner. If a shared query bypasses graph scoping (because the sharer was an admin), and the runner is a guest, the guest now has admin-level read access through the saved query.

Conversely, if permissions are enforced at execution time (correct), a shared query that worked for the admin may silently return empty results for a guest, with no indication that permissions are the cause. The guest sees an empty result set and assumes the query is broken.

**Why it happens:**
SPARQL queries are opaque text strings. There is no metadata about what permissions were assumed when the query was written. Graph scoping (`scope_to_current_graph`) strips user-supplied `FROM` clauses -- but a saved query may have been authored to work with `all_graphs=true`, which is a separate code path.

**Consequences:**
- Privilege escalation if queries bypass scoping
- Confusing empty results if queries require permissions the runner lacks
- Trust erosion: shared queries that "work for me but not for you" undermine collaboration

**Prevention:**
1. Saved queries MUST NOT store execution parameters like `all_graphs`. Only the query text is saved. Execution parameters are always determined at runtime from the runner's session.
2. When displaying shared query results, if the result set is empty and the query is shared, show a hint: "This query returned no results. If the query works for the author, you may not have permission to access the referenced data."
3. Add a `required_role` field to saved queries. If the author marks a query as requiring "owner" access, the UI shows a lock icon and prevents non-owners from running it (rather than returning confusing empty results).

**Detection:**
- Test: admin saves a query using `all_graphs=true`, shares with guest, guest runs it -- verify guest gets scoped results (not all-graphs results)

**Phase to address:**
SPARQL Interface (saved/shared queries). Implement after permissions are solid.

---

## Moderate Pitfalls

### Pitfall 6: SPARQL Autocomplete Floods RDF4J with Schema Introspection Queries

**What goes wrong:**
Ontology-aware autocomplete requires knowing the available classes, properties, and their domains/ranges. A naive implementation fires a SPARQL query on every keystroke to fetch matching terms from the triplestore. On a dataset with hundreds of properties across multiple Mental Models, each autocomplete request takes 200-500ms (SPARQL round-trip through the API proxy to RDF4J). With typical typing speed (5-10 keystrokes/second), the query queue grows faster than it drains, causing UI lag and triplestore load spikes.

The Yasgui CDN build already includes basic autocomplete (prefixed names, keywords), but it queries the SPARQL endpoint itself for class/property lists. On non-Qlever endpoints like RDF4J, this can take several seconds per request.

**How to avoid:**
Cache the schema introspection results server-side. On model install/uninstall, precompute and cache:
- All class IRIs with labels (from SHACL `sh:targetClass` and `rdf:type rdfs:Class/owl:Class`)
- All property IRIs with labels, domains, and ranges (from SHACL `sh:path` and `rdfs:domain`/`rdfs:range`)
- All prefix mappings

Serve this as a static JSON endpoint (`/api/sparql/schema`) that Yasgui's custom completer fetches once on init and caches in memory. The frontend filters locally -- no per-keystroke SPARQL queries.

Debounce any remaining dynamic completions (e.g., IRI suggestions from instance data) to 300ms minimum. Cancel in-flight requests when new input arrives.

**Warning signs:**
- Typing in the SPARQL editor feels laggy (>200ms between keystroke and suggestion popup)
- RDF4J access log shows repeated schema queries during editing
- Browser DevTools network tab shows queued pending requests to `/api/sparql`

**Phase to address:**
SPARQL Interface (autocomplete). Build the cached schema endpoint before wiring autocomplete into Yasgui.

---

### Pitfall 7: IRI Pill Rendering in SPARQL Results Breaks with Non-Object IRIs

**What goes wrong:**
The current Yasgui custom renderer converts IRI results into clickable pill links that open SemPKM object tabs. This works for object IRIs (which exist in `urn:sempkm:current` and have labels). But SPARQL results frequently contain non-object IRIs: ontology class URIs (`rdfs:Class`), property URIs (`dcterms:title`), blank node identifiers, event graph IRIs (`urn:sempkm:event:...`), and external URIs (`http://dbpedia.org/...`). Rendering all of these as clickable pills that attempt to open object tabs results in 404 errors, blank panels, or confusing "object not found" states.

**How to avoid:**
Classify IRIs before rendering:
1. **Object IRIs** (in `urn:sempkm:current` with `rdf:type`): render as clickable pills that open object tabs
2. **Ontology/schema IRIs** (classes, properties): render as styled pills with a different color, clicking opens a schema info popover (not an object tab)
3. **Event graph IRIs** (`urn:sempkm:event:*`): render as timestamped event links (open event log filtered to that event)
4. **External IRIs**: render as external links (open in new browser tab)
5. **Unknown IRIs**: render as plain text with copy-on-click

The classification requires a lookup. Do NOT make a per-IRI SPARQL query. Instead, batch-classify all IRIs in a result set with a single query: `ASK WHERE { GRAPH <urn:sempkm:current> { <{iri}> a ?type } }` for each unique IRI, batched into a single `VALUES` clause.

**Warning signs:**
- Clicking a pill in SPARQL results opens a blank or error panel
- SPARQL results showing class/property URIs all have the same "object" styling

**Phase to address:**
SPARQL Interface (IRI pills enhancement). Implement classification before expanding pill rendering beyond the current behavior.

---

### Pitfall 8: LDN Inbox Becomes an Open Write Endpoint for Spam

**What goes wrong:**
The LDN specification requires that the inbox endpoint accepts POST requests from any sender -- this is by design (anyone should be able to send a notification). Without rate limiting and content validation, the inbox becomes an unauthenticated write endpoint that spammers, bots, and fuzzers can flood with arbitrary JSON-LD payloads. Each notification is stored (per LDN spec), consuming storage. If notifications trigger side effects (e.g., federation sync, UI alerts), spam notifications cause cascading resource consumption.

**How to avoid:**
1. Rate limit the inbox endpoint: 10 notifications per minute per source IP, 100 per hour. Return `429 Too Many Requests` when exceeded.
2. Validate notification payloads against a minimal JSON-LD shape: require `@type`, `actor`, `object`, and `target` fields. Reject malformed payloads with `400 Bad Request` before storing.
3. Do NOT process notifications synchronously. Store them in a queue (or SQLite table) and process asynchronously with a background worker. This prevents a slow notification from blocking the HTTP response.
4. Add an admin UI to view and manage pending notifications. Notifications from untrusted sources should require admin approval before triggering any side effects.
5. Consider requiring authentication (via HTTP Signatures with a known WebID) for notifications that trigger write operations (e.g., sync requests). Read-only notifications (e.g., "I linked to your object") can be accepted anonymously.

**Warning signs:**
- Database/storage growing unexpectedly (spam notifications accumulating)
- Notifications from unknown origins appearing in the UI
- Sync or federation actions triggered by external POST requests without admin knowledge

**Phase to address:**
Collaboration & Federation (LDN notifications). Implement rate limiting and payload validation as part of the inbox endpoint, not as a later hardening step.

---

### Pitfall 9: MountSpec SHACL Frontmatter Writes Corrupt Properties on Partial Update

**What goes wrong:**
The current VFS write path (`vfs/write.py`) strips YAML frontmatter and commits only the Markdown body via `body.set`. MountSpec extends this to also write back frontmatter fields as RDF property changes. The danger: a WebDAV client may write a file with partial or stale frontmatter. If the user edits only the body in their text editor, the frontmatter echoed back is the version from when the file was last read -- which may be stale if another user or the web UI changed a property in the meantime.

The write handler sees the stale frontmatter as "the user's intended property values" and overwrites the current values, silently reverting the other user's change. This is a classic lost-update problem, but it is invisible because it happens through a side channel (file save) rather than an explicit property edit.

**How to avoid:**
1. Include a version/ETag in the frontmatter (e.g., `# etag: abc123`). On write, compare the ETag against the current object version. If they differ, reject the write with `412 Precondition Failed` (HTTP) or `409 Conflict` (WebDAV).
2. Alternatively: make frontmatter writes opt-in per MountSpec configuration. Default behavior: frontmatter is read-only (informational). Users who want bidirectional frontmatter sync must explicitly enable it in their MountSpec, with a warning about conflict risks.
3. If bidirectional sync is enabled without ETags: at minimum, compare the incoming frontmatter values against the current state. Only write properties that actually changed (diff-then-patch). This prevents "echoing back stale values" from causing overwrites when only the body changed.

**Warning signs:**
- Properties reverting to old values after saving a file in a text editor
- Event log shows `object.patch` events from VFS writes that the user did not intend

**Phase to address:**
User Custom VFS (SHACL frontmatter writes). The ETag or diff-then-patch approach must be designed before implementing bidirectional frontmatter.

---

### Pitfall 10: Named Queries as Views Bypass ViewSpec Cache and Authorization

**What goes wrong:**
When saved SPARQL queries are exposed as "views" (named queries as views), they enter the same rendering pipeline as Mental Model-defined ViewSpecs. But ViewSpecs have a server-side TTL cache (`ViewSpecService`, 300s TTL, 64 max entries) that caches query results. If named query views are also cached, a user who creates a query and then changes the underlying data will see stale results for up to 5 minutes. If named query views are NOT cached, they bypass the cache and hit RDF4J directly on every load, creating an inconsistency where model views are fast (cached) and user views are slow (uncached).

Additionally, ViewSpecs are scoped to the current graph via `scope_to_current_graph()`. Named queries from users may already have their own `FROM` clauses. If the named query is wrapped in the ViewSpec pipeline, double-scoping may occur (injecting `FROM <urn:sempkm:current>` into a query that already has `FROM <urn:sempkm:current>`, which is harmless, or into a query with a different `FROM`, which breaks it).

**How to avoid:**
1. Named query views should use a SEPARATE cache from model ViewSpecs. Use a shorter TTL (60s) and a per-user cache key (since different users may have different SPARQL permissions).
2. Before executing a named query as a view, apply the same scoping pipeline as regular SPARQL queries. If the query already contains `FROM` clauses, respect them only if the user has permission -- otherwise strip and re-inject.
3. Add an explicit "refresh" action in the view UI so users can bypass the cache when needed.

**Warning signs:**
- Named query views showing stale data after edits
- Named query views significantly slower than model-defined views
- Queries with custom `FROM` clauses returning unexpected results when used as views

**Phase to address:**
SPARQL Interface (named queries as views). Design the caching strategy alongside the view rendering integration.

---

### Pitfall 11: Object Browser Multi-Select Delete Races with Event Sourcing

**What goes wrong:**
Multi-select delete in the object browser sends one delete command per selected object. With 20 objects selected, 20 `EventStore.commit()` calls execute. Each commit begins an RDF4J transaction, writes an event graph, materializes deletes, and commits. If two transactions attempt to delete the same triple (e.g., a shared edge), one succeeds and the other fails with a conflict. The user sees a partial deletion: 18 of 20 objects deleted, 2 failed silently or with cryptic errors.

**How to avoid:**
Batch multi-select operations into a SINGLE `EventStore.commit()` call with multiple `Operation` instances. The `commit()` method already supports `operations: list[Operation]` -- use it. This ensures all deletes are atomic: either all succeed or all fail.

Limit batch size to prevent excessively long transactions: cap at 50 objects per batch. For larger selections, chunk into 50-object batches with a progress indicator.

**Warning signs:**
- Multi-select delete leaves some objects un-deleted with no clear error
- Event log shows multiple delete events instead of one batch event
- RDF4J logs show transaction conflict errors during bulk operations

**Phase to address:**
Object Browser UI Improvements (multi-select). Use the existing batch commit API from day one.

---

## Minor Pitfalls

### Pitfall 12: Server-Side SPARQL History Grows Unbounded

**What goes wrong:**
Moving SPARQL query history from localStorage to server-side storage (SQLite) without a retention policy means every query every user runs is stored forever. A power user running 50 queries/day accumulates 18,000 rows/year. With query text averaging 500 bytes, this is modest storage-wise but causes UI performance issues: loading "all history" into the history panel becomes slow, and search/filter over unbounded history adds latency.

**How to avoid:**
- Default retention: keep last 500 queries per user, auto-prune oldest on insert
- Add a "pinned" flag so users can mark important queries that survive pruning
- Paginate the history UI: show last 20 queries initially, load more on scroll
- Add a "clear history" button for users who want a fresh start

**Phase to address:**
SPARQL Interface (server-side history). Set the retention policy in the initial migration, not as a follow-up.

---

### Pitfall 13: Edge Inspector Panel Causes N+1 SPARQL Queries

**What goes wrong:**
An edge inspector that shows edge details (source, target, type, properties, provenance) for each edge in the relations panel fires one SPARQL query per edge. An object with 30 relations triggers 30 queries when the edge inspector is opened. Each query is a round-trip through the API to RDF4J.

**How to avoid:**
Fetch all edge details for an object in a single SPARQL query using `VALUES` or a `CONSTRUCT` pattern that returns the full edge subgraph. Parse the results client-side. The relations panel already loads edge data -- extend that query to include the additional fields the inspector needs, rather than adding a separate query per edge.

**Phase to address:**
Object Browser UI Improvements (edge inspector). Design the query as an extension of the existing relations query.

---

### Pitfall 14: VFS Browser Breadcrumb Navigation Breaks with URL-Encoded IRIs

**What goes wrong:**
VFS paths contain model IDs and type labels that may include characters requiring URL encoding. Breadcrumb navigation builds clickable segments from the path. If the path is `/basic-pkm/People/Alice%20Smith.md`, naive breadcrumb splitting on `/` produces correct segments. But if a MountSpec strategy uses IRI fragments in paths (e.g., a flat strategy with `https%3A%2F%2F...` encoded IRIs), the breadcrumb splits on the encoded slashes, producing nonsensical segments.

**How to avoid:**
Breadcrumbs should be built from the MountSpec hierarchy metadata (model > strategy > category > file), NOT by splitting the URL path. Each level of the hierarchy knows its own label and path -- compose breadcrumbs from that data structure, not from string manipulation.

**Phase to address:**
VFS Browser UX Polish (breadcrumbs). Use the hierarchy metadata from the MountSpec, not the raw URL path.

---

### Pitfall 15: Spatial Canvas Performance Degrades with Many Nodes

**What goes wrong:**
The spatial canvas uses Cytoscape.js for rendering. As the number of nodes on a canvas grows beyond ~200, layout computations and re-renders become sluggish. Adding features like per-node expand/delete controls (already shipped in v2.5) adds DOM elements per node. If v2.6 adds more interactive features (inline editing, hover cards), each additional DOM element per node multiplies the performance impact.

**How to avoid:**
- Use Cytoscape's `cy.batch()` for bulk DOM operations
- Implement virtual rendering: only render nodes visible in the current viewport
- Cap the default node count at 150 with a "load more" mechanism
- Profile with Chrome DevTools Performance tab before adding new per-node UI elements

**Phase to address:**
Spatial Canvas UI Improvements. Profile the current state before adding features.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| SPARQL Permissions | `all_graphs` bypass available to all users (Pitfall 1) | Gate behind owner role immediately; proxy via RDF4J dataset params |
| SPARQL Autocomplete | Per-keystroke schema queries flood triplestore (Pitfall 6) | Precompute schema cache; serve as static JSON |
| SPARQL IRI Pills | Non-object IRIs open broken tabs (Pitfall 7) | Classify IRIs before rendering; batch lookup |
| SPARQL History | Unbounded storage growth (Pitfall 12) | 500-per-user retention limit from day one |
| SPARQL Saved/Shared Queries | Permission escalation via shared queries (Pitfall 5) | Never store execution params; always scope at runtime |
| SPARQL Named Query Views | Cache inconsistency and double-scoping (Pitfall 10) | Separate cache; strip and re-inject FROM clauses |
| RDF Patch Sync | Ghost triples bypass event store (Pitfall 2) | Translate patches to Command API operations |
| LDN Notifications | Open inbox becomes spam vector (Pitfall 8) | Rate limit + payload validation + async processing |
| Federated WebID Auth | Untrusted remote WebID documents (Pitfall 4) | Trusted instance allowlist; SSRF protection; prefer IndieAuth |
| MountSpec Strategies | Write conflicts from multi-path aliasing (Pitfall 3) | One canonical writable path; others read-only |
| SHACL Frontmatter Writes | Lost updates from stale frontmatter (Pitfall 9) | ETag or diff-then-patch; opt-in bidirectional sync |
| Object Multi-Select | Race conditions on batch delete (Pitfall 11) | Single EventStore.commit() with multiple Operations |
| Edge Inspector | N+1 SPARQL queries (Pitfall 13) | Single CONSTRUCT query for all edges |
| VFS Breadcrumbs | URL-encoded IRIs break path splitting (Pitfall 14) | Build from hierarchy metadata, not path strings |
| Spatial Canvas UX | DOM bloat per node (Pitfall 15) | Profile before adding features; cap node count |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SPARQL permissions + Yasgui | Yasgui sends queries directly to triplestore URL | All queries MUST route through `/api/sparql` proxy (which enforces scoping); configure Yasgui's endpoint to point at the proxy, never at RDF4J directly |
| RDF Patch + Event Store | Applying patches as raw SPARQL UPDATE | Translate patches to Command API operations; let EventStore handle materialization |
| MountSpec + wsgidav locks | Assuming path-based locks protect the object | Implement IRI-based lock mapping or make non-canonical paths read-only |
| LDN + federation sync | Processing notifications synchronously in the HTTP handler | Store in queue, process async; rate limit the inbox |
| WebID auth + SSRF | Fetching arbitrary URLs during auth without filtering | Block private IPs, localhost, link-local; strict timeouts; no redirects |
| Named queries + ViewSpec cache | Sharing the same cache between model views and user queries | Separate caches with different TTLs and per-user keys |
| Multi-select + EventStore | Sending one commit per selected object | Batch into single commit with multiple Operations |
| Autocomplete + RDF4J | Firing SPARQL query per keystroke for schema suggestions | Precompute schema JSON; filter client-side |
| Frontmatter write-back + concurrent edits | Echoing stale frontmatter values as intended edits | ETag comparison or diff-then-patch on write |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-keystroke autocomplete SPARQL | UI lag, triplestore load spikes | Cached schema JSON endpoint | Immediately with >10 properties |
| N+1 edge inspector queries | Edge inspector takes 5-10s to populate | Single CONSTRUCT query for all edges | Objects with >10 edges |
| Unbounded query history | History panel load time > 2s | 500-per-user cap, pagination | After ~1 month of active use |
| Per-IRI classification for pills | SPARQL result rendering slow for large result sets | Batch VALUES query for all unique IRIs | Result sets with >50 IRIs |
| LDN notification flood | Storage growth, async worker saturation | Rate limit (10/min/IP), payload validation | Immediately if inbox URL is discovered |
| Sync patch application bypassing event store | Event log out of sync, cannot undo | Translate to Command API | First sync operation |
| Canvas DOM elements per node | Layout janky above 200 nodes | Virtual rendering, node count cap | Canvas sessions with many nodes |

---

## "Looks Done But Isn't" Checklist

- [ ] **SPARQL permissions**: `all_graphs=true` rejects non-owner users (not just scoping -- actual 403)
- [ ] **SPARQL permissions**: `GRAPH ?g { ... }` query patterns do not return event graph IRIs for non-owner users
- [ ] **SPARQL autocomplete**: typing in the editor does not fire SPARQL queries (check DevTools network tab)
- [ ] **SPARQL IRI pills**: clicking a class/property IRI in results does NOT open an object tab (opens schema popover or external link instead)
- [ ] **SPARQL saved queries**: a guest running an admin's shared query gets scoped results, not admin-level access
- [ ] **RDF Patch sync**: every synced change appears in the event log with provenance
- [ ] **RDF Patch sync**: synced objects pass SHACL validation (or show violations in lint dashboard)
- [ ] **LDN inbox**: 100 rapid POST requests from the same IP result in 429 responses, not 100 stored notifications
- [ ] **WebID federation**: WebID from a non-trusted instance is rejected with clear error message
- [ ] **WebID federation**: WebID fetch does not follow redirects to private IPs (SSRF test)
- [ ] **MountSpec multi-strategy**: editing a file via a non-canonical path returns 403, not silent overwrite
- [ ] **SHACL frontmatter**: saving a file with stale frontmatter returns 409/412, not silent property reversion
- [ ] **Multi-select delete**: selecting 20 objects and deleting produces exactly 1 event in the event log
- [ ] **Edge inspector**: opening the inspector on an object with 30 edges fires exactly 1 SPARQL query (check DevTools)
- [ ] **Named query views**: editing an object and immediately viewing via named query shows updated data (cache freshness)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SPARQL `all_graphs` bypass | LOW | Add `require_role("owner")` check; one-line fix |
| Ghost triples from raw sync | HIGH | Must identify all ghost triples (no event provenance), delete from current graph, and either re-sync through event store or accept data loss |
| MountSpec write conflicts | MEDIUM | Compare event log for competing writes; manually resolve conflicting property values; make non-canonical paths read-only |
| Spoofed WebID authentication | HIGH | Audit all actions performed by the spoofed identity; revoke access; implement trusted instance allowlist; notify affected users |
| Stale frontmatter overwrites | MEDIUM | Use event log to identify VFS-originated property changes; compensating events to restore correct values |
| Spam LDN notifications | LOW | Bulk-delete notifications from untrusted sources; add rate limiting |
| Unbounded query history | LOW | Run `DELETE FROM sparql_history WHERE id NOT IN (SELECT id FROM sparql_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 500)` per user |
| N+1 edge queries | LOW | Replace per-edge queries with single CONSTRUCT; no data migration needed |
| IRI pills opening broken tabs | LOW | Add classification logic; no data migration needed |

---

## Sources

- [RDF Patch specification](https://afs.github.io/rdf-patch/) -- ADD/DELETE operation format; HIGH confidence
- [RDF Patch (Apache Jena)](https://afs.github.io/rdf-delta/rdf-patch.html) -- format details, blank node handling; HIGH confidence
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/) -- inbox protocol, security considerations; HIGH confidence
- [Stardog Named Graph Security](https://docs.stardog.com/operating-stardog/security/named-graph-security) -- silent graph filtering pitfall, write permission enforcement; HIGH confidence (conceptual patterns apply to any triplestore)
- [GraphDB Quad-based Access Control](https://graphdb.ontotext.com/documentation/10.5/quad-based-access-control.html) -- fine-grained statement-level access patterns; HIGH confidence
- [Virtuoso SPARQL Security](https://docs.openlinksw.com/virtuoso/rdfgraphsecurityunddefperm/) -- default permission risks, anonymous SPARQL access; HIGH confidence
- [SPARQL Autocomplete on Large Knowledge Graphs](https://dl.acm.org/doi/10.1145/3511808.3557093) -- per-request query overhead, Qlever approach; MEDIUM confidence
- [Lightweight SPARQL Editor with Autocomplete](https://arxiv.org/html/2503.02688v1) -- metadata-driven approach, YASGUI limitations; MEDIUM confidence
- [SIB Swiss SPARQL Editor](https://www.npmjs.com/package/@sib-swiss/sparql-editor) -- implementation patterns; MEDIUM confidence
- [WsgiDAV Virtual DAV Provider](https://wsgidav.readthedocs.io/en/maintain_1.x/_generated/wsgidav.samples.virtual_dav_provider.html) -- multi-path aliasing, real vs virtual paths; HIGH confidence
- [WsgiDAV Documentation](https://wsgidav.readthedocs.io/) -- provider architecture, lock management; HIGH confidence
- [WebID-TLS Specification](https://dvcs.w3.org/hg/WebID/raw-file/tip/spec/tls-respec.html) -- trust model, certificate-based identity; MEDIUM confidence
- [Solid WebID authentication discussion](https://github.com/solid/solid/issues/22) -- WebID-TLS limitations, HTTP Signatures alternative; MEDIUM confidence
- [RDF4J REST API](https://rdf4j.org/documentation/reference/rest-api/) -- dataset parameters, default-graph-uri, named-graph-uri; HIGH confidence
- [RDF4J DROP GRAPH bug #1548](https://github.com/eclipse/rdf4j/issues/1548) -- DROP GRAPH on non-existing graph deletes all graphs; HIGH confidence
- SemPKM codebase analysis: `sparql/router.py`, `sparql/client.py`, `events/store.py`, `vfs/provider.py`, `vfs/write.py`, `auth/dependencies.py`, `auth/models.py` -- direct inspection; HIGH confidence

---
*Pitfalls research for: v2.6 Power User & Collaboration (SemPKM)*
*Researched: 2026-03-09*
