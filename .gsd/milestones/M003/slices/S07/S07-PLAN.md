# S07: Ontology Viewer & Gist Foundation

**Goal:** Workspace has an ontology viewer with TBox Explorer (class hierarchy across gist + all models), ABox Browser (instances by type with counts), and RBox Legend (property domains/ranges). Gist 14.0.0 is loaded and fully visible in the hierarchy.
**Demo:** User opens the ontology viewer from the command palette or sidebar. The TBox tab shows a collapsible class hierarchy with gist:Person, gist:Task, gist:FormattedContent, etc. as top-level classes, and bpkm:Project, bpkm:Note, etc. nested under their gist parents via rdfs:subClassOf. The ABox tab shows instance counts per type. The RBox tab shows a property reference table. All data comes from live SPARQL queries across gist + model ontology graphs.

## Must-Haves

- Gist 14.0.0 bundled as `backend/ontologies/gist/gistCore14.0.0.ttl` and loaded into `urn:sempkm:ontology:gist` named graph at startup
- Gist graph version-checked via ASK query — skip reload if already current
- INSERT DATA batched (≤500 triples per batch) to avoid RDF4J size limits
- Alignment triples added to basic-pkm and ppv model ontology JSON-LD files (rdfs:subClassOf gist:X)
- Ontology viewer opens as `special-panel` with `specialType: 'ontology'` in dockview
- TBox Explorer: collapsible class hierarchy tree via htmx, lazy-loading children, spanning gist + all model ontology graphs + `urn:sempkm:user-types` (forward compat)
- ABox Browser: instance list grouped by type with per-type counts, querying `urn:sempkm:current` + `urn:sempkm:inferred`
- RBox Legend: property table with domain, range, property type (object vs datatype)
- Labels resolved via LabelService (gist uses `skos:prefLabel`, model classes use `rdfs:label`)
- Ontology viewer accessible via command palette entry
- Backend unit tests for gist loading, TBox/ABox/RBox SPARQL queries
- E2E test covering ontology viewer open, TBox tree render, ABox counts

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker Compose stack with RDF4J triplestore for SPARQL queries)
- Human/UAT required: yes (ontology hierarchy correctness requires human judgment on gist alignment quality)

## Verification

- `cd backend && python -m pytest tests/test_ontology_service.py -v` — unit tests for gist loading logic, TBox/ABox/RBox query builders, batch splitting, version checking
- `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts` — E2E: open ontology viewer, verify TBox tree shows gist classes, verify ABox shows instance counts, verify RBox shows property table
- Manual: open Docker Compose stack → command palette → "Open: Ontology Viewer" → TBox tab shows gist hierarchy with model classes nested underneath

## Observability / Diagnostics

- Runtime signals: `logger.info` on gist load (triple count, duration), `logger.warning` on INSERT DATA batch failure, `logger.debug` on TBox/ABox/RBox query timing
- Inspection surfaces: `ASK { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }` via SPARQL console to verify gist is loaded; ontology viewer itself shows class counts
- Failure visibility: gist load failure at startup logs error with exception traceback; ontology viewer renders "Failed to load" message on SPARQL errors rather than blank panel
- Redaction constraints: none (no secrets in ontology data)

## Integration Closure

- Upstream surfaces consumed: `_build_insert_data_sparql()` in `services/models.py` for INSERT DATA generation; `_load_ontology_graphs()` pattern in `inference/service.py` for FROM clause aggregation; `special-panel` component in `workspace-layout.js` for panel hosting; explorer tree htmx patterns in `hierarchy_tree.html`/`hierarchy_children.html`; `LabelService.resolve_batch()` for label resolution; `IconService.get_type_icon()` for icons
- New wiring introduced in this slice: `backend/app/ontology/` module (service + router); gist graph loaded at startup via `main.py` lifespan; `ontology_router` included in `browser/router.py`; `openOntologyTab()` in `workspace.js`; command palette entry; 4 new templates in `templates/browser/ontology/`
- What remains before the milestone is truly usable end-to-end: S08 (in-app class creation) consumes the TBox hierarchy for parent class selection; S09 (admin stats) is independent; S10 (E2E coverage gaps) is independent

## Tasks

- [x] **T01: Bundle gist 14.0.0 and build ontology service with startup loader** `est:2h`
  - Why: Foundation for everything — gist must be in the triplestore before TBox/ABox/RBox queries can return cross-graph results. Also adds alignment triples to model ontology files.
  - Files: `backend/ontologies/gist/gistCore14.0.0.ttl`, `backend/ontologies/gist/LICENSE`, `backend/app/ontology/__init__.py`, `backend/app/ontology/service.py`, `backend/app/main.py`, `models/basic-pkm/ontology/basic-pkm.jsonld`, `models/ppv/ontology/ppv.jsonld`
  - Do: Download and bundle gistCore.ttl (pinned v14.0.0). Create `OntologyService` with `ensure_gist_loaded()` (ASK version check → batched INSERT DATA ≤500 triples). Add `rdfs:subClassOf` alignment triples to basic-pkm (Project→gist:Task, Person→gist:Person, Note→gist:FormattedContent, Concept→gist:KnowledgeConcept) and ppv (Project→gist:Task) JSON-LD files. Wire `ensure_gist_loaded()` into `main.py` lifespan after `ensure_starter_model()`. Add gist namespace to prefix declarations.
  - Verify: `cd backend && python -m pytest tests/test_ontology_service.py -v` — tests for batch splitting, version check logic, INSERT DATA generation
  - Done when: gist graph loads on startup without errors in Docker logs, ASK query confirms triples in `urn:sempkm:ontology:gist`, alignment triples visible in model ontology graphs

- [x] **T02: Build TBox Explorer with cross-graph class hierarchy SPARQL and htmx tree** `est:2h`
  - Why: The TBox Explorer is the primary deliverable — shows the unified class hierarchy across gist + all models. Users see how their types relate to gist's upper ontology.
  - Files: `backend/app/ontology/service.py`, `backend/app/ontology/router.py`, `backend/app/browser/router.py`, `backend/app/templates/browser/ontology/tbox_tree.html`, `backend/app/templates/browser/ontology/tbox_children.html`
  - Do: Add TBox query methods to OntologyService: `get_root_classes()` (classes with no rdfs:subClassOf or only owl:Thing parent) and `get_subclasses(parent_iri)` — both use FROM clause aggregation across gist + all model ontology graphs + user-types. Create `ontology_router` with `GET /browser/ontology/tbox` (root tree) and `GET /browser/ontology/tbox/children?parent={iri}` (lazy children). Create htmx tree templates following hierarchy_tree.html pattern. Include ontology_router in browser/router.py.
  - Verify: Start Docker stack → SPARQL console query confirms cross-graph class hierarchy → curl `/browser/ontology/tbox` returns HTML tree with gist classes
  - Done when: TBox tree renders gist root classes and model subclasses nested correctly via lazy expansion

- [x] **T03: Build ABox Browser and RBox Legend with ontology viewer panel** `est:2h`
  - Why: Completes the three-tab ontology viewer. ABox shows what data exists per type; RBox shows available properties. The viewer panel ties everything together as a workspace tab.
  - Files: `backend/app/ontology/service.py`, `backend/app/ontology/router.py`, `backend/app/templates/browser/ontology/ontology_page.html`, `backend/app/templates/browser/ontology/abox_browser.html`, `backend/app/templates/browser/ontology/abox_instances.html`, `backend/app/templates/browser/ontology/rbox_legend.html`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`
  - Do: Add ABox service methods: `get_type_counts()` (batched VALUES query across current+inferred graphs) and `get_instances(class_iri)` (instance list with labels). Add RBox service method: `get_properties()` (object + datatype properties with domain/range from all ontology graphs). Create `GET /browser/ontology` (main page with three tabs), `GET /browser/ontology/abox` (type list with counts), `GET /browser/ontology/abox/instances?class={iri}` (instances), `GET /browser/ontology/rbox` (property table). Create `openOntologyTab()` in workspace.js following openCanvasTab pattern. Add command palette entry. Add CSS for ontology viewer.
  - Verify: Open browser → command palette → "Open: Ontology Viewer" → three tabs visible, TBox shows tree, ABox shows counts, RBox shows properties
  - Done when: Full ontology viewer functional as a workspace tab with all three sections rendering real SPARQL data

- [x] **T04: Add unit tests and E2E test for ontology viewer** `est:1.5h`
  - Why: Proves the slice delivers at integration level. Unit tests verify SPARQL query correctness and batch logic. E2E test verifies the full user flow from opening the viewer to seeing data.
  - Files: `backend/tests/test_ontology_service.py`, `e2e/tests/22-ontology/ontology-viewer.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Write unit tests: gist batch splitting (4000 triples → 8 batches of 500), version check ASK query format, TBox root class query correctness, ABox type count query with VALUES, RBox property query shape. Write E2E test: navigate to workspace → open ontology viewer via command palette → verify TBox tab shows class tree → verify at least one gist class visible → expand a gist class to see model subclasses → switch to ABox tab → verify type counts rendered → switch to RBox tab → verify property table rendered. Add selectors to `selectors.ts`.
  - Verify: `cd backend && python -m pytest tests/test_ontology_service.py -v` passes; `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts` passes
  - Done when: All unit tests pass, E2E test passes against live Docker Compose stack

## Files Likely Touched

- `backend/ontologies/gist/gistCore14.0.0.ttl` (new — bundled gist file)
- `backend/ontologies/gist/LICENSE` (new — CC BY 4.0 attribution)
- `backend/app/ontology/__init__.py` (new)
- `backend/app/ontology/service.py` (new — OntologyService)
- `backend/app/ontology/router.py` (new — ontology_router)
- `backend/app/main.py` (modified — gist loading in lifespan)
- `backend/app/browser/router.py` (modified — include ontology_router)
- `backend/app/templates/browser/ontology/ontology_page.html` (new)
- `backend/app/templates/browser/ontology/tbox_tree.html` (new)
- `backend/app/templates/browser/ontology/tbox_children.html` (new)
- `backend/app/templates/browser/ontology/abox_browser.html` (new)
- `backend/app/templates/browser/ontology/abox_instances.html` (new)
- `backend/app/templates/browser/ontology/rbox_legend.html` (new)
- `frontend/static/js/workspace.js` (modified — openOntologyTab, command palette)
- `frontend/static/css/workspace.css` (modified — ontology viewer styles)
- `models/basic-pkm/ontology/basic-pkm.jsonld` (modified — alignment triples)
- `models/ppv/ontology/ppv.jsonld` (modified — alignment triples)
- `backend/tests/test_ontology_service.py` (new)
- `e2e/tests/22-ontology/ontology-viewer.spec.ts` (new)
- `e2e/helpers/selectors.ts` (modified — ontology selectors)
