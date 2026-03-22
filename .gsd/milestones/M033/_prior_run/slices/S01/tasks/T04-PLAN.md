---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T04: SPARQL console SERVICE clause UI assistance

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Writing federated SPARQL queries is hard — users need to know endpoint URLs and the specific PREFIX conventions each endpoint uses. This task adds two forms of assistance to the CodeMirror 6 SPARQL editor:

1. **Endpoint autocomplete:** When the user types `SERVICE <`, suggest allowed endpoints from the federation allowlist (fetched via `GET /api/federation/endpoints` from T02).
2. **PREFIX injection for known endpoints:** When a SERVICE clause targets a known endpoint (Wikidata, DBpedia), offer relevant PREFIX suggestions (e.g., `wdt:`, `wd:`, `wikibase:` for Wikidata; `dbo:`, `dbr:`, `dbp:` for DBpedia).

The SPARQL console already has a CodeMirror autocompletion extension loaded (`autocompletion` from `@codemirror/autocomplete`) and a vocabulary-based autocomplete. The endpoint autocomplete integrates into this existing system.

## Steps

1. **Fetch allowlist on console init:** In `sparql-console.js`, add a module-level `federationEndpoints` array. On `initSparqlConsole()`, fetch `GET /api/federation/endpoints` and populate the array. Cache it — re-fetch only when the settings page is visited (use a simple staleness flag). Handle fetch failure gracefully (empty array, federation features degraded but console works).

2. **Add endpoint autocomplete source:** Create a new CodeMirror completion source function `federationEndpointCompletion(context)` that activates when the cursor is after `SERVICE <` (or `SERVICE\s+<`). Return completions from `federationEndpoints` array with `{label: endpoint.label, detail: endpoint.url, apply: endpoint.url + ">"}`. Register it alongside the existing vocabulary autocomplete in the editor's `autocompletion` extension.

3. **Add known-endpoint PREFIX map and injection:** Define a map of known endpoints to their common prefixes:
   - Wikidata: `{wdt: "http://www.wikidata.org/prop/direct/", wd: "http://www.wikidata.org/entity/", wikibase: "http://wikiba.se/ontology#", bd: "http://www.bigdata.com/rdf#"}`
   - DBpedia: `{dbo: "http://dbpedia.org/ontology/", dbr: "http://dbpedia.org/resource/", dbp: "http://dbpedia.org/property/"}`
   When user runs a query containing a SERVICE clause, check if the endpoint matches a known entry. If matching prefixes aren't already in the query, show a subtle inline hint (or auto-inject them at the top). Prefer non-intrusive: add them to the prefix autocomplete suggestions so they appear when user types `PREFIX`.

4. **Add SERVICE snippet:** Add a "SERVICE" entry to the code completion that inserts a template:
   ```
   SERVICE <${endpoint}> {
     ${cursor}
   }
   ```
   This appears when user types `SERVICE` in the editor, using CodeMirror's snippet completion API.

## Must-Haves

- [ ] Allowlist fetched on console initialization
- [ ] Typing `SERVICE <` triggers endpoint autocomplete with allowed endpoints
- [ ] Known endpoint prefixes (Wikidata, DBpedia) available in prefix autocomplete
- [ ] SERVICE snippet template available in completions
- [ ] Graceful degradation if allowlist fetch fails (console still works, no autocomplete)

## Verification

- Visual inspection: open SPARQL console, type `SERVICE <` — endpoint suggestions appear
- Visual inspection: type `PREFIX w` — Wikidata-related prefixes appear if a Wikidata SERVICE clause is in the query
- `grep -q "federationEndpointCompletion" frontend/static/js/sparql-console.js` — function exists

## Observability Impact

- **Federation endpoint fetch:** Console logs a warning (`Failed to fetch federation endpoints:`) if the allowlist API fails — visible in browser devtools.
- **Autocomplete activation:** `federationEndpointCompletion` is registered as a CM6 completion source — inspect via CM6 devtools extension or by typing `SERVICE <` in the editor.
- **Known endpoint prefixes:** Prefixes for Wikidata/DBpedia appear with detail marker `F` (Federation) in autocomplete — distinguishable from standard vocabulary prefixes (detail `D`).
- **Graceful degradation:** If allowlist fetch fails, `federationEndpoints` stays empty — no autocomplete suggestions but console works normally. No error shown to user.

## Inputs

- `frontend/static/js/sparql-console.js` — existing console module with CodeMirror 6 editor and autocompletion
- `backend/app/federation/allowlist_router.py` — GET /api/federation/endpoints (from T02)

## Expected Output

- `frontend/static/js/sparql-console.js` — endpoint autocomplete, known-endpoint PREFIX map, SERVICE snippet
- `frontend/static/css/workspace.css` — optional: styles for endpoint autocomplete items (label + URL)
