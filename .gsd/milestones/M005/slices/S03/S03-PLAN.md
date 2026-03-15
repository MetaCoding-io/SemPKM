# S03: Hierarchical Tag Tree

**Goal:** By Tag explorer nests tags at arbitrary depth using `/` as delimiter; real Ideaverse tags render as a multi-level tree with lazy-loaded children.
**Demo:** Open workspace → select "By Tag" in explorer → see root-level tag segments as folders → expand `garden` → see sub-folders `cultivate`, `roses` (etc.) → expand a leaf tag → see tagged objects.

## Must-Haves

- Tags with `/` delimiters render as nested tree nodes at arbitrary depth
- Each tree level is lazy-loaded via htmx (not full tree upfront)
- Tag that is both a direct tag AND a folder prefix shows as expandable folder with combined count
- Intermediate nodes that have no directly-tagged objects still appear as navigable folders
- Count badges show total descendant count per folder
- Clicking a leaf-level tag expands to show tagged objects (existing behavior preserved)
- Existing flat tags (no `/`) still work as single-level folders
- `tree-count-badge` CSS class gets a proper style definition

## Proof Level

- This slice proves: integration
- Real runtime required: yes (unit tests for pure function; browser verification against running stack with real data)
- Human/UAT required: no (visual review deferred to S09 E2E)

## Verification

- `cd backend && python -m pytest tests/test_tag_tree_builder.py -v` — pure function unit tests for `build_tag_tree()` covering: simple flat tags, single-level nesting, multi-level nesting, mixed flat+nested, prefix collision (tag is both leaf and folder), empty intermediate segments, edge cases
- `cd backend && python -m pytest tests/test_tag_explorer.py -v` — extended tests covering new handler/endpoint structure
- Browser verification: explorer in "By Tag" mode shows hierarchical folders, expanding a folder shows sub-folders or objects
- Failure-path check: requesting `/explorer/tag-children?prefix=nonexistent` returns empty folder list (no crash); SPARQL errors surface via `_execute_sparql_select` error handling and return user-visible "No tags found" message

## Observability / Diagnostics

- Runtime signals: `logger.debug("By-tag explorer: %d root nodes", ...)` and `logger.debug("Tag children for prefix '%s': %d sub-folders, %d leaf tags", ...)`
- Inspection surfaces: browser network tab shows `/explorer/tag-children?prefix=...` requests with correct parameters
- Failure visibility: SPARQL query errors surface via `_execute_sparql_select` error handling; empty tree shows "No tags found"

## Integration Closure

- Upstream surfaces consumed: `_execute_sparql_select()`, `_sparql_escape()`, `_bindings_to_objects()`, `_LABEL_OPTIONALS`/`_LABEL_COALESCE`, `initTreeToggle()` JS, htmx lazy-load pattern
- New wiring introduced: `build_tag_tree()` pure function, extended `tag_children` endpoint with `prefix` parameter, new `tag_tree_folder.html` template
- What remains before the milestone is truly usable end-to-end: S04 (autocomplete), S09 (E2E tests + docs)

## Tasks

- [x] **T01: Implement build_tag_tree() pure function with unit tests** `est:45m`
  - Why: The tree-building algorithm is the core logic and highest-risk piece. A pure function is easily unit-tested without Docker/triplestore. Retiring this risk first ensures the grouping, counting, and prefix-collision handling are correct before touching endpoints.
  - Files: `backend/app/browser/tag_tree.py`, `backend/tests/test_tag_tree_builder.py`
  - Do: Create `tag_tree.py` with `build_tag_tree(tag_values, prefix="")` that takes flat `[{"value": "...", "count": N}]` and returns hierarchical nodes `[{"segment", "prefix", "direct_count", "total_count", "has_children"}]`. Handle: root extraction (first `/` segment), prefix-filtered children (strip prefix, extract next segment), tags that are both leaf AND folder, empty intermediate segments, tags with no `/`. Write comprehensive unit tests.
  - Verify: `cd backend && python -m pytest tests/test_tag_tree_builder.py -v` — all pass
  - Done when: `build_tag_tree()` correctly groups flat tag data into hierarchical nodes at any depth level, with all edge cases covered by tests

- [x] **T02: Wire hierarchical tree into endpoints, templates, and CSS** `est:1h`
  - Why: Connects the pure function to the live explorer. Modifies `_handle_by_tag()` to return root-level nodes, extends `tag_children` to handle both prefix-based sub-folder queries and exact-match object queries, updates templates for recursive folder rendering, and adds missing `tree-count-badge` CSS.
  - Files: `backend/app/browser/workspace.py`, `backend/app/templates/browser/tag_tree.html`, `backend/app/templates/browser/tag_tree_folder.html` (new), `frontend/static/css/workspace.css`, `backend/tests/test_tag_explorer.py`
  - Do: (1) Import `build_tag_tree` in workspace.py. (2) Modify `_handle_by_tag()`: keep existing SPARQL, pass results through `build_tag_tree()`, pass root nodes to updated template. (3) Extend `tag_children`: add `prefix` query parameter; when `prefix` is provided, run SPARQL with `STRSTARTS` filter, pass through `build_tag_tree(results, prefix)`, return sub-folder template for folders or object template for leaves; when only `tag` is provided, keep existing exact-match behavior. (4) Update `tag_tree.html` to render hierarchical folder nodes with `hx-get` pointing to `tag_children?prefix=...`. (5) Create `tag_tree_folder.html` for recursive sub-folder rendering. (6) Add `.tree-count-badge` CSS rule in workspace.css. (7) Update `test_tag_explorer.py` with tests for new handler structure.
  - Verify: `cd backend && python -m pytest tests/test_tag_explorer.py -v` — all pass; browser verification with running stack
  - Done when: By Tag explorer renders hierarchically with lazy-loaded children at arbitrary depth; flat tags still work; count badges are styled

## Files Likely Touched

- `backend/app/browser/tag_tree.py` (new — pure function)
- `backend/tests/test_tag_tree_builder.py` (new — unit tests for pure function)
- `backend/app/browser/workspace.py` (modify `_handle_by_tag`, extend `tag_children`)
- `backend/app/templates/browser/tag_tree.html` (modify for hierarchical root nodes)
- `backend/app/templates/browser/tag_tree_folder.html` (new — recursive sub-folder template)
- `frontend/static/css/workspace.css` (add `.tree-count-badge`)
- `backend/tests/test_tag_explorer.py` (extend with hierarchy tests)
