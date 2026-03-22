---
estimated_steps: 5
estimated_files: 7
skills_used: []
---

# T03: Mirror service and "Mirror Results" SPARQL console action

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

The mirror service stores federated query results in `urn:sempkm:mirrored` as RDF triples with provenance metadata. The "Mirror Results" button in the SPARQL console triggers it.

**How mirroring works:** When a user runs a federated query and clicks "Mirror Results", the SPARQL JSON result bindings are converted to RDF triples and inserted into the `urn:sempkm:mirrored` named graph. Provenance metadata (source endpoint, timestamp, query hash) is stored as a `urn:sempkm:mirror:{uuid}` resource using W3C PROV-O vocabulary (`prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:generatedAtTime`).

**Pattern followed:** The inferred graph pattern — separate named graph, queried alongside current data via FROM clauses, tagged with source metadata. The `insert_graph()` method on TriplestoreClient (Turtle via Graph Store protocol) is the storage mechanism, avoiding SPARQL INSERT DATA parsing issues (Knowledge Pattern 3).

## Steps

1. **Create `backend/app/federation/mirror_service.py`:** Define `MirrorService` class taking `TriplestoreClient`. Method `mirror_results(bindings: list[dict], source_endpoint: str, query_text: str) -> dict`: (a) Generate a mirror batch ID (`urn:sempkm:mirror:{uuid}`). (b) Convert bindings to RDF triples — for each binding row, extract URI→URI and URI→Literal relationships, building an rdflib Graph. Skip rows that don't produce valid triples (e.g., all literals). (c) Add provenance triples to the graph: mirror batch `prov:wasAttributedTo` source endpoint, `prov:generatedAtTime` timestamp, `dcterms:source` endpoint URL, store query hash for dedup tracking. (d) Serialize graph to Turtle and call `client.insert_graph(turtle, "urn:sempkm:mirrored")`. (e) Return `{batch_id, triple_count, source_endpoint, timestamp}`. Method `get_mirror_batches() -> list[dict]`: query provenance metadata from mirrored graph. Method `delete_mirror_batch(batch_id: str)`: remove all triples associated with a batch (using the batch IRI as subject in a DELETE WHERE).

2. **Create `backend/app/federation/mirror_router.py`:** API router with prefix `/api/sparql`. Route `POST /mirror` accepting JSON `{bindings: list, source_endpoint: str, query_text: str}`. Requires authenticated user. Calls MirrorService. Returns `{batch_id, triple_count, source_endpoint}`. Route `GET /mirror/batches` returns list of mirror batches with provenance. Route `DELETE /mirror/batches/{batch_id}` removes a batch (owner-only).

3. **Register router in main.py:** Import `mirror_router` and include it in the app. Add dependency provider for MirrorService (needs TriplestoreClient).

4. **Add "Mirror Results" button to SPARQL console:** In `sparql_panel.html`, add a toolbar button after the Saved dropdown: `<button class="sparql-toolbar-btn" id="sparql-mirror-btn" title="Mirror Results to Local Graph" disabled>` with a `database` Lucide icon and "Mirror" label. Disabled by default — enabled only after a successful query execution that contains SERVICE results.

5. **Wire button in sparql-console.js:** After successful query execution, detect if the query contained a SERVICE clause (simple string check on the editor content). If so, enable the mirror button. On click: POST to `/api/sparql/mirror` with `{bindings: currentResults.results.bindings, source_endpoint: extractedServiceEndpoint, query_text: editorContent}`. Show a toast on success ("Mirrored N triples from endpoint") or error. Disable button after successful mirror to prevent double-mirroring. Add CSS for the mirror button states (enabled, disabled, loading).

## Must-Haves

- [ ] MirrorService converts SPARQL JSON bindings to RDF triples in rdflib Graph
- [ ] Triples stored in `urn:sempkm:mirrored` via `insert_graph()` (Graph Store protocol)
- [ ] Provenance metadata stored with PROV-O vocabulary (source endpoint, timestamp, query hash)
- [ ] POST `/api/sparql/mirror` endpoint works and returns batch metadata
- [ ] "Mirror Results" button appears in SPARQL console toolbar
- [ ] Button enabled only after SERVICE query execution, disabled after mirroring
- [ ] Success/error toast feedback to user
- [ ] Unit tests for MirrorService binding conversion and provenance

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — all pass
- Mirror button visible in SPARQL console toolbar (visually verify in browser or check template)

## Observability Impact

- Signals added: Structured logging in MirrorService — logs mirror operations with endpoint, triple count, batch ID
- How a future agent inspects this: `GET /api/sparql/mirror/batches` returns all mirror batches with metadata; SPARQL query against `GRAPH <urn:sempkm:mirrored>` with all_graphs shows stored triples
- Failure state exposed: MirrorService returns error dict `{error, endpoint, timestamp}` on failure; API returns 502 with error detail

## Inputs

- `backend/app/triplestore/client.py` — TriplestoreClient.insert_graph() for Turtle storage
- `backend/app/rdf/namespaces.py` — MIRRORED_GRAPH_IRI, PROV namespace (from T01)
- `backend/app/sparql/client.py` — scope_to_current_graph() now includes mirrored graph (from T01)
- `frontend/static/js/sparql-console.js` — existing console module with toolbar, query execution, result handling
- `backend/app/templates/browser/sparql_panel.html` — existing toolbar HTML

## Expected Output

- `backend/app/federation/mirror_service.py` — MirrorService class with mirror_results(), get_mirror_batches(), delete_mirror_batch()
- `backend/app/federation/mirror_router.py` — API router with POST /mirror, GET /mirror/batches, DELETE /mirror/batches/{batch_id}
- `backend/app/main.py` — mirror_router registered
- `frontend/static/js/sparql-console.js` — mirror button wiring, SERVICE detection, toast feedback
- `backend/app/templates/browser/sparql_panel.html` — mirror button added to toolbar
- `frontend/static/css/workspace.css` — mirror button styles
- `backend/tests/test_mirror_service.py` — unit tests for MirrorService
