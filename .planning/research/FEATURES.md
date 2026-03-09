# Feature Landscape: v2.6 Power User & Collaboration

**Domain:** Semantic PKM platform -- SPARQL power tools, RDF federation/sync, custom VFS projections, UI polish
**Researched:** 2026-03-09
**Overall confidence:** MEDIUM (standards well-documented; integration complexity with existing SemPKM architecture requires validation)

---

## Scope

This file covers the **new features planned for v2.6**. Eight feature areas organized into three tiers: table stakes (expected by power users of semantic tools), differentiators (rare in PKM space), and anti-features (scope to avoid).

Feature areas:
1. SPARQL Interface enhancements (permissions, autocomplete, IRI pills, history, saved/shared queries, named queries as views)
2. Collaboration & Federation (RDF Patch, named graph sync, LDN notifications, federated WebID auth, collaboration UI)
3. User Custom VFS (MountSpec vocabulary, directory strategies, SHACL writes, management UI)
4. VFS Browser UX Polish
5. Object Browser UI Improvements
6. Event Log Fixes
7. Lint Dashboard Fixes
8. Spatial Canvas UI Improvements

---

## Table Stakes

Features power users of semantic/knowledge tools expect. Missing these makes the existing features feel half-finished.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| SPARQL role-based permissions | Every multi-user triplestore (GraphDB, Stardog, Virtuoso) gates SPARQL by role. Current SemPKM requires `get_current_user` but all authenticated users get identical access. Guests running arbitrary SPARQL is a data leak. | LOW | Existing RBAC (owner/member/guest roles) | Restrict `all_graphs` to owner. Guest = read-only, no `all_graphs`. Member = read current graph. Owner = full access. Query rewriting already exists in `sparql/client.py`. |
| SPARQL server-side history | Yasgui stores history in localStorage -- lost on browser clear, not accessible across devices. GraphDB, Blazegraph Workbench, and Virtuoso all persist query history server-side. | LOW | SQLAlchemy auth DB for storage | Store query text + timestamp + user_id in SQL. API: GET/POST `/api/sparql/history`. Cap at 100 per user with FIFO eviction. |
| SPARQL saved queries | GraphDB, Stardog Studio, and QLever UI all let users save and name queries. Power users accumulate a library of useful queries. Without save, they paste into text files. | MEDIUM | Server-side history (above) | SQL table: id, user_id, name, query, description, is_shared, created_at. CRUD API. Yasgui tab integration or sidebar list. |
| SPARQL IRI pill links in results | Already partially implemented (SPARQL-02 in v2.2) -- results display IRIs as clickable pill links. Needs polish: resolve labels, show type icon, open in workspace tab. | LOW | Label service, icon service | Enhance existing YASR custom renderer. Fetch labels via batch `/api/labels` endpoint. |
| VFS browser breadcrumbs | Every file browser (VS Code, Finder, Nautilus) has breadcrumb path navigation. Current VFS browser has tree-only navigation. | LOW | Existing VFS browser | Render clickable path segments above content pane. Click segment = navigate to that directory level. |
| VFS browser preview pane | VS Code, GitHub, and every modern file browser show file content alongside the tree. Current VFS browser opens files in CodeMirror tabs but lacks quick preview. | LOW | Existing VFS browser + CodeMirror | Render markdown preview in right pane on single-click; double-click opens editable tab. |
| Object browser refresh button | Users expect to manually refresh data views. Current nav tree has no refresh control. | LOW | Existing browser router | Add refresh icon button to nav tree header. Re-fetch `/browser/nav-tree` via htmx. |
| Object browser create (plus) button | Every object management UI has a "new" button in the object list. Current creation flow is command palette only. | LOW | Existing type picker + create flow | Plus icon in nav tree header. Click opens type picker, then create form. |
| Event log diff rendering fixes | Event log explorer shipped in v2.0 with known missing-diff and rendering issues. Users expect diffs to render for all operation types. | MEDIUM | Event query service | Investigate which operation types produce empty `before_values`. Fix SPARQL queries in `events/query.py` to extract before-state for patch operations. |
| Lint dashboard layout fixes | Dashboard shipped in v2.4 with layout width issues on narrow viewports. Walkthrough missing for new users. | LOW | Existing lint dashboard | CSS fixes for responsive width. Add Driver.js walkthrough step for lint panel. |

---

## Differentiators

Features that set SemPKM apart from other PKM tools. Not expected, but high value for the target audience.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| SPARQL ontology-aware autocomplete | SIB Swiss SPARQL Editor (2025) demonstrated context-aware autocomplete using VoID metadata. SemPKM has SHACL shapes and installed ontologies -- richer metadata than VoID. Autocomplete that knows "if subject is a `Note`, valid predicates are `dcterms:title`, `sempkm:body`..." is a genuine differentiator. | HIGH | SHACL shapes service, prefix registry | Two approaches: (1) Build VoID descriptions from installed models, serve to SIB editor web component. (2) Custom autocomplete endpoint that queries SHACL shapes for valid predicates given a subject class. Approach 2 is simpler for SemPKM since shapes are already parsed. Serve completions as JSON from `/api/sparql/completions?class=X`. |
| SPARQL named queries as views | Save a SPARQL query, give it a name, and it appears as a browsable "view" in the nav tree -- like a database view. No other PKM tool does this. Power users write custom reports and pin them. | HIGH | Saved queries (above), view spec service | Create a ViewSpec dynamically from a saved query. Renderer = table (default) or user-specified. Register in nav tree under "Custom Views" section. Requires view spec schema extension for user-defined views vs model-defined views. |
| SPARQL shared queries | Multi-user query sharing. Owner saves a query, marks it "shared", other users see it in their saved queries list. Collaboration primitive for teams exploring data together. | LOW | Saved queries with `is_shared` flag | Filter shared queries in list endpoint. Read-only for non-owners. |
| RDF Patch event serialization | SemPKM already has event-sourced writes as RDF named graphs. Serializing events as RDF Patch format (A/D operations) enables: export change logs, replay on another instance, incremental backup. The RDF Patch spec uses simple A (add) / D (delete) operations per triple -- maps directly onto SemPKM's `object.create`, `object.patch`, `body.set` events. | MEDIUM | Event store | New serializer: `events/patch.py`. Convert event named graph triples to RDF Patch text format. API endpoint: GET `/api/events/{id}/patch`. Bulk export: GET `/api/events/patches?since=timestamp`. |
| Named graph sync via RDF Patch log | RDF Delta pattern: maintain a patch log, remote instances pull patches they haven't seen. Enables offline-first sync between SemPKM instances. | HIGH | RDF Patch serialization (above) | Patch log = ordered sequence of patches with sequence numbers. API: GET `/api/sync/log?since=N`, POST `/api/sync/apply` (receive patches). Conflict resolution needed for concurrent edits -- last-writer-wins per subject IRI is simplest. |
| LDN inbox for cross-instance notifications | W3C Recommendation (stable spec). Resource advertises inbox via `Link: <inbox-url>; rel="http://www.w3.org/ns/ldp#inbox"`. Senders POST JSON-LD notifications. Enables: "Alice shared a concept with Bob's SemPKM instance." | MEDIUM | WebID profiles (already shipped) | New router: `/api/ldn/inbox`. Store notifications as RDF in dedicated named graph. Discovery: add `Link` header to WebID profile responses. Consume: list/read notifications in workspace UI. ActivityStreams 2.0 vocabulary for notification payloads. |
| Federated WebID authentication | Verify a remote WebID by dereferencing the profile document, checking the public key matches the request signature. Enables cross-instance identity without a central auth server. | HIGH | WebID profiles + Ed25519 keys (already shipped) | HTTP Signature verification: check `Authorization: Signature ...` header, dereference WebID URI, extract public key from RDF profile, verify signature. Python: `cryptography` library for Ed25519 verify. New middleware or dependency. |
| User Custom VFS (MountSpec) | Users define their own directory structures for the WebDAV mount. Current VFS is hardcoded: `/{model}/{type}/{object}.md`. A MountSpec lets users create custom "views" like `/by-date/2026/03/`, `/by-tag/philosophy/`, `/projects/active/`. | HIGH | Existing VFS provider | New RDF vocabulary: `sempkm:MountSpec`, `sempkm:DirectoryStrategy`, `sempkm:pathTemplate`. Five strategies: by-type (current), by-date, by-tag, by-property, flat. MountSpec stored as RDF in user's config graph. Provider dispatches to strategy based on path prefix. |
| MountSpec SHACL frontmatter writes | When user edits a `.md` file via WebDAV and changes frontmatter, parse YAML frontmatter and map keys back to RDF properties via SHACL shape definitions. Enables Obsidian-as-editor workflow. | HIGH | MountSpec (above), SHACL shapes service, VFS write path | Parse YAML frontmatter on `end_write`. Map keys to predicates using SHACL `sh:path` from the object's shape. Generate `object.patch` events for changed properties. Complex: must handle property types (literals, IRIs, dates), multi-valued properties, new vs changed vs deleted properties. |
| Multi-select in object browser | Select multiple objects for bulk operations (delete, tag, move). Standard in file managers and Notion databases, rare in PKM tools. | MEDIUM | Existing nav tree | Checkbox selection mode. Toolbar with bulk actions. Backend: batch delete endpoint. |
| Edge inspector panel | Click an edge in the graph view or relations panel, see its properties, provenance, and annotation. SemPKM has first-class edges (`sempkm:Edge`) -- this surfaces their metadata. | MEDIUM | Edge model, relations panel | New panel section or popover. Query edge IRI for properties. Show: created_by, created_at, edge type, annotations. |
| Spatial canvas UX improvements | Current canvas is a C0 prototype. Improvements: snap-to-grid, edge labels, minimap, keyboard navigation, group selection. | MEDIUM | Existing canvas.js | Incremental enhancements. Snap-to-grid is most impactful for usability. Edge labels require rendering text along SVG path. |

---

## Anti-Features

Features to explicitly NOT build in v2.6. Including rationale and what to do instead.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| SPARQL UPDATE as write surface | Bypasses event sourcing -- all writes must go through Command API to maintain immutable event log, provenance, and SHACL validation. Allowing SPARQL UPDATE creates two write paths with divergent guarantees. | Keep SPARQL read-only. Use Command API for all mutations. Document this as an intentional design constraint. |
| Real-time collaborative editing (CRDT/OT) | Enormous complexity (several person-years). SemPKM is self-hosted, typically single-user or small team. CRDT for RDF triples is an unsolved research problem. | Support async collaboration: saved/shared queries, LDN notifications for cross-instance sharing, named graph sync for eventual consistency. |
| Full ActivityPub federation | AP is designed for social media (follow, like, boost). PKM semantics don't map to AP's actor model cleanly. Implementation is massive (WebFinger, inbox forwarding, delivery, signatures). | Use LDN for targeted notifications between known instances. LDN is simpler, W3C Recommendation, and sufficient for "share a concept with Bob." |
| Full SOLID pod compatibility | SOLID's Web Access Control (WAC) and container model are extensive specs. Building full compliance is a multi-month effort that doesn't serve the core PKM use case. | Publish WebID profiles (already done). Support LDN inbox. These are the SOLID-adjacent features that provide value without full pod implementation. |
| Custom SPARQL UI replacing Yasgui | Yasgui is the de facto standard SPARQL editor. Building a custom one means maintaining syntax highlighting, validation, result rendering, and tab management. | Extend Yasgui with custom YASR plugins (for IRI pills) and a completion endpoint. Use Yasgui's plugin architecture rather than replacing it. |
| Bidirectional VFS sync | Full two-way sync between WebDAV and triplestore creates conflict resolution nightmares (which version wins? what about concurrent edits?). | Support one-way write (WebDAV -> triplestore via frontmatter parsing) with conflict detection (reject if object modified since last read). One-way is the Obsidian vault import pattern and what users expect. |
| Complex permission model for SPARQL | Row-level security, per-graph ACLs, query rewriting proxies (mu-authorization pattern). Overkill for self-hosted small-team PKM. | Simple role-based gating: guest = no SPARQL, member = current graph only, owner = all graphs. Three levels, no per-graph ACLs. |

---

## Feature Dependencies

```
SPARQL Permissions ──────────────────────────> (standalone, no deps)
SPARQL Server-side History ──────────────────> (standalone, needs SQL migration)
SPARQL Saved Queries ────────────────────────> depends on: Server-side History
SPARQL Shared Queries ───────────────────────> depends on: Saved Queries
SPARQL Named Queries as Views ───────────────> depends on: Saved Queries + ViewSpec service
SPARQL IRI Pill Enhancement ─────────────────> depends on: Label service batch endpoint
SPARQL Ontology-Aware Autocomplete ──────────> depends on: SHACL shapes service (exists)

RDF Patch Serialization ─────────────────────> depends on: Event store (exists)
Named Graph Sync ────────────────────────────> depends on: RDF Patch Serialization
LDN Inbox ───────────────────────────────────> depends on: WebID profiles (exists)
Federated WebID Auth ────────────────────────> depends on: WebID profiles + LDN Inbox
Collaboration UI ────────────────────────────> depends on: LDN Inbox + Shared Queries

MountSpec Vocabulary ────────────────────────> (standalone RDF vocabulary definition)
Directory Strategies ────────────────────────> depends on: MountSpec Vocabulary + existing VFS provider
SHACL Frontmatter Writes ────────────────────> depends on: Directory Strategies + SHACL shapes service
MountSpec Management UI ─────────────────────> depends on: MountSpec Vocabulary + Directory Strategies

VFS Browser Polish ──────────────────────────> depends on: existing VFS browser (exists)
Object Browser Improvements ─────────────────> depends on: existing browser router (exists)
Event Log Fixes ─────────────────────────────> depends on: existing event query service (exists)
Lint Dashboard Fixes ────────────────────────> depends on: existing lint service (exists)
Spatial Canvas Improvements ─────────────────> depends on: existing canvas.js (exists)
```

---

## MVP Recommendation

### Phase 1 -- SPARQL Power Tools (ship first)
Highest value-to-effort ratio. All build on existing infrastructure.

1. **SPARQL permissions** -- LOW effort, closes a security gap
2. **SPARQL server-side history** -- LOW effort, SQL migration + simple API
3. **SPARQL saved queries** -- MEDIUM effort, unlocks sharing and named views
4. **SPARQL IRI pill enhancement** -- LOW effort, polish existing feature

### Phase 2 -- UI Fixes & Object Browser
Clears tech debt before adding new UI features.

5. **Event log diff fixes** -- MEDIUM effort, clears known bugs
6. **Lint dashboard fixes** -- LOW effort, CSS + walkthrough
7. **Object browser refresh/plus icons** -- LOW effort, high UX impact
8. **VFS browser breadcrumbs + preview** -- LOW effort, standard patterns

### Phase 3 -- VFS & MountSpec
Build custom VFS after fixing the browser UX.

9. **MountSpec vocabulary** -- MEDIUM effort, RDF vocabulary design
10. **Directory strategies** -- HIGH effort, 5 strategy implementations
11. **SHACL frontmatter writes** -- HIGH effort, complex parsing + mapping
12. **MountSpec management UI** -- MEDIUM effort, settings page extension

### Phase 4 -- Autocomplete & Named Views
Most complex SPARQL features. Needs SHACL shapes metadata.

13. **SPARQL ontology-aware autocomplete** -- HIGH effort, new endpoint + Yasgui integration
14. **SPARQL named queries as views** -- HIGH effort, ViewSpec extension
15. **SPARQL shared queries** -- LOW effort (if saved queries exist)

### Phase 5 -- Federation & Collaboration
Most novel features. Highest risk, lowest urgency for single-user deployments.

16. **RDF Patch serialization** -- MEDIUM effort, new serializer
17. **LDN inbox** -- MEDIUM effort, new router + notification store
18. **Named graph sync** -- HIGH effort, sync protocol + conflict resolution
19. **Federated WebID auth** -- HIGH effort, cryptographic verification
20. **Collaboration UI** -- MEDIUM effort, notification panel + sharing flows

### Phase 6 -- Canvas & Multi-select
Polish features, lower priority.

21. **Spatial canvas improvements** -- MEDIUM effort, incremental UX
22. **Multi-select in object browser** -- MEDIUM effort, new selection mode
23. **Edge inspector** -- MEDIUM effort, new panel component

**Defer to v2.7+:**
- MountSpec SHACL frontmatter writes (complex, depends on MountSpec being validated first)
- Named graph sync (needs RDF Patch to be proven first)
- Federated WebID auth (needs LDN inbox to be proven first)

---

## Complexity Assessment

| Feature Area | Effort | Risk | Notes |
|-------------|--------|------|-------|
| SPARQL permissions | LOW | LOW | Straightforward role check on existing endpoint |
| SPARQL history/saved | LOW-MEDIUM | LOW | Standard CRUD, SQL migration |
| SPARQL autocomplete | HIGH | MEDIUM | Need to design completion metadata extraction from SHACL shapes; Yasgui integration may need custom CodeMirror extension |
| SPARQL named views | HIGH | MEDIUM | ViewSpec schema needs extension for user-defined vs model-defined views |
| RDF Patch | MEDIUM | LOW | Well-defined spec, SemPKM events map cleanly to A/D operations |
| Named graph sync | HIGH | HIGH | Conflict resolution is the hard part; last-writer-wins may lose data |
| LDN inbox | MEDIUM | LOW | W3C Recommendation, well-specified protocol |
| Federated WebID | HIGH | HIGH | HTTP Signatures are fiddly; WebID-TLS is deprecated, HTTP Signatures not fully standardized |
| MountSpec vocabulary | MEDIUM | MEDIUM | RDF vocabulary design requires iteration; 5 strategies are ambitious |
| MountSpec SHACL writes | HIGH | HIGH | YAML-to-RDF mapping through SHACL shapes is novel; edge cases (multi-value, IRI refs) are complex |
| UI fixes (event log, lint, browser) | LOW-MEDIUM | LOW | Known bugs, standard patterns |
| Spatial canvas | MEDIUM | LOW | Incremental improvements to existing code |

---

## Sources

- [RDF Patch specification](https://afs.github.io/rdf-patch/) -- Format for recording changes to RDF datasets
- [RDF Delta](https://afs.github.io/rdf-delta/) -- System for synchronizing RDF datasets via patch logs
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/) -- W3C Recommendation for decentralized notification protocol
- [SIB Swiss SPARQL Editor](https://github.com/sib-swiss/sparql-editor) -- Context-aware SPARQL autocomplete using VoID/SHACL metadata
- [A user-friendly SPARQL query editor (2025)](https://arxiv.org/abs/2503.02688) -- Academic paper on SPARQL autocomplete approaches
- [GraphDB saved queries](https://graphdb.ontotext.com/documentation/11.2/sparql-queries.html) -- Reference implementation for saved/shared SPARQL queries
- [mu-authorization SPARQL proxy](https://github.com/mu-semtech/mu-authorization) -- Query rewriting authorization for SPARQL endpoints
- [Yasgui documentation (Triply)](https://docs.triply.cc/yasgui/) -- Official Yasgui features and customization
- [RGS system for RDF sync (AAMAS 2024)](https://www.ifaamas.org/Proceedings/aamas2024/pdfs/p2827.pdf) -- RDF graph synchronization with merge/rebase
