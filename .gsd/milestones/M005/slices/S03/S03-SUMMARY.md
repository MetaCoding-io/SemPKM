---
id: S03
parent: M005
milestone: M005
provides:
  - Hierarchical tag tree with `/`-delimited nesting at arbitrary depth in By Tag explorer
  - build_tag_tree() pure function for flat→hierarchical tag grouping
  - tag_children endpoint extended with prefix parameter for lazy sub-folder loading
  - tag_tree_folder.html recursive template for nested folder rendering
  - tree-count-badge CSS class for count pills
requires: []
affects:
  - S04 (tag autocomplete — reuses tag query infrastructure)
  - S09 (E2E tests + docs)
key_files:
  - backend/app/browser/tag_tree.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/tag_tree.html
  - backend/app/templates/browser/tag_tree_folder.html
  - frontend/static/css/workspace.css
  - backend/tests/test_tag_tree_builder.py
  - backend/tests/test_tag_explorer.py
key_decisions:
  - D084: Fetch flat, nest in Python, lazy-load children — reuses existing SPARQL, pure function is unit-testable
  - D085: Extended existing tag_children endpoint with prefix param rather than new endpoint
  - D086: build_tag_tree() in separate module to keep workspace.py from growing
patterns_established:
  - Tag tree node dict shape: {segment, prefix, direct_count, total_count, has_children}
  - Prefix-based filtering for lazy-loading children at any depth level
  - tag_tree_folder.html renders both sub-folder and leaf nodes with same tree-node/tree-children pattern for initTreeToggle() compatibility
  - tree-count-badge CSS class for count pills in explorer tree (margin-left:auto pushes to right edge)
observability_surfaces:
  - logger.debug("By-tag explorer: %d root nodes", ...) in _handle_by_tag
  - logger.debug("Tag children for prefix '%s': %d sub-nodes, %d direct objects", ...) in tag_children prefix path
  - HTTP 400 with "Missing required parameter: tag or prefix" when neither param provided
drill_down_paths:
  - .gsd/milestones/M005/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M005/slices/S03/tasks/T02-SUMMARY.md
duration: 50m
verification_result: passed
completed_at: 2026-03-14
---

# S03: Hierarchical Tag Tree

**By Tag explorer now nests tags at arbitrary depth using `/` as delimiter, with lazy-loaded sub-folders, count badges, and correct handling of tags that are both leaves and folder prefixes.**

## What Happened

**T01** created a pure function `build_tag_tree()` in `backend/app/browser/tag_tree.py` that transforms flat tag-count data into hierarchical tree nodes. The function takes `[{"value": "...", "count": N}]` and a `prefix` parameter, returning nodes with `{segment, prefix, direct_count, total_count, has_children}`. It handles: root extraction (first `/` segment), prefix-filtered children, tags that are both leaf AND folder (prefix collision), empty intermediate segments from malformed tags (`//`), and alphabetical sorting. 28 unit tests across 9 test classes cover all edge cases.

**T02** wired the pure function into the live explorer. `_handle_by_tag()` now passes SPARQL results through `build_tag_tree()` before rendering. The `tag_children` endpoint gained an optional `prefix` parameter: when provided, it runs SPARQL with `STRSTARTS` filter for descendant tags, passes through `build_tag_tree(results, prefix)`, and renders the new `tag_tree_folder.html` template. When only `tag` is provided, existing exact-match behavior is preserved. The endpoint also fetches direct objects tagged with the exact prefix value for tags that are both folders and direct tags. Updated `tag_tree.html` renders hierarchical root nodes with folder/tag icons and count badges. Added `.tree-count-badge` CSS rule and 12 new tests.

## Verification

- `backend/.venv/bin/pytest tests/test_tag_tree_builder.py -v` — **28/28 passed**
- `backend/.venv/bin/pytest tests/test_tag_explorer.py -v` — **33/33 passed**
- Browser: "By Tag" mode shows hierarchical folders with counts
  - `architect` (9) → expands to `#build` (7), `#renovate` (2)
  - `garden` (39) → expands to sub-folders with correct counts
  - Flat tags (no `/`) work as single-level folders
  - Leaf tags expand to show tagged objects with type icons
- Failure path: `/explorer/tag-children?prefix=nonexistent` → "No tags found" (no crash)
- Missing params: `/explorer/tag-children` → HTTP 400 "Missing required parameter"

## Requirements Advanced

- TAG-04 — Hierarchical tag tree: By Tag explorer nests tags at arbitrary depth using `/` as delimiter with lazy-loaded children (new requirement, validated by this slice)

## Requirements Validated

- TAG-04 — Browser verification confirms multi-level nesting with real Ideaverse data; 61 unit tests pass

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None.

## Known Limitations

- Tag tree performance with very large tag sets (10k+) not benchmarked — lazy loading mitigates but STRSTARTS queries may slow
- No search/filter within the tag tree (deferred to S04 autocomplete)

## Follow-ups

- S04: Tag autocomplete can reuse the tag query infrastructure and existing tag values endpoint
- S09: E2E Playwright tests and user guide updates for the tag tree

## Files Created/Modified

- `backend/app/browser/tag_tree.py` — pure function module for hierarchical tag grouping (new)
- `backend/tests/test_tag_tree_builder.py` — 28 unit tests across 9 test classes (new)
- `backend/app/browser/workspace.py` — imported `build_tag_tree`, modified `_handle_by_tag()`, extended `tag_children()` with `prefix` parameter
- `backend/app/templates/browser/tag_tree.html` — rewritten for hierarchical root nodes with folder/tag icons
- `backend/app/templates/browser/tag_tree_folder.html` — new recursive sub-folder template
- `frontend/static/css/workspace.css` — added `.tree-count-badge` CSS rule
- `backend/tests/test_tag_explorer.py` — extended with 12 hierarchy and prefix parameter tests

## Forward Intelligence

### What the next slice should know
- `build_tag_tree()` is a pure function with zero external dependencies — it can be called from anywhere to transform flat tag data into hierarchical nodes
- The tag_children endpoint already returns all existing tag values when called without prefix — S04 autocomplete can reuse this SPARQL pattern
- Tag values in the triplestore come from both `bpkm:tags` and `schema:keywords` — any autocomplete must query both via UNION

### What's fragile
- `tag_tree_folder.html` relies on `initTreeToggle()` JS from workspace.js — if that function's selector targeting changes, folder expansion breaks
- The STRSTARTS SPARQL filter for prefix matching is case-sensitive — tags stored with inconsistent casing will appear as separate tree branches

### Authoritative diagnostics
- `backend/.venv/bin/pytest tests/test_tag_tree_builder.py tests/test_tag_explorer.py -v` — 61 tests, <1s, covers all edge cases
- Browser network tab: `/explorer/tag-children?prefix=...` requests show the lazy-loading chain

### What assumptions changed
- No assumptions changed — the implementation followed the plan closely
