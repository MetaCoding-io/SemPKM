---
id: S03
parent: M048
milestone: M048
provides:
  - deleteObject(iri, label) function exported as window.SemPKM.deleteObject
  - Inbound edge cleanup in bulk_delete_objects() — no dangling references after delete
requires:
  - slice: S01
    provides: Table/Cards views render correctly for verifying delete removes objects from views
affects:
  []
key_files:
  - backend/app/browser/objects.py
  - backend/tests/test_object_delete_inbound.py
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/object_tab.html
  - backend/app/templates/browser/tree_children.html
  - frontend/static/css/workspace.css
key_decisions:
  - D384: bulk_delete_objects cascades to inbound edges (triples where deleted IRI is the object)
  - Placed delete button between star-btn and properties-toggle for consistent toolbar grouping
  - Moved empty-bindings guard to check combined materialize_deletes list instead of early-exiting on empty outbound bindings alone
patterns_established:
  - Shared deleteObject(iri, label) function pattern: confirmation dialog → API call → close tab → refresh tree → toast. Reusable for any future single-object destructive action.
  - Three-surface action wiring: toolbar button + command palette + explorer hover action, all calling the same exported SemPKM.* function
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M048/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M048/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T18:44:34.037Z
blocker_discovered: false
---

# S03: Object Delete UI

**Single-object delete works from object toolbar, explorer tree hover action, and command palette, with backend inbound edge cleanup preventing dangling references.**

## What Happened

This slice delivered full single-object delete functionality across three UI surfaces, backed by a correctness fix to the backend delete logic.

**T01 — Backend inbound edge cleanup:** The existing `bulk_delete_objects()` only deleted triples where the deleted IRI was the subject (`<iri> ?p ?o`). A second SPARQL query now also collects inbound edges (`?s ?p <iri>`) and appends them to the same `materialize_deletes` list, so they're part of the same Operation and audit trail. The empty-bindings guard was moved from after the outbound query to after both queries, fixing a subtle bug where objects with only inbound references (no outbound triples) would have been silently skipped. 7 unit tests cover inbound edge inclusion, outbound regression, query failure handling, and edge cases.

**T02 — Frontend delete UI on three surfaces:**
1. **Object toolbar** — `.delete-btn` with trash-2 Lucide icon, placed between star button and properties toggle. CSS follows the `.star-btn` pattern per CLAUDE.md conventions (flex-shrink: 0, stroke: currentColor, CSS-only sizing).
2. **Command palette** — 'Delete Object' entry in the Objects section. Uses `getActiveTabIri()` and skips `view:` prefixed tabs. Gets label from `_tabMeta` for the confirmation dialog.
3. **Explorer tree** — `.tree-leaf-action` hover button using existing CSS (opacity 0→1 on hover, red on action hover).

All three surfaces call the shared `deleteObject(iri, label)` function which shows a confirmation dialog via `showConfirmDialog()`, calls `/browser/objects/delete` with `{ iris: [iri] }`, then closes the tab, refreshes the nav tree, and shows a success toast. The function is exported as `window.SemPKM.deleteObject` for cross-template access.

## Verification

All slice-level verifications passed:
1. Backend tests: `cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v` — 7/7 passed (0.67s)
2. Frontend checks: grep confirmed `function deleteObject` in workspace.js, `delete-btn` in object_tab.html, `delete-object` command ID in workspace.js, `deleteObject` in tree_children.html, `.delete-btn` in workspace.css — all present
3. SemPKM.deleteObject exported at line 3852 of workspace.js

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Moved the empty-bindings guard in bulk_delete_objects() from after the outbound query to after both queries (outbound + inbound). This is a correctness improvement beyond the plan — objects with only inbound references are now properly cleaned up rather than silently skipped.

## Known Limitations

The slice plan mentions T01 verify path as `cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v` which assumes CWD is project root. The actual backend venv is at `backend/.venv/bin/python`. Task executors used the correct path.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — Added inbound edge SPARQL query to bulk_delete_objects() and moved empty-bindings guard after both queries
- `backend/tests/test_object_delete_inbound.py` — New: 7 unit tests covering inbound edge cleanup, outbound regression, query failure handling
- `frontend/static/js/workspace.js` — Added deleteObject() function, command palette 'Delete Object' entry, window.SemPKM.deleteObject export
- `backend/app/templates/browser/object_tab.html` — Added .delete-btn with trash-2 icon to object toolbar
- `backend/app/templates/browser/tree_children.html` — Added .tree-leaf-action delete button for explorer hover
- `frontend/static/css/workspace.css` — Added .delete-btn styles following .star-btn pattern
