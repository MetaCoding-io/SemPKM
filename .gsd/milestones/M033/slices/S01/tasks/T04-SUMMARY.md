---
id: T04
parent: S01
milestone: M033
provides:
  - Federation endpoint autocomplete in SPARQL console (SERVICE < triggers suggestions)
  - Known-endpoint PREFIX injection for Wikidata and DBpedia
  - SERVICE snippet template in keyword completions
  - fetchFederationEndpoints() cached allowlist fetch on console init
key_files:
  - frontend/static/js/sparql-console.js
key_decisions:
  - Endpoint autocomplete implemented as a separate CM6 completion source (federationEndpointCompletion) rather than inlining into sparqlCompletions — cleaner separation, independent activation regex
  - Known-endpoint PREFIX suggestions use substring matching against endpoint URLs rather than exact match — handles query.wikidata.org, www.wikidata.org, etc.
patterns_established:
  - KNOWN_ENDPOINT_PREFIXES pattern — map of URL substring → prefix map, extensible for future known endpoints (e.g., GeoSPARQL, UniProt)
  - Dual completion source registration — sparqlCompletions for general SPARQL, federationEndpointCompletion for context-sensitive SERVICE endpoint suggestions
observability_surfaces:
  - Console warning on federation endpoint fetch failure — visible in browser devtools
  - Federation PREFIX suggestions marked with detail 'F' (distinguishable from vocabulary 'D' and keyword 'K')
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T04: SPARQL console SERVICE clause UI assistance

**Added federation endpoint autocomplete, known-endpoint PREFIX injection (Wikidata/DBpedia), and SERVICE snippet template to the CodeMirror 6 SPARQL editor.**

## What Happened

1. Added `federationEndpoints` module-level array and `KNOWN_ENDPOINT_PREFIXES` map to `sparql-console.js`. The KNOWN_ENDPOINT_PREFIXES map uses URL substring matching (e.g., `'wikidata.org'` → `{wdt, wd, wikibase, bd}`, `'dbpedia.org'` → `{dbo, dbr, dbp}`) so it works regardless of the exact endpoint URL form.

2. Created `federationEndpointCompletion(context)` — a CM6 completion source that activates when the cursor is after `SERVICE <` (or `SERVICE SILENT <`). It returns completions from the cached `federationEndpoints` array with the endpoint label as the visible text and the URL as detail. The `apply` text includes the closing `>` bracket for convenience.

3. Extended the PREFIX section of `sparqlCompletions` to scan the current document for SERVICE clauses targeting known endpoints. When a Wikidata or DBpedia SERVICE clause is detected, the autocomplete offers their common PREFIX declarations (marked with detail `'F'` for Federation). It skips prefixes already declared in the query to avoid duplicates.

4. Added a `SERVICE <endpoint> { … }` snippet to the keyword completions. When the user types "SERVICE" (or any prefix of it), a snippet option appears with `boost: 2` to rank it above the plain keyword.

5. Created `fetchFederationEndpoints()` async function that fetches `GET /api/federation/endpoints` and populates the `federationEndpoints` array. Handles failure gracefully — logs a console warning and leaves the array empty. Called in `initSparqlConsole()` alongside `fetchVocabulary()`.

6. Registered `federationEndpointCompletion` as a second completion source in the `autocompletion({ override: [...] })` extension alongside `sparqlCompletions`.

## Verification

- `grep -q "federationEndpointCompletion" frontend/static/js/sparql-console.js` — function exists ✅
- `grep -q "KNOWN_ENDPOINT_PREFIXES" frontend/static/js/sparql-console.js` — prefix map exists ✅
- `grep -q "fetchFederationEndpoints" frontend/static/js/sparql-console.js` — fetch function exists and called in init ✅
- `node -c frontend/static/js/sparql-console.js` — JS syntax valid ✅
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py tests/test_federation_allowlist.py -v` — all 87 slice-level tests pass ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "federationEndpointCompletion" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "KNOWN_ENDPOINT_PREFIXES" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "fetchFederationEndpoints" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 4 | `node -c frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py tests/test_federation_allowlist.py -v` | 0 | ✅ pass | 0.66s |

## Diagnostics

- **Endpoint autocomplete:** Type `SERVICE <` in the SPARQL console editor — should show federation allowlist endpoints as completions. If no suggestions appear, check browser devtools console for "Failed to fetch federation endpoints" warning.
- **Known-endpoint PREFIXes:** Write a SERVICE clause targeting wikidata.org or dbpedia.org, then type `PREFIX w` — should show Wikidata-specific prefixes with detail marker `F`. Only appears if a matching SERVICE clause is in the current document.
- **SERVICE snippet:** Type `SERV` in the editor — should show `SERVICE <endpoint> { … }` snippet option above the plain `SERVICE` keyword.
- **Graceful degradation:** If `/api/federation/endpoints` is unreachable, the console still works normally — just no endpoint autocomplete suggestions.

## Deviations

- Did not add custom CSS for autocomplete items — CM6's built-in autocomplete dropdown already renders `label`, `detail`, and `type` with appropriate styling. The `detail` markers (`F` for federation, `snippet` for template) are sufficient visual differentiation.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/sparql-console.js` — added federationEndpoints array, KNOWN_ENDPOINT_PREFIXES map, federationEndpointCompletion() CM6 completion source, fetchFederationEndpoints() fetch function, SERVICE snippet in keyword completions, known-endpoint PREFIX injection in PREFIX autocomplete section, registered both completion sources in autocompletion extension
- `.gsd/milestones/M033/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section per pre-flight requirement
