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
