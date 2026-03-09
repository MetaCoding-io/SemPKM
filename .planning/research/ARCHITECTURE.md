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
