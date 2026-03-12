# Phase 37: Global Lint Data Model & API - Research

**Researched:** 2026-03-05
**Domain:** SHACL validation data model, RDF named graphs, FastAPI SSE, paginated REST API
**Confidence:** HIGH

## Summary

Phase 37 transforms the existing per-event SHACL validation system into a structured, queryable data layer. The current system stores raw pyshacl report graphs and lightweight summary triples, but individual validation results are not independently queryable -- the lint panel reads raw SHACL result triples from the report graph directly. This phase introduces per-run named graphs with structured result triples (using the `urn:sempkm:` namespace), a new `/api/lint/*` REST namespace with pagination and filtering, SSE push replacing 10s polling, and migration of the per-object lint panel to use the new data source.

The existing codebase provides strong foundations: `ValidationResult` dataclass already has all required fields (`focus_node`, `severity`, `path`, `message`, `source_shape`, `constraint_component`), `AsyncValidationQueue` has an `on_complete` callback hook ready for SSE broadcast, and the LLM proxy already demonstrates `StreamingResponse` SSE through nginx. FastAPI 0.135.1 (installed) has built-in SSE support via `fastapi.sse.EventSourceResponse`.

**Primary recommendation:** Extend `ValidationService._store_report()` to write structured result triples alongside the raw report graph, add a new `LintService` for query/pagination/diff logic, create a `/api/lint/*` FastAPI router, implement SSE broadcast via `asyncio.Queue` fan-out, and migrate the lint panel template from `hx-trigger="every 10s"` to `EventSource`-driven updates.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Triplestore-native storage -- all validation result data stays in RDF4J, consistent with the rest of SemPKM's architecture
- Per-run named graphs -- each validation run gets its own named graph for structured results (natural history boundary)
- Keep all runs -- full audit trail, never delete. Future "Tidy" admin panel will handle cleanup
- Store both raw and structured -- raw pyshacl report graph preserved for fidelity, structured result triples stored alongside for querying
- Layered API detail -- default response is human-readable; `?detail=full` query param adds raw SHACL metadata
- Inline label resolution -- API returns `object_label`, `object_type_label` resolved server-side alongside IRIs
- Offset-based pagination -- `?page=1&per_page=50`
- Minimum viable filters -- `?severity=Violation&object_type=<iri>` plus pagination
- Latest by default, optional `?run_id=<iri>` for historical run queries
- Basic diff endpoint -- `GET /api/lint/diff` returns `new_issues[]` and `resolved_issues[]`
- Dedicated `GET /api/lint/status` endpoint for lightweight polling
- Track source model explicitly per result
- On model uninstall: keep results, mark as orphaned
- Tag trigger source on each run -- 'user_edit', 'inference', 'manual', etc.
- New `/api/lint/*` namespace -- clean separation
- Endpoints: `/api/lint/results`, `/api/lint/status`, `/api/lint/diff`, `/api/lint/stream`
- Remove old `/api/validation/latest` and `/api/validation/{event_id}` endpoints entirely
- Migrate per-object lint panel to query new structured results (filtered by focus_node)
- Replace 10s polling with SSE push via single global SSE stream (`/api/lint/stream`)

### Claude's Discretion
- Structured result triple schema design (predicates, datatypes, naming)
- SPARQL query optimization for filtered result retrieval
- SSE implementation details (reconnection, heartbeat)
- How orphaned results are visually distinguished (Phase 38 UI concern, but data model should support it)
- Diff algorithm for comparing runs (matching strategy for "same" vs "new" vs "resolved" results)

### Deferred Ideas (OUT OF SCOPE)
- "Tidy" admin panel for triplestore cleanup options
- Search/sort filters on lint results -- Phase 38
- Per-model lint health breakdown view -- future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LINT-01 | User can open a Global Lint Status view that shows all SHACL validation results across every object, with summary counts by severity and per-object breakdown | Structured result triples enable SPARQL aggregation queries; `/api/lint/results` endpoint with pagination and filtering provides the data; `/api/lint/status` provides summary counts. Phase 37 builds the data layer and API; Phase 38 builds the UI |
| LINT-02 | Global lint view updates automatically after each EventStore.commit() via AsyncValidationQueue | SSE stream at `/api/lint/stream` broadcasts `validation_complete` events; `AsyncValidationQueue.on_complete` callback triggers broadcast; client-side EventSource replaces polling |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | REST API + SSE endpoints | Already installed; built-in `fastapi.sse.EventSourceResponse` since 0.135.0 |
| rdflib | 7.5.0+ | RDF triple generation for structured results | Already used throughout for SHACL report parsing |
| httpx | 0.28+ | Async triplestore client | Already used via `TriplestoreClient` |
| pyshacl | 0.31.0+ | SHACL validation engine | Already integrated in `ValidationService` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi.sse.EventSourceResponse` | built-in | SSE streaming response | `/api/lint/stream` endpoint |
| `fastapi.sse.ServerSentEvent` | built-in | Typed SSE event with `event`, `data`, `id` fields | Broadcasting validation_complete events |
| `asyncio.Queue` | stdlib | Per-client SSE message queue | Fan-out pattern for multi-client broadcast |
| `cachetools.TTLCache` | 7.0+ | Cache label lookups | Already used in `LabelService` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Built-in `fastapi.sse` | `sse-starlette` | Third-party dep; FastAPI 0.135+ has native support with keep-alive pings, no extra dep needed |
| `asyncio.Queue` fan-out | Redis pub/sub | Overkill for single-process app; Redis adds infrastructure complexity |
| Offset pagination | Cursor pagination | Cursor is better for large datasets but offset is simpler and matches user decision |

**Installation:**
```bash
# No new dependencies needed -- all libraries already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── lint/                     # NEW - lint data layer
│   ├── __init__.py
│   ├── models.py             # Pydantic response models + RDF schema constants
│   ├── service.py            # LintService: query, paginate, diff, store structured results
│   ├── router.py             # /api/lint/* endpoints
│   └── broadcast.py          # SSE broadcast manager (client registry + fan-out)
├── validation/               # EXISTING - modified
│   ├── report.py             # Extended: add to_structured_triples() method
│   ├── queue.py              # Modified: pass trigger_source, wire SSE broadcast
│   └── router.py             # REMOVED: replaced by lint/router.py
├── services/
│   └── validation.py         # Modified: store structured result triples alongside raw report
└── browser/
    └── router.py             # Modified: lint panel endpoint queries new structured data
```

### Pattern 1: Structured Result Triple Schema
**What:** Each validation result is stored as individual triples in a per-run named graph, queryable via SPARQL.
**When to use:** Every validation run stores results this way.

```python
# Namespace: urn:sempkm: (already defined in report.py)
# Named graph per run: urn:sempkm:lint-run:{uuid}

# Run metadata triples (in the run's named graph):
# <urn:sempkm:lint-run:{uuid}> a sempkm:LintRun ;
#     sempkm:timestamp "2026-03-05T12:00:00Z"^^xsd:dateTime ;
#     sempkm:conforms true/false ;
#     sempkm:triggerSource "user_edit" ;
#     sempkm:violationCount 3 ;
#     sempkm:warningCount 1 ;
#     sempkm:infoCount 0 .

# Per-result triples (in same named graph):
# <urn:sempkm:lint-result:{uuid}> a sempkm:LintResult ;
#     sempkm:inRun <urn:sempkm:lint-run:{uuid}> ;
#     sh:focusNode <https://example.org/obj/1> ;
#     sh:resultSeverity sh:Violation ;
#     sh:resultPath <http://purl.org/dc/terms/title> ;
#     sh:resultMessage "Value is required" ;
#     sh:sourceShape <urn:model:basic-pkm/NoteShape> ;
#     sh:sourceConstraintComponent sh:MinCountConstraintComponent ;
#     sempkm:sourceModel <urn:sempkm:model:basic-pkm> .
```

**Key design choices:**
- Reuse W3C SHACL predicates (`sh:focusNode`, `sh:resultSeverity`, etc.) where they exist
- Use `sempkm:` namespace only for SemPKM-specific predicates (`inRun`, `triggerSource`, `sourceModel`)
- Each result gets a unique IRI (`urn:sempkm:lint-result:{uuid}`) for individual addressability
- Run IRI (`urn:sempkm:lint-run:{uuid}`) groups results and carries metadata

### Pattern 2: Latest Run Pointer
**What:** A dedicated triple in `urn:sempkm:validations` points to the latest lint run, avoiding ORDER BY DESC queries.
**When to use:** Every time a new run completes.

```python
# In urn:sempkm:validations graph:
# <urn:sempkm:lint-latest> sempkm:latestRun <urn:sempkm:lint-run:{uuid}> .
#
# Update pattern: DELETE old pointer, INSERT new pointer
# DELETE { GRAPH <urn:sempkm:validations> { <urn:sempkm:lint-latest> sempkm:latestRun ?old } }
# WHERE  { GRAPH <urn:sempkm:validations> { <urn:sempkm:lint-latest> sempkm:latestRun ?old } };
# INSERT DATA { GRAPH <urn:sempkm:validations> {
#   <urn:sempkm:lint-latest> sempkm:latestRun <urn:sempkm:lint-run:{new-uuid}> .
#   <urn:sempkm:lint-latest> sempkm:previousRun <urn:sempkm:lint-run:{old-uuid}> .
# }}
```

### Pattern 3: SSE Broadcast Manager
**What:** In-memory pub/sub for SSE clients using asyncio.Queue per connection.
**When to use:** `/api/lint/stream` endpoint + validation completion callback.

```python
import asyncio
from collections.abc import AsyncIterable
from fastapi.sse import ServerSentEvent

class LintBroadcast:
    """Fan-out SSE broadcast to connected clients."""

    def __init__(self):
        self._clients: set[asyncio.Queue[ServerSentEvent]] = set()

    def subscribe(self) -> asyncio.Queue[ServerSentEvent]:
        q: asyncio.Queue[ServerSentEvent] = asyncio.Queue(maxsize=16)
        self._clients.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[ServerSentEvent]) -> None:
        self._clients.discard(q)

    async def publish(self, event: ServerSentEvent) -> None:
        dead: list[asyncio.Queue] = []
        for q in self._clients:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._clients.discard(q)

    @property
    def client_count(self) -> int:
        return len(self._clients)
```

### Pattern 4: Paginated API Response
**What:** Standard pagination envelope matching the user-decided format.
**When to use:** `/api/lint/results` endpoint.

```python
from pydantic import BaseModel

class LintResultItem(BaseModel):
    """Default (human-readable) lint result."""
    focus_node: str
    object_label: str
    object_type_label: str | None
    severity: str          # "Violation", "Warning", "Info"
    message: str
    path_label: str | None
    # Only included when ?detail=full
    source_shape: str | None = None
    constraint_component: str | None = None
    source_model: str | None = None

class LintResultsResponse(BaseModel):
    """Paginated lint results envelope."""
    results: list[LintResultItem]
    page: int
    per_page: int
    total: int
    total_pages: int
    run_id: str
    run_timestamp: str
    conforms: bool
```

### Pattern 5: Diff Algorithm
**What:** Compare two runs to find new and resolved issues.
**When to use:** `GET /api/lint/diff` endpoint.

```python
# Matching strategy: a result is "the same" if it has the same
# (focus_node, severity, source_shape, constraint_component, path) tuple.
# This is a fingerprint -- message text can change between runs without
# making it a "new" issue.
#
# Algorithm:
# 1. Query results from latest run -> set of fingerprints
# 2. Query results from previous run -> set of fingerprints
# 3. new_issues = latest - previous
# 4. resolved_issues = previous - latest
```

### Anti-Patterns to Avoid
- **Storing results in SQLite:** The user locked "triplestore-native" -- all result data stays in RDF4J for consistency with the rest of SemPKM.
- **Polling from the lint panel:** Replace `hx-trigger="every 10s"` with SSE-driven updates. Do not add a second polling mechanism.
- **Querying raw pyshacl report graphs for listing:** The raw graphs lack source_model, trigger_source, and are shaped for pyshacl fidelity, not querying. Always query the structured result triples.
- **Using the old `/api/validation/*` endpoints alongside new ones:** Remove them completely per user decision. No dual-path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE protocol formatting | Manual `data:` string construction | `fastapi.sse.EventSourceResponse` + `ServerSentEvent` | Built-in keep-alive pings (15s), proper `Cache-Control`/`X-Accel-Buffering` headers, W3C spec compliance |
| Label resolution | Custom SPARQL per result | `LabelService.resolve_batch()` | Already handles caching, precedence chain, batch queries via VALUES |
| RDF term serialization | Manual string formatting | `_rdf_term_to_sparql()` from `services/validation.py` | Already handles URI escaping, literal datatypes, language tags |
| Pagination math | Manual offset/limit calculation | Simple `(page - 1) * per_page` + SPARQL `OFFSET/LIMIT` | Straightforward, but easy to get off-by-one errors on total_pages |
| UUID generation | Custom IRI generation | `uuid.uuid4()` with `urn:sempkm:lint-run:` / `urn:sempkm:lint-result:` prefix | Follows existing `urn:sempkm:event:` and `urn:sempkm:validation:` patterns |

## Common Pitfalls

### Pitfall 1: SPARQL Injection in Filter Parameters
**What goes wrong:** User-supplied `object_type` IRI or `severity` string injected directly into SPARQL query strings.
**Why it happens:** The existing codebase uses f-string SPARQL construction (e.g., `f"<{decoded_iri}>"` in the lint endpoint).
**How to avoid:** Validate severity against allowlist (`"Violation"`, `"Warning"`, `"Info"`). Validate object_type as a valid IRI (starts with `http://` or `urn:`). Use parameterized SPARQL VALUES clauses where possible.
**Warning signs:** Any user-supplied value appearing inside `<{...}>` in a SPARQL string.

### Pitfall 2: SSE Through nginx Buffering
**What goes wrong:** nginx buffers the SSE response, client sees no events until connection closes.
**Why it happens:** The default nginx `location /` block has `proxy_buffering on`.
**How to avoid:** Add a dedicated nginx location block for `/api/lint/stream` with `proxy_buffering off`, similar to the existing `/browser/llm/chat/stream` block. FastAPI's built-in `EventSourceResponse` already sets `X-Accel-Buffering: no` header, but an explicit nginx block is more reliable.
**Warning signs:** SSE works in dev (no nginx) but not in Docker.

### Pitfall 3: Stale Latest Run Pointer After Failed Validation
**What goes wrong:** Validation fails mid-run, latest pointer is never updated, clients see stale data.
**Why it happens:** `_store_report()` updates the pointer after storing results -- if an earlier step fails, the pointer is never written.
**How to avoid:** Only update the latest run pointer after all result triples are successfully committed. The existing `AsyncValidationQueue._worker()` already catches exceptions and continues, so a failed run simply keeps the previous pointer.
**Warning signs:** `/api/lint/status` returns old timestamp after a known edit.

### Pitfall 4: Large Result Sets Blocking SSE Broadcast
**What goes wrong:** Hundreds of validation results serialized and pushed via SSE as a single event -- large payload, slow.
**Why it happens:** Trying to send all results in the SSE event.
**How to avoid:** SSE `validation_complete` event should contain only the run summary (counts, timestamp, conforms, run_id). Clients then fetch full results from `/api/lint/results` as needed. The lint panel uses the SSE event as a signal to re-fetch its filtered view.
**Warning signs:** SSE event payload > 1KB.

### Pitfall 5: Race Between Run Storage and SSE Broadcast
**What goes wrong:** SSE event fires before results are committed to triplestore. Client fetches results, gets stale data.
**Why it happens:** Broadcast fires in `on_complete` callback, but SPARQL INSERT may not be fully committed.
**How to avoid:** Ensure `_store_report()` completes (all SPARQL updates return) before the `on_complete` callback fires. The current code already does this -- `_store_report()` is awaited before the callback in `_worker()`.
**Warning signs:** Intermittent stale results on first fetch after SSE event.

### Pitfall 6: Lint Panel Migration Breaking E2E Tests
**What goes wrong:** Existing e2e tests (`e2e/tests/04-validation/lint-panel.spec.ts`) expect `hx-trigger="every 10s"` attribute and specific HTML structure.
**Why it happens:** Tests assert on polling behavior that is being replaced by SSE.
**How to avoid:** Update lint panel template and tests in the same task. The test checking `hx-trigger` containing `"every 10s"` must be changed to verify SSE-driven behavior instead.
**Warning signs:** `lint-panel.spec.ts` test 4 (`lint panel auto-refreshes`) fails after migration.

### Pitfall 7: Orphaned Source Model Reference
**What goes wrong:** Results reference a `sempkm:sourceModel` IRI that no longer exists after model uninstall.
**Why it happens:** User decided "on model uninstall: keep results, mark as orphaned."
**How to avoid:** Add a `sempkm:orphaned` boolean predicate (default false) on each result. When a model is uninstalled, run a SPARQL UPDATE to set orphaned=true on all results referencing that model's shapes. The diff and listing endpoints should include this flag so Phase 38 UI can visually distinguish orphaned results.
**Warning signs:** Results with source_shape IRIs that resolve to nothing.

## Code Examples

### Storing Structured Result Triples (extend ValidationReport)

```python
# Source: extension of existing backend/app/validation/report.py
import uuid

def to_structured_triples(self, run_iri: str, source_model_map: dict[str, str] | None = None) -> list[tuple]:
    """Generate structured result triples for queryable storage.

    Each ValidationResult becomes an individual resource with its own IRI,
    linked to the run via sempkm:inRun.
    """
    triples = []
    run = URIRef(run_iri)

    for result in self.results:
        result_iri = URIRef(f"urn:sempkm:lint-result:{uuid.uuid4()}")
        triples.extend([
            (result_iri, RDF.type, SEMPKM.LintResult),
            (result_iri, SEMPKM.inRun, run),
            (result_iri, SH.focusNode, URIRef(result.focus_node)),
            (result_iri, SH.resultSeverity, _severity_uri(result.severity)),
            (result_iri, SH.resultMessage, Literal(result.message)),
        ])
        if result.path:
            triples.append((result_iri, SH.resultPath, URIRef(result.path)))
        if result.source_shape:
            triples.append((result_iri, SH.sourceShape, URIRef(result.source_shape)))
        if result.constraint_component:
            triples.append((result_iri, SH.sourceConstraintComponent, URIRef(result.constraint_component)))
        # Source model lookup
        if source_model_map and result.source_shape:
            model_iri = source_model_map.get(result.source_shape)
            if model_iri:
                triples.append((result_iri, SEMPKM.sourceModel, URIRef(model_iri)))

    return triples
```

### SSE Stream Endpoint

```python
# Source: FastAPI 0.135+ built-in SSE (verified via official docs)
from collections.abc import AsyncIterable
from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

router = APIRouter(prefix="/api/lint")

@router.get("/stream", response_class=EventSourceResponse)
async def lint_stream(
    user: User = Depends(get_current_user),
    broadcast: LintBroadcast = Depends(get_lint_broadcast),
) -> AsyncIterable[ServerSentEvent]:
    queue = broadcast.subscribe()
    try:
        while True:
            event = await queue.get()
            yield event
    finally:
        broadcast.unsubscribe(queue)
```

### SPARQL Query for Paginated Filtered Results

```sparql
# Query structured results from latest run with severity filter
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX sempkm: <urn:sempkm:>

SELECT ?result ?focusNode ?severity ?path ?message ?sourceShape ?component ?sourceModel
WHERE {
  GRAPH ?runGraph {
    ?result a sempkm:LintResult ;
            sempkm:inRun ?run ;
            sh:focusNode ?focusNode ;
            sh:resultSeverity ?severity ;
            sh:resultMessage ?message .
    OPTIONAL { ?result sh:resultPath ?path }
    OPTIONAL { ?result sh:sourceShape ?sourceShape }
    OPTIONAL { ?result sh:sourceConstraintComponent ?component }
    OPTIONAL { ?result sempkm:sourceModel ?sourceModel }
    # Severity filter (injected only when filter param present)
    # FILTER(?severity = sh:Violation)
  }
  # Bind to latest run
  GRAPH <urn:sempkm:validations> {
    <urn:sempkm:lint-latest> sempkm:latestRun ?run .
  }
  # The run graph IRI equals the run IRI (convention)
  BIND(?run AS ?runGraph)
}
ORDER BY ?focusNode ?severity
OFFSET 0 LIMIT 50
```

### Nginx SSE Location Block

```nginx
# Add to frontend/nginx.conf (before catch-all location /)
location /api/lint/stream {
    proxy_pass http://api:8000/api/lint/stream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;
    proxy_pass_header Set-Cookie;

    # SSE-specific
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    proxy_set_header Cache-Control "no-cache";
    proxy_set_header Connection "keep-alive";
    add_header X-Accel-Buffering "no";
}
```

### Lint Panel SSE Client (htmx + EventSource)

```javascript
// Replace hx-trigger="every 10s" with SSE-driven refresh
// In lint_panel.html or a small JS helper
(function() {
  const es = new EventSource('/api/lint/stream');
  es.addEventListener('validation_complete', (e) => {
    const data = JSON.parse(e.data);
    // Re-fetch lint panel for current object via htmx
    const panel = document.querySelector('[data-testid="lint-panel"]');
    if (panel) {
      const objectIri = panel.dataset.objectIri;
      htmx.ajax('GET', `/browser/lint/${encodeURIComponent(objectIri)}`, {
        target: panel,
        swap: 'outerHTML'
      });
    }
  });
  es.onerror = () => {
    // EventSource auto-reconnects; no action needed
  };
})();
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sse-starlette` third-party lib | `fastapi.sse.EventSourceResponse` built-in | FastAPI 0.135.0 (Dec 2024) | No extra dependency; built-in keep-alive pings, proper headers |
| Manual `data:` string construction | `ServerSentEvent` dataclass with `event`, `data`, `id`, `retry` | FastAPI 0.135.0 | Type-safe, auto-serializes Pydantic models |
| `hx-sse` extension | Native `EventSource` + `htmx.ajax()` | Current | htmx SSE extension adds complexity; plain EventSource + manual htmx trigger is simpler and more reliable |

## Open Questions

1. **Source model mapping: shape IRI to model IRI**
   - What we know: Each SHACL shape has a `sourceShape` IRI from pyshacl. Mental Models are loaded via `ModelService` and shapes come from model files.
   - What's unclear: Is there an existing mapping from shape IRI to model IRI? Or do we need to build one?
   - Recommendation: Check `ModelService` or `ShapesService` for shape-to-model mapping at query time. If not available, build a simple lookup during shapes loading that maps shape IRIs to their source model.

2. **Run named graph IRI convention**
   - What we know: Current report graphs use `urn:sempkm:validation:{uuid}` (derived from event UUID).
   - What's unclear: Should new lint run graphs use a different prefix to distinguish from old raw report graphs?
   - Recommendation: Use `urn:sempkm:lint-run:{uuid}` to clearly separate from legacy `urn:sempkm:validation:*` graphs. The old graphs can be left in place (no cleanup needed -- "keep all runs" decision).

3. **Trigger source propagation**
   - What we know: `AsyncValidationQueue.enqueue()` currently takes `event_iri` and `timestamp`.
   - What's unclear: How to propagate trigger source ("user_edit", "inference", "manual") from the call site to the stored run.
   - Recommendation: Add `trigger_source: str = "user_edit"` parameter to `enqueue()`. Inference engine passes `"inference"`, manual trigger passes `"manual"`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright + pytest (e2e), pytest (unit) |
| Config file | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| Quick run command | `cd e2e && npx playwright test tests/04-validation/ --project=chromium` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LINT-01 | Structured results queryable via `/api/lint/results` with pagination + filtering | integration | `cd e2e && npx playwright test tests/04-validation/ --project=chromium` | Partial -- `lint-panel.spec.ts` exists but tests old endpoints |
| LINT-02 | SSE push on validation complete, lint panel updates without polling | integration | `cd e2e && npx playwright test tests/04-validation/ --project=chromium` | No -- needs new SSE test |

### Sampling Rate
- **Per task commit:** `cd e2e && npx playwright test tests/04-validation/ --project=chromium`
- **Per wave merge:** `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update `e2e/tests/04-validation/lint-panel.spec.ts` -- adapt tests for new `/api/lint/*` endpoints and SSE behavior
- [ ] Add API integration test for `/api/lint/results` pagination and filtering
- [ ] Add API integration test for `/api/lint/status` endpoint
- [ ] Add API integration test for `/api/lint/diff` endpoint

## Sources

### Primary (HIGH confidence)
- FastAPI 0.135.1 installed in Docker container -- verified via `pip show fastapi`
- [FastAPI SSE official docs](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- verified `EventSourceResponse`, `ServerSentEvent` API, keep-alive pings, `X-Accel-Buffering` header
- Existing codebase: `backend/app/validation/report.py`, `backend/app/services/validation.py`, `backend/app/validation/queue.py`, `backend/app/validation/router.py`, `backend/app/browser/router.py` (lint endpoint at line 971)
- Existing SSE pattern: `backend/app/browser/router.py` lines 310-370 (LLM streaming proxy)
- Existing nginx SSE config: `frontend/nginx.conf` lines 51-71

### Secondary (MEDIUM confidence)
- [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- feature added in FastAPI 0.135.0

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and in use; FastAPI SSE verified against official docs
- Architecture: HIGH - patterns directly extend existing codebase (ValidationReport, AsyncValidationQueue, named graphs)
- Pitfalls: HIGH - identified from direct code inspection (nginx buffering, SPARQL injection, e2e test breakage)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, no fast-moving dependencies)