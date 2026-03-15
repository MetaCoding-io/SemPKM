---
estimated_steps: 5
estimated_files: 3
---

# T01: Backend tag-suggestions endpoint with template and tests

**Slice:** S04 — Tag Autocomplete
**Milestone:** M005

## Description

Add a `GET /browser/tag-suggestions?q=<query>` endpoint to the search router that returns an HTML partial with matching tag values from the triplestore. The endpoint queries both `bpkm:tags` and `schema:keywords` via UNION, applies case-insensitive CONTAINS filtering, and returns up to 30 results ordered by frequency (most-used first) then alphabetically. When `q` is empty, returns top tags by frequency for discoverability.

## Steps

1. Add `tag_suggestions` endpoint to `backend/app/browser/search.py`:
   - Accept `q` query parameter (default empty string)
   - Build SPARQL with UNION across both tag predicates, GROUP BY tag value, COUNT for frequency
   - When `q` is non-empty, add `FILTER(CONTAINS(LCASE(?tagValue), LCASE("{escaped_q}")))` 
   - Escape `q` using same `replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")` pattern as `_sparql_escape` in workspace.py
   - ORDER BY DESC(?count) ?tagValue, LIMIT 30
   - Execute via `client.query()` (async triplestore client from DI)
   - Parse bindings into `[{"value": "...", "count": N}]` list
   - Render `browser/tag_suggestions.html` template with results

2. Create `backend/app/templates/browser/tag_suggestions.html`:
   - Iterate results, render each as `.suggestion-item` div
   - Each item has `onclick` handler: find closest `.tag-autocomplete-field`, set input value, clear suggestions div innerHTML
   - Show tag value text with count badge (e.g. "architect (9)")
   - If no results, render nothing (empty response hides dropdown via CSS `:empty` rule)

3. Write unit tests in `backend/tests/test_tag_suggestions.py`:
   - Test SPARQL query generation with empty query
   - Test SPARQL query generation with prefix filter
   - Test special character escaping in query
   - Test result parsing from SPARQL bindings format
   - Test result ordering (by count DESC, then alpha)

## Must-Haves

- [ ] Endpoint queries both `bpkm:tags` and `schema:keywords` via UNION
- [ ] Case-insensitive matching via LCASE/CONTAINS
- [ ] User input is SPARQL-escaped (backslash, double-quote, newline)
- [ ] Results limited to 30, ordered by frequency DESC then alphabetically
- [ ] Empty query returns top tags (no filter applied)
- [ ] Template renders clickable suggestion items

## Verification

- `backend/.venv/bin/pytest tests/test_tag_suggestions.py -v` — all tests pass
- Manual: `curl http://localhost:8001/browser/tag-suggestions?q=arch` returns HTML with matching tags

## Inputs

- `backend/app/browser/search.py` — existing search router to extend
- `backend/app/browser/workspace.py` — `_sparql_escape()` pattern and `_execute_sparql_select()` pattern
- `backend/app/templates/browser/search_suggestions.html` — template pattern to follow (simplified)
- `frontend/static/css/forms.css` — `.suggestion-item` CSS already defined

## Expected Output

- `backend/app/browser/search.py` — extended with `tag_suggestions` endpoint
- `backend/app/templates/browser/tag_suggestions.html` — new template for tag suggestion items
- `backend/tests/test_tag_suggestions.py` — unit tests for query building and result parsing

## Observability Impact

- **New log signal:** `logger.debug("Tag suggestions for q='%s': %d results", ...)` emitted on every request — shows query term and result count.
- **Inspection surface:** `GET /browser/tag-suggestions?q=<term>` returns HTML partial directly, inspectable via curl or browser devtools network tab.
- **Failure visibility:** SPARQL query failures are caught and logged at WARNING level with `exc_info=True`; the endpoint returns an empty response (no crash). Malformed or empty queries degrade gracefully to zero results.
