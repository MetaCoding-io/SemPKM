---
phase: 34-merge-inferred-properties-into-relations
plan: 01
subsystem: browser-ui
tags: [inferred-properties, object-read, css-cleanup]
dependency_graph:
  requires: []
  provides: [unified-property-table, inline-inferred-badges]
  affects: [object-read-view, workspace-css]
tech_stack:
  added: []
  patterns: [source-tagged-values, merged-read-values-dict]
key_files:
  created: []
  modified:
    - backend/app/browser/router.py
    - backend/app/templates/browser/object_read.html
    - frontend/static/css/workspace.css
decisions:
  - Used separate read_values dict instead of modifying values to preserve edit form compatibility
  - Merged inferred_labels into ref_labels for single lookup instead of dual-dict pattern
metrics:
  duration: 3 min
  completed: 2026-03-10
---

# Quick Task 34: Merge Inferred Properties Into Relations Summary

Unified property table merging inferred properties inline with user-created properties, eliminating two-column layout.

## What Was Done

### Task 1: Merge inferred properties into main values dict in router (d424537)

Built a `read_values` dict in the `load_object` endpoint that merges user-created and inferred properties with source tracking. Each entry is tagged as `{"value": v, "source": "user"}` or `{"value": v, "source": "inferred"}`. The original `values` dict is preserved untouched for the edit form and property count badge. Also merged `inferred_labels` into `ref_labels` so the template has a single label lookup dict.

### Task 2: Update object_read template and remove inferred column CSS (d2720a3)

Rewrote `object_read.html` to use `read_values` instead of separate `values` + `inferred_values` dicts. All property types (reference, date, boolean, URI, tags, plain text) now iterate `item.value` and conditionally show an `inferred-badge` when `item.source == "inferred"`. Added a section after form-defined properties that renders inferred-only properties (predicates not in the SHACL form) with their resolved labels.

Removed 80 lines of two-column layout CSS from `workspace.css`: `.object-read-columns`, `.object-read-columns--single`, `.object-read-user-column`, `.inferred-column` and all child selectors, plus the responsive media query. Preserved the shared `.inferred-badge`, `.relation-item .inferred-badge`, and `.inferred-stale` rules used by the relations panel and inference tab.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- Template block balance verified (21 if/endif, 14 for/endfor)
- Router syntax verified via ast.parse
- Zero CSS matches for `inferred-column` confirmed
- `.inferred-badge` CSS preserved (4 rules remain)
- Edit form compatibility preserved (original `values` dict unchanged)
