---
id: T01
parent: S02
milestone: M048
key_files:
  - backend/app/browser/objects.py
  - frontend/static/js/workspace.js
key_decisions:
  - Extracted diff logic into testable module-level functions (_normalize_value_for_compare, _compute_changed_properties) for T02 unit testing
  - Excluded rdf:type and urn:sempkm:body from current-value comparison as they are not form-managed
  - dcterms:modified only stamped when changed_properties is non-empty
duration: 
verification_result: passed
completed_at: 2026-04-05T18:26:09.127Z
blocker_discovered: false
---

# T01: Added diff-based property filtering to save_object() and client-side body save short-circuit to eliminate phantom events

**Added diff-based property filtering to save_object() and client-side body save short-circuit to eliminate phantom events**

## What Happened

Implemented three changes to eliminate phantom save events: (1) Added _normalize_value_for_compare() helper that normalizes datetime strings to minute-precision YYYY-MM-DDTHH:MM format to match HTML datetime-local input truncation. (2) Added _compute_changed_properties() that compares form values against triplestore current values using normalized sorted lists, returning only differing properties. (3) Modified save_object() to query current triplestore values, compute the diff, and only create ObjectPatchParams for actually-changed properties. dcterms:modified is only injected when real changes exist. (4) Added client-side body save short-circuit in saveCurrentObject() that skips the body POST when editor content matches _sempkmSavedContent.

## Verification

All task verification commands passed: _normalize_value_for_compare found at 3 locations in objects.py, changed_properties found at 5 locations, _sempkmSavedContent short-circuit check found (count=1). Python syntax validation passed. LSP diagnostics show no new errors.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg -n '_normalize_value_for_compare' backend/app/browser/objects.py` | 0 | ✅ pass | 100ms |
| 2 | `rg -n 'changed_properties' backend/app/browser/objects.py` | 0 | ✅ pass | 100ms |
| 3 | `rg -n '_sempkmSavedContent' frontend/static/js/workspace.js | grep -v '= content' | grep -c '_sempkmSavedContent'` | 0 | ✅ pass | 100ms |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/browser/objects.py').read())"` | 0 | ✅ pass | 200ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/objects.py`
- `frontend/static/js/workspace.js`
