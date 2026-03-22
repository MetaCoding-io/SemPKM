---
id: T01
parent: S01
milestone: M033
provides:
  - MIRRORED_GRAPH_IRI constant in app.rdf.namespaces
  - Brace-depth-aware _find_outer_where() for SERVICE-safe FROM injection
  - include_mirrored parameter on scope_to_current_graph()
  - SERVICE clause rejection in check_member_query_safety()
  - 34 new unit tests for SERVICE pass-through, mirrored graph, and member safety
key_files:
  - backend/app/rdf/namespaces.py
  - backend/app/sparql/client.py
  - backend/app/sparql/router.py
  - backend/tests/test_sparql_client.py
key_decisions:
  - Brace-depth counting on string-stripped query to find outer WHERE — handles SERVICE, OPTIONAL, sub-selects uniformly
  - include_mirrored defaults to True so mirrored triples are visible in all queries without caller changes
  - Added urn:sempkm:mirrored: to _VOCAB_PREFIXES so mirrored provenance IRIs aren't enriched as user objects
patterns_established:
  - _find_outer_where() iterates stripped query tracking { } depth; only returns WHERE at depth 0
observability_surfaces:
  - check_member_query_safety raises 403 with distinct "SERVICE clauses not allowed" detail message
  - scope_to_current_graph injects FROM <urn:sempkm:mirrored> by default — visible in logger.debug SPARQL output
duration: 12min
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: SERVICE clause pass-through and mirrored graph scoping

**Refactored scope_to_current_graph() with brace-depth-aware WHERE detection for SERVICE clause safety, added MIRRORED_GRAPH_IRI constant and include_mirrored parameter, blocked SERVICE for member role**

## What Happened

Added `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` to `backend/app/rdf/namespaces.py` and exported it in `__all__`.

Replaced the simple `re.search(r'\bWHERE\b', ...)` in `scope_to_current_graph()` with a new `_find_outer_where()` helper that uses brace-depth counting on the string-stripped query. The algorithm iterates character by character, incrementing depth on `{` and decrementing on `}`. Only when depth is 0 does it check for the WHERE keyword. This correctly skips WHERE keywords inside SERVICE blocks, OPTIONAL blocks, sub-selects, and CONSTRUCT templates.

Added `include_mirrored: bool = True` parameter to `scope_to_current_graph()` — when True, injects `FROM <urn:sempkm:mirrored>` alongside the current and inferred graphs. Updated `_execute_sparql()` in router.py to pass `include_mirrored=True`.

Extended `check_member_query_safety()` to reject `SERVICE` clauses (federation requires owner role), using the same string-stripping approach that already handles FROM/GRAPH false positives in string literals and comments.

Added `urn:sempkm:mirrored:` to `_VOCAB_PREFIXES` in router.py so mirrored provenance IRIs aren't treated as user data objects during result enrichment.

Wrote 34 new unit tests across 4 test classes: `TestFindOuterWhere` (8 tests), `TestServicePassThrough` (10 tests), `TestMirroredGraph` (6 tests), and 3 new tests in `TestCheckMemberQuerySafety` for SERVICE handling. All 50 tests (16 existing + 34 new) pass.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — 50/50 passed
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v -k "service or mirrored"` — 20/20 passed
- `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` — constant exists and exported
- No regressions in existing test suite

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` | 0 | ✅ pass | 0.23s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v -k "service or mirrored"` | 0 | ✅ pass | 0.19s |
| 3 | `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- `_find_outer_where()` is exported from `client.py` and can be tested in isolation — pass any SPARQL query string and inspect the returned index.
- `check_member_query_safety()` error messages distinguish SERVICE rejection from FROM/GRAPH rejection by detail text.
- `scope_to_current_graph()` results are logged via `logger.debug("Executing SPARQL: %s", processed[:200])` in `_execute_sparql()`.

## Deviations

- Added `urn:sempkm:mirrored:` to `_VOCAB_PREFIXES` in router.py — not in the task plan but needed to prevent mirrored provenance IRIs from being enriched as user objects in SPARQL results.

## Known Issues

None.

## Files Created/Modified

- `backend/app/rdf/namespaces.py` — added MIRRORED_GRAPH_IRI constant and __all__ export
- `backend/app/sparql/client.py` — added _find_outer_where(), refactored scope_to_current_graph() with brace-depth WHERE detection and include_mirrored param, added SERVICE rejection to check_member_query_safety()
- `backend/app/sparql/router.py` — passed include_mirrored=True to scope_to_current_graph(), added urn:sempkm:mirrored: to _VOCAB_PREFIXES
- `backend/tests/test_sparql_client.py` — added 34 new tests across TestFindOuterWhere, TestServicePassThrough, TestMirroredGraph, and TestCheckMemberQuerySafety
- `.gsd/milestones/M033/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section per pre-flight requirement
