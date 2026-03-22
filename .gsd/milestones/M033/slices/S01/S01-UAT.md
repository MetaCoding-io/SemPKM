# S01: Federated SPARQL & Mirrored Triples — UAT

**Milestone:** M033
**Written:** 2026-03-21

## UAT Type

- UAT mode: mixed (artifact-driven for unit test contracts + live-runtime for UI)
- Why this mode is sufficient: Backend contracts proven by 95 unit tests. UI surfaces (settings page, SPARQL console toolbar, object page badges, graph edges) need visual verification against a running instance.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one model installed (basic-pkm) with some objects created
- Logged in as owner (for allowlist management)
- SPARQL console accessible at workspace → SPARQL tab

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_federation_allowlist.py tests/test_mirror_service.py -v`. All 95 tests must pass.

## Test Cases

### 1. SERVICE clause pass-through in SPARQL

1. Open SPARQL console in workspace.
2. Enter query:
   ```sparql
   SELECT ?item ?label WHERE {
     ?s a <urn:bpkm:Note> .
     SERVICE <https://query.wikidata.org/sparql> {
       ?item rdfs:label ?label .
       FILTER(LANG(?label) = "en")
     }
   } LIMIT 5
   ```
3. Click Execute.
4. **Expected:** Query executes without error. Results include `?item` and `?label` columns from Wikidata. The FROM clauses are injected only before the outer WHERE, not inside the SERVICE body. If Wikidata is unreachable, the query returns an error from the remote endpoint — NOT a parse error from scope_to_current_graph().

### 2. Federation allowlist management

1. Navigate to Settings page (gear icon in sidebar).
2. Click "Federation" category in sidebar.
3. **Expected:** Federation panel shows a table with at least Wikidata (`https://query.wikidata.org/sparql`) and DBpedia (`https://dbpedia.org/sparql`) as default entries.
4. In the "Add Endpoint" form, enter URL `https://sparql.uniprot.org/sparql` and label `UniProt`.
5. Click Add.
6. **Expected:** UniProt appears in the table. No page reload needed.
7. Click the delete button (trash icon) on the UniProt row.
8. **Expected:** UniProt removed from the table.

### 3. Allowlist enforcement for non-owner users

1. Log in as a member (non-owner) user.
2. Open SPARQL console.
3. Enter a query with `SERVICE <https://unlisted-endpoint.example.org/sparql> { ?s ?p ?o }`.
4. Click Execute.
5. **Expected:** HTTP 403 error with message containing "Federation endpoint not in allowlist: https://unlisted-endpoint.example.org/sparql".
6. Enter a query with `SERVICE <https://query.wikidata.org/sparql> { ?s ?p ?o }`.
7. Click Execute.
8. **Expected:** Query executes (Wikidata is in the default allowlist).

### 4. Mirror Results button state management

1. Open SPARQL console.
2. Enter a non-SERVICE query: `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5`.
3. Click Execute.
4. **Expected:** "Mirror Results" button in toolbar remains disabled (grayed out, 0.4 opacity).
5. Enter a SERVICE query (e.g., the Wikidata query from test case 1).
6. Click Execute and get results.
7. **Expected:** "Mirror Results" button becomes enabled (full opacity, clickable).
8. Click "Mirror Results".
9. **Expected:** Button shows "Mirroring..." briefly, then transitions to "Mirrored" with green border. Button becomes non-clickable (prevents double-mirroring).

### 5. Mirror batch persistence and API

1. After mirroring results (test case 4), call `GET /api/sparql/mirror/batches` (via browser devtools or curl).
2. **Expected:** JSON response with `{"batches": [...]}` containing at least one batch with fields: `batch_id` (starts with `urn:sempkm:mirror:`), `source_endpoint`, `timestamp`, `triple_count`, `query_hash`.
3. Query mirrored graph directly: In SPARQL console, check "All Graphs", enter `SELECT * FROM <urn:sempkm:mirrored> WHERE { ?s ?p ?o } LIMIT 20`.
4. **Expected:** Results include both mirrored data triples and PROV-O provenance triples (prov:wasAttributedTo, prov:generatedAtTime, dcterms:source).

### 6. Mirrored triple badges on object pages

1. After mirroring data that references an existing local object (or an object whose IRI matches a mirrored subject), open that object's page.
2. **Expected:** Properties sourced from the mirrored graph display with a teal "mirrored" badge (globe icon). Hovering the badge shows a tooltip with the source endpoint URL.
3. Properties from the user's own data do NOT have the mirrored badge.
4. Inferred properties show the existing gray "inferred" badge (not teal).

### 7. Mirrored edges in graph view

1. Open a graph view that includes nodes connected by mirrored triples.
2. **Expected:** Mirrored edges render as dotted teal lines, distinguishable from solid user edges and dashed gray inferred edges.
3. Click a mirrored edge.
4. **Expected:** Edge detail popover shows "Mirrored from <endpoint_url>" with timestamp. No delete button (mirrored edges cannot be deleted via the edge popover).

### 8. SPARQL console SERVICE autocomplete

1. Open SPARQL console.
2. Type `SERVICE <` (with the angle bracket).
3. **Expected:** Autocomplete dropdown appears with federation allowlist endpoints (Wikidata, DBpedia, any added endpoints). Each shows label and URL.
4. Select Wikidata from the dropdown.
5. **Expected:** Endpoint URL is inserted with closing `>`.
6. Type `PREFIX w` above the SERVICE clause.
7. **Expected:** Autocomplete includes Wikidata-specific prefixes (wdt:, wd:, wikibase:, bd:) marked with `F` detail marker.

### 9. SERVICE snippet template

1. In SPARQL console, type `SERV`.
2. **Expected:** Autocomplete shows a `SERVICE <endpoint> { … }` snippet option (ranked above plain `SERVICE` keyword).
3. Select the snippet.
4. **Expected:** Full SERVICE template inserted.

## Edge Cases

### Non-owner sees allowlist but cannot modify

1. Log in as a member (non-owner).
2. Navigate to Settings → Federation.
3. **Expected:** Endpoint table is visible (read-only). Add form and delete buttons are hidden or disabled.

### SERVICE SILENT variant

1. In SPARQL console, enter a query using `SERVICE SILENT <https://query.wikidata.org/sparql> { ... }`.
2. **Expected:** Query executes normally. The SILENT keyword suppresses errors from the remote endpoint (returns empty results instead of error). FROM clauses are not injected into the SERVICE body.

### Multiple SERVICE clauses in one query

1. Enter a query with two SERVICE clauses targeting different endpoints.
2. **Expected:** Both SERVICE blocks are preserved. FROM clauses appear only before the outer WHERE.

### Mirror same query twice

1. Execute a SERVICE query and click "Mirror Results".
2. Execute the same query again and click "Mirror Results" again.
3. **Expected:** Both mirror operations succeed. Two separate batches appear in `GET /api/sparql/mirror/batches` (each with unique batch_id). Query hash is the same for both batches.

### Federation endpoint fetch failure

1. If the `/api/federation/endpoints` endpoint is unreachable (e.g., API server down), open SPARQL console.
2. **Expected:** Console loads normally. Browser devtools console shows a warning: "Failed to fetch federation endpoints". SERVICE autocomplete shows no suggestions. All other editor features work.

## Failure Signals

- "Malformed SPARQL query" error when executing a SERVICE query → scope_to_current_graph() is injecting FROM inside the SERVICE body
- "Mirror Results" button never enables after a SERVICE query with results → SERVICE detection regex or lastQueryBindings state not working
- Object page properties show PROV-O triples (prov:wasAttributedTo etc.) as regular properties → PROV predicate filtering missing
- Mirror button shows "Mirrored" but `GET /api/sparql/mirror/batches` returns empty → mirror API not wired or storage failed silently
- Federation settings category missing from settings sidebar → template include not added or category button missing
- Graph edges from mirrored triples render as solid lines → mirrored_edge_set not populated or Cytoscape style not applied

## Requirements Proved By This UAT

- SPARQL-FED-01: SERVICE clause pass-through (test cases 1, SERVICE SILENT, multiple SERVICE)
- SPARQL-FED-02: Federation endpoint allowlist CRUD (test case 2)
- SPARQL-FED-03: MirrorService storage with PROV-O provenance (test cases 4, 5)
- SPARQL-FED-04: Allowlist enforcement (test case 3, non-owner edge case)
- SPARQL-FED-05: SPARQL console SERVICE UI assistance (test cases 8, 9)
- SPARQL-FED-06: Mirrored triple indicators (test cases 6, 7)

## Not Proven By This UAT

- Mirror batch deletion via API (needs curl/devtools — no UI for it yet)
- Performance under large mirrored datasets (deferred)
- TTL/staleness detection for mirrored triples (deferred per D297)
- Per-triple mirror selection (deferred — entire query result is mirrored)

## Notes for Tester

- Test cases 1, 3, and 4 require network access to Wikidata. If offline, use the mock endpoint pattern from the unit tests or substitute with a local SPARQL endpoint.
- The "Mirror Results" button only enables when the executed query contains a SERVICE clause AND returns results. A SERVICE query that returns zero rows leaves the button disabled.
- The mirrored badge test (case 6) requires that mirrored data references an object IRI that also exists in the local graph. The easiest way: mirror a Wikidata query that returns the IRI of a local object, or create a local object whose IRI matches a mirrored subject.
- Federation settings are owner-only for writes. The member enforcement test (case 3) requires a second user account.
