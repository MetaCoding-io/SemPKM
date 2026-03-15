---
estimated_steps: 5
estimated_files: 2
---

# T01: Implement build_tag_tree() pure function with unit tests

**Slice:** S03 — Hierarchical Tag Tree
**Milestone:** M005

## Description

Create the `build_tag_tree()` pure function that transforms a flat list of tag values with counts into hierarchical tree nodes at a specified prefix level. This is the core algorithm for the hierarchical tag tree — separated as a pure function for easy unit testing without any Docker/triplestore dependencies.

The function handles: root-level extraction (first `/` segment), prefix-filtered children (strip prefix, extract next segment), tags that are both a leaf AND a folder parent, empty intermediate segments, and tags with no `/` delimiter.

## Steps

1. Create `backend/app/browser/tag_tree.py` with `build_tag_tree(tag_values: list[dict], prefix: str = "") -> list[dict]`:
   - Input: `[{"value": "garden/cultivate/roses", "count": 3}, {"value": "garden", "count": 1}, ...]`
   - When `prefix=""` (root): extract first segment from each value (before first `/`), group by segment
   - When `prefix="garden"`: filter to values starting with `"garden/"`, strip prefix, extract next segment, group
   - For each resulting segment, compute:
     - `segment`: the folder label at this level (e.g. `"garden"`)
     - `prefix`: full prefix path (e.g. `"garden"` at root, `"garden/cultivate"` at level 2)
     - `direct_count`: objects tagged exactly with this prefix value (0 if only a folder)
     - `total_count`: sum of counts for this prefix and all descendants
     - `has_children`: whether deeper segments exist beyond this level
   - Sort output by segment alphabetically
   - Filter out empty segments (from `//` in tags)

2. Write comprehensive unit tests in `backend/tests/test_tag_tree_builder.py`:
   - Flat tags only (no `/`) — each tag is a root node with `has_children=False`
   - Single-level nesting (`garden/roses`) — `garden` is a folder with child `roses`
   - Multi-level nesting (`garden/cultivate/roses`) — 3 levels deep
   - Mixed flat + nested — tag `cooking` alongside `garden/roses`
   - Prefix collision — tag `garden` exists AND `garden/roses` exists: `garden` node has `direct_count > 0` AND `has_children=True`
   - Children query — call with `prefix="garden"` to get next-level nodes
   - Empty intermediate segments — tag `garden//roses` filtered cleanly
   - Single tag — one tag value produces one root node
   - No tags — returns empty list
   - Count aggregation — `garden/roses: 5` + `garden/tulips: 3` → `garden` total_count = 8

## Must-Haves

- [ ] `build_tag_tree()` is a pure function (no I/O, no async, no imports beyond stdlib)
- [ ] Prefix collision case handled: a tag value that is both a direct tag AND a folder parent
- [ ] Count aggregation is correct: total_count = direct_count + sum of all descendant counts
- [ ] Output sorted alphabetically by segment
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_tag_tree_builder.py -v` — all tests pass
- `python -c "from app.browser.tag_tree import build_tag_tree; print(build_tag_tree([{'value': 'a/b', 'count': 1}, {'value': 'a/c', 'count': 2}]))"` — returns expected structure

## Observability Impact

- **Signals changed:** None (pure function, no I/O or logging). Logging is added in T02 when this function is wired into the endpoint.
- **How to inspect:** Import and call `build_tag_tree()` directly in a Python REPL or test to verify grouping/counting behavior for any tag dataset.
- **Failure visibility:** Invalid inputs (non-list, missing keys) raise standard Python exceptions (`KeyError`, `TypeError`) — no silent failures. Empty input returns `[]`. Malformed tags (e.g. `//`) are filtered out cleanly.

## Inputs

- S03-RESEARCH.md design section for algorithm specification
- No prior task outputs (this is T01)

## Expected Output

- `backend/app/browser/tag_tree.py` — pure function module
- `backend/tests/test_tag_tree_builder.py` — comprehensive unit tests (10+ test cases)
