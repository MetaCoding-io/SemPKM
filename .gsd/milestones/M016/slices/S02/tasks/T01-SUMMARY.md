---
id: T01
parent: S02
milestone: M016
provides:
  - Pure field mapping module (6 functions) for Linear→bpkm:Task property conversion
  - GraphQL query builder for paginated issue fetching with optional delta filter
  - Deterministic SHA-256 slug computation for platform-minted Task IRIs
key_files:
  - apps/linear-sync/services/field_mapper.py
  - backend/tests/test_field_mapper.py
key_decisions:
  - Two separate GraphQL query templates (with/without updatedAfter) instead of dynamic string building for clarity
  - Unknown estimate values stringified as-is rather than mapped to a default
patterns_established:
  - importlib path resolution for app module tests: parent.parent.parent / "apps" / "linear-sync" / "services"
  - Full IRI keys for bpkm properties (urn:sempkm:model:basic-pkm:*), compact form only for dcterms
observability_surfaces:
  - none (pure functions — observability deferred to T03 sync engine)
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Build field mapper with full unit tests

**Implemented 6 pure field-mapping functions for Linear→bpkm:Task conversion with 49 unit tests covering all normalization paths, IRI format, date truncation, and GraphQL query construction.**

## What Happened

Created `apps/linear-sync/services/field_mapper.py` with all six functions specified in the plan:

1. `normalize_status()` — maps 5 Linear state types to bpkm statuses, unknown defaults to "todo"
2. `normalize_priority()` — maps Linear 0-4 to bpkm priority strings, returns None for 0/unknown
3. `map_labels_to_tags()` — extracts label names, handles None/empty/missing-name gracefully
4. `compute_issue_slug()` — SHA-256 based deterministic slug (`issue-{hash16}`)
5. `build_task_properties()` — assembles full properties dict with full IRIs, omits None/empty values, truncates dates, handles effort mapping with stringify fallback for unknown estimates
6. `build_issue_query()` — two GraphQL query variants (with/without updatedAfter filter), returns query + variables tuple

The test suite covers 49 cases across 6 test classes, exceeding the ~30 target.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v` — 49/49 passed
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` — syntax valid

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v` | 0 | ✅ pass | 2.8s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | 3.1s |

## Diagnostics

All functions are pure — no logging, no state, no network. To verify mappings hold after ontology changes, run `pytest tests/test_field_mapper.py -v`. The test helper `_make_issue()` provides a complete Linear issue fixture for downstream test files to reference.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/field_mapper.py` — 6 pure functions + constants for Linear→bpkm field mapping (~180 lines)
- `backend/tests/test_field_mapper.py` — 49 unit tests across 6 test classes (~250 lines)
- `.gsd/milestones/M016/slices/S02/S02-PLAN.md` — added diagnostic verification step (preflight fix)
- `.gsd/milestones/M016/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section (preflight fix)
