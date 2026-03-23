---
estimated_steps: 5
estimated_files: 3
skills_used:
  - best-practices
---

# T02: Build executor, router endpoints, and SHACL validation preview

**Slice:** S02 — RDF Data Import Wizard
**Milestone:** M039

## Description

Build the API layer that connects the parser to the triplestore. This includes: SHACL validation preview using pyshacl against installed model shapes, IRI collision detection via batch SPARQL query, an executor that builds `Operation` dataclasses directly from parsed triples and commits via EventStore with SSE progress broadcasting, and the FastAPI router with all endpoints for the 3-step wizard flow.

## Steps

1. **Build the executor** in `backend/app/rdf_import/executor.py`:
   - `async def validate_shacl(graph: Graph, triplestore_client: TriplestoreClient) -> dict[str, list[dict]]` — Load shapes via `model_shapes_loader(client)` from `app.services.models`. Run `pyshacl.validate(graph, shacl_graph=shapes, allow_warnings=True, allow_infos=True, advanced=True)` in `asyncio.to_thread()`. Parse results using `ValidationReport.from_pyshacl()` from `app.validation.report`. Group results by focus node IRI → list of `{severity, message, path}`. **Important:** `conforms=True` even with warnings when `allow_warnings=True` — must inspect results graph for `sh:ValidationResult` triples.
   - `async def check_collisions(iris: list[str], triplestore_client: TriplestoreClient) -> set[str]` — Build `SELECT ?s WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o } VALUES ?s { <iri1> ... } }` query, return set of existing IRIs.
   - `async def execute_import(parse_result: RdfParseResult, selected_iris: list[str], user: User, event_store: EventStore, triplestore_client: TriplestoreClient, broadcast: ScanBroadcast) -> RdfImportResult` — Filter subjects to selected_iris. For each subject, build `Operation(operation_type="rdf.import", affected_iris=[iri], description=f"Imported RDF subject {iri}", data_triples=list(triples), materialize_inserts=list(triples), materialize_deletes=[])`. If ≤10 subjects, commit individually via `event_store.commit()`. If >10, batch into chunks of 500 and use `event_store.commit_bulk()`. Broadcast SSE progress events (`import_progress` with `{phase, current, total, current_subject}`) throughout. Broadcast `import_complete` with stats on success, `import_error` on failure.

2. **Build the router** in `backend/app/rdf_import/router.py`:
   - `router = APIRouter(prefix="/browser/rdf-import", tags=["rdf-import"])`
   - Module-level `_parse_cache: dict[str, RdfParseResult] = {}` keyed by user ID for storing parse results between parse and execute steps.
   - Module-level `_broadcasts: dict[str, ScanBroadcast] = {}` keyed by user ID.
   - `GET /` — Render `rdf_import/import.html` template. Return full page if not htmx request, or just the import content for htmx partial swap.
   - `POST /parse` — Accept `content: str = Form(None)`, `file: UploadFile = None`, `format_override: str = Form(None)`. Read content from file or form field. Call `detect_format()` then `parse_rdf()`. If parse errors, render error template partial. Call `validate_shacl()` and `check_collisions()` on successful parse. Store result in `_parse_cache[user.id]`. Render `rdf_import/partials/preview.html` with subjects, SHACL results, collision info.
   - `POST /execute` — Accept `selected: list[str] = Form(...)` (selected subject IRIs). Retrieve cached parse result. Create `ScanBroadcast` instance, start import as `asyncio.create_task()`. Return `rdf_import/partials/progress.html`.
   - `GET /execute/stream` — Subscribe to user's broadcast, return `StreamingResponse` with `stream_sse()` using terminal events `{"import_complete", "import_error"}`.
   - `GET /summary` — Render `rdf_import/partials/summary.html` with import results.

3. **Import broadcast utilities** — Import `ScanBroadcast`, `SSEEvent`, `stream_sse` from `app.obsidian.broadcast`. Do NOT copy or duplicate these classes.

4. **Wire dependencies** — All endpoints use `user: User = Depends(get_current_user)`. Use `Depends(get_triplestore_client)` and `Depends(get_event_store)` following the existing dependency injection patterns in the codebase (check how obsidian/router.py gets its dependencies).

5. **Register router in main.py** — Add `from app.rdf_import.router import router as rdf_import_router` to imports in `backend/app/main.py`. Add `app.include_router(rdf_import_router)` after the `notion_router` line (line ~656).

## Must-Haves

- [ ] SHACL validation runs against installed model shapes and groups results by focus node
- [ ] IRI collision detection queries `urn:sempkm:current` graph
- [ ] Operations built directly from parsed triples — NOT through `handle_object_create()`
- [ ] Operations preserve original IRIs, datatypes, and language tags from rdflib Literals
- [ ] EventStore commit strategy: per-subject for ≤10, bulk for >10
- [ ] SSE progress events broadcast during import execution
- [ ] Router registered in `main.py` at prefix `/browser/rdf-import`
- [ ] All endpoints require authentication via `get_current_user`

## Verification

- `grep -n "rdf_import_router" backend/app/main.py` returns a match
- `cd backend && .venv/bin/python -c "from app.rdf_import.router import router; print(router.prefix)"` outputs `/browser/rdf-import`
- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` still passes (no regressions)

## Observability Impact

- Signals added: SSE events `import_progress`, `import_complete`, `import_error` via `ScanBroadcast`
- How a future agent inspects this: connect to `/browser/rdf-import/execute/stream` SSE endpoint during import; check `_parse_cache` and `_broadcasts` module-level dicts
- Failure state exposed: parse errors returned as user-visible messages; SHACL validation results per-subject; import errors in `RdfImportResult.errors` list

## Inputs

- `backend/app/rdf_import/__init__.py` — module init (from T01)
- `backend/app/rdf_import/parser.py` — `detect_format()`, `parse_rdf()`, `skolemize_bnodes()` (from T01)
- `backend/app/rdf_import/models.py` — `SubjectInfo`, `RdfParseResult`, `RdfImportResult` (from T01)
- `backend/app/events/store.py` — `EventStore`, `Operation` dataclass
- `backend/app/obsidian/broadcast.py` — `ScanBroadcast`, `SSEEvent`, `stream_sse()`
- `backend/app/validation/report.py` — `ValidationReport.from_pyshacl()`
- `backend/app/services/models.py` — `model_shapes_loader()`
- `backend/app/obsidian/router.py` — reference pattern for dependency injection and endpoint structure
- `backend/app/main.py` — router registration site

## Expected Output

- `backend/app/rdf_import/executor.py` — SHACL validation, collision detection, import execution with SSE
- `backend/app/rdf_import/router.py` — FastAPI router with all endpoints
- `backend/app/main.py` — modified to include `rdf_import_router`
