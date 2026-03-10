# Phase 56: VFS MountSpec - Research

**Researched:** 2026-03-10
**Domain:** WebDAV virtual filesystem extensions, RDF vocabulary design, SHACL-driven property editing, htmx settings UI
**Confidence:** HIGH

## Summary

Phase 56 extends the existing WebDAV VFS (model/type/object hierarchy) with user-defined "mounts" -- declarative directory structures that organize objects by different strategies (by-type, by-date, by-tag, by-property, flat). MountSpec definitions are stored as RDF triples in a dedicated named graph. The VFS provider dispatches paths starting with a mount prefix to strategy-specific collection classes. Editing YAML frontmatter in mounted files writes back to RDF properties via the existing `object.patch` command through the EventStore.

The existing codebase provides an excellent foundation: `SemPKMDAVProvider.get_resource_inst()` already dispatches by path segments, `ResourceFile` already renders objects as Markdown+frontmatter, `write.py` already bridges sync wsgidav to async EventStore, and the settings page already has a VFS section with the token management pattern to follow.

**Primary recommendation:** Extend the existing VFS module with new collection classes per strategy (one `DAVCollection` subclass per strategy), a `MountedResourceFile` that does SHACL-aware frontmatter rendering and property write-back, and store mount definitions in `urn:sempkm:mounts` named graph queried by a new `MountService`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Custom mounts appear alongside the existing model/type/object hierarchy at the WebDAV root -- not replacing it
- The existing model directories (basic-pkm/, etc.) are always visible -- no hide toggle
- MountSpec definitions stored as RDF in the triplestore (e.g., urn:sempkm:mounts named graph)
- Both shared (owner-created, visible to all users) and personal (user-created, visible only to creator) mounts supported
- Only SHACL-declared properties are writable via frontmatter edits -- the shape defines the writable boundary
- Edits committed via object.patch through the Command API -- full event sourcing, provenance, and validation
- On SHACL validation failure: accept the write and flag as lint warnings (consistent with "SHACL is assistive, not punitive -- saves always allowed")
- Relationship properties shown in frontmatter as label + IRI and are writable
- Mount scope can reference saved SPARQL queries (from Phase 53/54) to filter which objects appear
- Scope dropdown lists: "All objects" (default), all saved queries by name, and "Custom SPARQL..." for inline entry
- Inline form in the VFS settings section (same pattern as API token form)
- Fields: mount name, path prefix, strategy dropdown, strategy-specific fields, scope selector
- Strategy-specific fields appear dynamically when strategy is selected
- Live preview of the directory structure shown before saving (requires backend preview endpoint)
- Active mounts listed below the form with Edit and Delete actions
- Objects with multiple values for the grouping property appear as duplicate files in each relevant folder
- Both copies are real files with identical content; editing either updates the same RDF object
- ETag-based concurrency across paths -- all duplicate files share the same ETag (derived from object IRI)
- by-date strategy uses Year/Month bucketing: /2024/01-January/, /2024/02-February/
- Objects missing the grouping property go into _uncategorized/ folder

### Claude's Discretion
- RDF vocabulary term naming and namespace design for MountSpec
- Caching strategy for mounted directory listings
- Preview endpoint implementation details
- How to handle the sync bridge between wsgidav (WSGI/sync) and the async EventStore for property writes
- File naming convention within mounts (slugify strategy, deduplication approach)

### Deferred Ideas (OUT OF SCOPE)
- Composable/nested strategies (e.g., by-type then by-tag within each type) -- future enhancement
- User-defined SPARQL-based directory generators (full DSL) -- research doc Phase 3/4
- Non-Markdown file templates (JSON, Turtle) -- fileTemplate field in research doc
- FUSE transport as alternative to WebDAV -- research doc evaluated but deferred
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VFS-01 | MountSpec RDF vocabulary defines declarative directory structures | MountSpec vocabulary design in Architecture Patterns section; namespace `urn:sempkm:mount:` for instances, vocabulary terms under `urn:sempkm:` |
| VFS-02 | User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat) | Strategy collection classes per Don't Hand-Roll; strategy dispatch in provider; SPARQL queries per strategy documented |
| VFS-03 | VFS provider dispatches to the correct strategy based on mount path prefix | Provider path dispatch pattern documented in Architecture Patterns; prefix-check-first approach |
| VFS-04 | Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes | Frontmatter diff/write-back pattern documented; uses python-frontmatter + object.patch command; SHACL shape lookup for writable boundary |
| VFS-05 | Mount management UI in Settings for creating, editing, and deleting mounts | Settings page extension pattern; htmx inline form; dynamic strategy fields via JS; preview endpoint |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| wsgidav | >=4.3.3,<5.0 | WebDAV server -- DAVProvider, DAVCollection, DAVNonCollection | Already in use; custom providers are the documented extension pattern |
| python-frontmatter | >=1.1.0 | Parse/render YAML frontmatter + Markdown body | Already in use; supports dict-like metadata access and round-trip via `loads()`/`dumps()` |
| rdflib | (project version) | RDF vocabulary construction, SPARQL query building, graph manipulation | Already in use for all RDF operations |
| cachetools | >=7.0 | TTLCache for directory listing caching | Already in use in `vfs/cache.py` |
| a2wsgi | >=1.10 | WSGI-to-ASGI bridge for wsgidav | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (sync) | SyncTriplestoreClient for SPARQL in WSGI threads | All VFS collection/resource code runs sync |
| asyncio | stdlib | Bridge sync wsgidav writes to async EventStore | `asyncio.run()` in thread pool for commits |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RDF in triplestore for mount defs | SQLAlchemy table | RDF is consistent with project philosophy; triplestore makes mount scope SPARQL queries self-contained; no migration needed |
| Per-strategy collection classes | Single generic collection with strategy param | Per-strategy classes are cleaner; each ~50 lines; easier to test and extend |

**Installation:** No new dependencies needed. All libraries already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/vfs/
├── __init__.py
├── auth.py                 # (existing) WebDAV authenticator
├── cache.py                # (existing) TTL cache - extend for mount keys
├── collections.py          # (existing) RootCollection, ModelCollection, TypeCollection
├── mount_collections.py    # (NEW) MountRootCollection + strategy collections
├── mount_resource.py       # (NEW) MountedResourceFile with property write-back
├── mount_service.py        # (NEW) MountService - CRUD for mount definitions
├── provider.py             # (existing) SemPKMDAVProvider - extend dispatch
├── resources.py            # (existing) ResourceFile
├── router.py               # (existing) VFS browser API - extend for mount endpoints
├── strategies.py           # (NEW) Strategy enum + SPARQL query builders per strategy
├── write.py                # (existing) parse_dav_put_body - extend for property writes
```

### Pattern 1: Provider Path Dispatch with Mount Prefix Check
**What:** The provider checks mount prefixes BEFORE falling through to the existing model/type hierarchy. Mount definitions are loaded once and cached (TTL 30s like existing cache).
**When to use:** Every `get_resource_inst()` call.
**Example:**
```python
# In provider.py - extended get_resource_inst()
def get_resource_inst(self, path: str, environ: dict):
    parts = [p for p in path.strip("/").split("/") if p]

    if len(parts) == 0:
        # Root: includes both model dirs AND mount dirs
        return RootCollection("/", environ, self._client, self._mount_service)

    # Check if first segment is a mount path prefix
    mount = self._mount_service.get_mount_by_prefix(parts[0])
    if mount is not None:
        return self._resolve_mount_path(path, environ, mount, parts[1:])

    # Fall through to existing model/type/object hierarchy
    if len(parts) == 1:
        return ModelCollection(path, environ, self._client, model_id=parts[0])
    # ... existing dispatch
```

### Pattern 2: Strategy Collection Classes
**What:** Each of the 5 strategies has a dedicated `DAVCollection` subclass that knows how to query objects and organize them into subdirectories.
**When to use:** When resolving paths within a mount.
**Example:**
```python
class ByTagCollection(DAVCollection):
    """Lists tag value folders under a mount. e.g., /my-notes/machine-learning/"""

    def get_member_names(self) -> list[str]:
        """Query distinct tag values for objects in scope."""
        result = self._client.query(f"""
            SELECT DISTINCT ?tag FROM <urn:sempkm:current>
            WHERE {{
              {self._scope_filter}
              ?iri <{self._tag_property}> ?tag .
            }}
            ORDER BY ?tag
        """)
        tags = [b["tag"]["value"] for b in result["results"]["bindings"]]
        # Add _uncategorized if any objects lack the tag property
        if self._has_uncategorized():
            tags.append("_uncategorized")
        return [_slugify(t) for t in tags]
```

### Pattern 3: MountSpec RDF Vocabulary
**What:** Mount definitions stored as RDF in `urn:sempkm:mounts` named graph. Each mount is a named resource.
**When to use:** CRUD operations on mounts; loading mount configs at provider startup.

```turtle
@prefix sempkm: <urn:sempkm:> .
@prefix mount: <urn:sempkm:mount:> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

mount:my-notes a sempkm:MountSpec ;
    sempkm:mountName "My Notes" ;
    sempkm:mountPath "my-notes" ;               # URL-safe path prefix
    sempkm:directoryStrategy "by-tag" ;          # enum: by-type|by-date|by-tag|by-property|flat
    sempkm:groupByProperty <http://example.org/ns/tags> ;  # for by-tag, by-property
    sempkm:dateProperty <http://purl.org/dc/terms/created> ; # for by-date
    sempkm:sparqlScope "all" ;                   # "all" | saved query UUID | inline SPARQL
    sempkm:savedQueryId "uuid-here"^^xsd:string ; # optional, when using saved query
    sempkm:createdBy <urn:sempkm:user:uuid> ;
    sempkm:visibility "shared" ;                 # "shared" | "personal"
    sempkm:createdAt "2026-03-10T12:00:00Z"^^xsd:dateTime .
```

### Pattern 4: SHACL-Aware Frontmatter Rendering
**What:** `MountedResourceFile` queries the SHACL shape for the object's type, renders only SHACL-declared properties in frontmatter (with human-readable names from `sh:name`), and identifies writable vs read-only fields.
**When to use:** Every file GET (read) and PUT (write) in mounted directories.

```python
# Frontmatter rendering with SHACL awareness
def _render_shacl_frontmatter(self, iri: str, type_iri: str, triples: list) -> dict:
    """Build frontmatter dict guided by SHACL property shapes."""
    shape = self._get_shape_for_type(type_iri)  # sync SPARQL query
    fm = {"object_iri": iri, "type_iri": type_iri}

    for prop_shape in shape.properties:
        pred_iri = prop_shape.path
        values = [t[2] for t in triples if str(t[1]) == pred_iri]
        key = prop_shape.name  # sh:name -> human readable

        if prop_shape.target_class:
            # Object reference -> label + iri format
            fm[key] = self._resolve_references(values)
        elif len(values) == 1:
            fm[key] = str(values[0])
        elif len(values) > 1:
            fm[key] = [str(v) for v in values]

    return fm
```

### Pattern 5: Property Write-Back via Diff
**What:** On PUT, parse the new frontmatter, diff against the current state, build `object.patch` operations for changed properties only.
**When to use:** `MountedResourceFile.end_write()`.

```python
def _diff_and_patch(self, old_fm: dict, new_fm: dict, shape) -> dict:
    """Diff frontmatter and return {predicate_iri: new_value} for object.patch."""
    changes = {}
    for prop_shape in shape.properties:
        key = prop_shape.name
        old_val = old_fm.get(key)
        new_val = new_fm.get(key)
        if old_val != new_val and new_val is not None:
            # Convert back to RDF: resolve label+IRI dicts to IRIs
            if prop_shape.target_class:
                changes[prop_shape.path] = self._resolve_iri_refs(new_val)
            else:
                changes[prop_shape.path] = new_val
    return changes
```

### Pattern 6: Sync-to-Async Bridge for Property Writes
**What:** Reuse the existing `asyncio.run()` pattern from `write.py` to call async `object.patch` handler + `EventStore.commit()` from the sync wsgidav thread.
**When to use:** `MountedResourceFile.end_write()` when frontmatter properties have changed.

```python
# Extend write.py with property write support
async def _commit_property_patch(object_iri, changes, event_store, user_iri, user_role):
    from app.commands.handlers.object_patch import handle_object_patch
    from app.commands.schemas import ObjectPatchParams

    params = ObjectPatchParams(iri=object_iri, properties=changes)
    operation = await handle_object_patch(params, settings.base_namespace)
    user_ref = URIRef(user_iri) if user_iri else None
    await event_store.commit([operation], performed_by=user_ref, performed_by_role=user_role)

def write_properties_via_event_store(object_iri, changes, event_store, user_iri=None, user_role="member"):
    """Bridge sync context to async object.patch commit."""
    asyncio.run(_commit_property_patch(object_iri, changes, event_store, user_iri, user_role))
```

### Pattern 7: Mount Management API + Settings UI
**What:** REST endpoints for mount CRUD (stored as RDF), settings UI uses htmx inline form pattern identical to API token management.
**When to use:** Settings page VFS section.

```
API Endpoints:
  GET    /api/vfs/mounts          -> list mounts (filtered by user visibility)
  POST   /api/vfs/mounts          -> create mount (RDF insert into urn:sempkm:mounts)
  PUT    /api/vfs/mounts/{id}     -> update mount
  DELETE /api/vfs/mounts/{id}     -> delete mount
  POST   /api/vfs/mounts/preview  -> preview directory structure (dry-run)
```

### Anti-Patterns to Avoid
- **Modifying existing collection classes:** Mount collections should be NEW classes, not modifications to `ModelCollection`/`TypeCollection`. The existing hierarchy must remain untouched.
- **Using async in VFS collection code:** wsgidav runs in WSGI threads. All collection/resource code MUST use `SyncTriplestoreClient`. Only use `asyncio.run()` in the write path (isolated thread).
- **Storing mount definitions in SQLite:** RDF in the triplestore is consistent with the project philosophy. Mount scope SPARQL queries can directly reference the triplestore data. No migration needed.
- **Building a single monolithic strategy handler:** Use one class per strategy. Each is small (~50-80 lines) and independently testable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom YAML parser | `python-frontmatter` library | Already in use; handles edge cases (multiline values, special chars, encoding) |
| Filename slugification | New slug function | Existing `_slugify()` from `collections.py` | Already handles deduplication with hash suffix |
| Directory listing cache | New cache system | Existing `cached_get_member_names()` from `cache.py` | Thread-safe TTLCache already working; just add new cache keys |
| Property resolution | Manual IRI expansion | Existing `_resolve_predicate()` from `object_create.py` | Handles compact IRIs, full IRIs, bare local names |
| Value conversion | Manual type coercion | Existing `_to_rdf_value()` from `object_create.py` | Handles URIRef detection, typed literals |
| WebDAV auth | New auth system | Existing `SemPKMWsgiAuthenticator` | Already does Basic auth with API tokens |
| ETag generation | Custom ETag logic | SHA-256 of object IRI (not content) | Per CONTEXT.md: ETag derived from object IRI so duplicates share same ETag |
| SHACL shape lookup | Direct SPARQL in resource | Existing `ShapesService` pattern (sync variant needed) | Already extracts PropertyShape with path, name, datatype, target_class, in_values |

**Key insight:** The existing VFS module already has 80% of the patterns needed. The extension is additive -- new files, not rewrites. The `_slugify`, caching, auth, write bridge, and frontmatter patterns all transfer directly to mount collections.

## Common Pitfalls

### Pitfall 1: Sync vs Async Context Confusion
**What goes wrong:** Using `TriplestoreClient` (async) in VFS collection code, or using `SyncTriplestoreClient` in browser router endpoints.
**Why it happens:** Two parallel APIs exist -- async for FastAPI routes, sync for wsgidav WSGI threads.
**How to avoid:** VFS collection/resource classes ONLY use `SyncTriplestoreClient`. The `MountService` needs BOTH: a sync version for VFS use and async methods for the REST API. Create `SyncMountService` (for VFS) and keep async methods in the router (for settings UI).
**Warning signs:** `RuntimeError: This event loop is already running` or `RuntimeError: no running event loop`.

### Pitfall 2: Mount Path Conflicts with Model IDs
**What goes wrong:** User creates a mount with path prefix "basic-pkm" which collides with an existing model directory.
**Why it happens:** Mount prefixes and model IDs share the root namespace.
**How to avoid:** Validate mount path prefix on creation: reject if it matches any installed model ID. Also reject reserved names ("_uncategorized", path segments with slashes). Frontend validation + backend validation.
**Warning signs:** Mount hides an entire model's files from WebDAV access.

### Pitfall 3: SPARQL Scope Query Injection
**What goes wrong:** User provides inline SPARQL that modifies data or queries event graphs.
**Why it happens:** The "Custom SPARQL..." scope option allows arbitrary SPARQL input.
**How to avoid:** Use `scope_to_current_graph()` (already exists in `sparql/client.py`) to inject `FROM <urn:sempkm:current>` clause. Validate that the query is a SELECT (not UPDATE/INSERT/DELETE). Use `check_member_query_safety()` if applicable. The scope query is injected as a sub-select filter, not executed directly.
**Warning signs:** Objects from event graphs appearing in mounts; data modification via scope queries.

### Pitfall 4: Object IRI ETag vs Content ETag
**What goes wrong:** Using content-based ETag (SHA-256 of rendered content) means the same object at two different mount paths has different ETags if the frontmatter rendering differs slightly.
**Why it happens:** CONTEXT.md specifies "all duplicate files share the same ETag (derived from object IRI)".
**How to avoid:** Use `hashlib.sha256(object_iri.encode()).hexdigest()` as the ETag, NOT the rendered content hash. This ensures all paths pointing to the same object share the same ETag, enabling proper 412 Precondition Failed on stale edits.
**Warning signs:** Editing a file in one mount path doesn't invalidate the same file in another path.

### Pitfall 5: SHACL Shape Lookup in Sync Context
**What goes wrong:** `ShapesService.get_form_for_type()` is async but VFS code runs sync.
**Why it happens:** ShapesService uses the async TriplestoreClient.
**How to avoid:** Create a sync version of shape extraction that queries the shapes graph via `SyncTriplestoreClient`. The shape data is relatively stable (changes only when models are installed/updated), so cache aggressively (TTL 300s or until model change event).
**Warning signs:** Attempting to await in sync context; falling back to no-shape rendering.

### Pitfall 6: Frontmatter Key Name Collisions
**What goes wrong:** SHACL property `sh:name` values collide with reserved frontmatter keys (`object_iri`, `type_iri`).
**Why it happens:** `sh:name` is user-defined in Mental Model shapes.
**How to avoid:** Reserve `object_iri` and `type_iri` as system keys. Prefix any colliding property name with an underscore or use the predicate local name as fallback. Document the reserved keys.
**Warning signs:** Editing frontmatter corrupts system metadata; object IRI changes on save.

### Pitfall 7: Stale Mount Cache After CRUD
**What goes wrong:** After creating/editing/deleting a mount via the settings UI, the WebDAV provider still serves the old mount list.
**Why it happens:** Mount definitions are cached in the TTLCache with a 30s TTL.
**How to avoid:** Invalidate the mount cache key explicitly after any CRUD operation. Add a `clear_mount_cache()` function that removes mount-related keys from the listing cache. The REST API endpoints should call this after successful mutations.
**Warning signs:** New mount not visible in WebDAV until 30s later; deleted mount still accessible.

## Code Examples

### Mount SPARQL Queries by Strategy

#### by-type: List type folders
```sparql
# List distinct types for objects in scope
SELECT DISTINCT ?typeLabel ?typeIri FROM <urn:sempkm:current>
WHERE {
  ?iri a ?typeIri .
  # Scope filter (injected from mount definition)
  {scope_subquery}
  # Get human-readable type label
  OPTIONAL {
    GRAPH ?shapesGraph {
      ?shape <http://www.w3.org/ns/shacl#targetClass> ?typeIri ;
             <http://www.w3.org/ns/shacl#name> ?name .
    }
  }
  BIND(COALESCE(?name, REPLACE(STR(?typeIri), ".*[/:#]", "")) AS ?typeLabel)
}
ORDER BY ?typeLabel
```

#### by-tag: List tag value folders
```sparql
# List distinct tag values (grouping property values)
SELECT DISTINCT ?tagValue FROM <urn:sempkm:current>
WHERE {
  ?iri <{group_by_property}> ?tagValue .
  {scope_subquery}
}
ORDER BY ?tagValue
```

#### by-date: List year/month folders
```sparql
# List year-month combinations
SELECT DISTINCT ?year ?month FROM <urn:sempkm:current>
WHERE {
  ?iri <{date_property}> ?date .
  {scope_subquery}
  BIND(YEAR(xsd:dateTime(?date)) AS ?year)
  BIND(MONTH(xsd:dateTime(?date)) AS ?month)
}
ORDER BY DESC(?year) DESC(?month)
```

#### by-property: List property value folders
```sparql
# List distinct values of the grouping property
SELECT DISTINCT ?groupValue ?groupLabel FROM <urn:sempkm:current>
WHERE {
  ?iri <{group_by_property}> ?groupValue .
  {scope_subquery}
  OPTIONAL {
    ?groupValue <http://purl.org/dc/terms/title> ?t .
  }
  OPTIONAL {
    ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?r .
  }
  BIND(COALESCE(?t, ?r, IF(isIRI(?groupValue), REPLACE(STR(?groupValue), ".*[/:#]", ""), STR(?groupValue))) AS ?groupLabel)
}
ORDER BY ?groupLabel
```

### Frontmatter with Relationship Properties
```yaml
---
object_iri: "https://example.org/data/note-001"
type_iri: "https://example.org/ns/Note"
title: "Neural Networks Overview"
noteType: observation
tags:
  - machine-learning
  - deep-learning
relatedProject:
  label: AI Research
  iri: https://example.org/data/project-ai
isAbout:
  - label: Neural Networks
    iri: https://example.org/data/concept-nn
  - label: Deep Learning
    iri: https://example.org/data/concept-dl
created: "2024-01-15T10:30:00Z"
---

# Neural Networks Overview

The body content of the note...
```

### Mount Management Settings UI Pattern
```html
<!-- In _vfs_settings.html, below existing token sections -->
<div class="vfs-mount-section">
  <span class="settings-label">Custom Mounts</span>
  <span class="settings-description">Create directory structures that organize your objects by tag, date, type, or any property.</span>

  <form id="mount-form" onsubmit="return mountSubmitForm(event)">
    <div class="mount-form-row">
      <input type="text" id="mount-name" placeholder="My Notes by Tag" required>
      <input type="text" id="mount-path" placeholder="notes-by-tag" required
             pattern="[a-z0-9][a-z0-9-]*" title="Lowercase letters, numbers, hyphens only">
    </div>
    <div class="mount-form-row">
      <select id="mount-strategy" onchange="mountStrategyChanged(this.value)">
        <option value="flat">Flat (all files in one folder)</option>
        <option value="by-type">By Type</option>
        <option value="by-date">By Date</option>
        <option value="by-tag">By Tag</option>
        <option value="by-property">By Property</option>
      </select>
    </div>
    <!-- Dynamic strategy-specific fields inserted by JS -->
    <div id="mount-strategy-fields"></div>
    <div class="mount-form-row">
      <select id="mount-scope">
        <option value="all">All objects</option>
        <!-- Populated dynamically from saved queries API -->
      </select>
    </div>
    <div id="mount-preview"></div>
    <button type="submit" class="btn-primary">Create Mount</button>
  </form>

  <!-- Active mounts list (populated via fetch) -->
  <div id="mount-list"></div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded model/type/object VFS hierarchy | Extensible hierarchy with pluggable mount strategies | Phase 56 | Users can organize objects by any dimension |
| Body-only writes via WebDAV PUT | Full property write-back via frontmatter diff | Phase 56 | WebDAV becomes a true editing surface, not just body editing |
| Static SPARQL scope per collection | User-defined scope via saved queries | Phase 56 | Mounts can filter by any SPARQL-expressible condition |

**Current state of codebase:**
- VFS writes only support body changes (via `body.set` command)
- Frontmatter is rendered but not parsed back on write (silently ignored)
- Root collection only shows model directories
- No user-configurable VFS organization

## Open Questions

1. **SHACL shape sync access pattern**
   - What we know: ShapesService uses async TriplestoreClient; VFS needs sync access. SHACL shapes change rarely (only on model install/update).
   - What's unclear: Whether to create a parallel `SyncShapesService` or cache shape data in a module-level dict invalidated on model events.
   - Recommendation: Cache shapes in a module-level `TTLCache(maxsize=32, ttl=300)` keyed by type IRI. Populate via `SyncTriplestoreClient` CONSTRUCT query (same pattern as async version). 5-minute TTL is acceptable since shapes only change on model operations.

2. **Mount definition CRUD: who can create shared mounts?**
   - What we know: CONTEXT.md says "shared (owner-created, visible to all users) and personal (user-created, visible only to creator)".
   - What's unclear: Can members create shared mounts, or only owners?
   - Recommendation: Only owners can create shared mounts. Members can create personal mounts only. This follows the existing role model (owners have full control, members have scoped access).

3. **Preview endpoint performance for large object sets**
   - What we know: Live preview requires querying objects and building the directory tree.
   - What's unclear: Performance for mounts scoping thousands of objects.
   - Recommendation: Cap preview at first 100 objects per folder. Show "(and N more...)" indicator. This keeps preview response times under 2 seconds.

4. **Body property detection in mounted files**
   - What we know: Current ResourceFile uses a heuristic (predicate local name == "body") to separate body from frontmatter.
   - What's unclear: Whether all Mental Models use a `:body` predicate, or if this varies.
   - Recommendation: Check SHACL shapes for the body property. If no explicit body property is found, use the existing heuristic (`pred_local == "body"`). Fall back to empty body if none found.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (E2E) + pytest (if backend unit tests exist) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test tests/vfs-webdav.spec.ts --project=chromium` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VFS-01 | MountSpec RDF vocab creates valid mount definition in triplestore | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount definition" --project=chromium` | No -- Wave 0 |
| VFS-02 | Creating mount with each of 5 strategies produces correct directory structure via WebDAV | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount strategy" --project=chromium` | No -- Wave 0 |
| VFS-03 | WebDAV PROPFIND on mount path prefix returns correct children | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount dispatch" --project=chromium` | No -- Wave 0 |
| VFS-04 | PUT with modified frontmatter updates RDF properties | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "frontmatter write" --project=chromium` | No -- Wave 0 |
| VFS-05 | Settings UI creates/edits/deletes mounts | e2e | `cd e2e && npx playwright test tests/06-settings/vfs-mounts.spec.ts --project=chromium` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd e2e && npx playwright test tests/vfs-webdav.spec.ts --project=chromium`
- **Per wave merge:** `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Extend `e2e/tests/vfs-webdav.spec.ts` with mount strategy tests
- [ ] Create `e2e/tests/06-settings/vfs-mounts.spec.ts` for settings UI tests
- [ ] No backend unit test framework exists -- E2E tests via Playwright API requests cover the integration layer

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/vfs/` -- provider.py, collections.py, resources.py, write.py, cache.py (direct code reading)
- Existing codebase: `backend/app/commands/handlers/object_patch.py` -- property patch handler
- Existing codebase: `backend/app/services/shapes.py` -- SHACL shape extraction service
- Existing codebase: `backend/app/sparql/models.py` -- SavedSparqlQuery ORM model
- `.planning/research/virtual-filesystem.md` -- MountSpec vocabulary draft and prior art survey
- `.planning/phases/56-vfs-mountspec/56-CONTEXT.md` -- locked decisions and constraints

### Secondary (MEDIUM confidence)
- [WsgiDAV Custom Providers](https://wsgidav.readthedocs.io/en/latest/user_guide_custom_providers.html) -- DAVProvider/DAVCollection extension patterns
- [WsgiDAV Virtual Provider Example](https://wsgidav.readthedocs.io/en/latest/addons-virtual.html) -- Virtual directory strategy reference
- [python-frontmatter docs](https://python-frontmatter.readthedocs.io/) -- loads/dumps/dict-like API
- [python-frontmatter handlers](https://python-frontmatter.readthedocs.io/en/latest/handlers.html) -- YAML round-trip customization

### Tertiary (LOW confidence)
- None -- all findings verified against codebase and official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project; no new dependencies
- Architecture: HIGH -- patterns directly extend existing VFS module with minimal refactoring
- Pitfalls: HIGH -- identified from direct code analysis of sync/async boundaries, caching, path dispatch
- Validation: MEDIUM -- E2E test patterns established but VFS mount tests need to be written

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- no external dependency changes expected)
