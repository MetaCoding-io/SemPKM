## Decision

Implement a read-only WebDAV virtual filesystem using `wsgidav` v4.3.x bridged into FastAPI via `a2wsgi.WSGIMiddleware`, with a `SemPKMDAVProvider` that maps MountSpec definitions to SPARQL-backed directory listings and markdown+frontmatter file rendering; start with `flat` and `tag-groups` directory strategies; defer write support to a later phase.

**Rationale:**
- wsgidav provides the exact extension points needed (`DAVProvider`, `DAVCollection`, `DAVNonCollection`) with a sample `VirtualResourceProvider` that almost exactly matches the MountSpec `tag-groups` strategy; the WSGI/ASGI bridge via `a2wsgi.WSGIMiddleware` is a solved, well-documented pattern for FastAPI
- WebDAV is natively supported by macOS Finder, Windows Explorer (Map Network Drive), and Linux file managers (Nautilus, Dolphin) — no special client software required
- The WebDAV protocol is HTTP-only, requiring no kernel-level access; this is critical for the Docker-deployed architecture where managed hosting environments prohibit `SYS_ADMIN` capability
- All required Python dependencies (`pyyaml`, `rdflib`, `pyshacl`, `cachetools`, `httpx`) are already in `pyproject.toml`; only three new packages needed: `wsgidav`, `a2wsgi`, `python-frontmatter`
- Read-only first bounds risk and delivers immediate user value (browse and open notes from OS file manager); write path is complex (diff engine, concurrency control, ETag management) and can be deferred to Phase 22d after the read-only MVP is validated
- MVP MountSpec vocabulary (7 predicates: `mountPath`, `sparqlScope`, `directoryStrategy`, `fileNameProperty`, `bodyProperty`, `directoryProperty`, `writable`) is minimal and sufficient for the core use case; remaining predicates from the prior research (`targetShape`, `fileTemplate`, `shaclValidation`) are deferred to write-support phase

**Alternatives ruled out:**
- **FUSE (pyfuse3, fusepy, mfusepy)** — requires `--cap-add SYS_ADMIN` and `--device /dev/fuse` Docker flags; managed hosting environments (AWS Fargate, Fly.io, Railway) prohibit `SYS_ADMIN` capability; FUSE is only viable for local-only Docker and self-hosted VPS, making it unsuitable as the primary access method; FUSE could be offered as an optional enhancement for power users later
- **Full async WebDAV from scratch** — no production-ready async WebDAV Python library exists; implementing the full WebDAV protocol (PROPFIND, GET, PUT, MKCOL, LOCK, etc.) from scratch is weeks of work; the WSGI thread pool via a2wsgi is adequate for WebDAV's inherently request-response model
- **Nginx WebDAV module** — provides only static file serving, not dynamic SPARQL-backed virtual directories; cannot implement the MountSpec concept
- **OpenSearch/sidecar approach** — irrelevant to VFS; not considered for this feature

---

# Phase 22: Virtual Filesystem -- Technology Validation

**Researched:** 2026-02-27
**Status:** Technology validation of prior research
**Overall Confidence:** MEDIUM-HIGH
**Prior Research:** `.planning/research/virtual-filesystem.md`

---

## Executive Summary

The prior research in `virtual-filesystem.md` is **sound and well-grounded**. The WebDAV-first approach via wsgidav remains the correct architectural choice. This validation confirms the core design while surfacing several important implementation risks and refining the phased rollout plan.

**Key validation outcomes:**

1. **wsgidav is viable but maintenance-lagging.** The latest stable release (v4.3.3) shipped May 2024. The library works and has an excellent custom provider API (`DAVProvider` / `DAVCollection` / `DAVNonCollection`), but it is WSGI-only with no async support. Integration with FastAPI requires `WSGIMiddleware` from `a2wsgi`, which runs wsgidav in a thread pool. This is acceptable for the use case because WebDAV I/O is inherently synchronous from the client perspective.

2. **FUSE is a bad fit for Docker-deployed SemPKM.** It requires `--cap-add SYS_ADMIN` and `--device /dev/fuse` on containers, which most managed hosting environments prohibit. WebDAV avoids all kernel-level dependencies.

3. **The MountSpec vocabulary design in the prior research is already close to minimum viable.** I recommend starting with just two strategies (`flat` and `tag-groups`) and three predicates (`mountPath`, `sparqlScope`, `fileNameProperty`).

4. **Write path is the hardest part.** Round-tripping markdown+frontmatter back to RDF triples via EventStore.commit is feasible using `python-frontmatter` for parsing, but requires careful diff logic against the last-known state.

5. **WebDAV client compatibility is good but has platform-specific quirks.** macOS Finder, Windows Explorer, and Linux file managers (Nautilus, Dolphin) all mount WebDAV natively, but Windows requires HTTPS for Basic auth, and macOS Finder has known performance issues with large directories.

6. **SPARQL-per-readdir is acceptable for personal-scale data** (hundreds to low thousands of items). RDF4J in-memory indices return simple SELECT queries in single-digit milliseconds for datasets under 100K triples. A TTL-based cache with event-driven invalidation is the right mitigation for larger scales.

---

## 1. wsgidav + FastAPI Integration

### Current State of wsgidav

| Attribute | Value | Confidence |
|-----------|-------|------------|
| Latest stable version | 4.3.3 (May 4, 2024) | HIGH |
| Unreleased | 4.4.0 (in progress, tests with Python 3.13) | MEDIUM |
| Python support | 3.9+ (tested through 3.13 in dev) | MEDIUM |
| Async support | None -- pure WSGI, synchronous | HIGH |
| Maintenance status | Low activity; no release in 12+ months | HIGH |
| License | MIT | HIGH |

**Sources:**
- [wsgidav GitHub](https://github.com/mar10/wsgidav)
- [wsgidav CHANGELOG](https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md)

### Integration Architecture

wsgidav produces a standard WSGI application via `WsgiDAVApp`. FastAPI is ASGI. The bridge uses `WSGIMiddleware` from the `a2wsgi` package:

```python
from a2wsgi import WSGIMiddleware
from wsgidav.wsgidav_app import WsgiDAVApp

# Create wsgidav WSGI app with custom provider
dav_config = {
    "provider_mapping": {"/": SemPKMDAVProvider(triplestore_client)},
    "simple_dc": {"user_mapping": {"*": True}},  # auth handled by SemPKM
    "verbose": 1,
}
dav_app = WsgiDAVApp(dav_config)

# Mount as sub-application inside FastAPI
app.mount("/dav", WSGIMiddleware(dav_app))
```

**Threading model:** `a2wsgi.WSGIMiddleware` runs the WSGI app in a thread pool (default 10 workers). Each WebDAV request occupies one thread. Since WebDAV operations call SPARQL queries via httpx (which is async), the WSGI threads will block on synchronous HTTP calls to RDF4J. This means the custom provider needs to use `httpx.Client` (sync) rather than `httpx.AsyncClient`.

**Implication:** The VFS DAVProvider will need its own synchronous TriplestoreClient wrapper (or use `asyncio.run()` / `loop.run_until_complete()` to bridge). This is a minor but real engineering cost.

### Custom Provider API

wsgidav has an excellent extensibility model for virtual filesystems. The key classes:

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `DAVProvider` | Root provider, maps paths to resources | `get_resource_inst(path)` |
| `DAVCollection` | Represents a directory | `get_member_list()`, `get_member_names()`, `create_collection()`, `create_empty_resource()` |
| `DAVNonCollection` | Represents a file | `get_content()`, `get_content_length()`, `get_content_type()`, `begin_write()`, `end_write()` |

The library includes a sample `VirtualResourceProvider` that demonstrates exactly our use case: resources with attributes dynamically organized into virtual directory hierarchies based on those attributes. For example, if `status=draft`, a collection `/by_status/draft/` is created automatically.

**This is an almost exact match for our MountSpec `tag-groups` strategy.**

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| wsgidav maintenance decline | MEDIUM | Library is stable and feature-complete for our needs. Pin to 4.3.x. If truly abandoned, the WSGI DAV protocol layer is well-documented enough to fork or replace. |
| No async support | LOW | WebDAV is inherently request-response. Thread pool is adequate. |
| WSGI/ASGI bridge complexity | LOW | Well-tested pattern via a2wsgi. FastAPI docs recommend this approach. |
| Sync triplestore calls from WSGI threads | MEDIUM | Create `SyncTriplestoreClient` wrapper using `httpx.Client` instead of `httpx.AsyncClient`. Simple but must not accidentally share the async client. |

### Verdict: USE WSGIDAV

The library is stable, has the exact extension points we need, and the WSGI/ASGI bridge is a solved problem. The maintenance concerns are real but the library is feature-complete for WebDAV serving -- it is not the kind of library that needs frequent updates.

---

## 2. FUSE as Alternative

### Current State

| Library | Latest Version | Async | Maintained | Notes |
|---------|---------------|-------|------------|-------|
| pyfuse3 | 3.4.2 (Jan 2026) | Trio (stable), asyncio (experimental) | Bug-fix only | Requires libfuse3, C compiler |
| fusepy | ~1.0.2 (stale) | No | New maintainers, slow | ctypes bindings, simpler API |
| mfusepy | maintained fork | No | Active | Recommended sync alternative |

**Sources:**
- [pyfuse3 GitHub](https://github.com/libfuse/pyfuse3)
- [fusepy GitHub](https://github.com/fusepy/fusepy)

### Docker Implications

FUSE requires kernel-level access. In Docker, this means:

```bash
docker run --cap-add SYS_ADMIN --device /dev/fuse ...
```

| Environment | FUSE Support |
|-------------|-------------|
| Local Docker | Yes, with `--cap-add SYS_ADMIN --device /dev/fuse` |
| Docker Compose | Yes, via `cap_add` and `devices` in compose file |
| Kubernetes | Requires privileged security context or specific PSP |
| AWS ECS/Fargate | No -- Fargate does not support `SYS_ADMIN` |
| Fly.io, Railway | No -- managed platforms block `SYS_ADMIN` |
| Self-hosted VPS | Yes, full control |

**Sources:**
- [FUSE and Docker wiki](https://github.com/mitre/fusera/wiki/FUSE-and-Docker)
- [Docker SYS_ADMIN discussion](https://github.com/moby/moby/issues/13875)

### FUSE vs WebDAV for SemPKM

| Criterion | WebDAV | FUSE |
|-----------|--------|------|
| Docker compatibility | Excellent (HTTP only) | Poor (needs SYS_ADMIN) |
| Cross-platform clients | macOS/Windows/Linux native | Linux/macOS only, Windows needs WinFsp |
| Implementation complexity | Medium (wsgidav handles protocol) | High (must implement full POSIX FS ops) |
| Performance | HTTP overhead per operation | Near-native (kernel bypass) |
| Write semantics | PUT-based, natural for documents | POSIX write()/fsync(), complex buffering |
| Network transparency | Built-in (HTTP) | Requires additional network layer |
| User experience | "Connect to Server" dialog | Transparent mount point |

### Verdict: REJECT FUSE FOR PRIMARY IMPLEMENTATION

FUSE is a non-starter for the Docker-deployed architecture. WebDAV gives us cross-platform access without any kernel dependencies. FUSE could be offered as an optional local-only enhancement in a future phase for power users who want transparent mount points, but it must not be the primary access method.

---

## 3. Minimum Viable MountSpec Vocabulary

### Starting Vocabulary

The prior research proposed a comprehensive MountSpec with 11 fields. For MVP, we need far fewer:

```turtle
@prefix sempkm: <urn:sempkm:vocab:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Classes
sempkm:MountSpec    a rdfs:Class ;
                    rdfs:label "Mount Specification" .

# Properties
sempkm:mountPath    a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range xsd:string ;
                    rdfs:comment "Virtual path where this mount appears, e.g. /notes" .

sempkm:sparqlScope  a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range xsd:string ;
                    rdfs:comment "SPARQL SELECT returning ?s for resources in this mount" .

sempkm:directoryStrategy a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range xsd:string ;
                    rdfs:comment "How to organize: flat | tag-groups" .

sempkm:fileNameProperty a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range rdf:Property ;
                    rdfs:comment "RDF property whose value becomes the filename (slugified)" .

sempkm:bodyProperty a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range rdf:Property ;
                    rdfs:comment "RDF property holding markdown body content" .

sempkm:directoryProperty a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range rdf:Property ;
                    rdfs:comment "RDF property for grouping (only for tag-groups strategy)" .

sempkm:writable     a rdf:Property ;
                    rdfs:domain sempkm:MountSpec ;
                    rdfs:range xsd:boolean ;
                    rdfs:comment "Whether writes are allowed (default false)" .
```

### MVP Mount Definitions

For the basic-pkm model, two mounts cover the primary use case:

```jsonld
{
  "@id": "bpkm:mount-all-notes",
  "@type": "sempkm:MountSpec",
  "rdfs:label": "All Notes",
  "sempkm:mountPath": "/notes",
  "sempkm:directoryStrategy": "flat",
  "sempkm:sparqlScope": "SELECT ?s WHERE { ?s a <https://example.org/ontology/basic-pkm#Note> }",
  "sempkm:fileNameProperty": {"@id": "dcterms:title"},
  "sempkm:bodyProperty": {"@id": "bpkm:body"},
  "sempkm:writable": false
}
```

```jsonld
{
  "@id": "bpkm:mount-notes-by-tag",
  "@type": "sempkm:MountSpec",
  "rdfs:label": "Notes by Tag",
  "sempkm:mountPath": "/notes-by-tag",
  "sempkm:directoryStrategy": "tag-groups",
  "sempkm:sparqlScope": "SELECT ?s WHERE { ?s a <https://example.org/ontology/basic-pkm#Note> }",
  "sempkm:fileNameProperty": {"@id": "dcterms:title"},
  "sempkm:bodyProperty": {"@id": "bpkm:body"},
  "sempkm:directoryProperty": {"@id": "bpkm:tags"},
  "sempkm:writable": false
}
```

### Deferred Properties (Phase 2+)

| Property | Deferred Because |
|----------|-----------------|
| `targetShape` | Not needed for read-only; needed when write validation is added |
| `fileTemplate` | Default to markdown-frontmatter; other formats later |
| `shaclValidation` | Only relevant with write support |

---

## 4. Write Path Integration

### Parse Pipeline: File Save to EventStore.commit

When a user saves a file through WebDAV, the following must happen:

```
File content (bytes)
    |
    v
python-frontmatter.loads(content)
    |
    +-- metadata: dict (YAML frontmatter)
    +-- content: str (markdown body)
    |
    v
Diff against last-known state
    |
    +-- changed_properties: list[(predicate, old_value, new_value)]
    +-- changed_body: Optional[str]
    |
    v
Build Operation objects
    |
    +-- materialize_deletes: old triples
    +-- materialize_inserts: new triples
    |
    v
EventStore.commit([operation])
```

### python-frontmatter Library

| Attribute | Value |
|-----------|-------|
| Package | `python-frontmatter` (PyPI) |
| Version | 1.1.0 (current) |
| Capabilities | Parse/dump YAML, TOML, JSON frontmatter; round-trip |
| Key methods | `frontmatter.loads(text)` returns Post with `.metadata` dict and `.content` str |
| Round-trip | `frontmatter.dumps(post)` serializes back to string with frontmatter |

**Source:** [python-frontmatter docs](https://python-frontmatter.readthedocs.io/)

### Diff Strategy

The VFS layer must maintain a cache of "last rendered state" per resource IRI. On write:

1. Parse the incoming file with `python-frontmatter`
2. Compare each frontmatter key against the cached metadata
3. For changed keys:
   - Map the key name back to the RDF predicate IRI (maintained in the render cache)
   - Create `materialize_deletes` for old values
   - Create `materialize_inserts` for new values
4. Compare body content against cached body
5. If changed, create delete/insert for the body property

### Render Cache Data Structure

```python
@dataclass
class RenderedResource:
    """Cached state of a resource as last rendered to the client."""
    resource_iri: str
    etag: str  # hash of rendered content
    rendered_at: datetime
    metadata: dict[str, Any]  # frontmatter key -> value
    body: str  # markdown body content
    key_to_predicate: dict[str, str]  # frontmatter key -> RDF predicate IRI
    predicate_datatypes: dict[str, str]  # predicate IRI -> XSD datatype
```

### SHACL Validation on Write

For the write path, SHACL validation can occur in two places:

1. **Pre-commit validation** (synchronous): Before calling `EventStore.commit()`, run the proposed triple changes through `pyshacl` validation against the target shape. Reject the WebDAV PUT with HTTP 409 Conflict if validation fails.

2. **Post-commit validation** (async, existing): The existing `AsyncValidationQueue` validates after commit and reports violations. This already works for web UI writes.

**Recommendation:** Start with post-commit only (reuse existing infrastructure). Add pre-commit validation as a refinement once the write path is stable.

### Key Challenges

| Challenge | Difficulty | Approach |
|-----------|-----------|----------|
| Frontmatter key to predicate mapping | MEDIUM | Maintain a bidirectional map in the render cache: `{"title": "dcterms:title", ...}` |
| Multi-value properties (tags) | MEDIUM | Render as YAML lists; parse back as lists; diff element-by-element |
| Object properties (relationships) | HIGH | Render as `{uri: "...", label: "..."}` in frontmatter; on write, extract URI, ignore label |
| Concurrent edits (WebDAV + web UI) | HIGH | Use ETags on WebDAV resources based on the event log timestamp. Reject stale PUTs with 412 Precondition Failed. |
| New file creation via WebDAV | HIGH | Defer to Phase 2. Requires IRI minting, type inference from mount context. |

---

## 5. WebDAV Client Discovery

### Platform Compatibility Matrix

| Client | Protocol | Auth | Known Issues | Confidence |
|--------|----------|------|--------------|------------|
| macOS Finder | WebDAV via "Connect to Server" | Basic (HTTPS only) or Digest (HTTP) | Slow with large directories; aggressive PROPFIND caching; may create `.DS_Store` artifacts | MEDIUM |
| Windows Explorer | "Map Network Drive" | Basic (HTTPS required) or NTLM | 3-second delay on some versions; `WebClient` service must be running; HTTPS strongly preferred | MEDIUM |
| Linux Nautilus (GNOME) | `davs://` or `dav://` via GVFS | Basic, Digest | Copy of directories may produce HTML instead of actual files (known GVFS bug) | MEDIUM |
| Linux Dolphin (KDE) | `webdav://` or `webdavs://` via KIO | Basic, Digest | Generally reliable | MEDIUM |
| davfs2 (CLI mount) | Mount as local filesystem | Basic, Digest | Best Linux option for transparent access; file-level caching | HIGH |
| Cyberduck | Full WebDAV client | All | Excellent compatibility; recommended for testing | HIGH |
| rclone | CLI mount/sync | All | Can mount WebDAV as FUSE; good for power users | HIGH |

**Sources:**
- [wsgidav client docs](https://wsgidav.readthedocs.io/en/latest/user_guide_access.html)
- [Nextcloud WebDAV docs](https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html)

### Authentication Strategy

SemPKM currently uses cookie-based session auth. WebDAV clients do not support cookies. Options:

| Method | Compatibility | Security | Implementation Complexity |
|--------|--------------|----------|--------------------------|
| HTTP Basic over HTTPS | All clients | Good (with TLS) | LOW -- map to existing user sessions |
| HTTP Digest | All clients except some Windows configs | Moderate | MEDIUM -- wsgidav has built-in support |
| API tokens (Bearer via Basic password field) | All clients (use token as password) | Good | LOW -- mint long-lived API tokens per user |

**Recommendation:** Use **API tokens passed as Basic auth password**. This is the pattern used by Nextcloud, Gitea, and other self-hosted tools. The username is the SemPKM username; the password is a revocable API token generated in the web UI. wsgidav's `HTTPAuthenticator` can be customized to validate tokens against SemPKM's auth system.

### Nginx Proxy Configuration

The WebDAV endpoint must be proxied through nginx with special handling:

```nginx
# WebDAV endpoint -- proxy to backend with WebDAV-required headers
location /dav/ {
    proxy_pass http://api:8000/dav/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebDAV methods beyond standard HTTP
    proxy_pass_request_headers on;

    # Increase timeouts for large file operations
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    # Disable buffering for streaming
    proxy_buffering off;

    # Required for PROPFIND Depth headers
    proxy_set_header Depth $http_depth;
    proxy_set_header Destination $http_destination;
    proxy_set_header Overwrite $http_overwrite;
}
```

---

## 6. Performance Analysis

### SPARQL Query Latency Expectations

SemPKM targets personal knowledge management -- typical datasets:

| Scale | Triples | Notes | Expected Query Time |
|-------|---------|-------|-------------------|
| Small | 1K-10K | 10-100 | < 5ms |
| Medium | 10K-100K | 100-1000 | 5-50ms |
| Large | 100K-1M | 1000-10000 | 50-500ms |

For `readdir()` (PROPFIND Depth:1), the query pattern is:

```sparql
SELECT ?s ?title WHERE {
  GRAPH <urn:sempkm:current> {
    ?s a bpkm:Note .
    ?s dcterms:title ?title .
  }
}
```

For RDF4J with a memory store (default SemPKM config), simple typed queries with one or two triple patterns return in **1-10ms** for datasets under 100K triples. This is well within acceptable latency for directory listings.

### Caching Strategy

```
WebDAV PROPFIND
    |
    v
Cache lookup (mount_path + directory_path)
    |
    +-- HIT: return cached listing (< 1ms)
    +-- MISS: execute SPARQL query, populate cache
    |
    v
Cache invalidation triggers:
    - EventStore.commit() with affected_iris overlapping cached resources
    - TTL expiry (configurable, default 30 seconds)
    - Manual invalidation via admin API
```

**Implementation:** Use `cachetools.TTLCache` (already a dependency) keyed by `(user_iri, mount_path, directory_path)`. Invalidate on EventStore commits by checking if `affected_iris` intersect with any cached resource set.

### File Content Rendering Performance

Rendering a single resource as markdown+frontmatter requires:

1. SPARQL query for all triples of the resource: ~5-10ms
2. SHACL shape lookup (cached): ~1ms
3. Template rendering: ~1ms
4. **Total: ~10-15ms per file**

This is acceptable. WebDAV clients typically request files one at a time when opened.

### Bottleneck Analysis

| Operation | Bottleneck | Mitigation |
|-----------|-----------|------------|
| PROPFIND (directory listing) | SPARQL query per directory | TTL cache with event invalidation |
| GET (file read) | SPARQL query per resource | Cache rendered content per resource IRI |
| PUT (file write) | Frontmatter parse + diff + SPARQL update | Acceptable latency (~50-100ms total) |
| PROPFIND Depth:infinity | Recursive SPARQL queries | Reject or limit depth; return 403 |

---

## 7. Phased Rollout Plan

### Phase 22a: Read-Only MVP (2-3 weeks)

**Goal:** Mount SemPKM notes as a read-only WebDAV share accessible from any OS file manager.

**Deliverables:**
1. `SyncTriplestoreClient` wrapper (sync httpx for WSGI thread pool)
2. `SemPKMDAVProvider` with `get_resource_inst()` resolving mount paths
3. `MountCollection` (DAVCollection) implementing `get_member_list()` via SPARQL
4. `ResourceFile` (DAVNonCollection) implementing `get_content()` with markdown+frontmatter rendering
5. `flat` directory strategy only
6. Hard-coded mount config (not yet from RDF)
7. No authentication (relies on network isolation or reverse proxy auth)
8. Basic PROPFIND caching with TTL

**Minimal useful read-only VFS:**
- Navigate to `http://host/dav/notes/` and see all notes as `.md` files
- Open any `.md` file and see YAML frontmatter + markdown body
- Mount in Finder/Explorer/Nautilus and browse/read notes

### Phase 22b: Directory Strategies + MountSpec (1-2 weeks)

**Deliverables:**
1. `tag-groups` directory strategy (notes grouped by tag values)
2. MountSpec vocabulary stored in model views graph
3. MountSpec loader (query installed model mounts at startup)
4. Multiple mount points (e.g., `/dav/notes/`, `/dav/notes-by-tag/`)
5. Filename collision handling (append IRI hash suffix)

### Phase 22c: Authentication + Multi-User (1 week)

**Deliverables:**
1. API token generation in web UI (Settings page)
2. Custom wsgidav `HTTPAuthenticator` validating tokens against SemPKM auth
3. Per-user workspace scoping (user sees only their workspace's data)
4. nginx proxy configuration for `/dav/` path

### Phase 22d: Write Support (2-3 weeks)

**Deliverables:**
1. `python-frontmatter` integration for parsing writes
2. Frontmatter-to-RDF diff engine
3. `ResourceFile.begin_write()` / `end_write()` implementation
4. EventStore.commit() integration on write
5. ETag-based concurrency control
6. Post-commit SHACL validation (reuse existing queue)

### Phase 22e: Refinements (1-2 weeks)

**Deliverables:**
1. Pre-commit SHACL validation with descriptive error messages
2. `property-value` directory strategy
3. File creation (new resource via WebDAV PUT to mount)
4. Rename/move support (update title/tags based on destination path)
5. Performance optimization (batch SPARQL queries for directory listings)

---

## Architecture Diagram

```
                    OS File Manager
                    (Finder / Explorer / Nautilus)
                          |
                     WebDAV (HTTP)
                          |
                    +-----v------+
                    |   nginx    |
                    |  /dav/ --> |
                    +-----+------+
                          |
                    +-----v-----------+
                    |  FastAPI (ASGI) |
                    |                 |
                    |  app.mount(     |
                    |    "/dav",      |
                    |    WSGIMiddleware(
                    |      WsgiDAVApp)|
                    |  )             |
                    +-----+----------+
                          |
              +-----------v-----------+
              |  WSGIMiddleware       |
              |  (a2wsgi thread pool) |
              +-----------+-----------+
                          |
              +-----------v-----------+
              |  WsgiDAVApp           |
              |  +-----------------+  |
              |  | SemPKMProvider  |  |
              |  |   |            |  |
              |  |   +-> MountCollection (readdir)
              |  |   +-> TagGroupCollection (readdir)
              |  |   +-> ResourceFile (read/write)
              |  +-----------------+  |
              +-----------+-----------+
                          |
              +-----------v-----------+
              | SyncTriplestoreClient |
              |  (httpx.Client)       |
              +-----------+-----------+
                          |
              +-----------v-----------+
              |  RDF4J Triplestore    |
              |  (SPARQL endpoint)    |
              +-----------+-----------+
                          |
              +-----------v-----------+
              | urn:sempkm:current    |
              | (materialized graph)  |
              +-----------------------+
```

### Component Responsibilities

| Component | Responsibility | Key Integration Point |
|-----------|---------------|----------------------|
| `SemPKMDAVProvider` | Route WebDAV paths to collection/file objects | `get_resource_inst(path)` dispatches to mount handlers |
| `MountCollection` | Represent a mount point root directory | Executes `sparqlScope` query; returns member list |
| `TagGroupCollection` | Represent a tag-value subdirectory | Filters parent query by tag value |
| `ResourceFile` | Render/parse individual RDF resources as files | Read: SPARQL + SHACL -> markdown. Write: markdown -> EventStore |
| `SyncTriplestoreClient` | Synchronous SPARQL queries from WSGI threads | Wraps httpx.Client; mirrors async TriplestoreClient API |
| `FrontmatterRenderer` | Convert RDF triples to markdown+frontmatter | Uses SHACL shape to determine field order and types |
| `FrontmatterParser` | Parse markdown+frontmatter back to triple changes | Uses python-frontmatter; diffs against cached state |
| `MountSpecLoader` | Load MountSpec definitions from model graphs | Queries views graphs at startup; caches specs |

---

## Dependencies and Prerequisites

### Python Packages to Add

```
wsgidav>=4.3.3,<5.0
a2wsgi>=1.10
python-frontmatter>=1.1.0
```

### Existing Dependencies Already Sufficient

| Dependency | Used For | Already in pyproject.toml |
|-----------|----------|--------------------------|
| `pyyaml` | YAML frontmatter serialization | Yes (>=6.0) |
| `rdflib` | RDF triple manipulation | Yes (>=7.5.0) |
| `pyshacl` | Write validation | Yes (>=0.31.0) |
| `cachetools` | TTL caching for directory listings | Yes (>=7.0) |
| `httpx` | Sync triplestore client | Yes (>=0.28) |

### Infrastructure Prerequisites

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| EventStore transaction support | Done | `EventStore.commit()` handles atomic writes |
| SHACL shapes for all types | Done | `ShapesService` extracts form metadata |
| Label resolution | Done | `LabelService.resolve_batch()` for display names |
| ViewSpec infrastructure | Done | Pattern for MountSpec to follow |
| nginx proxy for `/dav/` | Needed | Add location block to `frontend/nginx.conf` |
| API token auth system | Needed | New auth mechanism for non-browser clients |

---

## Implementation Risk Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|-----------|--------|----------|------------|
| wsgidav abandoned entirely | LOW | MEDIUM | LOW | Pin version; protocol is stable; fork if needed |
| WSGI thread pool exhaustion under load | LOW | MEDIUM | LOW | Increase a2wsgi worker count; WebDAV is low-concurrency for personal use |
| macOS Finder compatibility issues | MEDIUM | MEDIUM | MEDIUM | Test early; Finder is the pickiest client. Provide Cyberduck as fallback. |
| Windows requiring HTTPS | HIGH | MEDIUM | MEDIUM | Document HTTPS setup; provide reverse proxy TLS termination guide |
| Write path data corruption | MEDIUM | HIGH | HIGH | Implement ETag concurrency control from day one; thorough diff testing |
| Frontmatter round-trip lossy | MEDIUM | MEDIUM | MEDIUM | Extensive test suite for parse/render round-trips; handle edge cases (special chars, unicode) |
| SPARQL injection via filenames | MEDIUM | HIGH | HIGH | Always parameterize/escape user-provided strings in SPARQL; never interpolate raw filename content |
| Event invalidation race conditions | LOW | MEDIUM | LOW | TTL cache provides eventual consistency; acceptable for personal tool |
| Large directory listings slow | LOW | LOW | LOW | Personal-scale data; cache mitigates |
| Concurrent WebDAV + web UI edits | MEDIUM | HIGH | HIGH | ETag-based optimistic concurrency; last-write-wins with conflict detection |

---

## Open Questions for Phase-Specific Research

1. **wsgidav lock manager:** Should we implement WebDAV LOCK/UNLOCK for file locking? Most clients work without it, but some (Microsoft Office) require it. wsgidav has a built-in `LockManager` -- investigate whether to enable it.

2. **`.DS_Store` and Thumbs.db:** macOS Finder and Windows Explorer create metadata files in mounted directories. wsgidav may need a filter to reject or silently discard these writes.

3. **Large file streaming:** For resources with very long body content, should `get_content()` return a file-like stream or load everything into memory? wsgidav supports both patterns.

4. **Watch/notification:** Can WebDAV notify clients of server-side changes? The protocol does not support push notifications, but some clients poll PROPFIND. Investigate polling frequency implications.

5. **Multi-workspace mounts:** When multi-user support is active, should each user get a separate mount namespace (e.g., `/dav/{workspace_id}/notes/`)? Or should the auth layer transparently filter?

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|-----------|-----------|
| wsgidav viability | HIGH | Verified API, version, license, integration pattern |
| FUSE rejection | HIGH | Docker constraints are definitive |
| MountSpec vocabulary | MEDIUM | Design is sound but untested; may need iteration |
| Write path | MEDIUM | Feasible but complex; many edge cases to discover |
| Client compatibility | MEDIUM | Known patterns from Nextcloud/ownCloud; need hands-on testing |
| Performance | MEDIUM-HIGH | Personal-scale data is well within RDF4J capabilities; cache design is standard |
| Phased rollout | HIGH | Read-only first is clearly the right MVP boundary |

---

## Sources

### Official Documentation
- [wsgidav GitHub Repository](https://github.com/mar10/wsgidav)
- [wsgidav Documentation](https://wsgidav.readthedocs.io/)
- [wsgidav WsgiDAVApp API](https://wsgidav.readthedocs.io/en/latest/_autosummary/wsgidav.wsgidav_app.html)
- [wsgidav Configuration](https://wsgidav.readthedocs.io/en/maintain_3.x/user_guide_configure.html)
- [pyfuse3 GitHub](https://github.com/libfuse/pyfuse3)
- [python-frontmatter Docs](https://python-frontmatter.readthedocs.io/)
- [a2wsgi PyPI](https://pypi.org/project/a2wsgi/)

### FastAPI/Starlette Integration
- [FastAPI Sub-Applications](https://fastapi.tiangolo.com/advanced/sub-applications/)
- [FastAPI WSGI Integration Guide](https://www.getorchestra.io/guides/fastapi-and-wsgi-integration-a-comprehensive-guide)
- [Starlette WSGIMiddleware Discussion](https://github.com/Kludex/starlette/discussions/1305)
- [Starlette root_path Refactor](https://github.com/Kludex/starlette/pull/2400)

### WebDAV Protocol
- [RFC 4918 -- WebDAV](https://datatracker.ietf.org/doc/html/rfc4918)
- [Nextcloud WebDAV Client Guide](https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html)
- [WebDAV Wikipedia](https://en.wikipedia.org/wiki/WebDAV)

### Docker / FUSE
- [FUSE and Docker](https://github.com/mitre/fusera/wiki/FUSE-and-Docker)
- [Docker CAP_SYS_ADMIN Discussion](https://github.com/moby/moby/issues/13875)
- [Azure Storage FUSE Container Instructions](https://github.com/Azure/azure-storage-fuse/issues/244)

### Frontmatter Parsing
- [python-frontmatter GitHub](https://github.com/eyeseast/python-frontmatter)
- [Python YAML Frontmatter Packages Comparison](https://safjan.com/python-packages-yaml-front-matter-markdown/)
