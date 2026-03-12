---
estimated_steps: 5
estimated_files: 1
---

# T02: Make SPARQL keyword detection ignore string literals and comments

**Slice:** S02 — Correctness Fixes
**Milestone:** M002

## Description

`scope_to_current_graph()` and `check_member_query_safety()` in `sparql/client.py` detect FROM/GRAPH keywords using naive regex on the uppercased query string. This false-positives on keywords inside SPARQL string literals (e.g. `FILTER(CONTAINS(?label, "FROM the archive"))`) and comments (`# FROM note`). The fix adds a `_strip_sparql_strings()` helper that blanks out string literal contents and comment lines before keyword detection.

Both functions share the same detection logic, so the helper fixes both. The helper lives in `client.py` (private to this module) since it's specifically for the keyword-detection use case, not general SPARQL escaping (which lives in `sparql/utils.py`).

## Steps

1. Read `backend/app/sparql/client.py` to confirm exact code at lines 21-43 (`check_member_query_safety`) and lines 82-87 (`scope_to_current_graph` keyword checks)
2. Add `_strip_sparql_strings(query: str) -> str` function that:
   - First strips `#`-comments (from `#` to end of line, but only when `#` is not inside a string literal — handle by stripping strings first)
   - Strips triple-quoted strings first (`"""..."""` and `'''...'''`) to avoid partial matches with single-quote variants
   - Then strips single-quoted strings (`"..."` and `'...'`), handling escaped quotes (`\"`, `\'`)
   - Replaces string contents with spaces (preserving string delimiters) so that word boundaries in the surrounding query are not disturbed
3. Update `check_member_query_safety()` to use `upper = _strip_sparql_strings(query).upper()` instead of `upper = query.upper()`
4. Update `scope_to_current_graph()` to use `stripped_upper = _strip_sparql_strings(query).upper()` for keyword detection, while keeping the original `query` for the `CURRENT_GRAPH in query` check and for the actual FROM injection
5. Verify with inline Python assertions covering: literals with FROM/GRAPH, comments with FROM/GRAPH, real FROM/GRAPH clauses, and triple-quoted strings

## Must-Haves

- [ ] `_strip_sparql_strings()` handles all four SPARQL string literal forms: `"..."`, `'...'`, `"""..."""`, `'''...'''`
- [ ] `_strip_sparql_strings()` handles escaped quotes inside strings (`\"`, `\'`)
- [ ] `_strip_sparql_strings()` strips `#`-comments (hash to end of line)
- [ ] `scope_to_current_graph()` uses stripped query for FROM/GRAPH keyword detection
- [ ] `check_member_query_safety()` uses stripped query for FROM/GRAPH keyword detection
- [ ] Real FROM/GRAPH clauses are still correctly detected (no regression)
- [ ] The actual query text passed through (for FROM injection or return) is the original, unstripped query

## Verification

- Run inline Python in Docker container that imports and tests `_strip_sparql_strings`:
  ```
  docker compose exec backend python -c "
  from app.sparql.client import _strip_sparql_strings, scope_to_current_graph, check_member_query_safety
  
  # 1. FROM inside double-quoted string is stripped
  q1 = 'SELECT ?s WHERE { FILTER(CONTAINS(?label, \"FROM the archive\")) }'
  assert 'FROM' not in _strip_sparql_strings(q1).upper().split('FILTER')[0], 'FROM in literal not stripped'
  
  # 2. scope_to_current_graph injects FROM when keyword is only in literal
  result = scope_to_current_graph(q1)
  assert 'FROM <urn:sempkm:current>' in result, 'FROM not injected'
  
  # 3. Real FROM clause is still detected
  q2 = 'SELECT ?s FROM <http://example.org/g> WHERE { ?s ?p ?o }'
  assert scope_to_current_graph(q2) == q2, 'Real FROM clause not detected'
  
  # 4. check_member_query_safety does not reject literal-only FROM
  try:
      check_member_query_safety(q1)
      print('OK: literal FROM not rejected')
  except:
      raise AssertionError('Literal FROM was incorrectly rejected')
  
  # 5. Comment with FROM is stripped
  q3 = 'SELECT ?s WHERE { ?s ?p ?o } # FROM note'
  result3 = scope_to_current_graph(q3)
  assert 'FROM <urn:sempkm:current>' in result3, 'Comment FROM not handled'
  
  print('All COR-02 assertions passed')
  "
  ```

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: The `_strip_sparql_strings` function is testable in isolation; S03 will add formal unit tests
- Failure state exposed: None (fix eliminates false-positive detection failure mode)

## Inputs

- `backend/app/sparql/client.py` — current implementation with naive `re.search` on uppercased query

## Expected Output

- `backend/app/sparql/client.py` — contains `_strip_sparql_strings()` helper; both `scope_to_current_graph()` and `check_member_query_safety()` use it for keyword detection
