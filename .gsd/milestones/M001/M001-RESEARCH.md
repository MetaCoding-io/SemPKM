# Research Summary: SemPKM v2.6 Power User & Collaboration

**Domain:** Semantic PKM platform -- SPARQL power tools, RDF federation/sync, custom VFS, UI improvements
**Researched:** 2026-03-09
**Overall confidence:** MEDIUM (SPARQL/VFS/UI work HIGH; federation protocol integration MEDIUM)

## Executive Summary

SemPKM v2.6 targets eight feature areas across five capability domains: SPARQL Interface enhancements, Collaboration & Federation, User Custom VFS (MountSpec), UI polish, and bug fixes. The existing three-layer architecture (htmx frontend / FastAPI backend / RDF4J triplestore) accommodates all new features without structural changes and without any new dependencies.

The SPARQL Interface enhancements are the highest-value, lowest-risk work. Permission enforcement is a simple guard layer on the existing `sparql/router.py` -- the `all_graphs` bypass must be gated behind `require_role("owner")` immediately (currently any authenticated user can access event data). Autocomplete requires a cached schema endpoint that Yasgui's custom completer queries once on init, avoiding per-keystroke SPARQL queries that would flood RDF4J. Server-side history and saved queries use SQL tables (high-churn CRUD data, not knowledge), requiring Alembic migrations. The killer differentiator is "named queries as views" -- promoting a saved SPARQL query to a ViewSpec alongside model-defined views.

Federation is the highest-complexity, highest-risk domain. RDF Patch serialization maps cleanly onto the existing EventStore's `Operation` dataclass (which already has `materialize_inserts` and `materialize_deletes` lists). The critical constraint: all federation writes MUST go through `EventStore.commit()` to preserve the audit trail, trigger SHACL validation, and fire webhooks. Sync requires infinite-loop prevention via `syncSource` tagging on federation-originated events. LDN provides standards-based notification exchange with rate limiting and peer authentication to prevent inbox spam.

User Custom VFS (MountSpec) extends the current fixed `/{model}/{type}/{object}.md` hierarchy with five user-defined directory strategies (ByType, ByDate, ByProperty, Flat, ByTag). The main architectural risk is multi-path aliasing: the same object appearing at multiple paths across strategies creates write conflicts. Solution: exactly one strategy per mount is writable (canonical path); others are read-only aliases.

No new Python or JavaScript dependencies are required. Three new SQL tables via Alembic. Four new triplestore named graph patterns. All UI improvements are htmx + vanilla JS + CSS.

## Key Findings

**Stack:** Zero new dependencies. All features build on existing rdflib, httpx, cryptography, SQLAlchemy, wsgidav, Yasgui CDN. Three SQL tables (sparql_query_history, saved_sparql_queries, federation_peers). Four new named graph patterns (user views, user mounts, sync conflicts, LDN inbox).

**Architecture:** New `federation/` package (4 modules: patch, sync, ldn, auth). Extended `sparql/` module (autocomplete, history, saved queries). Extended `vfs/` module (mounts, strategies, SHACL frontmatter writes). All other changes are modifications to existing modules.

**Critical pitfalls:**
1. `all_graphs=true` bypass available to all users -- gate behind owner role immediately (one-line fix)
2. Federation sync MUST go through EventStore -- bypassing creates ghost triples with no audit trail
3. MountSpec multi-path aliasing -- designate one canonical writable path per mount; others read-only
4. WebID federation trusts self-asserted documents -- require explicit trusted instance allowlist
5. SPARQL saved queries execute with runner's permissions -- never store execution params in saved queries

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Bug Fixes & Security** - SPARQL permissions, event log fixes, lint dashboard fixes
   - Addresses: Security gap (all_graphs bypass), known regressions
   - Avoids: Shipping new features on broken foundations

2. **SPARQL Power User** - Autocomplete, server-side history, saved queries, IRI pills enhancement
   - Addresses: Core SPARQL Interface table stakes
   - Avoids: Pitfall 6 (autocomplete flooding) via cached schema endpoint

3. **SPARQL Advanced** - Named queries as views, shared queries
   - Addresses: Key differentiators, foundation for collaboration
   - Avoids: Pitfall 5 (permission escalation via shared queries), Pitfall 10 (view cache inconsistency)

4. **Object Browser & VFS Browser UI** - Refresh/plus icons, multi-select, edge inspector, view filtering, breadcrumbs, preview pane
   - Addresses: Daily workflow friction, VFS browser completeness
   - Avoids: Pitfall 11 (multi-select race conditions) via single EventStore.commit()

5. **VFS MountSpec** - Vocabulary, service, strategies, SHACL frontmatter writes, management UI
   - Addresses: User custom VFS, markdown editor integration
   - Avoids: Pitfall 3 (multi-path aliasing) via canonical-path-is-writable rule

6. **Spatial Canvas UX** - Improvements TBD during phase planning
   - Addresses: Canvas usability
   - Avoids: Isolated module, low cross-cutting risk

7. **Federation** - RDF Patch serializer, federation auth, sync engine, LDN inbox/sender, collaboration UI
   - Addresses: Multi-instance collaboration
   - Avoids: Pitfall 2 (event store bypass) via mandatory EventStore.commit(), Pitfall 4 (WebID trust) via allowlist

**Phase ordering rationale:**
- Security and bug fixes first (group 1) establishes correctness before new features
- SPARQL enhancements (groups 2-3) before federation because shared queries are a prerequisite for meaningful collaboration, and these features have the best value-to-risk ratio
- UI improvements (group 4) can proceed in parallel with MountSpec backend work
- VFS MountSpec (group 5) before federation because it is user-facing with lower risk
- Federation last (group 7) because it has the highest complexity, the lowest urgency for personal-first deployments, and depends on WebID infrastructure already shipped in v2.5

**Research flags for phases:**
- Phase 7 (Federation): Needs deeper research on HTTP Signatures (RFC 9421) implementation in Python and sync conflict resolution UX
- Phase 5 (MountSpec): Needs careful design of path template grammar, sanitization rules, and SHACL-to-frontmatter reverse mapping completeness
- Phase 3 (Named Queries as Views): Needs design for ViewSpec cache separation (user views vs model views)
- Phases 1-2, 4, 6: Standard patterns, unlikely to need additional research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps; existing tools cover all needs; verified via codebase analysis |
| SPARQL Features | HIGH | Direct extension of existing sparql/ module; well-understood patterns |
| Object Browser UI | HIGH | Template/CSS/JS changes with clear scope and existing patterns |
| VFS MountSpec | MEDIUM | wsgidav collection subclass pattern is proven; directory strategy design and SHACL reverse mapping need validation |
| Federation | MEDIUM | No prior federation art in codebase; HTTP Signatures and sync loop prevention need implementation validation |
| Event Log/Lint Fixes | HIGH | Template-level fixes with identifiable bugs |

## Gaps to Address

- HTTP Signatures (RFC 9421) implementation details for Python -- validate Ed25519 signing/verification flow with httpx
- Yasgui custom autocompleter API specifics for @zazuko/yasgui v4.5.0 -- verify CDN version's completer registration method
- RDF Patch format edge cases -- blank nodes, language-tagged literals, named graph patches in rdflib serializer vs manual generation
- Sync conflict resolution UX -- how to present and resolve last-writer-wins conflicts in the collaboration UI
- SHACL frontmatter reverse mapping -- which SHACL constraints meaningfully map to YAML frontmatter keys; multi-valued properties, IRI references, typed literals
- MountSpec path template sanitization -- grammar for template variables, path traversal prevention, filename collision handling

## Sources

- `.planning/PROJECT.md` -- v2.6 milestone definition and constraints
- `.planning/research/STACK.md` -- technology stack analysis (zero new deps confirmed)
- `.planning/research/FEATURES.md` -- feature landscape with 11 table stakes, 12 differentiators, 7 anti-features
- `.planning/research/PITFALLS.md` -- 15 domain pitfalls with prevention strategies
- `.planning/research/ARCHITECTURE.md` -- integration architecture with component boundaries and data flows
- [RDF Patch specification](https://afs.github.io/rdf-patch/)
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/)
- [Yasgui documentation (Triply)](https://docs.triply.cc/yasgui/)
- [W3C Linked Data Patch Format](https://www.w3.org/TR/ldpatch/)

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*

# Architecture Research: SemPKM v2.6 Power User & Collaboration

**Domain:** Integration architecture for SPARQL permissions, RDF Patch sync, LDN notifications, MountSpec VFS, and UI improvements
**Researched:** 2026-03-09
**Confidence:** MEDIUM (existing codebase analysis HIGH; federation/LDN protocol details MEDIUM; no prior art in this codebase for multi-instance sync)

---

## System Overview

v2.6 adds five major capability domains to the existing three-layer architecture. The diagram below shows new components (marked NEW) and modified components (marked MOD) alongside existing infrastructure:

```
+-----------------------------------------------------------------------------------+
|                        Browser (htmx + vanilla JS)                                |
|                                                                                   |
|  Yasgui (MOD)              workspace.js (MOD)        vfs-browser.js (MOD)        |
|  +-------------------+    +------------------+       +---------------------+      |
|  | Autocomplete API  |    | Multi-select     |       | MountSpec UI        |      |
|  | IRI pill renderer |    | Edge inspector   |       | Breadcrumbs         |      |
|  | Server-side hist  |    | Refresh/plus btns|       | Preview pane        |      |
|  +-------------------+    +------------------+       +---------------------+      |
|                                                                                   |
|  sparql-console.js (MOD)  collaboration-ui.js (NEW)  canvas.js (MOD)             |
|  +-------------------+    +------------------+       +---------------------+      |
|  | Saved queries UI  |    | Remote instance  |       | UX improvements     |      |
|  | Share query links |    | Sync status      |       +---------------------+      |
|  | Named query→view  |    | Conflict display |                                   |
|  +-------------------+    +------------------+                                    |
+-----------------------------------------------------------------------------------+
                                    | htmx.ajax / fetch / SSE
+-----------------------------------------------------------------------------------+
|                        FastAPI Backend                                             |
|                                                                                   |
|  sparql/ (MOD)             federation/ (NEW)          vfs/ (MOD)                  |
|  +-------------------+    +------------------+       +---------------------+      |
|  | PermissionsGuard  |    | RDFPatchService  |       | MountSpecService    |      |
|  | /api/sparql/hist  |    | LDNInbox         |       | 5 dir strategies    |      |
|  | /api/sparql/saved |    | LDNSender        |       | SHACL frontmatter   |      |
|  | /api/sparql/auto  |    | SyncEngine       |       |   write path        |      |
|  +-------------------+    | WebIDAuthN       |       | /api/vfs/mounts     |      |
|                            +------------------+       +---------------------+      |
|                                                                                   |
|  browser/ (MOD)            events/ (MOD)              lint/ (MOD)                 |
|  +-------------------+    +------------------+       +---------------------+      |
|  | Edge inspector ep |    | Diff rendering   |       | Layout width fix    |      |
|  | Multi-select ops  |    | fixes            |       | Walkthrough fix     |      |
|  | View filtering    |    +------------------+       +---------------------+      |
|  +-------------------+                                                            |
|                                                                                   |
|  commands/ (MOD — new command types for federation)                               |
+-----------------------------------------------------------------------------------+
                                    | SPARQL / HTTP
+-----------------------------------------------------------------------------------+
|                        RDF4J Triplestore                                          |
|  urn:sempkm:current     urn:sempkm:inferred      urn:sempkm:event:*             |
|  urn:sempkm:sparql:*    urn:sempkm:sync:*         urn:sempkm:ldn:*              |
|  urn:sempkm:mount:*     urn:sempkm:validations                                  |
|  (NEW named graphs)     LuceneSail FTS index                                     |
+-----------------------------------------------------------------------------------+
```

---

## 1. SPARQL Interface Enhancements

### 1.1 SPARQL Permissions

**Current state:** `sparql/router.py` requires `get_current_user` (any authenticated user can run any SPARQL query). The `all_graphs` flag lets any user bypass graph scoping.

**Integration approach:** Add a `PermissionsGuard` middleware layer in the SPARQL router that checks the user's role before query execution.

| Query Capability | guest | member | owner |
|-----------------|-------|--------|-------|
| Read current graph | YES | YES | YES |
| Read inferred graph | YES | YES | YES |
| Read all_graphs (event data) | NO | NO | YES |
| Execute CONSTRUCT | NO | YES | YES |
| Execute ASK | YES | YES | YES |

**Implementation:** Modify `_execute_sparql()` in `sparql/router.py` to accept the `User` object and check role constraints before execution. This is a guard check, not a query rewrite -- the existing `scope_to_current_graph()` already handles graph isolation.

```python
# In sparql/router.py - modified _execute_sparql signature
async def _execute_sparql(
    query: str,
    client: TriplestoreClient,
    user: User,
    all_graphs: bool = False,
) -> Response:
    # Permission check: only owners can use all_graphs
    if all_graphs and user.role != "owner":
        return JSONResponse(status_code=403, content={"error": "all_graphs requires owner role"})

    # Permission check: guests cannot use CONSTRUCT
    query_type = _detect_query_type(query)
    if query_type == "CONSTRUCT" and user.role == "guest":
        return JSONResponse(status_code=403, content={"error": "CONSTRUCT requires member role"})
    ...
```

**Files modified:** `backend/app/sparql/router.py` (add permission checks to existing endpoints)
**Files new:** None -- this is a modification, not a new module

### 1.2 SPARQL Autocomplete

**Current state:** Yasgui CDN embed uses LOV API for prefix/class autocomplete by default.

**Integration approach:** Add a backend `/api/sparql/autocomplete` endpoint that returns completions from the triplestore's actual data. Override Yasgui's default autocomplete with a custom completer that queries this endpoint.

```
GET /api/sparql/autocomplete?type=prefix     -> returns installed prefix:namespace pairs
GET /api/sparql/autocomplete?type=class      -> returns rdf:type values from current graph
GET /api/sparql/autocomplete?type=property   -> returns distinct predicates from current graph
GET /api/sparql/autocomplete?type=iri&q=...  -> returns IRIs matching prefix
```

The backend queries are simple SPARQL SELECTs against `urn:sempkm:current`:

```sparql
# Classes
SELECT DISTINCT ?class WHERE {
  GRAPH <urn:sempkm:current> { ?s a ?class }
}

# Properties
SELECT DISTINCT ?prop WHERE {
  GRAPH <urn:sempkm:current> { ?s ?prop ?o }
}

# IRIs matching prefix
SELECT DISTINCT ?iri ?label WHERE {
  GRAPH <urn:sempkm:current> {
    ?iri ?p ?o .
    OPTIONAL { ?iri dcterms:title ?label }
    FILTER(STRSTARTS(STR(?iri), ?prefix))
  }
} LIMIT 50
```

**Yasgui integration:** The `@zazuko/yasgui` CDN embed supports custom autocompleters. On the frontend, configure YASQE (the editor component inside Yasgui) to use the SemPKM autocomplete endpoint instead of LOV:

```javascript
// In sparql-console initialization (workspace bottom panel)
yasqe.setAutocomplete('class', {
  autoShow: true,
  async getCompletions() {
    const resp = await fetch('/api/sparql/autocomplete?type=class');
    return (await resp.json()).completions;
  }
});
```

**Files new:** `backend/app/sparql/autocomplete.py` (autocomplete service with SPARQL queries)
**Files modified:** `backend/app/sparql/router.py` (mount autocomplete endpoints), frontend SPARQL console init code

### 1.3 IRI Pills in Results

**Current state:** `SPARQL-02` already renders IRIs as clickable pill links in SPARQL results. This is implemented via a custom YASR (result renderer) plugin.

**Enhancement:** Extend the pill renderer to show labels (not just IRIs). The existing `LabelService.resolve_labels()` takes a batch of IRIs and returns labels. Add a `/api/labels/batch` endpoint:

```
POST /api/labels/batch { "iris": ["urn:...", "urn:..."] }
-> { "labels": { "urn:...": "My Note", "urn:...": "Concept X" } }
```

The YASR plugin calls this endpoint after rendering results, then updates pill text with resolved labels.

**Files new:** Batch label endpoint (could be in `browser/router.py` or new `labels/router.py`)
**Files modified:** Frontend YASR plugin code

### 1.4 Server-Side Query History

**Current state:** Yasgui stores query history in `localStorage` (client-side only, SPARQL-03).

**Integration approach:** Add server-side history storage in SQL (not triplestore -- history is user metadata, not RDF data).

**New SQL table:**

```python
class SparqlQueryHistory(Base):
    __tablename__ = "sparql_query_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_text: Mapped[str] = mapped_column(Text())
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    result_count: Mapped[int | None] = mapped_column(nullable=True)
```

**Endpoints:**

```
GET  /api/sparql/history         -> paginated history for current user
POST /api/sparql/history         -> record a query execution (called after each SPARQL run)
DELETE /api/sparql/history/{id}  -> delete a history entry
```

**Why SQL not triplestore:** Query history is user-scoped CRUD data with pagination -- exactly what SQL excels at. Putting it in the triplestore would create noisy named graphs unrelated to knowledge data.

**Files new:** `backend/app/sparql/history.py` (service + model), Alembic migration
**Files modified:** `backend/app/sparql/router.py` (auto-record after execution), frontend SPARQL console

### 1.5 Saved & Shared Queries

**Integration approach:** Extend the SQL history model with a "saved queries" concept.

```python
class SavedSparqlQuery(Base):
    __tablename__ = "saved_sparql_queries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    query_text: Mapped[str] = mapped_column(Text())
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean(), default=False)
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Shared queries are accessible via `GET /api/sparql/shared/{share_token}` without authentication (read-only).

**Files new:** `backend/app/sparql/saved.py`, Alembic migration
**Files modified:** Frontend SPARQL console (save/load UI)

### 1.6 Named Queries as Views

**Integration approach:** A saved query can be "promoted" to a ViewSpec. This bridges the SPARQL console and the view system.

When a user promotes a saved query, the system creates a `sempkm:ViewSpec` in a user-specific views named graph (`urn:sempkm:user:{user_id}:views`) with the query text, a table renderer, and columns inferred from the query's SELECT variables.

The existing `ViewSpecService` already queries across model views graphs -- extend it to also query user views graphs.

**Files modified:** `backend/app/views/service.py` (query user views graphs), `backend/app/sparql/saved.py` (promote endpoint)

---

## 2. Collaboration & Federation

### 2.1 RDF Patch Format

**What it is:** RDF Patch is a format for describing changes to an RDF dataset as a series of add/delete operations in N-Triples-like syntax. SemPKM's event store already captures this information -- each `Operation` has `materialize_inserts` and `materialize_deletes`.

**Integration approach:** Add an RDF Patch serializer that converts `Operation` objects to the RDF Patch text format:

```
H id <urn:sempkm:event:abc123> .
H prev <urn:sempkm:event:abc122> .
A <urn:ex:note1> <dcterms:title> "My Note" .
D <urn:ex:note1> <dcterms:title> "Old Title" .
```

This is a new serialization layer on top of the existing event store, not a replacement.

**New module:** `backend/app/federation/patch.py`

```python
class RDFPatchSerializer:
    """Serialize Operation objects to RDF Patch format."""

    def serialize(self, operation: Operation, event_iri: str, prev_event_iri: str | None) -> str:
        lines = [f"H id <{event_iri}> ."]
        if prev_event_iri:
            lines.append(f"H prev <{prev_event_iri}> .")
        for s, p, o in operation.materialize_deletes:
            lines.append(f"D {_serialize(s)} {_serialize(p)} {_serialize(o)} .")
        for s, p, o in operation.materialize_inserts:
            lines.append(f"A {_serialize(s)} {_serialize(p)} {_serialize(o)} .")
        lines.append("TX .")
        return "\n".join(lines)
```

**Endpoint:** `GET /api/federation/patches?since={event_iri}` returns a stream of RDF Patch entries since the given event, for consumption by remote instances.

### 2.2 Named Graph Sync

**Design:** Each SemPKM instance has a sync identity derived from its WebID/instance URL. Sync operates on the `urn:sempkm:current` graph only -- event graphs and system graphs are not synced.

**Sync flow:**

```
Instance A                                      Instance B
    |                                                |
    |-- POST /api/federation/patches?since=X ------->|
    |<-- RDF Patch stream (A, D operations) ---------|
    |                                                |
    | Apply patches via EventStore.commit()          |
    | (creates local events for audit trail)          |
    |                                                |
    |-- POST /api/federation/ack { last_applied } -->|
    |                                                |
```

**New module:** `backend/app/federation/sync.py` (SyncEngine)

The SyncEngine is a background task (not middleware) that periodically polls configured remote instances. Configuration stored in SQL:

```python
class FederationPeer(Base):
    __tablename__ = "federation_peers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instance_url: Mapped[str] = mapped_column(String(2048), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    last_synced_event: Mapped[str | None] = mapped_column(String(2048))  # event IRI
    sync_direction: Mapped[str] = mapped_column(String(20))  # "pull", "push", "bidirectional"
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**Conflict resolution:** Last-writer-wins per triple, using event timestamps. Conflicts are logged to a `urn:sempkm:sync:conflicts` named graph for manual review.

### 2.3 LDN (Linked Data Notifications)

**What it is:** W3C Recommendation for a protocol where senders POST JSON-LD notifications to an inbox URL, and consumers GET notifications from it.

**Integration approach:** SemPKM acts as both LDN Sender (outbound notifications) and LDN Receiver (inbox).

**Inbox:** A new endpoint at `/api/ldn/inbox` that accepts JSON-LD POST notifications and stores them in the triplestore under `urn:sempkm:ldn:inbox:{notification_id}` named graphs.

```
POST /api/ldn/inbox
Content-Type: application/ld+json

{
  "@context": "https://www.w3.org/ns/activitystreams",
  "@type": "Announce",
  "actor": "https://remote.instance/users/bob#me",
  "object": "urn:sempkm:model:basic-pkm:seed-note-arch",
  "target": "https://this.instance/api/ldn/inbox"
}
```

**Sender:** When federation sync occurs, or when a shared query is created, the system can send LDN notifications to configured peers' inboxes.

**Discovery:** The inbox URL is advertised via HTTP Link header on the WebID profile: `Link: </api/ldn/inbox>; rel="http://www.w3.org/ns/ldp#inbox"`.

**New module:** `backend/app/federation/ldn.py` (LDNInbox, LDNSender)
**Files modified:** `backend/app/webid/router.py` (add inbox Link header)

### 2.4 Federated WebID Authentication

**Current state:** WebID profiles exist (v2.5). IndieAuth provides OAuth2 flows. Each user has Ed25519 keys.

**Integration approach for federation auth:** When Instance A fetches patches from Instance B, it authenticates using HTTP Signatures (RFC 9421) with the requesting user's Ed25519 key. Instance B verifies by dereferencing the WebID to get the public key.

```
Instance A -> GET /api/federation/patches
  Authorization: Signature keyId="https://instance-a/users/alice#me",
                 algorithm="ed25519",
                 headers="(request-target) date",
                 signature="base64..."

Instance B:
  1. Extract keyId (WebID URI)
  2. Dereference WebID -> get public key
  3. Verify signature
  4. Check if WebID is in allowed peers list
```

**New module:** `backend/app/federation/auth.py` (signature creation and verification)
**Dependencies:** `cryptography` (already installed for Fernet), `httpx` (already installed)

### 2.5 Collaboration UI

A new workspace panel (sidebar or dockview tab) showing:
- Configured federation peers with sync status (last sync time, pending patches count)
- LDN inbox notifications with accept/dismiss actions
- Sync conflict list with resolution options

**Files new:** `backend/app/federation/router.py`, templates for collaboration UI
**Files modified:** `backend/app/templates/browser/workspace.html` (add collaboration panel option)

---

## 3. User Custom VFS (MountSpec)

### 3.1 MountSpec Vocabulary

**Current state:** VFS provider (`vfs/provider.py`) has a fixed hierarchy: `/model-id/type-label/filename.md`. Users cannot customize directory structure.

**MountSpec design:** A declarative RDF vocabulary that defines how objects map to filesystem paths.

```turtle
@prefix mount: <urn:sempkm:vocab:mount:> .

<urn:sempkm:mount:my-notes>
    a mount:MountSpec ;
    mount:label "My Notes" ;
    mount:strategy mount:ByType ;           # directory strategy
    mount:targetModel "basic-pkm" ;
    mount:targetTypes ( bpkm:Note bpkm:Concept ) ;
    mount:pathTemplate "{type}/{label}.md" ;
    mount:owner <urn:sempkm:user:abc> .
```

### 3.2 Five Directory Strategies

Each strategy defines how objects are organized into directories:

| Strategy | Path Pattern | Example |
|----------|-------------|---------|
| `ByType` | `/{type_label}/{object_label}.md` | `/Notes/Architecture.md` |
| `ByDate` | `/{year}/{month}/{object_label}.md` | `/2026/03/Architecture.md` |
| `ByProperty` | `/{property_value}/{object_label}.md` | `/Work/Project Alpha.md` |
| `Flat` | `/{object_label}.md` | `/Architecture.md` |
| `ByTag` | `/{tag}/{object_label}.md` | `/architecture/My Note.md` |

**Implementation:** Extend `SemPKMDAVProvider.get_resource_inst()` to support mount-specific path routing. Each mount gets a top-level directory entry. The provider inspects the first path segment to determine if it is a default mount (model-id) or a user mount (mount label).

```python
# Modified provider.py
def get_resource_inst(self, path: str, environ: dict):
    parts = [p for p in path.strip("/").split("/") if p]

    if len(parts) == 0:
        return RootCollection(path, environ, self._client, self._mount_service)

    # Check if first segment is a user mount
    mount = self._mount_service.get_mount_by_label(parts[0], user_id=environ.get("sempkm.user_id"))
    if mount:
        return self._resolve_mount_path(mount, parts[1:], path, environ)

    # Fall back to existing model-based routing
    ...
```

### 3.3 MountSpecService

**New module:** `backend/app/vfs/mounts.py`

```python
class MountSpecService:
    """Manage user-defined VFS mount configurations."""

    def __init__(self, client: TriplestoreClient):
        self._client = client

    async def list_mounts(self, user_id: str) -> list[MountSpec]:
        """List all mount specs for a user."""
        # Query urn:sempkm:mount:* graphs

    async def create_mount(self, user_id: str, spec: MountSpecCreate) -> MountSpec:
        """Create a new mount spec, stored as RDF in triplestore."""

    async def resolve_path(self, mount: MountSpec, object_data: dict) -> str:
        """Given an object, return its filesystem path under this mount."""
```

**Storage:** MountSpecs stored as RDF in `urn:sempkm:user:{user_id}:mounts` named graph.

### 3.4 SHACL Frontmatter Writes

**Current state:** VFS write path (`vfs/write.py`) strips frontmatter and commits only the body via `body.set`.

**Enhancement:** Parse frontmatter YAML keys and map them back to RDF properties using SHACL shape definitions. When a user edits frontmatter in their editor (VS Code, Obsidian), the changed property values are committed as `object.patch` commands.

```python
# Extended write path
def parse_and_commit_frontmatter(raw_bytes: bytes, object_iri: str, shapes_service, event_store):
    post = frontmatter.loads(raw_bytes.decode("utf-8"))
    body = post.content
    metadata = post.metadata

    # Get SHACL shape for this object's type
    shape = shapes_service.get_shape_for_iri(object_iri)

    # Map frontmatter keys back to predicates using _PREDICATE_LABELS reverse map
    operations = []
    for key, value in metadata.items():
        predicate = _reverse_label_map.get(key)
        if predicate:
            operations.append(build_patch_operation(object_iri, predicate, value))

    # Also commit body
    operations.append(build_body_set_operation(object_iri, body))

    # Atomic commit
    event_store.commit(operations)
```

**Files modified:** `backend/app/vfs/write.py`, `backend/app/vfs/resources.py`
**Files new:** `backend/app/vfs/mounts.py`, `backend/app/vfs/strategies.py`

### 3.5 Management UI

A settings sub-page (or dockview tab) for managing VFS mounts:
- List existing mounts with edit/delete
- Create new mount: select strategy, target types, path template
- Preview: show example paths for sample objects

**Files new:** Template for mount management UI, endpoint in `vfs/router.py`

---

## 4. VFS Browser UX Polish

**Current state:** VFS browser (`vfs-browser.js`) shows a tree with model > type > objects. No breadcrumbs, no preview pane, limited navigation.

### Integration Points

| Enhancement | Backend Change | Frontend Change |
|-------------|---------------|-----------------|
| Breadcrumbs | None (path info in existing response) | Parse path segments, render breadcrumb bar |
| Preview pane | None (already renders markdown) | Split browser into tree + preview layout |
| Navigation improvements | None | Keyboard nav, back/forward buttons |
| File operations | None planned for v2.6 | UI affordances only |

**Files modified:** `frontend/static/js/vfs-browser.js`, `frontend/static/css/vfs-browser.css`, `backend/app/templates/browser/vfs_browser.html`

---

## 5. Object Browser UI Improvements

### 5.1 Refresh/Plus Icons in Nav Tree

**Current state:** Nav tree nodes show type label only. No action buttons.

**Change:** Add inline icon buttons (Lucide) for "refresh this branch" and "create new object of this type" directly in tree nodes.

**Files modified:** `backend/app/templates/browser/nav_tree.html`, `frontend/static/css/workspace.css`

### 5.2 Multi-Select

**Integration approach:** Add checkbox selection to table/card views. Selected objects can be batch-deleted, batch-exported, or batch-tagged.

Backend needs a batch delete endpoint:

```
POST /api/commands/batch-delete
{ "iris": ["urn:...", "urn:..."] }
```

This dispatches multiple `object.patch` commands (setting `sempkm:deleted true`) in a single transaction.

**Files modified:** `frontend/static/js/workspace.js`, table/card view templates, `backend/app/commands/router.py`

### 5.3 Edge Inspector

A dockview panel (or right-pane section) showing all edges for the currently focused object with:
- Edge IRI, source, target, predicate
- Edge metadata (created, modified, provenance)
- Delete/edit actions per edge

**Files new:** `backend/app/templates/browser/edge_inspector.html`
**Files modified:** `backend/app/browser/router.py` (new endpoint), `frontend/static/js/workspace.js`

### 5.4 View Filtering

Add filter controls to table/card views: filter by property value, date range, or label substring.

**Backend:** The existing `ViewSpecService.execute_query()` already supports pagination and sorting. Add a `filters` parameter that injects FILTER clauses into the SPARQL query.

**Files modified:** `backend/app/views/service.py`, `backend/app/views/router.py`, table/card view templates

---

## 6. Event Log & Lint Dashboard Fixes

### Event Log Fixes

**Current state:** `events/query.py` EventQueryService provides diffs but some diff rendering has issues.

**Fix scope:** Template-level fixes in event log templates, not architectural changes. The `body_diff` field in `EventDetail` already computes diffs via `difflib` -- rendering issues are CSS/template bugs.

**Files modified:** Event log templates, `frontend/static/css/workspace.css`

### Lint Dashboard Fixes

**Current state:** `lint/` module with LintService, broadcast, and router.

**Fix scope:** CSS layout width issues, walkthrough (Driver.js tour) improvements.

**Files modified:** Lint dashboard templates, CSS, possibly `frontend/static/js/tutorials.js`

---

## 7. Spatial Canvas UI

**Current state:** `canvas/` module with Cytoscape.js integration, named sessions.

**Enhancement scope:** UX improvements TBD during phase planning. Architectural impact is minimal -- canvas is well-isolated.

**Files modified:** `frontend/static/js/canvas.js`, canvas templates

---

## Component Boundary Summary

| Component | Owns | Communicates With |
|-----------|------|-------------------|
| `sparql/router.py` (MOD) | Permission checks, autocomplete, history recording | TriplestoreClient, AuthService, SQL DB |
| `sparql/history.py` (NEW) | Query history CRUD, saved queries | SQL DB (Alembic migration) |
| `federation/patch.py` (NEW) | RDF Patch serialization | EventStore (read-only) |
| `federation/sync.py` (NEW) | Background sync polling, patch application | EventStore (write), remote HTTP, FederationPeer SQL |
| `federation/ldn.py` (NEW) | LDN inbox/sender protocol | TriplestoreClient (notification storage), httpx (outbound) |
| `federation/auth.py` (NEW) | HTTP Signature creation/verification | WebID service (key access), httpx (WebID dereference) |
| `federation/router.py` (NEW) | REST API for federation config + patches | All federation services |
| `vfs/mounts.py` (NEW) | MountSpec CRUD, path resolution | TriplestoreClient, ShapesService |
| `vfs/strategies.py` (NEW) | 5 directory strategy implementations | MountSpecService, LabelService |
| `vfs/provider.py` (MOD) | Path routing with mount awareness | MountSpecService |
| `vfs/write.py` (MOD) | SHACL-aware frontmatter write path | ShapesService, EventStore |
| `browser/router.py` (MOD) | Edge inspector, multi-select, view filter | TriplestoreClient, LabelService |
| `views/service.py` (MOD) | User views graphs, filter injection | TriplestoreClient |

---

## Data Flow Changes

### SPARQL Autocomplete Flow

```
User types "bpkm:" in YASQE editor
    |
YASQE custom autocompleter fires
    |
GET /api/sparql/autocomplete?type=class&q=bpkm:
    |
AutocompleteService.get_classes(prefix="bpkm:")
    |
SPARQL: SELECT DISTINCT ?class WHERE { ?s a ?class . FILTER(STRSTARTS(STR(?class), "urn:sempkm:model:basic-pkm:")) }
    |
Returns: [{ iri: "bpkm:Note", label: "Note" }, { iri: "bpkm:Concept", label: "Concept" }]
    |
YASQE shows completion dropdown
```

### RDF Patch Sync Flow

```
SyncEngine background task wakes up (every 60s configurable)
    |
For each enabled FederationPeer:
    |
GET https://remote.instance/api/federation/patches?since={last_synced_event}
  Authorization: HTTP Signature with local user's Ed25519 key
    |
Remote instance:
  1. Verify HTTP Signature against sender's WebID public key
  2. Check sender is in allowed peers
  3. Query EventStore for events since requested event IRI
  4. Serialize as RDF Patch stream
  5. Return text/x-rdf-patch response
    |
Local SyncEngine:
  1. Parse RDF Patch (A/D operations)
  2. For each patch transaction:
     a. Build Operation(materialize_inserts=A_triples, materialize_deletes=D_triples)
     b. EventStore.commit([operation], performed_by=remote_webid, performed_by_role="federation")
  3. Update FederationPeer.last_synced_event
  4. If conflict detected (triple exists with different value):
     Log to urn:sempkm:sync:conflicts graph
```

### MountSpec VFS Path Resolution Flow

```
User mounts VFS via WebDAV client
    |
GET /vfs/My Notes/Architecture.md
    |
SemPKMDAVProvider.get_resource_inst("/My Notes/Architecture.md")
    |
MountSpecService.get_mount_by_label("My Notes", user_id)
    -> Returns MountSpec(strategy=ByType, targetTypes=[bpkm:Note])
    |
StrategyResolver.resolve("/My Notes", "Architecture.md", mount_spec)
    -> ByTypeStrategy: lookup object with label "Architecture" of type bpkm:Note
    -> Returns object_iri, type_iri
    |
ResourceFile(path, environ, client, ...) -- renders as before
```

### LDN Notification Flow

```
Instance A creates a shared query
    |
LDNSender.send_notification(
    target_inbox="https://instance-b/api/ldn/inbox",
    notification={
        "@type": "Announce",
        "actor": "https://instance-a/users/alice#me",
        "object": { "@id": "https://instance-a/api/sparql/shared/abc123", "@type": "SparqlQuery" },
        "summary": "Alice shared a SPARQL query"
    }
)
    |
POST https://instance-b/api/ldn/inbox
Content-Type: application/ld+json
Authorization: HTTP Signature
    |
Instance B LDN Inbox:
  1. Validate JSON-LD structure
  2. Store in urn:sempkm:ldn:inbox:{uuid} named graph
  3. Return 201 Created with Location header
    |
Instance B user sees notification in Collaboration UI panel
```

---

## New Named Graphs

| Named Graph | Purpose | Owner |
|-------------|---------|-------|
| `urn:sempkm:user:{id}:views` | User-created ViewSpecs (promoted from saved queries) | User |
| `urn:sempkm:user:{id}:mounts` | User MountSpec definitions | User |
| `urn:sempkm:sync:conflicts` | Federation sync conflicts | System |
| `urn:sempkm:ldn:inbox:{id}` | Individual LDN notifications | System |

---

## New SQL Tables (Alembic Migrations)

| Table | Purpose | Rationale for SQL vs RDF |
|-------|---------|--------------------------|
| `sparql_query_history` | Per-user query execution log | High-churn CRUD, pagination, not knowledge data |
| `saved_sparql_queries` | Named/shared queries | User metadata, share tokens, not knowledge data |
| `federation_peers` | Remote instance configuration | Config data with last-sync cursor, not RDF |

---

## Build Order (Dependency Graph)

```
Phase group 1: Independent, no cross-deps
  [SPARQL Permissions]         <- Smallest change, immediate security value
  [Event Log Fixes]            <- Template-level fixes, zero risk
  [Lint Dashboard Fixes]       <- CSS fixes, zero risk
  [Spatial Canvas UX]          <- Isolated module

Phase group 2: SPARQL Interface (sequential within)
  [SPARQL Autocomplete]        <- Needs autocomplete endpoint
  [SPARQL Server History]      <- Needs SQL migration
  [SPARQL Saved Queries]       <- Builds on history model
  [Named Queries as Views]     <- Depends on saved queries + ViewSpecService mod
  [IRI Pills Enhancement]      <- Independent of history, batch labels endpoint

Phase group 3: Object Browser (parallel)
  [Nav Tree Refresh/Plus]      <- Template change
  [Multi-Select]               <- Frontend + batch endpoint
  [Edge Inspector]             <- New panel, new endpoint
  [View Filtering]             <- ViewSpecService filter injection

Phase group 4: VFS (sequential)
  [MountSpec Vocabulary]       <- Define RDF vocabulary first
  [MountSpec Service]          <- CRUD for mount specs
  [Directory Strategies]       <- 5 strategy implementations
  [SHACL Frontmatter Writes]   <- Depends on ShapesService integration
  [VFS Browser UX Polish]      <- Can proceed in parallel
  [Mount Management UI]        <- Depends on service layer

Phase group 5: Federation (sequential, highest complexity)
  [RDF Patch Serializer]       <- Pure function, no deps
  [Federation Auth]            <- HTTP Signatures, WebID key access
  [Patch Sync Engine]          <- Depends on patch serializer + auth
  [LDN Inbox/Sender]           <- Independent of sync, but same auth
  [Collaboration UI]           <- Depends on all federation services
```

**Recommended phase ordering rationale:**
1. Groups 1-3 can proceed in parallel (no cross-dependencies)
2. Group 4 (VFS) depends only on existing ShapesService
3. Group 5 (Federation) is the most complex and should be last -- it builds on WebID (v2.5) and requires new protocol implementations
4. Within each group, the listed order respects internal dependencies

---

## Patterns to Follow

### Pattern: SQL for User Metadata, RDF for Knowledge Data

Query history, saved queries, and federation peer config are user CRUD data -- use SQL with Alembic migrations. MountSpecs and user ViewSpecs are knowledge-adjacent data that benefit from RDF querying -- store in triplestore named graphs.

### Pattern: Event Store for All Writes

Federation sync must go through `EventStore.commit()` even for remotely-sourced patches. This preserves the audit trail, triggers validation, and fires webhooks. Never bypass the event store with direct triplestore updates.

### Pattern: HTTP Signatures for Federation Auth

Use RFC 9421 HTTP Signatures with Ed25519 keys (already generated per user in v2.5). Verify by dereferencing the sender's WebID to retrieve their public key. This avoids shared secrets and leverages the existing WebID infrastructure.

### Pattern: Background Tasks via asyncio.create_task

The SyncEngine should run as a periodic background task created during app lifespan, similar to the existing `AsyncValidationQueue`. Use `asyncio.create_task()` with a sleep loop, not a full task queue system (Celery/Redis would be overengineering for single-instance sync).

---

## Anti-Patterns to Avoid

### Anti-Pattern: Direct Triplestore Writes for Sync

**What:** Federation sync writing directly to the triplestore via `client.update()`, bypassing EventStore.
**Why bad:** Breaks the event-sourced audit trail, skips SHACL validation, skips webhooks.
**Instead:** Always create proper Operations and commit via EventStore, with `performed_by` set to the remote WebID and `performed_by_role` set to "federation".

### Anti-Pattern: Storing Query History in the Triplestore

**What:** Creating named graphs for each SPARQL query execution.
**Why bad:** Query history is high-churn data (dozens of entries per session). Triplestore named graphs are designed for knowledge data, not logging. Would pollute SPARQL queries and slow down graph listing.
**Instead:** Use SQL tables with proper indexes and pagination.

### Anti-Pattern: Custom WebSocket Protocol for Sync

**What:** Building a real-time WebSocket sync channel between instances.
**Why bad:** Adds persistent connection management, reconnection logic, and stateful protocol complexity. SemPKM is a personal tool used by 1-5 users.
**Instead:** Polling-based sync with configurable interval (60s default). Simple, stateless, debuggable.

### Anti-Pattern: Monolithic Federation Module

**What:** One large `federation.py` file handling patches, sync, LDN, and auth.
**Why bad:** These are distinct concerns with different lifecycles and dependencies.
**Instead:** Separate modules (`patch.py`, `sync.py`, `ldn.py`, `auth.py`) under a `federation/` package.

---

## Scalability Considerations

| Concern | At 1 user | At 5 users | At 2 federated instances |
|---------|-----------|------------|--------------------------|
| SPARQL autocomplete | Direct triplestore query (~50ms) | Same, cached 30s | Same, local data only |
| Query history | SQLite fine | SQLite fine | Per-instance, not synced |
| Sync polling | N/A | N/A | 1 HTTP request per interval per peer |
| LDN inbox | N/A | N/A | Stored as named graphs, manual curation keeps count low |
| MountSpec resolution | On each VFS request, SPARQL lookup | Cached mount specs recommended (TTL 300s) | Not synced |

---

## Sources

- `backend/app/sparql/router.py` -- current SPARQL endpoint, permission model
- `backend/app/sparql/client.py` -- graph scoping, prefix injection
- `backend/app/events/store.py` -- EventStore, Operation dataclass
- `backend/app/commands/dispatcher.py` -- 5-command API
- `backend/app/commands/router.py` -- command execution with provenance
- `backend/app/vfs/provider.py` -- current WebDAV provider routing
- `backend/app/vfs/resources.py` -- ResourceFile, frontmatter rendering
- `backend/app/vfs/write.py` -- VFS write path, body.set bridge
- `backend/app/auth/models.py` -- User model, SQL tables
- `backend/app/auth/dependencies.py` -- role-based auth guards
- `backend/app/webid/` -- WebID profile, Ed25519 keys
- `backend/app/indieauth/` -- OAuth2 flows
- `backend/app/views/service.py` -- ViewSpecService
- `backend/app/lint/service.py` -- LintService
- `backend/app/events/query.py` -- EventQueryService
- [RDF Patch specification](https://afs.github.io/rdf-patch/)
- [Apache Jena RDF Patch docs](https://jena.apache.org/documentation/rdf-patch/)
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/)
- [py-ldnlib Python LDN library](https://github.com/trellis-ldp/py-ldnlib)
- [Yasgui documentation (Triply)](https://docs.triply.cc/yasgui/)
- [TriplyDB Yasgui GitHub](https://github.com/TriplyDB/Yasgui)
- [sib-swiss/sparql-editor (YASGUI-based)](https://github.com/sib-swiss/sparql-editor)
- [W3C Linked Data Patch Format](https://www.w3.org/TR/ldpatch/)
- [CodeMirror autocompletion API](https://codemirror.net/examples/autocompletion/)

---

*Architecture research for: SemPKM v2.6 Power User & Collaboration*
*Researched: 2026-03-09*

# Technology Stack: v2.6 Power User & Collaboration

**Project:** SemPKM v2.6
**Researched:** 2026-03-09
**Confidence:** HIGH for SPARQL/VFS/UI work; MEDIUM for sync/federation (protocol design complexity)

---

## Scope Note

This is a **subsequent milestone** research document. The existing validated stack (FastAPI, RDF4J LuceneSail, htmx/vanilla-web, SQLAlchemy, wsgidav, a2wsgi, dockview-core, Alembic, Yasgui CDN, ninja-keys, owlrl, pyshacl, mf2py, Cytoscape.js, CodeMirror, Driver.js, rdflib, httpx, cryptography) is **not re-researched**. This document covers only what changes or is added for v2.6 features.

---

## Executive Summary

v2.6 requires **zero new Python packages and zero new frontend libraries**. Every feature builds on existing dependencies:

- **SPARQL enhancements** -- Yasgui autocompleter config (existing CDN), new SQLAlchemy models for server-side history/saved queries, RBAC middleware on existing `/api/sparql` endpoint
- **RDF Patch** -- rdflib's built-in `patch` serializer (already in pyproject.toml as rdflib >=7.5.0), SQLAlchemy for patch log storage
- **LDN notifications** -- custom implementation using httpx (existing) for sending and FastAPI endpoint for receiving. Protocol is trivial (~100 LOC)
- **MountSpec VFS** -- extend existing wsgidav provider with new collection subclasses per strategy
- **Federated WebID auth** -- Ed25519 keys (already generated in v2.5), HTTP Signature verification using cryptography (existing)
- **All UI improvements** -- pure htmx + vanilla JS + CSS + existing Lucide icons

The primary new work is backend services and SQLAlchemy models, not technology adoption.

---

## Recommended Stack

### Core Framework (no changes)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| FastAPI | existing | Backend API | No change |
| rdflib | >=7.5.0 (existing) | RDF processing + RDF Patch serialization | **New usage**: `patch` format serializer for change tracking |
| httpx | >=0.28 (existing) | HTTP client | **New usage**: LDN sender, remote WebID profile fetcher, sync client |
| SQLAlchemy | >=2.0.46 (existing) | Auth + metadata DB | **New usage**: 5 new tables (saved queries, query history, patch log, remote instances, mount specs) |
| cryptography | >=43.0 (existing) | Key management | **New usage**: HTTP Signature signing/verification for federated auth |

### Database (extends existing auth DB)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Alembic migrations | >=1.18 (existing) | Schema evolution for new tables | Standard pattern. 5 new tables require 1-2 migration files. |

### Infrastructure (no changes)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| RDF4J | 5.x (existing) | Triplestore | No change. SPARQL Graph Store Protocol already supported for named graph sync. |
| wsgidav | >=4.3.3 (existing) | WebDAV VFS | Extended with new collection subclasses for 5 directory strategies. |
| nginx | existing | Reverse proxy | May need new location blocks for `/api/sync/*` and `/api/inbox`. |

### Frontend (no changes)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| @zazuko/yasgui | 4.5.0 CDN (existing) | SPARQL console | **New config**: custom autocompleters for class/property suggestions. |
| dockview-core | existing | Panel management | No change. |
| Cytoscape.js | existing | Graph view | No change. |
| Lucide icons | existing | UI icons | New icon usage (refresh, plus, multi-select) but no version change. |

---

## Feature-by-Feature Stack Mapping

### 1. SPARQL Permissions

**New code, no new dependencies.**

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Permission check | FastAPI dependency (`check_sparql_permission`) on existing `/api/sparql` route | Owner: full access including `all_graphs=true`. Member: current graph only, `all_graphs` rejected. Guest: denied (403). |
| Role model extension | Add `sparql_access` field to user role enum or settings | Reuses existing RBAC system from v1.0 Phase 6-7. |

### 2. SPARQL Autocomplete

**Yasgui configuration, no new library.**

Yasgui's YASQE component supports custom autocompleters via its initialization config. Build two custom completers that query the existing `/api/sparql` endpoint:

| Completer | Query | Mode |
|-----------|-------|------|
| Class completer | `SELECT DISTINCT ?class WHERE { ?s a ?class }` | `bulk: true` (fetch all on init, cache in-memory) |
| Property completer | `SELECT DISTINCT ?p WHERE { ?s ?p ?o }` | `bulk: true` (fetch all on init, cache in-memory) |

This avoids the `@sib-swiss/sparql-editor` alternative which requires VoID metadata generation (SemPKM does not generate VoID) and would add an npm build step.

### 3. SPARQL IRI Pills (Enhancement)

**Extend existing YASR custom cell renderer.**

Already implemented in v2.2. Enhancement: add `data-node-label` attribute for hover preview tooltips. Uses existing LabelService via a lightweight API call.

### 4. Server-Side Query History + Saved Queries

**New SQLAlchemy models + Alembic migration + API endpoints.**

```python
# backend/app/sparql/models.py
class SavedQuery(Base):
    __tablename__ = "saved_queries"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str]
    sparql_text: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]]
    is_shared: Mapped[bool] = mapped_column(default=False)
    is_view: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

class QueryHistory(Base):
    __tablename__ = "query_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sparql_text: Mapped[str] = mapped_column(Text)
    executed_at: Mapped[datetime]
    duration_ms: Mapped[Optional[int]]
    result_count: Mapped[Optional[int]]
```

API endpoints: `GET/POST/DELETE /api/sparql/saved`, `GET /api/sparql/history`. Both use standard SQLAlchemy async CRUD patterns already established in the auth layer.

**Named Queries as Views:** When `is_view=True` on a SavedQuery, generate a ViewSpec that references the saved SPARQL text. Uses existing `ViewSpecService` infrastructure.

### 5. RDF Patch Change Tracking

**rdflib built-in `patch` serializer -- already a dependency.**

| Component | Technology | Notes |
|-----------|-----------|-------|
| Patch generation | rdflib `serialize(format='patch')` | Supports serializing diff between two Datasets. Already available in rdflib >=7.5.0 (project uses >=7.5.0). |
| Patch storage | SQLAlchemy `PatchLogEntry` table | Append-only. Indexed by `graph_uri` + `version` for efficient `since` queries. |
| EventStore integration | Post-commit hook | After successful `EventStore.commit()`, serialize insert/delete operations as RDF Patch text, insert `PatchLogEntry`. Failure logs error but does NOT roll back the event commit. |

```python
# backend/app/sync/models.py
class PatchLogEntry(Base):
    __tablename__ = "patch_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    graph_uri: Mapped[str] = mapped_column(index=True)
    version: Mapped[int]  # Monotonic per graph_uri
    patch_data: Mapped[str] = mapped_column(Text)  # RDF Patch format
    event_iri: Mapped[str]
    timestamp: Mapped[datetime]
```

**Confidence note (MEDIUM):** rdflib's `patch` serializer documentation is sparse. It handles quad-level diffs between Dataset objects, which maps to named graph operations. However, SemPKM's EventStore already has structured `materialize_inserts`/`materialize_deletes` lists -- it may be simpler to generate RDF Patch text directly from these lists rather than reconstructing Dataset objects for rdflib's serializer. Evaluate during implementation.

### 6. Named Graph Sync API

**httpx (existing) + SPARQL Graph Store Protocol (RDF4J built-in).**

| Component | Technology | Notes |
|-----------|-----------|-------|
| Sync endpoint | FastAPI routes at `/api/sync/{graph}` | GET returns patches since version. POST applies incoming patches. |
| Full graph bootstrap | SPARQL Graph Store Protocol | RDF4J supports `GET/PUT /rdf4j-server/repositories/{repo}/rdf-graphs/service?graph={uri}`. Use for initial full-graph exchange. |
| Remote instance config | SQLAlchemy `RemoteInstance` table | Stores peer URLs, sync direction (push/pull/both), last synced version. |
| Outbound sync | httpx.AsyncClient | Existing dependency. POST patches to remote `/api/sync/{graph}`. |

```python
# backend/app/sync/models.py
class RemoteInstance(Base):
    __tablename__ = "remote_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str]
    base_url: Mapped[str]
    webid_uri: Mapped[Optional[str]]
    sync_direction: Mapped[str]  # push, pull, both
    last_synced_version: Mapped[Optional[int]]
    is_active: Mapped[bool] = mapped_column(default=True)
```

### 7. LDN Notifications

**Custom implementation using httpx + FastAPI. No new library.**

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Receiver | `POST /api/inbox` FastAPI endpoint | Accepts `application/ld+json`. Validates JSON-LD payload. Stores in `urn:sempkm:inbox` named graph. Triggers sync pull if notification references a known remote. |
| Sender | `httpx.AsyncClient.post()` | Posts JSON-LD notification to discovered inbox URLs when subscribed graphs change. |
| Inbox discovery | HTTP `Link` header parsing | Look for `rel="http://www.w3.org/ns/ldp#inbox"` on remote resource responses. |

**Why not py-ldnlib?** [Last released August 2018](https://pypi.org/project/py-ldnlib/). Unmaintained for 8 years. The [LDN W3C spec](https://www.w3.org/TR/ldn/) is simple: receivers accept JSON-LD POSTs, consumers GET notification lists. ~100 lines of custom code is lower risk than an abandoned dependency.

**Why not coarnotify?** [coarnotify](https://pypi.org/project/coarnotify/) is domain-specific to academic repository workflows (COAR Notify protocol). Over-specialized for SemPKM's use case.

### 8. Federated WebID Auth

**cryptography (existing) + rdflib (existing).**

| Component | Implementation | Notes |
|-----------|---------------|-------|
| HTTP Signature signing | `cryptography.hazmat.primitives.asymmetric.ed25519` | Ed25519 keys already generated per user in v2.5 (`WBID-05`). Sign outgoing sync/notification requests. |
| HTTP Signature verification | Same library | Verify incoming requests by fetching sender's WebID profile (Turtle/JSON-LD), extracting public key, verifying signature. |
| WebID profile parsing | rdflib | Parse remote Turtle/JSON-LD to extract `sec:publicKeyPem` or equivalent. Already a dependency. |
| Key cache | cachetools.TTLCache (existing) | Cache remote public keys with 5-minute TTL to avoid re-fetching on every request. |

New FastAPI dependency: `get_authenticated_identity` -- accepts either cookie session (local users) OR HTTP Signature header (remote WebID users). Used on `/api/sync/*` and `/api/inbox` routes.

### 9. User Custom VFS (MountSpec)

**Extend existing wsgidav provider -- no new library.**

| Component | Implementation | Notes |
|-----------|---------------|-------|
| MountSpec storage | SQLAlchemy `MountSpec` table | User-defined mount configurations with strategy, SPARQL scope, group property. |
| Strategy classes | New DAVCollection subclasses | `TagGroupCollection`, `DateCollection`, `PropertyGroupCollection`, `HierarchicalCollection` extending existing `TypeCollection` pattern. |
| Provider routing | Extend `SemPKMDAVProvider.get_resource_inst()` | Currently hardcoded 4-level path. Add MountSpec prefix matching before default routing. |
| Management UI | htmx form in Settings page | No new frontend library. |

```python
# backend/app/vfs/models.py
class MountSpecModel(Base):
    __tablename__ = "mount_specs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mount_path: Mapped[str] = mapped_column(unique=True)
    strategy: Mapped[str]  # flat, tag-groups, date, property-grouped, hierarchical
    sparql_scope: Mapped[str] = mapped_column(Text)
    group_property: Mapped[Optional[str]]
    include_body: Mapped[bool] = mapped_column(default=True)
    frontmatter_shape_iri: Mapped[Optional[str]]
    is_active: Mapped[bool] = mapped_column(default=True)
```

**5 Directory Strategies:**

| Strategy | Directory Structure | SPARQL Pattern |
|----------|-------------------|----------------|
| `flat` | `/mount/object1.md, /mount/object2.md` | All objects matching scope, flat list |
| `tag-groups` | `/mount/tag-a/object1.md` | Group by `skos:broader` or tag property |
| `date` | `/mount/2026/03/object1.md` | Group by `dcterms:created` year/month |
| `property-grouped` | `/mount/property-value/object1.md` | Group by configurable `group_property` |
| `hierarchical` | `/mount/parent/child/object1.md` | Follow `skos:broader` or `dcterms:isPartOf` chain |

### 10. UI Improvements

**All vanilla JS/CSS/htmx. Zero new dependencies.**

| Feature | Implementation |
|---------|---------------|
| Object browser refresh/plus icons | Lucide icons + htmx click handlers |
| Multi-select in object browser | CSS checkbox overlay + JS selection state + batch action bar |
| Edge inspector panel | New dockview panel component, htmx-loaded content |
| View filtering | htmx `hx-get` with query params on existing view endpoints |
| VFS browser breadcrumbs | Pure CSS/HTML breadcrumb trail + htmx navigation |
| VFS file operations | Extend existing wsgidav write path |
| Spatial canvas improvements | Cytoscape.js API calls (existing) |
| Event log fixes | Template/CSS fixes (existing Jinja2 + htmx) |
| Lint dashboard fixes | Template/CSS layout fixes |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| SPARQL autocomplete | Yasgui custom autocompleter config | @sib-swiss/sparql-editor | Requires VoID metadata. Adds npm build step. Violates no-build-step principle. |
| RDF Patch | rdflib `patch` serializer | rdf-delta-python | Client for Java Delta Server. SemPKM generates patches itself. Wrong tool. |
| RDF Patch | rdflib `patch` serializer | Jelly-Patch (binary) | Python impl does not exist. Java only. 3.5-8.9x compression is appealing but blocked. Monitor. |
| LDN | Custom httpx impl | py-ldnlib | Unmaintained since 2018. Protocol is trivial. |
| LDN | Custom httpx impl | coarnotify | Over-specialized for academic repositories. |
| Graph sync | Custom patch-based | Quit Store (Git-backed) | Unmaintained since 2022. Git adds complexity. |
| Graph sync | Custom patch-based | NextGraph CRDT | Alpha. No Python SDK. Future Layer 4. |
| Saved queries | SQLAlchemy | RDF in triplestore | SQL is better for CRUD + pagination + user-scoping. Use triplestore for query results, SQL for query management. |
| HTTP Signatures | Manual with cryptography | httpsig PyPI | Last updated 2019. cryptography package already provides Ed25519 primitives. |
| VFS strategies | Extend wsgidav provider | New WebDAV library | wsgidav proven and integrated. Just add collection subclasses. |

---

## What NOT to Add

| Technology | Why Not | Use Instead |
|------------|---------|-------------|
| @sib-swiss/sparql-editor | VoID metadata dependency + npm build step | Yasgui autocompleter config |
| Any new Python package | All features build on existing deps | Existing rdflib, httpx, cryptography, SQLAlchemy |
| Any new CDN library | All UI work uses existing frontend libs | Existing Lucide, dockview, Yasgui, Cytoscape |
| Redis / Valkey | Overkill for self-hosted single-instance notification | HTTP-based LDN with httpx |
| WebSocket library | Real-time co-editing deferred to Layer 4 (CRDT) | SSE (existing) for sync status updates |
| Protocol Buffers / gRPC | No Python Jelly-Patch impl. HTTP + text patches sufficient at PKM scale | Plain HTTP + RDF Patch text format |
| ActivityPub library | Full AP is wrong abstraction for knowledge graph sync | LDN (subset of AP, simpler) |
| SOLID libraries | Pod model mismatched (document store, no SPARQL) | Monitor only |
| py-ldnlib | Unmaintained since 2018 | Custom httpx implementation |

---

## Installation

```bash
# No new packages required. Existing pyproject.toml is unchanged.
# All v2.6 features use existing dependencies:
#   rdflib>=7.5.0   (RDF Patch serializer)
#   httpx>=0.28     (LDN sender, sync client)
#   cryptography>=43.0 (HTTP Signatures)
#   sqlalchemy[asyncio]>=2.0.46 (new tables)
#   wsgidav>=4.3.3  (extended provider)

# Only action needed: Alembic migration for new tables
alembic revision --autogenerate -m "add saved_queries, query_history, patch_log, remote_instances, mount_specs tables"
alembic upgrade head
```

---

## Integration Points

### EventStore.commit() -> RDF Patch Log

```
EventStore.commit()
  |-- Creates event named graph (existing)
  |-- Materializes to current graph (existing)
  |-- [NEW] Serializes materialize_inserts/deletes as RDF Patch text
  |-- [NEW] Inserts PatchLogEntry with monotonic version
  |-- [NEW] If graph has subscribers, enqueue LDN notification
```

### Yasgui Autocompleter Wiring

Add to existing Yasgui initialization in workspace bottom panel:

```javascript
// Custom autocompleters querying /api/sparql for schema info
yasqe.addAutocompleter('semPkmClasses', {
  bulk: true,
  get: async () => {
    const resp = await fetch('/api/sparql', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'query=' + encodeURIComponent(
        'SELECT DISTINCT ?class WHERE { ?s a ?class } ORDER BY ?class'
      )
    });
    const data = await resp.json();
    return data.results.bindings.map(b => b.class.value);
  }
});
```

### VFS MountSpec Dynamic Routing

Extend `SemPKMDAVProvider.get_resource_inst()`:
1. Load active MountSpecs from SQLAlchemy at startup (cache with invalidation)
2. Match incoming path prefix against mount paths
3. Dispatch to appropriate strategy collection class
4. Fall through to default model/type/object routing for unmatched paths

### WebID Auth for Sync/Inbox Endpoints

New `get_authenticated_identity` dependency:
```
Request arrives at /api/sync/* or /api/inbox
  |-- Check cookie session (existing local auth) -> return local User
  |-- Check Authorization: HttpSig header -> verify signature
  |     |-- Extract keyId (WebID URI) from signature
  |     |-- Fetch WebID profile (cached 5min TTL)
  |     |-- Extract public key from profile
  |     |-- Verify signature against public key
  |     |-- Return FederatedIdentity(webid_uri, verified=True)
  |-- Neither present -> 401 Unauthorized
```

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| SPARQL permissions | HIGH | Standard RBAC middleware on existing endpoint. Well-established pattern. |
| SPARQL autocomplete | HIGH | Yasgui YASQE autocompleter API is documented. Custom completers are a known pattern. |
| Saved queries / history | HIGH | Standard SQLAlchemy CRUD. No new technology. |
| IRI pills enhancement | HIGH | Extending existing v2.2 custom YASR renderer. |
| RDF Patch generation | MEDIUM | rdflib `patch` serializer exists but docs are sparse. May need to generate patches manually from insert/delete lists rather than using serializer. Verify during implementation. |
| Named graph sync | MEDIUM | Protocol is straightforward. Conflict resolution (diverged versions) needs careful design. |
| LDN notifications | MEDIUM | Protocol is simple. Inbox discovery across heterogeneous deployments may have edge cases. |
| Federated WebID auth | MEDIUM | Ed25519 keys exist. HTTP Signature spec has multiple draft versions -- need to pick one and validate interop. |
| MountSpec VFS strategies | HIGH | Extends existing wsgidav provider. Collection subclass approach proven by current flat strategy. |
| UI improvements | HIGH | All vanilla JS/CSS/htmx. No new technology. |

---

## Sources

- [RDFLib plugin serializers (patch format)](https://rdflib.readthedocs.io/en/stable/plugin_serializers.html) -- rdflib built-in RDF Patch serializer documentation
- [RDF Patch format specification](https://afs.github.io/rdf-patch/) -- canonical format definition by Andy Seaborne
- [Kurrawong/rdf-delta-python](https://github.com/Kurrawong/rdf-delta-python) -- Python Delta client (evaluated, not adopted)
- [Jelly-Patch SEMANTiCS 2025 paper](https://arxiv.org/html/2507.23499v1) -- binary patch format benchmarks (Java only)
- [py-ldnlib on PyPI](https://pypi.org/project/py-ldnlib/) -- unmaintained LDN library (evaluated, not adopted)
- [COAR Notify on PyPI](https://pypi.org/project/coarnotify/) -- domain-specific LDN (evaluated, not adopted)
- [W3C Linked Data Notifications spec](https://www.w3.org/TR/ldn/) -- LDN W3C Recommendation
- [W3C SPARQL Graph Store Protocol](https://w3c.github.io/sparql-graph-store-protocol/) -- named graph HTTP operations
- [YASQE autocompleter documentation](http://yasqe.yasgui.org/doc/) -- Yasgui YASQE autocompleter configuration
- [@sib-swiss/sparql-editor](https://github.com/sib-swiss/sparql-editor) -- VoID-dependent SPARQL editor (evaluated, not adopted)
- [WsgiDAV documentation](https://wsgidav.readthedocs.io/) -- custom DAVProvider architecture
- [SemPKM collaboration architecture research](.planning/research/collaboration-architecture.md) -- prior research (40+ sources)
- [SemPKM decentralized identity research](.planning/research/decentralized-identity.md) -- WebID/IndieAuth prior research

---
*Stack research for: SemPKM v2.6 Power User & Collaboration milestone*
*Researched: 2026-03-09*

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

# Academic Workspace Design & PKM Research Analysis

**Created:** 2026-03-05
**Context:** Analysis of a Perplexity Deep Research chat examining academic UI design patterns, PKM/PIM research literature, and research-backed feature requirements for knowledge management tools. This document captures all insights and cross-references them against SemPKM's existing roadmap.

---

## Executive Summary

A comprehensive deep research analysis explored three interconnected areas relevant to SemPKM's future development: academic workspace UI design, the PKM/PIM research landscape, and a research-backed feature checklist organized into seven themes.

The **academic UI layout proposal** describes a three-pane workspace with top-level modes aligned to academic verbs (Read, Think, Organize, Plan, Publish). This maps naturally onto SemPKM's existing dockview-based workspace architecture and the installable mental models concept -- modes could be model-contributed view configurations rather than hardcoded application states.

The **PKM/PIM research landscape** traces the field from its emergence in the late 1990s through current multi-disciplinary approaches incorporating AI integration and "second brain" practices. Key takeaways include the importance of structured personal spaces, the socio-technical nature of PKM, explicit support for reflection and learning loops, and the parallel between reusable workflow templates and SemPKM's installable mental models.

The **research-backed feature checklist** spans seven themes: Capture, Organize, Retrieve & Sensemaking, Plan & Execute, Reflect & Learn, Share & Publish, and Collaboration & Social PKM. Cross-referencing these against SemPKM's roadmap reveals that the core Organize and Retrieve capabilities are well-covered by shipped milestones (v1.0 through v2.4), several features naturally extend planned milestones (RSS Reader, Collaboration, Identity), and a meaningful set of features -- particularly around reading capture, review cycles, learning metrics, and draft-from-graph publishing -- represent entirely new territory not yet on the roadmap.

This document is purely informational input for future milestone planning. No changes to ROADMAP.md are proposed or made.

---

## 1. Academic UI Layout Proposal

### 1.1 Three-Pane Workspace Design

The research proposes a three-pane layout organized around academic workflows:

**Left Pane -- Navigation & Context Selection:**
- Workspaces and projects (scoping what the user is working on)
- Saved views and filters (quick access to curated result sets)
- Persistent navigation tree for the active workspace

**Center Pane -- Active Mode:**
- The primary working area, switching between modes:
  - **PDF/HTML Reader** -- reading and annotating source material
  - **Argument Map** -- structuring claims, evidence, and reasoning
  - **Concept Map** -- visual knowledge organization
  - **Draft Editor** -- writing and composition
  - **Task Board** -- project and action management

**Right Pane -- Contextual Information:**
- Annotations list for the current document/object
- Semantic metadata (types, properties, provenance)
- Local graph neighborhood (related objects)
- Linked tasks and projects

### 1.2 Top-Level Modes Aligned with Academic Verbs

The proposed modes align with the core activities of academic knowledge work:

| Mode | Verb | Primary Activity |
|------|------|-----------------|
| **Read** | Consume & annotate | PDF/HTML reading with inline annotation |
| **Think** | Analyze & synthesize | Argument maps, concept maps, claim linking |
| **Organize** | Curate & classify | Library management, tagging, type assignment |
| **Plan** | Coordinate & schedule | Project templates, task boards, dependencies |
| **Publish** | Compose & export | Draft editing, reference formatting, export pipelines |

### 1.3 Mapping to SemPKM Architecture

SemPKM's existing dockview workspace (shipped in v2.3, Phase 30) provides the infrastructure for this kind of multi-pane, mode-switching interface:

- **Left pane**: Already exists as the sidebar with nav tree, type picker, and command palette access
- **Center pane**: Dockview panels already support tabbed object views, graph visualization, SPARQL console, and lint dashboard
- **Right pane**: Object detail views already show relations, lint results, and metadata in collapsible sections

The key gap is not architectural but content-level: SemPKM lacks a PDF/HTML reader, argument mapping tool, and draft editor. The dockview infrastructure could host these as new panel types.

### 1.4 Modes as Model-Contributed Views

The "Academic Persona" framing connects directly to SemPKM's installable mental models concept. Rather than hardcoding modes into the application, they could be:

- **Named layouts** (shipped in v2.3, Phase 33) that arrange dockview panels for specific workflows
- **Model-contributed view configurations** where a mental model's manifest declares "when in Read mode, show these panels in this arrangement"
- **Installable ontologies** that bring both the data types (Claim, Evidence, Argument) and the UI modes that work with them

This would allow an "Academic Research" mental model to install Read/Think/Organize/Plan/Publish modes alongside the entity types those modes operate on.

---

## 2. PKM/PIM Research Landscape

### 2.1 Origins and Evolution

PKM (Personal Knowledge Management) emerged in the late 1990s as an extension and critique of organizational KM. Where traditional KM focused on capturing and sharing institutional knowledge, PKM shifted focus to individual processes and tools -- how a person captures, organizes, retrieves, and applies knowledge in their own practice.

The field frames PKM as a response to information overload, spanning three concerns:
- **Personal information management** -- organizing digital artifacts
- **Contextualization** -- connecting information to personal meaning and projects
- **Personalization** -- adapting tools and workflows to individual needs
- **Lightweight sharing** -- selectively externalizing personal knowledge for collaboration

### 2.2 Key Literature

**Razmerita et al.** cataloged capture/organize/retrieve strategies across the PKM literature, establishing a vocabulary of core operations that recurs in tool design. Their reviews span HCI, KM, and education domains.

**Frand & Hixson** contributed early frameworks for understanding PKM as a learnable skill set, not just a tool category. Their work emphasizes that PKM tools succeed when they support cognitive processes, not just file management.

### 2.3 Empirical Work

Research on PKM support using wikis and Web 2.0 tools in online courses demonstrated that **structured personal spaces plus social features** help learners externalize and apply knowledge. Key findings:

- Students who maintained structured personal knowledge bases (not just notes) showed better retention and application
- Social features (sharing, commenting, collaborative curation) amplified individual PKM effectiveness
- The structure of the personal space mattered more than the specific tool -- templates and guided workflows outperformed blank-page approaches

### 2.4 Recent Trends

The PKM field has become increasingly multi-disciplinary, with tensions between individual and organizational goals. Notable developments:

- **AI integration**: LLM-assisted capture, summarization, and linking are becoming expected features in PKM tools
- **"Second brain" practices**: Popularized by Tiago Forte and others, emphasizing systematic capture-organize-distill-express workflows
- **Digital garden / networked thought**: Graph-based tools (Obsidian, Roam, Logseq) have mainstreamed the idea of interconnected notes over hierarchical filing

### 2.5 PIM Methodologies

Library and information science guides have formalized PKM for academics using established productivity frameworks:

- **GTD (Getting Things Done)**: Capture everything, clarify next actions, organize by context, review regularly, engage with confidence
- **PARA (Projects, Areas, Resources, Archives)**: Organize by actionability, not topic
- **Annotation + concept mapping workflows**: Structured annotation during reading supports later mapping and synthesis -- the reading-to-thinking pipeline

### 2.6 Project Management as Knowledge Work

Research highlights that control-oriented project management tools are insufficient for emergent, innovative tasks typical of academic work. Integrating KM principles into project management means:

- **Reflective practice**: Built-in review cycles, not just task completion
- **Learning loops**: Projects generate knowledge (not just deliverables) that feeds future work
- **Collaboration as knowledge exchange**: Team interactions are information-sharing events, not just coordination
- **Information dependency visualization**: Tools that surface "this task depends on understanding these concepts" improve productivity over simple task-to-task dependencies

### 2.7 Takeaways for SemPKM

1. **Vocabulary of core operations**: The PKM literature provides evidence-backed names for the operations a tool must support (capture, organize, retrieve, synthesize, express). SemPKM's typed entities and SHACL-driven forms align with the "structured personal spaces" that research shows are effective.

2. **Socio-technical nature of PKM**: Tools alone are insufficient -- PKM is a practice. SemPKM's mental models concept (installable ontologies with views and workflows) supports this by encoding practices as installable packages.

3. **Explicit support for reflection and learning**: Research projects need review cycles, not just task boards. This is a gap in SemPKM's current roadmap.

4. **Reusable workflow templates**: The research emphasis on templates for academic workflows parallels SemPKM's installable mental models. An "Empirical Study" or "Literature Review" template is essentially a specialized mental model.

---

## 3. Research-Backed Feature Checklist

### 3.1 Capture

**Integrated reading capture**: PDF/HTML reader with inline annotation and highlighting, producing structured notes (claims, evidence, questions, concepts). The research evidence shows that annotation combined with mapping improves comprehension and synthesis -- the pipeline from reading to structured knowledge is a critical path.

**Low-friction inboxes**: "Quick capture" from anywhere (browser extension, mobile, CLI) into a unified inbox. PKM literature consistently emphasizes frictionless capture as the first defense against information overload. If capture requires context-switching to the main application, material is lost.

**Multi-modal capture**: Text, images, links, code snippets, email excerpts, and chat fragments all become first-class nodes in the knowledge graph. The diversity of academic input sources (papers, slides, code, email threads, Slack conversations) demands multi-modal treatment.

### 3.2 Organize

**Typed entities with templates**: Distinct types (Work, Concept, Claim, Evidence, Project, Task, Review) with minimal templates defining required fields and relations, rather than relying solely on tags. PKM/PIM guidance consistently shows that structured personal spaces outperform unstructured ones -- but the structure must be lightweight and domain-appropriate.

**Flexible but opinionated hierarchies**: PPV-like chains (Pillar to Goal to Project to Action) AND lightweight patterns (PARA, GTD) as installable ontologies. The key insight is that no single hierarchy fits all users, but having no hierarchy leads to entropy. Installable ontologies let users choose their organizational framework.

**Faceted navigation**: Filter by type, topic, author, project, status, and context simultaneously. Library PIM advice and academic PKM guides emphasize that retrieval fails when the only access path is search -- faceted browsing complements full-text search for re-finding.

### 3.3 Retrieve & Sensemaking

**Graph-based search**: Semantic search over concepts, claims, projects, and annotations -- not just full-text keyword matching. PKM literature emphasizes re-finding and contextualization: "I know I read something about X in the context of project Y" requires graph-aware search.

**Argument and concept maps**: Visual maps constructed from annotations and links, using frameworks like AIF (Argument Interchange Format) and structured concept representations. Research evidence shows that reading combined with mapping improves understanding for complex academic tasks -- the visual synthesis step is where comprehension deepens.

**Question-centric views**: Explicit "research questions" and "problems" as first-class entities with linked evidence, claims, and open sub-questions. Knowledge work research shows that problem framing and iterative refinement drive quality -- questions are not just search queries but persistent investigative threads.

### 3.4 Plan & Execute

**Research project templates**: Reusable project templates encoding typical academic workflows such as "Empirical Study," "Theory Paper," and "Literature Review." Each template defines phases, expected deliverables, common subtask patterns, and linked entity types. Research on knowledge-intensive settings shows reusable workflows reduce cognitive overhead and encode institutional best practices.

**Integrated task boards**: Tasks as first-class nodes linked to Works, claims, and projects -- not isolated to-do items. States follow GTD/PPV patterns (Next, Waiting, Future, Done) with contexts (energy level, location, available time). The integration between tasks and knowledge objects distinguishes academic task management from generic project management.

**Dependency and information-flow views**: Visualizing "this task depends on understanding these claims / reading these Works" rather than just task-to-task sequencing. Research on team information interactions shows that revealing knowledge dependencies improves productivity and reduces redundant work.

### 3.5 Reflect & Learn

**Review cycles**: Built-in weekly, monthly, quarterly, and yearly review entities (following PPV methodology) with prompts and metrics. Metrics include claims clarified, open questions resolved, new concepts integrated, and projects advanced. The project-as-knowledge-work literature emphasizes that reflection and learning loops are what distinguish knowledge work from rote task execution.

**Learning metrics**: Non-gamified indicators that help users understand their knowledge growth without reducing it to points or streaks. Examples: "concepts strengthened" (claims with increasing evidence), "open decisions with weak evidence" (areas needing investigation), "papers annotated but not integrated" (capture without synthesis). PKM research focuses on learning and understanding over quantity.

### 3.6 Share & Publish

**Draft-from-graph workflows**: Generate outlines and drafts from argument and concept graphs. A user builds an argument map linking claims to evidence to sources, then the system generates a structured outline following the argument's logical flow. This implements the "express" phase from Tiago Forte's distill/express framework and maps to the academic writing process of moving from notes to draft.

**Export pipelines**: Multiple output formats preserving provenance and structure:
- **Markdown/LaTeX** for academic writing workflows
- **Reference manager formats** (BibTeX, RIS) for bibliography management
- **Nanopublications** for structured, attributable scientific claims
- **ClaimReview** for fact-checking and claim verification contexts
- **Institutional repository formats** for archival and discovery

### 3.7 Collaboration & Social PKM

**Shared annotation and argument spaces**: Group annotation layers where multiple users annotate the same documents, and shared argument graphs where team members contribute claims and evidence to collective reasoning. Research on wiki-based PKM in education and collaborative annotation shows that social knowledge construction amplifies individual understanding.

**Team/project dashboards**: Multi-person project views showing shared reading progress (who has read what), argument coverage (which claims have evidence, which are contested), and knowledge gaps (areas where the team lacks expertise or evidence). Project management as knowledge work research shows that making knowledge state visible across a team improves coordination.

---

## 4. Key Integrations & Standards

### 4.1 Hypothes.is / W3C Web Annotation

[Hypothes.is](https://web.hypothes.is/) is an open annotation layer for the web, implementing the [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/). Annotations are structured JSON-LD with selectors (TextQuoteSelector, TextPositionSelector, etc.) pointing to specific content ranges.

**Relevance to SemPKM:** The RSS Reader & Hypothesis Integration milestone already plans Hypothesis annotation sync (Phase 6 of that milestone). The academic workspace research reinforces this as a high-priority integration -- annotations are the bridge between reading capture and structured knowledge. W3C Web Annotation is inherently RDF-compatible (JSON-LD), making it a natural fit for SemPKM's triplestore.

### 4.2 BIBFRAME

[BIBFRAME (Bibliographic Framework)](https://www.loc.gov/bibframe/) is the Library of Congress's RDF-based replacement for MARC records. It models bibliographic description as Works (abstract intellectual content), Instances (specific editions/formats), and Items (individual copies).

**Relevance to SemPKM:** BIBFRAME could serve as the vocabulary for a "Library" or "Bibliography" mental model, providing structured metadata for academic sources. This extends the mental model system (v1.0 Phase 3) with a domain-specific ontology. BIBFRAME's Work/Instance/Item hierarchy maps well to how academics think about sources (the paper vs. the PDF vs. the annotated copy).

### 4.3 Nanopublications / ClaimReview

[Nanopublications](https://nanopub.net/) are minimal units of publishable information: an assertion (the claim), provenance (who said it, based on what), and publication info (when, where). [ClaimReview](https://schema.org/ClaimReview) is Schema.org's vocabulary for fact-checking.

**Relevance to SemPKM:** These represent structured, attributable knowledge claims -- exactly what SemPKM's typed entities could model. A "Research Claims" mental model could define Claim, Evidence, and Review types that export as nanopublications. This is entirely new territory for SemPKM's roadmap.

### 4.4 Reference Managers (Zotero, Mendeley)

Academic workflows depend on reference managers for bibliography management. Integration points include:
- **Import**: Zotero RDF export, BibTeX import, CSL-JSON
- **Sync**: Zotero API for bidirectional library sync
- **Citation**: Generate citations from SemPKM objects in standard formats

**Relevance to SemPKM:** Not currently on the roadmap. Reference manager integration is a common expectation for academic tools and could be implemented as a mental model (types + sync service) or a dedicated integration milestone.

### 4.5 ORCID

[ORCID](https://orcid.org/) provides persistent digital identifiers for researchers. The ORCID API allows retrieving researcher profiles, publications, and affiliations.

**Relevance to SemPKM:** ORCID integration connects to the Identity: WebID + IndieAuth milestone. WebID profiles could include ORCID identifiers, and Person entities could link to ORCID profiles for disambiguation. This is a natural extension of the planned identity work.

### 4.6 Relationship to Existing SemPKM Standards

SemPKM already uses several standards that the academic workspace features build upon:

| Standard | Current Use | Academic Extension |
|----------|------------|-------------------|
| **RDF** | Core data model | All proposed features are RDF-native |
| **SHACL** | Form generation, validation | Shapes for Claim, Evidence, Argument types |
| **OWL** | Inference (v2.4) | Ontological relationships between academic concepts |
| **SKOS** | Concept hierarchies | Thesaurus/taxonomy for research domains |
| **Dublin Core** | Basic metadata | Extended bibliographic metadata |
| **FOAF** | Person entities | Researcher profiles, co-authorship |
| **Schema.org** | General metadata | Article, CreativeWork, Review types |

---

## 5. Cross-Reference with SemPKM Roadmap

### 5.A Already Covered by Existing/Shipped Milestones

These features are substantially addressed by SemPKM's current implementation:

| Feature | Roadmap Coverage |
|---------|-----------------|
| Typed entities with templates | v1.0 Phase 3: Mental Model System -- SHACL shapes define types with fields and relations |
| Flexible hierarchies (PPV, PARA, GTD) | v1.0 Phase 3 + Quick Task 24: PPV mental model installed; any hierarchy is an installable ontology |
| Graph visualization | v1.0 Phase 5: Data Browsing and Visualization -- force-directed graph with navigation |
| Dark mode and visual polish | v2.0 Phase 13: Dark Mode and Visual Polish |
| Faceted navigation (by type) | v2.0 Phase 12: Sidebar and Navigation -- nav tree filtered by type |
| Full-text keyword search | v2.2 Phase 24: FTS Keyword Search + v2.3 Phase 29: FTS Fuzzy Search |
| SPARQL query interface | v2.2 Phase 23: SPARQL Console |
| Flexible panel workspace | v2.3 Phase 30: Dockview Migration -- arbitrary panel arrangement |
| Named layouts / saved workspaces | v2.3 Phase 33: Named Layouts |
| Object views (read/edit/flip) | v2.3 Phase 31: Object View Redesign |
| OWL inference / bidirectional links | v2.4 Phase 35: OWL 2 RL Inference |
| SHACL-AF derived triples | v2.4 Phase 36: SHACL-AF Rules Support |
| Global lint/validation dashboard | v2.4 Phases 37-38: Lint Data Model, API, and Dashboard UI |
| Settings system | v2.0 Phase 15: Settings System |

### 5.B Extends Planned Milestones

These features build on existing roadmap items but go further than currently planned:

| Feature | Extends Milestone | How It Extends |
|---------|------------------|----------------|
| Hypothes.is annotation sync | RSS Reader & Hypothesis Integration | Already planned as Phase 6; academic research reinforces priority and adds structured annotation-to-claim pipelines |
| W3C Web Annotation storage | RSS Reader & Hypothesis Integration | Already planned; academic use case adds annotation-to-concept-map workflows |
| Argument/concept maps | Graph visualization (v1.0 Phase 5) | Current graph shows entity relationships; argument maps need typed edges (supports, contradicts, qualifies) and layout algorithms for argumentation |
| BIBFRAME bibliographic metadata | Mental Model System (v1.0 Phase 3) | New mental model using BIBFRAME vocabulary -- extends the model packaging pattern |
| Export pipelines (Markdown/LaTeX) | Web Components for Mental Models (Potential Idea) | Export could be a model-contributed capability; LaTeX/BibTeX generation is domain-specific |
| Integrated task boards | Low-Code UI Builder & Workflows (Potential Idea) | Task boards linked to knowledge objects extend the workflow orchestration concept |
| Shared annotation spaces | Collaboration & Federation | Shared annotation layers extend the named graph sync with annotation-specific UI |
| Team/project dashboards | Collaboration & Federation (Phase E) | Already sketched as "Collaboration UI"; academic use case adds knowledge-gap analysis |
| Graph-based semantic search | SPARQL Interface (Phase 2: Autocomplete) | Ontology-aware autocomplete is planned; semantic similarity search (embeddings) goes further |
| ORCID researcher identity | Identity: WebID + IndieAuth | WebID profiles could include ORCID links; natural extension of identity work |
| Dependency/info-flow views | Low-Code UI Builder & Workflows (Potential Idea) | Information dependency visualization extends basic task dependency tracking |

### 5.C Entirely New Feature Areas Not on Roadmap

These features have no current roadmap coverage and would require new milestones or significant additions to existing ones:

| Feature | Description | Alignment with SemPKM Architecture |
|---------|-------------|-------------------------------------|
| **PDF/HTML reading capture** | In-app reader with inline annotation producing structured notes | High -- annotations are RDF (W3C Web Annotation); needs PDF rendering component |
| **Low-friction inboxes** | Quick capture from browser, mobile, CLI into unified inbox | Medium -- requires browser extension, mobile app, or API endpoint; inbox is a typed entity |
| **Multi-modal capture** | Images, code snippets, email, chat fragments as first-class nodes | Medium -- extends object creation; needs file attachment support and content extractors |
| **Question-centric views** | Research questions as persistent entities with linked evidence/claims | High -- naturally modeled as a mental model type with SHACL shapes; needs dedicated view |
| **Research project templates** | Reusable templates for "Empirical Study," "Lit Review," etc. | High -- directly maps to mental models with pre-configured types, views, and workflows |
| **Review cycles** | Weekly/monthly/quarterly review entities with prompts and metrics | High -- review is a typed entity; metrics computed from graph queries; needs scheduling |
| **Learning metrics** | Non-gamified indicators (concepts strengthened, gaps identified) | High -- computed from SPARQL queries over the knowledge graph; needs dashboard UI |
| **Draft-from-graph publishing** | Generate outlines/drafts from argument and concept maps | Medium -- requires text generation from graph traversal; optional LLM integration |
| **Nanopublication export** | Export structured claims as nanopublications | High -- nanopub format is RDF; SemPKM's typed entities map directly |
| **ClaimReview export** | Export fact-checking structured data | Medium -- Schema.org ClaimReview is RDF; needs claim type definition |
| **Reference manager integration** | Zotero/Mendeley sync, BibTeX import/export | Medium -- Zotero has an API; BibTeX is parseable; needs sync service |
| **Concept/argument mapping tool** | Visual argument construction with typed edges | Medium -- extends graph viz with editable argument-specific layout |

---

## 6. Implications for SemPKM

### 6.1 Highest Architectural Alignment

The following new feature areas align most naturally with SemPKM's existing RDF/SHACL architecture and could be implemented with the least friction:

1. **Question-centric views and research project templates** -- These are essentially new mental models. A "Research Methodology" model could define Question, Hypothesis, Method, Finding, and Review types with SHACL shapes, views, and named layouts. No new infrastructure required; just model packaging.

2. **Review cycles and learning metrics** -- Reviews are typed entities. Metrics are SPARQL queries over the existing graph (count of claims with evidence, open questions without answers, annotated-but-unintegrated sources). The lint dashboard pattern (v2.4 Phase 38) provides a template for the metrics UI.

3. **Nanopublication and ClaimReview export** -- Both formats are RDF. SemPKM already stores structured claims as typed entities. Export is a serialization problem, not an architectural one. Could be implemented as an API endpoint or model-contributed export action.

4. **BIBFRAME bibliographic model** -- Another installable mental model. The Work/Instance/Item hierarchy maps to SHACL node shapes. Import from BibTeX/RIS could be a model-contributed utility.

### 6.2 Mental Model vs. Core Platform

| Approach | Features |
|----------|----------|
| **Installable Mental Model** | Research project templates, BIBFRAME bibliography, question-centric entities, review cycle entities, nanopub types, ClaimReview types, PPV-style hierarchies (already done) |
| **Core Platform Extension** | PDF/HTML reader, low-friction capture (browser extension), multi-modal file attachments, argument mapping UI, draft-from-graph generation, reference manager sync, learning metrics dashboard |
| **Integration Service** | Zotero sync, ORCID lookup, Hypothes.is sync (already planned), LLM-assisted linking |

The mental model approach handles entity types and views; core platform extensions handle new UI components and external service integrations. This distinction is important: mental models should not require new platform capabilities to function.

### 6.3 Suggested Priority Ordering for Future Consideration

Based on architectural alignment, user value, and implementation effort:

**Tier 1 -- High alignment, low effort (mental model packages):**
1. Research methodology mental model (questions, hypotheses, findings, reviews)
2. BIBFRAME bibliography mental model
3. Review cycles and learning metrics (SPARQL-computed, dashboard UI)

**Tier 2 -- High value, moderate effort (platform extensions):**
4. PDF/HTML reading with annotation (W3C Web Annotation, extends RSS Reader milestone)
5. Reference manager integration (Zotero API, BibTeX import)
6. Nanopublication/ClaimReview export endpoints

**Tier 3 -- High value, high effort (new subsystems):**
7. Argument/concept mapping tool (visual editor with typed edges)
8. Draft-from-graph publishing (text generation from graph traversal)
9. Low-friction capture ecosystem (browser extension, mobile, CLI)

**Tier 4 -- Dependent on other milestones:**
10. Shared annotation spaces (depends on Collaboration & Federation)
11. Team knowledge dashboards (depends on Collaboration & Federation)
12. Multi-modal capture (depends on file attachment infrastructure)

### 6.4 Note on Scope

This analysis is purely informational. The features identified here represent research-backed possibilities, not commitments. Many of the Tier 1 items could be created as community-contributed mental models rather than project-maintained features. The strength of SemPKM's architecture is that domain-specific knowledge structures (academic research, bibliographic management, project methodology) can be packaged and shared without modifying the core platform.

---

*Research conducted: 2026-03-05*
*Source: Perplexity Deep Research chat analyzing academic workspace UI design, PKM/PIM literature, and research-backed feature requirements*
*Cross-referenced against: SemPKM ROADMAP.md (milestones v1.0 through v2.4 + future milestones)*

# Collaboration & Federation Architecture Research

**Created:** 2026-03-03
**Context:** Deep research into how SemPKM (self-hosted, RDF triplestore-backed PKM) could support teams and collaboration. Evaluated SOLID, ActivityPub/Fediverse, RDF sync protocols, CRDTs, and hypertext-native patterns.

---

## Executive Summary

No single protocol is production-ready for collaborative RDF knowledge management in 2026. The recommended path is a **layered, incremental architecture** built on proven components: RDF Patch for change tracking, SPARQL Graph Store Protocol for graph exchange, Linked Data Notifications for cross-instance awareness, and WebID for federated identity. Real-time co-editing via CRDTs should wait for the W3C CRDT-for-RDF standardization effort to mature.

---

## 1. SOLID (Social Linked Data) Protocol

### How It Works

A [SOLID Pod](https://solidproject.org/) is a personal data store where all data lives as Linked Data resources (Turtle/JSON-LD) accessible via HTTP. Pods implement [LDP (Linked Data Platform)](https://www.w3.org/TR/ldp/) — data organized into containers holding resources. Authentication uses [WebID](https://www.w3.org/wiki/WebID) and [Solid-OIDC](https://solid.github.io/solid-oidc/). Access control via [WAC (Web Access Control)](https://solidproject.org/TR/wac) or ACP.

### Current State (2024-2026)

- **Governance:** [ODI took stewardship](https://theodi.org/news-and-events/news/odi-and-solid-come-together-to-give-individuals-greater-control-over-personal-data/) of Solid in October 2024
- **W3C:** [Linked Web Storage WG](https://www.w3.org/2024/09/linked-web-storage-wg-charter.html) targeting Candidate Recommendation by March 2026, full Rec by September 2026
- **Servers:** [Community Solid Server](https://github.com/CommunitySolidServer/CommunitySolidServer) (TypeScript, experimental TRL 1-3), [Enterprise Solid Server](https://www.inrupt.com/blog/enterprise-server-release) (Inrupt, commercial)
- **SHACL integration:** The [Solid Application Interoperability](https://solid.github.io/data-interoperability-panel/specification/) spec uses shapes for data validation — direct alignment with SemPKM

### Honest Assessment

A [detailed developer critique](https://blog.ldodds.com/2024/03/12/baffled-by-solid/) raises concerns: no commercial Pod hosting, no query API (document store not triplestore), poor UIs, missing pagination/search/timestamps. A [Solid app developer confirms](https://noeldemartin.com/blog/why-solid) RDF complexity and authentication friction remain pain points.

### Verdict for SemPKM

**Philosophically aligned, practically mismatched.** Pods are document stores — no SPARQL. Our triplestore *is* the data store. Monitor W3C standardization but don't adopt as infrastructure. Potentially useful as an interoperability target (export/import to Pods).

---

## 2. ActivityPub / Fediverse

### How It Works

[ActivityPub](https://www.w3.org/TR/activitypub/) (W3C Recommendation) has two sub-protocols: Client-to-Server (apps POST to user outbox) and Server-to-Server (servers deliver to recipient inboxes). Activities are JSON-LD documents — inherently RDF, though most implementations treat as opaque JSON.

### Non-Social Uses

- **[ForgeFed](https://forgefed.org/):** Federated code forges (Gitea/Forgejo cross-instance issues and merge requests)
- **[Bonfire](https://bonfirenetworks.org/):** Modular federated platform for coordination, governance, groups ([TechCrunch coverage](https://techcrunch.com/2025/06/05/bonfires-new-software-lets-users-build-their-own-social-communities-free-from-platform-control/))
- **[ActivityPods](https://activitypods.org/):** Combines ActivityPub federation with Solid Pod storage; [v2.0 roadmap](https://activitypods.org/the-road-to-activitypods-2-0) adds CRDT-based RDF sync via NextGraph partnership
- **[rdf-pub](https://rdf-pub.org/):** ActivityPub server supporting full RDF (not limited to ActivityStreams), uses rdf4j — pre-alpha
- **openEngiadina/CPub:** Attempted full RDF ActivityPub — [development discontinued](https://codeberg.org/openengiadina/cpub/), moved to XMPP

### Knowledge Sharing Pattern

[SocialHub discussion](https://socialhub.activitypub.rocks/t/federated-knowledge-management-with-activitypub/2991) proposes dual compatibility: generic fediverse services see basic title/summary, specialized nodes interpret full structured RDF data. Directly applicable to SemPKM.

### Verdict for SemPKM

**Good transport layer, wrong data model.** JSON-LD payloads map directly to our RDF, but the protocol is designed for social streams not knowledge graphs. The RDF-native implementations have failed or stalled. Use selectively for notifications/sharing, not as primary sync.

---

## 3. RDF Synchronization

### RDF Patch / RDF Delta

[RDF Patch](https://afs.github.io/rdf-patch/) is a text format for triple-level changes: `A <s> <p> <o>` (add), `D <s> <p> <o>` (delete), wrapped in transactions. [RDF Delta](https://afs.github.io/rdf-delta/) builds a replication system on top: a Delta Server hosts patch logs, clients fetch since last known version. Supports "Replicated Fuseki." **Note:** [RDF Delta is archived](https://github.com/afs/rdf-delta) (unmaintained), but concepts remain foundational.

### Jelly-Patch (2025)

[Jelly-Patch](https://jelly-rdf.github.io/dev/) is a binary RDF patch format built on Protocol Buffers. Published at SEMANTiCS 2025 ([paper](https://arxiv.org/html/2507.23499v1)): 3.5-8.9x better compression, up to 2.5x serialization throughput, 4.6x parsing throughput vs text-based patches. Java implementation (Apache 2.0); Python/Rust planned.

### SPARQL Graph Store Protocol

[W3C SPARQL 1.1 Graph Store HTTP Protocol](https://w3c.github.io/sparql-graph-store-protocol/) provides REST ops on named graphs: GET, PUT, POST (merge), DELETE. Coarse-grained (whole graphs) but directly supported by Fuseki/RDF4J.

### Linked Data Notifications (LDN)

[W3C Recommendation](https://www.w3.org/TR/ldn/) for decentralized notifications. Senders POST JSON-LD to receiver's Inbox (LDP container). Used for [credential exchange between Solid Pods](https://ceur-ws.org/Vol-3705/short04.pdf). Lightweight, RDF-native.

### Changeset Vocabularies

- **ChangeSet vocabulary:** Resource-centric, linking statements-to-add/remove
- **[eccrev (eccenca Revision Vocabulary)](https://github.com/eccenca/eccrev-vocab):** Based on Delta ontology, reuses PROV-O for provenance
- **[PROV-O](https://www.w3.org/TR/prov-o/):** W3C provenance ontology for who/when/why metadata

### Verdict for SemPKM

**The most practical building blocks.** RDF Patch is simple enough to implement in Python. Graph Store Protocol works with our existing triplestore. LDN adds lightweight notifications. These form the foundation of Layer 1 and Layer 2 in the recommended architecture.

---

## 4. Hypertext / Web-Native Collaboration

### Webmention

[W3C Recommendation](https://www.w3.org/TR/webmention/) for peer-to-peer web notifications. When site A links to site B, A sends an HTTP POST to B's endpoint. B can display it as a comment/reference. Simple, [well-adopted in IndieWeb](https://indieweb.org/Webmention).

### Linked Data Platform (LDP)

[W3C LDP 1.0](https://www.w3.org/TR/ldp/) defines REST patterns for RDF resource management: LDP Resources (documents via GET/PUT/DELETE), LDP Containers (collections, POST to create). Solid is built as an LDP profile. [Multiple implementations](https://www.w3.org/wiki/LDP_Implementations) (Fedora, Carbon LDP, Eclipse Lyo).

### Content-Addressable RDF

- **[IPLD (InterPlanetary Linked Data)](https://docs.ipfs.tech/concepts/merkle-dag/):** Merkle DAGs with hash-based addressing, used by IPFS
- **Timestamp-based integrity proofs:** Sorted Merkle trees from RDF datasets for verification
- Enables: verifiable snapshots, deduplication during sync, tamper detection

### dokieli

[dokieli](https://dokie.li/) ([paper](https://csarven.ca/dokieli-rww)) is a fully decentralized browser-based authoring platform: HTML+RDFa documents, LDP for storage, LDN for notifications, WebID for auth. Proves decentralized RDF collaboration works for real-world authoring.

### Verdict for SemPKM

**Webmention and LDN are low-hanging fruit** for cross-instance awareness. LDP provides clean CRUD if we ever expose graphs as web resources. Content-addressing is future-state for verification.

---

## 5. Self-Hosted + Cloud Coordination Patterns

### Matrix Protocol Model

[Matrix](https://matrix.org/) is federated real-time communication: event-based DAG in rooms, full state replication, E2E encryption, self-hostable. A [5-year self-hosting retrospective](https://yaky.dev/2025-11-30-self-hosting-matrix/) confirms viability but notes resource intensity. **Insight:** Matrix's "room" model maps well to "shared named graphs."

### Git-Like Sync for RDF

- **[Quit Store (Quads in Git)](https://github.com/AKSW/QuitStore):** Python-based, stores named graphs as N-Triples in Git, provides SPARQL 1.1 endpoint, supports branching/merging/push/pull. 1,031 commits, last significant activity 2022.
- **[Radicle](https://radicle.xyz):** P2P code collaboration on Git. Not RDF-specific but its replication model could inform graph sharing.

### CRDTs for RDF

**[W3C CRDT for RDF Community Group](https://www.w3.org/community/crdt4rdf/)** (est. October 2024, 27 members): coordinating efforts to specify CRDTs for RDF.

**[NextGraph](https://nextgraph.org/):** Novel CRDT designed for RDF, P2P, E2E encrypted, uses Oxigraph locally. Alpha stage, SDK published July 2025. [Partnering with ActivityPods](https://activitypods.org/activitypods-and-nextgraph-are-joining-forces) to replace Jena Fuseki.

**[m-ld](https://m-ld.org/doc/):** Decentralized live RDF sharing, embeds as library, eventual consistency, pluggable messaging. JS-only developer preview. [Paper](https://ceur-ws.org/Vol-2941/paper1.pdf).

### Pattern Comparison

| Pattern | Examples | Pros | Cons |
|---------|----------|------|------|
| **Hub-and-spoke cloud** | Notion, Google Docs | Simple, strong consistency | Single point of failure, data sovereignty |
| **Federated (S2S)** | Matrix, ActivityPub, Email | Self-hostable, resilient, proven | Complex state resolution, server-bound identity |
| **Peer-to-peer** | NextGraph, Radicle | Max sovereignty, offline-first | NAT traversal, discovery, key management |
| **Git-like (DVCS)** | Quit Store | Familiar, branching/merging, full history | RDF merge conflicts hard, no real-time |

### Verdict for SemPKM

**Federated (server-to-server) is the pragmatic choice** for self-hosted scenarios. CRDTs for RDF are the future but pre-standard. Quit Store's concepts (Git-backed graphs) could inform our versioning layer. NextGraph is the one to watch for Layer 4.

---

## 6. Real-World Examples

| Tool | Model | Lesson for SemPKM |
|------|-------|--------------------|
| **[Semantic MediaWiki](https://www.semantic-mediawiki.org/)** | Wiki editing + version history, 10+ years production | Simplest model wins. RDF behind the scenes. |
| **[dokieli](https://dokie.li/)** | Decentralized RDF authoring, LDP+LDN+WebID | Proves decentralized RDF collaboration works |
| **[Relay for Obsidian](https://relay.md/)** | CRDT-based folder-level sharing plugin | Local-first PKM adds collab via plugins, not core rewrites |
| **[ActivityPods](https://activitypods.org/)** | Solid + ActivityPub + NextGraph convergence | Most ambitious integration; too early to adopt |
| **Notion** | Cloud-first, operational transform | Users expect seamless real-time — anything less feels broken |

---

## Recommended Architecture: Layered & Incremental

Rather than betting on a single protocol, build incrementally using proven components:

### Layer 1: Named Graph Sync (Build First)

**Pattern:** RDF Patch logs + HTTP sync endpoint

1. Wrap triplestore writes to emit RDF Patch log entries
2. Expose a `/sync` endpoint serving patches since a given version
3. "Remote" configuration pointing to other SemPKM instances
4. Pull-based sync: periodically fetch patches from configured remotes
5. Named graph-level conflict detection (reject if base version diverged)

**Why first:** Uses existing triplestore, no new infra, solves core "share knowledge between instances" use case.

### Layer 2: Cross-Instance Notifications (Build Second)

**Pattern:** Linked Data Notifications + Webmention

- Instance A modifies a subscribed graph → sends LDN notification to instance B
- Instance A references instance B's content → sends Webmention
- Notifications trigger pull-based sync from Layer 1

### Layer 3: Federated Identity (Build Third)

**Pattern:** WebID for cross-instance identity

- Each SemPKM user gets a WebID (profile URL on their instance)
- Cross-instance permissions use WebID to identify remote users
- ACL on named graphs references WebIDs
- Local auth unchanged

### Layer 4: Real-Time Collaboration (Future)

**Pattern:** CRDT-based RDF sync (when ecosystem matures)

- Monitor W3C CRDT for RDF CG
- Watch NextGraph alpha → stable progression
- Integrate when mature Python/JS CRDT-for-RDF library exists

### What NOT to Build

- **Don't build a Solid Pod server** — different problem (app-data separation), no SPARQL
- **Don't implement full ActivityPub S2S** — enormous complexity, wrong use case
- **Don't build a custom CRDT** — W3C is standardizing this, wait
- **Don't try P2P yet** — NAT traversal unsolved for self-hosted; federated is pragmatic

---

## Technology Fitness Matrix

| Technology | SemPKM Fit | Maturity | Effort | Recommendation |
|-----------|-----------|----------|--------|----------------|
| RDF Patch | Excellent | Proven format | Medium | **Build Layer 1 on this** |
| Graph Store Protocol | Excellent | W3C Rec | Low | Use for full graph exchange |
| Linked Data Notifications | Good | W3C Rec | Low | **Build Layer 2 on this** |
| WebID | Good | W3C | Medium | **Build Layer 3 on this** |
| Webmention | Moderate | W3C Rec | Low | Add for cross-referencing |
| ActivityPub (C2S only) | Moderate | W3C Rec | High | Consider for external API |
| SOLID Protocol | Low-Moderate | Pre-Rec | Very High | Monitor only |
| NextGraph CRDT | High (future) | Alpha | N/A | **Monitor for Layer 4** |
| m-ld | Moderate | JS-only preview | High | Monitor |
| Quit Store | Moderate | Unmaintained | Medium | Borrow concepts |

---

## Projects to Watch

- **[NextGraph](https://nextgraph.org/)** — RDF CRDT, E2E encrypted, P2P. If it reaches stable, could be turnkey Layer 4
- **[W3C CRDT for RDF CG](https://www.w3.org/community/crdt4rdf/)** — standardization progress
- **[ActivityPods 2.0](https://activitypods.org/our-roadmap-for-2025)** — Solid + ActivityPub + NextGraph convergence
- **[Jelly-Patch](https://jelly-rdf.github.io/dev/)** — when Python/Rust implementations land
- **[Linked Web Storage WG](https://www.w3.org/2024/09/linked-web-storage-wg-charter.html)** — Solid standardization timeline

---

*Research conducted: 2026-03-03*
*Sources: 40+ web pages across W3C specs, GitHub repos, developer blogs, academic papers, and project documentation*

# Decentralized Identity Research

**Created:** 2026-03-03
**Context:** Research into how SemPKM (self-hosted, RDF triplestore-backed PKM) could serve as an identity provider and integrate with decentralized identity systems. Evaluated DIDs, Verifiable Credentials, WebID, IndieAuth, and specific DID methods.

---

## Executive Summary

SemPKM has a natural advantage: DID Documents and Verifiable Credentials are JSON-LD (which is RDF), so they'd live natively in the triplestore. The recommended approach is tiered: start with WebID profiles + IndieAuth (days of work, immediate interoperability), then add did:web + RDF graph signing (cryptographic provenance), then Verifiable Credentials (knowledge attestation). Key management should be server-managed — users should never handle cryptographic keys directly.

---

## 1. W3C Decentralized Identifiers (DIDs)

### Specification Status

- [DID 1.0](https://www.w3.org/press-releases/2022/did-rec/) became a W3C Recommendation on July 19, 2022 (despite formal objections from Google, Apple, Mozilla)
- [DID 1.1](https://www.w3.org/TR/did-1.1/) is currently a Candidate Recommendation (incremental update)
- A new [DID Methods Working Group](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html) chartered to standardize at least three methods: one ephemeral, one web-based, one fully decentralized

### DID Methods Relevant to Self-Hosted Apps

**[did:key](https://w3c-ccg.github.io/did-key-spec/)** — Simplest method: public key IS the identifier. Zero infrastructure, purely generative. No key rotation or deactivation. Best for ephemeral interactions, testing, short-lived sessions.

**[did:web](https://w3c-ccg.github.io/did-method-web/)** — Maps DIDs to HTTPS. `did:web:example.com:users:alice` resolves to `https://example.com/users/alice/did.json`. No blockchain, just serve JSON. Supports key rotation (update the doc) but no cryptographic audit trail. Inherits DNS/TLS vulnerabilities.

**[did:plc](https://web.plc.directory/spec/v0.1/did-plc)** — Bluesky's method. Self-authenticating operation log with 72-hour recovery window. DID is hash of genesis operation. Currently relies on single directory server (plc.directory). Production-proven at 25M+ Bluesky users.

**[did:dht](https://did-dht.com/)** — Uses BitTorrent's Mainline DHT for resolution. Ed25519 identity key. Fully decentralized, relatively new.

**[did:webvh](https://identity.foundation/didwebvh/v0.3/)** (formerly did:tdw) — "Trust DID Web with Verifiable History." Enhances did:web with `did.jsonl` cryptographic chain, self-certifying identifier (SCID), pre-rotation, optional witnesses. Fixes did:web's trust gaps while keeping ease of deployment. **Python implementation exists (~1500 LOC).**

### DID Documents

JSON-LD documents containing verification methods (public keys), authentication methods, assertion methods, service endpoints, and controller info. Use `@context` of `https://www.w3.org/ns/did/v1` — **natively RDF**, processable as triples. Directly fits SemPKM's triplestore.

### Libraries

- **DIDKit** (Spruce): Rust core with Python bindings (`pip install didkit`). Supports did:key, did:web, VC issuance/verification. **Python bindings archived July 2025** — team recommends [`ssi`](https://github.com/spruceid/ssi) Rust library directly.
- **[PyLD](https://github.com/digitalbazaar/pyld)**: Python JSON-LD processor, essential for URDNA2015 canonicalization
- **python-cryptography**: Ed25519, secp256k1, P-256 key operations
- **[Veramo](https://veramo.io/)** (JS): Full DID/VC framework in TypeScript
- **[Universal Resolver](https://github.com/decentralized-identity/universal-resolver)**: Single interface to resolve any DID method

### Controversy

[W3C overruled formal objections](https://www.theregister.com/2022/07/01/w3c_overrules_objections/) from Google, Apple, Mozilla. Key criticisms: 180+ non-interoperable methods ("namespace land rush"), some rely on blockchains, no privacy requirements. Valid at ecosystem level but less relevant when choosing a specific, well-understood method like did:web.

---

## 2. W3C Verifiable Credentials (VCs)

### Specification Status

[Verifiable Credentials 2.0](https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/) became a W3C Recommendation on May 15, 2025. Seven specs including [VC Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/), Data Integrity 1.0, Bitstring Status List, JOSE/COSE securing, EdDSA/ECDSA cryptosuites.

### Issuer-Holder-Verifier Model

1. **Issuer** creates credential asserting claims about subject, signs with DID assertion key
2. **Holder** stores credential
3. **Holder** presents to **Verifier**
4. **Verifier** checks signature validity, issuer trust, revocation status, claims

VCs are JSON-LD with `@context` including `https://www.w3.org/ns/credentials/v2` — natively RDF.

### Credentials a PKM Tool Could Issue

| Credential Type | Description | Value |
|---|---|---|
| **Authorship Attestation** | "User X authored graph Y on date Z" | Provenance for shared knowledge |
| **Knowledge Contribution** | "User X contributed N triples to domain Y" | Reputation/portfolio |
| **Membership Credential** | "User X is a member of instance at domain.com" | Cross-instance auth |
| **Data Integrity Certificate** | "Named graph X has hash Y, signed by instance Z" | Tamper-evident sharing |
| **Peer Review** | "User X reviewed/endorsed graph Y" | Trust chains |

### Python Libraries

- **DIDKit** (archived but functional): `didkit.issue_credential()`, `didkit.verify_credential()`
- **PyLD + cryptography**: Manual VC construction via [URDNA2015 canonicalization workflow](https://grotto-networking.com/blog/posts/jsonldProofs.html)
- **ACA-Py** (Hyperledger Aries): Full VC lifecycle agent, but heavyweight

---

## 3. WebID

### How It Works

A [WebID](https://w3c.github.io/WebID/spec/identity/index.html) is an HTTP(S) URI denoting an agent. Dereferencing returns an RDF document (Turtle/JSON-LD) describing the agent with FOAF/schema.org properties.

Example: `https://sempkm.example.com/users/alice#me` — fragment `#me` refers to person, document URL returns RDF profile.

### Authentication Mechanisms

- **WebID-TLS** (deprecated): Client-side TLS certs. Browser support degraded.
- **WebID-OIDC** (v0.1.0, 2022): Layer on OpenID Connect with Proof of Possession tokens.
- **[Solid-OIDC](https://solid.github.io/solid-oidc/)**: Current Solid auth spec. Still in draft.

### SemPKM as WebID Provider

SemPKM already stores user data as RDF. Serving [WebID Profile Documents](https://solid.github.io/webid-profile/) at user URLs with content negotiation is ~1 day of work. Include FOAF properties, public keys, `solid:oidcIssuer`. Compatible with Solid ecosystem and any Linked Data consumer.

---

## 4. did:web for SemPKM — Detailed

### Resolution

`did:web:sempkm.example.com:users:alice` → `https://sempkm.example.com/users/alice/did.json`

Two FastAPI routes:
```python
@app.get("/.well-known/did.json")       # Instance DID
@app.get("/users/{username}/did.json")   # Per-user DIDs
```

### Pros
- Zero additional infrastructure
- Globally resolvable DIDs mapping to existing URL structure
- W3C DID Methods WG actively standardizing
- Path-based DIDs for per-user identities

### Cons
- DNS dependency: identity security = DNS + TLS security
- No cryptographic audit trail (update document = no history)
- Server operator can change any user's DID Document
- Privacy: DNS providers and server logs track resolution

### Upgrade Path: did:webvh
Start with did:web (minimal effort), upgrade to [did:webvh](https://identity.foundation/didwebvh/v0.3/) when spec stabilizes. did:webvh adds cryptographic version chain, pre-rotation, witnesses, and portability across domains. Python implementation exists.

---

## 5. AT Protocol / did:plc

### How did:plc Works

Operation log with genesis → updates → recovery. DID is SHA-256 hash of genesis operation. 72-hour recovery window via higher-authority rotation keys. Currently relies on plc.directory (centralization risk, being addressed via Swiss association governance).

### Could SemPKM Participate?

Theoretically possible, practically challenging:
- AT Protocol data model (signed record repos) fundamentally different from RDF triplestores
- Custom [Lexicons](https://docs.bsky.app/docs/advanced-guides/custom-schemas) could represent knowledge, but bridging is enormous effort
- [2025 roadmap](https://docs.bsky.app/blog/2025-protocol-roadmap-spring): 41M+ users, PDS web interface, shared/group-private data planned

### did:plc vs did:web

| Aspect | did:plc | did:web |
|---|---|---|
| Key rotation | Full with audit trail | Replace doc, no audit |
| Recovery | 72-hour window | None |
| Infrastructure | Requires plc.directory | Just HTTPS |
| Self-hosted | Not really | Yes, fully |
| Portability | Full (survives domain changes) | None (domain-bound) |
| Maturity | Production (25M+ users) | Wide adoption |

**Verdict:** did:web more appropriate for self-hosted app. AT Protocol integration not worth the effort.

---

## 6. IndieAuth / IndieWeb Identity

### How [IndieAuth](https://indieauth.spec.indieweb.org/) Works

OAuth2-based identity where URLs are identifiers:
1. User enters their URL (e.g., `https://sempkm.example.com/users/alice`)
2. Client discovers `rel=indieauth-metadata` link
3. OAuth2 authorization flow with mandatory PKCE
4. Profile URL is the verified identity

No client registration needed. Both users and apps identified by URLs.

### [RelMeAuth](https://indieweb.org/RelMeAuth)

Bidirectional link verification: your site links to Mastodon with `rel="me"`, Mastodon links back. Used for Mastodon verified checkmarks.

### IndieAuth vs DIDs

| Aspect | IndieAuth | DIDs (did:web) |
|---|---|---|
| Identifier | URL (your domain) | DID string |
| Complexity | OAuth2 (well-understood) | New protocol |
| Key management | None for users | Server-managed keys |
| Cryptographic proof | No (relies on HTTPS) | Yes (Ed25519 signatures) |
| Graph signing | Not possible | Yes — main value-add |
| Maturity | Production, many implementations | Evolving |

### Python Libraries

- [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html): Helper functions for IndieAuth endpoints
- [Alto](https://github.com/capjamesg/alto): Flask-based IndieAuth authorization + token endpoint
- [Punyauth](https://github.com/cleverdevil/punyauth): Pure Python IndieAuth endpoint

**Verdict:** Highest value-to-complexity ratio for authentication. Build alongside DIDs — IndieAuth for auth, DIDs for signing.

---

## 7. RDF Graph Signing

[RDF Dataset Canonicalization](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/) (URDNA2015) became a W3C Recommendation in 2024. This enables:

1. Canonicalize named graph using URDNA2015 (N-Quads output)
2. SHA-256 hash the canonical form
3. Sign with user's Ed25519 key (from DID)
4. Store proof as RDF alongside the graph

```python
from pyld import jsonld
canonical = jsonld.normalize(graph_as_jsonld, {
    'algorithm': 'URDNA2015',
    'format': 'application/n-quads'
})
# Hash and sign with user's key
```

Directly applicable to SemPKM's named graph architecture — knowledge contributions get cryptographically signed provenance.

---

## 8. Integration with Collaboration Architecture

The identity work layers onto the [collaboration architecture](collaboration-architecture.md):

| Collab Layer | Identity Integration |
|---|---|
| Layer 1: RDF Patch Sync | Sign patches with user DID keys → verifiable change attribution |
| Layer 2: LDN Notifications | Notifications identify sender by DID, receiver verifies |
| Layer 3: Federated Identity | **This IS the identity layer** — WebID + did:web + IndieAuth |
| Layer 4: CRDT Real-Time | DID Auth for session establishment between instances |

---

## Recommended Phased Approach

### Phase 1: Foundation (WebID + IndieAuth)
- Serve WebID profiles at user URLs (Turtle via content negotiation)
- Implement IndieAuth provider (authorization + token endpoints)
- Add `rel="me"` for fediverse verification
- **Effort:** ~1 week | **Value:** Immediate interoperability with IndieWeb + Solid ecosystem

### Phase 2: DID Layer (did:web)
- Generate Ed25519 key pairs per user (server-managed)
- Serve DID Documents at did:web resolution paths
- Sign named graphs with URDNA2015 + user keys
- Store proofs as RDF in triplestore
- **Effort:** ~2-3 weeks | **Value:** Cryptographic provenance for knowledge sharing

### Phase 3: Verifiable Credentials
- Issue authorship/contribution VCs using DID keys
- VC verification endpoint
- Cross-instance knowledge sharing with signed provenance
- **Effort:** ~2-3 weeks | **Value:** Portable, verifiable knowledge attestations

### Phase 4: Enhanced Trust (did:webvh)
- Migrate did:web → did:webvh for verifiable history
- Pre-rotation for key compromise recovery
- **Effort:** ~4-6 weeks | **Value:** Tamper-evident identity history

### What NOT to Build
- Full Solid Pod provider (different problem, no SPARQL)
- AT Protocol integration (incompatible data models)
- Blockchain-based DIDs (unnecessary complexity)
- Custom DID method (use existing methods)
- Full SSI wallet (overkill for PKM)

### Key Management Strategy

Users should **never** manage cryptographic keys directly. Approach:
- Server generates Ed25519 key pairs per user, stores encrypted
- Users authenticate via normal password/2FA
- Progressive disclosure: power users can optionally provide own keys later
- [Key management is the biggest practical barrier](https://deepthix.com/en/blog/atproto-gestion-cles-decentralisation-1771755536559/) to decentralized identity adoption

---

## Sources

### W3C Specifications
- [DID 1.0 W3C Recommendation](https://www.w3.org/press-releases/2022/did-rec/)
- [DID 1.1 Candidate Recommendation](https://www.w3.org/TR/did-1.1/)
- [VC 2.0 W3C Recommendation](https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/)
- [VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [RDF Dataset Canonicalization](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/)
- [DID Methods WG Charter](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html)

### DID Methods
- [did:web](https://w3c-ccg.github.io/did-method-web/) | [did:key](https://w3c-ccg.github.io/did-key-spec/) | [did:plc](https://web.plc.directory/spec/v0.1/did-plc) | [did:dht](https://did-dht.com/) | [did:webvh](https://identity.foundation/didwebvh/v0.3/)

### WebID and Solid
- [WebID 1.0](https://w3c.github.io/WebID/spec/identity/index.html) | [WebID Profile](https://solid.github.io/webid-profile/) | [Solid-OIDC](https://solid.github.io/solid-oidc/)

### IndieAuth and IndieWeb
- [IndieAuth spec](https://indieauth.spec.indieweb.org/) | [RelMeAuth](https://indieweb.org/RelMeAuth) | [IndieAuth wiki](https://indieweb.org/IndieAuth)

### AT Protocol
- [2025 Protocol Roadmap](https://docs.bsky.app/blog/2025-protocol-roadmap-spring) | [Custom Schemas](https://docs.bsky.app/docs/advanced-guides/custom-schemas) | [AT Protocol DID spec](https://atproto.com/specs/did)

### Libraries
- [PyLD](https://github.com/digitalbazaar/pyld) | [Universal Resolver](https://github.com/decentralized-identity/universal-resolver) | [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html) | [Punyauth](https://github.com/cleverdevil/punyauth) | [Alto](https://github.com/capjamesg/alto)

### Analysis
- [W3C overrules DID objections](https://www.theregister.com/2022/07/01/w3c_overrules_objections/) | [AT Protocol key management](https://deepthix.com/en/blog/atproto-gestion-cles-decentralisation-1771755536559/) | [Fediverse DID integration](https://github.com/WebOfTrustInfo/rwot9-prague/blob/master/topics-and-advance-readings/fediverse-did-integration.md) | [VC verification tutorial](https://grotto-networking.com/blog/posts/jsonldProofs.html)

---

*Research conducted: 2026-03-03*

# SemPKM Future Milestones Planning

**Created:** 2026-02-26
**Context:** Planning session after v2.0 completion. Captures feature ideas, milestone breakdown, dependency map, parallelization strategy, and architectural decisions.

---

## Key Architectural Decision: No VSCode/Theia

**Decision:** Stay with the current FastAPI + htmx + vanilla JS stack. Do NOT adopt Theia or VSCode as the IDE shell.

**Rationale:**
- Theming is already substantially done (theme.css, CSS custom properties, dark mode Phase 13, settings Phase 15). Full user-configurable themes are a CSS variable extension problem, not an architecture problem.
- Flexible panel layout (more than Split.js) is achievable with **GoldenLayout** (pure JS, no framework required) — handles arbitrary drag-to-dock panel rearrangement with saved layout configs. Integrates cleanly with htmx-rendered panel content.
- Adopting Theia/VSCode would mean a complete frontend rewrite, extension model, and a new paradigm with massive complexity. Not justified when the current stack can deliver the UX goals.

**What this means for future phases:**
- Theming: CSS variable token sets + theme picker in settings
- Flexible panels: GoldenLayout integration phase
- Dashboards: Store layout configs in RDF, apply via GoldenLayout API

---

## Parallelization Strategy

The biggest lever for parallel execution is **research milestones** where all phases run simultaneously, followed by **implementation milestones** where independent features overlap in plans.

**Research milestone pattern:**
- All research phases spawn in parallel (4+ agents at once)
- Each produces a RESEARCH.md and recommendation
- Synthesis phase reviews all research, makes final decisions
- Then plan implementation phases with confidence

**Implementation milestone pattern:**
- Features with independent backends (search, VFS, SPARQL) can be parallel plans within a phase
- Features that share UI components (dashboards, panels) must sequence after shared infrastructure

---

## Milestone: v2.1 — Research & Architecture Decisions

**Goal:** Resolve all major open questions before building. No implementation — research and decisions only.

**All phases run in parallel.**

### Phase 20: Full-Text Search + Vector Store Research
**Agent focus:** What is the right search technology for SemPKM?

Key questions:
- Are there open-source RDF triplestores with built-in FTS (RDF4J, Apache Jena, Oxigraph)?
- RDF4J's Lucene integration — current state, query syntax, config?
- OpenSearch as a sidecar: index `urn:sempkm:current` graph, sync via webhooks?
- pgvector / sentence-transformers for semantic similarity search?
- How does FTS compose with SPARQL filtering?
- What does the write path look like (index on EventStore.commit)?

Output: RESEARCH.md with recommended approach, indexing strategy, query API design.

### Phase 21: SPARQL Interface Research
**Agent focus:** What is the most modern, beautiful SPARQL UI to integrate?

Key questions:
- Zazuko Yasgui — current state (2025/2026), license, embed options?
- Other modern SPARQL UIs (SPARQL Playground, Triply, etc.)?
- Iframe embed vs. sidecar deployment vs. custom implementation?
- Autocomplete: how does it work in Yasgui (schema-aware, prefix-aware)?
- "Pills" / inline object rendering for query results — does Yasgui support it or do we build it?
- Saved queries + query history: server-side (user-scoped RDF storage) or localStorage?
- Integration with SemPKM's existing `/sparql` debug endpoint?

Output: RESEARCH.md with recommended approach, integration plan, UI mockup description.

### Phase 22: Virtual Filesystem — Technology Validation
**Agent focus:** Validate the WebDAV approach from `.planning/research/virtual-filesystem.md` and identify implementation risks.

Existing research: `.planning/research/virtual-filesystem.md` — comprehensive, covers prior art, design, protocol choices.

Key questions to validate:
- `wsgidav` + FastAPI integration — current state, async support?
- FUSE as alternative — `fusepy` / `pyfuse3` current state on Linux?
- What's the minimum viable MountSpec vocabulary (start with `flat` and `tag-groups` strategies)?
- How does the write path integrate with EventStore.commit?
- WebDAV discovery — will macOS Finder / Linux file managers mount it without config?
- Performance: SPARQL on every readdir() — acceptable? Caching strategy?

Output: RESEARCH.md with implementation plan, phased rollout (read-only first, then writes), risks.

### Phase 23: UI Shell Architecture Research
**Agent focus:** GoldenLayout for flexible panels + theming token system design.

Key questions:
- GoldenLayout 2.x vs alternatives (Flexlayout-model, Dockview) — feature comparison, bundle size, htmx compatibility?
- How does GoldenLayout interact with htmx partial renders inside panels?
- Layout persistence: JSON config → store in RDF as user preference, load on workspace init?
- Theme token system: what CSS custom property vocabulary covers all components (sidebar, tabs, editor, graph, forms, modals)?
- Model-contributed themes: how does a Mental Model declare a theme bundle?
- Can GoldenLayout handle the "Dashboards" use case (named saved layouts)?

Output: RESEARCH.md with GoldenLayout integration design, CSS token vocabulary, theme contribution spec.

---

## Milestone: v2.2 — Data Discovery

**Goal:** Make the knowledge graph findable and queryable. Three independent features, mostly parallel.

### Phase 24: Full-Text Search Implementation
Implement the technology chosen in Phase 20 research.

Likely plans:
- Backend: index integration (RDF4J Lucene or OpenSearch sidecar), EventStore hook, search API endpoint
- Frontend: search UI (command palette integration, search results panel, filter by type/date)

### Phase 25: SPARQL Interface Integration
Implement the approach chosen in Phase 21 research.

Likely plans:
- Integration: embed Yasgui (or chosen tool) as a special tab / bottom panel tab
- Enhancements: saved queries (RDF storage, user-scoped), query history, inline object pills in results
- Polish: autocomplete schema-aware, prefix auto-complete from PrefixRegistry

### Phase 26: Virtual Filesystem MVP
Implement the WebDAV approach validated in Phase 22 research.

Likely plans:
- Read-only WebDAV server: wsgidav + FastAPI mount, MountSpec model, SPARQL-to-directory mapping
- Markdown+frontmatter rendering: SHACL-driven frontmatter fields, body property rendering
- MountSpec UI: configure mounts via Settings page
- (Optional next milestone) Write support with SHACL validation on parse-back

---

## Milestone: v2.3 — Shell & Navigation

**Goal:** Dashboards, flexible panels, full theming. Depends on v2.2 UI shell research (Phase 23).

### Phase 27: GoldenLayout Integration
Replace or extend Split.js with GoldenLayout for arbitrary drag-to-dock panel rearrangement.

- GoldenLayout initialization, panel registry, htmx content loading into panels
- Layout persistence (JSON config in RDF as user preference)
- Migration from existing Split.js panel model

### Phase 28: Dashboards (Named Layouts)
User-defined and model-provided named workspace layouts (Bases equivalent).

- Dashboard data model (RDF storage, user-scoped + model-provided)
- Dashboard picker UI (sidebar section or command palette)
- Mental Model manifest: `dashboards` key for model-provided layouts
- Default dashboards for basic-pkm model (e.g. "Research Mode", "Writing Mode")

### Phase 29: Full Theming System
User-selectable themes; model-contributed theme bundles.

- CSS custom property token vocabulary (finalized from Phase 23 research)
- Built-in themes: Dark+, Light, High Contrast, Solarized
- Theme picker in settings
- Mental Model manifest: `theme` key for model-contributed themes
- Theme preview in settings

---

## Milestone: v2.4 — Low-Code & Workflows

**Goal:** SemPKM as a platform for structured user interactions. Depends on v2.3 shell being stable.

### Phase 30: Low-Code UI Builder
Users compose basic components tied to SemPKM actions. Notion + Airflow inspired.

- Component palette: form fields, buttons, text blocks, object references, view embeds
- Layout canvas: drag-and-drop component placement
- Action binding: bind components to SemPKM commands (object.create, object.patch, etc.)
- Save as Mental Model artifact (user-created "App")

Design principle: NOT a general-purpose UI builder. Components are SemPKM-native. No arbitrary HTML/JS injection.

### Phase 31: Minimal Workflow Orchestration
Orchestrated sequences of views/forms — not n8n (no business logic engine). Think CRM onboarding.

- Workflow definition: sequence of steps, each a form or view, with conditions
- Step types: form (SHACL-validated), confirmation, object reference picker, note append
- Example: "Add Client" → "Add Project" → "Add Invoice" → "Log success to note body"
- Trigger types: manual (sidebar entry), webhook (event-triggered), model-provided workflow
- State: workflow instance stored as RDF (current step, collected values, outcome)

Design principle: Complement n8n for complex business logic. SemPKM workflows are UI-orchestration only — for data collection and structured entry, not computation.

---

## Tech Debt Phases (schedule across milestones)

These are from CONCERNS.md. Schedule as plan slots within feature milestones rather than dedicated phases.

**High priority (Phase 19 scope):**
- Label cache invalidation after writes
- datetime.now() → datetime.now(timezone.utc) in browser router
- EventStore DI in browser router write handlers
- CORS wildcard + credentials fix
- Debug endpoint owner-only guard
- IRI validation before SPARQL interpolation

**Medium priority (schedule in v2.1-v2.2):**
- Alembic migration runner at startup (replace create_all)
- SMTP email delivery implementation
- Session cleanup job (expired sessions accumulate)
- ViewSpecService TTL cache (two SPARQL queries per lookup)
- source_model attribution for multi-model installs
- validation/report.py hash() fallback → raise instead

**Lower priority (v2.3+):**
- browser/router.py monolith split into sub-routers
- LabelService Redis cache for multi-worker deployments
- Dependency pinning in pyproject.toml

---

## Standing Decisions for All Future Phases

1. **E2E tests required**: Every phase with user-visible behavior must add/update Playwright tests in `e2e/tests/`. Gate enforced in execute-plan.md.
2. **User guide docs required**: Any user-visible feature must be reflected in `docs/`. Gate enforced in execute-plan.md.
3. **No VSCode/Theia**: Current stack handles theming and flexible panels. Do not revisit unless constraints change dramatically.
4. **VFS uses WebDAV first**: FUSE is an option but WebDAV is the starting point (cross-platform, existing HTTP infra).
5. **Workflows are UI-orchestration only**: Do not replicate n8n. Deep n8n integration is the answer for complex business logic.
6. **Mental Models stay the extensibility mechanism**: Themes, dashboards, workflows, apps — all contributed via Mental Model manifests.

---

## Milestone: (Future) Collaboration & Federation

**Goal:** Enable multi-instance knowledge sharing with data sovereignty. Self-hosted SemPKM instances sync named graphs, notify each other of changes, and authenticate cross-instance users. Real-time co-editing deferred until CRDT-for-RDF ecosystem matures.

**Depends on:** SPARQL Interface milestone (permissions infrastructure needed for cross-instance access control)

**Research:** [`collaboration-architecture.md`](collaboration-architecture.md) — comprehensive analysis of SOLID, ActivityPub, RDF sync, CRDTs, and hypertext collaboration patterns (40+ sources)

### Phase A: RDF Patch Change Tracking

Wrap triplestore writes to emit RDF Patch log entries. Foundation for all sync.

- Patch log model (SQLAlchemy or append-only file per named graph)
- EventStore integration: each commit() emits corresponding RDF Patch entries
- Patch replay: apply a patch sequence to bring a graph to a target version
- Graph versioning: monotonic version counter per named graph

Key tech: [RDF Patch format](https://afs.github.io/rdf-patch/), [Jelly-Patch](https://jelly-rdf.github.io/dev/) (binary, when Python impl lands)

### Phase B: Named Graph Sync API

HTTP sync endpoint for exchanging patches between SemPKM instances.

- `GET /api/sync/{graph}?since={version}` — returns patches since version
- `POST /api/sync/{graph}` — accept and apply incoming patches
- Remote configuration: list of peer instances with sync direction (push/pull/both)
- Conflict detection: reject patches when base version has diverged (manual merge)
- [SPARQL Graph Store Protocol](https://w3c.github.io/sparql-graph-store-protocol/) for full graph bootstrap

### Phase C: Cross-Instance Notifications

[Linked Data Notifications (LDN)](https://www.w3.org/TR/ldn/) for change awareness + [Webmention](https://www.w3.org/TR/webmention/) for cross-references.

- LDN Inbox endpoint: receive notifications as JSON-LD
- Subscription model: instance B subscribes to graph changes on instance A
- Notification triggers pull-based sync from Phase B
- Webmention: when an object references a URL on another instance, notify them

### Phase D: Federated Identity (WebID)

[WebID](https://www.w3.org/wiki/WebID) for cross-instance user identity + ACL on shared graphs.

- Each SemPKM user gets a WebID (profile URL resolving to RDF)
- WebID authentication for incoming sync/API requests
- Named graph ACL: grant read/write to specific WebIDs
- Local auth system unchanged; WebID layered on top for federation

### Phase E: Collaboration UI

User-facing features for managing shared graphs and remote instances.

- Settings: manage remote instances (add, remove, sync status)
- Graph sharing: select named graphs to share, set permissions per WebID
- Sync status: visual indicator of sync state per graph (synced, pending, conflict)
- Incoming changes: notification panel for cross-instance activity

### Phase F: Real-Time Collaboration (Deferred)

CRDT-based concurrent editing — **build only when ecosystem is ready.**

- Watch: [W3C CRDT for RDF CG](https://www.w3.org/community/crdt4rdf/), [NextGraph](https://nextgraph.org/), [m-ld](https://m-ld.org/)
- Integrate when a mature Python/JS library exists
- Scope: concurrent editing of individual resources within shared named graphs
- Until then, Layer 1 (patch-based async sync) handles collaboration

---

## Milestone: (Future) Identity & Authentication

**Goal:** Make SemPKM users verifiable identities on the web. Serve WebID profiles, provide IndieAuth login, issue DID-based identifiers, sign knowledge graphs cryptographically, and issue Verifiable Credentials for knowledge attestation.

**Depends on:** Can start independently (Phases A-B have no dependencies). Phases C-D depend on Collaboration & Federation milestone (cross-instance sharing needs signed graphs).

**Research:** [`decentralized-identity.md`](decentralized-identity.md) — comprehensive analysis of DIDs, VCs, WebID, IndieAuth, did:web, did:plc, RDF graph signing (50+ sources)

### Phase A: WebID Profiles + rel="me"

Serve user URLs as RDF via content negotiation. Immediate interop with Solid ecosystem and fediverse.

- Content negotiation on `/users/{username}`: Turtle for RDF clients, HTML for browsers
- FOAF/schema.org properties from existing user data in triplestore
- `rel="me"` links on profile pages for [RelMeAuth](https://indieweb.org/RelMeAuth) fediverse verification
- Key tech: existing RDF4J + FastAPI content negotiation

### Phase B: IndieAuth Provider

[IndieAuth](https://indieauth.spec.indieweb.org/) (OAuth2 + URL-as-identity) lets SemPKM users sign into other IndieWeb services.

- Authorization endpoint: `/auth/indieauth/authorize`
- Token endpoint: `/auth/indieauth/token`
- Server metadata at `rel=indieauth-metadata`
- Mandatory PKCE per current spec
- Python libs: [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html), [Punyauth](https://github.com/cleverdevil/punyauth), [Alto](https://github.com/capjamesg/alto)

### Phase C: did:web DID Documents + Graph Signing

[did:web](https://w3c-ccg.github.io/did-method-web/) maps to existing HTTPS. Each user gets a globally resolvable DID.

- Generate Ed25519 key pairs per user (server-managed, stored encrypted)
- Serve DID Documents at `/.well-known/did.json` (instance) and `/users/{username}/did.json` (per-user)
- Sign named graphs: [URDNA2015](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/) canonicalization → SHA-256 → Ed25519 signature
- Store proofs as RDF in triplestore (native JSON-LD)
- Key risk: key management UX — users must never handle keys directly

### Phase D: Verifiable Credentials

[VC 2.0](https://www.w3.org/TR/vc-data-model-2.0/) (W3C Rec, May 2025) for knowledge attestation.

- Issue authorship/contribution VCs using DID assertion keys
- VC verification endpoint: `/api/vc/verify`
- Credential types: authorship, membership, data integrity certificates
- VCs stored as RDF named graphs (JSON-LD is RDF)
- Cross-instance knowledge sharing with signed, verifiable provenance

### Phase E: did:webvh Migration (Future)

Upgrade from did:web to [did:webvh](https://identity.foundation/didwebvh/v0.3/) for verifiable history.

- `did.jsonl` cryptographic version chain
- Pre-rotation for key compromise recovery
- Optional witness support
- Python implementation exists (~1500 LOC)
- Build when [DID Methods WG](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html) standardizes web-based method

### What NOT to Build
- Full Solid Pod provider (different problem, no SPARQL)
- AT Protocol / did:plc integration (incompatible data models, depends on plc.directory)
- Blockchain-based DIDs (unnecessary complexity)
- Custom DID method (use existing methods)
- Full SSI wallet (overkill for PKM)

---

## Milestone: (Future) Global Lint Status

**Goal:** Provide a workspace-wide SHACL validation dashboard so users can see every violation, warning, and info across all objects at a glance, filter and search results, read actionable fix guidance, and click directly into the offending object to fix issues in a continuous triage workflow.

**Depends on:** v2.3 (dockview panel infrastructure, object view redesign for field-focus targets). Can start research independently.

**Builds on:** Existing `ValidationService` + `AsyncValidationQueue` pipeline (runs pyshacl after every EventStore.commit()), `ValidationReport`/`ValidationResult` dataclasses, per-object `lint_panel.html`, `/api/validation/latest` endpoint.

### Phase A: Global Validation Data Model and API

Extend the validation pipeline to persist per-object, per-result detail and expose it via paginated API endpoints.

- New storage: individual `ValidationResult` records queryable by focus_node, severity, path, constraint_component
- Storage options: RDF named graph (`urn:sempkm:lint-results`) vs. SQLAlchemy model — research trade-offs
- API: `GET /api/lint/results?severity=Violation&type=Note&page=1` with filtering, sorting, pagination
- Incremental validation: only re-validate objects whose triples changed in the commit (performance at scale)
- Existing `ValidationReportSummary` for aggregate counts remains; new detail layer adds per-result access

### Phase B: Global Lint Dashboard UI

Dockview panel or dedicated page showing all validation results across all objects.

- Summary bar: total violations / warnings / infos with color-coded badges
- Result list: table or card layout with object label, severity icon, property path, message, timestamp
- Filters: severity toggles, type dropdown (from ModelRegistry), keyword search
- Sorting: by severity, object name, property path, timestamp
- Pagination or virtual scroll for large result sets
- Status bar indicator: persistent badge showing knowledge base health at a glance
- Design: htmx partials + CSS custom properties, following existing SemPKM patterns

### Phase C: Fix Guidance Engine

Generate human-readable, actionable fix messages from SHACL shape metadata.

- Template registry: maps `sh:sourceConstraintComponent` URIs to message templates
- Built-in templates for top 10 constraint types:
  - `sh:MinCountConstraintComponent` → "This field requires at least {minCount} value(s) -- add a {propertyName} to fix"
  - `sh:MaxCountConstraintComponent` → "This field allows at most {maxCount} value(s) -- remove extras to fix"
  - `sh:DatatypeConstraintComponent` → "Expected {datatype} but got {actualValue} -- update the value format"
  - `sh:PatternConstraintComponent` → "Value must match pattern {pattern} -- check formatting"
  - `sh:ClassConstraintComponent` → "Value must be an instance of {class} -- select the right type"
  - `sh:MinLengthConstraintComponent`, `sh:MaxLengthConstraintComponent`, `sh:InConstraintComponent`, `sh:NodeKindConstraintComponent`, `sh:HasValueConstraintComponent`
- Shape-author override: if `sh:description` is set on the property shape, use it as the guidance message
- Mental Model helptext: models can provide `sempkm:fixGuidance` annotations on shapes for domain-specific advice
- Graceful fallback: unknown constraint types get "Constraint violated on {path} -- check the value against the shape definition"

### Phase D: Click-to-Edit Triage Workflow

Wire the global lint dashboard to the object editing workflow for continuous issue resolution.

- Click a lint result row → open object in dockview pane (or focus existing pane) → scroll to field
- Extend `jumpToField()` to work cross-pane (currently only works within the active object's lint tab)
- After save: lint dashboard refreshes to show updated results (resolved issues disappear)
- Sequential triage: user works through list top-to-bottom, fixing each issue without leaving the lint view
- Keyboard navigation: arrow keys through lint results, Enter to open, Escape to return to lint view

### What NOT to Build
- Auto-fix engine (programmatic correction of violations) -- too risky, bypasses user intent
- Custom validation rules outside SHACL -- SHACL is the constraint language, extend via shapes
- Cross-object relationship validation (orphan detection, referential integrity) -- separate graph-health feature
- Real-time collaborative lint (multi-user live updates) -- depends on Collaboration milestone

---

## Research Artifacts

- `virtual-filesystem.md` — Comprehensive prior art + design for VFS feature (ready for Phase 22 validation)
- `collaboration-architecture.md` — SOLID, ActivityPub, RDF sync, CRDTs, hypertext collaboration research (2026-03-03)
- `decentralized-identity.md` — DIDs, VCs, WebID, IndieAuth, RDF graph signing research (2026-03-03)

---

*Created: 2026-02-26 — planning session after v2.0 milestone completion*

# Identity & Collaboration Refresh: Implementation-Ready Details

**Created:** 2026-03-07
**Context:** Targeted refresh of decentralized-identity.md and collaboration-architecture.md research for v2.5 implementation. Focuses on library verification, WebID+IndieAuth integration patterns, cross-instance authentication, and IndieAuth provider implementation.

---

## 1. Library Verification

### indieweb-utils (v0.10.0, September 2025) -- USABLE WITH CAVEATS

**Status:** Actively maintained (501 commits, 8 releases). Latest release September 11, 2025. MIT license.

**IndieAuth support:** The library provides **both server-side and client-side** helpers:

Server-side functions:
- `generate_auth_token()` -- creates JWT-encoded authorization codes
- `redeem_code()` -- exchanges authorization codes for access tokens
- `validate_access_token()` -- verifies token validity, returns user info
- `is_user_authenticated()` -- Flask helper (would need adaptation for FastAPI)

Client-side functions:
- `discover_indieauth_endpoints()` -- locates metadata endpoints
- `handle_indieauth_callback()` -- processes callback responses
- `get_valid_relmeauth_links()` -- validates bidirectional rel=me links
- `get_profile()` -- fetches user profile via h-card

**Assessment:** The server-side functions provide useful scaffolding but are Flask-oriented. For SemPKM's FastAPI backend, use as reference/utility rather than direct integration. The discovery and validation functions are framework-agnostic and directly usable.

**Confidence:** HIGH (verified via PyPI and GitHub)

### PyLD (v2.0.4, February 2024) -- STABLE, USABLE

**Status:** Maintained by Digital Bazaar. Requires Python >= 3.6. Implements JSON-LD API including URDNA2015 canonicalization.

**Key capability for SemPKM:** `jsonld.normalize()` with `algorithm: 'URDNA2015'` produces deterministic N-Quads output for graph signing. This is the critical function for RDF graph integrity proofs.

**Confidence:** HIGH (verified via PyPI, well-established library)

### python-cryptography -- CURRENT, Ed25519 SUPPORTED

**Status:** Actively maintained (currently at v44.x). Ed25519 support is stable and well-documented.

**Ed25519 usage pattern:**
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Key generation
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Signing (deterministic -- same key+data = same signature)
signature = private_key.sign(b"message")

# Verification (raises InvalidSignature on failure)
public_key.verify(signature, b"message")

# Serialization for storage/DID documents
from cryptography.hazmat.primitives import serialization
public_bytes = public_key.public_bytes(
    serialization.Encoding.Raw,
    serialization.PublicFormat.Raw
)
```

**Confidence:** HIGH (official docs verified)

### http-message-signatures (v2.0.1, January 2026) -- NEW RECOMMENDATION

**Not in original research.** This is a Python implementation of RFC 9421 (HTTP Message Signatures), the IETF standard that supersedes the old draft used by Mastodon/fediverse.

- `pip install http-message-signatures` -- core signing/verification
- `pip install requests-http-signature` -- requests integration with body digest

**Why this matters:** RFC 9421 is the standardized version of what the fediverse uses for server-to-server authentication. SemPKM should implement RFC 9421 from the start rather than the legacy cavage-12 draft.

**Confidence:** HIGH (verified via PyPI, January 2026 release)

### PunyAuth -- DEAD, DO NOT USE

**Status:** Repository archived March 5, 2026. Only 10 commits. Never completed. The original research listed this as an option -- it is no longer viable.

### Alto -- STALE, USE AS REFERENCE ONLY

**Status:** Last significant activity October 2021. Flask-based. Use as architectural reference for how IndieAuth endpoints are structured, but do not depend on it.

### datasette-indieauth (v1.2.2, November 2022) -- CLIENT ONLY

Simon Willison's implementation is an IndieAuth **client** (consumer), not a provider. Useful as reference for the client-side flow, not for building SemPKM's authorization server.

---

## 2. WebID + IndieAuth Integration Pattern

### How They Connect

WebID and IndieAuth are **complementary but independent** systems. They do NOT automatically discover each other -- SemPKM must bridge them.

**WebID** answers: "Who is this person?" (an RDF profile document at an HTTP URI)
**IndieAuth** answers: "Can this person prove they control that URL?" (OAuth2-based authentication)

### The Bridge: Same URL, Two Representations

The key insight is that the **user's profile URL serves both purposes**:

```
https://sempkm.example.com/users/alice
```

1. **As WebID:** When requested with `Accept: text/turtle`, returns RDF profile document (FOAF properties, public keys, linked identities)
2. **As IndieAuth identity:** When requested with `Accept: text/html`, returns HTML page with `<link rel="indieauth-metadata" href="...">` discovery

This is content negotiation -- the same URL, different representations based on what the client asks for.

### Minimal WebID Profile Document

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix cert: <http://www.w3.org/ns/auth/cert#> .
@prefix solid: <http://www.w3.org/ns/solid/terms#> .
@prefix dcterms: <http://purl.org/dc/terms/> .

<https://sempkm.example.com/users/alice>
    a foaf:PersonalProfileDocument ;
    foaf:primaryTopic <https://sempkm.example.com/users/alice#me> .

<https://sempkm.example.com/users/alice#me>
    a foaf:Person ;
    foaf:name "Alice" ;
    cert:key [
        a cert:Ed25519PublicKey ;
        cert:publicKeyBase64 "..." ;
    ] ;
    solid:oidcIssuer <https://sempkm.example.com/> .
```

### HTML Representation (for IndieAuth discovery)

```html
<html>
<head>
    <link rel="indieauth-metadata" href="https://sempkm.example.com/.well-known/oauth-authorization-server">
    <link rel="me" href="https://mastodon.social/@alice">
</head>
<body>
    <div class="h-card">
        <a class="p-name u-url" href="https://sempkm.example.com/users/alice">Alice</a>
    </div>
</body>
</html>
```

### How Solid Servers Do It

Solid uses `solid:oidcIssuer` in the WebID profile to point to the OIDC provider. The verification flow:

1. Client obtains an ID Token from the issuer
2. Client extracts the WebID URI from the token
3. Resource server fetches the WebID profile
4. Resource server checks that the issuer in the ID Token matches `solid:oidcIssuer` in the profile
5. If they match, the request is authenticated as that WebID

SemPKM should adopt this same pattern but with IndieAuth instead of full OIDC. The `solid:oidcIssuer` triple (or an equivalent custom predicate) in the WebID profile points to the SemPKM instance's IndieAuth metadata endpoint.

### Recommended FastAPI Routes

```python
# WebID profile with content negotiation
@app.get("/users/{username}")
async def user_profile(username: str, request: Request):
    accept = request.headers.get("accept", "text/html")
    if "text/turtle" in accept or "application/ld+json" in accept:
        return turtle_profile(username)  # RDF WebID document
    return html_profile(username)  # HTML with IndieAuth discovery links

# IndieAuth metadata (RFC 8414 style)
@app.get("/.well-known/oauth-authorization-server")
async def indieauth_metadata():
    return {
        "issuer": "https://sempkm.example.com/",
        "authorization_endpoint": "https://sempkm.example.com/auth/authorize",
        "token_endpoint": "https://sempkm.example.com/auth/token",
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["profile", "read", "write"],
    }
```

**Confidence:** MEDIUM (synthesized from Solid-OIDC spec, IndieAuth spec, and WebID spec -- no single implementation demonstrates this exact pattern)

---

## 3. Cross-Instance Authentication for RDF Collaboration

### The Problem

Instance A wants to push/pull named graphs to/from Instance B. Instance B needs to verify that the request is from a specific WebID (e.g., `https://a.example.com/users/alice#me`).

### Recommended Pattern: HTTP Message Signatures (RFC 9421)

This is the same mechanism the fediverse uses for server-to-server ActivityPub, but SemPKM should use the standardized RFC 9421 rather than the legacy draft.

**Flow:**

1. **Instance A signs the request** using the Ed25519 private key associated with the actor's WebID
2. **Instance B receives the request** and extracts the `keyId` from the Signature-Input header
3. **Instance B fetches the WebID profile** at the keyId URL (with caching)
4. **Instance B extracts the public key** from the profile's `cert:key` property
5. **Instance B verifies the signature** against the public key
6. **Instance B checks authorization** -- does this WebID have permission on the requested resource?

**Implementation with http-message-signatures:**

```python
from http_message_signatures import HTTPMessageSigner, HTTPMessageVerifier

# Signing outbound requests (Instance A)
signer = HTTPMessageSigner(
    signature_algorithm=Ed25519,
    key_resolver=LocalKeyResolver(actor_private_key),
    covered_component_ids=["@method", "@target-uri", "content-type", "content-digest"],
)
signer.sign(request, key_id=f"https://a.example.com/users/alice#key")

# Verifying inbound requests (Instance B)
verifier = HTTPMessageVerifier(
    signature_algorithm=Ed25519,
    key_resolver=WebIDKeyResolver(),  # Fetches WebID, extracts public key
)
verify_result = verifier.verify(request)
webid = verify_result.parameters["keyId"]  # The authenticated identity
```

### Why NOT Solid-OIDC / WebID-OIDC

Solid-OIDC requires a full OpenID Connect provider with ID Tokens, DPoP (Demonstration of Proof of Possession), and token introspection. This is a heavy implementation for server-to-server communication. HTTP Signatures are simpler and more appropriate for machine-to-machine trust.

**Use IndieAuth for:** Human users authenticating via browser (OAuth2 flow)
**Use HTTP Signatures for:** Instance-to-instance API calls (server-to-server)

### Fediverse State of the Art (Context)

The fediverse (Mastodon et al.) currently uses the legacy cavage-12 HTTP Signatures draft with RSA-SHA256. Migration to RFC 9421 is underway but slow -- as of January 2026, only Mastodon and WordPress have partial RFC 9421 support, and neither supports Ed25519 yet.

**Implication for SemPKM:** Since we are building a new system (not interoperating with existing fediverse), we should implement RFC 9421 with Ed25519 from the start. If fediverse interop becomes important later, adding RSA-SHA256 as a fallback is straightforward.

### Key Discovery via WebID

The `WebIDKeyResolver` mentioned above would:

1. HTTP GET the WebID URI with `Accept: text/turtle`
2. Parse the Turtle response
3. Find `cert:key` or `sec:publicKey` triples for the WebID subject
4. Match the `keyId` from the signature to a specific key in the profile
5. Extract the public key bytes
6. Cache the result (with TTL, e.g., 1 hour)

**Confidence:** MEDIUM-HIGH (RFC 9421 is standardized, Python library exists and is current, but the WebID+HTTP Signatures combination is not widely deployed outside Solid research)

---

## 4. IndieAuth Provider Implementation

### Required Endpoints

An IndieAuth authorization server needs exactly three endpoints:

| Endpoint | Purpose | SemPKM Route |
|----------|---------|--------------|
| **Metadata** | Server discovery (RFC 8414 adapted) | `/.well-known/oauth-authorization-server` |
| **Authorization** | User consent + auth code generation | `/auth/authorize` |
| **Token** | Exchange auth code for access token | `/auth/token` |

Optional but recommended:
- **Token Revocation** (`/auth/revoke`) -- invalidate tokens
- **Userinfo** (`/auth/userinfo`) -- return profile info for `profile` scope

### PKCE Flow (Mandatory)

PKCE is **REQUIRED** by the IndieAuth spec (not optional like in base OAuth2).

```
1. Client generates code_verifier (43-128 chars, [A-Za-z0-9-._~])
2. Client computes code_challenge = BASE64URL(SHA256(code_verifier))
3. Client redirects to authorization endpoint with:
   - response_type=code
   - client_id=https://client.example.com/
   - redirect_uri=https://client.example.com/callback
   - state=<random>
   - code_challenge=<challenge>
   - code_challenge_method=S256
   - scope=profile  (or "read write" etc.)
   - me=https://sempkm.example.com/users/alice

4. SemPKM shows consent screen to logged-in user
5. User approves -> SemPKM generates authorization code
6. Redirect to redirect_uri with code=<auth_code>&state=<state>

7. Client POSTs to token endpoint:
   - grant_type=authorization_code
   - code=<auth_code>
   - client_id=https://client.example.com/
   - redirect_uri=https://client.example.com/callback
   - code_verifier=<original_verifier>

8. Token endpoint verifies:
   - code is valid and not expired
   - client_id matches
   - redirect_uri matches
   - SHA256(code_verifier) == stored code_challenge
9. Returns access token + profile URL
```

### Token Format

The IndieAuth spec says tokens are **opaque to clients** -- no specific format required. Options:

**Option A: JWT (recommended for SemPKM)**
- Self-contained, verifiable without DB lookup
- Include `me` (WebID URL), `scope`, `exp`, `iss`
- Sign with instance's Ed25519 key
- `indieweb-utils` already uses JWT for auth codes

**Option B: Random opaque tokens with DB storage**
- Simpler but requires token table and lookups
- Better for revocation

**Recommendation:** JWT for access tokens (stateless verification on API routes), with a revocation list for invalidated tokens.

### Client Identification (No Registration)

A key IndieAuth difference from standard OAuth2: **clients are identified by URL, not pre-registered**. The authorization server:

1. Receives `client_id` as a URL (e.g., `https://other-sempkm.example.com/`)
2. Fetches that URL to verify it exists
3. Optionally parses `h-app` microformat for app name/icon
4. Shows the client info on the consent screen
5. Verifies `redirect_uri` is on the same domain as `client_id` (or explicitly listed)

This means any SemPKM instance can authenticate against any other without pre-registration -- critical for decentralized collaboration.

### Minimal Implementation Checklist

```
[x] GET /.well-known/oauth-authorization-server
    Returns JSON with issuer, authorization_endpoint, token_endpoint,
    code_challenge_methods_supported: ["S256"]

[x] GET /auth/authorize
    - Verify user is logged in (redirect to login if not)
    - Validate client_id (fetch URL, check redirect_uri)
    - Show consent screen with client info + requested scopes
    - On approve: generate auth code, store with PKCE challenge, redirect

[x] POST /auth/token
    - Validate grant_type=authorization_code
    - Verify code, client_id, redirect_uri, code_verifier
    - Return { "access_token": "...", "token_type": "Bearer",
               "me": "https://sempkm.example.com/users/alice",
               "scope": "profile read" }

[x] User profile URL returns HTML with:
    <link rel="indieauth-metadata"
          href="/.well-known/oauth-authorization-server">
```

### Reference Implementations Worth Studying

1. **indieweb-utils** (Python) -- server-side helper functions, JWT-based codes. Best Python reference despite Flask orientation.
2. **datasette-indieauth** (Python) -- clean client-side implementation by Simon Willison. Good for understanding the flow from the consumer side.
3. **WordPress IndieAuth plugin** (PHP) -- most battle-tested IndieAuth provider implementation. Study for edge cases and error handling.
4. **indieauth.com** (service) -- Aaron Parecki's reference implementation. Not open-source server-side, but the spec author's implementation.

**Confidence:** HIGH (IndieAuth spec is stable, well-documented, and the endpoints are straightforward OAuth2 with PKCE)

---

## 5. Corrections to Existing Research

### PunyAuth is Dead
The existing `decentralized-identity.md` lists PunyAuth as a viable option. It was **archived March 5, 2026**. Remove from consideration.

### indieweb-utils Has Server-Side IndieAuth Support
The existing research only mentions "helper functions for IndieAuth endpoints" -- it actually provides `generate_auth_token()`, `redeem_code()`, `validate_access_token()`, and more. These are substantial building blocks, not just helpers.

### HTTP Message Signatures Are Standardized
The existing research mentions "HTTP Signatures (draft-ietf-httpbis-message-signatures)" -- this is now **RFC 9421** (published February 2024). There is a good Python implementation (`http-message-signatures` v2.0.1). This should be the recommended mechanism for server-to-server authentication, not an afterthought.

### WebID-OIDC vs IndieAuth Clarification
The existing research treats these as separate concerns. For SemPKM, the cleaner model is:
- **IndieAuth** for human browser-based authentication (simpler than full OIDC)
- **HTTP Signatures** for server-to-server API authentication (no tokens needed)
- **WebID profile** as the identity document that both systems reference
- Do NOT implement full Solid-OIDC -- it is overengineered for our use case

---

## 6. Recommended Implementation Order for v2.5

### Step 1: WebID Profile Endpoint (1-2 days)
- Content-negotiated route at `/users/{username}`
- Turtle representation with FOAF properties from existing user data in triplestore
- HTML representation with `rel="indieauth-metadata"` and `rel="me"` links
- Fragment URI pattern: `https://domain/users/alice#me` for the person

### Step 2: IndieAuth Metadata + Authorization Endpoint (2-3 days)
- `/.well-known/oauth-authorization-server` metadata endpoint
- `/auth/authorize` with consent screen
- Auth code generation with PKCE challenge storage (can use existing DB or in-memory with TTL)

### Step 3: IndieAuth Token Endpoint (1 day)
- `/auth/token` endpoint
- JWT access token generation signed with instance key
- Token verification middleware for protected routes

### Step 4: Ed25519 Key Management (1 day)
- Generate Ed25519 keypair per user on account creation
- Store encrypted private key in database
- Expose public key in WebID profile document (`cert:key`)
- Expose public key at a fetchable URI for HTTP Signature verification

### Step 5: HTTP Signature Signing/Verification (2-3 days)
- Outbound request signing using `http-message-signatures`
- Inbound request verification with WebID-based key resolver
- Key caching with TTL
- This enables instance-to-instance authenticated API calls

### Total: ~7-10 days for complete identity foundation

---

## Sources

### Libraries (Verified)
- [indieweb-utils v0.10.0](https://pypi.org/project/indieweb-utils/) -- PyPI, September 2025
- [PyLD v2.0.4](https://pypi.org/project/PyLD/) -- PyPI, February 2024
- [http-message-signatures v2.0.1](https://pypi.org/project/http-message-signatures/) -- PyPI, January 2026
- [requests-http-signature](https://pypi.org/project/requests-http-signature/) -- PyPI, requests integration
- [PunyAuth](https://github.com/cleverdevil/punyauth) -- ARCHIVED March 2026
- [Alto](https://github.com/capjamesg/alto) -- Last active October 2021

### Specifications
- [IndieAuth Spec](https://indieauth.spec.indieweb.org/) -- Endpoint requirements, PKCE mandate
- [RFC 9421: HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421) -- Published February 2024
- [Solid WebID Profile](https://solid.github.io/webid-profile/) -- Profile document structure
- [WebID 1.0](https://w3c.github.io/WebID/spec/identity/index.html) -- Identity spec
- [ActivityPub HTTP Signatures](https://swicg.github.io/activitypub-http-signature/) -- Fediverse signing patterns

### Implementation References
- [indieweb-utils IndieAuth docs](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html) -- Server-side function reference
- [Simon Willison: Implementing IndieAuth for Datasette](https://simonwillison.net/2020/Nov/18/indieauth/) -- Client-side implementation walkthrough
- [RFC 9421 HTTP Signatures in 2026 - SocialHub](https://socialhub.activitypub.rocks/t/rfc-9421-http-signatures-in-2026/8427) -- Fediverse adoption status
- [Solid-OIDC issuer discovery](https://github.com/solid/webid-oidc-spec) -- WebID-to-issuer verification flow

---

*Research conducted: 2026-03-07*
*Refreshes: decentralized-identity.md (2026-03-03), collaboration-architecture.md (2026-03-03)*

# Obsidian Import Wizard: Interactive UX/UI Flow Design

**Status:** Research document -- specification for future implementation
**Date:** 2026-03-03
**Context:** Replaces the external-script workflow described in Chapter 24 (Obsidian Onboarding) with an in-app interactive wizard modeled on OpenRefine's column reconciliation UX.

---

## 1. Overview and Design Goals

### Current Workflow (Chapter 24)

The existing Obsidian onboarding workflow requires three separate external Python scripts run outside SemPKM:

1. **vault_audit.py** -- scans the vault directory, extracts file counts, frontmatter keys, link targets, and tags. Output is a printed summary in the terminal.
2. **classify_vault.py** -- sends each note to an OpenAI-compatible LLM API for type classification. Output is a CSV file requiring manual review in a spreadsheet editor.
3. **import_to_sempkm.py** -- reads the reviewed CSV and vault files, builds Command API payloads, and batch-sends them to SemPKM.

This workflow has significant usability gaps:
- Requires Python, pip dependencies (requests, pyyaml), and a terminal
- CSV review in a spreadsheet is disconnected from the app
- No visual feedback during classification or import
- No interactive type/property mapping -- the user edits CSV cells by hand
- No undo or rollback mechanism
- LLM API key required even for vaults where folder-based classification would suffice

### Proposed In-App Wizard

An interactive import wizard built into SemPKM's workspace UI that provides a guided, visual experience for importing Obsidian vaults. The wizard replaces all three external scripts with a single in-app flow.

### Design Principles

1. **Progressive disclosure** -- each wizard step reveals only what the user needs at that stage. The vault scan summary appears before type mapping; type mapping appears before property mapping.

2. **OpenRefine-style reconciliation** -- the type and property mapping steps draw directly from OpenRefine's column reconciliation UX: a table of items with auto-suggested assignments, bulk operations via facets/filters, and a live distribution summary that updates as the user works.

3. **Batch-then-review** -- the wizard auto-suggests mappings (by folder, by frontmatter patterns, by string similarity) and presents them for review. The user corrects exceptions rather than configuring every file individually.

4. **No data loss** -- unmapped frontmatter keys are explicitly handled (skip or store as tag). Wiki-links to non-existent targets are logged, not silently dropped. The original vault is never modified.

5. **Server-side state** -- wizard state lives in the backend (SQLAlchemy models or session store), not in browser JavaScript. This allows the user to close the browser mid-wizard and resume later.

6. **Type-level mappings** -- property mappings apply to ALL files of a given type, not per-file. If the user maps `related` to `skos:related` for type Note, every Note file with a `related` frontmatter key inherits that mapping. This is the key UX insight from OpenRefine: reconciliation operates on columns (types), not rows (files).

---

## 2. Wizard Step Sequence

The wizard consists of six steps, presented as a horizontal stepper bar at the top of the wizard panel. Each step is an htmx partial page load.

```
[1. Scan] --> [2. Type Mapping] --> [3. Property Mapping] --> [4. Relationships] --> [5. Preview] --> [6. Import]
```

### Step 1: Start Import Job (Vault Scan)

**Purpose:** User selects a folder of .md files. Backend scans the folder, extracts file metadata, and displays a vault audit summary.

**Entry point:** Settings page or workspace toolbar button: "Import from Obsidian"

**Interaction flow:**

1. User enters or browses to a vault folder path (server filesystem path, since SemPKM runs locally or in Docker with volume mounts)
2. User clicks "Scan Vault"
3. Backend walks the directory, extracts metadata for each .md file:
   - Relative file path
   - Parent folder name
   - YAML frontmatter keys and values
   - Wiki-link targets (`[[target]]`)
   - Tags (`#tag`)
   - File size and modification date
4. Display summary stats as a dashboard card grid:
   - Total .md files found
   - Files with frontmatter (count and percentage)
   - Unique frontmatter keys (top 10 listed)
   - Folder distribution (bar chart or table)
   - Wiki-link count and unique target count
   - Tag count and top tags
5. User reviews the summary and clicks "Next: Map Types"

**Error handling:**
- Path does not exist or is not readable: show inline error with suggestion
- No .md files found: show warning, suggest checking the path
- Very large vault (>5000 files): show warning about processing time, proceed normally

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import from Obsidian                          Step 1 of 6: Scan  |
+------------------------------------------------------------------+
|                                                                  |
|  Vault Path: [/home/user/obsidian-vault________] [Browse] [Scan] |
|                                                                  |
|  +--- Vault Summary ----------------------------------------+   |
|  |                                                           |   |
|  |  Total Files     347       Files w/ Frontmatter  89 (26%) |   |
|  |  Unique Tags      54       Unique Link Targets       412  |   |
|  |                                                           |   |
|  |  --- Folder Distribution ---                              |   |
|  |  Daily Notes ........... 142  (41%)                       |   |
|  |  Meetings ............... 44  (13%)                       |   |
|  |  Projects ............... 31  ( 9%)                       |   |
|  |  People ................. 28  ( 8%)                       |   |
|  |  Concepts ............... 19  ( 5%)                       |   |
|  |  (root) ................. 83  (24%)                       |   |
|  |                                                           |   |
|  |  --- Top Frontmatter Keys ---                             |   |
|  |  date (89)  tags (67)  status (31)  aliases (22)          |   |
|  |  type (18)  priority (15)  related (12)  source (8)       |   |
|  |                                                           |   |
|  +-----------------------------------------------------------+   |
|                                                                  |
|                                          [Cancel]  [Next: Types] |
+------------------------------------------------------------------+
```

---

### Step 2: Type Mapping (OpenRefine-style)

**Purpose:** Assign a SemPKM type to each file. Default: all files start as Note. User uses bulk operations (folder-based, glob patterns, manual selection) to reassign types.

**Data source for available types:** `ShapesService.get_types()` returns all types from installed Mental Model shapes graphs. Not hardcoded to Basic PKM -- if a custom model adds Recipe or Meeting types, they appear here.

**Layout:** Split view with a file table on the left and a type distribution summary on the right.

**Interaction patterns:**

1. **Folder-based bulk assign:** Click a folder group header row to assign all files in that folder to a type. Example: click "People/" header, select "Person" from dropdown -- all 28 files in People/ become Person.

2. **Glob pattern assign:** A pattern input bar above the table. Enter `Projects/**` and select "Project" to assign all matching files. Patterns support `*` (single level) and `**` (recursive). Multiple patterns can be stacked.

3. **Individual file assign:** Each file row has a type dropdown. Click to change a single file's type.

4. **Filter/facet sidebar:** Filter the table by current assigned type, folder, or presence of specific frontmatter keys. This lets the user focus on unclassified files or review a specific type.

5. **Live distribution summary:** A sidebar card showing type counts that updates in real-time as assignments change:
   ```
   Note ........... 142  (41%)
   Person .......... 28  ( 8%)
   Project ......... 31  ( 9%)
   Concept ......... 19  ( 5%)
   Unassigned ..... 127  (37%)
   ```

**Type dropdown population:** The dropdown calls `ShapesService.get_types()` which returns `[{iri, label}]` for each `sh:NodeShape` with `sh:targetClass`. The dropdown displays `label` and stores `iri`.

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                     Step 2 of 6: Type Mapping      |
+------------------------------------------------------------------+
| Pattern: [Projects/** -> [Project v] ] [Apply]                   |
+----------------------------------------------+-------------------+
| File Path            | Folder   | FM Keys    | Type         |    |
|----------------------|----------|------------|--------------|    |
| [v] People/          |          |            | [Person   v] | <- folder header
|   Alice Chen.md      | People   | name,role  | [Person   v] |    |
|   Bob Smith.md       | People   | name       | [Person   v] |    |
|   ...28 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Projects/        |          |            | [Project  v] | <- folder header
|   Project Alpha.md   | Projects | status,pri | [Project  v] |    |
|   Migration Plan.md  | Projects | status     | [Project  v] |    |
|   ...31 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Concepts/        |          |            | [Concept  v] | <- folder header
|   Machine Learning.md| Concepts | aliases    | [Concept  v] |    |
|   ...19 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Daily Notes/     |          |            | [Note     v] |    |
|   2024-01-15.md      | Daily..  | date       | [Note     v] |    |
|   ...142 files       |          |            |              |    |
|                      |          |            |              |    |
| [v] (root)/          |          |            | [Note     v] |    |
|   README.md          | .        |            | [skip     v] |    |
|   TODO.md            | .        | tags       | [Note     v] |    |
|   ...83 files        |          |            |              |    |
+----------------------------------------------+-------------------+
| Type Distribution                                                |
| Note ........... 225   Project ......... 31                      |
| Person .......... 28   Concept ......... 19                      |
| Skipped .......... 1   Unassigned ...... 43                      |
+------------------------------------------------------------------+
|                                 [Back: Scan]  [Next: Properties] |
+------------------------------------------------------------------+
```

**Skip option:** Files can be marked "skip" to exclude them from import (e.g., README.md, template files).

---

### Step 3: Property Mapping (Per Type)

**Purpose:** For each type that has files assigned, map YAML frontmatter keys to SHACL property shapes. Mappings apply to ALL files of that type (type-level, not file-level).

**Data source for available properties:** `ShapesService.get_form_for_type(type_iri)` returns a `NodeShapeForm` with a `properties: list[PropertyShape]`. Each `PropertyShape` has:
- `path`: full predicate IRI (e.g., `http://purl.org/dc/terms/title`)
- `name`: human-readable label (e.g., "Title")
- `datatype`: XSD datatype if literal (e.g., `xsd:string`, `xsd:date`)
- `target_class`: if the property expects an object reference
- `min_count`: 0 or 1 (required vs optional)
- `in_values`: allowed values for dropdowns
- `description`: help text

**Layout:** Tabbed panel with one tab per assigned type. Each tab shows a two-column mapping table.

**Interaction flow:**

1. For each type tab (e.g., "Note (225 files)"), show:
   - Left column: unique frontmatter keys found across all files of this type, with occurrence count
   - Right column: auto-suggested SHACL property match (see fuzzy matching below)
   - Confidence indicator: high/medium/low based on match score
   - Action buttons: Accept, Change, Skip, Store as Tag

2. User reviews each suggestion:
   - **Accept** (default for high-confidence): keeps the suggested mapping
   - **Change**: opens a dropdown of all available properties for this type
   - **Skip**: frontmatter key is ignored during import
   - **Store as Tag**: value is appended to the object's tags property

3. Special handling for title properties:
   - The wizard auto-detects which frontmatter key is the title based on the type's title predicate (dcterms:title for Note/Project, foaf:name for Person, skos:prefLabel for Concept)
   - If no frontmatter key maps to the title, the filename (without .md) is used as the title

4. Preview panel: clicking any frontmatter key shows sample values from 3-5 files of this type, helping the user understand what the key contains

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                   Step 3 of 6: Property Mapping    |
+------------------------------------------------------------------+
| [Note (225)] [Person (28)] [Project (31)] [Concept (19)]         |
+------------------------------------------------------------------+
| Mapping properties for: Note (225 files)                         |
|                                                                  |
| Frontmatter Key | Occurs | Suggested Mapping     | Conf | Action|
|-----------------|--------|-----------------------|------|-------|
| title           | 180    | dcterms:title (Title) |  H   | [Acc] |
| date            |  89    | dcterms:created (Date)|  H   | [Acc] |
| tags            |  67    | bpkm:tags (Tags)      |  H   | [Acc] |
| status          |  31    | bpkm:noteType (Type)  |  M   | [Chg] |
| related         |  12    | skos:related (Related) |  M   | [Acc] |
| source          |   8    | -- no match --        |  --  | [Tag] |
| aliases         |  22    | skos:altLabel (Alias) |  H   | [Acc] |
| rating          |   5    | -- no match --        |  --  | [Skp] |
|                                                                  |
| +--- Sample Values for "status" (3 of 31 files) ---+            |
| |  Daily Notes/2024-01-15.md: "active"              |            |
| |  Projects/Alpha.md: "completed"                   |            |
| |  Meetings/standup.md: "recurring"                 |            |
| +---------------------------------------------------+            |
|                                                                  |
|                            [Back: Types]  [Next: Relationships]  |
+------------------------------------------------------------------+
```

**Key behavior:** When the user maps `status` to `bpkm:status` for type Project, every Project file with a `status` frontmatter key will have its value written to `bpkm:status`. This is type-level mapping, not file-level.

---

### Step 4: Relationship Mapping

**Purpose:** Configure how wiki-links (`[[target]]`) are converted to typed edges. Uses type-pair heuristics from Chapter 24's EDGE_PREDICATES table, with user overrides.

**Layout:** A mapping table showing type-pair to predicate assignments, plus a sample preview.

**Interaction flow:**

1. Show the auto-detected type-pair -> predicate table (derived from the Chapter 24 heuristic, extended for any types from installed Mental Models):

   ```
   Source Type  | Target Type | Predicate                | Override
   -------------|-------------|--------------------------|--------
   Project      | Person      | bpkm:hasParticipant      | [Change]
   Person       | Project     | bpkm:participatesIn      | [Change]
   Note         | Project     | bpkm:relatedProject      | [Change]
   Note         | Concept     | bpkm:isAbout             | [Change]
   Note         | Person      | skos:related             | [Change]
   Concept      | Concept     | skos:related             | [Change]
   *            | *           | skos:related (fallback)  | [Change]
   ```

2. User can change any predicate via dropdown (populated from all predicates across all installed shapes)

3. Default fallback predicate: `skos:related` -- used when no specific type-pair rule matches

4. Sample edge preview: show 5-10 detected edges with source title, target title, and the predicate that would be applied

5. Link resolution stats:
   - Total wiki-links found across all files
   - Links that resolve to a file in the import (will create edges)
   - Links that do not resolve (target file not in vault or skipped)
   - Links where target has no assigned type (uses fallback)

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                    Step 4 of 6: Relationships      |
+------------------------------------------------------------------+
| Edge Predicate Rules                                             |
|                                                                  |
| Source Type | Target Type | Predicate              | Action      |
|-------------|-------------|------------------------|-------------|
| Project     | Person      | bpkm:hasParticipant    | [Change v]  |
| Person      | Project     | bpkm:participatesIn    | [Change v]  |
| Note        | Project     | bpkm:relatedProject    | [Change v]  |
| Note        | Concept     | bpkm:isAbout           | [Change v]  |
| Note        | Person      | skos:related           | [Change v]  |
| Concept     | Concept     | skos:related           | [Change v]  |
| * (default) | *           | [skos:related      v]  |             |
|                                                                  |
| +--- Link Resolution Stats ---+                                 |
| | Total wiki-links:       512  |                                 |
| | Resolvable:             438  (86%)                             |
| | Unresolvable:            74  (14%) -- targets not in vault     |
| +------------------------------+                                 |
|                                                                  |
| +--- Sample Edges (5 of 438) ---------------------------+       |
| | Meeting Jan 15 --> Alice Chen    | bpkm:hasParticipant |       |
| | Project Alpha  --> Bob Smith     | bpkm:hasParticipant |       |
| | ML Research    --> Deep Learning | skos:related        |       |
| | Daily 2024-01  --> Project Alpha | bpkm:relatedProject |       |
| | Alice Chen     --> Project Alpha | bpkm:participatesIn |       |
| +-------------------------------------------------------|       |
|                                                                  |
|                               [Back: Properties]  [Next: Review] |
+------------------------------------------------------------------+
```

---

### Step 5: Preview and Confirm

**Purpose:** Show a complete summary of the import before execution. Run dry-run validation against SHACL shapes. Allow the user to go back and fix issues.

**Layout:** Summary dashboard with expandable sections.

**Content:**

1. **Object counts by type:** Table with type, count, and property mapping count
2. **Property mappings summary:** Collapsed per-type sections showing all active mappings
3. **Edge summary:** Total edges, predicate distribution
4. **Sample object previews:** 3-5 fully rendered objects showing how they will look after import (title, properties, body snippet, edges)
5. **Dry-run validation results:**
   - Duplicate title detection: warn if two files would create objects with the same title under the same type
   - Missing required properties: check each object against its type's SHACL shape `min_count` constraints
   - Invalid property values: check `sh:in` constraints (e.g., status must be one of active/completed/on-hold/cancelled)
   - Validation uses `PropertyShape.min_count` and `PropertyShape.in_values` from `ShapesService.get_form_for_type()`

6. **"Start Import" button** -- only enabled when no blocking validation errors exist (warnings are OK)

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                      Step 5 of 6: Preview         |
+------------------------------------------------------------------+
| Import Summary                                                   |
|                                                                  |
| Objects to create:                                               |
|   Note ........... 225    Project ......... 31                   |
|   Person .......... 28    Concept ......... 19                   |
|   Total: 303 objects                                             |
|                                                                  |
| Edges to create: 438                                             |
|   bpkm:hasParticipant ... 89    bpkm:isAbout ........... 67     |
|   bpkm:relatedProject ... 54    skos:related ........... 228    |
|                                                                  |
| +--- Validation Results ---+                                    |
| | [!] 3 warnings, 0 errors |                                    |
| | WARN: 2 duplicate titles found (Note: "TODO", "README")      |
| | WARN: 12 Notes missing "noteType" (optional, will be blank)  |
| | WARN: 3 Projects have status="in-progress" (not in sh:in)    |
| +---------------------------+                                    |
|                                                                  |
| +--- Sample Object Preview ---+                                 |
| | Type: Person                 |                                 |
| | Title: Alice Chen            |                                 |
| | Properties:                  |                                 |
| |   foaf:name = "Alice Chen"   |                                 |
| |   schema:jobTitle = "Eng"    |                                 |
| | Body: "Alice is a senior..." |                                 |
| | Edges: 3 incoming, 1 out    |                                 |
| +------------------------------+                                 |
|                                                                  |
|                          [Back: Relationships]  [Start Import]   |
+------------------------------------------------------------------+
```

---

### Step 6: Import Execution and Progress

**Purpose:** Execute the import via batched Command API calls. Show real-time progress and error reporting.

**Execution phases:**

1. **Creating objects** -- `object.create` commands batched 10-20 per request via `POST /api/commands`
2. **Setting body content** -- `body.set` commands for each file's Markdown body (frontmatter stripped)
3. **Creating edges** -- `edge.create` commands for resolved wiki-links

Each phase shows a progress bar and phase indicator.

**Progress communication:** Server-Sent Events (SSE) from a dedicated endpoint. The backend streams progress events as JSON lines:
```json
{"phase": "objects", "current": 45, "total": 303, "last_title": "Alice Chen"}
{"phase": "bodies",  "current": 12, "total": 280, "last_title": "Meeting Jan 15"}
{"phase": "edges",   "current": 200, "total": 438}
{"phase": "complete", "objects_created": 303, "edges_created": 438, "errors": 2}
```

**Error handling:** Individual command failures do not abort the import. Errors are collected and displayed in an error log panel. The user can review failed items and retry or skip them.

**Completion screen:** Shows import results with links to browse imported objects:
- "Browse all imported Notes (225)"
- "Browse all imported Persons (28)"
- "View import error log (2 failures)"

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                       Step 6 of 6: Importing      |
+------------------------------------------------------------------+
|                                                                  |
| Phase: Creating Objects                                          |
| [=========================>          ] 156 / 303  (51%)          |
|                                                                  |
| Last created: "Project Alpha" (Project)                          |
|                                                                  |
| +--- Phase Progress ---+                                        |
| | [x] Scan vault       |                                        |
| | [x] Create objects   | <- current                             |
| | [ ] Set body content |                                        |
| | [ ] Create edges     |                                        |
| +----------------------+                                        |
|                                                                  |
| +--- Error Log (1 error so far) ---+                            |
| | [!] object.create failed for "README.md":                     |
| |     "Slug 'readme' already exists"                            |
| +-----------------------------------+                            |
|                                                                  |
| ---- After completion: ----                                      |
|                                                                  |
| Import Complete!                                                 |
| Objects created: 302/303 (1 failed)                              |
| Bodies set: 280/302                                              |
| Edges created: 436/438 (2 targets not found)                    |
|                                                                  |
| [Browse Notes (225)]  [Browse Persons (28)]  [View Error Log]   |
| [Close Wizard]                                                   |
+------------------------------------------------------------------+
```

---

## 3. Data Model for Import Jobs

### Option A: SQLAlchemy Models (Recommended)

Persistent storage enables resumable imports and import history. Uses the existing SQLAlchemy session infrastructure.

```python
class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_hex)
    status: Mapped[str] = mapped_column(String, default="scanning")
    # Status values: scanning, mapping, previewing, importing,
    #                complete, failed, cancelled
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=utcnow)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    file_mappings: Mapped[list["ImportFileMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    property_mappings: Mapped[list["ImportPropertyMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    edge_mappings: Mapped[list["ImportEdgeMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ImportFileMapping(Base):
    __tablename__ = "import_file_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    folder: Mapped[str] = mapped_column(String, default="")
    assigned_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # None = unassigned, "skip" = excluded from import
    frontmatter_keys: Mapped[str] = mapped_column(Text, default="{}")
    # JSON dict of frontmatter key -> value for this file
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    # Resolved title (from frontmatter or filename)
    created_iri: Mapped[str | None] = mapped_column(String, nullable=True)
    # IRI of the created object (populated during import execution)

    job: Mapped["ImportJob"] = relationship(back_populates="file_mappings")


class ImportPropertyMapping(Base):
    __tablename__ = "import_property_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    type_iri: Mapped[str] = mapped_column(String, nullable=False)
    frontmatter_key: Mapped[str] = mapped_column(String, nullable=False)
    target_predicate: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_mode: Mapped[str] = mapped_column(String, default="auto-suggested")
    # Modes: auto-suggested, user-set, skip, tag
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    job: Mapped["ImportJob"] = relationship(back_populates="property_mappings")

    # Unique constraint: one mapping per (job, type, frontmatter_key)
    __table_args__ = (
        UniqueConstraint("job_id", "type_iri", "frontmatter_key"),
    )


class ImportEdgeMapping(Base):
    __tablename__ = "import_edge_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)

    job: Mapped["ImportJob"] = relationship(back_populates="edge_mappings")

    __table_args__ = (
        UniqueConstraint("job_id", "source_type", "target_type"),
    )
```

### Option B: In-Memory Session State

Store wizard state in the server-side session (e.g., Starlette's SessionMiddleware with a signed cookie pointing to server-side storage).

**Pros:** No database migration needed, simpler implementation, automatic cleanup on session expiry.
**Cons:** Lost if session expires or server restarts, no import history, no resume-after-crash capability.

### Recommendation

Use **Option A (SQLAlchemy models)** for the following reasons:
- Import jobs for large vaults can take minutes; session timeout during import is a real risk
- Import history enables undo/rollback in a future enhancement
- The database migration is straightforward (4 new tables, no changes to existing tables)
- The existing Alembic migration pipeline handles this cleanly

---

## 4. Backend Integration Points

### Existing Services Used by Each Step

| Wizard Step | Backend Service | Method / Endpoint | Purpose |
|---|---|---|---|
| Step 1: Scan | *New* ImportService | `scan_vault(path)` | Walk directory, extract metadata |
| Step 2: Type Mapping | ShapesService | `get_types()` | Populate type dropdown with `[{iri, label}]` |
| Step 2: Type Mapping | ShapesService | `get_node_shapes()` | Get full `NodeShapeForm` list for type metadata |
| Step 3: Property Mapping | ShapesService | `get_form_for_type(type_iri)` | Get `PropertyShape` list for mapping targets |
| Step 3: Property Mapping | *New* FuzzyMatcher | `suggest_mappings(keys, shapes)` | Auto-suggest frontmatter-to-property matches |
| Step 4: Relationships | ShapesService | `get_node_shapes()` | Enumerate all property paths across all types |
| Step 5: Preview | ShapesService | `get_form_for_type(type_iri)` | Validate against `PropertyShape.min_count`, `in_values` |
| Step 5: Preview | SearchService | `search(title)` | Detect duplicate titles in existing data |
| Step 6: Import | Command API | `POST /api/commands` | Batch `object.create`, `body.set`, `edge.create` |

### New Endpoints Required

```
POST   /api/import/scan
  Body: { "path": "/home/user/obsidian-vault" }
  Response: { "job_id": "abc123", "file_count": 347, "summary": {...} }
  Creates an ImportJob in "scanning" status, returns vault audit summary.

GET    /api/import/{job_id}
  Response: Full ImportJob with file_mappings, property_mappings, edge_mappings.
  Used to hydrate the wizard UI on page load or resume.

PATCH  /api/import/{job_id}/files
  Body: { "updates": [{ "file_path": "People/Alice.md", "assigned_type": "Person" }] }
  Bulk-update file type assignments (Step 2).

PATCH  /api/import/{job_id}/properties
  Body: { "updates": [{ "type_iri": "...:Note", "key": "status", "target": "bpkm:status", "mode": "user-set" }] }
  Update property mappings (Step 3).

PATCH  /api/import/{job_id}/edges
  Body: { "updates": [{ "source_type": "Note", "target_type": "Concept", "predicate": "bpkm:isAbout" }] }
  Update edge predicate rules (Step 4).

GET    /api/import/{job_id}/preview
  Response: { "objects": [...], "edges": [...], "validation": {...} }
  Dry-run preview with validation results (Step 5).

POST   /api/import/{job_id}/execute
  Response: SSE stream of progress events
  Kicks off the actual import. Streams progress via Server-Sent Events.

GET    /api/import/{job_id}/status
  Response: { "status": "importing", "phase": "objects", "current": 45, "total": 303 }
  Poll-based fallback if SSE is not available.

DELETE /api/import/{job_id}
  Cancels and deletes an import job (cleanup).
```

### Command API Usage During Import (Step 6)

The import execution phase uses the existing `POST /api/commands` endpoint with batch payloads. Each batch contains 10-20 commands for atomicity and performance.

**Phase 1 -- Object creation:**
```json
[
  {
    "command": "object.create",
    "params": {
      "type": "Note",
      "slug": "meeting-jan-15",
      "properties": {
        "dcterms:title": "Meeting Jan 15",
        "bpkm:noteType": "meeting-note",
        "bpkm:tags": "meeting, standup"
      }
    }
  },
  ...
]
```

**Phase 2 -- Body content:**
```json
[
  {
    "command": "body.set",
    "params": {
      "iri": "https://example.org/data/Note/meeting-jan-15",
      "body": "## Attendees\n- Alice Chen\n- Bob Smith\n\n## Discussion\n..."
    }
  },
  ...
]
```

**Phase 3 -- Edge creation:**
```json
[
  {
    "command": "edge.create",
    "params": {
      "source": "https://example.org/data/Note/meeting-jan-15",
      "target": "https://example.org/data/Person/alice-chen",
      "predicate": "urn:sempkm:model:basic-pkm:hasParticipant"
    }
  },
  ...
]
```

### Markdown Body Extraction

During import, the backend strips YAML frontmatter from each .md file before sending the body content:

```python
import re

def extract_body(markdown_text: str) -> str:
    """Strip YAML frontmatter and return the body content."""
    return re.sub(
        r"^---\n.*?\n---\n?", "", markdown_text,
        count=1, flags=re.DOTALL
    ).strip()
```

Wiki-links (`[[target]]`) in the body are preserved as-is. A future enhancement could convert them to SemPKM-style object links, but for the initial implementation they remain as plain text.

---

## 5. Fuzzy Matching Algorithm for Property Auto-Suggestion

### Problem Statement

Given a YAML frontmatter key (e.g., `"related"`, `"jobTitle"`, `"date_created"`) and a list of `PropertyShape` objects, suggest the best-matching SHACL property.

The challenge: frontmatter keys use informal names (`"related"`, `"status"`, `"name"`), while SHACL properties use full IRIs (`http://www.w3.org/2004/02/skos/core#related`, `urn:sempkm:model:basic-pkm:status`, `http://xmlns.com/foaf/0.1/name`).

### Recommended Approach: Multi-Signal Token Matching

Use a combination of three signals, weighted and combined:

**Signal 1: Exact local name match (weight: 1.0)**
Extract the local name from the `PropertyShape.path` IRI (the part after `#` or the last `/`) and compare case-insensitively to the frontmatter key.

```python
def local_name(iri: str) -> str:
    """Extract local name from IRI (after # or last /)."""
    if "#" in iri:
        return iri.rsplit("#", 1)[-1]
    return iri.rsplit("/", 1)[-1]

# "http://www.w3.org/2004/02/skos/core#related" -> "related"
# "http://purl.org/dc/terms/title" -> "title"
# "urn:sempkm:model:basic-pkm:status" -> "status"
```

If `local_name(property.path).lower() == frontmatter_key.lower()`, confidence = 1.0 (exact match).

**Signal 2: PropertyShape.name similarity (weight: 0.8)**
Compare the frontmatter key to `PropertyShape.name` (the human-readable label like "Title", "Status", "Job Title") using Jaro-Winkler similarity.

Jaro-Winkler is preferred over Levenshtein for short strings because:
- It gives higher scores to strings that match from the beginning (prefix bonus)
- It handles transpositions well
- It is more discriminating for short tokens (5-15 chars) than raw edit distance

```python
from jellyfish import jaro_winkler_similarity

score = jaro_winkler_similarity(
    frontmatter_key.lower(),
    property.name.lower()
)
```

**Signal 3: Token overlap (weight: 0.6)**
Split both the frontmatter key and the property name/local-name on camelCase boundaries, underscores, and hyphens. Compute Jaccard similarity on the resulting token sets.

```python
import re

def tokenize(s: str) -> set[str]:
    """Split on camelCase, underscores, hyphens."""
    # Split camelCase: "jobTitle" -> ["job", "Title"]
    tokens = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    # Split on non-alphanumeric
    parts = re.split(r'[^a-zA-Z0-9]+', tokens)
    return {t.lower() for t in parts if t}

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

# "date_created" tokens: {"date", "created"}
# "dcterms:created" local name "created" tokens: {"created"}
# Jaccard: 1/2 = 0.5
```

**Combined score:**

```python
def match_score(
    frontmatter_key: str,
    prop: PropertyShape
) -> float:
    ln = local_name(prop.path).lower()
    fk = frontmatter_key.lower()

    # Signal 1: exact local name match
    if ln == fk:
        return 1.0

    # Signal 2: Jaro-Winkler on PropertyShape.name
    name_score = jaro_winkler_similarity(fk, prop.name.lower())

    # Signal 3: token overlap (best of local name and property name)
    fk_tokens = tokenize(fk)
    ln_tokens = tokenize(ln)
    name_tokens = tokenize(prop.name)
    token_score = max(jaccard(fk_tokens, ln_tokens), jaccard(fk_tokens, name_tokens))

    return 0.8 * name_score + 0.6 * token_score
```

**Confidence levels:**
- Score >= 0.9: High confidence (auto-accept candidate)
- Score >= 0.6: Medium confidence (suggest but require confirmation)
- Score < 0.6: Low confidence (show as "no match", offer manual selection)

### Dependency

The `jellyfish` Python library provides Jaro-Winkler (pure C implementation, fast). Add to `pyproject.toml`:

```toml
dependencies = [
    ...,
    "jellyfish>=1.0",
]
```

Alternative: implement Jaro-Winkler from scratch (the algorithm is ~30 lines) to avoid the dependency.

### Example Matches

| Frontmatter Key | Best Match Property | Score | Confidence |
|---|---|---|---|
| `title` | dcterms:title (name: "Title") | 1.0 | High |
| `name` | foaf:name (name: "Name") | 1.0 | High |
| `status` | bpkm:status (name: "Status") | 1.0 | High |
| `related` | skos:related (name: "Related") | 1.0 | High |
| `date_created` | dcterms:created (name: "Created") | 0.78 | Medium |
| `jobTitle` | schema:jobTitle (name: "Job Title") | 0.95 | High |
| `priority` | bpkm:priority (name: "Priority") | 1.0 | High |
| `source_url` | (no match) | 0.3 | Low |
| `rating` | (no match) | 0.2 | Low |

---

## 6. UI Technology Notes

### htmx Compatibility

The wizard is fully compatible with SemPKM's htmx-driven architecture. Each wizard step is a server-rendered HTML partial loaded via `hx-get` or `hx-post`.

**Step navigation:**

```html
<!-- Stepper bar -->
<div class="wizard-steps">
  <button hx-get="/import/{{job_id}}/step/1" hx-target="#wizard-content"
          class="step active">1. Scan</button>
  <button hx-get="/import/{{job_id}}/step/2" hx-target="#wizard-content"
          class="step">2. Types</button>
  ...
</div>

<div id="wizard-content">
  <!-- Step content loaded here via htmx -->
</div>
```

**Type assignment (Step 2):**

```html
<!-- Individual file type dropdown -->
<select hx-post="/import/{{job_id}}/files/{{file_id}}/type"
        hx-target="#type-distribution"
        hx-swap="outerHTML"
        name="type">
  {% for t in types %}
  <option value="{{t.iri}}" {% if t.iri == file.assigned_type %}selected{% endif %}>
    {{t.label}}
  </option>
  {% endfor %}
  <option value="skip">Skip</option>
</select>
```

**Glob pattern application (Step 2):**

```html
<form hx-post="/import/{{job_id}}/apply-glob"
      hx-target="#file-table"
      hx-swap="outerHTML">
  <input name="pattern" placeholder="Projects/**" />
  <select name="type">
    {% for t in types %}
    <option value="{{t.iri}}">{{t.label}}</option>
    {% endfor %}
  </select>
  <button type="submit">Apply</button>
</form>
```

**Property mapping (Step 3):**

```html
<!-- Property mapping row -->
<tr id="mapping-{{key}}">
  <td>{{key}}</td>
  <td>{{occurrence_count}}</td>
  <td>
    <select hx-post="/import/{{job_id}}/properties/{{type_iri}}/{{key}}"
            hx-target="#mapping-{{key}}"
            hx-swap="outerHTML"
            name="target">
      <option value="">-- no match --</option>
      {% for prop in available_properties %}
      <option value="{{prop.path}}" {% if prop.path == suggested %}selected{% endif %}>
        {{prop.name}} ({{prop.path | local_name}})
      </option>
      {% endfor %}
    </select>
  </td>
  <td>{{confidence_badge}}</td>
  <td>
    <button hx-post="..." hx-vals='{"mode": "skip"}'>Skip</button>
    <button hx-post="..." hx-vals='{"mode": "tag"}'>Tag</button>
  </td>
</tr>
```

### Server-Sent Events for Import Progress (Step 6)

htmx has built-in SSE support via the `sse` extension:

```html
<div hx-ext="sse"
     sse-connect="/api/import/{{job_id}}/execute"
     sse-swap="progress">
  <div id="progress-bar">Waiting to start...</div>
</div>
```

The backend SSE endpoint streams events:

```python
from starlette.responses import StreamingResponse

async def import_sse(job_id: str):
    async def event_stream():
        async for progress in execute_import(job_id):
            yield f"event: progress\ndata: {json.dumps(progress)}\n\n"
        yield f"event: complete\ndata: {json.dumps(final_summary)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

### State Management

All wizard state is stored server-side in the ImportJob SQLAlchemy model. The browser holds only the `job_id` (in the URL path or a hidden form field). This means:

- No complex JavaScript state management
- Browser refresh or back-button works correctly (htmx reloads from server)
- Multiple browser tabs for the same job show consistent state
- Session expiry does not lose import progress (data is in the database)

### CSS and Layout

The wizard UI reuses existing SemPKM CSS patterns:
- Card grid for summary stats (Step 1)
- Data table with sortable columns (Steps 2, 3, 4)
- Badge/pill components for type labels and confidence indicators
- Progress bar component (Step 6)
- The wizard panel replaces the main content area (not a modal overlay), allowing full-width tables

---

## 7. Detailed Screen Descriptions

### Step 1 Screen: Vault Scan

**Header:** "Import from Obsidian" with step indicator (1 of 6)
**Main content:**
- Path input field with optional browse button (if server supports file dialogs)
- "Scan" button triggers `POST /api/import/scan`
- After scan completes, displays a summary card grid:
  - Top row: 4 metric cards (Total Files, With Frontmatter, Unique Tags, Wiki-links)
  - Bottom section: two side-by-side panels
    - Left: Folder distribution table (folder name, file count, percentage bar)
    - Right: Top frontmatter keys list (key name, occurrence count)
- Footer: Cancel and Next buttons

### Step 2 Screen: Type Mapping

**Header:** Step indicator (2 of 6) + glob pattern input bar
**Main content:** Full-width data table
- Columns: Checkbox | File Path | Folder | Frontmatter Keys (truncated) | Assigned Type (dropdown)
- Rows grouped by folder with collapsible folder headers
- Folder header row: bold text, type dropdown applies to all files in folder
- Selected rows can be bulk-assigned via toolbar action
**Sidebar:** Type distribution card with live-updating counts and colored bars
**Footer:** Back and Next buttons

### Step 3 Screen: Property Mapping

**Header:** Step indicator (3 of 6) + type tabs
**Tab bar:** One tab per type with file count badge: "Note (225)" | "Person (28)" | "Project (31)" | "Concept (19)"
**Main content:** Mapping table for the active type tab
- Columns: Frontmatter Key | Occurs In | Suggested Mapping (dropdown) | Confidence (badge) | Action (Accept/Change/Skip/Tag)
- Below the table: collapsible "Sample Values" panel showing 3 example values for the selected key
**Footer:** Back and Next buttons

### Step 4 Screen: Relationship Mapping

**Header:** Step indicator (4 of 6)
**Main content:** Two sections
- Top: Edge predicate rules table (Source Type | Target Type | Predicate dropdown | Override button)
- Middle: Link resolution stats card (total links, resolvable count, unresolvable count)
- Bottom: Sample edges table showing 5-10 example edges with source, target, and predicate
**Footer:** Back and Next buttons

### Step 5 Screen: Preview and Confirm

**Header:** Step indicator (5 of 6)
**Main content:** Dashboard layout
- Top: Object counts by type (horizontal bar or card row)
- Middle-left: Collapsible property mapping summary per type
- Middle-right: Edge predicate distribution
- Bottom: Validation results panel (warnings in yellow, errors in red)
- Below: 3-5 sample object cards showing full rendered preview
**Footer:** Back and "Start Import" button (disabled if blocking errors exist)

### Step 6 Screen: Import Progress

**Header:** Step indicator (6 of 6)
**Main content:**
- Phase checklist with progress bar for current phase
- Current item indicator ("Last created: ...")
- Error log panel (collapsible, shows failed commands)
- After completion: summary card with browse links per type
**Footer:** "Close Wizard" button (after completion)

---

## 8. Open Questions and Future Enhancements

### LLM-Assisted Classification (Enhancement)

The wizard could offer an optional "Auto-classify with AI" button in Step 2 that sends unassigned files to an LLM for type classification (reusing the prompt from Chapter 24). This would require:
- LLM API configuration in SemPKM settings (API URL, key, model)
- A background job that classifies files in batches
- Results appearing as suggested types in the file table with confidence indicators
- User still reviews and confirms all suggestions

This is an enhancement, not a requirement for the initial wizard. The folder-based and manual assignment flows handle most vaults well without an LLM.

### Incremental / Delta Imports

After the initial import, users may want to re-import only new or modified files. This requires:
- Tracking which vault files have been imported (store in ImportFileMapping.created_iri)
- Comparing file modification dates against the last import timestamp
- Detecting renamed or moved files (by content hash or title matching)
- UI for reviewing the delta before importing

### Undo / Rollback

The import wizard creates objects via the Command API, which records all mutations in event graphs. A rollback feature could:
- Store the event IRIs generated during import in the ImportJob record
- Provide a "Rollback Import" button that deletes all objects created by the import
- Implementation: query the event graph for all objects created by the import's event IRIs, then issue `object.delete` commands

This depends on a `object.delete` command being available in the Command API (currently not implemented).

### Non-Obsidian Markdown Sources

The wizard's vault scanning logic assumes Obsidian conventions (YAML frontmatter, `[[wiki-links]]`, `#tags`). Other Markdown-based tools use different conventions:
- **Logseq:** block-based structure, `((block-refs))`, `[[page-links]]`
- **Dendrite:** hierarchical filenames (`root.child.grandchild.md`), no wiki-links
- **Foam/Zettelkasten:** UID-based filenames, `[[wiki-links]]` similar to Obsidian
- **Bear:** nested tags (`#tag/subtag`), no frontmatter

A future enhancement could add pluggable "source adapters" that normalize different Markdown tool conventions into the wizard's internal format.

### Batch Size Tuning

The current batch size (10-20 commands per `POST /api/commands`) is conservative. For large vaults (>1000 files), this could be tuned:
- Measure transaction latency vs batch size on the target triplestore
- Consider async command processing with a queue for very large imports
- Add a "batch size" setting in the wizard's advanced options

### Conflict Detection

For repeat imports or imports into a populated SemPKM instance:
- Use `SearchService.search(title)` to detect objects with matching titles already in the triplestore
- Offer merge/skip/replace options per conflict
- Show a conflict resolution step between Preview and Import

---

## 9. Implementation Priority

### Phase 1: Minimum Viable Wizard
- Steps 1, 2, 5, 6 (Scan, Type Mapping, Preview, Import)
- Folder-based type assignment only (no glob patterns)
- Title derived from filename, no property mapping
- All wiki-links mapped to `skos:related`
- No LLM integration

### Phase 2: Property and Relationship Mapping
- Steps 3, 4 (Property Mapping, Relationship Mapping)
- Fuzzy matching for property suggestions
- Type-pair heuristic for edge predicates
- Sample previews and validation

### Phase 3: Advanced Features
- Glob pattern type assignment
- LLM-assisted classification option
- Incremental imports
- Conflict detection
- Undo/rollback

This phased approach delivers a usable wizard quickly (Phase 1 covers the most common import scenario: folder-based classification into Basic PKM) while leaving room for sophisticated features in later iterations.

# PPV Productivity System Ontology
# Translated from System/Schema Spec.md
# RDFS/OWL/SHACL Turtle format

@prefix ppv:  <https://ppv.systems/ontology#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .

# =============================================================================
# ONTOLOGY DECLARATION
# =============================================================================

<https://ppv.systems/ontology>
    a owl:Ontology ;
    rdfs:label "PPV Productivity System Ontology" ;
    rdfs:comment "Machine-readable RDFS/OWL/SHACL data model for August Bradley's Pillars, Pipelines, and Vaults (PPV) productivity system, as implemented in Obsidian with the Bases plugin. Derived from System/Schema Spec.md." .


# =============================================================================
# CLASSES
# =============================================================================

# --- Abstract base classes ---

ppv:PPVEntity
    a owl:Class ;
    rdfs:label "PPV Entity" ;
    rdfs:comment "Abstract base class for all entities in the PPV system. Every note in the vault corresponds to an instance of a subclass of PPVEntity." .

ppv:HierarchyEntity
    a owl:Class ;
    rdfs:subClassOf ppv:PPVEntity ;
    rdfs:label "Hierarchy Entity" ;
    rdfs:comment "Abstract class for the five core hierarchy levels: Pillar, ValueGoal, GoalOutcome, Project, ActionItem. These form the core planning chain." .

ppv:ReviewEntity
    a owl:Class ;
    rdfs:subClassOf ppv:PPVEntity ;
    rdfs:label "Review Entity" ;
    rdfs:comment "Abstract class for the four review cycle types: WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview." .

# --- User-defined grouping concept ---

ppv:PillarGroup
    a owl:Class ;
    rdfs:label "Pillar Group" ;
    rdfs:comment "User-defined grouping for organizing pillars. Instances are created by the user (e.g., Growth, Business, Home & Social). Not a fixed enumeration." .

# --- Concrete hierarchy classes ---

ppv:Pillar
    a owl:Class ;
    rdfs:subClassOf ppv:HierarchyEntity ;
    rdfs:label "Pillar" ;
    rdfs:comment "Top-level life area that organizes all goals, projects, and actions. Examples: Health & Fitness, Career, Relationships." .

ppv:ValueGoal
    a owl:Class ;
    rdfs:subClassOf ppv:HierarchyEntity ;
    rdfs:label "Value Goal" ;
    rdfs:comment "Long-term aspiration linked to a Pillar. Called 'Value Goals' in August Bradley's Notion PPV template." .

ppv:GoalOutcome
    a owl:Class ;
    rdfs:subClassOf ppv:HierarchyEntity ;
    rdfs:label "Goal Outcome" ;
    rdfs:comment "Measurable result derived from a ValueGoal. Called 'Outcome Goals' in August Bradley's Notion PPV template." .

ppv:Project
    a owl:Class ;
    rdfs:subClassOf ppv:HierarchyEntity ;
    rdfs:label "Project" ;
    rdfs:comment "Discrete work item with completion criteria, linked to a GoalOutcome. Consists of ActionItems." .

ppv:ActionItem
    a owl:Class ;
    rdfs:subClassOf ppv:HierarchyEntity ;
    rdfs:label "Action Item" ;
    rdfs:comment "Individual task that drives project and goal completion. The atomic unit of work in the PPV system." .

# --- Concrete review classes ---

ppv:WeeklyReview
    a owl:Class ;
    rdfs:subClassOf ppv:ReviewEntity ;
    rdfs:label "Weekly Review" ;
    rdfs:comment "Weekly review cycle note for pillar scoring, work review, and next-week planning." .

ppv:MonthlyReview
    a owl:Class ;
    rdfs:subClassOf ppv:ReviewEntity ;
    rdfs:label "Monthly Review" ;
    rdfs:comment "Monthly review cycle note for aggregating weekly reviews, pillar assessment, pipeline review, and vault maintenance." .

ppv:QuarterlyReview
    a owl:Class ;
    rdfs:subClassOf ppv:ReviewEntity ;
    rdfs:label "Quarterly Review" ;
    rdfs:comment "Quarterly review cycle note for aggregating monthly reviews and conducting deeper strategic reflection." .

ppv:YearlyReview
    a owl:Class ;
    rdfs:subClassOf ppv:ReviewEntity ;
    rdfs:label "Yearly Review" ;
    rdfs:comment "Yearly review cycle note for annual reflection and strategic planning." .


# =============================================================================
# OBJECT PROPERTIES (links between entities)
# =============================================================================

# --- Core hierarchy chain (upward / parent links) ---

ppv:pillar
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "pillar" ;
    rdfs:range ppv:Pillar ;
    rdfs:comment "Links a ValueGoal (required), Project (optional shortcut), or ActionItem (optional shortcut) to its Pillar. The Project and ActionItem uses are denormalized shortcuts: the canonical path is ActionItem -> Project -> GoalOutcome -> ValueGoal -> Pillar, but direct pillar links are stored for convenient dashboard queries." .

ppv:valueGoal
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "valueGoal" ;
    rdfs:domain ppv:GoalOutcome ;
    rdfs:range ppv:ValueGoal ;
    rdfs:comment "Links a GoalOutcome to its parent ValueGoal. Required on GoalOutcome." .

ppv:goalOutcome
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "goalOutcome" ;
    rdfs:domain ppv:Project ;
    rdfs:range ppv:GoalOutcome ;
    rdfs:comment "Links a Project to its parent GoalOutcome. Optional (some projects may be standalone)." .

ppv:project
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "project" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range ppv:Project ;
    rdfs:comment "Links an ActionItem to its parent Project. Optional (some actions may be standalone)." .

ppv:pillarGroup
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "pillarGroup" ;
    rdfs:domain ppv:Pillar ;
    rdfs:range ppv:PillarGroup ;
    rdfs:comment "Links a Pillar to its user-defined PillarGroup (e.g., Growth, Business, Home & Social). The set of PillarGroup instances is open and user-defined; this is NOT constrained to a fixed enumeration." .

# --- Review chain (upward / parent links) ---

ppv:month
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "month" ;
    rdfs:domain ppv:WeeklyReview ;
    rdfs:range ppv:MonthlyReview ;
    rdfs:comment "Links a WeeklyReview to its parent MonthlyReview for monthly rollup queries." .

ppv:quarter
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "quarter" ;
    rdfs:domain ppv:MonthlyReview ;
    rdfs:range ppv:QuarterlyReview ;
    rdfs:comment "Links a MonthlyReview to its parent QuarterlyReview for quarterly rollup queries." .

ppv:yearLink
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:label "yearLink" ;
    rdfs:domain ppv:QuarterlyReview ;
    rdfs:range ppv:YearlyReview ;
    rdfs:comment "Links a QuarterlyReview to its parent YearlyReview. Named yearLink (not year) to avoid collision with the xsd:string year datatype property on Monthly/Quarterly/Yearly reviews." .

ppv:quarters
    a owl:ObjectProperty ;
    rdfs:label "quarters" ;
    rdfs:domain ppv:YearlyReview ;
    rdfs:range ppv:QuarterlyReview ;
    rdfs:comment "Links a YearlyReview to its constituent QuarterlyReviews (multi-value). Not a FunctionalProperty because a year has up to 4 quarters." .

# --- Inverse properties (downward / child direction) ---

ppv:hasValueGoals
    a owl:ObjectProperty ;
    rdfs:label "hasValueGoals" ;
    rdfs:comment "Inverse of ppv:pillar — navigates from a Pillar to all its ValueGoals." ;
    owl:inverseOf ppv:pillar .

ppv:hasGoalOutcomes
    a owl:ObjectProperty ;
    rdfs:label "hasGoalOutcomes" ;
    rdfs:comment "Inverse of ppv:valueGoal — navigates from a ValueGoal to all its GoalOutcomes." ;
    owl:inverseOf ppv:valueGoal .

ppv:hasProjects
    a owl:ObjectProperty ;
    rdfs:label "hasProjects" ;
    rdfs:comment "Inverse of ppv:goalOutcome — navigates from a GoalOutcome to all its Projects." ;
    owl:inverseOf ppv:goalOutcome .

ppv:hasActionItems
    a owl:ObjectProperty ;
    rdfs:label "hasActionItems" ;
    rdfs:comment "Inverse of ppv:project — navigates from a Project to all its ActionItems." ;
    owl:inverseOf ppv:project .

ppv:hasWeeklyReviews
    a owl:ObjectProperty ;
    rdfs:label "hasWeeklyReviews" ;
    rdfs:comment "Inverse of ppv:month — navigates from a MonthlyReview to all its WeeklyReviews." ;
    owl:inverseOf ppv:month .

ppv:hasMonthlyReviews
    a owl:ObjectProperty ;
    rdfs:label "hasMonthlyReviews" ;
    rdfs:comment "Inverse of ppv:quarter — navigates from a QuarterlyReview to all its MonthlyReviews." ;
    owl:inverseOf ppv:quarter .

ppv:hasQuarterlyReviews
    a owl:ObjectProperty ;
    rdfs:label "hasQuarterlyReviews" ;
    rdfs:comment "Inverse of ppv:yearLink — navigates from a YearlyReview to all its QuarterlyReviews." ;
    owl:inverseOf ppv:yearLink .


# =============================================================================
# DATATYPE PROPERTIES
# =============================================================================

# --- Text properties (xsd:string) ---

ppv:type
    a owl:DatatypeProperty ;
    rdfs:label "type" ;
    rdfs:domain ppv:PPVEntity ;
    rdfs:range xsd:string ;
    rdfs:comment "Note type identifier. Fixed value per class: 'pillar', 'value-goal', 'goal-outcome', 'project', 'action', 'weekly-review', 'monthly-review', 'quarterly-review', 'yearly-review'. Required on all entities." .

ppv:status
    a owl:DatatypeProperty ;
    rdfs:label "status" ;
    rdfs:domain ppv:PPVEntity ;
    rdfs:range xsd:string ;
    rdfs:comment "Lifecycle status of the entity. Allowed values differ per type (see SHACL shapes). Uses Title Case matching Notion exactly. Required on all hierarchy entities and review entities." .

ppv:cycle
    a owl:DatatypeProperty ;
    rdfs:label "cycle" ;
    rdfs:domain ppv:ReviewEntity ;
    rdfs:range xsd:string ;
    rdfs:comment "Review cycle identifier. Fixed value per review type: 'weekly', 'monthly', 'quarterly', 'yearly'. Required on all review entities." .

ppv:priority
    a owl:DatatypeProperty ;
    rdfs:label "priority" ;
    rdfs:range xsd:string ;
    rdfs:comment "Relative importance/urgency. Used by ValueGoal, Project, and ActionItem. ValueGoal and Project use positional priorities ('1st Priority' through '5th Priority'). ActionItem uses priority labels with emojis (e.g., 'Immediate 🔥', 'Quick ⚡'). Optional on all types." .

ppv:icon
    a owl:DatatypeProperty ;
    rdfs:label "icon" ;
    rdfs:domain ppv:Pillar ;
    rdfs:range xsd:string ;
    rdfs:comment "Emoji icon for the Pillar. Obsidian addition for dashboard display. Optional." .

ppv:color
    a owl:DatatypeProperty ;
    rdfs:label "color" ;
    rdfs:domain ppv:Pillar ;
    rdfs:range xsd:string ;
    rdfs:comment "Color name for the Pillar. Obsidian addition for dashboard display. Optional." .

ppv:focusObjective
    a owl:DatatypeProperty ;
    rdfs:label "focusObjective" ;
    rdfs:domain ppv:WeeklyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "The focus objective or theme for the review week. Displayed in the planning section of the Weekly Review. Corresponds to Notion's Focus/Objective field. Optional." .

ppv:monthName
    a owl:DatatypeProperty ;
    rdfs:label "monthName" ;
    rdfs:domain ppv:MonthlyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "Human-readable month label in 'February 2026' format. Used as display name and in weekly review rollup filter. Named monthName to avoid collision with the ppv:month object property. Required on MonthlyReview." .

ppv:quarterName
    a owl:DatatypeProperty ;
    rdfs:label "quarterName" ;
    rdfs:domain ppv:QuarterlyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "Human-readable quarter label in 'Q1 2026' format. Used as display name. Required on QuarterlyReview." .

ppv:year
    a owl:DatatypeProperty ;
    rdfs:label "year" ;
    rdfs:range xsd:string ;
    rdfs:comment "Year label in '2026' format. Used on MonthlyReview (required), QuarterlyReview (via yearLink object property to YearlyReview), and YearlyReview (required). Required on MonthlyReview and YearlyReview." .

ppv:yearName
    a owl:DatatypeProperty ;
    rdfs:label "yearName" ;
    rdfs:domain ppv:YearlyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "Human-readable year label in '2026' format for YearlyReview. Required on YearlyReview." .

ppv:gratitude
    a owl:DatatypeProperty ;
    rdfs:label "gratitude" ;
    rdfs:domain ppv:MonthlyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "Monthly gratitude reflection stored as a frontmatter property, matching Notion's database property approach. Optional." .

ppv:learnedThisMonth
    a owl:DatatypeProperty ;
    rdfs:label "learnedThisMonth" ;
    rdfs:domain ppv:MonthlyReview ;
    rdfs:range xsd:string ;
    rdfs:comment "Key learning from the month stored as a frontmatter property, matching Notion's database property approach. Optional." .

ppv:description
    a owl:DatatypeProperty ;
    rdfs:label "description" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:string ;
    rdfs:comment "Freeform description/notes for the ActionItem. Displayed in Action Items dashboard. Optional." .

ppv:context
    a owl:DatatypeProperty ;
    rdfs:label "context" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:string ;
    rdfs:comment "GTD-style execution context for the ActionItem. Allowed values: 'home', 'office', 'errands', 'calls', 'computer', 'anywhere'. Used for context-based filtering in Action Items dashboard. Optional." .

ppv:energy
    a owl:DatatypeProperty ;
    rdfs:label "energy" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:string ;
    rdfs:comment "Energy level required for the ActionItem. Allowed values: 'low', 'medium', 'high'. Default: 'medium'. Used for energy-based filtering in Action Items dashboard. Optional." .

# --- Date properties (xsd:date) ---

ppv:created
    a owl:DatatypeProperty ;
    rdfs:label "created" ;
    rdfs:domain ppv:PPVEntity ;
    rdfs:range xsd:date ;
    rdfs:comment "ISO date when the note was created (YYYY-MM-DD). Defaults to current date. Required on all entity types." .

ppv:targetDate
    a owl:DatatypeProperty ;
    rdfs:label "targetDate" ;
    rdfs:range xsd:date ;
    rdfs:comment "Target completion date. Used by ValueGoal (optional) and GoalOutcome (optional). ISO date format." .

ppv:startDate
    a owl:DatatypeProperty ;
    rdfs:label "startDate" ;
    rdfs:range xsd:date ;
    rdfs:comment "Start date. Used by Project (optional) and WeeklyReview (required: Monday of review week). ISO date format." .

ppv:endDate
    a owl:DatatypeProperty ;
    rdfs:label "endDate" ;
    rdfs:domain ppv:WeeklyReview ;
    rdfs:range xsd:date ;
    rdfs:comment "End date of the weekly review period (Sunday of review week). Required on WeeklyReview. Used as upper bound for completed actions filter. ISO date format." .

ppv:dueDate
    a owl:DatatypeProperty ;
    rdfs:label "dueDate" ;
    rdfs:domain ppv:Project ;
    rdfs:range xsd:date ;
    rdfs:comment "Due date for the Project. Obsidian addition (Notion uses a date range 'Timeline Dates'; Obsidian splits this into startDate + dueDate). Used in Projects Board and Life Dashboard sorting. Optional." .

ppv:reviewDate
    a owl:DatatypeProperty ;
    rdfs:label "reviewDate" ;
    rdfs:domain ppv:Project ;
    rdfs:range xsd:date ;
    rdfs:comment "Date when the Project is next scheduled for review. Obsidian addition. Displayed in Projects Board. Optional." .

ppv:completedDate
    a owl:DatatypeProperty ;
    rdfs:label "completedDate" ;
    rdfs:range xsd:date ;
    rdfs:comment "Date when the GoalOutcome or Project was completed. Obsidian addition for tracking completion history. Used in completed item sorting. Optional." .

ppv:completionDate
    a owl:DatatypeProperty ;
    rdfs:label "completionDate" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:date ;
    rdfs:comment "Date when the ActionItem was completed. Used in Weekly Review to filter completed actions within the review period. Obsidian addition. Optional." .

ppv:doDate
    a owl:DatatypeProperty ;
    rdfs:label "doDate" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:date ;
    rdfs:comment "Date when the ActionItem should be done. Corresponds to Notion 'Do Date' field (PPV philosophy: when to DO, not when it's DUE). Used in Action Items dashboard sorting. Optional." .

# --- Number properties (xsd:integer) ---

ppv:order
    a owl:DatatypeProperty ;
    rdfs:label "order" ;
    rdfs:domain ppv:Pillar ;
    rdfs:range xsd:integer ;
    rdfs:comment "Display order for the Pillar on dashboards. Integer in range 1-10. Obsidian addition for dashboard display control. Optional." .

ppv:progress
    a owl:DatatypeProperty ;
    rdfs:label "progress" ;
    rdfs:range xsd:integer ;
    rdfs:comment "Completion percentage as integer 0-100. Used by GoalOutcome (Notion: '% Completed') and Project. Displayed in Goals Overview, Projects Board, and Life Dashboard. Optional." .

ppv:timeEstimate
    a owl:DatatypeProperty ;
    rdfs:label "timeEstimate" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:integer ;
    rdfs:comment "Estimated time to complete the ActionItem, in minutes as integer. Obsidian addition for GTD-style time-boxing. Optional." .

# --- Boolean properties (xsd:boolean) ---

ppv:done
    a owl:DatatypeProperty ;
    rdfs:label "done" ;
    rdfs:domain ppv:ActionItem ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether the ActionItem is complete. Maps to Obsidian checkbox property (true/false). Used in Action Items dashboard to filter incomplete tasks. Optional (defaults false)." .


# =============================================================================
# SHACL NODE SHAPES
# =============================================================================

# --- Pillar Shape ---

ppv:PillarShape
    a sh:NodeShape ;
    sh:targetClass ppv:Pillar ;
    rdfs:label "Pillar Shape" ;
    rdfs:comment "SHACL constraints for Pillar notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "pillar" ) ;
        rdfs:comment "Fixed type identifier for Pillar notes."
    ] ;

    # Required: status
    sh:property [
        sh:path ppv:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Active"
            "Active (Hide from Command Center)"
            "Paused"
            "Inactive"
        ) ;
        rdfs:comment "Pillar lifecycle status."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: pillarGroup (user-defined class, NOT sh:in)
    sh:property [
        sh:path ppv:pillarGroup ;
        sh:maxCount 1 ;
        sh:class ppv:PillarGroup ;
        rdfs:comment "User-defined pillar group (e.g., Growth, Business, Home & Social). Validated as instance of ppv:PillarGroup, NOT constrained to a fixed enumeration."
    ] ;

    # Optional: icon
    sh:property [
        sh:path ppv:icon ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Emoji icon. Optional."
    ] ;

    # Optional: color
    sh:property [
        sh:path ppv:color ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Color name. Optional."
    ] ;

    # Optional: order (1-10)
    sh:property [
        sh:path ppv:order ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
        sh:minInclusive 1 ;
        sh:maxInclusive 10 ;
        rdfs:comment "Display order 1-10. Optional."
    ] .


# --- Value Goal Shape ---

ppv:ValueGoalShape
    a sh:NodeShape ;
    sh:targetClass ppv:ValueGoal ;
    rdfs:label "Value Goal Shape" ;
    rdfs:comment "SHACL constraints for ValueGoal notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "value-goal" ) ;
        rdfs:comment "Fixed type identifier for ValueGoal notes."
    ] ;

    # Required: pillar link
    sh:property [
        sh:path ppv:pillar ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:class ppv:Pillar ;
        rdfs:comment "Link to parent Pillar. Required."
    ] ;

    # Required: status
    sh:property [
        sh:path ppv:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Underway"
            "Paused"
            "Waiting"
            "Off Track"
            "Complete"
        ) ;
        rdfs:comment "ValueGoal lifecycle status."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: priority
    sh:property [
        sh:path ppv:priority ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "1st Priority"
            "2nd Priority"
            "3rd Priority"
            "4th Priority"
            "5th Priority"
        ) ;
        rdfs:comment "ValueGoal priority. Optional."
    ] ;

    # Optional: targetDate
    sh:property [
        sh:path ppv:targetDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Target completion date. Optional."
    ] .


# --- Goal Outcome Shape ---

ppv:GoalOutcomeShape
    a sh:NodeShape ;
    sh:targetClass ppv:GoalOutcome ;
    rdfs:label "Goal Outcome Shape" ;
    rdfs:comment "SHACL constraints for GoalOutcome notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "goal-outcome" ) ;
        rdfs:comment "Fixed type identifier for GoalOutcome notes."
    ] ;

    # Required: valueGoal link
    sh:property [
        sh:path ppv:valueGoal ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:class ppv:ValueGoal ;
        rdfs:comment "Link to parent ValueGoal. Required."
    ] ;

    # Required: status
    sh:property [
        sh:path ppv:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Active"
            "Next Up"
            "Future 1"
            "Future 2"
            "Future 3"
            "Completed"
        ) ;
        rdfs:comment "GoalOutcome lifecycle status."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: progress (0-100)
    sh:property [
        sh:path ppv:progress ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
        sh:minInclusive 0 ;
        sh:maxInclusive 100 ;
        rdfs:comment "Completion percentage 0-100. Optional."
    ] ;

    # Optional: targetDate
    sh:property [
        sh:path ppv:targetDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Target completion date. Optional."
    ] ;

    # Optional: completedDate
    sh:property [
        sh:path ppv:completedDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Date when goal outcome was completed. Optional."
    ] .


# --- Project Shape ---

ppv:ProjectShape
    a sh:NodeShape ;
    sh:targetClass ppv:Project ;
    rdfs:label "Project Shape" ;
    rdfs:comment "SHACL constraints for Project notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "project" ) ;
        rdfs:comment "Fixed type identifier for Project notes."
    ] ;

    # Required: status
    sh:property [
        sh:path ppv:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Active"
            "On Hold"
            "Next Up"
            "Future"
            "Someday/Maybe"
            "Completed"
        ) ;
        rdfs:comment "Project lifecycle status."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: goalOutcome link
    sh:property [
        sh:path ppv:goalOutcome ;
        sh:maxCount 1 ;
        sh:class ppv:GoalOutcome ;
        rdfs:comment "Link to parent GoalOutcome. Optional (some projects may be standalone)."
    ] ;

    # Optional: pillar link (denormalized shortcut)
    sh:property [
        sh:path ppv:pillar ;
        sh:maxCount 1 ;
        sh:class ppv:Pillar ;
        rdfs:comment "Direct link to Pillar (denormalized shortcut for dashboard queries). Optional."
    ] ;

    # Optional: priority
    sh:property [
        sh:path ppv:priority ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "1st Priority"
            "2nd Priority"
            "3rd Priority"
            "4th Priority"
            "5th Priority"
        ) ;
        rdfs:comment "Project priority. Optional."
    ] ;

    # Optional: progress (0-100)
    sh:property [
        sh:path ppv:progress ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
        sh:minInclusive 0 ;
        sh:maxInclusive 100 ;
        rdfs:comment "Completion percentage 0-100. Optional."
    ] ;

    # Optional: startDate
    sh:property [
        sh:path ppv:startDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Project start date. Optional."
    ] ;

    # Optional: dueDate
    sh:property [
        sh:path ppv:dueDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Project due date. Optional."
    ] ;

    # Optional: reviewDate
    sh:property [
        sh:path ppv:reviewDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Next scheduled review date. Optional."
    ] ;

    # Optional: completedDate
    sh:property [
        sh:path ppv:completedDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Date when project was completed. Optional."
    ] .


# --- Action Item Shape ---

ppv:ActionItemShape
    a sh:NodeShape ;
    sh:targetClass ppv:ActionItem ;
    rdfs:label "Action Item Shape" ;
    rdfs:comment "SHACL constraints for ActionItem notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "action" ) ;
        rdfs:comment "Fixed type identifier for ActionItem notes."
    ] ;

    # Required: status
    sh:property [
        sh:path ppv:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Active"
            "Waiting"
            "Paused"
            "Next Up"
            "Future 1"
            "Future 2"
            "Future 3"
        ) ;
        rdfs:comment "ActionItem lifecycle status."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: project link
    sh:property [
        sh:path ppv:project ;
        sh:maxCount 1 ;
        sh:class ppv:Project ;
        rdfs:comment "Link to parent Project. Optional (some actions may be standalone)."
    ] ;

    # Optional: pillar link (denormalized shortcut)
    sh:property [
        sh:path ppv:pillar ;
        sh:maxCount 1 ;
        sh:class ppv:Pillar ;
        rdfs:comment "Direct link to Pillar (denormalized shortcut). Optional."
    ] ;

    # Optional: priority (with emojis — UTF-8 encoded directly)
    sh:property [
        sh:path ppv:priority ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "Immediate 🔥"
            "Quick ⚡"
            "Scheduled 📅"
            "1st Priority 🚀"
            "2nd Priority"
            "3rd Priority"
            "4th Priority"
            "5th Priority"
            "Errand 🚘"
            "Remember 💭"
        ) ;
        rdfs:comment "ActionItem priority. Optional. Uses emoji labels matching Notion exactly."
    ] ;

    # Optional: doDate
    sh:property [
        sh:path ppv:doDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Date to do the action (PPV: 'Do Date', not due date). Optional."
    ] ;

    # Optional: done
    sh:property [
        sh:path ppv:done ;
        sh:maxCount 1 ;
        sh:datatype xsd:boolean ;
        rdfs:comment "Completion checkbox. Optional (defaults false)."
    ] ;

    # Optional: completionDate
    sh:property [
        sh:path ppv:completionDate ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Date the action was completed. Optional."
    ] ;

    # Optional: description
    sh:property [
        sh:path ppv:description ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Freeform notes about the action. Optional."
    ] ;

    # Optional: context
    sh:property [
        sh:path ppv:context ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "home"
            "office"
            "errands"
            "calls"
            "computer"
            "anywhere"
        ) ;
        rdfs:comment "Execution context for GTD-style filtering. Optional."
    ] ;

    # Optional: energy
    sh:property [
        sh:path ppv:energy ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in (
            "low"
            "medium"
            "high"
        ) ;
        rdfs:comment "Energy level required. Optional."
    ] ;

    # Optional: timeEstimate
    sh:property [
        sh:path ppv:timeEstimate ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
        rdfs:comment "Time estimate in minutes. Optional."
    ] .


# --- Weekly Review Shape ---

ppv:WeeklyReviewShape
    a sh:NodeShape ;
    sh:targetClass ppv:WeeklyReview ;
    rdfs:label "Weekly Review Shape" ;
    rdfs:comment "SHACL constraints for WeeklyReview notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "weekly-review" ) ;
        rdfs:comment "Fixed type identifier for WeeklyReview notes."
    ] ;

    # Required: cycle = "weekly"
    sh:property [
        sh:path ppv:cycle ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "weekly" ) ;
        rdfs:comment "Fixed cycle value for WeeklyReview."
    ] ;

    # Required: startDate (Monday of review week)
    sh:property [
        sh:path ppv:startDate ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Monday of the review week (start of period for completed actions filter). Required."
    ] ;

    # Required: endDate (Sunday of review week)
    sh:property [
        sh:path ppv:endDate ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "Sunday of the review week (end of period for completed actions filter). Required."
    ] ;

    # Required: month link
    sh:property [
        sh:path ppv:month ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:class ppv:MonthlyReview ;
        rdfs:comment "Link to parent MonthlyReview for monthly rollup queries. Required."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: focusObjective
    sh:property [
        sh:path ppv:focusObjective ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Focus objective for the week. Optional."
    ] .


# --- Monthly Review Shape ---

ppv:MonthlyReviewShape
    a sh:NodeShape ;
    sh:targetClass ppv:MonthlyReview ;
    rdfs:label "Monthly Review Shape" ;
    rdfs:comment "SHACL constraints for MonthlyReview notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "monthly-review" ) ;
        rdfs:comment "Fixed type identifier for MonthlyReview notes."
    ] ;

    # Required: cycle = "monthly"
    sh:property [
        sh:path ppv:cycle ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "monthly" ) ;
        rdfs:comment "Fixed cycle value for MonthlyReview."
    ] ;

    # Required: monthName ("February 2026" format)
    sh:property [
        sh:path ppv:monthName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Month name in 'February 2026' format. Required."
    ] ;

    # Required: year
    sh:property [
        sh:path ppv:year ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Year in '2026' format. Required."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: quarter link
    sh:property [
        sh:path ppv:quarter ;
        sh:maxCount 1 ;
        sh:class ppv:QuarterlyReview ;
        rdfs:comment "Link to parent QuarterlyReview for quarterly rollup. Optional."
    ] ;

    # Optional: gratitude
    sh:property [
        sh:path ppv:gratitude ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Monthly gratitude reflection. Optional."
    ] ;

    # Optional: learnedThisMonth
    sh:property [
        sh:path ppv:learnedThisMonth ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Key learning from the month. Optional."
    ] .


# --- Quarterly Review Shape ---

ppv:QuarterlyReviewShape
    a sh:NodeShape ;
    sh:targetClass ppv:QuarterlyReview ;
    rdfs:label "Quarterly Review Shape" ;
    rdfs:comment "SHACL constraints for QuarterlyReview notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "quarterly-review" ) ;
        rdfs:comment "Fixed type identifier for QuarterlyReview notes."
    ] ;

    # Required: cycle = "quarterly"
    sh:property [
        sh:path ppv:cycle ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "quarterly" ) ;
        rdfs:comment "Fixed cycle value for QuarterlyReview."
    ] ;

    # Required: quarterName ("Q1 2026" format)
    sh:property [
        sh:path ppv:quarterName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Quarter name in 'Q1 2026' format. Required."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: yearLink (link to YearlyReview)
    sh:property [
        sh:path ppv:yearLink ;
        sh:maxCount 1 ;
        sh:class ppv:YearlyReview ;
        rdfs:comment "Link to parent YearlyReview for yearly rollup. Optional."
    ] .


# --- Yearly Review Shape ---

ppv:YearlyReviewShape
    a sh:NodeShape ;
    sh:targetClass ppv:YearlyReview ;
    rdfs:label "Yearly Review Shape" ;
    rdfs:comment "SHACL constraints for YearlyReview notes." ;

    # Required: type
    sh:property [
        sh:path ppv:type ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "yearly-review" ) ;
        rdfs:comment "Fixed type identifier for YearlyReview notes."
    ] ;

    # Required: cycle = "yearly"
    sh:property [
        sh:path ppv:cycle ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:in ( "yearly" ) ;
        rdfs:comment "Fixed cycle value for YearlyReview."
    ] ;

    # Required: yearName ("2026" format)
    sh:property [
        sh:path ppv:yearName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        rdfs:comment "Year in '2026' format. Required."
    ] ;

    # Required: created
    sh:property [
        sh:path ppv:created ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:date ;
        rdfs:comment "ISO creation date. Required."
    ] ;

    # Optional: quarters (list of links to QuarterlyReviews)
    sh:property [
        sh:path ppv:quarters ;
        sh:class ppv:QuarterlyReview ;
        rdfs:comment "Links to constituent QuarterlyReviews (up to 4). No maxCount — multi-value list. Optional."
    ] .

# =============================================================================
# END OF ONTOLOGY
# =============================================================================

# SHACL and OWL Logical Inference for SemPKM Mental Models

**Research Date:** 2026-03-03
**Author:** Claude (research task quick-19)
**Status:** Research complete -- architecture proposal with source links

---

## 1. Executive Summary

SemPKM already ships two of the semantic web's most powerful standards -- SHACL and OWL -- but uses only a fraction of their capabilities. SHACL is limited to form generation (`backend/app/services/shapes.py` extracts `sh:PropertyShape` metadata for Jinja2 templates) and data validation (`backend/app/services/validation.py` calls `pyshacl.validate()`). OWL is limited to class and property declarations in the ontology files (`models/basic-pkm/ontology/basic-pkm.jsonld`). The `owl:inverseOf` axiom linking `bpkm:hasParticipant` and `bpkm:participatesIn` is declared but never materialized -- users must manually maintain both directions of every relationship. No inference engine is configured: the RDF4J repository (`config/rdf4j/sempkm-repo.ttl`) runs a bare `NativeStore` with `LuceneSail`, and pyshacl is called without the `advanced=True` flag that enables SHACL rules.

**Primary recommendation (HIGH confidence):** Add Python-side OWL 2 RL inference via the `owlrl` library to the existing `ValidationService` pipeline, materializing inverse properties and RDFS subclass/subproperty entailments on every write. This is a low-risk, high-value change: `owlrl` operates on rdflib graphs already in the pipeline, requires no triplestore reconfiguration, and immediately delivers bidirectional links, type inheritance, and richer graph visualizations. Follow with SHACL rule support (`pyshacl` `advanced=True`) to let Mental Models declare domain-specific derivation rules alongside their shapes.

**What changes for users:** (1) Automatic bidirectional links -- adding a participant to a Project automatically makes that Person's "participatesIn" list show the Project. (2) Richer graph views -- inference surfaces implicit connections (transitive concept hierarchies, inherited properties) without manual linking. (3) Smarter suggestions -- derived relationships power link recommendation ("this Note is about Concept X, which is broader than Y -- suggest Y as related"). (4) Mental Models become intelligent -- model authors can ship inference rules that derive domain-specific knowledge (a GTD model infers task contexts; a Zettelkasten model computes transitive backlinks).

---

## 2. Current State Audit

### 2.1 How SHACL is used today

**Form generation** (`backend/app/services/shapes.py`): The `ShapesService` fetches SHACL shapes via SPARQL CONSTRUCT from named graphs (`urn:sempkm:model:{id}:shapes`), parses them into an rdflib Graph, and extracts `sh:NodeShape`/`sh:PropertyShape` metadata into Python dataclasses (`NodeShapeForm`, `PropertyShape`, `PropertyGroup`). This metadata drives Jinja2 form templates -- field types, order, groups, cardinality constraints, `sh:in` enumerated values, and default values. The shapes file for basic-pkm (`models/basic-pkm/shapes/basic-pkm.jsonld`) defines four NodeShapes (ProjectShape, PersonShape, NoteShape, ConceptShape) with a total of ~40 property shapes across 12 property groups.

**Validation** (`backend/app/services/validation.py`): The `ValidationService.validate()` method fetches the current state graph via SPARQL CONSTRUCT, loads shapes via a configurable shapes loader, and runs `pyshacl.validate(data_graph, shacl_graph=shapes_graph, allow_infos=True, allow_warnings=True)` in a thread (CPU-bound). Results are parsed into a `ValidationReport` and stored as named graphs. Critically, the call does **not** pass `advanced=True`, `inference=...`, or `ont_graph=...` -- so SHACL rules and OWL inference are both disabled.

### 2.2 How OWL is used today

The ontology file (`models/basic-pkm/ontology/basic-pkm.jsonld`) declares:

| OWL Construct | Example | Count |
|---|---|---|
| `owl:Class` | `bpkm:Project`, `bpkm:Person`, `bpkm:Note`, `bpkm:Concept` | 4 |
| `owl:DatatypeProperty` | `bpkm:status`, `bpkm:priority`, `bpkm:body`, `bpkm:noteType`, `bpkm:tags` | 5 |
| `owl:ObjectProperty` | `bpkm:hasParticipant`, `bpkm:hasNote`, `bpkm:participatesIn`, `bpkm:isAbout`, `bpkm:relatedProject` | 5 |
| `owl:inverseOf` | `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` | 1 |
| `rdfs:domain`/`rdfs:range` | On all 10 properties | 10+10 |

The `owl:inverseOf` axiom between `hasParticipant` and `participatesIn` is the clearest example of declared-but-not-materialized intelligence. When a user creates `ProjectA bpkm:hasParticipant PersonB`, the inverse triple `PersonB bpkm:participatesIn ProjectA` should be automatically inferred -- but no reasoner is configured to do this.

### 2.3 What is NOT happening

1. **No OWL inference:** The RDF4J repo config uses plain `NativeStore` without `SchemaCachingRDFSInferencer` or `ForwardChainingRDFSInferencer`. No reasoner layer is configured.
2. **No SHACL rule execution:** pyshacl is called without `advanced=True`, so `sh:rule` (sh:TripleRule, sh:SPARQLRule) directives are ignored.
3. **No ontology-aware validation:** pyshacl is not given an `ont_graph`, so it cannot use OWL axioms during validation.
4. **No RDFS entailments:** `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:domain`, `rdfs:range` entailments are not computed.
5. **The gap:** Users manually maintain bidirectional relationships that the ontology already describes formally.

---

## 3. SHACL Advanced Features Analysis

### 3.1 SHACL Rules (sh:rule)

SHACL Advanced Features (SHACL-AF) extends the core validation spec with triple generation capabilities. A SHACL rule, attached to a `sh:NodeShape` via `sh:rule`, produces new triples rather than validation results.

**Source:** [W3C SHACL Advanced Features](https://www.w3.org/TR/shacl-af/) (W3C Working Group Note, 8 June 2017)

Two rule types exist:

**sh:TripleRule** -- Declarative triple generation:
```turtle
ex:InverseParticipationRule a sh:TripleRule ;
    sh:subject sh:this ;
    sh:predicate bpkm:participatesIn ;
    sh:object [sh:path [sh:inversePath bpkm:hasParticipant]] ;
    sh:condition [sh:property [sh:path bpkm:hasParticipant ; sh:minCount 1]] .
```
This says: for each node matching the shape's target, generate a triple where the subject is `sh:this`, the predicate is `bpkm:participatesIn`, and the object is found by traversing `sh:inversePath bpkm:hasParticipant`.

**sh:SPARQLRule** -- SPARQL CONSTRUCT-based generation:
```turtle
ex:InverseParticipationSPARQL a sh:SPARQLRule ;
    sh:prefixes bpkm: ;
    sh:construct """
        CONSTRUCT { ?person bpkm:participatesIn $this }
        WHERE { $this bpkm:hasParticipant ?person }
    """ .
```
SPARQLRules are more flexible -- they can reference variables, use FILTER, OPTIONAL, and other SPARQL features.

**Source:** [SHACL-AF Section 4: Rules](https://www.w3.org/TR/shacl-af/#rules) (W3C)

### 3.2 pyshacl's SHACL-AF support

pyshacl (currently `>=0.31.0` in SemPKM's `pyproject.toml`) supports SHACL Advanced Features when called with `advanced=True`:

```python
conforms, results_graph, text = pyshacl.validate(
    data_graph,
    shacl_graph=shapes_graph,
    ont_graph=ontology_graph,  # optional: OWL ontology for inference
    advanced=True,              # enables SHACL-AF rules
    inplace=True,               # modify data_graph directly with inferred triples
    inference='rdfs',           # or 'owlrl' for OWL 2 RL reasoning
)
```

Key pyshacl features relevant to SemPKM:

| Feature | pyshacl Flag | Status |
|---|---|---|
| SHACL-AF Rules (sh:TripleRule, sh:SPARQLRule) | `advanced=True` | Supported since v0.14+ |
| OWL inference during validation | `inference='owlrl'` | Requires `owlrl` package |
| RDFS inference during validation | `inference='rdfs'` | Built-in |
| Ontology graph for OWL axioms | `ont_graph=Graph` | Supported |
| In-place graph modification (materialization) | `inplace=True` | Supported |
| SHACL-SPARQL Constraints | `advanced=True` | Supported |
| SHACL-SPARQL Target Types | `advanced=True` | Supported |
| sh:order on rules (execution ordering) | `advanced=True` | Supported since v0.17+ |

**Source:** [pyshacl README](https://github.com/RDFLib/pySHACL) (GitHub, RDFLib project)
**Source:** [pyshacl SHACL-AF support documentation](https://github.com/RDFLib/pySHACL#advanced-features) (GitHub)

### 3.3 SHACL-SPARQL Constraints

Beyond rules, SHACL-AF provides `sh:SPARQLConstraint` for custom validation logic that goes beyond the core constraint components. For example, validating that a Project's end date is after its start date:

```turtle
ex:DateOrderConstraint a sh:SPARQLConstraint ;
    sh:message "End date must be after start date" ;
    sh:prefixes schema: ;
    sh:select """
        SELECT $this ?start ?end
        WHERE {
            $this schema:startDate ?start ;
                 schema:endDate ?end .
            FILTER (?end < ?start)
        }
    """ .
```

This is more expressive than core SHACL constraints but stays within the SHACL validation paradigm (produces validation results, not new triples).

**Source:** [W3C SHACL-SPARQL](https://www.w3.org/TR/shacl/#sparql-constraints) (W3C Recommendation)

### 3.4 DASH Vocabulary Extensions

The Data Shapes (DASH) vocabulary, developed by TopBraid, extends SHACL with UI-aware metadata for form generation. Relevant DASH properties:

| DASH Property | Purpose | SemPKM Relevance |
|---|---|---|
| `dash:viewer` | Widget type for read-only display | Could specify `dash:MarkdownViewer` for `bpkm:body` |
| `dash:editor` | Widget type for editing | `dash:TextAreaEditor`, `dash:DatePickerEditor`, `dash:AutoCompleteEditor` |
| `dash:singleLine` | Whether text field is single-line | Form layout hints |
| `dash:readOnly` | Mark a property as non-editable | Computed/derived properties |
| `dash:hidden` | Hide a property from UI | System properties (`dcterms:created`) |
| `dash:rootClass` | Root class for class hierarchy browsing | Type picker tree |
| `dash:reifiableBy` | Annotation properties on statements | Provenance metadata |

DASH is particularly interesting for SemPKM because the existing `ShapesService` already extracts UI metadata from shapes -- DASH would formalize and extend this pattern with a community-standard vocabulary rather than custom conventions.

**Source:** [DASH Data Shapes Vocabulary](https://datashapes.org/dash.html) (TopBraid/datashapes.org)
**Source:** [DASH GitHub specification](https://github.com/TopQuadrant/shacl/blob/master/src/main/resources/etc/dash.ttl) (TopQuadrant)

### 3.5 SHACL Rules vs. OWL Inference: Key Differences

| Aspect | SHACL Rules | OWL Inference |
|---|---|---|
| **World assumption** | Closed-world (absence = not true) | Open-world (absence = unknown) |
| **Paradigm** | Forward-chaining rules on shapes | Logical entailment from axioms |
| **Expressiveness** | Arbitrary SPARQL patterns | Limited to OWL profile axioms |
| **Scope** | Per-shape (targeted to node types) | Global (all triples) |
| **Materialization** | Explicit (run rules, get triples) | Depends on reasoner strategy |
| **Debugging** | Traceable (which rule fired) | Less traceable (entailment chain) |
| **SemPKM fit** | Domain-specific derivations per model | Cross-cutting axiom-level entailments |

For SemPKM, the recommended approach is to use **OWL for universal entailments** (inverseOf, subClassOf, domain/range) and **SHACL rules for model-specific derivations** (completion percentages, smart suggestions, transitive closures).

---

## 4. OWL Inference Analysis

### 4.1 OWL 2 Profiles

OWL 2 defines three tractable profiles designed for different use cases:

| Profile | Reasoning Complexity | Use Case | SemPKM Fit |
|---|---|---|---|
| **OWL 2 EL** | Polynomial time | Large ontologies, biomedical | Low (overkill for PKM) |
| **OWL 2 QL** | LogSpace (SPARQL rewriting) | Query answering over large data | Medium (query-time only) |
| **OWL 2 RL** | Polynomial time (rule-based) | Business rules, RDF data | **HIGH** (forward-chaining, materialize) |

**OWL 2 RL** is the best fit for SemPKM because:
1. It supports forward-chaining materialization (new triples stored, fast query)
2. It handles the axioms already in the ontology (`owl:inverseOf`, `rdfs:domain/range`, `rdfs:subClassOf`)
3. The `owlrl` Python library implements it directly on rdflib graphs
4. Performance is linear in the size of the data for typical PKM ontologies (hundreds of axioms, thousands of data triples)

**Source:** [W3C OWL 2 Profiles](https://www.w3.org/TR/owl2-profiles/) (W3C Recommendation, 11 December 2012)
**Source:** [OWL 2 RL reasoning](https://www.w3.org/TR/owl2-profiles/#OWL_2_RL) (W3C -- Section 4.3)

### 4.2 RDF4J Inference Configuration

RDF4J supports inference through layered Sail implementations. The current SemPKM config:

```turtle
# Current: NativeStore + LuceneSail, no inference
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:delegate [
      config:sail.type "openrdf:NativeStore" ;
   ]
]
```

To add RDFS inference, a `SchemaCachingRDFSInferencer` would be inserted between LuceneSail and NativeStore:

```turtle
# With RDFS inference:
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:delegate [
      config:sail.type "openrdf:SchemaCachingRDFSInferencer" ;
      config:delegate [
         config:sail.type "openrdf:NativeStore" ;
      ]
   ]
]
```

**RDF4J inference options:**

| Inferencer | What it does | Overhead |
|---|---|---|
| `ForwardChainingRDFSInferencer` | Materializes all RDFS entailments on write | ~2x write cost, significant for bulk loads |
| `SchemaCachingRDFSInferencer` | Caches schema triples, computes entailments on query | Lower write overhead, higher query cost |
| Custom SPIN/SHACL rules | User-defined rules via SPIN or SHACL-AF | Depends on rule complexity |

**Important:** RDF4J's built-in inferencers handle RDFS (subClassOf, subPropertyOf, domain, range) but **not OWL constructs** like `owl:inverseOf`. For OWL-level inference in RDF4J, you need either:
- The commercial GraphDB edition (built on RDF4J with OWL 2 RL reasoner)
- Custom SPIN rules that replicate OWL semantics
- External reasoning (Python-side with `owlrl`)

**Source:** [RDF4J RDFS Inference](https://rdf4j.org/documentation/programming/rdfs-reasoning/) (Eclipse RDF4J docs)
**Source:** [RDF4J Sail Architecture](https://rdf4j.org/documentation/programming/sail/) (Eclipse RDF4J docs)
**Source:** [RDF4J Repository Configuration](https://rdf4j.org/documentation/tools/repository-configuration/) (Eclipse RDF4J docs)

### 4.3 Python-side inference with owlrl

The `owlrl` library implements OWL 2 RL and RDFS reasoning entirely in Python on rdflib graphs. This is the recommended approach for SemPKM because:

1. **No triplestore reconfiguration** -- works on rdflib graphs already in the validation pipeline
2. **OWL 2 RL support** -- handles `owl:inverseOf`, `owl:TransitiveProperty`, `owl:SymmetricProperty`, `owl:sameAs`, `rdfs:subClassOf` entailments
3. **Composable** -- can run before or after pyshacl validation
4. **Small footprint** -- pure Python, no native dependencies
5. **Already compatible** -- pyshacl can invoke owlrl internally via `inference='owlrl'`

Usage:

```python
import owlrl

# Standalone usage
g = rdflib.Graph()
g.parse("data.ttl")
g.parse("ontology.ttl")
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
# g now contains all OWL 2 RL entailments

# Via pyshacl (integrated)
conforms, results, text = pyshacl.validate(
    data_graph, shacl_graph=shapes,
    ont_graph=ontology,
    inference='owlrl',  # runs owlrl before validation
    advanced=True,
    inplace=True,
)
# data_graph now has inferred triples + validation results
```

**What owlrl materializes from the existing basic-pkm ontology:**

| Axiom in Ontology | Entailment | Example |
|---|---|---|
| `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` | `?person bpkm:participatesIn ?project` from `?project bpkm:hasParticipant ?person` | Auto bidirectional links |
| `bpkm:hasParticipant rdfs:domain bpkm:Project` | `?x rdf:type bpkm:Project` from `?x bpkm:hasParticipant ?y` | Type assertion from property usage |
| `bpkm:hasParticipant rdfs:range bpkm:Person` | `?y rdf:type bpkm:Person` from `?x bpkm:hasParticipant ?y` | Type assertion from property usage |
| `bpkm:isAbout rdfs:range bpkm:Concept` | `?c rdf:type bpkm:Concept` from `?note bpkm:isAbout ?c` | Auto-type inference |

**Source:** [owlrl on PyPI](https://pypi.org/project/owlrl/) (Python Package Index)
**Source:** [owlrl GitHub](https://github.com/RDFLib/OWL-RL) (RDFLib project)
**Source:** [pyshacl inference parameter](https://github.com/RDFLib/pySHACL#command-line-use) (GitHub)

### 4.4 What additional axioms would be valuable

The basic-pkm ontology could be enriched with:

| Proposed Axiom | OWL Construct | Benefit |
|---|---|---|
| `bpkm:hasNote owl:inverseOf bpkm:noteOf` (new property) | `owl:inverseOf` | Notes automatically know their parent Project |
| `skos:broader owl:TransitiveProperty` | `owl:TransitiveProperty` | Concept hierarchy traversal: "ancestors of X" without recursive SPARQL |
| `skos:broader owl:inverseOf skos:narrower` | `owl:inverseOf` | Automatic narrower from broader assertions |
| `skos:related owl:SymmetricProperty` | `owl:SymmetricProperty` | Bidirectional concept relationships |
| `bpkm:Project owl:disjointWith bpkm:Person` | `owl:disjointWith` | Catch classification errors |
| `bpkm:isAbout owl:inverseOf bpkm:topicOf` (new) | `owl:inverseOf` | Concepts automatically list their Notes |

Note: `skos:broader` and `skos:narrower` already have `owl:inverseOf` defined in the SKOS specification itself ([SKOS Reference, Section 8.6.1](https://www.w3.org/TR/skos-reference/#semantic-relations)). If the SKOS ontology is loaded alongside the basic-pkm ontology, owlrl would automatically materialize narrower from broader assertions.

---

## 5. Combined Architecture: SHACL Rules + OWL Inference

### 5.1 Proposed Inference Pipeline

The recommended pipeline integrates inference into the existing write path:

```
User saves object
       |
       v
[1. Build data graph] -- current object triples
       |
       v
[2. Load ontology graph] -- all installed model ontologies
       |
       v
[3. OWL 2 RL inference] -- owlrl.DeductiveClosure on merged graph
       |                    Materializes: inverses, domain/range types,
       |                    transitive closures, symmetric properties
       v
[4. SHACL validation + rules] -- pyshacl.validate(advanced=True, inplace=True)
       |                          Validates constraints AND executes sh:rule directives
       |                          Model-contributed rules fire here
       v
[5. Extract new triples] -- diff inferred graph against original
       |
       v
[6. Store to triplestore] -- INSERT original + inferred triples
       |
       v
[7. Store validation report] -- existing ValidationService._store_report()
```

### 5.2 Where to run inference

| Approach | Pros | Cons | SemPKM Recommendation |
|---|---|---|---|
| **Python-side (owlrl + pyshacl)** | No triplestore reconfig; full OWL 2 RL; composable; model-portable | CPU cost on Python side; must pass full graph | **Phase A** (start here) |
| **RDF4J inference layer** | Query-time reasoning; no Python overhead; scales better | RDFS only (no OWL); requires repo recreation; config complexity | **Phase D** (future) |
| **Hybrid** | Best of both: OWL in Python, RDFS in triplestore | Two inference engines to maintain | **Phase C** (after validation) |

**Recommendation:** Start with Python-side inference (Phase A). At PKM scale (thousands of triples, not millions), the CPU cost of owlrl on an rdflib graph is negligible (<100ms for typical operations). This avoids any triplestore migration and keeps the inference logic portable across Mental Models.

### 5.3 Integration with existing ValidationService

The existing `ValidationService.validate()` method in `backend/app/services/validation.py` is the natural integration point. The current call:

```python
# Current (line 95-101 of validation.py)
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    allow_infos=True,
    allow_warnings=True,
)
```

Would become:

```python
# Proposed: with inference enabled
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    ont_graph=ontology_graph,      # NEW: pass ontology for OWL axioms
    inference='owlrl',             # NEW: run OWL 2 RL before validation
    advanced=True,                 # NEW: enable SHACL-AF rules
    inplace=True,                  # NEW: materialize inferred triples into data_graph
    allow_infos=True,
    allow_warnings=True,
)
# After this call, data_graph contains original + inferred triples
# Extract inferred triples: data_graph - original_graph
```

This requires:
1. An ontology loader (similar to the existing shapes loader) to fetch merged ontology graphs
2. The `owlrl` package added to `pyproject.toml` dependencies
3. A mechanism to extract and store only the newly-inferred triples

---

## 6. Practical Applications in SemPKM

### 6.1 Inverse Property Materialization

**What it does:** Automatically creates bidirectional links when one direction is asserted.

**Example in basic-pkm:** User adds `ProjectA bpkm:hasParticipant PersonB`. Inference materializes `PersonB bpkm:participatesIn ProjectA`. PersonB's detail page now shows ProjectA in the "Participates In" section without any additional user action.

**Implementation sketch:**
```python
# In ValidationService or a new InferenceService
from owlrl import DeductiveClosure, OWLRL_Semantics

async def infer_and_validate(self, data_graph, shapes_graph, ontology_graph):
    merged = data_graph + ontology_graph  # rdflib graph union
    DeductiveClosure(OWLRL_Semantics).expand(merged)
    # merged now contains inverse triples
    new_triples = merged - data_graph - ontology_graph
    return new_triples
```

**Already declared in ontology:** `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` -- this would work immediately with owlrl.

**Impact on existing UI:** The `PersonShape` already declares `sh:path bpkm:participatesIn` with `sh:class bpkm:Project` (line 234-239 of `models/basic-pkm/shapes/basic-pkm.jsonld`). The form already renders a "Projects" field for Person objects. Materialized inverse triples would populate this field automatically.

### 6.2 Transitive Concept Hierarchies

**What it does:** Computes the full ancestry chain for concepts linked by `skos:broader`.

**Example in basic-pkm:** If `MachineLearning skos:broader ArtificialIntelligence` and `ArtificialIntelligence skos:broader ComputerScience`, then inference produces `MachineLearning skos:broader ComputerScience` (transitive closure).

**Implementation sketch:** Declare `skos:broader` as `owl:TransitiveProperty` in the ontology:
```json
{
  "@id": "skos:broader",
  "@type": ["owl:ObjectProperty", "owl:TransitiveProperty"]
}
```
owlrl automatically computes transitive closure.

**Impact on graph view:** The graph visualization (`bpkm:view-concept-graph`) would show not just direct broader/narrower edges but the full hierarchy tree, enabling "zoom out to see the big picture" exploration. The SPARQL CONSTRUCT queries in ViewSpecs would automatically pick up transitive triples from the store.

**Source:** [SKOS Reference -- Transitive Hierarchical Relations](https://www.w3.org/TR/skos-reference/#L2422) (W3C)

### 6.3 Derived Property Computation

**What it does:** Computes new property values from existing data using SHACL rules.

**Example in basic-pkm:** A SHACL rule could derive a "project completion percentage" from the statuses of related Notes:

```turtle
bpkm:ProjectShape sh:rule [
    a sh:SPARQLRule ;
    sh:prefixes bpkm: , dcterms: ;
    sh:construct """
        CONSTRUCT { $this bpkm:completionPct ?pct }
        WHERE {
            { SELECT $this (COUNT(?done) AS ?doneCount) (COUNT(?note) AS ?totalCount)
              WHERE {
                  $this bpkm:hasNote ?note .
                  OPTIONAL { ?note bpkm:noteType "reference" . BIND(?note AS ?done) }
              }
              GROUP BY $this }
            BIND(IF(?totalCount > 0, ?doneCount * 100 / ?totalCount, 0) AS ?pct)
        }
    """ ;
] .
```

**Implementation:** Add SHACL rules to the shapes file. When `pyshacl.validate(advanced=True, inplace=True)` runs, the rule fires and adds `bpkm:completionPct` triples to the data graph.

### 6.4 Smart Relationship Suggestions

**What it does:** Uses inferred relationships to suggest new links to the user.

**Example in basic-pkm:** A Note `isAbout` Concept "Machine Learning". If "Machine Learning" `skos:broader` "Artificial Intelligence", the system could suggest linking the Note to "Artificial Intelligence" as well (or to other Notes that are about "Artificial Intelligence").

**Implementation sketch:** A SPARQL query (not inference per se, but inference-enabled):
```sparql
SELECT ?suggestedConcept ?label WHERE {
    ?note bpkm:isAbout ?concept .
    ?concept skos:broader+ ?suggestedConcept .  # Uses materialized transitive triples
    ?suggestedConcept skos:prefLabel ?label .
    FILTER NOT EXISTS { ?note bpkm:isAbout ?suggestedConcept }
}
```

With materialized transitive closure from owlrl, this query becomes a simple pattern match instead of requiring property path traversal (`skos:broader+`) at query time.

### 6.5 Consistency Checking

**What it does:** Uses OWL disjointness and cardinality axioms to detect logical inconsistencies.

**Example:** If `bpkm:Project owl:disjointWith bpkm:Person`, then asserting `?x rdf:type bpkm:Project ; rdf:type bpkm:Person` would be detected as inconsistent. This catches classification errors early.

**Implementation:** owlrl computes `owl:Nothing` membership for entities violating disjointness. A post-inference check can detect these:
```python
from rdflib import OWL
nothing_instances = list(g.subjects(RDF.type, OWL.Nothing))
if nothing_instances:
    raise ConsistencyError(f"Inconsistent entities: {nothing_instances}")
```

**Source:** [OWL 2 RL rules for disjointness](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs) (W3C -- Table 9)

### 6.6 Shape-driven Query Generation

**What it does:** Auto-generates SPARQL queries from SHACL shape definitions, replacing hand-written ViewSpec queries.

**Example:** The `ProjectShape` declares properties (`dcterms:title`, `bpkm:status`, `bpkm:priority`, etc.) with their `sh:path`, `sh:datatype`/`sh:class`, and `sh:order`. A query generator could produce:

```sparql
-- Auto-generated from ProjectShape
SELECT ?s ?title ?status ?priority ?startDate WHERE {
    ?s a bpkm:Project ;
       dcterms:title ?title .
    OPTIONAL { ?s bpkm:status ?status }
    OPTIONAL { ?s bpkm:priority ?priority }
    OPTIONAL { ?s schema:startDate ?startDate }
}
ORDER BY ?title
```

This is essentially what `bpkm:view-project-table` in `models/basic-pkm/views/basic-pkm.jsonld` already contains -- but written by hand. Shape-driven generation would:
1. Eliminate query duplication (shapes already declare the same property paths)
2. Keep queries in sync when shapes change
3. Reduce the model author's burden (contribute shapes, get views for free)

**Implementation:** Extend `ShapesService` with a `generate_sparql_for_shape(shape: NodeShapeForm) -> str` method that iterates over `properties`, maps `sh:datatype` to SELECT variables and `sh:class` to OPTIONAL joins. The existing `ViewSpec` system would support a `sempkm:rendererType "auto"` that delegates to shape-driven generation.

**Source:** [Generating SPARQL from SHACL](https://w3id.org/schimatos/spec) (Schimatos project -- academic research on SHACL-to-SPARQL transformation)

---

## 7. Mental Model Intelligence

### 7.1 Models as inference-aware packages

Currently, a Mental Model bundle (as defined in `manifest.yaml`) contains:
- `ontology/` -- OWL class and property declarations
- `shapes/` -- SHACL shapes for validation and form generation
- `views/` -- ViewSpec instances (SPARQL queries + renderer types)
- `seed/` -- Example data

With inference support, models could additionally contain:
- `rules/` -- SHACL rule files (sh:TripleRule, sh:SPARQLRule) that derive domain-specific knowledge

### 7.2 Manifest extension

```yaml
# Proposed manifest.yaml extension
entrypoints:
  ontology: "ontology/basic-pkm.jsonld"
  shapes: "shapes/basic-pkm.jsonld"
  views: "views/basic-pkm.jsonld"
  seed: "seed/basic-pkm.jsonld"
  rules: "rules/basic-pkm.jsonld"   # NEW: inference rules
```

The `rules` entrypoint would point to a JSON-LD file containing SHACL rules (sh:rule directives attached to NodeShapes or standalone RuleShapes). These rules would be loaded alongside shapes and passed to pyshacl with `advanced=True`.

The `ManifestSchema` in `backend/app/models/manifest.py` would need an optional `rules` field in the `entrypoints` section. The `ModelInstallService` would load rules into a named graph (`urn:sempkm:model:{id}:rules`) and the inference pipeline would merge them with shapes.

### 7.3 Example: GTD Mental Model

A "Getting Things Done" model could declare inference rules:

```json
{
    "@id": "gtd:TaskContextRule",
    "@type": "sh:SPARQLRule",
    "sh:prefixes": {"gtd": "urn:sempkm:model:gtd:"},
    "sh:construct": "CONSTRUCT { $this gtd:inferredContext ?context } WHERE { $this gtd:relatedProject ?project . ?project gtd:context ?context . FILTER NOT EXISTS { $this gtd:context ?any } }"
}
```

This rule says: if a Task is related to a Project that has a context (e.g., "@computer", "@phone"), and the Task does not have its own context, infer the Project's context onto the Task.

### 7.4 Example: Zettelkasten Mental Model

A Zettelkasten model with transitive linking:

```json
{
    "@id": "zk:TransitiveLinkRule",
    "@type": "sh:SPARQLRule",
    "sh:construct": "CONSTRUCT { $this zk:transitivelyLinkedTo ?far } WHERE { $this zk:linkedTo ?near . ?near zk:linkedTo ?far . FILTER(?far != $this) }"
}
```

This computes 2-hop link neighborhoods, enabling "notes linked to notes you linked to" discovery.

### 7.5 Trust boundary

Model-contributed rules execute inside pyshacl's SHACL-AF engine, which constrains them to:
- SHACL Triple Rules (declarative, no side effects)
- SPARQL CONSTRUCT queries (read-only graph patterns producing new triples)

Neither mechanism can execute arbitrary Python code, access the filesystem, or make network requests. The trust boundary is:

| Capability | Allowed | Mechanism |
|---|---|---|
| Read triples from the data graph | Yes | SPARQL WHERE patterns |
| Generate new triples | Yes | CONSTRUCT / sh:TripleRule |
| Modify existing triples | No | SHACL rules are additive only |
| Delete triples | No | No DELETE support in SHACL-AF |
| Execute Python code | No | pyshacl sandboxes rule execution |
| Access filesystem | No | SPARQL operates on in-memory graph |
| Make HTTP requests | No | No SERVICE clause support in pyshacl rules |

This makes model-contributed rules safe to execute without additional sandboxing. The worst a malicious rule could do is generate excessive triples (a denial-of-service via graph bloat), which can be mitigated by setting a maximum triple count threshold.

**Source:** [SHACL-AF Security Considerations](https://www.w3.org/TR/shacl-af/#security-considerations) (W3C)
**Source:** [pyshacl execution model](https://github.com/RDFLib/pySHACL/blob/master/pyshacl/rules/__init__.py) (GitHub source)

---

## 8. Implementation Roadmap

### Phase A: OWL 2 RL inference in ValidationService (LOW risk, HIGH value)

**Scope:** Add `owlrl` to dependencies, pass `ont_graph` and `inference='owlrl'` to pyshacl, materialize inferred triples on write.

**Changes:**
1. Add `owlrl>=6.0.2` to `backend/pyproject.toml`
2. Add an ontology loader to `ValidationService` (fetch from `urn:sempkm:model:{id}:ontology` named graphs, parallel to existing shapes loader)
3. Update `pyshacl.validate()` call with `ont_graph=ontology_graph`, `inference='owlrl'`, `inplace=True`
4. After validation, extract inferred triples (diff original vs. expanded graph) and store them
5. Store inferred triples in a separate named graph (`urn:sempkm:inferred`) for easy identification and re-computation

**Immediate benefits:**
- `bpkm:participatesIn` auto-materialized from `bpkm:hasParticipant` (existing `owl:inverseOf`)
- `rdfs:domain`/`rdfs:range` type assertions (implicit `rdf:type` from property usage)
- Person detail pages show linked Projects without manual inverse entry

**Estimated effort:** 1-2 plan tasks. Docker rebuild needed for new dependency.

**Risk:** Low. owlrl is a well-maintained RDFLib project (same org as pyshacl). The change is additive -- existing validation behavior is preserved.

### Phase B: SHACL rule support (MEDIUM risk, MEDIUM value)

**Scope:** Enable `advanced=True` in pyshacl, add `rules` entrypoint to manifest, allow models to contribute SHACL rules.

**Changes:**
1. Update `pyshacl.validate()` call with `advanced=True`
2. Add optional `rules` field to `ManifestSchema` entrypoints
3. Update `ModelInstallService` to load rules into `urn:sempkm:model:{id}:rules` named graph
4. Merge rules graph with shapes graph before passing to pyshacl
5. Add example SHACL rules to basic-pkm model (e.g., derive `bpkm:noteOf` inverse, compute concept ancestry)

**Benefits:**
- Models can contribute domain-specific inference logic
- Derived properties appear in views and forms
- Foundation for "intelligent" Mental Models

**Risk:** Medium. SHACL rules add complexity for model authors. Need documentation and examples. Rules could generate unexpected triples if poorly written.

### Phase C: DASH vocabulary and shape-driven queries (MEDIUM risk, HIGH value)

**Scope:** Adopt DASH vocabulary for richer UI metadata, implement shape-driven SPARQL generation.

**Changes:**
1. Add DASH vocabulary imports to shapes files
2. Extend `ShapesService._extract_property_shape()` to read DASH properties (`dash:viewer`, `dash:editor`, `dash:readOnly`, `dash:hidden`)
3. Add `PropertyShape.viewer`, `PropertyShape.editor`, `PropertyShape.readonly`, `PropertyShape.hidden` fields
4. Implement `ShapesService.generate_sparql()` to produce SELECT/CONSTRUCT queries from shape properties
5. Add `sempkm:rendererType "auto"` support to ViewSpecService

**Benefits:**
- Richer form generation (date pickers, markdown editors, autocomplete)
- Reduced manual query authoring for model developers
- Shapes become the single source of truth for both UI and queries

**Risk:** Medium. DASH is a community vocabulary, not a W3C standard. Need to evaluate which DASH properties are stable.

### Phase D: RDF4J inference layer (FUTURE, HIGH complexity)

**Scope:** Add `SchemaCachingRDFSInferencer` to RDF4J config for query-time RDFS inference, reducing Python-side inference load.

**Changes:**
1. Update `config/rdf4j/sempkm-repo.ttl` to insert inferencer between LuceneSail and NativeStore
2. Re-create the RDF4J repository (requires data migration or volume reset)
3. Adjust Python-side inference to avoid duplicating RDFS entailments already handled by RDF4J
4. Keep OWL 2 RL inference in Python (RDF4J Community Edition does not support OWL)

**Benefits:**
- Query-time inference for RDFS (subClassOf, subPropertyOf) without materialization
- Reduced write-time overhead for RDFS-level entailments
- Better scaling for larger knowledge bases

**Risk:** High. Requires triplestore migration, careful layering to avoid duplicate inference, and thorough testing of named graph behavior with inference enabled. The LuceneSail + Inferencer interaction needs validation.

---

## 9. Risks and Tradeoffs

### 9.1 Materialization Bloat

Adding inferred triples increases the total triple count. For a typical PKM with 5,000 user-asserted triples:

| Inference Level | Estimated Additional Triples | Total | Overhead |
|---|---|---|---|
| `owl:inverseOf` only | ~500 (10% of object property assertions) | 5,500 | +10% |
| Full OWL 2 RL | ~2,000 (domain/range types, inverses, transitivity) | 7,000 | +40% |
| OWL 2 RL + SHACL rules | ~3,000 (above + derived properties) | 8,000 | +60% |

At PKM scale this is negligible -- RDF4J NativeStore handles millions of triples. The LuceneSail FTS index will grow proportionally, but the inferred triples are mostly structural (type assertions, inverse links) not natural-language content, so FTS impact is minimal.

**Mitigation:** Store inferred triples in a separate named graph (`urn:sempkm:inferred`). On ontology change or rule update, drop and recompute. Use `GRAPH` clauses in SPARQL to distinguish asserted vs. inferred when needed.

### 9.2 Rule Debugging (Provenance)

When inference adds triples, users may wonder "why does this relationship exist?" Without provenance tracking, debugging is difficult.

**Mitigation strategies:**
1. **Named graph separation:** Inferred triples in `urn:sempkm:inferred` are clearly machine-generated
2. **Inference metadata:** For each inference run, store a provenance record: timestamp, which rules fired, how many triples generated
3. **UI indicator:** In the object detail view, mark inferred properties with a small icon (e.g., a chain-link or sparkle) to distinguish them from user-asserted properties
4. **Re-inference command:** Provide a "recompute inferences" action that drops and regenerates all inferred triples

### 9.3 Model Author Complexity

Writing OWL axioms and SHACL rules is harder than writing SHACL shapes for forms. The learning curve could deter model contributors.

**Mitigation:**
1. **Inference is optional:** Models work without rules (current behavior). Rules are an enhancement, not a requirement.
2. **Templates and examples:** Provide rule templates for common patterns (inverse materialization, transitive closure, derived counts)
3. **Rule validation:** pyshacl validates rule syntax before execution. Malformed rules produce clear error messages.
4. **Documentation:** Ship a "Model Author's Guide to Inference Rules" with the SHACL rules specification

### 9.4 Backward Compatibility

When inference rules change (model update), existing inferred triples may be stale or incorrect.

**Mitigation:**
1. **Re-inference on model install/update:** Drop `urn:sempkm:inferred` and recompute from scratch
2. **Versioned inference graphs:** `urn:sempkm:inferred:{model-id}:{version}` for rollback capability
3. **Incremental inference:** For per-object writes, only recompute inference for the affected object's neighborhood (optimization for Phase D)

### 9.5 Performance Considerations

| Operation | Current Cost | With OWL 2 RL | With OWL 2 RL + SHACL Rules |
|---|---|---|---|
| Single object save | ~50ms (SPARQL INSERT) | ~150ms (+owlrl on object graph) | ~200ms (+rule execution) |
| Full validation | ~200ms (pyshacl on full graph) | ~500ms (+owlrl on full graph) | ~700ms (+rules on full graph) |
| Bulk import (100 objects) | ~5s | ~15s | ~20s |

These are estimates for PKM-scale data (5,000-10,000 triples). The overhead is acceptable for a single-user application where saves are interactive (user clicks "save" and waits <1 second).

**Optimization path:** If performance becomes an issue:
1. Run inference per-object (not full graph) -- infer only the neighborhood of the changed object
2. Cache ontology and rules graphs (reload on model install/update only)
3. Move RDFS inference to RDF4J (Phase D) and keep only OWL in Python

---

## 10. Source Links

### W3C Specifications
- [SHACL Core](https://www.w3.org/TR/shacl/) -- W3C Recommendation, 20 July 2017
- [SHACL Advanced Features (SHACL-AF)](https://www.w3.org/TR/shacl-af/) -- W3C Working Group Note, 8 June 2017
- [SHACL-SPARQL](https://www.w3.org/TR/shacl/#sparql-constraints) -- Section 6 of the SHACL Core spec
- [OWL 2 Web Ontology Language Profiles](https://www.w3.org/TR/owl2-profiles/) -- W3C Recommendation, 11 December 2012
- [OWL 2 RL reasoning rules](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs) -- Table 4-9 of OWL 2 Profiles
- [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/) -- W3C Recommendation, 18 August 2009
- [SKOS Semantic Relations](https://www.w3.org/TR/skos-reference/#semantic-relations) -- Section 8 (broader/narrower/related semantics)

### Python Libraries
- [pyshacl on GitHub](https://github.com/RDFLib/pySHACL) -- RDFLib project, SHACL validation + SHACL-AF rules
- [pyshacl on PyPI](https://pypi.org/project/pyshacl/) -- Version history and changelog
- [pyshacl Advanced Features documentation](https://github.com/RDFLib/pySHACL#advanced-features) -- advanced=True, inference, ont_graph
- [owlrl on GitHub](https://github.com/RDFLib/OWL-RL) -- RDFLib project, OWL 2 RL + RDFS reasoning
- [owlrl on PyPI](https://pypi.org/project/owlrl/) -- Version 6.0.2+
- [rdflib documentation](https://rdflib.readthedocs.io/) -- Core RDF library for Python

### RDF4J / Triplestore
- [RDF4J RDFS Reasoning](https://rdf4j.org/documentation/programming/rdfs-reasoning/) -- Eclipse Foundation docs
- [RDF4J Sail Architecture](https://rdf4j.org/documentation/programming/sail/) -- Layered sail implementations
- [RDF4J Repository Configuration](https://rdf4j.org/documentation/tools/repository-configuration/) -- TTL config for inferencers
- [RDF4J SchemaCachingRDFSInferencer](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/inferencer/fc/SchemaCachingRDFSInferencer.html) -- JavaDoc

### DASH and Extended SHACL
- [DASH Data Shapes Vocabulary](https://datashapes.org/dash.html) -- datashapes.org (TopBraid)
- [DASH specification on GitHub](https://github.com/TopQuadrant/shacl/blob/master/src/main/resources/etc/dash.ttl) -- TopQuadrant
- [TopBraid SHACL API](https://www.topquadrant.com/technology/shacl/) -- TopQuadrant commercial product (patterns are informative)

### Academic / Community
- [Schimatos: SHACL-to-SPARQL transformation](https://w3id.org/schimatos/spec) -- Academic research on generating SPARQL from SHACL shapes
- [SHACL Playground](https://shacl-playground.zazuko.com/) -- Interactive SHACL validation testing (Zazuko)
- [Validating and Describing Linked Data](https://book.validatingrdf.com/) -- Book by Jose Emilio Labra Gayo et al. (comprehensive SHACL + ShEx reference)

### SemPKM Source Files Referenced
- `backend/app/services/shapes.py` -- ShapesService: SHACL shape extraction for form metadata
- `backend/app/services/validation.py` -- ValidationService: pyshacl validation orchestration
- `models/basic-pkm/ontology/basic-pkm.jsonld` -- OWL ontology with inverseOf, domain/range
- `models/basic-pkm/shapes/basic-pkm.jsonld` -- SHACL NodeShapes for 4 types, ~40 property shapes
- `models/basic-pkm/views/basic-pkm.jsonld` -- ViewSpec instances with hand-written SPARQL
- `models/basic-pkm/manifest.yaml` -- Model manifest with entrypoints (no rules entrypoint yet)
- `config/rdf4j/sempkm-repo.ttl` -- RDF4J repo config: NativeStore + LuceneSail, no inferencer
- `backend/pyproject.toml` -- Dependencies: rdflib>=7.5.0, pyshacl>=0.31.0 (no owlrl yet)

# SemPKM Spatial RDF Canvas — Project-Specific Implementation Plan

## Why this plan is different from the generic PRD plan
The PRD/implementation draft assumes a greenfield React app with canvas-specific APIs. SemPKM today is:
- FastAPI + Jinja templates + htmx shell (no frontend build pipeline in main app).
- Cytoscape-based graph view already present under `/browser/views/graph/*`.
- Server-rendered workspace tabs managed by Dockview, where each view is loaded via htmx into an editor panel.

This plan integrates the canvas incrementally into that architecture so we can ship value without destabilizing the existing graph/browser flows.

---

## 1) Current-codebase fit analysis (concrete integration points)

### Frontend shell and navigation
- Workspace view tabs are opened by `frontend/static/js/workspace.js` and route through `/browser/views/{renderer}/{spec}`.
- Graph view currently renders via template + Cytoscape boot code (`frontend/static/js/graph.js`).
- Base scripts are CDN/static JS loaded from `backend/app/templates/base.html`.

### Backend services we can leverage
- View loading and graph data access already live in `backend/app/views/router.py` + `backend/app/views/service.py`.
- User-scoped settings persistence exists (`/browser/settings/*`) backed by `user_settings` rows via `SettingsService`.
- Event-sourced writes already exist via command dispatch (`/api/commands`), which can later support “agent writes” provenance hooks.

### Implication
We should ship canvas as a new **view renderer type** in the existing workspace flow first, not a separate SPA.

---

## 2) Proposed architecture for SemPKM

## 2.1 Rendering model
- Keep HTMX shell as-is.
- Add a **React Flow island** inside a new template (`browser/canvas_view.html`) mounted to a single DOM root.
- Keep inspector/details on the server side initially (existing right pane + htmx partials), avoiding duplicate state systems.

## 2.2 Frontend packaging decision
Because the app currently has no JS build step, we should choose one of these two tracks before coding:

### Track A (recommended): checked-in bundled asset
- Build a small Vite bundle in a `frontend/canvas-ui/` workspace.
- Commit built artifacts to `frontend/static/js/canvas/`.
- Load with normal `<script src="/js/canvas/main.js">` from template.
- Pros: modern React Flow DX, predictable runtime, no CDN module complexity.
- Cons: introduces build workflow for contributors.

### Track B: CDN ESM only
- Attempt no-build React/ReactDOM/ReactFlow via ESM CDNs.
- Pros: no local build tooling.
- Cons: brittle imports/version pinning/caching/debuggability; higher long-term risk.

Recommendation: **Track A** for maintainability.

## 2.3 Data and persistence model
- Internal saved canvas format = React Flow `toObject()` + SemPKM metadata in `node.data` / `edge.data`.
- Store per-user canvases using `user_settings` first (keyed under `canvas.{canvas_id}`) to avoid introducing a new DB table in MVP.
- If size/scale becomes an issue, migrate to dedicated SQL table (`canvas_documents`) in Beta.

## 2.4 RDF graph source
- Reuse existing graph service primitives where possible.
- Add focused canvas endpoints for predictable payload shape:
  - `GET /api/canvas/{id}`
  - `PUT /api/canvas/{id}`
  - `GET /api/canvas/subgraph?root_uri=&depth=&predicates=`
- Keep query scoping rules consistent with existing current-graph semantics.

---

## 3) Phased implementation plan (SemPKM-specific)

## Phase C0 — Decision gate + thin vertical slice (2–3 days)
**Goal:** de-risk packaging and mount strategy.

Tasks:
1. Finalize Track A vs B packaging.
2. Add a minimal `/browser/views/canvas/{spec_iri}` route and template shell.
3. Mount a hard-coded React Flow graph in workspace tab.
4. Ensure no regression to existing table/card/graph renderers.

Deliverable: canvas tab opens in Dockview and supports pan/zoom with hardcoded nodes.

---

## Phase C1 — Backend canvas document API (3–4 days)
**Goal:** save/restore canvas state using existing auth + user setting infrastructure.

Tasks:
1. Add `backend/app/canvas/router.py` with read/write endpoints.
2. Add lightweight schemas for flow document validation.
3. Implement storage adapter backed by `SettingsService` key namespace:
   - `canvas.{id}.document`
   - `canvas.{id}.meta`
4. Add optimistic concurrency field (`updated_at` or revision token) to avoid accidental overwrite.

Deliverable: exact restore of nodes/edges/viewport after refresh.

---

## Phase C2 — Integrate RDF subgraph loading (4–5 days)
**Goal:** load real resource nodes + RDF edges into canvas.

Tasks:
1. Add subgraph endpoint reusing ViewSpecService/SPARQL helper patterns.
2. Transform response to React Flow node/edge contracts with stable IDs.
3. Add “add node by URI” action in canvas panel UI.
4. Add edge metadata payload for right-pane inspection (predicate IRI, labels).

Deliverable: users can place resources and see RDF edges among present nodes.

---

## Phase C3 — Markdown expansion + link-anchor edges (5–7 days)
**Goal:** make nodes semantically rich and spatially anchored.

Tasks:
1. Reuse markdown rendering conventions from existing `markdown-render.js` behavior where possible (sanitization/link policies).
2. Implement node expand/collapse with markdown preview.
3. Parse rendered links and compute dynamic anchor handles.
4. Trigger `updateNodeInternals(nodeId)` whenever anchors change.
5. Create markdown-link edges to existing target nodes; prompt to add missing targets.

Deliverable: expanded nodes show anchor dots and edges originate from link-aligned handles.

---

## Phase C4 — Agent write streaming MVP (4–6 days)
**Goal:** live node updates while file/resource content changes.

Tasks:
1. Add SSE endpoint under existing API conventions (or bridge to existing event stream if available).
2. Implement `useAgentStream` client hook with reconnect/backoff.
3. Update node markdown incrementally (v1 full-text replace acceptable).
4. Recompute anchors after each update.
5. Badge state: writing / updated / error.

Deliverable: demo where node content visibly updates in real time without page refresh.

---

## Phase C5 — JSON Canvas import/export + perf guardrails (4–5 days)
**Goal:** interoperability and stability at moderate graph size.

Tasks:
1. Export React Flow document to JSON Canvas 1.0 (best effort).
2. Import JSON Canvas into node/edge layout.
3. Add zoom-threshold behavior to hide markdown/anchors when zoomed out.
4. Limit neighbor-expansion batch size and add predicate filters.

Deliverable: 50 nodes / 200 edges remains smooth on modern laptop baseline.

---

## 4) Concrete file-level change map

### New backend modules
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
- `backend/app/canvas/service.py`
- `backend/app/canvas/__init__.py`

### Backend integration touchpoints
- `backend/app/main.py` (router registration)
- `backend/app/templates/browser/canvas_view.html` (canvas host)
- `backend/app/views/router.py` (add/route renderer type `canvas` if needed)

### Frontend additions (Track A)
- `frontend/canvas-ui/*` (source + build config)
- `frontend/static/js/canvas/main.js` (built artifact)
- `frontend/static/css/canvas.css`
- `frontend/static/js/workspace.js` (open/load canvas view type)

---

## 5) Testing and rollout strategy

## Automated
- Backend pytest:
  - canvas API CRUD + auth checks.
  - subgraph endpoint contract tests.
  - JSON canvas adapter unit tests.
- Frontend tests (if added in canvas-ui):
  - transform functions, anchor math, import/export.
- E2E Playwright:
  - open canvas tab, add node, save, reload, restore.
  - expand markdown node and verify anchor markers.

## Manual acceptance gates
1. No regression in current table/card/graph views.
2. Canvas doc persists per user session/account as expected.
3. Anchor edges remain attached after node drag, zoom changes, and markdown updates.
4. SSE stream survives brief network drop and resumes cleanly.

## Release strategy
- Ship behind feature flag (`settings.experimental.canvas_enabled`) for one milestone.
- Enable for **all authenticated users** in the initial rollout (no admin-only restriction).

---

## 6) Risks and SemPKM-specific mitigations
- **Build-pipeline drift risk:** committing built assets can drift from source.
  - Mitigation: add CI check that rebuild diff is clean.
- **Anchor measurement instability inside Dockview/htmx lifecycle:** render timing races.
  - Mitigation: schedule anchor measure on `requestAnimationFrame` + `ResizeObserver` + node expansion events.
- **Payload bloat in user_settings:** very large canvases may exceed practical limits.
  - Mitigation: enforce size cap + migrate to dedicated table at Beta.
- **Semantic mismatch between markdown links and RDF URIs:** existing content may mix wiki links/files/IRIs.
  - Mitigation: define canonical link resolver before C3 (see locked decisions below).

---

## 7) Decisions (locked)

The following implementation decisions are now **approved** and should be treated as baseline constraints for execution:

1. **Packaging:** **Track A** (Vite-built, checked-in bundle).
2. **Storage scope (MVP):** **Per-user private** canvases.
3. **Canonical ID:** **RDF URI canonical**; file path retained as metadata.
4. **Link dialect (MVP):** **Standard Markdown links only** (`[text](...)`).
5. **Auto-triples from markdown links:** **No** in MVP (visual edge only).
6. **Rollout policy:** **All authenticated users** (feature enabled broadly, no admin-only preview).

### Execution implications of locked decisions

- Frontend implementation should proceed with `frontend/canvas-ui/` source + committed built output under `frontend/static/js/canvas/` (Track A).
- Canvas persistence should use the existing user-scoped settings path for MVP (`canvas.{id}.*` in `user_settings`), deferring shared/team canvases to a later phase.
- Node identity handling, subgraph lookup, and edge wiring should treat URI as the sole canonical key to avoid duplication conflicts.
- Markdown anchor parsing can scope to standard link tokens in MVP; wiki-link parsing is explicitly out-of-scope for initial delivery.
- Markdown link edges remain UI/visual semantics only in MVP; RDF graph mutation stays opt-in and future-scoped.
- Feature flagging, if used, should target all authenticated users rather than admin-only gating.

These decisions unblock conversion into execution-ready phase plans (`C0-01`, `C1-01`, etc.) matching the existing `.planning/phases/*` workflow.

# Virtual Filesystem over RDF Knowledge Graph

**Status:** Research / Early Design
**Date:** 2024-02-24
**Context:** SemPKM — Semantic Personal Knowledge Management

---

## 1. Vision

Expose the SemPKM knowledge graph as a virtual, mountable filesystem where:

- **Mount points** are configurable projections of graph shapes onto directory hierarchies.
- **Folders** represent grouping dimensions (tags, types, relationships, property values).
- **Files** are RDF resources rendered as Markdown with YAML frontmatter.
- **Edits** (writes, renames, moves) are translated back into SPARQL updates, validated against SHACL shapes before commit.
- A **declarative mapping language** describes how graph patterns project onto filesystem trees.

### Example: `/notes` Mount

```
/notes/
  by-tag/
    machine-learning/
      neural-networks-overview.md
      transformer-architecture.md
    philosophy/
      epistemology-notes.md
  by-type/
    observation/
      ...
    idea/
      ...
  all/
    neural-networks-overview.md
    ...
```

Each `.md` file contains:

```markdown
---
uri: "https://example.org/data/note-001"
type: Note
title: "Neural Networks Overview"
noteType: observation
tags:
  - machine-learning
  - deep-learning
isAbout:
  - uri: "https://example.org/data/concept-nn"
    label: "Neural Networks"
relatedProject:
  uri: "https://example.org/data/project-ai"
  label: "AI Research"
created: "2024-01-15T10:30:00Z"
modified: "2024-02-20T14:00:00Z"
---

# Neural Networks Overview

The body content of the note in Markdown...
```

---

## 2. Prior Art & Academic Research

### 2.1 Foundational Work: Semantic File Systems (1991)

The concept was proposed by **Gifford et al. at MIT** in 1991. Their system interpreted file paths as conjunctive queries against automatically extracted metadata, using "transducers" for type-specific metadata extraction. Virtual directories provided compatibility with existing filesystem protocols.

**Key insight:** Paths *are* queries. `/tag:ml/type:note/` is equivalent to `SELECT ?s WHERE { ?s bpkm:tags "ml" ; a bpkm:Note }`.

**Reference:** Gifford et al., "Semantic File Systems," 1991 — [ResearchGate](https://www.researchgate.net/publication/2503061_Semantic_File_Systems)

### 2.2 SemFS — Semantic File System via WebDAV

SemFS exposes an RDF knowledge base as a **WebDAV drive**, reinterpreting filesystem paths as RDF resource locations. Developed under the EU NEPOMUK and ACTIVE projects (2006-2010). Resources are accessed through hierarchical paths mapped to metadata attributes rather than physical directories.

**Relevance to SemPKM:** SemFS is the closest existing system to our vision. It uses WebDAV (widely supported by OS file managers), maps paths to RDF queries, and integrates with desktop environments.

**Reference:** [SemFS on semanticweb.org](http://semanticweb.org/wiki/SemFS.html)

### 2.3 TagFS — SPARQL-Backed Tag Filesystem

TagFS (Schenk & Staab, 2006) defines filesystem semantics directly in terms of **SPARQL queries over an RDF graph**. Each filesystem view translates into a SPARQL query; views compose functionally. For example, `hasTag(hasTag(/, 'paper'), 'WWW2006')` composes two SPARQL views to filter by two tags.

**Key insight:** Filesystem operations (ls, open, stat) can be formally defined as SPARQL query/update operations. This is the most rigorous mapping between filesystem semantics and RDF graph operations.

**Relevance to SemPKM:** TagFS's compositional view model directly informs our declarative mapping language design. Our `sempkm:ViewSpec` already maps SPARQL queries to UI renderers — a filesystem "renderer" is a natural extension.

**Reference:** [TagFS Paper (ESWC 2006)](https://kmi.open.ac.uk/events/eswc06/poster-papers/FP31-Schenk.pdf)

### 2.4 GFS — Graph-based File System

GFS (2017) is a FUSE filesystem that allows **semantic spaces** to be nested within a traditional directory hierarchy. Users can selectively enable semantic organization in chosen folders while leaving system directories unaltered.

**Relevance to SemPKM:** The hybrid approach (semantic spaces coexisting with regular folders) is appealing. Mount points could be nested into an existing filesystem.

**Reference:** [GFS on GitHub](https://github.com/danieleds/GFS) — [ACM Paper](https://dl.acm.org/doi/10.1145/3077584.3077591)

### 2.5 rdflib-fuse — RDF Store as FUSE Filesystem

A Python project (by Pierre-Antoine Champin) that mounts any RDFLib-backed store as a FUSE filesystem. Graph names become directory paths; files contain serialized graph data.

**Relevance to SemPKM:** Demonstrates the FUSE + RDFLib approach. However, it exposes raw RDF serializations (Turtle, N-Triples) rather than user-friendly Markdown. Our design goes beyond this by rendering resources as human-editable documents.

**Reference:** [rdflib-fuse on GitHub](https://github.com/pchampin/rdflib-fuse)

### 2.6 FS2KG — From File Systems to Knowledge Graphs

FS2KG (Tzitzikas, 2022) works in the **reverse direction**: automatically producing knowledge graphs from folder structures via small configuration files. Demonstrates the bidirectional potential between filesystem hierarchies and KGs.

**Relevance to SemPKM:** Informs the "import" direction. If we expose a virtual FS, users could also bootstrap graph data by placing files into mount points.

**Reference:** [FS2KG Paper (CEUR)](https://ceur-ws.org/Vol-3254/paper354.pdf)

### 2.7 Plan 9 Synthetic Filesystems & 9P Protocol

Plan 9 from Bell Labs (1990s) took "everything is a file" to its logical extreme. All system services (networking, hardware, processes) are exposed as **synthetic filesystems** using the 9P protocol. Per-user namespaces mean each user gets a custom view of the filesystem. The protocol is intentionally simple and network-transparent.

**Key insights:**
- Synthetic filesystems are a proven IPC and data access paradigm.
- Per-user namespaces map well to personalized mount configurations.
- The 9P protocol (now available on Linux via v9fs) could be an alternative transport.
- Well-known filesystem semantics provide a universal, scriptable interface.

**Reference:** [9P Protocol (Wikipedia)](https://en.wikipedia.org/wiki/9P_(protocol)) — [Synthetic Filesystems (HandWiki)](https://handwiki.org/wiki/Synthetic_file_system)

### 2.8 Solid Pods — Linked Data Personal Data Stores

Tim Berners-Lee's **Solid project** stores personal data in "pods" using Linked Data (RDF) technologies. Pods are essentially filesystem-like containers accessed via HTTP/REST, with WAC (Web Access Control) for permissions. While not a traditional filesystem, Solid demonstrates that RDF data can be organized in hierarchical container structures with standard protocols.

**Relevance to SemPKM:** Solid's container model (LDP containers as folders, resources as files) is analogous to our mount point concept. Our system could potentially expose data as a Solid-compatible pod.

**Reference:** [Solid Project](https://solidproject.org/) — [Solid on Wikipedia](https://en.wikipedia.org/wiki/Solid_(web_decentralization_project))

### 2.9 Mozilla GRAPH-TO-TREE Algorithm

Mozilla's archived RDF content model documentation describes a generic **GRAPH-TO-TREE** algorithm that recursively descends an RDF graph to produce a tree-shaped content model. The algorithm is parameterized by "hints" to handle the inherent ambiguity of projecting graphs onto trees. It can be performed **lazily** (on-demand per node).

**Key insight:** You need *one* generic graph-to-tree algorithm, not m×n custom converters. The hints/parameters are what we call the "declarative mapping."

**Reference:** [Mozilla RDF Content Model](https://www-archive.mozilla.org/rdf/content-model)

### 2.10 SHACL for Editing Interfaces

**Schímatos** generates web forms from SHACL shapes for knowledge graph editing. **SHAPEness** provides graph-based, form-based, and tree-based views for SHACL-constrained editing. The 2024 ACM Web Conference paper "From Shapes to Shapes" formally defines how SHACL constraints propagate through SPARQL CONSTRUCT queries.

**Key insight:** SHACL shapes can drive not just validation but also UI generation. In our case, SHACL shapes would determine which frontmatter fields are editable, what values are allowed, and which edits would be rejected.

**Relevance to SemPKM:** SemPKM already uses SHACL shapes for form generation. The same shapes can govern filesystem edit validation. **No existing work combines SHACL with filesystem-based editing** — this is a novel contribution.

**References:**
- [Schímatos on GitHub](https://github.com/schimatos/schimatos.org)
- [SHAPEness (ResearchGate)](https://www.researchgate.net/publication/373036851_SHAPEness_A_SHACL-Driven_Metadata_Editor)
- [From Shapes to Shapes (ACM 2024)](https://dl.acm.org/doi/10.1145/3589334.3645550)

---

## 3. Declarative Mapping Languages — Existing Work

### 3.1 R2RML & RML

**R2RML** (W3C) maps relational databases to RDF using declarative triples maps. **RML** extends R2RML to heterogeneous sources (CSV, JSON, XML). Both define Subject Maps, Predicate Maps, Object Maps, and Graph Maps — a vocabulary for describing how source structures become RDF terms.

**Relevance:** We need the *inverse* — mapping FROM RDF TO a hierarchical structure. But the R2RML/RML vocabulary for term maps, logical sources, and join conditions provides design patterns for our mapping language.

**References:**
- [R2RML W3C Recommendation](https://www.w3.org/TR/r2rml/)
- [RML Specification](https://rml.io/specs/rml/)

### 3.2 G2GML — Graph to Graph Mapping

G2GML maps RDF graphs to property graphs using declarative pattern pairs. Each mapping specifies an RDF graph pattern and a corresponding property graph pattern.

**Relevance:** G2GML demonstrates declarative graph-to-graph mapping. Our language is graph-to-tree, but the pattern-matching approach is transferable.

### 3.3 SPARQL CONSTRUCT as a Mapping Primitive

SPARQL CONSTRUCT already serves as a mapping language in SemPKM's `ViewSpec` system. The graph view specs use CONSTRUCT queries to project subgraphs. A filesystem mount could use a similar CONSTRUCT query to define "what data belongs in this mount."

**Key advantage:** SPARQL CONSTRUCT is well-understood, standardized, and already used in SemPKM.

---

## 4. Design Concepts for SemPKM

### 4.1 Architecture: Mount as ViewSpec Extension

SemPKM already has `sempkm:ViewSpec` with `rendererType` values of `table`, `card`, and `graph`. A virtual filesystem is conceptually a new renderer type: `filesystem`.

```jsonld
{
  "@id": "bpkm:mount-notes-by-tag",
  "@type": "sempkm:MountSpec",
  "rdfs:label": "Notes by Tag",
  "sempkm:mountPath": "/notes/by-tag",
  "sempkm:targetShape": { "@id": "bpkm:NoteShape" },
  "sempkm:directoryStrategy": "tag-groups",
  "sempkm:fileTemplate": "markdown-frontmatter",
  "sempkm:sparqlScope": "SELECT ?s WHERE { ?s a bpkm:Note }",
  "sempkm:directoryProperty": { "@id": "bpkm:tags" },
  "sempkm:fileNameProperty": { "@id": "dcterms:title" },
  "sempkm:bodyProperty": { "@id": "bpkm:body" },
  "sempkm:writable": true
}
```

### 4.2 Proposed Mapping Language: `sempkm:MountSpec`

A `MountSpec` would define:

| Field | Purpose |
|---|---|
| `mountPath` | Where this mount appears in the virtual FS |
| `targetShape` | SHACL NodeShape governing resources in this mount |
| `sparqlScope` | SPARQL query defining which resources appear |
| `directoryStrategy` | How to organize into folders: `flat`, `tag-groups`, `property-value`, `type-hierarchy`, `relationship-tree` |
| `directoryProperty` | Which RDF property defines folder grouping |
| `fileNameProperty` | Which property provides the filename (slugified) |
| `bodyProperty` | Which property holds the main file content (Markdown) |
| `fileTemplate` | How to render the file: `markdown-frontmatter`, `json`, `turtle` |
| `writable` | Whether edits are allowed |
| `shaclValidation` | Whether to validate edits against the target shape |

### 4.3 Directory Strategies

**`tag-groups`** — Each unique tag value becomes a folder; resources with that tag appear as files within:
```
/notes/by-tag/
  machine-learning/
    note-1.md
    note-2.md
  philosophy/
    note-3.md
    note-1.md    # same note can appear under multiple tags
```

**`property-value`** — Group by a property's distinct values:
```
/notes/by-type/
  observation/
    ...
  idea/
    ...
  meeting-note/
    ...
```

**`type-hierarchy`** — Directories mirror `rdfs:subClassOf` or `skos:broader/narrower`:
```
/concepts/
  artificial-intelligence/
    machine-learning/
      deep-learning/
        neural-networks.md
```

**`relationship-tree`** — Follow an object property to create nesting:
```
/projects/
  ai-research/
    notes/
      meeting-2024-01-15.md
    participants/
      alice.md
      bob.md
```

**`flat`** — All resources as files in a single directory:
```
/all-notes/
  note-1.md
  note-2.md
  ...
```

### 4.4 File Rendering: Markdown + YAML Frontmatter

The rendering pipeline:

1. **SPARQL query** retrieves all triples for the resource.
2. **SHACL shape** determines which properties are frontmatter fields vs. body content.
3. **Property groups** from SHACL organize the frontmatter sections.
4. **Object properties** (relationships) render as URIs with labels in frontmatter.
5. **The body property** (e.g., `bpkm:body`) becomes the Markdown content below the frontmatter separator.

### 4.5 Write Path: Edit → Validate → Update

When a file is saved:

1. **Parse** the Markdown+YAML back into property-value pairs.
2. **Diff** against the last-known state to identify changed triples.
3. **Validate** the proposed changes against the SHACL shape:
   - Cardinality constraints (`sh:minCount`, `sh:maxCount`)
   - Datatype constraints (`sh:datatype`)
   - Value constraints (`sh:in`, `sh:pattern`)
   - Class constraints for relationships (`sh:class`)
4. **If valid:** Execute SPARQL UPDATE to modify the graph.
5. **If invalid:** Reject the write (return an I/O error with a descriptive message in the log).

### 4.6 Transport Protocol Options

| Protocol | Pros | Cons |
|---|---|---|
| **FUSE** | Native OS integration, full POSIX semantics, transparent to all apps | Linux/macOS only, kernel module dependency, performance concerns |
| **WebDAV** | Cross-platform, supported by all OS file managers, HTTP-based | Limited semantics (no symlinks, limited xattr), needs HTTP server |
| **9P/v9fs** | Elegant, minimal, plan9-inspired, good Linux support | Less familiar, limited tooling outside Linux |
| **NFS** | Universal, mature | Complex to implement, heavy |
| **REST API + FUSE bridge** | SemPKM already has HTTP API, FUSE layer translates | Two-layer architecture, latency |

**Recommended initial approach:** WebDAV via the existing FastAPI backend, since:
- SemPKM is already an HTTP application
- WebDAV is supported natively by Windows Explorer, macOS Finder, and Linux file managers
- Python has mature WebDAV server libraries (wsgidav)
- SemFS demonstrated this approach successfully

### 4.7 Relationship to Existing SemPKM Architecture

```
┌─────────────────────────────────────────────────┐
│  SemPKM Backend (FastAPI)                       │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Browser  │  │ REST API │  │ VirtualFS    │  │
│  │ (HTML)   │  │ (JSON)   │  │ (WebDAV)     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│  ┌────┴──────────────┴───────────────┴───────┐  │
│  │          Service Layer                    │  │
│  │  ┌─────────────┐  ┌──────────────────┐    │  │
│  │  │ ViewSpec    │  │ MountSpec        │    │  │
│  │  │ (table,card,│  │ (filesystem      │    │  │
│  │  │  graph)     │  │  projection)     │    │  │
│  │  └─────────────┘  └──────────────────┘    │  │
│  │          │               │                │  │
│  │  ┌───────┴───────────────┴──────────┐     │  │
│  │  │    SPARQL / Triplestore Layer    │     │  │
│  │  └──────────────┬───────────────────┘     │  │
│  │                 │                         │  │
│  │  ┌──────────────┴───────────────────┐     │  │
│  │  │    SHACL Validation Layer        │     │  │
│  │  └──────────────────────────────────┘     │  │
│  └───────────────────────────────────────────┘  │
│                    │                            │
│           ┌────────┴────────┐                   │
│           │   RDF4J Store   │                   │
│           └─────────────────┘                   │
└─────────────────────────────────────────────────┘
```

---

## 5. Novelty Assessment

Based on the literature survey, the following aspects appear **novel** (not found in existing work):

1. **SHACL-validated filesystem writes.** No existing system uses SHACL shapes to validate edits made through a filesystem interface. SemFS, TagFS, and GFS all support read-only or unconstrained writes.

2. **Declarative mount specs as RDF.** While TagFS defines views as SPARQL queries, and R2RML/RML define source-to-RDF mappings, no existing system defines filesystem-to-graph mappings as RDF resources using a declarative vocabulary.

3. **Markdown+frontmatter as a round-trippable RDF serialization.** Existing systems (rdflib-fuse) expose raw RDF serializations. Rendering RDF resources as human-friendly Markdown with YAML frontmatter, and parsing edits back into RDF updates, is not found in the literature.

4. **SHACL-driven frontmatter schema.** Using SHACL property shapes to determine which RDF properties appear in YAML frontmatter, their types, cardinalities, and allowed values — generating what is effectively a schema for the frontmatter — has no precedent.

5. **Integration with ViewSpec.** Treating the filesystem as another "renderer" alongside table, card, and graph views, sharing the same SPARQL and SHACL infrastructure, is architecturally novel.

---

## 6. Open Questions & Risks

### 6.1 Graph-to-Tree Ambiguity
RDF graphs are not trees. A resource with multiple tags appears in multiple directories. Options:
- **Symlinks / hardlinks** — One canonical location, links in others.
- **Duplicate files** — Same content in multiple folders (risk of conflicting edits).
- **Virtual copies with conflict resolution** — Writes to any copy update the same resource; conflicts are detected.

### 6.2 Filename Collisions
Multiple resources could have the same title within a directory. Strategies:
- Append a hash suffix: `neural-networks-overview-a1b2c3.md`
- Use the local part of the URI as filename
- Use title + disambiguator from another property

### 6.3 Performance
SPARQL queries on every `readdir()` or `stat()` call could be expensive.
- **Caching layer** with invalidation on graph changes (SemPKM's event system could drive cache invalidation).
- **Lazy enumeration** — Only query when a directory is actually listed.
- **Watch for SPARQL query cost** — Mount specs with broad scope could be slow.

### 6.4 Concurrency
Multiple processes editing the same file, or editing via the filesystem and the web UI simultaneously:
- Use ETags / last-modified timestamps for optimistic concurrency.
- SemPKM's event log could provide a conflict detection mechanism.

### 6.5 Mapping Language Evolution
Starting simple (static mount specs) but designing for extensibility:
- Phase 1: Fixed directory strategies (tag-groups, flat, property-value)
- Phase 2: Composable strategies (nested groupings)
- Phase 3: User-defined SPARQL-based directory generators
- Phase 4: Full declarative DSL or SPARQL-template language

### 6.6 Non-Markdown Resources
Some RDF resources may not naturally map to Markdown (e.g., a Person with no body text). Options:
- Render as YAML-only files (no body below frontmatter)
- Use `.yaml` extension for property-only resources
- Always include an empty body section

---

## 7. Recommended Next Steps

1. **Prototype a read-only WebDAV mount** using `wsgidav` integrated with FastAPI, serving a single hardcoded mount (Notes by tag).
2. **Define the `MountSpec` vocabulary** as JSON-LD in the model layer.
3. **Implement Markdown+frontmatter rendering** from SPARQL results + SHACL shapes.
4. **Add write support** with SHACL validation on the parse-back path.
5. **Design the declarative mapping language** iteratively based on real usage patterns.
6. **Evaluate FUSE as an alternative** if WebDAV proves limiting.

---

## 8. References

### Academic Papers
- Gifford et al., "Semantic File Systems," MIT, 1991 — [ResearchGate](https://www.researchgate.net/publication/2503061_Semantic_File_Systems)
- Schenk & Staab, "TagFS: Bringing Semantic Metadata to the Filesystem," ESWC 2006 — [Paper](https://kmi.open.ac.uk/events/eswc06/poster-papers/FP31-Schenk.pdf)
- Tzitzikas, "FS2KG: From File Systems to Knowledge Graphs," 2022 — [Paper](https://ceur-ws.org/Vol-3254/paper354.pdf)
- Danieleds et al., "GFS: a Graph-based File System Enhanced with Semantic Features," ACM 2017 — [Paper](https://dl.acm.org/doi/10.1145/3077584.3077591)
- "From Shapes to Shapes: Inferring SHACL Shapes for Results of SPARQL CONSTRUCT Queries," ACM Web Conference 2024 — [Paper](https://dl.acm.org/doi/10.1145/3589334.3645550)
- Van Assche et al., "Declarative RDF graph generation from heterogeneous data: A systematic literature review," 2022 — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1570826822000373)
- "A Declarative Formalization of R2RML Using Datalog," CEUR 2024 — [Paper](https://ceur-ws.org/Vol-4083/paper63.pdf)

### Standards & Specifications
- [R2RML: RDB to RDF Mapping Language (W3C)](https://www.w3.org/TR/r2rml/)
- [RML: RDF Mapping Language](https://rml.io/specs/rml/)
- [SPARQL 1.1 Query Language (W3C)](https://www.w3.org/TR/sparql11-query/)
- [9P Protocol (Wikipedia)](https://en.wikipedia.org/wiki/9P_(protocol))
- [SHACL (Wikipedia)](https://en.wikipedia.org/wiki/SHACL)

### Software Projects
- [SemFS — Semantic File System](http://semanticweb.org/wiki/SemFS.html)
- [rdflib-fuse — RDF Store as FUSE Filesystem](https://github.com/pchampin/rdflib-fuse)
- [GFS — Graph-based File System](https://github.com/danieleds/GFS)
- [Schímatos — SHACL-based Web-Form Generator](https://github.com/schimatos/schimatos.org)
- [Solid Project](https://solidproject.org/)
- [libferris — Virtual Filesystem](https://lwn.net/Articles/306860/)
- [D2RQ Platform](http://d2rq.org/)

### SemPKM Internal
- `models/basic-pkm/shapes/basic-pkm.jsonld` — SHACL shapes for Note, Concept, Project, Person
- `models/basic-pkm/views/basic-pkm.jsonld` — ViewSpec definitions using SPARQL
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL ontology with `bpkm:tags`, `bpkm:body`

# Web Components for Mental Model System Integration

**Research Date:** 2026-03-03
**Author:** Claude (research task quick-18)
**Status:** Research complete -- architecture proposal with source links

---

## 1. Executive Summary

SemPKM's Mental Model system currently contributes backend-consumable artifacts: ontologies (JSON-LD), SHACL shapes (for form generation), view specifications (SPARQL-backed table/card/graph renderers), seed data, icons, and settings. The frontend consumes these through generic Jinja2 templates and htmx-driven partial updates. There is no mechanism for a model to contribute custom frontend UI code.

**The opportunity:** Allow Mental Model authors to ship specialized UI components alongside their data and schema artifacts. A "Kanban" model could contribute a `<sempkm-kanban-board>` element for project management views. A "Chemistry" model could contribute a `<sempkm-molecule-viewer>` for rendering molecular structures. A "Music" model could contribute a `<sempkm-chord-chart>` for displaying chord progressions. This would transform Mental Models from data-only packages into full-stack domain kits.

**Primary recommendation:** A phased approach starting with **Jinja2 macro bundles** (lowest risk, immediate value) progressing to **light DOM Custom Elements** (medium risk, high extensibility). Shadow DOM should be avoided for htmx compatibility. Full Web Component adoption (Phase 2+) should use a registration protocol where model-served JavaScript modules call `customElements.define()` with SemPKM-prefixed tag names, receiving RDF data via element attributes and properties. **Confidence level: MEDIUM-HIGH** for the phased approach; MEDIUM for Web Components specifically due to htmx interop friction points documented below.

**Key risks:** (1) htmx does not process `hx-*` attributes inside Shadow DOM without explicit configuration, making Shadow DOM Custom Elements incompatible with SemPKM's htmx-first architecture; (2) model-contributed JavaScript introduces a new attack surface requiring a trust model; (3) component registration lifecycle must integrate with the existing model install/uninstall flow without breaking hot-reload development patterns.

---

## 2. Current State

### 2.1 How Mental Models contribute artifacts today

A Mental Model is a directory containing a `manifest.yaml` and four artifact types stored in named graphs upon installation:

| Artifact | Named Graph | Format | Purpose |
|----------|-------------|--------|---------|
| Ontology | `urn:sempkm:model:{id}:ontology` | JSON-LD | RDF classes, properties, constraints |
| Shapes | `urn:sempkm:model:{id}:shapes` | JSON-LD | SHACL shapes for form generation |
| Views | `urn:sempkm:model:{id}:views` | JSON-LD | ViewSpec instances (SPARQL + renderer type) |
| Seed | `urn:sempkm:model:{id}:seed` | JSON-LD | Example instances loaded into `urn:sempkm:current` |

The `manifest.yaml` schema (`backend/app/models/manifest.py` -- `ManifestSchema`) validates `modelId`, `version`, `name`, `description`, `namespace`, `prefixes`, `entrypoints`, `settings`, and `icons`. There is no entrypoint for frontend code (JavaScript, CSS, or HTML templates).

### 2.2 How the frontend consumes model data

The rendering pipeline flows through:

1. **ViewSpecService** (`backend/app/views/service.py`) loads `ViewSpec` instances from model views graphs via SPARQL
2. **Renderer Registry** (`backend/app/views/registry.py`) maps renderer types (`table`, `card`, `graph`) to Jinja2 template paths
3. **Jinja2 templates** render HTML server-side; htmx swaps fragments into the DOM
4. **Frontend JS** (`frontend/static/js/`) provides interactivity (graph.js for Cytoscape, editor.js for forms, workspace.js for layout)

The `register_renderer()` function in `registry.py` already supports model-contributed renderer types, but these must map to Jinja2 templates that exist on the server filesystem. A model cannot currently contribute its own templates or JavaScript.

### 2.3 The gap

There is no mechanism for a model to:
- Contribute JavaScript that runs in the browser
- Register Custom Elements or Web Components
- Provide CSS specific to its custom UI
- Serve static assets from its model directory
- Declare frontend dependencies (CDN libraries, etc.)

---

## 3. Web Components + htmx Analysis

### 3.1 How Custom Elements behave during htmx DOM swaps

htmx operates by swapping HTML fragments into the DOM. When htmx performs an `innerHTML` swap (the default), the browser's HTML parser processes the new content, which includes upgrading any Custom Elements that have been registered via `customElements.define()`.

**Key finding:** Custom Elements work naturally with htmx's swap mechanism *if they are already registered* before the swap occurs. The browser automatically calls the element's `constructor()` and `connectedCallback()` when the element is inserted into the DOM, whether by initial page load or by htmx swap.

Source: [htmx documentation on 3rd party JS](https://htmx.org/docs/#3rd-party) describes that htmx fires `htmx:afterSwap` and `htmx:load` events after content insertion, which can be used to initialize components that need post-insertion setup.

Source: [MDN Web Components lifecycle callbacks](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements#custom_element_lifecycle_callbacks) documents that `connectedCallback` fires whenever an element is moved into the document, which is exactly what htmx swap does.

**Caveat:** The `htmx:afterSettle` event (fires after htmx has processed new content) is the correct hook for components that need to interact with htmx-processed siblings, not `connectedCallback` alone.

### 3.2 Shadow DOM implications for htmx attribute processing

**Critical finding: Shadow DOM is incompatible with htmx's default behavior.**

htmx processes attributes (`hx-get`, `hx-post`, `hx-swap`, `hx-trigger`, etc.) by scanning the DOM tree after each swap. It does **not** pierce Shadow DOM boundaries. This means:

- `hx-*` attributes inside a Shadow DOM are invisible to htmx
- htmx event bubbling (`htmx:beforeRequest`, etc.) does not cross shadow boundaries by default
- `hx-target` selectors cannot reach elements inside Shadow DOM from outside, or outside from inside

Source: [htmx GitHub issue #1022](https://github.com/bigskysoftware/htmx/issues/1022) discusses Shadow DOM incompatibility. The htmx team's position is that Shadow DOM support is not a priority because htmx is designed for server-rendered HTML, which inherently uses the light DOM.

Source: [htmx documentation](https://htmx.org/docs/) does not mention Shadow DOM at all, confirming it is not a supported use case.

### 3.3 Recommended pattern: Light DOM Custom Elements

The recommended approach for SemPKM is **light DOM Custom Elements** -- Custom Elements that render directly into the document DOM without using `this.attachShadow()`. This pattern:

1. Allows htmx to process `hx-*` attributes inside the component
2. Allows SemPKM's existing CSS to style component internals
3. Allows event bubbling to work naturally
4. Retains the benefit of Custom Element lifecycle callbacks (`connectedCallback`, `disconnectedCallback`, `attributeChangedCallback`)
5. Enables model-specific initialization logic

**Code example -- a model-contributed kanban board element:**

```javascript
// models/kanban-model/components/kanban-board.js
class SempkmKanbanBoard extends HTMLElement {
  static get observedAttributes() {
    return ['data-type-iri', 'data-view-spec'];
  }

  connectedCallback() {
    // Fetch board data from SemPKM API
    const typeIri = this.getAttribute('data-type-iri');
    const viewSpec = this.getAttribute('data-view-spec');

    // Render directly into light DOM (no Shadow DOM)
    this.innerHTML = `
      <div class="kanban-container"
           hx-get="/api/views/${encodeURIComponent(viewSpec)}/cards?group_by=status"
           hx-trigger="load"
           hx-target="this">
        <div class="kanban-loading">Loading board...</div>
      </div>
    `;
  }

  disconnectedCallback() {
    // Cleanup event listeners, observers, etc.
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== null && oldValue !== newValue) {
      // Re-render on attribute change
      this.connectedCallback();
    }
  }
}

// Register with SemPKM prefix
customElements.define('sempkm-kanban-board', SempkmKanbanBoard);
```

**Server-side usage (Jinja2 template):**

```html
<!-- The model contributes this template for its custom renderer -->
<sempkm-kanban-board
  data-type-iri="{{ target_class }}"
  data-view-spec="{{ spec_iri }}">
</sempkm-kanban-board>
```

Source: [Google Web Fundamentals - Custom Elements best practices](https://web.dev/articles/custom-elements-best-practices) recommends light DOM for components that need to participate in document-level CSS and event systems.

Source: [Lit documentation on light DOM](https://lit.dev/docs/components/shadow-dom/#implementing-createrenderroot) describes the `createRenderRoot() { return this; }` pattern for light DOM rendering in the Lit framework, confirming this is a well-understood pattern.

### 3.4 htmx extension point: `htmx:load` event

When htmx swaps new content into the DOM, it fires `htmx:load` on each new element. This is the ideal hook for Custom Elements that need post-swap initialization. SemPKM already uses this pattern implicitly (Lucide icon re-initialization after swap).

```javascript
// Global listener that model components can rely on
document.addEventListener('htmx:load', function(evt) {
  // evt.detail.elt is the newly loaded element
  // Custom Elements' connectedCallback will have already fired
  // This event is for any additional initialization
});
```

Source: [htmx events reference](https://htmx.org/events/#htmx:load) documents the `htmx:load` event lifecycle.

---

## 4. Security Model

### 4.1 Trust levels

Model-contributed JavaScript introduces executable code into the browser, requiring a trust model:

| Trust Level | Source | Examples | JavaScript Allowed? |
|-------------|--------|----------|---------------------|
| **Core** | SemPKM codebase | Built-in renderers, workspace.js, editor.js | Yes (trusted by definition) |
| **Trusted** | Published/curated models | `basic-pkm`, community-reviewed models | Yes (with CSP restrictions) |
| **Untrusted** | User-created models | Custom models without review | No (Jinja2 macros only) |

### 4.2 Sandboxing options analysis

| Approach | Security | htmx Compat | Performance | Complexity | Verdict |
|----------|----------|-------------|-------------|------------|---------|
| **No sandbox** | None | Full | Best | Lowest | Trusted models only |
| **CSP restrictions** | Medium | Full | Good | Low | Recommended for trusted |
| **iframe sandbox** | High | None | Poor | High | Too isolated |
| **ShadowRealm** | High | Unknown | Good | Medium | Not yet standardized |
| **Module scope** | Low-Medium | Full | Good | Low | Recommended baseline |

**CSP restrictions** (Content Security Policy): The server can set CSP headers that restrict what model JavaScript can do:
- `script-src 'self'` -- only scripts served from the same origin
- `connect-src 'self'` -- only fetch/XHR to the same origin (prevents data exfiltration)
- No `eval()`, no inline scripts, no `data:` URIs for scripts
- Model JS modules loaded via `<script type="module" src="/models/{id}/components/...">` are allowed by `'self'`

Source: [MDN Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) provides comprehensive CSP documentation.

Source: [W3C CSP Level 3 specification](https://www.w3.org/TR/CSP3/) defines the full policy model.

**iframe sandbox**: The `<iframe sandbox="allow-scripts" srcdoc="...">` approach provides strong isolation but completely breaks htmx integration. Components inside iframes cannot participate in htmx request/response cycles, cannot access parent DOM, and require `postMessage` for all communication. This approach is viable only for fully self-contained widgets (e.g., a molecule viewer that doesn't need htmx).

Source: [MDN iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox) documents sandbox restrictions.

**ShadowRealm proposal**: TC39 Stage 2 proposal (as of early 2026) for JavaScript realm isolation. Would allow executing model JavaScript in an isolated global scope. Not yet available in any browser. Not recommended for near-term adoption.

Source: [TC39 ShadowRealm proposal](https://github.com/nicolo-ribaudo/tc39-proposal-shadowrealm) tracks the current proposal status.

### 4.3 Recommended approach per trust level

| Trust Level | Approach | Rationale |
|-------------|----------|-----------|
| **Core** | No restrictions | Part of the application codebase |
| **Trusted** | CSP + module scope | Prevents exfiltration, allows DOM access for htmx compat |
| **Untrusted** | Jinja2 macros only (no JS) | Server-side rendering eliminates client-side risk |

### 4.4 What model authors CAN and CANNOT do

**CAN:**
- Define Custom Elements with `sempkm-` prefixed tag names
- Render HTML into light DOM (no Shadow DOM)
- Use `hx-*` attributes in rendered HTML
- Listen to `htmx:load`, `sempkm:tab-activated`, and other SemPKM events
- Fetch data from SemPKM API endpoints (`/api/views/`, `/api/commands`, etc.)
- Import other model-provided ES modules
- Use CSS custom properties defined by SemPKM's theme system

**CANNOT:**
- Execute `eval()` or create inline scripts (CSP blocks this)
- Make network requests to external origins (CSP `connect-src 'self'`)
- Access `document.cookie` (httpOnly flag on `sempkm_session`)
- Modify core SemPKM DOM elements outside their component boundary (convention, not enforced)
- Override `customElements.define()` for non-`sempkm-` prefixed tags (enforced by registration API)
- Load external scripts or stylesheets (CSP `script-src 'self'`, `style-src 'self' 'unsafe-inline'`)

---

## 5. Manifest Extension Design

### 5.1 Proposed additions to manifest.yaml schema

```yaml
# Proposed new fields for ManifestSchema
components:
  # JavaScript modules to load (ES modules)
  modules:
    - path: "components/kanban-board.js"
      elements:
        - tag: "sempkm-kanban-board"
          description: "Kanban board view for projects"
    - path: "components/timeline.js"
      elements:
        - tag: "sempkm-timeline-view"
          description: "Timeline visualization"

  # CSS files to include
  styles:
    - "components/kanban.css"
    - "components/timeline.css"

  # Custom renderer registrations (extends existing registry.py)
  renderers:
    - type: "kanban"
      template: "components/kanban-renderer.html"  # Jinja2 template (Phase 1)
      element: "sempkm-kanban-board"               # Custom Element (Phase 2)

  # Template macros (Phase 1 - Jinja2 only)
  templates:
    - path: "templates/kanban-renderer.html"
      type: "renderer"
```

### 5.2 File structure within model bundle

```
models/kanban-model/
  manifest.yaml
  ontology/kanban-model.jsonld
  shapes/kanban-model.jsonld
  views/kanban-model.jsonld
  seed/kanban-model.jsonld
  components/                      # NEW: frontend components
    kanban-board.js                 # ES module defining Custom Element
    kanban.css                      # Component-specific styles
    timeline.js                     # Another component
    timeline.css
  templates/                       # NEW: Jinja2 templates (Phase 1)
    kanban-renderer.html            # Server-side renderer template
```

### 5.3 Registration lifecycle

```
Model Install                      Browser Load
    |                                   |
    v                                   v
1. parse manifest.yaml             5. Page loads, <head> includes
2. validate component entries         model CSS links
3. register renderers              6. <script type="module"> tags
   in RENDERER_REGISTRY               load model JS
4. serve static files via          7. customElements.define()
   nginx /models/{id}/static/         called per component
                                   8. htmx swaps content with
                                      <sempkm-*> elements
                                   9. connectedCallback() fires
                                      for each element instance
```

**Install time (server):**
1. `ModelService.install_model()` parses `manifest.yaml` including new `components` section
2. Validates component entries: tag names must start with `sempkm-`, JS files must exist, no `eval()` in source
3. Registers custom renderers in `RENDERER_REGISTRY` (template path or element tag)
4. Model static files are already volume-mounted; nginx needs a route to serve them

**Runtime (browser):**
5. Base template includes `<link>` tags for model CSS and `<script type="module">` tags for model JS
6. JavaScript modules execute, calling `customElements.define()` to register elements
7. When htmx swaps HTML containing `<sempkm-*>` tags, browser auto-upgrades them
8. `connectedCallback()` runs, component renders its light DOM content

### 5.4 Example manifest.yaml with component declarations

```yaml
modelId: kanban-model
version: "1.0.0"
name: "Kanban Board"
description: "Adds kanban board visualization for project management"
namespace: "urn:sempkm:model:kanban-model:"
prefixes:
  kbn: "urn:sempkm:model:kanban-model:"
entrypoints:
  ontology: "ontology/kanban-model.jsonld"
  shapes: "shapes/kanban-model.jsonld"
  views: "views/kanban-model.jsonld"
  seed: null
icons:
  - type: "kbn:Board"
    icon: "kanban"
    color: "#4e79a7"
settings:
  - key: "defaultColumns"
    label: "Default Kanban Columns"
    description: "Comma-separated list of default column names"
    input_type: "text"
    default: "Backlog,In Progress,Done"
components:
  modules:
    - path: "components/kanban-board.js"
      elements:
        - tag: "sempkm-kanban-board"
          description: "Kanban board with drag-and-drop columns"
  styles:
    - "components/kanban.css"
  renderers:
    - type: "kanban"
      element: "sempkm-kanban-board"
```

---

## 6. Integration Architecture

### 6.1 Serving model JavaScript modules

**Option A: nginx static path (RECOMMENDED)**

Add an nginx location block to serve model static files:

```nginx
# frontend/nginx.conf addition
location /models/ {
    alias /app/models/;
    # Only serve JS and CSS files from components/ directories
    location ~ ^/models/([a-z][a-z0-9-]*)/components/ {
        alias /app/models/$1/components/;
        add_header X-Content-Type-Options nosniff;
        add_header Cache-Control "public, max-age=3600";
    }
    # Block all other model files (ontology, shapes, etc.)
    return 403;
}
```

This leverages the existing Docker volume mount (`models/` directory is already accessible). No new API endpoint needed. Files are served with proper MIME types and caching headers.

**Option B: API endpoint**

A FastAPI endpoint like `GET /api/models/{model_id}/components/{filename}` could serve component files. This adds Python overhead for static file serving but enables access control and audit logging.

**Option C: Inline in template**

Model JavaScript could be inlined into Jinja2 templates via `<script>` tags. This avoids serving separate files but prevents browser caching and makes CSP harder (requires `'unsafe-inline'` or nonces).

**Recommendation:** Option A (nginx) for production, with Option B as fallback for deployments without nginx.

### 6.2 Component discovery

The frontend needs to know which components are available from installed models. Two approaches:

**Server-side discovery (recommended):**

The base template (`base.html`) already receives context data. Add a `model_components` context variable:

```python
# In the base template context
model_components = await model_service.get_installed_components()
# Returns: [{"model_id": "kanban-model", "modules": ["components/kanban-board.js"], "styles": ["components/kanban.css"]}]
```

```html
<!-- base.html head section -->
{% for comp in model_components %}
  {% for style in comp.styles %}
    <link rel="stylesheet" href="/models/{{ comp.model_id }}/components/{{ style }}">
  {% endfor %}
  {% for module in comp.modules %}
    <script type="module" src="/models/{{ comp.model_id }}/components/{{ module }}"></script>
  {% endfor %}
{% endfor %}
```

**Client-side discovery:**

An API endpoint returns component metadata, and a bootstrap script loads them dynamically:

```javascript
// frontend/static/js/model-components.js
async function loadModelComponents() {
  const response = await fetch('/api/models/components');
  const components = await response.json();
  for (const comp of components) {
    for (const module of comp.modules) {
      await import(`/models/${comp.model_id}/components/${module}`);
    }
  }
}
```

**Recommendation:** Server-side discovery for initial load (no JS needed, works with `<noscript>`), with lazy loading via dynamic `import()` for components only needed on specific views.

### 6.3 Data binding: how components receive RDF data

Custom Elements receive data through three channels:

**1. HTML attributes (simple values):**

```html
<sempkm-kanban-board
  data-type-iri="urn:sempkm:model:basic-pkm:Project"
  data-view-spec="urn:sempkm:model:kanban-model:kanban-projects">
</sempkm-kanban-board>
```

**2. htmx server-rendered content (HTML fragments):**

The component uses `hx-get` to fetch server-rendered HTML, which htmx swaps into the component's light DOM. This is the most htmx-native approach and keeps rendering on the server.

**3. JavaScript API calls (JSON data):**

For components that need raw data (e.g., graph visualizations), they can call SemPKM API endpoints:

```javascript
connectedCallback() {
  const specIri = this.getAttribute('data-view-spec');
  fetch(`/api/views/${encodeURIComponent(specIri)}/execute?format=json`)
    .then(r => r.json())
    .then(data => this.render(data));
}
```

**Recommendation:** Prefer approach #2 (htmx server-rendered) for most components. Use approach #3 only for components that genuinely need client-side rendering (interactive visualizations, drag-and-drop).

### 6.4 htmx integration: components in the request/response cycle

Light DOM Custom Elements participate in htmx naturally:

```html
<!-- Server returns this HTML fragment -->
<sempkm-kanban-board data-type-iri="...">
  <div class="kanban-columns" hx-get="/api/views/.../cards" hx-trigger="load">
    <!-- htmx will swap card data here -->
  </div>
</sempkm-kanban-board>
```

Components can also trigger htmx requests programmatically:

```javascript
// Inside a Custom Element method
this.querySelector('.kanban-card').dispatchEvent(
  new CustomEvent('moveCard', { bubbles: true })
);
// Or use htmx's JS API
htmx.ajax('POST', '/api/commands', {
  values: { command: 'object.patch', params: { iri: cardIri, ... } },
  target: this
});
```

Source: [htmx JavaScript API](https://htmx.org/api/#ajax) documents the `htmx.ajax()` function for programmatic requests.

---

## 7. Alternatives Comparison Table

| Criterion | Web Components (Light DOM) | Jinja2 Macro Bundles | iframe Sandbox | Server-Side Plugins (Python) | Declarative JSON Config |
|-----------|---------------------------|---------------------|----------------|-----------------------------|-----------------------|
| **Security** | Medium (CSP-restricted) | High (no client JS) | Highest (full isolation) | High (server-side only) | High (no code execution) |
| **DX for model authors** | Good (standard web APIs) | Good (familiar templating) | Poor (postMessage complexity) | Good (Python ecosystem) | Limited (constrained to schema) |
| **htmx compatibility** | Excellent (light DOM) | Excellent (native Jinja2) | None (cross-frame barrier) | Excellent (server-rendered) | Good (server-rendered JSON-to-HTML) |
| **Performance** | Good (browser-native) | Best (no JS overhead) | Poor (iframe overhead) | Good (server-rendered) | Good (server-rendered) |
| **Complexity to implement** | Medium (new serving/registration) | Low (extend existing template system) | High (message passing, sizing) | Medium (new plugin API) | Medium (schema design, validation) |
| **Interactivity** | Full (drag-and-drop, animations, canvas) | Limited (htmx-level only) | Full (within iframe) | Limited (htmx-level only) | None (static rendering) |
| **Offline/PWA support** | Good (cached modules) | None (requires server) | Poor (complex caching) | None (requires server) | None (requires server) |
| **Community ecosystem** | Large (standard Web APIs) | Small (SemPKM-specific) | Moderate (micro-frontends) | Moderate (Python plugins) | Moderate (JSON Schema tools) |

### Detailed comparison notes

**Jinja2 Macro Bundles** are the lowest-risk approach. Models contribute `.html` template files containing Jinja2 macros. The renderer registry already supports custom templates. The only gap is serving model templates -- currently, Jinja2 templates must be on the server filesystem at a known path. Extending the Jinja2 loader to include model directories (`models/{id}/templates/`) would close this gap with minimal code changes.

**Server-Side Plugins (Python)** would allow models to contribute Python code that generates HTML. This is powerful but introduces server-side code execution from model packages, which is a larger security concern than client-side JavaScript (server has access to the database, triplestore, filesystem). Python sandboxing is significantly harder than browser sandboxing.

**Declarative JSON Config** (similar to JSON Forms / RJSF) would define UI structure as JSON, which a generic renderer converts to HTML. This is safe and structured but severely limits what model authors can express. Complex visualizations (graphs, charts, kanban boards) cannot be described declaratively.

Source: [JSON Forms](https://jsonforms.io/) is a framework for rendering forms from JSON Schema.
Source: [React JSON Schema Form (RJSF)](https://rjsf-team.github.io/react-jsonschema-form/) is a popular JSON-to-form renderer.

---

## 8. Phased Adoption Roadmap

### Phase 1: Custom Renderer Templates (Jinja2 macros from models)

**Risk:** Low
**Effort:** Small (1-2 plans)
**Value:** Immediate -- models can contribute custom table layouts, card designs, and list formats

**What changes:**
1. Extend Jinja2 template loader to include `models/{id}/templates/` directories
2. Model `manifest.yaml` gets a `templates` section listing contributed template files
3. `register_renderer()` in `registry.py` maps renderer types to model template paths
4. Model templates use existing Jinja2 macros and SemPKM template context

**What model authors can do:**
- Custom table column layouts
- Custom card face designs
- Custom list/detail renderers
- All rendering is server-side; no JavaScript involved
- Full access to htmx attributes in templates

**Example manifest addition:**
```yaml
components:
  templates:
    - path: "templates/timeline-renderer.html"
      type: "renderer"
      renderer_type: "timeline"
```

**Example model template:**
```html
{# models/timeline-model/templates/timeline-renderer.html #}
{% macro render_timeline(rows, columns) %}
<div class="timeline-container">
  {% for row in rows %}
  <div class="timeline-entry"
       hx-get="/browser/object/{{ row.s | urlencode }}"
       hx-target="#editor-area-group-1"
       hx-push-url="false">
    <span class="timeline-date">{{ row.date }}</span>
    <span class="timeline-title">{{ row.title }}</span>
  </div>
  {% endfor %}
</div>
{% endmacro %}
```

### Phase 2: Light DOM Web Components (model-contributed Custom Elements)

**Risk:** Medium
**Effort:** Medium (2-3 plans)
**Value:** High -- enables interactive, client-rendered UI components

**What changes:**
1. `manifest.yaml` schema extended with `components.modules` and `components.styles`
2. nginx configured to serve `models/{id}/components/` static files
3. Base template includes model component `<script>` and `<link>` tags
4. `ManifestSchema` (`backend/app/models/manifest.py`) gains `ManifestComponentDef` model
5. `ModelService.install_model()` validates component entries (tag name prefix, file existence)
6. Tag name enforcement: all Custom Elements must use `sempkm-{modelId}-` prefix
7. CSP headers updated to allow model scripts from `/models/` path

**What model authors can do:**
- Full Custom Element API (lifecycle callbacks, observed attributes)
- Light DOM rendering with htmx integration
- Client-side interactivity (drag-and-drop, animations, canvas/SVG)
- Fetch data from SemPKM API endpoints
- Listen to SemPKM custom events (`sempkm:tab-activated`, etc.)
- Use SemPKM CSS custom properties for theming

**Tag naming convention:**
```
sempkm-{modelId}-{component-name}

Examples:
- sempkm-kanban-model-board
- sempkm-chemistry-molecule-viewer
- sempkm-music-chord-chart
```

### Phase 3: Full Component SDK (model author toolkit)

**Risk:** High
**Effort:** Large (4-6 plans)
**Value:** Very high -- professional model development experience

**What changes:**
1. `@sempkm/model-sdk` npm package with TypeScript types, base classes, test utilities
2. CLI tool for model scaffolding: `sempkm model create kanban-model`
3. Dev server with hot-reload for component development
4. Type-safe RDF data binding (TypeScript interfaces generated from SHACL shapes)
5. Component testing framework (renders Custom Elements with mock SemPKM API)
6. Model marketplace / registry for publishing and discovering models

**SDK base class example:**
```typescript
// @sempkm/model-sdk
export abstract class SempkmComponent extends HTMLElement {
  // Typed RDF data access
  protected get typeIri(): string { ... }
  protected get viewSpec(): ViewSpec { ... }

  // htmx integration helpers
  protected htmxGet(url: string, target?: HTMLElement): void { ... }
  protected htmxPost(command: string, params: object): void { ... }

  // Theme access
  protected getThemeVar(name: string): string { ... }

  // Lifecycle (override these)
  abstract render(): void;
  onDataChange?(data: RdfData): void;
  onThemeChange?(): void;
}
```

**This phase is aspirational and should only be undertaken after Phase 1 and Phase 2 are validated in production with real model authors.**

---

## 9. Source Links

### Web Components + htmx

- [htmx documentation - 3rd party JS integration](https://htmx.org/docs/#3rd-party) -- how htmx interacts with external JavaScript
- [htmx events reference](https://htmx.org/events/) -- `htmx:load`, `htmx:afterSwap`, `htmx:afterSettle` event documentation
- [htmx JavaScript API](https://htmx.org/api/) -- `htmx.ajax()`, `htmx.process()` for programmatic use
- [htmx GitHub issue #1022 - Shadow DOM](https://github.com/bigskysoftware/htmx/issues/1022) -- Shadow DOM incompatibility discussion
- [MDN Custom Elements](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements) -- lifecycle callbacks, registration, best practices
- [MDN Shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM) -- encapsulation model and limitations
- [Google Web Fundamentals - Custom Elements best practices](https://web.dev/articles/custom-elements-best-practices) -- light DOM vs Shadow DOM patterns

### Plugin/Extension Systems Using Web Components

- [Home Assistant Custom Cards](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/) -- model for community-contributed UI cards using Custom Elements with lifecycle hooks and typed data binding
- [Grafana Panel Plugins](https://grafana.com/developers/plugin-tools/) -- panel SDK with React/preact components, build system, and marketplace; security via iframe sandboxing for untrusted plugins
- [Backstage Plugin System](https://backstage.io/docs/plugins/) -- Spotify's developer portal uses React components as plugins; each plugin is an npm package with a well-defined API surface
- [Obsidian Plugin API](https://docs.obsidian.md/Plugins/) -- desktop app plugin system; plugins have full DOM access but run in a sandboxed Electron webview
- [Shoelace Web Components](https://shoelace.style/) -- production Web Component library demonstrating light DOM patterns and framework-agnostic design
- [Lit Framework](https://lit.dev/) -- Google's Web Component framework; documents light DOM rendering via `createRenderRoot()` override

### Security and Sandboxing

- [MDN Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) -- comprehensive CSP documentation
- [W3C CSP Level 3 Specification](https://www.w3.org/TR/CSP3/) -- formal specification
- [MDN iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox) -- sandbox restrictions and permissions
- [TC39 ShadowRealm proposal](https://github.com/nicolo-ribaudo/tc39-proposal-shadowrealm) -- Stage 2 JavaScript realm isolation proposal
- [OWASP Third-Party JavaScript Management](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html) -- security checklist for loading external JavaScript

### RDF/Linked Data + Web Components

- [Solid Project](https://solidproject.org/) -- Tim Berners-Lee's decentralized web platform; bridges RDF (Linked Data) with web applications; Solid apps consume RDF via authenticated HTTP
- [LDflex](https://github.com/LDflex/LDflex) -- JavaScript library for querying Linked Data; could power data binding in model components
- [rdflib.js](https://github.com/linkeddata/rdflib.js) -- RDF library for JavaScript; used in Solid ecosystem for client-side RDF manipulation
- [Comunica](https://comunica.dev/) -- modular SPARQL query engine for JavaScript; could enable client-side SPARQL queries from model components
- [Schema.org WebApplication type](https://schema.org/WebApplication) -- semantic description of web applications, not directly for components but shows the gap in standardized component discovery

### Alternative Approaches

- [JSON Forms](https://jsonforms.io/) -- declarative JSON Schema to UI rendering framework
- [React JSON Schema Form (RJSF)](https://rjsf-team.github.io/react-jsonschema-form/) -- JSON Schema-driven form rendering
- [Micro Frontends](https://micro-frontends.org/) -- architectural pattern for composing frontend applications; iframe-based isolation approach
- [Module Federation (Webpack 5)](https://webpack.js.org/concepts/module-federation/) -- runtime module sharing between independently deployed applications
- [single-spa](https://single-spa.js.org/) -- micro-frontend framework; orchestrates multiple frameworks in a single page

### Registration and Lifecycle

- [MDN customElements.define()](https://developer.mozilla.org/en-US/docs/Web/API/CustomElementRegistry/define) -- registration API
- [MDN Dynamic import()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/import) -- lazy loading ES modules
- [Web Components lazy loading patterns](https://web.dev/articles/custom-elements-best-practices#lazy-loading) -- deferred registration for performance
- [import maps specification](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script/type/importmap) -- browser-native module resolution mapping; could map `@sempkm/sdk` to a served URL

---

*Research completed 2026-03-03. This document provides architecture analysis for future implementation planning. No code changes required.*