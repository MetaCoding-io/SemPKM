---
id: T01
parent: S01
milestone: M054
key_files:
  - backend/app/browser/explorer_config.py
  - backend/tests/test_explorer_config.py
  - backend/app/browser/workspace.py
key_decisions:
  - Reuse _LABEL_OPTIONALS/_LABEL_COALESCE from strategies.py — no duplication
  - Tag grouping uses UNION across known tag predicates
  - Config-options endpoint flags sh:in properties as preferred_group
duration: 
verification_result: passed
completed_at: 2026-04-06T04:20:41.652Z
blocker_discovered: false
---

# T01: Created ExplorerConfig dataclass with composable SPARQL query builder and config-options JSON endpoint for the explorer config UI

**Created ExplorerConfig dataclass with composable SPARQL query builder and config-options JSON endpoint for the explorer config UI**

## What Happened

Built the backend foundation for the composable explorer: an ExplorerConfig dataclass with filter/group/sort fields, two SPARQL query builders (build_explorer_query for object listing, build_group_folders_query for folder counts), and a GET /browser/explorer/config-options endpoint that returns available types, built-in group/sort options, and per-type SHACL property lists. Label resolution reuses _LABEL_OPTIONALS/_LABEL_COALESCE from strategies.py. All IRI interpolation uses safe_iri(). 20 unit tests cover all config combinations.

## Verification

Ran pytest tests/test_explorer_config.py — all 20 tests pass. Verified module imports and endpoint registration.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py -v` | 0 | ✅ pass | 170ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/explorer_config.py`
- `backend/tests/test_explorer_config.py`
- `backend/app/browser/workspace.py`
