# Phase 56: VFS MountSpec - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create custom VFS directory structures using declarative mount definitions with multiple organization strategies. MountSpec is an RDF vocabulary that defines how graph data projects onto filesystem trees. The existing model/type/object VFS hierarchy remains; custom mounts appear alongside it. Frontmatter editing writes back to RDF properties via the Command API. A management UI in Settings lets users create, edit, and delete mounts.

</domain>

<decisions>
## Implementation Decisions

### Mount coexistence
- Custom mounts appear alongside the existing model/type/object hierarchy at the WebDAV root — not replacing it
- The existing model directories (basic-pkm/, etc.) are always visible — no hide toggle
- MountSpec definitions stored as RDF in the triplestore (e.g., urn:sempkm:mounts named graph)
- Both shared (owner-created, visible to all users) and personal (user-created, visible only to creator) mounts supported

### Frontmatter write-back
- Only SHACL-declared properties are writable via frontmatter edits — the shape defines the writable boundary
- Edits committed via object.patch through the Command API — full event sourcing, provenance, and validation
- On SHACL validation failure: accept the write and flag as lint warnings (consistent with "SHACL is assistive, not punitive — saves always allowed")
- Relationship properties (object references) shown in frontmatter as label + IRI and are writable:
  ```yaml
  relatedProject:
    label: AI Research
    iri: https://example.org/data/project-ai
  isAbout:
    - label: Neural Networks
      iri: https://example.org/data/concept-nn
  ```

### Mount scope & SPARQL integration
- Mount scope can reference saved SPARQL queries (from Phase 53/54) to filter which objects appear
- Scope dropdown lists: "All objects" (default), all saved queries by name, and "Custom SPARQL..." for inline entry
- This is a key integration point: users can craft a query in the SPARQL console, save it, then use it to define a mount's scope

### Mount config UX
- Inline form in the VFS settings section (same pattern as API token form)
- Fields: mount name, path prefix, strategy dropdown, strategy-specific fields, scope selector
- Strategy-specific fields appear dynamically when strategy is selected:
  - by-tag: "Tag property" dropdown (populated from SHACL shapes)
  - by-property: "Group by" dropdown (populated from SHACL shapes)
  - by-date: "Date field" dropdown (populated from SHACL shapes), year/month granularity
  - by-type: no extra fields (uses rdf:type)
  - flat: no extra fields
- Live preview of the directory structure shown before saving (requires backend preview endpoint)
- Active mounts listed below the form with Edit and Delete actions

### Multi-folder objects
- Objects with multiple values for the grouping property (e.g., multiple tags) appear as duplicate files in each relevant folder
- Both copies are real files with identical content; editing either updates the same RDF object
- ETag-based concurrency across paths — all duplicate files share the same ETag (derived from object IRI). Editing one copy invalidates the other's ETag; stale edits get HTTP 412 Precondition Failed
- by-date strategy uses Year/Month bucketing: `/2024/01-January/`, `/2024/02-February/`
- Objects missing the grouping property go into `_uncategorized/` folder — no objects silently dropped

### Claude's Discretion
- RDF vocabulary term naming and namespace design for MountSpec
- Caching strategy for mounted directory listings
- Preview endpoint implementation details
- How to handle the sync bridge between wsgidav (WSGI/sync) and the async EventStore for property writes
- File naming convention within mounts (slugify strategy, deduplication approach)

</decisions>

<specifics>
## Specific Ideas

- MountSpecs should reference saved SPARQL queries as a scope mechanism — "the SPARQL console is where you craft the query, the mount form is where you apply it as a directory structure"
- The research document (`.planning/research/virtual-filesystem.md`) has a detailed MountSpec vocabulary draft that should inform the RDF vocabulary design
- Research doc's `sempkm:MountSpec` fields (mountPath, targetShape, sparqlScope, directoryStrategy, etc.) are a good starting point

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/vfs/provider.py` — SemPKMDAVProvider with `get_resource_inst()` path dispatch; needs extension for mount path prefixes
- `backend/app/vfs/collections.py` — RootCollection, ModelCollection, TypeCollection; mount strategies would follow the same DAVCollection pattern
- `backend/app/vfs/resources.py` — ResourceFile with frontmatter rendering and body write-back; needs extension for property write-back
- `backend/app/vfs/write.py` — `parse_dav_put_body()` and `write_body_via_event_store()` async bridge; needs extension for property diffing
- `backend/app/vfs/cache.py` — `cached_get_member_names()` TTL cache for directory listings
- `backend/app/templates/browser/_vfs_settings.html` — VFS settings partial with API token management; mount form adds to this section
- SPARQL saved queries model (Phase 53) — `sparql_queries` table with `query_text`, `name`, `description`

### Established Patterns
- VFS uses `SyncTriplestoreClient` (not async) because wsgidav is WSGI — all VFS code runs synchronously
- Body writes bridge sync→async via `asyncio.run()` in a separate thread (wsgidav thread pool)
- Directory listings use SPARQL queries against `urn:sempkm:current` graph
- File names are slugified from labels with hash suffix for deduplication
- SHACL shapes queried from `urn:sempkm:model:{model_id}:shapes` graphs
- Settings page uses htmx partials with inline `<script>` blocks

### Integration Points
- `SemPKMDAVProvider.get_resource_inst()` — path dispatch needs to check mount prefixes before falling through to model/type hierarchy
- `RootCollection.get_member_names()` — needs to include custom mount directories alongside model directories
- Settings page — mount management section goes below existing VFS token section
- Command API `object.patch` handler — used for property write-back (already exists)
- SPARQL saved queries API — mount form scope dropdown queries this

</code_context>

<deferred>
## Deferred Ideas

- Composable/nested strategies (e.g., by-type then by-tag within each type) — future enhancement
- User-defined SPARQL-based directory generators (full DSL) — research doc Phase 3/4
- Non-Markdown file templates (JSON, Turtle) — `fileTemplate` field in research doc
- FUSE transport as alternative to WebDAV — research doc evaluated but deferred

</deferred>

---

*Phase: 56-vfs-mountspec*
*Context gathered: 2026-03-10*
