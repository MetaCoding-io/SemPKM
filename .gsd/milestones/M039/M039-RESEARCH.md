# M039 Research: RDF Data Import & API Documentation Cleanup

## 1. Codebase Findings

### Existing Import Infrastructure

Two fully-working import wizards establish the pattern: Obsidian (`backend/app/obsidian/`) and Notion (`backend/app/notion/`). Both follow the same architecture:

- **Router** (FastAPI, prefix-based, htmx partials) — multi-step wizard flow
- **Scanner** — analyzes uploaded data, produces structured scan results
- **Executor** — two-pass import engine (Pass 1: objects, Pass 2: edges) using `handle_object_create`, `handle_body_set`, `handle_edge_create` + `EventStore.commit()`
- **Broadcast** — SSE fan-out for real-time progress (shared `ScanBroadcast` + `stream_sse` async generator)
- **Models** — dataclasses for scan results, mapping config, import results
- **Templates** — step-bar UI, upload form, scan results, mapping, preview, progress, summary partials

The Obsidian executor is 439 lines; Notion is 412. Both use `asyncio.create_task()` for background import execution with SSE progress streaming.

### RDF Import vs. Obsidian/Notion Import

The RDF import is **structurally simpler** than Obsidian/Notion:

| Concern | Obsidian/Notion | RDF Import |
|---------|----------------|------------|
| Type detection | Heuristic (frontmatter, folder, tags) | Explicit `rdf:type` triples |
| Type mapping | Interactive wizard step (user picks target type) | Not needed — types are declared |
| Property mapping | Interactive wizard step (frontmatter key → SHACL property) | Not needed — predicates are RDF URIs |
| Body extraction | Markdown content parsing | Not applicable (RDF is structured data) |
| Edge detection | Wiki-link/relation resolution by name matching | Direct: triples where object is a URIRef subject |
| Format handling | ZIP upload → extract → scan | Paste text or upload file → rdflib parse |

The wizard simplifies to: **Paste/Upload → Parse & Preview → SHACL Validate → Import**.

### rdflib Parsing Capabilities

All three target formats parse correctly with rdflib (verified in `backend/.venv`):

| Format | Extension | `guess_format()` | Auto-detect from string? | Notes |
|--------|-----------|-------------------|--------------------------|-------|
| JSON-LD | `.jsonld`, `.json` | `json-ld` | **No** — rdflib can't detect JSON from string content | Must specify `format='json-ld'` explicitly |
| Turtle | `.ttl` | `turtle` | **Yes** — works as default | `@prefix` triggers turtle parser |
| N-Triples | `.nt` | `nt` | **No** — falls back to turtle, which may fail on bare IRIs | Specify `format='nt'` for reliability |

**Format detection strategy:** For file uploads, use `rdflib.util.guess_format(filename)`. For pasted content, use a heuristic: starts with `{` or `[` → JSON-LD; starts with `@prefix` or `@base` → Turtle; starts with `<` and lines end with `.` → N-Triples. Provide a manual format override dropdown as fallback.

### Blank Node Handling

rdflib has built-in `Graph.skolemize()` but it produces `https://rdflib.github.io/.well-known/genid/rdflib/N...` URIs. For SemPKM, manual skolemization to `urn:sempkm:import:{uuid}` is cleaner. Pattern: iterate parsed graph, build a BNode→URIRef mapping, reconstruct graph with substituted terms.

JSON-LD without `@id` creates BNode subjects — this is the most common blank node scenario for import. Turtle `_:label` syntax also produces BNodes.

### EventStore Integration

The `Operation` dataclass is format-agnostic — it takes:
- `operation_type: str`
- `affected_iris: list[str]`
- `description: str`
- `data_triples: list[tuple]` (s, p, o)
- `materialize_inserts: list[tuple]`
- `materialize_deletes: list[tuple]`

For RDF import, we can build Operations directly from parsed triples without going through `handle_object_create()`. This is cleaner because:
1. `handle_object_create()` calls `mint_object_iri()` — imported data already has IRIs
2. `handle_object_create()` expects `ObjectCreateParams` with a properties dict — parsed triples are already (s, p, o) tuples
3. Direct Operation construction preserves the original RDF data faithfully

`EventStore.commit_bulk()` is ideal for imports of 10+ subjects — creates ~10 summary triples instead of N*5 per-operation triples. Has a 1000-operation limit.

### SHACL Validation Preview

`pyshacl.validate(data_graph, shacl_graph=shapes_graph)` works on standalone rdflib Graphs — no triplestore needed. For preview:

1. Call `model_shapes_loader(client)` to get installed model shapes
2. Run `pyshacl.validate(parsed_data, shacl_graph=shapes, allow_infos=True, allow_warnings=True, advanced=True)` in thread
3. Parse `ValidationReport.from_pyshacl()` for per-subject results

This validates against real SHACL shapes without committing anything. The `advanced=True` flag enables SHACL-AF rules (which some models like CRM and Research use).

### Edge Handling Architecture

SemPKM models edges as reified resources: `sempkm:Edge` with `sempkm:source`, `sempkm:target`, `sempkm:predicate`. But raw RDF has direct triples like `ex:alice schema:knows ex:bob`.

**Design decision needed:** Two approaches:

1. **Direct triple insertion** — Store `ex:alice schema:knows ex:bob` as-is in `urn:sempkm:current`. Simple, faithful. Object properties show in the property table. But the Edge Inspector UI won't show these as edges (it queries `sempkm:Edge` resources).

2. **Hybrid** — Store literal-valued triples directly. For triples where the object is a URIRef that's also an imported subject, create reified Edge resources via `handle_edge_create()`. This matches the existing two-pass pattern and makes cross-object links visible in the edge inspector.

**Recommendation:** Option 1 (direct insertion) for v1. Reification is lossy and complex — some URIRef objects are vocabulary terms, not importable subjects. Edge detection is ambiguous without a heuristic. Users can always create edges manually later. Direct triples are valid RDF and queryable via SPARQL.

### IRI Collision Detection

Simple ASK query: `ASK { GRAPH <urn:sempkm:current> { <{iri}> ?p ?o } }`. The triplestore client's `query()` method returns `{"boolean": true/false}` for ASK queries. Can batch-check multiple IRIs with a `VALUES` clause for efficiency.

### Router Tag Status

10 routers confirmed without `tags=` parameter (85 total routes):

| Router | Routes | Proposed Tag |
|--------|--------|-------------|
| `commands/router.py` | 2 | `commands` |
| `sparql/router.py` | 18 | `sparql` |
| `validation/router.py` | 2 | `validation` |
| `health/router.py` | 1 | `health` |
| `admin/router.py` | 21 | `admin` |
| `inference/router.py` | 6 | `inference` |
| `lint/router.py` | 17 | `lint` |
| `apps/admin_router.py` | 11 | `app-management` |
| `apps/router.py` | 2 | `app-proxy` |
| `shell/router.py` | 5 | `shell` |

Each fix is one parameter addition to the `APIRouter()` constructor. Zero behavior change.

### UI Integration Points

- **Sidebar:** Import section in `backend/app/templates/components/_sidebar.html` (lines 109-117) has "Import Vault" and "Import Notion" entries. Add "Import RDF" here.
- **Command palette:** `frontend/static/js/workspace.js` lines 1496-1512 has import entries. Add "Import > RDF Data" entry.
- **Dockview special panel:** `workspace-layout.js` maps `specialType` to URL. Either use `specialType: 'import/rdf'` (maps to `/browser/import/rdf` automatically) or add a specific case.
- **CSS:** `frontend/static/css/import.css` (997 lines) — shared import styling. Reuse for RDF import.

### Routing Considerations

The Obsidian router has `prefix="/browser/import"`. Adding an RDF import at `/browser/import/rdf` works as a separate route on either the same router or a new one. A new router (`backend/app/rdf_import/router.py`) with `prefix="/browser/import/rdf"` keeps concerns separated and follows the Notion pattern (separate module).

## 2. Key Design Decisions

### D1: Store imported triples directly (no IRI reminting)

Imported RDF subjects keep their original IRIs. No reminting to SemPKM `{namespace}/{Type}/{slug}` pattern. Rationale: RDF import users expect their IRIs to be preserved. The EventStore `Operation` accepts arbitrary IRIs. The object view queries `<iri> ?p ?o` and renders any IRI.

### D2: Direct triple insertion, no edge reification

All parsed triples go into `urn:sempkm:current` as-is. URIRef-to-URIRef triples (like `ex:alice schema:knows ex:bob`) are stored as direct triples, not reified as `sempkm:Edge` resources. Simplifies the import, preserves data fidelity. Edge Inspector won't show these — acceptable for v1.

### D3: One Operation per subject, commit_bulk for batches

Group parsed triples by subject. Each subject becomes one `Operation` with `operation_type="rdf.import"`. For imports with ≤1000 subjects, use `EventStore.commit_bulk()`. For larger imports, chunk into batches of 500.

### D4: Manual format detection with heuristic fallback

File uploads: detect from extension via `guess_format()`. Pasted text: heuristic (starts with `{`/`[` → JSON-LD, `@prefix` → Turtle, `<` with trailing `.` → N-Triples). Always show a format override dropdown.

### D5: Separate module, not extension of Obsidian router

New `backend/app/rdf_import/` module with its own router, templates, models. Parallel to `obsidian/` and `notion/` but simpler (no scanner, no mapping wizard).

## 3. Risk Assessment

### Low Risk
- **Redoc tag cleanup** — Pure metadata addition, zero behavior change. 10 one-line edits. Test: open `/redoc` and verify grouping.
- **rdflib parsing** — Well-tested library, already a project dependency. All three formats verified.
- **SHACL preview** — Same `pyshacl.validate()` call used by `ValidationService`, just against parsed data instead of triplestore data.

### Medium Risk
- **Blank node skolemization** — Needs careful implementation to maintain internal consistency (blank nodes referenced by multiple triples must map to the same URI). The BNode→URIRef mapping is straightforward but must be applied to both subject and object positions.
- **Large file performance** — rdflib parsing and pyshacl validation are CPU-bound. A 10,000-triple file may take several seconds for SHACL validation. The existing `asyncio.to_thread()` pattern handles this. May want to skip SHACL preview above a configurable threshold (e.g., 5000 triples) and validate post-import instead.
- **Subject grouping accuracy** — Some RDF data uses reified statements, blank nodes for structured values (e.g., schema.org PostalAddress), or intermediate nodes. Grouping by "top-level subjects" (those that appear as subjects but not as objects of non-rdf:type predicates) would be more accurate than naive subject enumeration.

### Low-Medium Risk
- **IRI collision** — Simple check, but the UX needs to be clear. Show which IRIs already exist, default to skip with option to override (merge/replace). Skip-only is fine for v1.

## 4. Slice Boundary Recommendations

### Natural Boundaries

1. **Redoc tag cleanup** — Completely independent, zero risk, 10 one-line edits. Can be a standalone slice or folded into another. Proves value immediately (open `/redoc`).

2. **RDF parse + preview backend** — The parsing engine, format detection, subject grouping, SHACL validation preview. No UI, no EventStore integration. This is the novel code. Testable with unit tests.

3. **RDF import execution** — EventStore integration, blank node skolemization, IRI collision detection, SSE progress. Builds on the parse/preview output. Follows the established Obsidian/Notion executor pattern.

4. **RDF import UI** — Templates, sidebar entry, command palette entry, dockview panel integration. Follows established import wizard UI patterns. Can reuse `import.css` styling.

5. **E2E integration** — Full round-trip: paste JSON-LD → see preview → import → verify objects in browser.

### Recommended Order

1. **Redoc tags** (risk: none, proves immediate value)
2. **Parse + preview backend** (risk: medium — novel format detection and subject grouping)
3. **Import execution backend** (risk: low-medium — follows established patterns)
4. **Import UI + integration** (risk: low — template work following established patterns)

Alternatively, slices 2+3 could be combined since the backend is cohesive and the execution code directly consumes the parser output.

## 5. Candidate Requirements

These should be created in REQUIREMENTS.md if the milestone proceeds:

| ID | Requirement | Priority |
|----|-------------|----------|
| IMPORT-01 | RDF paste/upload UI with format detection (JSON-LD, Turtle, N-Triples) | Must |
| IMPORT-02 | rdflib parsing with error capture and subject extraction | Must |
| IMPORT-03 | SHACL validation preview against installed model shapes | Must |
| IMPORT-04 | Event-sourced object creation via EventStore with provenance | Must |
| IMPORT-05 | Blank node skolemization to `urn:sempkm:import:` URIs | Must |
| IMPORT-06 | IRI collision detection with skip-duplicate default | Should |
| IMPORT-07 | SSE progress events during import | Should |
| API-09 | Redoc tag cleanup — zero "default" routes | Must |

### Not Requiring New Requirements

- Edge reification is explicitly out of scope (design decision D2)
- Large file optimization (skip SHACL preview above threshold) is an implementation detail
- Import from URL is explicitly out of scope per CONTEXT.md

## 6. Open Questions for Planner

1. **Subject filtering in preview** — Should users be able to deselect individual subjects before import? The context says yes (checkboxes). This adds complexity to both preview UI and import execution (filter out deselected subjects). Worth doing — follows Obsidian pattern.

2. **Import provenance** — The `commit_bulk()` call needs `summary` and `source` strings. Recommend: `summary="RDF import: {n} objects from {format}"`, `source="rdf-import"`.

3. **Post-import validation** — Should we trigger a full SHACL validation run after import completes (like the Obsidian importer does implicitly via EventStore webhooks)? The existing webhook + ValidationService pipeline handles this automatically — any EventStore commit triggers validation. No extra code needed.

## 7. Technology Notes

### No New Dependencies

- `rdflib` — already installed, version in `pyproject.toml`
- `pyshacl` — already installed
- `frontmatter` — not needed (RDF data is structured, not Markdown)
- All import infrastructure (EventStore, SSE broadcast, handle_* commands) exists

### Relevant Skills

No additional agent skills needed. The project uses:
- **FastAPI** — well-established patterns in codebase (38+ routers)
- **htmx** — standard template pattern for import wizards
- **rdflib / pyshacl** — already used extensively, no docs lookup needed

Potentially useful but not critical:
- `wshobson/agents@fastapi-templates` (8.7K installs) — FastAPI patterns skill
- `mindrally/skills@htmx` (239 installs) — htmx skill

Both are optional — the codebase conventions are clear enough.
