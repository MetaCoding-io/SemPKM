---
id: T02
parent: S03
milestone: M002
provides:
  - 23 unit tests covering _strip_sparql_strings(), scope_to_current_graph(), check_member_query_safety()
  - COR-02 edge case regression tests (keywords inside string literals)
key_files:
  - backend/tests/test_sparql_client.py
key_decisions: []
patterns_established:
  - Import CURRENT_GRAPH_IRI/INFERRED_GRAPH_IRI from namespaces and str() them for test assertions
  - Use pytest.raises(HTTPException) with status_code check for 403 rejection tests
observability_surfaces:
  - "Run `cd backend && .venv/bin/pytest tests/test_sparql_client.py -v` — each test name describes the edge case it covers"
duration: 5m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Write SPARQL client tests — string stripping, graph scoping, and member safety

**Wrote 23 passing tests covering all three SPARQL client safety functions including COR-02 edge case regression tests.**

## What Happened

Created `backend/tests/test_sparql_client.py` with three test classes:

- **TestStripSparqlStrings** (7 tests): double-quoted, single-quoted, triple-double-quoted, triple-single-quoted strings all get interiors blanked with delimiters preserved. Hash comments replaced with spaces. Escaped quotes inside strings handled correctly. Mixed query with strings + comments + real keywords — only real keywords survive.

- **TestScopeToCurrentGraph** (9 tests): basic FROM injection before WHERE, all_graphs bypass, existing FROM clause skip, GRAPH+CURRENT_GRAPH skip, include_inferred=True adds inferred graph, include_inferred=False omits it, shared_graphs adds additional FROM clauses, no WHERE clause returns as-is. COR-02 edge case: FROM inside a string literal does NOT prevent scoping.

- **TestCheckMemberQuerySafety** (7 tests): clean SELECT passes, FROM raises 403, GRAPH raises 403. COR-02 false positive prevention: FROM in string literal does NOT raise, GRAPH in string literal does NOT raise, FROM in hash comment does NOT raise, GRAPH in hash comment does NOT raise.

## Verification

- `cd backend && .venv/bin/pytest tests/test_sparql_client.py -v` — 23 passed in 0.21s
- `cd backend && .venv/bin/pytest tests/ -v` — 57 passed in 0.27s (full suite including T01 tests)
- COR-02 edge case explicitly tested in both scope_to_current_graph and check_member_query_safety

### Slice-level checks (intermediate — T02 of T04):
- ✅ `cd backend && .venv/bin/pytest tests/ -v` — all 57 tests pass
- ✅ 0 failures
- ✅ 3 test modules with 5+ tests each (test_sparql_utils: 19, test_rdf_serialization: 15, test_sparql_client: 23)
- ⬜ 5 test modules with 5+ each — need T03 (test_iri_validation) and T04 (test_auth_tokens)
- ✅ No Docker/triplestore dependency

## Diagnostics

Run `cd backend && .venv/bin/pytest tests/test_sparql_client.py -v` — each test name describes the edge case it covers. Use `--tb=long` for full tracebacks on failure.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_sparql_client.py` — created with 23 tests across 3 test classes covering string stripping, graph scoping, and member query safety
