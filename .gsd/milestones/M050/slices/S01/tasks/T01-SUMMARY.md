---
id: T01
parent: S01
milestone: M050
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_compatible_types.py
key_decisions:
  - Unfiltered renderers (table, card, graph, quadrant, bmc, okr, decision-matrix) return all types — no false restriction
  - Unknown renderer names return all types as safe fallback
duration: 
verification_result: passed
completed_at: 2026-04-05T21:30:45.819Z
blocker_discovered: false
---

# T01: Add get_compatible_types() to ViewSpecService with JSON endpoint and renderer-filtered type lists in generic_view()

**Add get_compatible_types() to ViewSpecService with JSON endpoint and renderer-filtered type lists in generic_view()**

## What Happened

Added `get_compatible_types(renderer, exclude_iris)` method to ViewSpecService that leverages existing SHACL detection methods (_detect_status_field, _detect_date_fields, _detect_geo_fields) to filter types by renderer compatibility. Added GET /browser/views/compatible-types?renderer=X endpoint returning JSON. Updated generic_view() to pass renderer-filtered types to templates instead of all types.

## Verification

Ran 10 unit tests covering all renderer filter paths (table/card/graph return all, kanban filters to status types, calendar/timeline filter to date types, map filters to geo types), plus exclude_iris, no-shapes-service, and unknown-renderer edge cases. All 10 passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_compatible_types.py -v` | 0 | ✅ pass | 620ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/tests/test_compatible_types.py`
