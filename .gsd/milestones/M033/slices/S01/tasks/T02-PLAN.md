---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T02: Mirror service, endpoint allowlist, and API endpoints

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Build the backend mirror service that stores federated SPARQL query results as triples in `urn:sempkm:mirrored` with provenance tracking. Each mirror operation records which external endpoint provided the data. An endpoint allowlist (configurable via environment variable) controls which external SPARQL endpoints users are permitted to query.

The service follows the same structural pattern as `InferenceService` — a domain service class with async methods operating on the triplestore, paired with a FastAPI router for HTTP endpoints.

## Steps

1. **Add `federation_allowed_endpoints` to `backend/app/config.py`:**
   - Add `federation_allowed_endpoints: str = ""` to the Settings class. This is a comma-separated list of allowed SPARQL endpoint URLs (e.g., `https://query.wikidata.org/sparql,https://dbpedia.org/sparql`). Empty string means no endpoints are allowed (secure default).
   - Add a helper method `get_allowed_endpoints() -> list[str]` that parses the comma-separated string and strips whitespace.

2. **Create `backend/app/sparql/mirror.py` with `MirrorService`:**
   - Constructor takes `TriplestoreClient`.
   - `validate_endpoint(url: str) -> bool` checks if the URL is in the allowlist.
   - `mirror_results(bindings: list[dict], vars: list[str], endpoint_url: str) -> MirrorResult` — takes parsed SPARQL JSON result bindings, converts URI bindings to triples, stores in `urn:sempkm:mirrored` via `INSERT DATA`, creates provenance metadata in a `urn:sempkm:mirror-prov:{uuid}` named graph linking each mirrored triple batch to its source endpoint via `prov:wasAttributedTo <endpoint_url>` and `prov:generatedAtTime`.
   - `clear_mirrored() -> int` — drops `urn:sempkm:mirrored` graph and all `urn:sempkm:mirror-prov:*` graphs, returns count of cleared triples.
   - `get_mirror_stats() -> dict` — returns count of mirrored triples and list of source endpoints.
   - `MirrorResult` dataclass with `triple_count: int`, `provenance_graph: str`, `endpoint: str`.

3. **Create `backend/app/sparql/mirror_router.py`:**
   - `POST /api/sparql/mirror` — accepts JSON `{query: str, endpoint_url: str}`. Validates endpoint against allowlist (403 if blocked). Executes the user's original query via the triplestore client (RDF4J handles the SERVICE clause natively). Passes the result bindings to `MirrorService.mirror_results()`. Returns `{mirrored_count, provenance_graph}`.
   - `GET /api/sparql/mirror/endpoints` — returns the allowlist as JSON `{endpoints: [...], allowlist_configured: bool}`.
   - `DELETE /api/sparql/mirror` — owner-only, clears all mirrored triples.
   - `GET /api/sparql/mirror/stats` — returns mirror statistics (triple count, source endpoints).
   - All endpoints require authentication; POST/DELETE require owner role.

4. **Mount the router in `backend/app/main.py`:**
   - Import `mirror_router` and include it with the existing SPARQL routers. Add `from app.sparql.mirror_router import router as mirror_router` and `app.include_router(mirror_router)`.

5. **Write unit tests in `backend/tests/test_mirror_service.py`:**
   - Test `validate_endpoint()` with allowed and blocked URLs.
   - Test `mirror_results()` with mock TriplestoreClient — verify INSERT DATA SPARQL includes correct triples and provenance graph.
   - Test `clear_mirrored()` calls CLEAR GRAPH on the mirrored graph.
   - Test `get_allowed_endpoints()` parsing with various formats (empty, single, multiple, whitespace).
   - Test router endpoint validation (mock auth, verify 403 for blocked endpoints).
   - Test mirror with empty bindings returns 0 count.
   - Test provenance graph IRI format includes UUID.
   - ~20 tests total.

## Must-Haves

- [ ] `federation_allowed_endpoints` config setting exists with secure default (empty = all blocked)
- [ ] `MirrorService` stores triples in `urn:sempkm:mirrored` via SPARQL INSERT DATA
- [ ] Provenance metadata stored in `urn:sempkm:mirror-prov:{uuid}` named graphs
- [ ] `POST /api/sparql/mirror` validates endpoint against allowlist before proceeding
- [ ] `DELETE /api/sparql/mirror` clears mirrored triples (owner-only)
- [ ] Router mounted in `main.py`
- [ ] Unit tests cover allowlist validation, mirror storage, provenance, and clear

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — all tests pass
- `rg "mirror_router" backend/app/main.py` — router is mounted

## Inputs

- `backend/app/rdf/namespaces.py` — `MIRRORED_GRAPH_IRI` constant from T01
- `backend/app/sparql/client.py` — `scope_to_current_graph()` with SERVICE support from T01
- `backend/app/triplestore/client.py` — TriplestoreClient API (query, update, construct methods)
- `backend/app/config.py` — Settings class to extend
- `backend/app/main.py` — app instance for router mounting
- `backend/app/inference/service.py` — reference pattern for domain service structure

## Expected Output

- `backend/app/sparql/mirror.py` — MirrorService with mirror_results, validate_endpoint, clear_mirrored, get_mirror_stats
- `backend/app/sparql/mirror_router.py` — FastAPI router with POST/GET/DELETE endpoints
- `backend/app/config.py` — with federation_allowed_endpoints setting
- `backend/app/main.py` — with mirror_router mounted
- `backend/tests/test_mirror_service.py` — ~20 unit tests

## Observability Impact

- **New signals:** `logger.info` in MirrorService for mirror operations (endpoint, triple count, provenance graph IRI), `logger.warning` in mirror_router for blocked endpoint attempts (includes endpoint URL and user email).
- **Inspection:** `GET /api/sparql/mirror/endpoints` returns the configured allowlist; `GET /api/sparql/mirror/stats` returns triple count and source endpoint list. Both are authenticated but available to any role.
- **Failure visibility:** Mirror router returns structured JSON errors: 403 with `detail: "Endpoint not in allowlist: <url>"` for blocked endpoints, 502 for upstream query failures, 500 for triplestore write failures. Empty result sets return `mirrored_count: 0` with a message (not an error).
- **Future agent inspection:** To check if mirroring is operational, call `GET /api/sparql/mirror/stats`. To verify the allowlist, call `GET /api/sparql/mirror/endpoints`. `logger.debug` calls in the service internals trace count/provenance queries.
