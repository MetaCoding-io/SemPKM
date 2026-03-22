# S01: Federated SPARQL & Mirrored Triples

**Goal:** Users can write SPARQL queries with SERVICE clauses targeting external endpoints, mirror federated results into `urn:sempkm:mirrored`, and see mirrored triples alongside local and inferred data with provenance badges.
**Demo:** User writes SERVICE query in SPARQL console, sees federated results, clicks Mirror, triples persist in `urn:sempkm:mirrored` with provenance badges in object views and graph edges.

## Must-Haves

- `scope_to_current_graph()` detects SERVICE clauses and passes them through without injecting FROM into the SERVICE block's inner pattern
- `scope_to_current_graph()` adds `FROM <urn:sempkm:mirrored>` alongside current and inferred graphs
- `MIRRORED_GRAPH_IRI` constant defined in `app.rdf.namespaces`
- Configurable endpoint allowlist (list of allowed SPARQL endpoint URLs, admin-only)
- Mirror service stores federated query results in `urn:sempkm:mirrored` with provenance metadata
- Mirror API endpoint (`POST /api/sparql/mirror`) accepts query text and stores results
- Object detail page queries `GRAPH <urn:sempkm:mirrored>` and tags properties with `source: "mirrored"`
- Graph view shows mirrored edges with distinct styling (dotted lines, different from inferred dashed lines)
- SPARQL console has "Mirror Results" button on federated query results
- Provenance badge in UI shows which endpoint sourced mirrored triples
- `check_member_query_safety()` rejects SERVICE clauses for member role (security)
- All new backend logic has unit tests

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (SERVICE queries hit external endpoints; unit tests mock them)
- Human/UAT required: no (automated tests + manual smoke test via SPARQL console)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` — all pass
- `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` — constant exists
- `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` — mirrored graph queried in object detail
- `rg "mirror" frontend/static/js/sparql-console.js` — mirror button exists in console
- `rg "mirrored-badge\|mirrored-edge" frontend/static/css/workspace.css` — provenance styling exists

## Observability / Diagnostics

- Runtime signals: `logger.info` for mirror operations (endpoint, triple count, provenance graph), `logger.warning` for blocked endpoints
- Inspection surfaces: `GET /api/sparql/mirror/endpoints` returns configured allowlist; mirror service logs query provenance
- Failure visibility: mirror API returns structured JSON errors for disallowed endpoints, empty results, and triplestore write failures
- Redaction constraints: external endpoint URLs are not secrets; no PII in mirrored triples

## Integration Closure

- Upstream surfaces consumed: `backend/app/sparql/client.py` (scope_to_current_graph), `backend/app/rdf/namespaces.py` (graph IRIs), `backend/app/browser/objects.py` (property rendering), `frontend/static/js/sparql-console.js` (result rendering)
- New wiring introduced: `MIRRORED_GRAPH_IRI` added to FROM clause injection; mirror router mounted in `main.py`; mirrored graph queried in object detail; mirror button in SPARQL console
- What remains before the milestone is truly usable end-to-end: S02-S07 are independent features; this slice is self-contained

## Tasks

- [x] **T01: SERVICE clause pass-through and mirrored graph scoping** `est:1.5h`
  - Why: The #1 risk in this slice — `scope_to_current_graph()` uses regex to inject FROM clauses before WHERE. SERVICE clauses contain inner WHERE blocks that must not be scoped. Also need to add `urn:sempkm:mirrored` to the FROM clause set.
  - Files: `backend/app/rdf/namespaces.py`, `backend/app/sparql/client.py`, `backend/tests/test_sparql_client.py`
  - Do: (1) Add `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` to namespaces.py. (2) Refactor `scope_to_current_graph()` to detect SERVICE blocks and exclude them from FROM injection — use brace-depth counting to find the outer WHERE vs inner SERVICE WHERE. (3) Add `include_mirrored: bool = True` parameter that adds `FROM <urn:sempkm:mirrored>`. (4) Update `check_member_query_safety()` to reject SERVICE clauses for member role. (5) Add ~25 unit tests covering: SERVICE pass-through, nested SERVICE, SERVICE inside OPTIONAL, mirrored graph inclusion, member safety rejection of SERVICE.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all pass including new SERVICE tests
  - Done when: SERVICE clauses survive `scope_to_current_graph()` intact; FROM `<urn:sempkm:mirrored>` appears in scoped queries; member queries with SERVICE are rejected

- [x] **T02: Mirror service, endpoint allowlist, and API endpoints** `est:2h`
  - Why: Core backend capability — stores federated results as mirrored triples with provenance. Endpoint allowlist prevents querying arbitrary external endpoints.
  - Files: `backend/app/sparql/mirror.py`, `backend/app/sparql/mirror_router.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/tests/test_mirror_service.py`
  - Do: (1) Add `federation_allowed_endpoints: str = ""` to config.py (comma-separated URLs, empty = all blocked). (2) Create `mirror.py` with `MirrorService` class: `mirror_results(query, endpoint_url)` extracts SERVICE results, stores triples in `urn:sempkm:mirrored` via SPARQL INSERT DATA with provenance (each mirror batch gets a provenance graph `urn:sempkm:mirror-prov:{uuid}` linking to source endpoint via `prov:wasAttributedTo`). (3) Create `mirror_router.py` with: `POST /api/sparql/mirror` (accepts `{query, endpoint_url}`, validates endpoint against allowlist, executes query, stores mirrored triples); `GET /api/sparql/mirror/endpoints` (returns allowlist); `DELETE /api/sparql/mirror` (clears all mirrored triples). (4) Mount router in `main.py`. (5) Add ~20 unit tests covering: allowlist validation, mirror storage, provenance creation, clear operation, blocked endpoint rejection.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — all pass
  - Done when: mirror API accepts federated results and stores them with provenance; disallowed endpoints are rejected with 403; allowlist is configurable via env var

- [x] **T03: Mirrored triples in object views and graph edges** `est:1.5h`
  - Why: Users need to see mirrored triples alongside local and inferred data, with visual distinction showing their external provenance.
  - Files: `backend/app/browser/objects.py`, `backend/app/templates/browser/object_read.html`, `frontend/static/css/workspace.css`, `frontend/static/js/graph.js`, `backend/app/sparql/router.py`, `frontend/static/js/sparql-console.js`
  - Do: (1) In `objects.py`, add a mirrored-properties query block (same pattern as lines 119-145 for inferred) querying `GRAPH <urn:sempkm:mirrored>`, tag values with `source: "mirrored"`. (2) In `objects.py` edge query (lines 479-519), add a UNION for mirrored graph with `BIND("mirrored" AS ?source)`. (3) In `object_read.html`, add mirrored badge template (similar to `.inferred-badge` but with different text/color). (4) In `workspace.css`, add `.mirrored-badge` styling (teal/cyan color to distinguish from inferred purple) and `.prop-mirrored` row styling. (5) In `graph.js`, add `.mirrored-edge` style (dotted line, teal color) alongside existing `.inferred-edge` (dashed line, purple). (6) Add `urn:sempkm:mirror-prov:` to `_VOCAB_PREFIXES` in `sparql/router.py` and `KNOWN_VOCAB_PREFIXES` in `sparql-console.js`.
  - Verify: `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` shows mirrored graph queries; `rg "mirrored-badge" frontend/static/css/workspace.css` shows styling
  - Done when: Object detail page shows mirrored properties with teal provenance badge; graph edges from mirrored triples render with dotted teal lines; mirrored namespace excluded from IRI enrichment

- [ ] **T04: SPARQL console Mirror button and endpoint picker** `est:1.5h`
  - Why: Users need a way to trigger mirroring from the SPARQL console after running a federated query, and see which endpoints are available.
  - Files: `frontend/static/js/sparql-console.js`, `frontend/static/css/workspace.css`
  - Do: (1) Add SERVICE clause detection in the query text (scan for `SERVICE <url>` pattern). (2) When query results render successfully and query contains SERVICE, show a "Mirror Results" button next to the existing result info bar. (3) Mirror button calls `POST /api/sparql/mirror` with the query text and detected endpoint URL. (4) Show success/error toast after mirror operation. (5) Add endpoint allowlist indicator — if the detected endpoint is not in the allowlist, show a warning icon on the Mirror button. (6) Add `.sparql-mirror-btn` styling in workspace.css. (7) After successful mirror, show a count of mirrored triples.
  - Verify: `rg "mirror" frontend/static/js/sparql-console.js` — mirror button and SERVICE detection present; `rg "sparql-mirror-btn" frontend/static/css/workspace.css` — button styled
  - Done when: SPARQL console shows Mirror button for SERVICE queries; clicking it stores triples and shows success feedback; disallowed endpoints show warning

## Files Likely Touched

- `backend/app/rdf/namespaces.py`
- `backend/app/sparql/client.py`
- `backend/app/sparql/router.py`
- `backend/app/sparql/mirror.py` (new)
- `backend/app/sparql/mirror_router.py` (new)
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/browser/objects.py`
- `backend/app/templates/browser/object_read.html`
- `backend/tests/test_sparql_client.py`
- `backend/tests/test_mirror_service.py` (new)
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
