---
id: T01
parent: S01
milestone: M033
provides:
  - MIRRORED_GRAPH_IRI namespace constant
  - SERVICE block protection in scope_to_current_graph()
  - include_mirrored parameter for scope_to_current_graph()
  - check_member_query_safety() allows SERVICE clauses
  - urn:sempkm:mirror: in _VOCAB_PREFIXES
key_files:
  - backend/app/rdf/namespaces.py
  - backend/app/sparql/client.py
  - backend/app/sparql/router.py
  - backend/tests/test_sparql_client.py
key_decisions:
  - SERVICE block protection via placeholder substitution with brace-depth counting (rather than regex-only approach) for correctness with nested braces
patterns_established:
  - _protect_service_blocks() / _restore_service_blocks() pattern for any future query-rewriting that must skip SERVICE bodies
observability_surfaces:
  - scope_to_current_graph() output is verifiable by calling with SERVICE-containing query and checking FROM placement
duration: 30m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Extend scope_to_current_graph() for SERVICE pass-through and mirrored graph

**Added SERVICE block protection to scope_to_current_graph(), MIRRORED_GRAPH_IRI namespace, and include_mirrored parameter — FROM clauses inject only before the outer WHERE, never inside SERVICE blocks.**

## What Happened

1. Added `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` to `namespaces.py` and exported it in `__all__`.

2. Rewrote `scope_to_current_graph()` in `client.py` with SERVICE block protection. The algorithm: (a) find SERVICE keywords in the string-stripped query to avoid false positives inside literals/comments, (b) extract each SERVICE block using brace-depth counting that handles nested `{ }`, (c) replace with numbered placeholders, (d) inject FROM clauses before the outer WHERE, (e) restore SERVICE blocks from placeholders. Added `include_mirrored: bool = True` parameter following the existing `include_inferred` pattern.

3. Updated `check_member_query_safety()` docstring to explicitly document that SERVICE clauses are allowed — the function already only checks for FROM/GRAPH, so no code change was needed, just documentation.

4. Added `"urn:sempkm:mirror:"` to `_VOCAB_PREFIXES` in `router.py` so mirror provenance IRIs aren't enriched as user objects.

5. Wrote 14 new tests across two test classes: `TestCheckMemberQuerySafety` (2 new: SERVICE and SERVICE SILENT) and `TestServiceClauseHandling` (12 new: SERVICE without WHERE, SERVICE with WHERE, multiple SERVICE blocks, nested braces, string literal, comment, no-SERVICE backwards compat, include_mirrored true/false, shared_graphs + SERVICE).

Initial run had 1 failure in the multiple-SERVICE test due to a placeholder renumbering bug (reverse-collect + re-index created collisions). Fixed by collecting spans in forward order and replacing in reverse order with pre-assigned indices.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all 35 tests pass (16 existing + 19 new)
- Manual verification: `scope_to_current_graph("SELECT ?x WHERE { ?s a ?t . SERVICE <http://ex.org/sparql> { ?x rdfs:label ?l } }")` produces FROM clauses at position 10, outer WHERE at position 90, SERVICE at 108 — FROM before WHERE, not inside SERVICE block

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` | 0 | ✅ pass | 0.19s |
| 2 | `python -c "from app.sparql.client import scope_to_current_graph; ..."` (manual FROM placement check) | 0 | ✅ pass | <1s |

## Diagnostics

- Verify SERVICE protection: call `scope_to_current_graph()` with a SERVICE-containing query and confirm FROM appears before outer WHERE, not inside SERVICE body.
- All call sites of `scope_to_current_graph()` (router.py, views/service.py) now automatically include `FROM <urn:sempkm:mirrored>` via the default `include_mirrored=True`. The mirrored graph is empty until T03 creates the MirrorService.

## Deviations

- Initial placeholder renumbering approach (reverse-collect then re-index) caused collisions with multiple SERVICE blocks. Replaced with forward-collect + reverse-replace algorithm. No impact on API or behavior.
- Added `SERVICE SILENT` test case beyond what the plan specified.

## Known Issues

None.

## Files Created/Modified

- `backend/app/rdf/namespaces.py` — added MIRRORED_GRAPH_IRI constant and exported it
- `backend/app/sparql/client.py` — added _protect_service_blocks(), _restore_service_blocks(), MIRRORED_GRAPH constant; rewrote scope_to_current_graph() with SERVICE protection and include_mirrored param; updated check_member_query_safety() docstring
- `backend/app/sparql/router.py` — added "urn:sempkm:mirror:" to _VOCAB_PREFIXES tuple
- `backend/tests/test_sparql_client.py` — added TestServiceClauseHandling class (12 tests), 2 SERVICE tests to TestCheckMemberQuerySafety
