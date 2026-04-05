---
id: S02
parent: M048
milestone: M048
provides:
  - Phantom-event-free save_object() endpoint
  - _normalize_value_for_compare() and _compute_changed_properties() helper functions importable from app.browser.objects
requires:
  []
affects:
  []
key_files:
  - backend/app/browser/objects.py
  - frontend/static/js/workspace.js
  - backend/tests/test_save_diff.py
key_decisions:
  - Extracted diff logic into testable module-level functions (_normalize_value_for_compare, _compute_changed_properties) rather than inlining in save_object()
  - Excluded rdf:type and urn:sempkm:body from current-value comparison as they are not form-managed
  - dcterms:modified only stamped when changed_properties is non-empty — prevents phantom modification timestamps
  - Tests are synchronous since both helpers are pure functions with no I/O
patterns_established:
  - Diff-based save pattern: query current triplestore values → normalize → compare sorted lists → patch only changes
  - Datetime normalization for form↔triplestore comparison: strip timezone, truncate to minute precision to match HTML datetime-local input
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M048/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M048/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T18:29:38.364Z
blocker_discovered: false
---

# S02: Diff-Based Save — No Phantom Events

**Eliminated phantom save events by adding diff-based property filtering to save_object() — only actually-changed properties generate events, and no-op saves create no events at all.**

## What Happened

The save_object() endpoint unconditionally created an object.patch event recording every form property as changed, even when values hadn't changed. This produced phantom events cluttering the event log timeline.

**T01 — Diff-based filtering implementation:** Added two module-level helper functions to objects.py: `_normalize_value_for_compare()` normalizes datetime strings to minute-precision YYYY-MM-DDTHH:MM format to match HTML datetime-local input truncation (strips timezone suffixes and truncates to 16 chars). `_compute_changed_properties()` compares form values against current triplestore values using normalized sorted lists, returning only differing properties. In save_object(), a SPARQL query now fetches current values from the triplestore before building the patch. rdf:type and urn:sempkm:body are excluded from comparison (not form-managed). dcterms:modified is only stamped when real property changes exist. On the client side, saveCurrentObject() in workspace.js now short-circuits the body POST when editor content matches _sempkmSavedContent, avoiding a no-op network call.

**T02 — Unit tests:** Created backend/tests/test_save_diff.py with 22 tests across 3 test classes: TestNormalizeValueForCompare (10 tests covering ISO datetime variants, plain dates, URIs, empty strings), TestComputeChangedProperties (10 tests covering unchanged/changed properties, datetime format normalization, multi-value ordering, new/deleted properties, empty inputs), and TestDctermsModifiedIntegration (2 tests confirming dcterms:modified is only injected when real changes exist). All tests are synchronous since both helpers are pure functions.

## Verification

All slice-level verifications passed:

1. `rg -n '_normalize_value_for_compare' backend/app/browser/objects.py` — found at 3 locations (definition + 2 usages) ✅
2. `rg -n 'changed_properties' backend/app/browser/objects.py` — found at 5 locations ✅
3. `rg -n '_sempkmSavedContent' frontend/static/js/workspace.js | grep -v '= content' | grep -c '_sempkmSavedContent'` — count=1 ✅
4. `python3 -c "import ast; ast.parse(open('backend/app/browser/objects.py').read())"` — syntax OK ✅
5. `cd backend && .venv/bin/python -m pytest tests/test_save_diff.py -v` — 22 passed in 0.64s ✅

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

The diff compares only form-submitted properties against the triplestore. Properties present in the triplestore but not rendered in the form (e.g., properties from a different shape or manually added via SPARQL) are not treated as deletions — the form only manages fields it renders. This is intentional to prevent accidental data loss.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — Added _normalize_value_for_compare(), _compute_changed_properties() helpers and modified save_object() to use diff-based filtering with SPARQL current-value query
- `frontend/static/js/workspace.js` — Added _sempkmSavedContent short-circuit in saveCurrentObject() to skip body POST when content unchanged
- `backend/tests/test_save_diff.py` — New file: 22 unit tests covering datetime normalization, multi-value comparison, new/deleted properties, and dcterms:modified injection guard
