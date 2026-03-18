---
id: T01
parent: S03
milestone: M013
provides:
  - POST /api/context-query endpoint with URL + keyword matching, deduplication, and type enrichment
key_files:
  - backend/app/api/router.py
  - backend/tests/test_api_surface.py
key_decisions:
  - URL match_type wins over keyword when same IRI appears in both result sets (first-match-wins dedup)
  - match_type is "title" when only title is provided without keywords, "keyword" otherwise
patterns_established:
  - Context-query uses dict[iri, match_type] for dedup across URL and FTS result sets
  - Graceful degradation: each stage (URL match, keyword match, label resolve, type resolve) catches exceptions independently and logs at WARNING
observability_surfaces:
  - POST /api/context-query response includes match_type per result and total count
  - Empty body → 400 with "At least one of url, title, or keywords is required"
  - SPARQL/FTS errors logged at WARNING with exc_info, degraded (not 500)
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Implement POST /api/context-query endpoint

**Added POST /api/context-query with URL matching (SPARQL), keyword matching (FTS/LuceneSail), deduplication, and type/label enrichment**

## What Happened

Implemented the context-query endpoint on `api_surface_router` in `backend/app/api/router.py`. The endpoint accepts `{url, title, keywords}` (all optional, at least one required) and returns deduplicated results from two matching strategies:

1. **URL matching** — SPARQL query finds objects where any property value matches the exact URL string via `FILTER(STR(?val) = "...")`.
2. **Keyword matching** — combines title + keywords into a search string and runs FTS via `SearchService.search()` (LuceneSail).

Results are merged into a `dict[iri → match_type]` for deduplication (URL matches take precedence). Labels are resolved via `LabelService.resolve_batch()`, types via a SPARQL `?s a ?type` VALUES query, and type labels via a second label batch. Each stage catches exceptions independently and logs at WARNING — the endpoint degrades gracefully rather than failing entirely.

Added 9 unit tests covering URL match, keyword match, title match, empty results, validation (400), auth (401), deduplication, type info enrichment, and Bearer token auth.

## Verification

- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v -k "context_query"` — 9 passed
- Full suite: 53 passed (44 existing + 9 new)
- Python AST parse check passed on router.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `.venv/bin/pytest tests/test_api_surface.py -v -k "context_query"` | 0 | ✅ pass | 0.69s |
| 2 | `.venv/bin/pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 1.28s |
| 3 | `python3 -c "import ast; ast.parse(open('app/api/router.py').read())"` | 0 | ✅ pass | <1s |

### Slice-level checks (intermediate task — partial expected)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Unit tests `-k "context_query"` | ✅ pass | 9/9 |
| 2 | curl URL match against Docker | ⏳ pending | Requires Docker stack |
| 3 | curl keyword match against Docker | ⏳ pending | Requires Docker stack |
| 4 | E2E Playwright tests | ⏳ pending | T03 |
| 5 | docs/guide/31-api-surface.md | ⏳ pending | T04 |
| 6 | curl empty body → 400 (failure-path) | ⏳ pending | Requires Docker stack |

## Diagnostics

- **Response shape**: `{results: [{iri, label, type_iri, type_label, match_type, snippet}], total: N}`
- **Empty results**: Returns `{results: [], total: 0}` (200, not 404)
- **Validation failure**: Empty body → 400 `"At least one of url, title, or keywords is required"`
- **SPARQL errors**: Logged at WARNING with `exc_info=True`, that result set skipped
- **FTS errors**: Same pattern — logged and skipped, other result sets still returned

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/router.py` — Added ContextQueryRequest/ContextResult/ContextQueryResponse models and POST /api/context-query endpoint
- `backend/tests/test_api_surface.py` — Added 9 tests in TestContextQueryEndpoint class
- `.gsd/milestones/M013/slices/S03/S03-PLAN.md` — Added failure-path verification check
- `.gsd/milestones/M013/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
