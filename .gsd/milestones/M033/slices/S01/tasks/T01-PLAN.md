---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Extend scope_to_current_graph() for SERVICE pass-through and mirrored graph

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

The `scope_to_current_graph()` function in `backend/app/sparql/client.py` injects `FROM <urn:sempkm:current>` (and optionally `FROM <urn:sempkm:inferred>`) before the `WHERE` keyword in SPARQL queries. This is a security/scoping mechanism to prevent queries from accessing event graphs.

The problem: SPARQL SERVICE clauses contain their own `WHERE { }` blocks. The current regex (`\bWHERE\b`) finds the **first** WHERE in the query, which may be inside a SERVICE block. Example:

```sparql
SELECT ?x WHERE {
  ?s a ?type .
  SERVICE <https://query.wikidata.org/sparql> {
    ?x rdfs:label ?label
  }
}
```

If the SERVICE block's WHERE (if explicitly written) comes before the outer WHERE, FROM gets injected in the wrong place. More commonly, SERVICE blocks don't have an explicit WHERE, but nested `{ }` blocks can still confuse brace-counting approaches.

This task:
1. Adds `MIRRORED_GRAPH_IRI` to namespaces.py
2. Rewrites `scope_to_current_graph()` to detect SERVICE blocks, protect them, inject FROM before the outer WHERE, and include the mirrored graph
3. Updates `check_member_query_safety()` to allow SERVICE (safe — only reads remote data)
4. Adds `urn:sempkm:mirror:` to `_VOCAB_PREFIXES` in router.py
5. Writes comprehensive unit tests

## Steps

1. **Add MIRRORED_GRAPH_IRI to namespaces.py:** Add `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` after `INFERRED_GRAPH_IRI`. Add it to `__all__`. Add `MIRRORED_GRAPH` constant in client.py importing from namespaces.

2. **Rewrite scope_to_current_graph() with SERVICE protection:** Before searching for WHERE, scan the stripped-strings query for `SERVICE <...> { ... }` blocks using brace-depth counting. Replace each SERVICE block with a placeholder token (e.g., `__SERVICE_BLOCK_N__`). Then find the outer WHERE, inject FROM clauses (current + inferred + mirrored), and restore SERVICE blocks. Add `include_mirrored: bool = True` parameter with same pattern as `include_inferred`.

3. **Update check_member_query_safety():** Currently rejects queries with `FROM` or `GRAPH` clauses. Add: do NOT reject `SERVICE` clauses — they only send read queries to remote endpoints and don't access local graphs beyond what scoping permits. The existing FROM/GRAPH rejection still applies to prevent graph escape.

4. **Add vocabulary prefix exclusion:** Add `"urn:sempkm:mirror:"` to `_VOCAB_PREFIXES` tuple in `backend/app/sparql/router.py` so mirror provenance IRIs aren't treated as user objects in enrichment.

5. **Write unit tests in test_sparql_client.py:** Add new test class `TestServiceClauseHandling` with cases:
   - SERVICE clause without explicit WHERE — FROM injected before outer WHERE only
   - SERVICE clause with explicit WHERE — FROM not injected inside SERVICE
   - Multiple SERVICE clauses — all protected
   - Nested braces inside SERVICE — properly matched
   - SERVICE in string literal — ignored (existing strip behavior)
   - SERVICE in comment — ignored
   - Query with no SERVICE — existing behavior unchanged
   - `include_mirrored=True` adds FROM <urn:sempkm:mirrored>
   - `include_mirrored=False` omits mirrored graph
   - Members can run SERVICE queries (check_member_query_safety allows it)

## Must-Haves

- [ ] `MIRRORED_GRAPH_IRI` defined in namespaces.py and exported
- [ ] SERVICE blocks are detected and their contents protected from FROM injection
- [ ] FROM <urn:sempkm:mirrored> injected alongside current and inferred graphs
- [ ] `include_mirrored` parameter controls mirrored graph inclusion
- [ ] `check_member_query_safety()` does NOT reject SERVICE clauses
- [ ] All existing tests in test_sparql_client.py still pass
- [ ] New SERVICE-related tests pass (6+ test cases)
- [ ] `urn:sempkm:mirror:` added to _VOCAB_PREFIXES in router.py

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all tests pass (existing + new)
- Verify that `scope_to_current_graph("SELECT ?x WHERE { ?s a ?t . SERVICE <http://ex.org/sparql> { ?x rdfs:label ?l } }")` produces FROM clauses before the outer WHERE, not inside the SERVICE block

## Inputs

- `backend/app/sparql/client.py` — current scope_to_current_graph() implementation
- `backend/app/rdf/namespaces.py` — current namespace definitions (CURRENT_GRAPH_IRI, INFERRED_GRAPH_IRI)
- `backend/app/sparql/router.py` — _VOCAB_PREFIXES tuple
- `backend/tests/test_sparql_client.py` — existing unit tests for sparql client

## Expected Output

- `backend/app/rdf/namespaces.py` — MIRRORED_GRAPH_IRI added
- `backend/app/sparql/client.py` — scope_to_current_graph() rewritten with SERVICE protection and include_mirrored param; check_member_query_safety() updated
- `backend/app/sparql/router.py` — urn:sempkm:mirror: added to _VOCAB_PREFIXES
- `backend/tests/test_sparql_client.py` — new TestServiceClauseHandling class with 8+ test cases

## Observability Impact

- **Signals changed:** `scope_to_current_graph()` now includes `FROM <urn:sempkm:mirrored>` by default in all SPARQL queries. All existing queries will see mirrored graph data (empty until T03 creates the MirrorService). SERVICE blocks are transparently protected — no new logging since this is a pure query-rewriting function.
- **Inspection:** A future agent can verify SERVICE protection by calling `scope_to_current_graph()` with a SERVICE-containing query and checking that FROM clauses appear only before the outer WHERE keyword.
- **Failure visibility:** If SERVICE detection fails (malformed SERVICE without opening brace), the block is silently skipped and the query proceeds as-is — defensive, not destructive. The unit tests cover this implicitly via the nested-braces and multiple-SERVICE cases.
