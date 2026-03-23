# S02 Research: RDF Data Import Wizard

## Summary

This slice builds a full RDF data import pipeline: paste/upload → parse → preview with SHACL validation → selective import as event-sourced objects. The work follows established patterns from the Obsidian and Notion importers but is structurally simpler — no type mapping, no property mapping, no scanner step. RDF data already has types, predicates, and values declared.

The key technical risks are format detection from pasted text (rdflib can't auto-detect JSON-LD), blank node skolemization consistency, and building Operations directly from parsed triples rather than going through `handle_object_create()`.

## Recommendation

Decompose into 4 tasks:

1. **Backend parser + models** — format detection heuristic, rdflib parsing, subject extraction, blank node skolemization, data models. This is the novel code.
2. **Backend executor + router** — EventStore integration with direct Operation construction, IRI collision detection, SHACL preview endpoint, SSE progress, router endpoints.
3. **Templates + CSS** — import wizard UI (3-step: Input → Preview → Import), step bar, paste area, file upload, preview table, progress/summary partials. Reuses `import.css` patterns.
4. **Workspace integration + verification** — sidebar entry, command palette entry, dockview tab function, main.py router registration, end-to-end verification.

## Implementation Landscape

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/rdf_import/__init__.py` | Module init |
| `backend/app/rdf_import/parser.py` | Format detection, rdflib parsing, subject extraction, blank node skolemization |
| `backend/app/rdf_import/executor.py` | EventStore Operation construction, IRI collision check, two-pass import, SSE progress |
| `backend/app/rdf_import/models.py` | Dataclasses: `RdfParseResult`, `SubjectInfo`, `RdfImportResult` |
| `backend/app/rdf_import/router.py` | FastAPI router, prefix `/browser/import/rdf`, endpoints for page/parse/preview/execute/stream/summary |
| `backend/app/templates/rdf_import/import.html` | Base import page (extends `base.html`) |
| `backend/app/templates/rdf_import/partials/step_bar.html` | 3-step wizard bar (Input → Preview → Import) |
| `backend/app/templates/rdf_import/partials/input_form.html` | Paste textarea + file upload + format override dropdown |
| `backend/app/templates/rdf_import/partials/preview.html` | Subject preview table with SHACL status, checkboxes for selective import |
| `backend/app/templates/rdf_import/partials/import_progress.html` | SSE-driven progress bar + log |
| `backend/app/templates/rdf_import/partials/import_summary.html` | Post-import stat cards + actions |
| `backend/tests/test_rdf_import_parser.py` | Unit tests for parser: format detection, parsing all 3 formats, subject extraction, blank node skolemization |

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/main.py` | Add `from app.rdf_import.router import router as rdf_import_router` + `app.include_router(rdf_import_router)` |
| `backend/app/templates/components/_sidebar.html` | Add "Import RDF" entry after the Notion import link (line ~117) |
| `frontend/static/js/workspace.js` | Add `openRdfImportTab()` function (follows `openImportTab()` pattern at line ~962) + command palette entry (after line ~1508) |

### Files to Reuse (Read-Only Reference)

| File | What to Reuse |
|------|---------------|
| `backend/app/obsidian/broadcast.py` | `ScanBroadcast` + `SSEEvent` + `stream_sse()` — import directly, don't copy |
| `backend/app/obsidian/executor.py` | Two-pass pattern reference (Pass 1: objects, Pass 2: edges via EventStore) |
| `backend/app/events/store.py` | `Operation` dataclass, `EventStore.commit()` / `commit_bulk()` API |
| `backend/app/validation/report.py` | `ValidationReport.from_pyshacl()` for parsing SHACL results |
| `backend/app/services/models.py` | `model_shapes_loader()` for loading installed SHACL shapes |
| `frontend/static/css/import.css` | Shared import styling (`.import-upload-wrapper`, `.import-section`, `.import-stat-cards`, etc.) |
| `backend/app/templates/obsidian/partials/import_progress.html` | SSE progress pattern with EventSource |
| `backend/app/templates/obsidian/partials/import_summary.html` | Post-import stat cards + actions |

## Key Technical Details

### 1. Format Detection Heuristic

rdflib cannot auto-detect JSON-LD from string content (verified — `Graph.parse(data=jsonld_string)` raises "Could not guess RDF format"). N-Triples auto-detect works because N-Triples is valid Turtle syntax. Detection strategy:

**For file uploads:** Use `rdflib.util.guess_format(filename)` — works correctly for `.jsonld`, `.json`, `.ttl`, `.nt` extensions.

**For pasted text:** Content-based heuristic:
```python
text = content.strip()
if text.startswith('{') or text.startswith('['):
    return 'json-ld'
elif text.startswith('@prefix') or text.startswith('@base'):
    return 'turtle'
elif text.startswith('<') and re.search(r'\.\s*$', text.split('\n')[0]):
    return 'nt'
else:
    return 'turtle'  # fallback — turtle parser is most forgiving
```

Always provide a manual format override `<select>` in the UI. The heuristic sets the default; user can change it.

### 2. Subject Extraction + Grouping

Group parsed triples by subject. For each subject, extract:
- **IRI** (or blank node ID before skolemization)
- **rdf:type** values (may have multiple)
- **Label** (resolve via label precedence: `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name`)
- **Property count** (number of distinct predicates)
- **Is blank node** (bool — affects IRI display in preview)

"Top-level subject" heuristic: subjects that appear in subject position but NOT in object position of any triple (excluding `rdf:type` targets and vocabulary IRIs). This separates actual objects from nested structural nodes (e.g., `schema:PostalAddress` used as object of `schema:address`). Fallback: if heuristic yields zero top-level subjects, show all subjects.

### 3. Blank Node Skolemization

Pattern: build a `BNode → URIRef` mapping, then reconstruct the graph.

```python
import uuid
from rdflib import BNode, URIRef, Graph

def skolemize_bnodes(graph: Graph) -> tuple[Graph, dict[BNode, URIRef]]:
    mapping: dict[BNode, URIRef] = {}
    new_graph = Graph()
    for ns_prefix, ns_uri in graph.namespaces():
        new_graph.bind(ns_prefix, ns_uri)
    
    def resolve(term):
        if isinstance(term, BNode):
            if term not in mapping:
                mapping[term] = URIRef(f"urn:sempkm:import:{uuid.uuid4()}")
            return mapping[term]
        return term
    
    for s, p, o in graph:
        new_graph.add((resolve(s), p, resolve(o)))
    
    return new_graph, mapping
```

Critical: the mapping must be applied to both subject AND object positions to maintain internal consistency. A blank node referenced by subject `_:addr` and as object of `schema:address _:addr` must map to the same URI.

### 4. Direct Operation Construction (NOT handle_object_create)

The existing `handle_object_create()` mints new IRIs via `mint_object_iri()` and expects `ObjectCreateParams(type, slug, properties)`. Imported RDF already has IRIs, predicates, and typed literals — routing through `handle_object_create()` would:
- Discard the original IRI (reminting)
- Require decomposing triples into a properties dict then recomposing
- Lose datatype information from typed literals

Instead, build `Operation` dataclasses directly:

```python
from app.events.store import Operation

def build_import_operation(subject_iri: str, triples: list[tuple]) -> Operation:
    return Operation(
        operation_type="rdf.import",
        affected_iris=[subject_iri],
        description=f"Imported RDF subject {subject_iri}",
        data_triples=list(triples),
        materialize_inserts=list(triples),
        materialize_deletes=[],
    )
```

This preserves original IRIs, datatypes, and language tags exactly as parsed. `materialize_inserts` = `data_triples` because we're adding everything to `urn:sempkm:current`. No deletes for new objects.

### 5. SHACL Validation Preview

Run pyshacl against the parsed (skolemized) data graph using installed model shapes. No triplestore needed for preview.

```python
shapes_graph = await model_shapes_loader(triplestore_client)
conforms, results_graph, _ = await asyncio.to_thread(
    pyshacl.validate,
    parsed_graph,
    shacl_graph=shapes_graph,
    allow_warnings=True,
    allow_infos=True,
    advanced=True,
)
```

Parse results using `ValidationReport.from_pyshacl()` pattern — extract focus nodes, severity, messages. Group by focus node to show per-subject SHACL status in the preview table.

**Important:** With `allow_warnings=True`, `conforms` returns True even when warnings exist (see KNOWLEDGE.md pattern). Must inspect the results graph for `sh:ValidationResult` triples to detect warnings.

**Performance consideration:** For large files (>5000 triples), SHACL validation could take several seconds. Run in `asyncio.to_thread()`. Consider skipping SHACL preview for very large imports and showing a "too large for preview validation" message instead.

### 6. IRI Collision Detection

Batch ASK query against `urn:sempkm:current`:

```sparql
SELECT ?s WHERE {
    GRAPH <urn:sempkm:current> { ?s ?p ?o }
    VALUES ?s { <iri1> <iri2> ... }
}
```

Returns set of IRIs that already exist. Show warning in preview, default to skip. Only check non-blank-node subjects (skolemized blank nodes are guaranteed unique).

### 7. EventStore Integration

Use `EventStore.commit()` for small imports (≤10 subjects) — gives per-subject provenance events. Use `EventStore.commit_bulk()` for larger imports — creates one summary event with counts.

Decision boundary: `len(subjects) <= 10 → commit()` per subject, else `commit_bulk()` in chunks of 500 operations.

The import function itself should run as `asyncio.create_task()` (same pattern as Obsidian executor) with SSE progress broadcasting.

### 8. SSE Progress Broadcasting

Import `ScanBroadcast`, `SSEEvent`, `stream_sse` directly from `app.obsidian.broadcast` — no need to duplicate. The broadcast pattern is generic despite being in the obsidian module.

Progress events:
- `import_progress` with `{phase: "parsing"|"validating"|"importing", current, total, current_subject}`
- `import_complete` with `{created, skipped, errors, duration_seconds}`
- `import_error` with `{message}`

### 9. Router Endpoints

| Method | Path | Returns | Purpose |
|--------|------|---------|---------|
| GET | `/browser/import/rdf` | HTML page | Main import page (full page or htmx partial) |
| POST | `/browser/import/rdf/parse` | HTML partial | Parse pasted/uploaded RDF, return preview table |
| POST | `/browser/import/rdf/execute` | HTML partial | Trigger import, return progress UI |
| GET | `/browser/import/rdf/execute/stream` | SSE stream | Import progress events |
| GET | `/browser/import/rdf/summary` | HTML partial | Post-import summary with stats |

The parse endpoint accepts:
- `content`: pasted text (form field)
- `file`: uploaded file (UploadFile)
- `format_override`: optional format hint (`json-ld`, `turtle`, `nt`)

Parse result is stored in server-side session state (similar to obsidian's `scan_result.json` but kept in memory or a temp dict keyed by import_id since RDF parse is fast and doesn't need disk persistence).

### 10. Workspace Integration

**Sidebar** (`_sidebar.html`, after line 117):
```html
<a href="/browser/import/rdf" class="nav-link" data-tooltip="Import RDF"
   hx-boost="false">
    <i data-lucide="file-code-2" class="nav-icon"></i>
    <span class="nav-label">Import RDF</span>
</a>
```

**Command palette** (`workspace.js`, after the import-notion entry):
```javascript
{
  id: 'import-rdf',
  title: 'Import > RDF Data',
  section: 'Navigation',
  handler: function () {
    openRdfImportTab();
  }
}
```

**Dockview tab** (`workspace.js`, near `openImportTab()`):
```javascript
function openRdfImportTab() {
    var tabKey = 'special:import/rdf';
    var dv = window._dockview;
    if (!dv) return;
    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }
    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'Import RDF', dirty: false };
    dv.api.addPanel({
        id: tabKey,
        component: 'special-panel',
        params: { specialType: 'import/rdf', isView: false, isSpecial: true },
        title: 'Import RDF'
    });
}
window.openRdfImportTab = openRdfImportTab;
```

The `special-panel` component in `workspace-layout.js` already maps `specialType` to URL via `'/browser/' + st`, so `specialType: 'import/rdf'` → URL `/browser/import/rdf` — no changes needed to `workspace-layout.js`.

### 11. Template Structure

The RDF import wizard is 3 steps (vs. Obsidian's 7):
1. **Input** — Paste textarea + file upload + format override dropdown
2. **Preview** — Subject table with type, label, property count, SHACL status, select checkboxes
3. **Import** — Progress bar + summary

The step bar uses the same `.import-step-bar` CSS classes from `import.css`. The import page extends `base.html` with `<link rel="stylesheet" href="/css/import.css">`.

### 12. Auth Pattern

The router prefix `/browser/import/rdf` falls under the `/browser/` path which `_is_html_route()` treats as an HTML route. Auth middleware returns 302 to `/login.html` for unauthenticated requests. All endpoints use `user: User = Depends(get_current_user)`. No changes needed to `_is_html_route()`.

## Pitfalls & Constraints

### P1: JSON-LD auto-detect fails
rdflib raises `"Could not guess RDF format ... tried Turtle but failed"` when parsing JSON-LD from string without explicit `format='json-ld'`. The format detection heuristic MUST handle this before calling `Graph.parse()`.

### P2: BNode mapping must be consistent across subject and object positions
If `_:addr` appears as subject of `(_, schema:streetAddress, "123 Main")` AND as object of `(ex:alice, schema:address, _:addr)`, both must map to the same `urn:sempkm:import:{uuid}`. The skolemization function must build the mapping in a single pass over the graph.

### P3: Typed literals must be preserved
`Graph.parse()` preserves XSD datatypes on literals. When building `Operation.data_triples`, the `(s, p, o)` tuples contain rdflib `Literal` objects with datatype info. The `_serialize_rdf_term()` function in `events/store.py` already handles `Literal` serialization including datatypes. Verified — no special handling needed.

### P4: Lucide icons in flex containers
Per CLAUDE.md rules: any Lucide SVG in a flex container needs `flex-shrink: 0` via CSS. The import templates reuse `.import-section-title svg` which already has this. New button icons should use existing CSS classes.

### P5: nginx serves /js/ and /css/ NOT /static/
Per KNOWLEDGE.md: template `<link>` and `<script>` tags must use `/css/import.css` not `/static/css/import.css`.

### P6: commit_bulk doesn't support target_graph parameter
`EventStore.commit_bulk()` always materializes to `CURRENT_GRAPH_IRI`. This is fine for RDF import — imported data goes to `urn:sempkm:current`.

### P7: ScanBroadcast lives in obsidian module
Import from `app.obsidian.broadcast` — it's generic despite the module name. Alternatively, could move to a shared module, but that's outside this slice's scope.

## Verification Strategy

### Unit Tests (`test_rdf_import_parser.py`)
- Format detection: JSON-LD heuristic (starts with `{`), Turtle (`@prefix`), N-Triples (`<` with trailing `.`)
- Parse all 3 formats: valid JSON-LD, Turtle, N-Triples
- Parse error handling: malformed JSON-LD, invalid Turtle
- Subject extraction: correct IRI, type, label, property count
- Top-level subject heuristic: nested blank nodes excluded from top-level
- Blank node skolemization: consistent mapping, `urn:sempkm:import:` prefix, UUID format

### Integration Verification (Manual / E2E)
- Paste valid JSON-LD with 5 typed objects → preview shows 5 subjects with types
- SHACL warnings appear in preview → import proceeds
- Import creates objects visible in workspace object browser
- Paste malformed Turtle → clear parse error message
- Upload `.jsonld` file → same preview/import flow
- Sidebar "Import RDF" link opens import wizard tab
- Command palette "Import > RDF Data" opens import wizard tab

## Requirement Coverage

This slice directly delivers:
- **IMPORT-01**: RDF paste/upload UI with format detection — covered by router, input form, format heuristic
- **IMPORT-02**: rdflib parsing with error capture and subject extraction — covered by parser module
- **IMPORT-03**: SHACL validation preview against installed model shapes — covered by parse/preview endpoint + pyshacl
- **IMPORT-04**: Event-sourced object creation via EventStore with provenance — covered by executor
- **IMPORT-05**: Blank node skolemization to `urn:sempkm:import:` URIs — covered by parser skolemize function
- **IMPORT-06**: IRI collision detection with skip-duplicate default — covered by executor collision check
- **IMPORT-07**: SSE progress events during import — covered by broadcast integration
