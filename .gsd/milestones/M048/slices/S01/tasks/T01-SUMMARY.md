---
id: T01
parent: S01
milestone: M048
key_files:
  - backend/app/views/service.py
  - backend/tests/test_view_prefix_fix.py
key_decisions:
  - Applied inject_prefixes() at each query construction site rather than at the _client.query() call level to keep the fix surgical and avoid changing the triplestore client interface
duration: 
verification_result: passed
completed_at: 2026-04-05T18:09:32.279Z
blocker_discovered: false
---

# T01: Added inject_prefixes() to all 4 reconstructed SPARQL queries in execute_table_query and execute_cards_query so prefixed names are declared before triplestore execution

**Added inject_prefixes() to all 4 reconstructed SPARQL queries in execute_table_query and execute_cards_query so prefixed names are declared before triplestore execution**

## What Happened

The execute_table_query and execute_cards_query methods in backend/app/views/service.py extract WHERE body and FROM clause from the original scoped SPARQL query, then reconstruct new count/data/subjects queries. These reconstructed queries dropped all PREFIX declarations, causing SPARQL parse errors when the WHERE body used prefixed names like rdf:type, rdfs:label|dcterms:title, dcterms:created, dcterms:modified. The exceptions were silently caught, resulting in zero results and the 'No objects found' empty state. Fixed by importing inject_prefixes from app.sparql.client and wrapping all 4 reconstructed queries (count_query and data_query in execute_table_query; count_query and subjects_query in execute_cards_query) with inject_prefixes() before passing to self._client.query(). Created 6 unit tests verifying prefix injection and non-empty results for both methods.

## Verification

Ran cd backend && python -m pytest tests/test_view_prefix_fix.py tests/test_view_scope.py -v — all 31 tests passed (6 new + 25 existing, zero regressions). LSP diagnostics show no new errors from the changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_view_prefix_fix.py -v` | 0 | ✅ pass | 330ms |
| 2 | `cd backend && python -m pytest tests/test_view_scope.py -v` | 0 | ✅ pass | 360ms |
| 3 | `cd backend && python -m pytest tests/test_view_prefix_fix.py tests/test_view_scope.py -v` | 0 | ✅ pass | 400ms |

## Deviations

ViewSpec dataclass uses renderer_type/target_class fields instead of view_type/model_id as planner assumed — adapted test helper. Line numbers slightly different from plan. Added AsyncMock for label_service.resolve_batch() needed by execute_cards_query.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/service.py`
- `backend/tests/test_view_prefix_fix.py`
