# S04: Tag System Fix & Tag Explorer — Research

**Date:** 2026-03-12

## Summary

S04 addresses three requirements: TAG-01 (fix comma-separated tag storage), TAG-02 (tag pill rendering), and TAG-03 (by-tag explorer mode). The codebase already has partial tag support: the Obsidian importer writes individual `schema:keywords` triples correctly, the read view already renders `tag-pill` elements for properties with "tags" in the path, and the VFS `strategies.py` module has reusable SPARQL query builders for tag folders and tag-filtered objects.

The core problem is that the basic-pkm model's seed data stores `bpkm:tags` as comma-separated string literals (e.g., `"semantic-web,knowledge-management,rdf"`). These need splitting into individual triples both in the seed data and via a one-time SPARQL migration for existing triplestore data. The by-tag explorer mode is a new `_handle_by_tag` handler replacing the current placeholder, querying across all tag-like properties in the current graph.

The work is medium-risk. The tag splitting logic is straightforward, but there are two tag properties in play (`bpkm:tags` and `schema:keywords`), the by-tag explorer mode must query across both, and the SPARQL migration must handle already-split values idempotently.

## Recommendation

**Approach: Normalize seed data + SPARQL migration + multi-property by-tag explorer.**

1. **Fix seed data at source**: Update `models/basic-pkm/seed/basic-pkm.jsonld` to store tags as JSON-LD arrays of individual strings instead of comma-separated strings. This is the clean fix — new installs get correct data from the start.

2. **Add tag-splitting middleware in `handle_object_patch`**: When a property path matches a known tag pattern (path contains "tags" or is `schema:keywords`), split comma-separated values into individual triples. This covers user edits via the form UI.

3. **One-time SPARQL UPDATE migration**: A management endpoint or startup script that finds all `bpkm:tags` literals containing commas, deletes the comma-separated triple, and inserts individual triples for each tag. Must be idempotent (skip values without commas).

4. **Replace `_handle_by_tag` placeholder**: Query all objects with any tag-like property (`bpkm:tags` or `schema:keywords`), group by tag value, render as expandable tree nodes with counts. Reuse VFS `query_tag_folders` / `query_objects_by_tag` patterns but adapt for multi-property, unscoped queries.

5. **Add tag-children endpoint**: `GET /browser/explorer/tag-children?tag={value}` returns objects with that tag value across all tag properties.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Tag folder SPARQL query | `strategies.py:query_tag_folders()` | Already builds the correct `SELECT DISTINCT ?tagValue` pattern; adapt for multi-property |
| Tag-filtered object query | `strategies.py:query_objects_by_tag()` | Already builds correct `FILTER(STR(?matchVal) = ...)` with escaping |
| Label resolution | `_LABEL_OPTIONALS` + `_LABEL_COALESCE` in `strategies.py` | Consistent label fallback chain; copy into by-tag queries |
| Explorer tree rendering | `mount_tree.html` + `mount_tree_objects.html` | Template patterns for folder→children lazy expansion |
| Tag pill CSS | `.tag-pill` in `workspace.css:2824` | Already styled with accent color, border-radius, margin |
| Icon service for leaf nodes | `icon_svc.get_type_icon()` + `_bindings_to_objects()` | Standard helper for object leaf rendering |

## Existing Code and Patterns

- `backend/app/browser/workspace.py:146-157` — Current `_handle_by_tag` placeholder handler to replace. Handler signature: `async fn(request, **_kwargs) -> HTMLResponse`. Must accept `label_service` and `icon_svc` kwargs (passed by `explorer_tree` dispatcher at line 535-538).
- `backend/app/browser/workspace.py:160-163` — `EXPLORER_MODES` registry. No change needed; `by-tag` key already maps to handler.
- `backend/app/browser/workspace.py:498-538` — `explorer_tree` endpoint. Passes `shapes_service`, `icon_svc`, `label_service` to all handlers. The by-tag handler can use `label_service` and `icon_svc`.
- `backend/app/browser/workspace.py:671-700` — `mount_children` endpoint pattern. Reference for the new `tag_children` endpoint structure.
- `backend/app/vfs/strategies.py:157-182` — `query_tag_folders()` and `query_objects_by_tag()` with SPARQL escaping. Reusable but hardcoded to single `tag_property` parameter; by-tag explorer needs multi-property variant.
- `backend/app/templates/browser/object_read.html:96-100` — Tag pill rendering: `{% elif 'tags' in prop.path %}` → `<span class="tag-pill">#{{ item.value }}</span>`. Works for `bpkm:tags` path (`urn:sempkm:model:basic-pkm:tags` contains "tags"). Does NOT match `schema:keywords` — need to extend the condition.
- `backend/app/templates/forms/_field.html:55,62` — Tag pill edit styling via `'tags' in prop.path` check. Same limitation as read view.
- `models/basic-pkm/seed/basic-pkm.jsonld` — 11 objects with `"bpkm:tags": "comma,separated,values"`. Must be converted to `"bpkm:tags": ["tag1", "tag2", "tag3"]` (JSON-LD array = individual triples).
- `models/basic-pkm/ontology/basic-pkm.jsonld:63-67` — `bpkm:tags` defined as `owl:DatatypeProperty` with `rdfs:comment: "Comma-separated tags"`. Comment needs updating.
- `models/basic-pkm/shapes/basic-pkm.jsonld` — 4 shapes use `bpkm:tags` with `sh:datatype xsd:string`, no `sh:maxCount`. Already multi-valued — form UI renders multi-value inputs. No shape changes needed.
- `backend/app/obsidian/executor.py:181-205` — Obsidian import already stores tags as individual `schema:keywords` triples (one Literal per tag). No change needed here.
- `backend/app/commands/handlers/object_patch.py` — `handle_object_patch` iterates `params.properties` and creates one `materialize_delete` (variable pattern) per predicate + one `materialize_insert` per value. Multi-valued tags already handled correctly IF the form sends them as separate values. The comma-splitting middleware should go here.
- `frontend/static/css/workspace.css:2824-2835` — `.tag-pill` CSS already complete (inline-flex, border-radius, accent colors, margin).

## Constraints

- **Two tag properties coexist**: `bpkm:tags` (basic-pkm model, `urn:sempkm:model:basic-pkm:tags`) and `schema:keywords` (Obsidian imports, `https://schema.org/keywords`). The by-tag explorer must query both.
- **No SPARQL migration infrastructure**: There's no existing migration runner for triplestore data. The tag migration must be a one-time script (management command or startup check).
- **Form save flow uses predicate IRIs**: `save_object()` collects form values by predicate IRI key and passes to `handle_object_patch`. Each value in a multi-value field is sent as a separate form value — comma splitting only needed if user types commas in a single field.
- **Template tag detection is path-based**: `'tags' in prop.path` matches `bpkm:tags` but not `schema:keywords`. Must extend to also match `keywords` in the path.
- **Explorer handler receives specific kwargs**: The dispatcher passes `shapes_service`, `icon_svc`, and `label_service` — the by-tag handler should accept `label_service` and `icon_svc` explicitly (not just `**_kwargs`).
- **Seed data is loaded as raw JSON-LD triples**: The `ModelService.install_model()` materializes seed triples directly. If seed data uses JSON-LD arrays, rdflib will produce individual triples automatically. No custom parsing needed.
- **E2E tests limited by auth rate**: 5 magic-link calls/minute. Explorer E2E tests must be combined efficiently.

## Common Pitfalls

- **Comma-in-tag-value confusion** — If a user types `"machine-learning, deep-learning"` in a single input field, the save handler receives it as one string. The tag-splitting middleware must only activate on save, not on read. Splitting on comma within a single field value is the correct behavior for tag properties.
- **Idempotent migration** — Running the migration twice must not create duplicates. The SPARQL UPDATE should delete the comma-separated literal and insert individual tags in a single atomic operation. A `FILTER(CONTAINS(STR(?val), ","))` clause ensures only comma-separated values are processed.
- **Tag property detection heuristic** — Using `'tags' in prop.path` will match any property with "tags" in the IRI (e.g., a hypothetical `bpkm:relatedTags`). This is acceptable for now since only `bpkm:tags` exists. Adding `'keywords' in prop.path` for `schema:keywords` is safe similarly.
- **VFS by-tag queries are scoped, explorer by-tag is unscoped** — The VFS `query_tag_folders` takes a `scope_filter` param and a single `tag_property`. The explorer by-tag must use empty scope filter and UNION across multiple tag properties. Don't reuse the VFS functions directly; write adapted queries.
- **Tag count accuracy with multi-property queries** — If an object has both `bpkm:tags "rdf"` and `schema:keywords "rdf"`, it should count once under the "rdf" tag folder, not twice. Use `COUNT(DISTINCT ?iri)` in the tag folders query.

## Open Risks

- **Performance with large tag sets**: If Obsidian imports produce hundreds of unique tags, the by-tag tree root will be very long. Consider alphabetical grouping (A-Z sub-folders) if this becomes an issue. For now, flat alphabetical list matches the VFS by-tag pattern.
- **Migration timing**: The one-time migration runs against the triplestore. If the user has no basic-pkm model installed, there's nothing to migrate. The migration should be safe to run at any time (idempotent, targets only comma-containing `bpkm:tags` values).
- **Seed data JSON-LD array handling**: Verify that rdflib's JSON-LD parser produces separate triples from `"bpkm:tags": ["tag1", "tag2"]`. This is standard JSON-LD behavior (each array element is a separate object of the property), but should be verified with a quick test.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (198 installs) | available — not needed; project already has strong htmx patterns |
| SPARQL/RDF | `letta-ai/skills@sparql-university` (36 installs) | available — low install count; project already has mature SPARQL patterns |
| FastAPI | (standard) | no skill needed — mature codebase patterns |

No skills recommended for installation — the project has well-established patterns for all technologies involved.

## Sources

- Codebase exploration of `backend/app/vfs/strategies.py`, `backend/app/browser/workspace.py`, `backend/app/commands/handlers/object_patch.py`
- `models/basic-pkm/seed/basic-pkm.jsonld` for seed data analysis
- `models/basic-pkm/ontology/basic-pkm.jsonld` and `models/basic-pkm/shapes/basic-pkm.jsonld` for property definitions
- S01 task summaries (T01-T04) for explorer mode infrastructure patterns
- `backend/app/templates/browser/object_read.html` and `frontend/static/css/workspace.css` for existing tag pill rendering
