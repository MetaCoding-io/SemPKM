# VFS Mount Spec v2 — Design & Implementation Guide

> Status: **Revised**
> Original Date: 2026-03-13
> Revision Date: 2026-03-14
> Depends on: S01 (Query SQL→RDF), S07 (Views Rethink)

---

## Current State (v1)

Each mount has:
- **One strategy** — `flat | by-type | by-date | by-tag | by-property`
- **One scope** — `"all"` or a raw SPARQL WHERE fragment (`sparql_scope`)
- **saved_query_id** — stored in RDF but not consumed by `build_scope_filter()`
- Strategy produces 1 level of folders (except `by-date` → year/month)

**What works well:**
- Simple mental model: pick a strategy, get a folder structure
- WebDAV clients see it immediately
- Scope filtering via raw SPARQL is powerful for advanced users
- Full CRUD for mounts with `saved_query_id` plumbed through storage

**What's missing:**
- `saved_query_id` is dead-wired: UI sets it, RDF stores it, `build_scope_filter()` ignores it
- No way to compose strategies (e.g. by-tag → by-date within each tag)
- No way to filter to "just my Notes tagged #project-x" without writing SPARQL
- Mount preview is flat and skips saved query resolution entirely
- Path↔IRI contract is implicit — no documented forward/reverse mapping
- Query IRI pattern diverges from Views Rethink `sempkm:scopeQuery`

---

## Proposed Changes

### 1. Saved Query as Scope Source

**Problem:** `saved_query_id` is stored on the mount definition (`MountDefinition.saved_query_id` in `mount_service.py`) and the UI correctly sets it (the mount form scope dropdown lists saved queries, and `collectFormData()` in `workspace.js` populates `saved_query_id` from `query:` prefix scope values). However, `build_scope_filter()` at `strategies.py:51` only reads `mount.sparql_scope` — it completely ignores `mount.saved_query_id`. The field is dead.

**The Gap (Current Code):**

```python
# strategies.py:45-56 — build_scope_filter()
def build_scope_filter(mount: MountDefinition) -> str:
    if not mount.sparql_scope or mount.sparql_scope == "all":
        return ""
    # Treats sparql_scope as WHERE clause fragment — saved_query_id is never checked
    return f"{{ SELECT ?iri WHERE {{ {mount.sparql_scope} }} }}"
```

**Fix Approach — Direct SPARQL via SyncTriplestoreClient:**

The `QueryService` (`query_service.py`) is async-only — it uses `TriplestoreClient` (async). The WebDAV provider runs in sync WSGI threads and only has `SyncTriplestoreClient`. Calling `asyncio.run()` from WebDAV threads is unsafe (the event loop may or may not be running depending on threading context).

The fix is a direct SPARQL SELECT against the `urn:sempkm:queries` graph using the `SyncTriplestoreClient` already available in `build_scope_filter()`'s call chain:

```sparql
SELECT ?text FROM <urn:sempkm:queries>
WHERE {
  <urn:sempkm:query:{id}> <urn:sempkm:vocab:queryText> ?text
}
```

This retrieves the saved query's SPARQL text, which is then wrapped as a sub-select scope filter — the same pattern `build_scope_filter()` already uses for raw `sparql_scope`.

**Revised `build_scope_filter()`:**

```python
def build_scope_filter(
    mount: MountDefinition,
    sync_client: SyncTriplestoreClient,
) -> str:
    """Build a SPARQL scope filter fragment from mount definition.

    Priority: saved_query_id (resolved from RDF) > sparql_scope > no filter.
    Both saved_query_id and sparql_scope filters compose with type_filter via AND.
    """
    scope_text = None

    # 1. Resolve saved query text if saved_query_id is set
    if mount.saved_query_id:
        query_text = _resolve_query_text(mount.saved_query_id, sync_client)
        if query_text:
            scope_text = query_text

    # 2. Fall back to raw sparql_scope
    if not scope_text and mount.sparql_scope and mount.sparql_scope != "all":
        scope_text = mount.sparql_scope

    if not scope_text:
        return ""

    return f"{{ SELECT ?iri WHERE {{ {scope_text} }} }}"
```

**Cache Strategy:**

`build_scope_filter()` is called on every WebDAV collection init (every directory listing request). Query text resolution must be cached to avoid repeated SPARQL SELECTs.

Use `TTLCache` from `cache.py` (already imported in mount collections, 30s TTL, thread-safe with `_cache_lock`):

```python
from app.vfs.cache import listing_cache, _cache_lock

def _resolve_query_text(
    saved_query_id: str,
    sync_client: SyncTriplestoreClient,
) -> str | None:
    """Resolve saved query text from RDF, with 30s TTL cache."""
    cache_key = f"query_text:{saved_query_id}"
    with _cache_lock:
        if cache_key in listing_cache:
            return listing_cache[cache_key]

    # Construct the query IRI
    if saved_query_id.startswith("urn:"):
        query_iri = saved_query_id
    else:
        query_iri = f"urn:sempkm:query:{saved_query_id}"

    result = sync_client.query(
        f'SELECT ?text FROM <urn:sempkm:queries> '
        f'WHERE {{ <{query_iri}> <urn:sempkm:vocab:queryText> ?text }}'
    )

    bindings = result.get("results", {}).get("bindings", [])
    text = bindings[0]["text"]["value"] if bindings else None

    with _cache_lock:
        listing_cache[cache_key] = text

    return text
```

**Signature Change:** `build_scope_filter()` gains a `sync_client` parameter. Callers (`MountRootCollection`, `StrategyFolderCollection`) already have `self._client` (a `SyncTriplestoreClient`).

**Preview Endpoint Update:** The comment at `mount_router.py:509` says "full scope query execution would require loading the saved query text from SQLite" — this is now stale. Post-S01, queries live in RDF (`urn:sempkm:queries` graph). The preview endpoint can resolve saved queries using the async `TriplestoreClient` (preview runs in async FastAPI context, not WSGI). Update the preview to actually resolve and apply saved query scope.

**Complexity:** Low — wiring existing fields, no schema change. ~50 lines of new code in `strategies.py` + callers pass `sync_client`.

### 2. Type Filter (No SPARQL Required)

**Problem:** Filtering to "just Notes" or "just Notes + Concepts" requires writing `?iri a <urn:...Note>` in raw SPARQL. Most users won't do this.

**Design:** Add a `sempkm:typeFilter` predicate on `MountSpec` — a list of type IRIs. If set, only objects of those types appear in the mount.

```json
{
  "type_filter": ["urn:example:Note", "urn:example:Concept"],
  "strategy": "by-tag"
}
```

**UI Population:** The type list is populated from `ShapesService` target class list — the same data source as the Views Rethink type filter pills. This reuses existing infrastructure.

**Composition with Saved Query Scope (AND, Not Exclusive):**

`type_filter` and `saved_query_id` compose via AND — both narrow the result set. They are additional WHERE clauses, not alternatives:

```sparql
-- type_filter adds this clause to build_scope_filter():
?iri a ?filterType .
VALUES ?filterType { <urn:example:Note> <urn:example:Concept> }
```

If both `type_filter` and `saved_query_id` are set, the object must match the saved query's scope AND be one of the filtered types. This is the natural SPARQL composition.

**Implementation in `build_scope_filter()`:**

```python
def build_scope_filter(mount, sync_client) -> str:
    parts = []

    # Saved query / sparql_scope sub-select (as above)
    if scope_text:
        parts.append(f"{{ SELECT ?iri WHERE {{ {scope_text} }} }}")

    # Type filter VALUES clause
    if mount.type_filter:
        iris = " ".join(f"<{t}>" for t in mount.type_filter)
        parts.append(f"?iri a ?filterType . VALUES ?filterType {{ {iris} }}")

    return "\n".join(parts)
```

**Complexity:** Low — add field to `MountDefinition`, extend `build_scope_filter()`, add multi-select to mount form UI.

### 3. Composable Strategy Chains (Multi-Level Folders)

**Problem:** Users want `by-tag/by-date` or `by-type/flat` hierarchies. Currently stuck with one level.

**Decision: Chain Model (Option A) over Nested (Option B).**

Chain (flat list) is simpler to serialize, validate, and build UI for:

```json
{
  "strategy": ["by-tag", "by-date"],
  "group_by_property": "urn:sempkm:tag",
  "date_property": "http://purl.org/dc/terms/created"
}
```

Produces: `/mount/machine-learning/2025/03-March/my-note.md`

**Max depth: 3 levels enforced.** WebDAV clients struggle with deep paths. Combined with the mount prefix, this yields max 6 path segments — within the `provider.py` dispatch capacity (with extension; see below).

**Implementation Hook — `parent_folder_value`:**

`StrategyFolderCollection` already has `parent_folder_value` for `by-date`'s year→month nesting. This is the generalization hook — each level in the chain narrows the object set. The pattern:

1. Level 0 (root): full scope, first strategy groups objects → folders
2. Level 1: each folder filters to its group's objects, second strategy sub-groups → sub-folders
3. Level 2 (terminal): each sub-folder's objects rendered as files

The `strategy` field becomes `str | list[str]` (backward compatible: single string = current behavior, list = chain).

**Provider Path Extension:**

`provider.py:_resolve_mount_path()` currently handles max 4 segments (`len(parts)` 1–4). Strategy chains deeper than 1 level produce paths like `/prefix/tag/year/month/file.md` (5 segments). The path dispatch needs extension to handle up to 6 segments for 3-level chains:

```
len(parts) == 5: /prefix/L1/L2/file.md  — 2-level chain file
len(parts) == 6: /prefix/L1/L2/L3/file.md — 3-level chain file (max)
```

Each additional level instantiates a nested `StrategyFolderCollection` with the parent's folder value constraining the scope.

**Strategy Chain Repeats:**

Yes, repeats are allowed with different properties at each level. Example: `["by-property", "by-property"]` with `status` at level 0 and `priority` at level 1. Each level needs its own property configuration — the chain config becomes:

```json
{
  "strategy": [
    { "type": "by-property", "property": "urn:sempkm:vocab:status" },
    { "type": "by-property", "property": "urn:sempkm:vocab:priority" }
  ]
}
```

**UI Recommendation:**

- "+" button to add levels (max 3)
- Predefined combos for common patterns: "By Tag then By Date", "By Type then By Tag"
- Each level shows a strategy dropdown + property config (if applicable)
- Cognitive load reduction: predefined combos avoid the need to understand chain composition

**Complexity:** Medium — requires generalized folder nesting in WebDAV collections + provider path extension + UI for chain building.

### 4. Bidirectional Path Contract

**Problem:** The mapping between WebDAV paths and RDF object IRIs is implicit, scattered across `_build_file_map_from_bindings()`, `_slugify()`, and the `file_map` dicts in `MountRootCollection` and `StrategyFolderCollection`. It's undocumented and has known fragility.

**Forward Mapping (IRI → Path):**

`_build_file_map_from_bindings()` in `mount_collections.py` converts SPARQL query results to WebDAV filenames:

1. `_slugify(label)` → lowercase, replace non-alphanum with hyphens, collapse runs, strip trailing
2. If slug collision occurs (two objects with same label), append `--{sha256(iri)[:6]}` dedup suffix
3. Append `.md` extension

Example: `<urn:example:my-great-note>` with label "My Great Note" → `my-great-note.md`
Collision: two "My Great Note" objects → `my-great-note--a1b2c3.md`, `my-great-note--d4e5f6.md`

**Reverse Mapping (Path → IRI):**

Filename → IRI resolution uses `file_map` dict lookup, built per-folder:
- `MountRootCollection._flat_file_map` — flat strategy file map
- `StrategyFolderCollection._file_map` — per-folder file map

Both are built on first access and cached for the lifetime of the collection instance. The `file_map` stores `{filename: {"iri": iri, "label": label, "typeIri": typeIri}}`.

**Key Constraint — Filename Instability:**

Filenames are derived from `dcterms:title` (or fallback label predicates). If an object's title changes, its slugified filename changes. This breaks:
- WebDAV client bookmarks/symlinks to the old path
- Any external tool referencing the file by path
- Strategy chain folder names (derived from property values like tag labels)

**Recommendation for Write-Support Milestone:**

A persistent `filename→IRI` index is needed before write support can be robust. Options:
- RDF-based: `sempkm:vfsFilename` predicate on the object → stable across label changes
- In-memory index with TTL: cheaper but loses stability across restarts
- The write-support milestone should design this index as part of its scope

### 5. Query IRI Alignment

**Problem:** VFS stores `saved_query_id` as a bare UUID string, while S01's `QueryService` uses `urn:sempkm:query:{uuid}` IRIs and the Views Rethink (D096) uses `sempkm:scopeQuery` to link views to queries by full IRI. These patterns should converge.

**Current State:**

| System | Predicate | Value Format | Example |
|--------|-----------|-------------|---------|
| VFS Mount | `sempkm:savedQueryId` | Bare UUID string | `"abc-123"` |
| QueryService (S01) | — | Full IRI | `urn:sempkm:query:abc-123` |
| Views Rethink (D096) | `sempkm:scopeQuery` | Full IRI | `<urn:sempkm:query:abc-123>` |
| Model queries | — | Full IRI (different pattern) | `urn:sempkm:model:basic-pkm:query:active-projects` |

**Recommendation — Adopt `sempkm:scopeQuery` with Full IRI:**

1. **Rename predicate:** `sempkm:savedQueryId` → `sempkm:scopeQuery` — aligns with Views Rethink D096
2. **Store full IRI, not bare UUID:** `<urn:sempkm:query:abc-123>` instead of `"abc-123"`
3. **Accept both patterns:** `scopeQuery` should accept user query IRIs (`urn:sempkm:query:{uuid}`) and model query IRIs (`urn:sempkm:model:{id}:query:{name}`)
4. **Resolution is pattern-agnostic:** `_resolve_query_text()` looks up query text from `urn:sempkm:queries` graph regardless of IRI pattern — both user and model queries are stored there

**Migration:**

Existing mounts with `sempkm:savedQueryId` values need:
1. Delete `sempkm:savedQueryId` triples from `urn:sempkm:mounts` graph
2. Insert `sempkm:scopeQuery` triples with `urn:sempkm:query:` prefix prepended to bare UUID values
3. This is a simple SPARQL UPDATE — no mount behavior changes

**Relationship to Views Rethink:**

`sempkm:fromQuery` (provenance: which query created this view) is distinct from `sempkm:scopeQuery` (runtime: which query limits results). VFS uses `scopeQuery` semantics — the query actively filters mount contents at runtime.

### 6. Preview Improvements

**Problem:** Current preview returns a flat `directories` array. For strategy chains, the response schema needs to be nested. More importantly, the preview endpoint currently skips saved query resolution entirely.

**Stale Comment — Now Fixable:**

`mount_router.py:509` contains:
```python
# For preview, we just use all objects (full scope query execution
# would require loading the saved query text from SQLite)
```

Post-S01, queries are in RDF (`urn:sempkm:queries` graph). The preview endpoint runs in async FastAPI context and has `TriplestoreClient` — it can resolve saved query text directly. This comment should be removed and the preview should honor saved query scope.

**Tree Response Schema:**

For strategy chains, return a nested tree with file counts per folder:

```json
{
  "tree": [
    {"name": "machine-learning", "count": 42, "children": [
      {"name": "2025", "count": 15, "children": [
        {"name": "03-March", "count": 8}
      ]}
    ]}
  ],
  "total_files": 120,
  "truncated": false
}
```

**Complexity:** Low-medium — reuse existing strategy queries with COUNT. The main change is resolving saved query scope in the async context.

### 7. File Naming Control

**Problem:** Filenames are always `slugified-title.md`. Some users might want date-prefixed names, type-prefixed names, or custom patterns.

**Design:** Add optional `filename_template` field:
- `"{title}"` (default) → `my-great-note.md`
- `"{date}-{title}"` → `2025-03-13-my-great-note.md`
- `"{type}-{title}"` → `note-my-great-note.md`

Available variables: `{title}`, `{date}`, `{type}`, `{id}` (IRI hash)

**Implementation:** Template expansion in `_build_file_map_from_bindings()`. The dedup suffix still applies after template expansion.

**Complexity:** Low — template expansion in existing function.

### 8. Write Support (Future — Separate Milestone)

**Status: Confirmed deferred.** The write path already works for body and frontmatter property changes via `MountedResourceFile.end_write()`. True bidirectional (new file creation, file deletion) requires:

- IRI minting policy (what type? which graph? what default properties?)
- Persistent `filename→IRI` index (see Bidirectional Path Contract)
- Conflict resolution (object edited in browser and via WebDAV)
- Event store integration for change propagation

The read-only projection is already very useful for Obsidian/VS Code integration. Write support has complex edge cases that deserve a dedicated milestone.

---

## Priority Table

| # | Feature | Effort | Impact | Depends On | Notes |
|---|---------|--------|--------|------------|-------|
| 1 | Saved query as scope | Low (~50 LOC) | High | — | Wire `build_scope_filter()` to resolve `saved_query_id` via direct SPARQL + TTLCache. `sync_client` already available in callers. |
| 2 | Type filter | Low (~40 LOC) | High | — | `sempkm:typeFilter` on MountSpec, `VALUES` clause in `build_scope_filter()`. UI from `ShapesService`. |
| 3 | Query IRI alignment | Low (~30 LOC) | Medium | #1 | Rename predicate, store full IRI. Migration is a simple SPARQL UPDATE. |
| 4 | Preview fix | Low (~20 LOC) | Medium | #1 | Remove stale SQL comment, resolve saved queries in async context. |
| 5 | Path contract docs | None (doc only) | Medium | — | Already implemented — just needs documentation and test coverage. |
| 6 | Composable strategies | Medium (~200 LOC) | Medium | — | Chain model, `parent_folder_value` generalization, provider path extension. |
| 7 | Filename templates | Low (~30 LOC) | Low | — | Template expansion in `_build_file_map_from_bindings()`. |
| 8 | Write support | High (~500+ LOC) | High | Separate milestone | Needs IRI minting, persistent index, conflict resolution. |

Items 1–4 are quick wins: ~140 lines total, dramatically improve usability. Item 6 is the main architectural change. Item 8 is deferred.

**Sync/Async Constraint Note:** Items 1–3 execute in sync WSGI context (`SyncTriplestoreClient`). The preview fix (item 4) runs in async FastAPI context (`TriplestoreClient`). Do NOT use `asyncio.run()` or `QueryService` from WebDAV threads.

---

## Open Questions (Resolved)

### Q1: Should strategy chains allow repeats?

**Answer: Yes**, with different properties at each level. Example: `["by-property", "by-property"]` with `status` at level 0 and `priority` at level 1. The chain config uses per-level objects instead of bare strings to carry property configuration.

**Rationale:** The underlying SPARQL composition works naturally — each level just adds another GROUP BY / filter. The restriction to different strategies would be arbitrary and limit legitimate use cases.

### Q2: Should `type_filter` and `saved_query_id` compose (AND) or be mutually exclusive?

**Answer: AND** — both narrow the result set. `type_filter` adds a `VALUES ?filterType` clause, `saved_query_id` adds a sub-select scope. They compose as additional WHERE clauses in `build_scope_filter()`.

**Rationale:** AND composition is the natural SPARQL behavior. An OR semantic would require UNION and be harder to reason about. Users expect "Notes from my Project X query" to mean both constraints apply.

### Q3: For strategy chains, does the UI show a "+" to add levels, or predefined combos?

**Answer: Both.** A "+" button to add levels (max 3) for power users, plus predefined combos ("By Tag then By Date", "By Type then By Tag") for cognitive-load reduction.

**Rationale:** Predefined combos serve the 80% case — most users want common patterns. The "+" button serves the 20% who need custom chains. Max 3 levels keeps the UI manageable and WebDAV paths sane.

### Q4: Should mounts support an "auto-refresh" interval or always use cache invalidation?

**Answer: Defer.** Use existing TTL cache (30s from `cache.py`). Event-bus integration is a separate concern.

**Rationale:** The current TTLCache (30s, 256 entries, thread-safe with `_cache_lock`) is adequate for read-heavy WebDAV workloads. An event bus for real-time invalidation adds complexity (subscription management, cross-thread signaling) without proportional UX benefit — users tolerate 30s staleness in file explorers. Revisit when write support is implemented.

---

## Constraints & Risks

### Async/Sync Mismatch

The WebDAV provider runs in sync WSGI threads. `SyncTriplestoreClient` is the only available client. `QueryService` is async-only — do NOT use `asyncio.run()` to call it from WebDAV context. The event loop may or may not be running depending on threading, making `asyncio.run()` unreliable. All query text resolution in `build_scope_filter()` must use direct SPARQL via `SyncTriplestoreClient`.

### Cache Invalidation Timing

Query text resolution uses TTLCache (30s). If a saved query's text is updated via the SPARQL console, mounts using that query as scope won't reflect the change until the cache expires. This is acceptable for a TTL-based system but should be documented for users.

The `clear_mount_cache()` function in `cache.py` removes mount-related keys. Extend it to also clear `query_text:*` keys when query scope resolution is added.

### SPARQL Injection Safety

`build_scope_filter()` wraps scope text as `{ SELECT ?iri WHERE { <text> } }`. If the saved query contains `INSERT` or `DELETE`, wrapping it in a SELECT neutralizes write operations. However, malformed SPARQL could cause parser errors.

Apply `check_member_query_safety()` from `sparql/client.py` (line 64) to scope queries as an additional guard. This function validates that queries don't contain destructive operations.

### Provider Path Depth Limit

`provider.py:_resolve_mount_path()` handles max 4 segments (`len(parts)` 1–4). Strategy chains with 2–3 levels produce paths with 5–6 segments. The path dispatch must be extended to handle `len(parts)` up to 6.

### Filename Instability

Filenames derived from `dcterms:title` change when the title changes. Strategy chain folder names (from property values) have the same fragility. Until a persistent filename index exists (write-support milestone), external tools should not rely on path stability. This is a known limitation of the read-only projection.

### SPARQL Complexity at Chain Depth

A 3-level strategy chain requires multiple sequential SPARQL queries or nested sub-selects. Each level adds latency. Performance testing with real data (895 objects in test Ideaverse) is needed before exposing chains beyond 2 levels.

### Query Escape Consistency

`strategies.py` uses `_escape()` with double quotes for SPARQL literals. `QueryService` uses `_esc()` with single quotes. No conflict since they operate in different query contexts (scope filter vs query CRUD), but be consistent within new code — use the `_escape()` convention in scope filter resolution.
