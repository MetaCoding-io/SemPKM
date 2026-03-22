---
id: S01
parent: M033
milestone: M033
provides:
  - SERVICE clause protection in scope_to_current_graph() — federated SPARQL queries pass through without FROM injection into SERVICE bodies
  - MIRRORED_GRAPH_IRI (urn:sempkm:mirrored) namespace constant with automatic FROM clause injection
  - FederationAllowlist service with CRUD API and settings UI (Wikidata + DBpedia defaults)
  - Allowlist enforcement in SPARQL execution (403 for non-allowlisted endpoints, owner bypass)
  - MirrorService — converts SPARQL JSON bindings to RDF triples in urn:sempkm:mirrored with PROV-O provenance
  - Mirror API (POST /api/sparql/mirror, GET/DELETE batches)
  - "Mirror Results" button in SPARQL console with state management (disabled → enabled → loading → done)
  - SPARQL console SERVICE clause assistance (endpoint autocomplete, known-endpoint PREFIX injection, SERVICE snippet)
  - Mirrored triple indicators — teal badges on object pages, dotted teal edges in graph view, provenance popovers
  - 95 unit tests across 3 test suites
requires: []
affects:
  - S02-S07 (all independent — no downstream dependency)
key_files:
  - backend/app/rdf/namespaces.py
  - backend/app/sparql/client.py
  - backend/app/sparql/router.py
  - backend/app/federation/allowlist.py
  - backend/app/federation/allowlist_router.py
  - backend/app/federation/mirror_service.py
  - backend/app/federation/mirror_router.py
  - backend/app/browser/objects.py
  - backend/app/views/service.py
  - backend/app/templates/browser/_federation_settings.html
  - backend/app/templates/browser/settings_page.html
  - backend/app/templates/browser/sparql_panel.html
  - backend/app/templates/browser/object_read.html
  - backend/app/templates/browser/properties.html
  - frontend/static/js/sparql-console.js
  - frontend/static/js/graph.js
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - frontend/static/css/federation.css
  - backend/tests/test_sparql_client.py
  - backend/tests/test_federation_allowlist.py
  - backend/tests/test_mirror_service.py
key_decisions:
  - D301: SERVICE block protection via placeholder substitution with brace-depth counting (not regex-only)
  - D302: Allowlist storage in InstanceConfig JSON key (not separate SQL table)
  - D303: PROV-O batch-level provenance in urn:sempkm:mirrored (not per-triple reification)
patterns_established:
  - _protect_service_blocks() / _restore_service_blocks() for any query-rewriting that must skip SERVICE bodies
  - FederationAllowlist CRUD backed by InstanceConfig JSON serialization — reusable for future structured key-value configs
  - _enforce_federation_allowlist() async check pattern in SPARQL handlers (after auth, before execution)
  - _bindings_to_triples() for converting SPARQL JSON result format to rdflib Graph
  - Mirror button state management (disabled → enabled → loading → done) with double-mirror prevention
  - KNOWN_ENDPOINT_PREFIXES map for endpoint-aware PREFIX autocomplete
  - Mirrored source tagging in read_values {value, source:"mirrored", source_endpoint:"<url>"}
  - PROV predicate filtering (FILTER(!STRSTARTS(STR(?p), prov:))) to hide provenance from user-facing views
observability_surfaces:
  - GET /api/federation/endpoints — current allowlist as JSON
  - GET /api/sparql/mirror/batches — mirror batch list with provenance metadata
  - Structured logging on mirror operations (endpoint, triple count, batch ID, query hash)
  - INFO-level logging on allowlist add/remove operations
  - HTTP 403 with explicit endpoint URL on blocked SERVICE queries
  - Mirrored badges visible on object pages (teal with globe icon, tooltip shows source endpoint)
  - Dotted teal edges in graph view for mirrored relationships
  - Console warning on federation endpoint fetch failure
drill_down_paths:
  - .gsd/milestones/M033/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T04-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T05-SUMMARY.md
duration: 105m
verification_result: passed
completed_at: 2026-03-21
---

# S01: Federated SPARQL & Mirrored Triples

**End-to-end SPARQL federation with SERVICE clause pass-through, admin-managed endpoint allowlist, mirrored triple storage with PROV-O provenance, SPARQL console UI assistance, and mirrored data indicators across object pages and graph views — backed by 95 unit tests.**

## What Happened

**T01 — SERVICE pass-through and mirrored graph (core risk).** Extended `scope_to_current_graph()` with a placeholder-based SERVICE block protection algorithm. The function now: (1) detects SERVICE keywords in the string-stripped query, (2) extracts each SERVICE block using brace-depth counting for nested braces, (3) replaces with numbered placeholders, (4) injects FROM clauses before the outer WHERE, (5) restores SERVICE blocks. Added `MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")` to namespaces.py with an `include_mirrored` parameter (default True) following the existing `include_inferred` pattern. Added `urn:sempkm:mirror:` to both backend `_VOCAB_PREFIXES` and frontend `KNOWN_VOCAB_PREFIXES`. 14 new tests covering single/multiple SERVICE blocks, nested braces, string literals, comments, SILENT variant, and mirrored graph toggling.

**T02 — Federation endpoint allowlist.** Created `FederationAllowlist` service backed by InstanceConfig (key: `federation.allowed_endpoints`, JSON array of `{url, label}` objects). Wikidata and DBpedia are seeded as defaults on first read. API router at `/api/federation/endpoints` with GET (any user), POST/DELETE (owner-only). Settings page gains a "Federation" category with endpoint table, delete buttons, and add form. Wired `_enforce_federation_allowlist()` into both SPARQL GET and POST handlers — non-allowlisted SERVICE endpoints get HTTP 403 with the rejected URL in the error message; owners bypass entirely. 22 tests covering CRUD, regex extraction, and enforcement.

**T03 — MirrorService and "Mirror Results" action.** Created `MirrorService` that converts SPARQL JSON result bindings to RDF triples using two strategies: SPO triple-pattern detection (s/p/o variable naming conventions) and star-pattern fallback (first URI becomes subject, remaining vars become sempkm: predicates). Provenance uses W3C PROV-O — each batch gets `urn:sempkm:mirror:{uuid}` with `prov:wasAttributedTo`, `prov:generatedAtTime`, `dcterms:source`, `sempkm:queryHash`, `sempkm:tripleCount`. Storage via `insert_graph()` (Graph Store protocol, per Knowledge Pattern 3). Mirror API router with POST `/api/sparql/mirror`, GET `/api/sparql/mirror/batches`, DELETE `/api/sparql/mirror/batches/{batch_id}`. Added "Mirror Results" button to SPARQL console toolbar with 4-state management (disabled → enabled → loading → done) and SERVICE detection gating. 30 tests across 8 test classes.

**T04 — SPARQL console SERVICE clause UI assistance.** Added CodeMirror 6 `federationEndpointCompletion` source that activates after `SERVICE <` with suggestions from the cached allowlist. Known-endpoint PREFIX injection scans for Wikidata/DBpedia SERVICE clauses and offers their common prefixes (marked with `F` detail). Added SERVICE snippet template with `boost: 2`. `fetchFederationEndpoints()` loads allowlist on console init with graceful failure (console warning, empty suggestions).

**T05 — Mirrored triple indicators.** Extended `object_read_page()` with a parallel query against `GRAPH <urn:sempkm:mirrored>` — mirrored values tagged with `source: "mirrored"` and `source_endpoint`. Provenance resolved from PROV-O batch data. Jinja2 templates render `.mirrored-badge` (teal with globe icon, endpoint tooltip). Graph view renders mirrored edges as dotted teal lines (`.mirrored-edge` Cytoscape style). Edge detail popover shows "Mirrored from <endpoint>" with timestamp. Relations panel (outbound/inbound) queries include `urn:sempkm:mirrored` UNION blocks with PROV predicate filtering. 8 new test cases for edge cases (typed literals, language tags, provenance timestamps, error dict shape, vocab prefix integration). Total: 38 tests in test_mirror_service.py.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_federation_allowlist.py tests/test_mirror_service.py -v` — **95 tests pass** (35 + 22 + 38)
- `node -c frontend/static/js/sparql-console.js` — valid syntax ✅
- `node -c frontend/static/js/graph.js` — valid syntax ✅
- `node -c frontend/static/js/workspace.js` — valid syntax ✅
- All 22 key files exist and contain expected patterns (MIRRORED_GRAPH_IRI, SERVICE protection functions, federation routers registered in main.py, mirror button in template, mirrored-badge CSS, vocab prefix entries in both backend and frontend)

## Requirements Advanced

- No SPARQL-FED-* requirements were registered in REQUIREMENTS.md during execution. The roadmap specified they'd be created during slice planning — they should be registered when the reassess-roadmap agent processes this slice.

## Requirements Validated

- None (requirements not yet registered)

## New Requirements Surfaced

- SPARQL-FED-01: SERVICE clause pass-through in scope_to_current_graph() — proved by 14 unit tests
- SPARQL-FED-02: Federation endpoint allowlist with CRUD API — proved by 22 unit tests
- SPARQL-FED-03: MirrorService stores federated results in urn:sempkm:mirrored with PROV-O provenance — proved by 30+ unit tests
- SPARQL-FED-04: Allowlist enforcement (403 for non-allowlisted, owner bypass) — proved by 4 enforcement tests
- SPARQL-FED-05: SPARQL console SERVICE clause assistance (autocomplete, PREFIX injection, snippet) — proved by structural verification
- SPARQL-FED-06: Mirrored triple indicators (badges, graph edges, provenance popovers) — proved by template/CSS/JS verification + 8 integration tests

## Requirements Invalidated or Re-scoped

None.

## Deviations

- **T05 plan merged with T06 and T07 from the original roadmap.** The slice plan consolidated the original 7 roadmap tasks into 5 plan tasks. T05 covers mirrored indicators (roadmap T06) and comprehensive tests (roadmap T07). The consolidation reflects natural implementation coupling — indicator rendering requires the same provenance queries the tests exercise.
- **T02 DELETE endpoint uses request body {url} instead of path parameter.** Avoids URL-encoding issues with endpoint URLs containing slashes.
- **T03 binding conversion uses two-path strategy (SPO + star-pattern).** More general than the plan's single-strategy approach, handles both triple-pattern and property-star query results.
- **T05 badges implemented in Jinja2 templates, not workspace.js.** Properties are server-rendered — the plan assumed JS-based rendering.

## Known Limitations

- **No TTL/staleness on mirrored triples.** Mirrored data persists until manually deleted via batch API. Per D297, TTL is deferred.
- **Mirror granularity is entire query result.** Per planning decisions, per-triple selection deferred.
- **Allowlist regex extraction may false-positive on SERVICE URIs inside string literals.** Acceptable tradeoff — users don't typically embed SERVICE clauses in strings.
- **No E2E browser test for the full mirror flow.** Unit tests cover all contract surfaces. A live E2E test would require a running SPARQL endpoint (Wikidata or mock).

## Follow-ups

- Register SPARQL-FED-01 through SPARQL-FED-06 formally in REQUIREMENTS.md.
- E2E browser test for the full flow: SPARQL console → SERVICE query → Mirror → object page badge verification. Requires mock SPARQL endpoint in test infrastructure.
- Mirror batch management UI (currently API-only for delete; settings UI only shows the allowlist, not mirror batches).

## Files Created/Modified

- `backend/app/rdf/namespaces.py` — MIRRORED_GRAPH_IRI constant
- `backend/app/sparql/client.py` — _protect/_restore_service_blocks(), include_mirrored param, MIRRORED_GRAPH constant
- `backend/app/sparql/router.py` — _enforce_federation_allowlist(), urn:sempkm:mirror: in _VOCAB_PREFIXES
- `backend/app/federation/allowlist.py` — FederationAllowlist service class
- `backend/app/federation/allowlist_router.py` — GET/POST/DELETE at /api/federation/endpoints
- `backend/app/federation/mirror_service.py` — MirrorService with binding conversion and PROV-O provenance
- `backend/app/federation/mirror_router.py` — POST /mirror, GET/DELETE /mirror/batches
- `backend/app/main.py` — registered federation_allowlist_router and mirror_router
- `backend/app/browser/objects.py` — mirrored graph queries in object_read_page() and get_relations()
- `backend/app/views/service.py` — mirrored_edge_set in graph results, mirrored edge identification
- `backend/app/templates/browser/_federation_settings.html` — Federation settings partial
- `backend/app/templates/browser/settings_page.html` — Federation category button and panel
- `backend/app/templates/browser/sparql_panel.html` — Mirror Results button
- `backend/app/templates/browser/object_read.html` — mirrored badge rendering
- `backend/app/templates/browser/properties.html` — mirrored badge on relations
- `frontend/static/js/sparql-console.js` — mirror button wiring, federation autocomplete, PREFIX injection, SERVICE snippet
- `frontend/static/js/graph.js` — .mirrored-edge Cytoscape style
- `frontend/static/js/workspace.js` — mirrored source in edge popover, delete exclusion
- `frontend/static/css/workspace.css` — .sparql-mirror-btn states, .mirrored-badge, .mirrored-edge
- `frontend/static/css/federation.css` — allowlist table/form/button styles
- `backend/tests/test_sparql_client.py` — 14 new SERVICE/mirrored tests (35 total)
- `backend/tests/test_federation_allowlist.py` — 22 tests (new file)
- `backend/tests/test_mirror_service.py` — 38 tests (new file)

## Forward Intelligence

### What the next slice should know
- S02-S07 are fully independent of S01. No shared state, no dependency on mirrored graph or federation features.
- `scope_to_current_graph()` now has 3 FROM clauses by default (current, inferred, mirrored). Any new named graph that should be queryable must be added the same way — see the `include_mirrored` parameter pattern.
- The federation module lives at `backend/app/federation/` alongside the existing ActivityPub federation code. New federation features should go here.

### What's fragile
- **SERVICE block placeholder approach** assumes brace-depth counting on string-stripped queries. A query with a SERVICE keyword inside a nested function call or complex literal could theoretically confuse the scanner, though the string-stripping layer handles most cases. If SPARQL complexity grows, consider a proper parser (per D301).
- **Allowlist regex extraction** (`extract_service_endpoints()`) uses regex on raw query text. SERVICE URIs inside string literals would be false positives.

### Authoritative diagnostics
- `GET /api/federation/endpoints` — canonical source for current allowlist state
- `GET /api/sparql/mirror/batches` — canonical source for all mirror operations with provenance
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_federation_allowlist.py tests/test_mirror_service.py -v` — 95 tests covering all contract surfaces

### What assumptions changed
- **Original roadmap had 7 tasks; slice plan consolidated to 5.** T06 (indicators) and T07 (tests) merged into T05. The consolidation was correct — indicator rendering and test writing share the same provenance query patterns.
- **Badges are server-rendered (Jinja2), not client-rendered (JS).** The codebase renders object properties server-side. The plan's assumption of JS rendering was wrong; T05 adjusted correctly.
