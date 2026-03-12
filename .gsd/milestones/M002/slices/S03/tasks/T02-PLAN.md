---
estimated_steps: 3
estimated_files: 1
---

# T02: Write SPARQL client tests — string stripping, graph scoping, and member safety

**Slice:** S03 — Backend Test Foundation
**Milestone:** M002

## Description

Write comprehensive tests for the three SPARQL client safety functions: `_strip_sparql_strings()`, `scope_to_current_graph()`, and `check_member_query_safety()`. These are the most injection-sensitive code paths in the backend. The COR-02 edge case (keywords inside string literals) is a critical test target — S02 hardened these functions specifically to handle it, and this task proves that hardening works.

## Steps

1. Create `backend/tests/test_sparql_client.py` with imports from `app.sparql.client` for `_strip_sparql_strings`, `scope_to_current_graph`, `check_member_query_safety`, and from `app.rdf.namespaces` for `CURRENT_GRAPH_IRI`.
2. Write `_strip_sparql_strings()` tests:
   - Double-quoted string interior blanked, delimiters preserved.
   - Single-quoted string interior blanked.
   - Triple-quoted (both `"""` and `'''`) string interior blanked.
   - Hash comment replaced with spaces.
   - Escaped quote inside string does not break parsing.
   - Mixed: query with strings, comments, and real keywords — only real keywords survive.
3. Write `scope_to_current_graph()` tests:
   - Basic query gets FROM `<urn:sempkm:current>` injected before WHERE.
   - `all_graphs=True` returns query unchanged.
   - Query with existing FROM clause returned unchanged.
   - Query with GRAPH clause referencing CURRENT_GRAPH returned unchanged.
   - `include_inferred=True` (default) adds FROM `<urn:sempkm:inferred>`.
   - `include_inferred=False` omits inferred graph.
   - `shared_graphs` parameter adds additional FROM clauses.
   - **COR-02 edge case**: query with `FROM` inside a string literal still gets scoped (not treated as already having FROM).
   - Query without WHERE clause returned as-is.
4. Write `check_member_query_safety()` tests:
   - Clean SELECT query passes without exception.
   - Query with FROM clause raises HTTPException 403.
   - Query with GRAPH clause raises HTTPException 403.
   - **COR-02 edge case**: query with FROM/GRAPH inside a string literal does NOT raise (false positive prevention).
   - Query with FROM/GRAPH in a hash comment does NOT raise.

## Must-Haves

- [ ] `_strip_sparql_strings()` tested with all 4 SPARQL string forms + comments
- [ ] `scope_to_current_graph()` tested for injection, bypass conditions, shared graphs, and COR-02 edge case
- [ ] `check_member_query_safety()` tested for rejection and false-positive prevention
- [ ] COR-02 edge case explicitly tested in both `scope_to_current_graph` and `check_member_query_safety`

## Verification

- `cd backend && .venv/bin/pytest tests/test_sparql_client.py -v` — all pass
- At least 15 tests total across the three function groups

## Observability Impact

- Signals added/changed: None (pure test code)
- How a future agent inspects this: run `pytest tests/test_sparql_client.py -v` — each test name describes the edge case it covers
- Failure state exposed: assertion diffs show exact string comparison failures for SPARQL output

## Inputs

- `backend/app/sparql/client.py` — `_strip_sparql_strings()`, `scope_to_current_graph()`, `check_member_query_safety()` functions to test
- `backend/app/rdf/namespaces.py` — `CURRENT_GRAPH_IRI` constant for building test expectations
- `backend/tests/conftest.py` — from T01, provides settings isolation
- S02 summary — confirms `_strip_sparql_strings()` was created to fix the COR-02 edge case

## Expected Output

- `backend/tests/test_sparql_client.py` — created with 15+ tests covering string stripping, graph scoping (including COR-02), and member query safety
