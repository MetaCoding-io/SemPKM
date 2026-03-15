# S03: Hierarchical Tag Tree — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: Tag tree rendering requires the triplestore with real Ideaverse data to verify hierarchical grouping, lazy loading, and count aggregation at multiple depth levels

## Preconditions

- Docker stack running (`docker compose up -d`)
- Ideaverse vault imported (provides `/`-delimited tags like `architect/build`, `garden/cultivate`)
- Browser open to workspace at `http://localhost:3000/browser/`

## Smoke Test

1. Open workspace → click explorer mode dropdown → select "By Tag"
2. **Expected:** Tree shows hierarchical folders (e.g. `architect`, `garden`) with count badges, not a flat list of all tag values

## Test Cases

### 1. Root-level hierarchical rendering

1. Select "By Tag" explorer mode
2. Observe the root-level tree nodes
3. **Expected:** Tags with `/` delimiters appear as folder nodes (folder icon, expandable). Tags without `/` appear as leaf nodes (tag icon with `#` prefix). Each node shows a count badge with total descendant count.

### 2. First-level folder expansion

1. Click the `architect` folder node to expand it
2. **Expected:** Sub-items appear: `#build` and `#renovate` (or similar sub-tags from Ideaverse data). Each has its own count badge. Network tab shows `/explorer/tag-children?prefix=architect` request.

### 3. Multi-level folder expansion

1. If any expanded folder contains sub-folders (not just leaf tags), click to expand the sub-folder
2. **Expected:** Third-level items appear. Counts at each level reflect only that level's descendants.

### 4. Leaf tag expansion to objects

1. Click a leaf tag (one with `#` prefix and tag icon, no sub-folders)
2. **Expected:** Tagged objects appear below the tag node with type icons and labels. These are clickable to open in workspace tabs.

### 5. Tag that is both leaf and folder (prefix collision)

1. Look for a tag value that exists as both a direct tag AND a prefix for deeper tags (e.g. if `garden` is used as a tag AND `garden/cultivate` exists)
2. **Expected:** The node appears as a folder (expandable) with `has_children=True`. When expanded, both sub-folder nodes and direct-tagged objects are shown.

### 6. Flat tags still work

1. Find a tag with no `/` in its value (a simple flat tag)
2. Click to expand it
3. **Expected:** Tagged objects appear directly (same behavior as before hierarchical tree). No folder nesting.

### 7. Count badge accuracy

1. Expand a folder and note individual child counts
2. Compare sum of children counts to parent's count badge
3. **Expected:** Parent total_count = sum of all descendant direct_counts. Badge values are consistent.

### 8. Count badge styling

1. Observe count badges on tree nodes
2. **Expected:** Badges have `.tree-count-badge` CSS styling: small pill shape, positioned to the right of the node label (margin-left: auto), visually similar to `.abox-count-badge`.

## Edge Cases

### Nonexistent prefix returns empty

1. Manually navigate to `/explorer/tag-children?prefix=nonexistent_prefix_xyz`
2. **Expected:** Returns "No tags found" message. No crash or error.

### Missing parameters returns 400

1. Manually navigate to `/explorer/tag-children` (no `tag` or `prefix` param)
2. **Expected:** HTTP 400 response with "Missing required parameter: tag or prefix" message.

### Explorer mode switch preserves behavior

1. Switch from "By Tag" to "By Type" and back to "By Tag"
2. **Expected:** Tag tree re-renders correctly each time. No stale state or broken expansion.

## Failure Signals

- Flat list of all tags instead of hierarchical folders → `build_tag_tree()` not called or not imported
- Folders don't expand → `tag_children?prefix=` endpoint not working or template `hx-get` URL wrong
- Count badges missing or unstyled → `.tree-count-badge` CSS rule missing
- "No tags found" when tags exist → SPARQL query failing (check backend logs for errors)
- Clicking folder expands but shows no sub-items → STRSTARTS filter in SPARQL may have wrong prefix format
- 500 error on tag expansion → check backend logs for Python traceback

## Requirements Proved By This UAT

- TAG-04 — Hierarchical tag tree with `/`-delimited nesting at arbitrary depth, lazy-loaded children, count badges, prefix collision handling

## Not Proven By This UAT

- Tag autocomplete (S04 scope)
- E2E Playwright test coverage (S09 scope)
- Performance with very large tag sets (10k+ tags)
- Tag tree appearance in dark mode (visual review deferred)

## Notes for Tester

- Real Ideaverse data has tags like `architect/build`, `architect/renovate`, `garden/cultivate`, `garden/plant`, `garden/probe`, etc. — these are the primary test data for hierarchical nesting
- The tag tree uses the same `initTreeToggle()` JS as other explorer trees — expansion behavior should feel identical to By Type and Hierarchy modes
- Count badges should be right-aligned within the tree node row
