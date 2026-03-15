# S08: VFS v2 Design Refinement — Research

**Date:** 2026-03-14  
**Status:** Researched, ready for planning

## Summary

This slice refines the existing VFS v2 design draft (`.gsd/design/VFS-V2-DESIGN.md`, dated 2026-03-13) against the **current codebase state** — in particular the completed S01 (Query SQL→RDF) migration and the S07 Views Rethink design doc. The existing draft is well-structured and identifies 6 features in priority order. Most of the draft's proposals are sound, but two critical areas need refinement:

1. **Saved query as scope is dead-wired.** The `saved_query_id` field exists on `MountDefinition`, is stored in RDF, and the UI even lists saved queries in a dropdown — but `build_scope_filter()` in `strategies.py` ignores it completely. The S01 migration to RDF means queries now have stable IRIs (`urn:sempkm:query:{uuid}`), but the WebDAV provider runs in sync WSGI threads (`SyncTriplestoreClient`) while `QueryService` is async-only (`TriplestoreClient`). This is the main technical gap.

2. **The bidirectional path contract** (how WebDAV paths map to/from RDF objects) is implicit and fragile. Filenames are derived from slugified labels with hash dedup, but there's no reverse index. The `_resolve_type_iri_from_label()` and `_resolve_group_value()` methods in `mount_collections.py` already do expensive reverse-lookup SPARQL on every folder access. This pattern won't scale to strategy chains where the path depth increases.

The refinement should: (a) wire `saved_query_id` through `build_scope_filter()` using the sync client, (b) formalize the prefix model for `sempkm:scopeQuery` alignment with the Views Rethink, (c) prioritize the 6 features with realistic effort estimates based on current code, and (d) document the path↔IRI contract explicitly.

## Recommendation

Update `.gsd/design/VFS-V2-DESIGN.md` with the following refinements:

### Priority 1: Wire `saved_query_id` → `build_scope_filter()` (Low effort, high impact)
The existing S01 `QueryService` is async-only. The WebDAV provider uses `SyncTriplestoreClient`. Two approaches:
- **Option A (recommended):** Add a direct SPARQL query in `build_scope_filter()` that reads the query text from `urn:sempkm:queries` graph using `SyncTriplestoreClient`, bypassing `QueryService` entirely. The query is simple: `SELECT ?text FROM <urn:sempkm:queries> WHERE { <urn:sempkm:query:{id}> <urn:sempkm:vocab:queryText> ?text }`. This avoids async/sync bridging.
- **Option B:** Add sync methods to `QueryService` (duplicates async methods with sync client). Rejected: doubles the surface area for minimal gain.

The retrieved query text is wrapped as a sub-select scope filter, exactly as the current draft proposes.

### Priority 2: Type filter (Low effort, high impact)
Add `sempkm:typeFilter` predicate to `MountSpec` — list of type IRIs. Extend `build_scope_filter()` to inject `?iri a ?filterType . VALUES ?filterType { <t1> <t2> }`. Straightforward. The mount form UI needs a multi-select populated from `ShapesService` types (same data as the Views Rethink type filter pills).

### Priority 3: Document the path↔IRI contract (Low effort, medium impact)  
Currently implicit in `_build_file_map_from_bindings()` and `_slugify()`. Document:
- Forward (IRI→path): `slugify(label) + optional --{sha256(iri)[:6]}` dedup
- Reverse (path→IRI): filename → file_map lookup (cached per folder)  
- Key constraint: filenames are NOT stable if object labels change
- For write support (future): a persistent `filename→IRI` index would be needed

### Priority 4: Composable strategies (Medium effort, medium impact)
The draft proposes chain vs nested — chain is simpler. Key finding: `StrategyFolderCollection` already has `parent_folder_value` for by-date's year→month nesting. Generalizing this to arbitrary chains means each level's `get_member()` creates a sub-`StrategyFolderCollection` with a narrowed scope (the parent's objects become the child's input set). Max depth of 3 is wise — WebDAV path depth of 6+ segments causes client compatibility issues.

### Priority 5: Preview tree (Low-medium effort, medium impact)
The existing flat `directories` array in `preview_mount()` is adequate for single-level strategies. For chains, the response schema needs to be nested (the draft's JSON tree is right).

### Priority 6: File naming templates (Low effort, low impact)  
Simple template expansion in `_build_file_map_from_bindings()`. Deferred.

### Write support: Confirmed defer
The write path already works for body and frontmatter property changes via `MountedResourceFile.end_write()`. True bidirectional (new file creation, file deletion) requires an IRI minting policy and event store integration that belongs in a dedicated milestone.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Saved query text retrieval (sync context) | Direct SPARQL SELECT against `urn:sempkm:queries` graph | `QueryService` is async-only; direct SPARQL avoids sync/async bridging and uses the same `SyncTriplestoreClient` already in `build_scope_filter()` |
| Type IRI discovery for filter | `ShapesService` target class list | Already queries all model shapes graphs; reuse for mount form multi-select |
| Scope filter injection pattern | `build_scope_filter()` sub-select wrapping | Existing pattern works — extend, don't replace |
| File map deduplication | `_build_file_map_from_bindings()` sha256 suffix | Already handles slug collisions; reuse for filename templates |
| View-to-query binding pattern | `sempkm:scopeQuery` from Views Rethink (D096) | VFS `saved_query_id` and Views `scopeQuery` should reference queries by the same IRI pattern |

## Existing Code and Patterns

- `backend/app/vfs/strategies.py` — `build_scope_filter()` at line 45: **only reads `sparql_scope`**, completely ignores `saved_query_id`. This is the primary gap to document fixing. Mount definition is passed but `mount.saved_query_id` is never accessed.
- `backend/app/vfs/mount_service.py` — `MountDefinition` dataclass at line 50: has `saved_query_id` field, stored as `sempkm:savedQueryId` triple in `urn:sempkm:mounts` graph. The field is fully plumbed through CRUD but never consumed.
- `backend/app/vfs/mount_collections.py` — `MountRootCollection` and `StrategyFolderCollection`: both call `build_scope_filter(mount)` at init time but `mount.saved_query_id` is silently dropped. `StrategyFolderCollection` has `parent_folder_value` for by-date nesting — this is the hook for generalizing to strategy chains.
- `backend/app/vfs/mount_resource.py` — `MountedResourceFile`: full write support for body and frontmatter via `end_write()`. Uses `_frontmatter_to_rdf_properties()` diff. Already functional — no changes needed for v2 read-side features.
- `backend/app/vfs/provider.py` — `SemPKMDAVProvider._resolve_mount_path()`: hardcoded 4-segment max depth (parts 0-3). Strategy chains deeper than 3 levels would need this extended.
- `backend/app/sparql/query_service.py` — `QueryService.get_query()` at line 183: async-only, returns `SavedQueryData` with `query_text` field. Not usable from sync WebDAV context. Direct SPARQL against the graph is the right approach.
- `frontend/static/js/workspace.js` — Mount form at line 2843: `initMountForm()` already loads saved queries via `GET /api/sparql/queries` and populates scope dropdown with `query:{id}` values. The `collectFormData()` at line 2999 correctly sets `saved_query_id` from `query:` prefix scope values. **UI is done; only the backend consumption is missing.**
- `backend/app/vfs/mount_router.py` — Preview endpoint at line 495: line 507 has a telling comment: "For preview, we just use all objects (full scope query execution would require loading the saved query text from SQLite)" — this was written pre-S01 when queries were in SQL. Now they're in RDF, preview can resolve them.
- `.gsd/design/VIEWS-RETHINK.md` — Views Rethink uses `sempkm:scopeQuery` to link views to saved queries by IRI. VFS should use the same query IRI pattern (`urn:sempkm:query:{uuid}`) for consistency. Currently stores bare UUID in `saved_query_id`; should store full IRI or at least construct it the same way.

## Constraints

- **WebDAV runs in sync WSGI threads** — `SyncTriplestoreClient` only; cannot call async `QueryService` methods. Any new query resolution must use sync SPARQL.
- **`build_scope_filter()` is called on every collection init** — must stay fast (single SPARQL query or cached). TTL cache from `cache.py` (30s) could be applied to query text resolution.
- **Provider path dispatch is hardcoded to 4 segments** — `_resolve_mount_path()` handles `len(parts)` 1-4. Strategy chains adding depth would need extension here.
- **Query IRIs use `urn:sempkm:query:{uuid}` pattern** (S01 Forward Intelligence) — VFS should reference queries by this IRI, not bare UUID. Current `saved_query_id` stores a bare UUID string. The design doc should specify whether to store the full IRI or construct it.
- **Model-shipped queries use `sempkm:source` predicate** — they're read-only. VFS scoping to model queries should work (scope is just the query text, source doesn't matter).
- **`_escape()` in strategies.py uses double quotes** for SPARQL literals, while `QueryService` uses single quotes via `_esc()`. No conflict since they operate in different query contexts, but consistency is worth noting.

## Common Pitfalls

- **Async/sync mismatch** — The biggest gotcha. `QueryService` is async, WebDAV context is sync. Do NOT try `asyncio.run()` for query text resolution (the event loop may or may not be running depending on threading). Use direct SPARQL with `SyncTriplestoreClient` instead.
- **Preview endpoint ignores scope for saved queries** — `mount_router.py` line 507 explicitly comments that scope queries aren't resolved during preview. This means users set up a mount with query scope but preview shows all objects — confusing UX. Fix this in v2.
- **Filename instability on label change** — If an object's `dcterms:title` changes, its slugified filename changes. Any WebDAV client with bookmarks/symlinks to the old path breaks. Strategy chain paths are even more fragile (folder names derived from property values). The design doc should acknowledge this and recommend the persistent filename index for the write-support milestone.
- **Type filter vs scope query composition** — The draft asks "should type_filter and saved_query_id compose (AND) or be exclusive?" Answer: AND. Both narrow the result set. `type_filter` adds a `?iri a <typeIri>` clause; `saved_query_id` adds a sub-select scope. They compose naturally as additional WHERE clauses.
- **Strategy chain UI complexity** — A multi-level strategy chain builder (drag-and-drop strategy reordering) is significantly more complex than the simple dropdown. The "+" button approach from the draft is fine for v1 with a max of 3 levels. Predefined combos ("By Tag then By Date") would reduce cognitive load.

## Open Risks

- **Query text injection in scope filter** — `build_scope_filter()` wraps `sparql_scope` as `{ SELECT ?iri WHERE { <raw_query_text> } }`. If the saved query's text contains `INSERT` or `DELETE`, it would be wrapped in a SELECT which neutralizes write operations. But malformed SPARQL could still cause parser errors. The existing `scope_to_current_graph()` and `check_member_query_safety()` guards in `sparql/client.py` should be applied to scope queries too.
- **Cache invalidation for query-scoped mounts** — If a saved query's text is updated via the SPARQL console, mounts using that query as scope won't reflect the change until the cache expires (30s from `cache.py`). Acceptable for TTL cache, but worth documenting.
- **Strategy chain SPARQL complexity** — A 3-level chain (e.g., by-tag → by-date → flat) requires nested sub-selects or multiple sequential queries. RDF4J handles sub-selects well, but each level adds latency. Performance testing with real Ideaverse data (895 objects) would be needed.
- **Model query scope uniqueness** — Model-shipped queries have IRIs like `urn:sempkm:model:basic-pkm:query:active-projects` (different IRI pattern than user queries). If `saved_query_id` stores a UUID, it can't reference model queries. The design should specify how model query IRIs are handled — either extend `saved_query_id` to accept full IRIs, or add a separate `sempkm:scopeQueryIRI` predicate matching the Views Rethink `sempkm:scopeQuery`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| WebDAV | salesforcecommercecloud/b2c-developer-tooling@b2c-webdav | Not relevant (Salesforce-specific) |
| wsgidav | — | None found |
| RDF/SPARQL | — | None found |

No applicable professional agent skills were found for the core technologies in this slice. The codebase has well-established patterns for WebDAV, SPARQL, and mount management.

## Sources

- Existing VFS v2 design draft (`.gsd/design/VFS-V2-DESIGN.md`) — 6 features with priority order, existing as of 2026-03-13
- S01 Forward Intelligence — `QueryService` available via `get_query_service`, model queries use `sempkm:source`, `urn:sempkm:queries` graph holds all data
- S07 Views Rethink (`.gsd/design/VIEWS-RETHINK.md`) — `sempkm:scopeQuery` predicate for view-to-query binding, generic views with type filter pills
- D093–D097 — Views rethink decisions (generic views in-memory, SHACL columns, type filter pills, scopeQuery semantics, 3-phase migration)
- Codebase exploration — `strategies.py`, `mount_service.py`, `mount_collections.py`, `mount_resource.py`, `provider.py`, `mount_router.py`, `query_service.py`, `workspace.js`
