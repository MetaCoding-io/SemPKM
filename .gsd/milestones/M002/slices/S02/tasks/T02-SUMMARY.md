---
id: T02
parent: S02
milestone: M002
provides:
  - "_strip_sparql_strings() helper that blanks SPARQL string literals and comments for safe keyword detection"
  - "False-positive-free FROM/GRAPH detection in scope_to_current_graph() and check_member_query_safety()"
key_files:
  - backend/app/sparql/client.py
key_decisions:
  - "Used a single compiled regex (_SPARQL_STRINGS_RE) with alternation to match all four SPARQL string forms plus hash-comments in one pass — triple-quoted first to avoid partial matches"
  - "Replace string interiors with spaces (preserving delimiters) rather than removing them, to maintain word boundaries in surrounding query text"
patterns_established:
  - "Private _strip_sparql_strings() helper in client.py for keyword-safe query inspection"
observability_surfaces:
  - none
duration: 1 step
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Make SPARQL keyword detection ignore string literals and comments

**Added `_strip_sparql_strings()` helper so FROM/GRAPH keyword detection in `scope_to_current_graph()` and `check_member_query_safety()` ignores keywords inside SPARQL string literals and comments.**

## What Happened

Added a `_strip_sparql_strings(query)` function to `backend/app/sparql/client.py` that uses a single compiled regex (`_SPARQL_STRINGS_RE`) to match all four SPARQL string literal forms (`"..."`, `'...'`, `"""..."""`, `'''...'''`) plus `#`-comments in one pass. Triple-quoted forms are matched first in the alternation to avoid partial matches with single-quoted variants. Escaped quotes (`\"`, `\'`) are handled by the `\\.` alternative in the regex interior.

The function replaces string interiors with spaces (preserving delimiters) and replaces entire comments with spaces. This preserves the overall string length and word boundaries so keyword detection on the stripped result works correctly.

Updated both `check_member_query_safety()` and `scope_to_current_graph()` to run keyword detection on `_strip_sparql_strings(query).upper()` instead of `query.upper()`. The original unstripped query is still used for the `CURRENT_GRAPH in query` IRI check and for actual FROM clause injection.

## Verification

Ran 11 inline assertions in the Docker container (`docker compose exec api python -c ...`):

1. FROM inside double-quoted string is blanked by `_strip_sparql_strings` ✓
2. `scope_to_current_graph` injects FROM when keyword is only in literal ✓
3. Real FROM clause is still detected (no regression) ✓
4. `check_member_query_safety` does not reject literal-only FROM ✓
5. Comment with FROM is stripped ✓
6. GRAPH inside string literal not rejected by safety check ✓
7. Real GRAPH clause still rejected by safety check ✓
8. Triple-quoted strings handled ✓
9. Single-quoted strings handled ✓
10. Escaped quotes inside strings handled ✓
11. Real FROM clause correctly rejected by member safety ✓

Slice-level checks: COR-01 pass, COR-02 pass, COR-03 pending (T03). Docker build succeeds.

## Diagnostics

`_strip_sparql_strings` is a pure function testable in isolation — import and call it with any SPARQL query string to inspect behavior. No runtime signals or persisted state.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/client.py` — Added `_SPARQL_STRINGS_RE` compiled regex, `_strip_sparql_strings()` helper; updated `check_member_query_safety()` and `scope_to_current_graph()` to use stripped query for keyword detection
