---
id: T01
parent: S03
milestone: M005
provides:
  - build_tag_tree() pure function for hierarchical tag grouping
key_files:
  - backend/app/browser/tag_tree.py
  - backend/tests/test_tag_tree_builder.py
key_decisions:
  - Pure function with no imports beyond stdlib — enables unit testing without Docker/triplestore
  - Malformed tags (empty segments from //) degrade gracefully (filtered out) rather than raising errors
patterns_established:
  - Tag tree node dict shape: {segment, prefix, direct_count, total_count, has_children}
  - Prefix-based filtering for lazy-loading children at any depth level
observability_surfaces:
  - none (pure function; logging added in T02 when wired into endpoint)
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Implement build_tag_tree() pure function with unit tests

**Created `build_tag_tree()` pure function that transforms flat tag values with counts into hierarchical tree nodes at any prefix depth, with 28 passing unit tests.**

## What Happened

Implemented the core tree-building algorithm in `backend/app/browser/tag_tree.py`. The function takes a flat list of `{"value": "...", "count": N}` dicts and a `prefix` parameter, then groups tags into hierarchical nodes at the specified depth level. Each node contains `segment` (display label), `prefix` (full path for child queries), `direct_count` (exact-match count), `total_count` (direct + all descendants), and `has_children` (whether deeper segments exist).

Key algorithm details:
- Root level (`prefix=""`): extracts first `/`-delimited segment from each tag value
- Nested level (`prefix="garden"`): filters to tags starting with `"garden/"`, strips prefix, extracts next segment
- Prefix collision: when a tag is both a direct value AND a folder parent (e.g. `garden` exists alongside `garden/roses`), the node correctly shows `direct_count > 0` AND `has_children=True`
- Empty segments from malformed tags (`//`) are filtered out gracefully
- Output is sorted alphabetically by segment

Wrote 28 unit tests across 9 test classes covering: edge cases (empty, single), flat tags, single/multi-level nesting, mixed flat+nested, prefix collisions, empty segments, count aggregation, sorting, prefix filtering, and output structure validation.

## Verification

- `python -m pytest tests/test_tag_tree_builder.py -v` — **28/28 passed**
- `from app.browser.tag_tree import build_tag_tree; build_tag_tree([{"value": "a/b", "count": 1}, {"value": "a/c", "count": 2}])` — returns `[{"segment": "a", "prefix": "a", "direct_count": 0, "total_count": 3, "has_children": True}]` ✓

### Slice-level verification (partial — T01 is intermediate):
- ✅ `python -m pytest tests/test_tag_tree_builder.py -v` — all pass
- ⬜ `python -m pytest tests/test_tag_explorer.py -v` — not yet (T02 scope)
- ⬜ Browser verification — not yet (T02 scope)
- ⬜ Failure-path check — not yet (T02 scope)

## Diagnostics

Pure function with no I/O — inspect by importing and calling directly:
```python
from app.browser.tag_tree import build_tag_tree
build_tag_tree([{"value": "x/y", "count": 1}], prefix="x")
```
Invalid inputs raise standard Python exceptions (`KeyError`, `TypeError`). Empty input returns `[]`.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/tag_tree.py` — pure function module (new)
- `backend/tests/test_tag_tree_builder.py` — 28 unit tests across 9 test classes (new)
- `.gsd/milestones/M005/slices/S03/S03-PLAN.md` — added failure-path verification check
- `.gsd/milestones/M005/slices/S03/tasks/T01-PLAN.md` — added Observability Impact section
