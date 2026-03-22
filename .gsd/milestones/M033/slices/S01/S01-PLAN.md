# S01: Federated SPARQL & Mirrored Triples

**Goal:** Users can write SPARQL queries with SERVICE clauses to federate against external endpoints (e.g. Wikidata), mirror federated results into `urn:sempkm:mirrored`, and see mirrored triples alongside local/inferred data with provenance badges.

**Demo:** User writes `SELECT ?name WHERE { SERVICE <https://query.wikidata.org/sparql> { ... } }` in the SPARQL console, sees federated results. User clicks "Mirror Results" and the triples persist in `urn:sempkm:mirrored`. Mirrored triples appear on object pages with a provenance badge showing the source endpoint. The admin settings page has a "Federation" section for managing the endpoint allowlist.

## Must-Haves

- `scope_to_current_graph()` detects SERVICE clauses and does NOT inject FROM into their bodies — only into the outer query
- `MIRRORED_GRAPH_IRI` defined in namespaces.py and included in FROM clause injection alongside current and inferred
- Federation endpoint allowlist stored in InstanceConfig with CRUD API and settings UI
- MirrorService stores federated results in `urn:sempkm:mirrored` with provenance metadata (source endpoint IRI)
- "Mirror Results" button in SPARQL console sends query results to MirrorService
- SPARQL console SERVICE clause assistance: endpoint autocomplete from allowlist
- Mirrored triples visible on object pages with `source: "mirrored"` tagging and provenance badge
- `check_member_query_safety()` updated to allow SERVICE for members (it's safe — SERVICE only reads remote data)
- `_VOCAB_PREFIXES` (backend) and `KNOWN_VOCAB_PREFIXES` (frontend) include `urn:sempkm:mirror:` namespace

## Proof Level

- This slice proves: contract + integration (SERVICE pass-through correctness, mirrored graph storage and retrieval, end-to-end mirror flow)
- Real runtime required: yes (triplestore for integration, mock for unit)
- Human/UAT required: no (automated tests cover the contracts)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py tests/test_federation_allowlist.py -v` — all pass
- Unit tests verify: SERVICE clause detection/pass-through (6+ cases), mirrored graph FROM injection, mirror storage with provenance, allowlist CRUD
- Integration-level: MirrorService stores triples in named graph, retrieves them with provenance metadata
- Failure-path: MirrorService returns structured error dict (endpoint, message, timestamp) on federation failure; verify error dict shape in unit test

## Observability / Diagnostics

- Runtime signals: structured logging in MirrorService (mirror operations with endpoint, triple count, timestamp), federation allowlist changes logged
- Inspection surfaces: `GET /api/federation/endpoints` returns current allowlist; `urn:sempkm:mirrored` graph queryable via SPARQL console with all_graphs
- Failure visibility: MirrorService returns error dict with endpoint URL, error message, timestamp on federation failure
- Redaction constraints: none (endpoint URLs are not secrets)

## Integration Closure

- Upstream surfaces consumed: `backend/app/sparql/client.py` (scope_to_current_graph), `backend/app/rdf/namespaces.py` (graph IRIs), `backend/app/triplestore/client.py` (SPARQL update), `backend/app/browser/objects.py` (property source tagging), `frontend/static/js/sparql-console.js` (editor toolbar), `backend/app/templates/browser/settings_page.html` (settings categories)
- New wiring introduced: MirrorService class, federation allowlist API router, mirrored graph in scope injection, "Mirror Results" toolbar button, Federation settings panel
- What remains before milestone is truly usable end-to-end: nothing for federation; other slices (S02-S07) are independent features

## Tasks

- [x] **T01: Extend scope_to_current_graph() for SERVICE pass-through and mirrored graph** `est:1.5h`
  - Why: The core technical risk — `scope_to_current_graph()` injects `FROM` before `WHERE`, but SERVICE clauses have their own WHERE blocks. Without fixing this, any federated query is mangled. Also need `MIRRORED_GRAPH_IRI` in the FROM injection alongside current/inferred.
  - Files: `backend/app/sparql/client.py`, `backend/app/rdf/namespaces.py`, `backend/tests/test_sparql_client.py`
  - Do: (1) Add `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` to namespaces.py, export it. (2) In `scope_to_current_graph()`, before injecting FROM, detect SERVICE blocks in the stripped query and protect them — replace SERVICE...{...} bodies with placeholders, inject FROM before the outer WHERE, then restore SERVICE bodies. Add `include_mirrored: bool = True` parameter, default True. (3) Update `check_member_query_safety()` to NOT reject SERVICE clauses — SERVICE only reads remote data and is safe for members. (4) Add `urn:sempkm:mirror:` to `_VOCAB_PREFIXES` in router.py. (5) Write comprehensive unit tests for SERVICE detection and mirrored graph injection.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all existing tests still pass, new SERVICE tests pass
  - Done when: A query like `SELECT ?x WHERE { ?s a ?t . SERVICE <http://example.org/sparql> { ?x rdfs:label ?l } }` gets FROM injected only before the outer WHERE, not inside SERVICE. Mirrored graph is in FROM clauses.

- [x] **T02: Federation endpoint allowlist — API and settings UI** `est:1.5h`
  - Why: Federation SERVICE queries against arbitrary endpoints is a security risk. An admin-managed allowlist stored in InstanceConfig gates which endpoints are permitted. The settings UI lets admins manage it.
  - Files: `backend/app/federation/allowlist.py`, `backend/app/federation/allowlist_router.py`, `backend/app/templates/browser/_federation_settings.html`, `backend/app/templates/browser/settings_page.html`, `backend/app/browser/settings.py`, `backend/tests/test_federation_allowlist.py`
  - Do: (1) Create `allowlist.py` with `FederationAllowlist` class: get_endpoints(), add_endpoint(url, label), remove_endpoint(url), is_allowed(url) — all backed by InstanceConfig key `federation.allowed_endpoints` storing JSON array. (2) Create `allowlist_router.py` with `GET /api/federation/endpoints`, `POST /api/federation/endpoints`, `DELETE /api/federation/endpoints/{endpoint_url}` — owner-only. (3) Create `_federation_settings.html` partial with endpoint list, add form, delete buttons. (4) Add "Federation" category button to settings_page.html sidebar and include the partial. (5) Wire the allowlist check into `_execute_sparql()` — parse SERVICE URIs from query and reject if not in allowlist (owner bypasses). (6) Write unit tests for allowlist CRUD.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_federation_allowlist.py -v` — all pass
  - Done when: Allowlist CRUD works via API. Settings page shows Federation category with endpoint management. Non-allowlisted SERVICE endpoints are rejected with clear error message.

- [x] **T03: Mirror service and "Mirror Results" SPARQL console action** `est:2h`
  - Why: The mirror service stores federated query results in `urn:sempkm:mirrored` with provenance. The "Mirror Results" button in the SPARQL console triggers it. These are tightly coupled — the button calls the service endpoint.
  - Files: `backend/app/federation/mirror_service.py`, `backend/app/federation/mirror_router.py`, `backend/app/main.py`, `frontend/static/js/sparql-console.js`, `backend/app/templates/browser/sparql_panel.html`, `frontend/static/css/workspace.css`, `backend/tests/test_mirror_service.py`
  - Do: (1) Create `mirror_service.py` with `MirrorService(client: TriplestoreClient)`: `mirror_results(bindings, source_endpoint, query_text)` — converts SPARQL JSON bindings to triples, stores in `urn:sempkm:mirrored` graph via `insert_graph()`, writes provenance metadata (source endpoint, mirror timestamp, original query hash) as a `urn:sempkm:mirror:{uuid}` resource. (2) Create `mirror_router.py` with `POST /api/sparql/mirror` accepting `{bindings, source_endpoint, query_text}` — calls MirrorService. (3) Register router in main.py. (4) Add "Mirror Results" button to sparql_panel.html toolbar (after Run/Save/History/Saved). (5) In sparql-console.js, wire the button: on click, POST current results + detected SERVICE endpoint to `/api/sparql/mirror`, show success/failure toast. (6) Add CSS for mirror button and toast. (7) Write unit tests for MirrorService.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — all pass
  - Done when: MirrorService stores triples in urn:sempkm:mirrored with provenance. SPARQL console has a "Mirror Results" button that's enabled after a successful federated query execution, and clicking it stores the results.

- [x] **T04: SPARQL console SERVICE clause UI assistance** `est:1h`
  - Why: Users need help writing SERVICE queries — endpoint URLs are hard to remember, and each endpoint has different PREFIX conventions. Autocomplete from the allowlist and PREFIX injection for known endpoints (Wikidata, DBpedia) make federation accessible.
  - Files: `frontend/static/js/sparql-console.js`, `frontend/static/css/workspace.css`
  - Do: (1) Fetch allowlist on console init via `GET /api/federation/endpoints`. (2) Add SERVICE clause autocomplete in CodeMirror: when user types `SERVICE <`, suggest allowed endpoints. (3) When a SERVICE clause with a known endpoint (Wikidata, DBpedia) is detected, auto-inject relevant PREFIXes (wdt:, wd:, wikibase:, etc.) into prefix suggestions. (4) Add a "SERVICE" snippet button to toolbar or as a code snippet (inserts `SERVICE <endpoint> { }` template). (5) Style autocomplete items with endpoint labels.
  - Verify: Manual inspection of SPARQL console — typing `SERVICE <` shows endpoint suggestions from allowlist
  - Done when: SPARQL console suggests allowed endpoints when writing SERVICE clauses and offers PREFIX injection for Wikidata/DBpedia.

- [x] **T05: Mirrored triple indicators on object pages and comprehensive test suite** `est:1.5h`
  - Why: Mirrored triples must be visually distinct from user-created and inferred data. Object pages already display inferred triples with badges — mirrored triples follow the same pattern with a different badge. This task also writes the integration test that validates the full mirror flow.
  - Files: `backend/app/browser/objects.py`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`, `frontend/static/js/graph.js`, `backend/tests/test_mirror_service.py`
  - Do: (1) In objects.py `object_read_page()`, add a third GRAPH query for `urn:sempkm:mirrored` (parallel to existing inferred query), tag values with `source: "mirrored"`. Also query provenance metadata (source endpoint) for mirrored properties. (2) In workspace.js, render mirrored properties with a "mirrored" badge showing the source endpoint as tooltip (similar to `.inferred-badge`). (3) In workspace.css, add `.mirrored-badge` styles (blue/teal color scheme to distinguish from inferred purple). (4) In graph.js, add `.mirrored-edge` style (dotted line, different color from inferred dashed). (5) Add `KNOWN_VOCAB_PREFIXES` entry for `urn:sempkm:mirror:`. (6) Extend test_mirror_service.py with integration-level test verifying the full flow: store → scope includes mirrored → provenance queryable.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_sparql_client.py -v` — all pass
  - Done when: Object pages show mirrored properties with a distinct badge. Graph view shows mirrored edges with dotted style. All unit and integration tests pass.

## Files Likely Touched

- `backend/app/rdf/namespaces.py`
- `backend/app/sparql/client.py`
- `backend/app/sparql/router.py`
- `backend/app/federation/allowlist.py`
- `backend/app/federation/allowlist_router.py`
- `backend/app/federation/mirror_service.py`
- `backend/app/federation/mirror_router.py`
- `backend/app/main.py`
- `backend/app/browser/objects.py`
- `backend/app/browser/settings.py`
- `backend/app/templates/browser/sparql_panel.html`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_federation_settings.html`
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_sparql_client.py`
- `backend/tests/test_mirror_service.py`
- `backend/tests/test_federation_allowlist.py`
