---
id: T02
parent: S02
milestone: M048
key_files:
  - backend/tests/test_save_diff.py
key_decisions:
  - Tests are synchronous since both helpers are pure functions with no I/O
duration: 
verification_result: passed
completed_at: 2026-04-05T18:28:00.584Z
blocker_discovered: false
---

# T02: Added 22 unit tests for _normalize_value_for_compare and _compute_changed_properties covering datetime normalization, multi-value ordering, new/deleted properties, and dcterms:modified injection guard

**Added 22 unit tests for _normalize_value_for_compare and _compute_changed_properties covering datetime normalization, multi-value ordering, new/deleted properties, and dcterms:modified injection guard**

## What Happened

Created backend/tests/test_save_diff.py with three test classes (TestNormalizeValueForCompare, TestComputeChangedProperties, TestDctermsModifiedIntegration) totaling 22 tests. Covers all edge cases: datetime format normalization across ISO/Z/offset/local variants, multi-value order-insensitive comparison, new and deleted properties, empty inputs, original value preservation, and the dcterms:modified conditional injection pattern used in save_object(). Both helpers were already extracted as module-level functions in T01, so no changes to objects.py were needed.

## Verification

Ran `cd backend && .venv/bin/python -m pytest tests/test_save_diff.py -v` — all 22 tests passed in 0.67s. Verified objects.py syntax validity with ast.parse.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_save_diff.py -v` | 0 | ✅ pass | 670ms |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/browser/objects.py').read())"` | 0 | ✅ pass | 100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_save_diff.py`
