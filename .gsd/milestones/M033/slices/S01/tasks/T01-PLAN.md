---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: SERVICE clause pass-through and mirrored graph scoping

## Observability Impact

- **Changed signal:** `scope_to_current_graph()` now injects `FROM <urn:sempkm:mirrored>` by default alongside current and inferred graphs. Future agents debugging SPARQL results that include unexpected triples should check whether they originated from the mirrored graph.
- **Inspection:** The `_find_outer_where()` function returns `None` when no outer WHERE is found — callers can detect this to understand why FROM injection was skipped.
- **Failure visibility:** `check_member_query_safety()` now raises 403 with `"SERVICE clauses not allowed for member role"` detail — distinguishable from the existing FROM/GRAPH rejection message.
- **Diagnostic surface:** `_strip_sparql_strings()` continues to blank out string literals and comments before keyword detection, preventing false positives for SERVICE/FROM/GRAPH/WHERE keywords inside quoted text.

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Refactor `scope_to_current_graph()` in `backend/app/sparql/client.py` to handle SPARQL 1.1 SERVICE clauses correctly. Currently the function uses a simple regex to find the WHERE keyword and inject FROM clauses before it. SERVICE clauses contain their own inner `{ ... }` blocks (and often their own WHERE), so the current approach would mangle federated queries by injecting FROM into the wrong position or scoping the remote endpoint's query.

The fix uses brace-depth counting on the string-stripped query to identify which WHERE keyword belongs to the outer query (depth 0) versus inner SERVICE blocks (depth >= 1). FROM clauses are injected only before the outer WHERE.

Also adds `MIRRORED_GRAPH_IRI` to the namespace constants and extends the FROM clause injection to include `urn:sempkm:mirrored` by default.

## Steps

1. **Add `MIRRORED_GRAPH_IRI` to `backend/app/rdf/namespaces.py`:** Add `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` below the existing `INFERRED_GRAPH_IRI`. Add it to `__all__`.

2. **Refactor `scope_to_current_graph()` in `backend/app/sparql/client.py`:**
   - Import `MIRRORED_GRAPH_IRI` from namespaces.
   - Add `MIRRORED_GRAPH = str(MIRRORED_GRAPH_IRI)` constant.
   - Add `include_mirrored: bool = True` parameter to `scope_to_current_graph()`.
   - Replace the simple `re.search(r'\bWHERE\b', query, re.IGNORECASE)` with a brace-depth-aware scanner that finds the *outer* WHERE keyword (the one at brace depth 0, not inside a SERVICE block). The algorithm: iterate through the string-stripped query char by char, tracking brace depth (`{` increments, `}` decrements). When at depth 0, scan for the `WHERE` keyword. This handles SERVICE, OPTIONAL, sub-selects, etc.
   - When `include_mirrored=True`, add `FROM <urn:sempkm:mirrored>` to the injected FROM clause set.
   - **Critical:** The SERVICE clause and its entire `{ ... }` body must pass through completely unchanged. Only the outer query gets FROM clauses.

3. **Update `check_member_query_safety()` to reject SERVICE:**
   - Add a check for `\bSERVICE\s+` on the stripped query. Members cannot use SERVICE (federation requires owner role).

4. **Update `_execute_sparql()` in `backend/app/sparql/router.py`:**
   - Pass `include_mirrored=True` to `scope_to_current_graph()` so mirrored triples are visible in all SPARQL queries by default.

5. **Write comprehensive unit tests in `backend/tests/test_sparql_client.py`:**
   - Add a new `TestServicePassThrough` class with tests:
     - Basic SERVICE query gets FROM injected before outer WHERE, SERVICE block unchanged
     - SERVICE with inner WHERE keyword — FROM not injected at inner WHERE
     - Nested SERVICE (SERVICE inside SERVICE) — both inner blocks unchanged
     - SERVICE inside OPTIONAL — SERVICE block unchanged, outer FROM injected
     - Query with only SERVICE (no outer WHERE body) — handled gracefully
     - SERVICE keyword inside string literal — not detected as real SERVICE
     - SERVICE keyword inside comment — not detected
   - Add tests to `TestScopeToCurrentGraph`:
     - `include_mirrored=True` adds `FROM <urn:sempkm:mirrored>`
     - `include_mirrored=False` omits mirrored graph
   - Add tests to `TestCheckMemberQuerySafety`:
     - SERVICE clause raises 403
     - SERVICE in string literal does not raise
     - SERVICE in comment does not raise

## Must-Haves

- [ ] `MIRRORED_GRAPH_IRI` constant exists in `app.rdf.namespaces`
- [ ] `scope_to_current_graph()` handles SERVICE clauses — FROM injected before outer WHERE only
- [ ] `scope_to_current_graph()` supports `include_mirrored` parameter
- [ ] `check_member_query_safety()` rejects SERVICE for members
- [ ] All existing tests still pass (no regressions)
- [ ] At least 20 new unit tests covering SERVICE pass-through, mirrored graph, and member safety

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all tests pass (existing + new)
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v -k "service or mirrored"` — new tests pass specifically

## Inputs

- `backend/app/rdf/namespaces.py` — existing namespace constants to extend
- `backend/app/sparql/client.py` — existing scope/safety functions to refactor
- `backend/tests/test_sparql_client.py` — existing test file to extend
- `backend/app/sparql/router.py` — existing `_execute_sparql()` to update

## Expected Output

- `backend/app/rdf/namespaces.py` — with `MIRRORED_GRAPH_IRI` added
- `backend/app/sparql/client.py` — with SERVICE-aware `scope_to_current_graph()` and SERVICE-blocking `check_member_query_safety()`
- `backend/app/sparql/router.py` — with `include_mirrored=True` passed to scoping
- `backend/tests/test_sparql_client.py` — with ~25 new tests for SERVICE and mirrored graph
