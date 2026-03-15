# S03 (Hierarchical Tag Tree) — Research

**Date:** 2026-03-14  
**Status:** Ready for planning

## Summary

The current by-tag explorer renders a flat list of tag folders — each distinct tag value is one node with a count badge. Tags containing `/` delimiters (e.g. `garden/cultivate/roses`) appear as flat entries. The goal is to nest these into a tree: `garden` → `cultivate` → `roses`, where each intermediate node is an expandable folder showing descendant counts, and only leaf-level nodes expand into object lists.

The key design decision is **where to compute the hierarchy: SPARQL or Python**. SPARQL 1.1 supports `STRBEFORE`, `STRAFTER`, `CONTAINS`, and `STRSTARTS` string functions, and RDF4J 5.0.1 implements them. However, extracting the first `/` segment from arbitrary tag values requires either:

1. **SPARQL string functions** — `STRBEFORE(?tagValue, "/")` for top-level segments, then `STRSTARTS(?tagValue, "prefix/")` for filtering children. Elegant for querying descendants at any level but requires different SPARQL per depth level.
2. **Python post-processing** — Fetch all tag values flat (existing query works), build the tree in Python, pass nested structure to template. Simpler to reason about, more testable, but loads all tags upfront.

**Recommendation: Hybrid approach.** Fetch all tag values flat via the existing SPARQL query (unchanged), build the hierarchical tree structure in Python (a pure function, easily unit-tested), and use a new `tag-children` endpoint for lazy-loading sub-folders at deeper levels. This mirrors the hierarchy tree pattern (D035) where root nodes load first, children lazy-load via htmx.

## Recommendation

**Fetch flat, nest in Python, lazy-load children.**

1. **Root handler (`_handle_by_tag`):** Fetch all distinct tag values (existing SPARQL). In Python, extract top-level segments (everything before first `/`, or the full value if no `/`). Group and count. Return only root-level nodes.
2. **Children endpoint (`/explorer/tag-children`):** Receives a `prefix` parameter. Finds all tag values starting with `prefix/`, extracts the next segment, groups and counts. Returns either sub-folder nodes (if more `/` segments remain) or object leaves (if this is a full tag value).
3. **Template:** New `tag_tree_folder.html` for folder sub-nodes that recurse via htmx. Reuse existing `tag_tree_objects.html` for leaf-level object lists.

This approach:
- Reuses the existing flat SPARQL query (no new SPARQL string functions needed for roots)
- Uses `STRSTARTS` for children queries (well-supported, fast with literal indexes)
- Follows the proven htmx lazy-load pattern (D035, D036, D040, D044)
- Enables pure-function unit testing of the tree-building logic

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| SPARQL SELECT execution + error handling | `_execute_sparql_select()` in `workspace.py` | Consistent error handling, logging |
| Binding → object dict conversion | `_bindings_to_objects()` in `workspace.py` | De-duplication, label resolution, icon lookup |
| SPARQL string escaping | `_sparql_escape()` in `workspace.py` | Injection protection for tag prefix values |
| Label resolution | `_LABEL_OPTIONALS` / `_LABEL_COALESCE` imported from VFS strategies | Consistent label precedence |
| Tree node toggle behavior | `initTreeToggle()` in `workspace.js` (generic `.tree-node` click → `.expanded` toggle) | No JS changes needed |
| htmx lazy-load pattern | `hx-trigger="click once"` + `hx-target` + `hx-swap="innerHTML"` | Proven across all tree modes |

## Existing Code and Patterns

- `backend/app/browser/workspace.py:150-190` — `_handle_by_tag()` handler: flat SPARQL query, builds folder list, renders `tag_tree.html`. **Modify** to build hierarchical root-level nodes.
- `backend/app/browser/workspace.py:702-750` — `tag_children()` endpoint: returns objects for a specific tag value. **Extend** to support prefix-based sub-folder queries alongside exact-match object queries.
- `backend/app/templates/browser/tag_tree.html` — Root-level tag folders. **Modify** to render folder nodes that can expand into sub-folders (not just objects).
- `backend/app/templates/browser/tag_tree_objects.html` — Object leaves. **Keep as-is** — used when expanding a leaf-level tag.
- `backend/app/templates/browser/mount_tree_folders.html` — Reference pattern for nested folder templates with parent context.
- `backend/app/templates/browser/hierarchy_children.html` — Reference pattern for recursive tree-node rendering.
- `backend/app/vfs/strategies.py:157-182` — VFS tag query functions. Not reused directly (different query shape per D042) but pattern reference.
- `backend/tests/test_tag_explorer.py` — Existing unit tests for by-tag mode. **Extend** with hierarchy tests.
- `e2e/tests/20-tags/tag-explorer.spec.ts` — Existing E2E test. **Will need updates in S09** for hierarchy verification.
- `backend/app/obsidian/scanner.py:35` — `TAG_RE` regex already supports `/` in tags: `r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)"`. Tags like `garden/cultivate/roses` are imported as-is.
- `backend/app/obsidian/executor.py:202-204` — Tags stored as `schema:keywords` literals with full `/`-delimited values.

## Constraints

- **RDF4J 5.0.1** — Full SPARQL 1.1 string function support (`STRBEFORE`, `STRAFTER`, `STRSTARTS`, `CONTAINS`). No constraints on query capabilities.
- **Tag predicates: dual-property UNION** — Tags exist on both `bpkm:tags` (`urn:sempkm:model:basic-pkm:tags`) and `schema:keywords` (`https://schema.org/keywords`). All queries must UNION both (per D042).
- **htmx server-side rendering** — No client-side tree building. All nesting comes from server-rendered HTML partials.
- **Generic tree toggle JS** — `initTreeToggle()` toggles `.expanded` class on any `.tree-node` click. Templates must follow `.tree-node` + sibling `.tree-children` pattern.
- **No global tree load** — Must lazy-load children (not render full tree upfront). Tags could number in hundreds/thousands with imported vaults.
- **`tree-count-badge` class** — Used in current `tag_tree.html` but has **no CSS definition**. Need to add styling or use an existing badge class.

## Common Pitfalls

- **Prefix collisions** — A tag `garden` and a tag `garden/roses` both exist. The tag `garden` is both a leaf (objects are tagged with it) AND a parent folder (has children). Must handle this by showing the folder as expandable with its own count, plus a "(direct)" or merged listing. The simplest approach: count objects tagged exactly `garden` as `folder.direct_count`, count all objects with tags starting with `garden/` as `folder.children_count`, and show the total.
- **Safe ID generation for nested nodes** — Current `safe_id` pattern replaces `:`, `/`, `#`, `.`, ` ` with `_`. For nested tags, the prefix path (e.g., `garden/cultivate`) must produce unique IDs. This already works because the full prefix value gets sanitized.
- **SPARQL `STRSTARTS` requires exact prefix match** — When querying children of `garden`, must use `STRSTARTS(?tagValue, "garden/")` with trailing `/` to avoid matching `gardening` or `garden-tools`.
- **Double-counting with UNION** — If the same object has both `bpkm:tags "garden/roses"` and `schema:keywords "garden/roses"`, `COUNT(DISTINCT ?iri)` handles this correctly (already in current query).
- **Empty intermediate segments** — Tags like `garden//roses` (double slash) are theoretically possible. Filter these with `FILTER(STRLEN(?segment) > 0)` or clean in Python.
- **URL encoding in htmx requests** — Tag prefixes containing `/` must be URL-encoded in `hx-get` attributes. Use `{{ prefix | urlencode }}` (already used in current template).
- **Lucide icon re-render** — After htmx swaps, `lucide.createIcons()` must run. This is already handled by the workspace's `htmx:afterSwap` listener.

## Design: Tree-Building Algorithm

### Python pure function (unit-testable)

```python
def build_tag_tree(tag_values: list[dict], prefix: str = "") -> list[dict]:
    """Group tag values into tree nodes at the specified prefix level.
    
    Args:
        tag_values: List of {"value": "garden/cultivate/roses", "count": N}
        prefix: Parent prefix (empty for roots, "garden" for first-level children)
    
    Returns:
        List of folder dicts with:
        - segment: The folder label at this level (e.g. "garden")
        - prefix: Full prefix path (e.g. "garden" or "garden/cultivate")
        - direct_count: Objects tagged exactly with this prefix value
        - total_count: Objects tagged with this prefix or any descendant
        - has_children: Whether deeper segments exist
    """
```

### Root-level flow

1. SPARQL: Fetch all `?tagValue` with `COUNT(DISTINCT ?iri)` (existing query, unchanged)
2. Python: For each tag value, extract first segment (`value.split('/')[0]`)
3. Python: Group by first segment → `{segment, prefix, direct_count, total_count, has_children}`
4. Template: Render root nodes; folders with `has_children` get `hx-get` to tag-children endpoint

### Children-level flow

1. htmx request: `GET /explorer/tag-children?prefix=garden`
2. SPARQL: `SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count) WHERE { ... FILTER(STRSTARTS(?tagValue, "garden/")) } GROUP BY ?tagValue`
3. Python: Strip prefix, extract next segment, group → sub-folders or leaf objects
4. Template: Sub-folders get recursive `hx-get`; leaf tags expand into objects

### When a node is BOTH a tag and a folder

For tag `garden` that has direct objects AND child tags (`garden/roses`):
- Render as a folder node with the combined count
- On expansion, show a special "Tagged: garden" entry (objects directly tagged `garden`) followed by sub-folders
- Alternative: show direct objects mixed with sub-folders, with sub-folders always first

## Open Risks

- **Performance with large tag sets** — The root handler fetches ALL tag values and groups in Python. With an imported Ideaverse vault (905 notes), this could be hundreds of tag values. This is a single SPARQL query returning lightweight data (string + count), so likely fine. If it becomes slow, add TTLCache on the handler (same pattern as ViewSpecService).
- **Tag delimiter convention** — M005 scope says `/` is the delimiter. Some tagging conventions use `.` or `:`. Hardcoding `/` is correct for now per the milestone spec. If other delimiters are needed, the pure function is easy to parameterize.
- **VFS by-tag strategy interaction** — VFS mount `by-tag` strategy also uses flat tag queries. This slice only changes the explorer by-tag mode, not VFS mounts. VFS mounts can optionally adopt hierarchical rendering later.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| SPARQL | `letta-ai/skills@sparql-university` | available (38 installs) — low relevance, university-style reference |
| htmx | `mindrally/skills@htmx` | available (203 installs) — potentially useful but codebase has extensive htmx patterns already |

Both skills are optional — the codebase already has strong SPARQL and htmx patterns to follow.

## Sources

- RDF4J 5.0.1 SPARQL function support confirmed via `docker-compose.yml` image tag
- SPARQL 1.1 string functions (`STRBEFORE`, `STRSTARTS`) are standard W3C; no external docs needed
- Tag regex supporting `/`: `backend/app/obsidian/scanner.py:35` — `TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)")`
- Tag storage as `schema:keywords` literals: `backend/app/obsidian/executor.py:202-204`
- Lazy-load tree pattern: hierarchy tree (M003/S02), VFS mount tree (M003/S03), tag tree (M003/S04)
- D035, D036, D040, D042, D044 — design decisions governing tree endpoint separation and query patterns
