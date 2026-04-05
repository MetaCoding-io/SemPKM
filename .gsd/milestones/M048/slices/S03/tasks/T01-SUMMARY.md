---
id: T01
parent: S03
milestone: M048
key_files:
  - backend/app/browser/objects.py
  - backend/tests/test_object_delete_inbound.py
key_decisions:
  - Moved empty-bindings guard to check combined materialize_deletes list instead of early-exiting on empty outbound bindings alone
duration: 
verification_result: passed
completed_at: 2026-04-05T18:40:16.375Z
blocker_discovered: false
---

# T01: Added inbound edge SPARQL query to bulk_delete_objects() so deleting an object also removes all triples referencing it, preventing dangling references

**Added inbound edge SPARQL query to bulk_delete_objects() so deleting an object also removes all triples referencing it, preventing dangling references**

## What Happened

Added a second SPARQL query inside bulk_delete_objects() that selects inbound edges (?s ?p <iri>) and appends them to the same materialize_deletes list as outbound triples. Fixed the empty-bindings guard to check after both queries so objects with only inbound references are still cleaned up. Wrapped in the same try/except pattern for graceful degradation. Created 7 unit tests covering inbound edge inclusion, outbound regression, query failure handling, and edge cases.

## Verification

Ran cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v — all 7 tests passed in 0.66s. LSP diagnostics showed no new errors from the changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v` | 0 | ✅ pass | 660ms |

## Deviations

Moved the empty-bindings guard from after the outbound query to after both queries (if not materialize_deletes: continue), ensuring objects with only inbound references are cleaned up. This is a correctness improvement beyond the task plan.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/objects.py`
- `backend/tests/test_object_delete_inbound.py`
