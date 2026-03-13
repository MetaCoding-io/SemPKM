---
id: T03
parent: S04
milestone: M003
provides:
  - Tag pill rendering for both bpkm:tags and schema:keywords in read and edit views
  - Real _handle_by_tag explorer handler with SPARQL UNION query across both tag properties
  - tag_children endpoint at GET /browser/explorer/tag-children?tag={value}
  - tag_tree.html and tag_tree_objects.html templates for by-tag explorer UI
  - 21 unit tests for by-tag handler registration, SPARQL construction, and SPARQL injection protection
key_files:
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/object_read.html
  - backend/app/templates/forms/_field.html
  - backend/app/templates/browser/tag_tree.html
  - backend/app/templates/browser/tag_tree_objects.html
  - backend/tests/test_tag_explorer.py
key_decisions:
  - Imported _LABEL_OPTIONALS and _LABEL_COALESCE from vfs/strategies.py into workspace.py rather than duplicating the label resolution SPARQL patterns
patterns_established:
  - Tag tree templates follow mount_tree.html / mount_tree_objects.html pattern with data-testid="tag-folder" / data-testid="tag-object"
  - Tag detection condition uses `'tags' in prop.path or 'keywords' in prop.path` in both read and edit templates
observability_surfaces:
  - logger.debug("By-tag explorer: %d tag folders", len(folders)) in _handle_by_tag
  - logger.debug("Tag children for '%s': %d objects", tag, len(objects)) in tag_children
  - HTTP 400 with "Missing required parameter: tag" when tag param absent from tag_children
  - Empty tree with "No tags found" when no tag triples exist
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Extend tag pill rendering to schema:keywords and create by-tag explorer backend

**Extended tag pill rendering to detect `schema:keywords` alongside `bpkm:tags`, replaced the by-tag explorer placeholder with a real SPARQL-driven implementation, and added the tag-children endpoint with templates.**

## What Happened

1. Extended the tag pill condition in `object_read.html` from `'tags' in prop.path` to `'tags' in prop.path or 'keywords' in prop.path` so Obsidian-imported `schema:keywords` values render as `#`-prefixed pills.

2. Extended the same condition in `_field.html` for the edit form's `tag-pill-item` CSS class on both the existing-values loop and the empty-input fallback.

3. Replaced the `_handle_by_tag` placeholder with a real implementation that:
   - Queries `urn:sempkm:current` graph using `UNION` across `bpkm:tags` and `schema:keywords`
   - Uses `COUNT(DISTINCT ?iri)` to avoid double-counting objects tagged via both properties
   - Groups by tag value, orders alphabetically
   - Renders via new `tag_tree.html` template

4. Created `tag_tree.html` template matching the `mount_tree.html` pattern: folder nodes with lucide `tag` icon, `#tagValue` label, count badge, and `hx-get` for lazy expansion via `tag-children` endpoint.

5. Added `tag_children` endpoint at `GET /browser/explorer/tag-children?tag={value}`:
   - Validates `tag` parameter (HTTP 400 if missing)
   - Uses `_sparql_escape` on tag value to prevent SPARQL injection
   - SPARQL UNION query across both tag properties with label resolution via `_LABEL_OPTIONALS`/`_LABEL_COALESCE`
   - Processes results through `_bindings_to_objects()` for icon resolution
   - Renders via `tag_tree_objects.html`

6. Created `tag_tree_objects.html` template matching `mount_tree_objects.html` pattern with `data-testid="tag-object"`, drag support, and `handleTreeLeafClick` click-through.

7. Created `test_tag_explorer.py` with 21 tests across 5 test classes covering handler registration, signature validation, SPARQL query construction, SPARQL injection protection, and tag-children query structure.

## Verification

- `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — 21/21 passed
- `cd backend && .venv/bin/pytest tests/ -v` — 204/204 passed (no regressions)
- `rg "keywords" backend/app/templates/browser/object_read.html` — shows extended condition
- `rg "keywords" backend/app/templates/forms/_field.html` — shows extended condition (2 occurrences)
- `ls backend/app/templates/browser/tag_tree*.html` — both files present
- `rg "tag-children" backend/app/browser/workspace.py` — endpoint registered

### Slice-level verification status (T03 is task 3 of 4):
- ✅ `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — passes (from T01/T02)
- ✅ `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — passes
- ⬜ `cd e2e && npx playwright test tests/20-tags/` — not yet created (T04)
- ⬜ Manual docker smoke test — deferred to T04

## Diagnostics

- Hit `/browser/explorer/tree?mode=by-tag` to see tag folder HTML with counts
- Hit `/browser/explorer/tag-children?tag=rdf` to see objects tagged "rdf"
- Hit `/browser/explorer/tag-children` (no tag param) to get HTTP 400
- Backend DEBUG logs show folder/object counts on each request

## Deviations

- Imported `_LABEL_OPTIONALS` and `_LABEL_COALESCE` from `vfs/strategies.py` rather than duplicating the SPARQL label resolution pattern. These are private-by-convention but stable and well-tested.
- Updated `_handle_by_tag` signature to accept `label_service` and `icon_svc` positional kwargs (matching `_handle_by_type` and `_handle_hierarchy` patterns). The explorer_tree dispatcher already passes these.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/object_read.html` — extended tag pill condition to match `'keywords'`
- `backend/app/templates/forms/_field.html` — extended tag pill edit styling to match `'keywords'`
- `backend/app/browser/workspace.py` — replaced `_handle_by_tag` placeholder with real SPARQL implementation, added `tag_children` endpoint, imported `_LABEL_OPTIONALS`/`_LABEL_COALESCE`
- `backend/app/templates/browser/tag_tree.html` — new template for tag folder tree nodes
- `backend/app/templates/browser/tag_tree_objects.html` — new template for tag object leaf nodes
- `backend/tests/test_tag_explorer.py` — 21 unit tests for by-tag explorer
