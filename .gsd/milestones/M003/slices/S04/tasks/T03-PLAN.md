---
estimated_steps: 6
estimated_files: 7
---

# T03: Extend tag pill rendering to schema:keywords and create by-tag explorer backend

**Slice:** S04 — Tag System Fix & Tag Explorer
**Milestone:** M003

## Description

Two deliverables: (1) Extend tag pill rendering in templates to detect `schema:keywords` alongside `bpkm:tags`. (2) Replace the `_handle_by_tag` placeholder with a real explorer mode that queries both tag properties via SPARQL UNION, and add the `tag_children` endpoint with templates for lazy expansion.

## Steps

1. In `backend/app/templates/browser/object_read.html` (~line 113), change `{% elif 'tags' in prop.path %}` to `{% elif 'tags' in prop.path or 'keywords' in prop.path %}`. This makes Obsidian-imported `schema:keywords` render as pills too.
2. In `backend/app/templates/forms/_field.html`, find the tag-detection conditions (`'tags' in prop.path`) and extend them identically to also match `'keywords' in prop.path`.
3. Replace `_handle_by_tag` in `backend/app/browser/workspace.py` with a real implementation:
   - Build a SPARQL query using `UNION` across both `bpkm:tags` IRI and `schema:keywords` IRI, no scope filter (explorer is global)
   - Query: `SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count) WHERE { { ?iri <bpkm:tags> ?tagValue } UNION { ?iri <schema:keywords> ?tagValue } } GROUP BY ?tagValue ORDER BY ?tagValue`
   - Use `urn:sempkm:current` graph
   - Execute via the existing triplestore client pattern from workspace.py
   - Pass results to new `tag_tree.html` template
4. Create `backend/app/templates/browser/tag_tree.html`:
   - Pattern matches `mount_tree.html`: folder nodes with `hx-get="/browser/explorer/tag-children?tag={{ folder.value | urlencode }}"`, lucide `tag` icon, label showing `#tagValue`, count badge span
   - `hx-trigger="click once"`, lazy expansion into `#tag-children-{safe_id}` div
   - Empty state: "No tags found"
5. Add `tag_children` endpoint to workspace.py:
   - `GET /browser/explorer/tag-children?tag={value}` (requires authenticated user)
   - SPARQL: query objects with that tag value across both properties using UNION, with label resolution (`_LABEL_OPTIONALS`/`_LABEL_COALESCE` pattern from strategies.py)
   - Process results via `_bindings_to_objects()` for icon resolution
   - Render via `tag_tree_objects.html` (copy of `mount_tree_objects.html` pattern with `data-testid="tag-object"`)
6. Create `backend/tests/test_tag_explorer.py` with tests:
   - `_handle_by_tag` is in `EXPLORER_MODES` and is async callable
   - SPARQL query construction produces valid UNION query
   - Tag value escaping in `tag_children` query (prevent SPARQL injection)
   - Handler accepts `label_service` and `icon_svc` kwargs

## Must-Haves

- [ ] Tag pills render for both `bpkm:tags` and `schema:keywords` in read view
- [ ] Tag pill edit styling works for both tag properties in edit form
- [ ] `_handle_by_tag` returns real SPARQL-driven tag folders with counts
- [ ] Tag folders use `COUNT(DISTINCT ?iri)` to avoid double-counting
- [ ] `tag_children` endpoint returns objects for a given tag value
- [ ] Tag tree uses same leaf pattern as mount_tree_objects.html (click-through to object tabs)
- [ ] Unit tests pass for by-tag handler and SPARQL construction

## Verification

- `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — all tests pass
- `cd backend && .venv/bin/pytest tests/ -v` — no regressions
- Template changes verified: `rg "keywords" backend/app/templates/browser/object_read.html` shows extended condition
- Template changes verified: `rg "keywords" backend/app/templates/forms/_field.html` shows extended condition
- New templates exist: `ls backend/app/templates/browser/tag_tree*.html` shows both files
- Tag-children endpoint registered: `rg "tag-children" backend/app/browser/workspace.py`

## Observability Impact

- Signals added/changed: `logger.debug("By-tag explorer: %d tag folders", len(folders))` in handler; `logger.debug("Tag children for '%s': %d objects", tag, len(objects))` in tag_children
- How a future agent inspects this: Hit `/browser/explorer/tree?mode=by-tag` to see tag folder HTML; hit `/browser/explorer/tag-children?tag=rdf` to see objects
- Failure state exposed: Empty tree with "No tags found" if no tag triples exist; HTTP 400 if `tag` parameter missing from tag-children request

## Inputs

- `backend/app/browser/workspace.py` — existing `_handle_by_tag` placeholder (line ~146), `_bindings_to_objects` helper, `explorer_tree` dispatcher
- `backend/app/vfs/strategies.py` — `query_tag_folders` and `query_objects_by_tag` as SPARQL reference patterns (lines 157-186)
- `backend/app/templates/browser/mount_tree.html` — template pattern for folder nodes
- `backend/app/templates/browser/mount_tree_objects.html` — template pattern for object leaves
- `backend/app/templates/browser/object_read.html` — current tag pill condition (line ~113)
- `backend/app/templates/forms/_field.html` — current tag edit styling condition

## Expected Output

- `backend/app/browser/workspace.py` — real `_handle_by_tag` + `tag_children` endpoint
- `backend/app/templates/browser/object_read.html` — extended tag pill condition
- `backend/app/templates/forms/_field.html` — extended tag edit condition
- `backend/app/templates/browser/tag_tree.html` — tag folder tree template
- `backend/app/templates/browser/tag_tree_objects.html` — tag object leaves template
- `backend/tests/test_tag_explorer.py` — unit tests for by-tag explorer
