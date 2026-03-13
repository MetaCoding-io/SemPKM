---
estimated_steps: 5
estimated_files: 6
---

# T02: Build TBox Explorer with cross-graph class hierarchy SPARQL and htmx tree

**Slice:** S07 — Ontology Viewer & Gist Foundation
**Milestone:** M003

## Description

Build the TBox Explorer — the collapsible class hierarchy tree spanning gist + all installed model ontology graphs + the user-types graph. This is the primary visual deliverable: users see how bpkm:Project nests under gist:Task, how bpkm:Note nests under gist:FormattedContent, etc. Uses FROM clause aggregation (same pattern as inference service's `_load_ontology_graphs()`) and lazy htmx expansion (same pattern as explorer hierarchy tree).

## Steps

1. **Add TBox query methods to OntologyService** — In `backend/app/ontology/service.py`:
   - `async get_ontology_graph_iris(self) -> list[str]` — query model registry for installed models, return list of `urn:sempkm:model:{id}:ontology` graph IRIs + `urn:sempkm:ontology:gist` + `urn:sempkm:user-types`
   - `async get_root_classes(self) -> list[dict]` — SPARQL: query `?class a owl:Class` with FROM clauses across all ontology graphs, filter to classes with no explicit `rdfs:subClassOf` (or only `rdfs:subClassOf owl:Thing`). Exclude blank nodes (`FILTER(isIRI(?class))`). Resolve labels via LabelService. Return `[{iri, label, graph_source}]` sorted by label.
   - `async get_subclasses(self, parent_iri: str) -> list[dict]` — SPARQL: query `?class rdfs:subClassOf <parent_iri>` across all ontology graphs. Filter to IRIs only. Resolve labels. Return sorted list.
   - Both methods include `has_subclasses` flag: quick ASK to check if the class has any subclasses (for tree toggle icon).
   
   Key SPARQL pattern for FROM clause aggregation:
   ```sparql
   SELECT DISTINCT ?class ?label WHERE {
     FROM <urn:sempkm:ontology:gist>
     FROM <urn:sempkm:model:basic-pkm:ontology>
     FROM <urn:sempkm:model:ppv:ontology>
     FROM <urn:sempkm:user-types>
     ?class a owl:Class .
     FILTER(isIRI(?class))
     FILTER NOT EXISTS { ?class rdfs:subClassOf ?parent . FILTER(isIRI(?parent) && ?parent != owl:Thing) }
     OPTIONAL { ?class skos:prefLabel ?skosLabel }
     OPTIONAL { ?class rdfs:label ?rdfsLabel }
     BIND(COALESCE(?skosLabel, ?rdfsLabel, REPLACE(STR(?class), "^.*/|^.*#|^.*:", "", "")) AS ?label)
   }
   ORDER BY ?label
   ```

2. **Create ontology router** — Create `backend/app/ontology/router.py`:
   - `ontology_router = APIRouter(tags=["ontology"])`
   - `GET /browser/ontology/tbox` — calls `get_root_classes()`, renders `tbox_tree.html`
   - `GET /browser/ontology/tbox/children?parent={iri}` — calls `get_subclasses(iri)`, renders `tbox_children.html`
   - Router depends on `get_current_user`, OntologyService via app.state
   - Wire LabelService dependency for label resolution

3. **Create TBox tree templates** — Following `hierarchy_tree.html` pattern:
   - `backend/app/templates/browser/ontology/tbox_tree.html` — root classes as `.tree-node` elements with:
     - `hx-get="/browser/ontology/tbox/children?parent={{ cls.iri | urlencode }}"` for lazy expansion
     - `hx-trigger="click once"` on the tree toggle
     - `hx-target="#tbox-children-{{ safe_id }}"` for child container
     - Class label click navigates to ABox instance list for that class (future wiring via htmx)
     - Show class source as muted badge (gist, basic-pkm, ppv) for disambiguation
   - `backend/app/templates/browser/ontology/tbox_children.html` — recursive child nodes with same pattern
   - Both handle empty state: "No subclasses" for leaf nodes

4. **Include ontology_router in browser coordinator** — Edit `backend/app/browser/router.py`:
   - Import `ontology_router` from `app.ontology.router`
   - Note: this router is NOT under `browser/` prefix — the `special-panel` fetches `/browser/ontology` which means the route needs to be `@ontology_router.get("/ontology/tbox")` registered under the `/browser` prefix via the browser coordinator. Alternatively, register as a separate top-level router. Follow the pattern used by `canvas` which is `@pages_router.get("/canvas")` — so ontology routes go through the browser router prefix.
   - Include `ontology_router` before `objects_router` (same as comments — avoid `:path` consumption)

5. **Add OntologyService DI** — Create `get_ontology_service()` dependency in `backend/app/dependencies.py` or access via `request.app.state.ontology_service`. Follow existing pattern (most services use `app.state`).

## Must-Haves

- [ ] Cross-graph SPARQL using FROM clause aggregation (gist + all model ontology graphs + user-types)
- [ ] Root classes query excludes blank nodes and owl:Thing-only parents
- [ ] Lazy child expansion via htmx (click once trigger)
- [ ] Label resolution handles gist's `skos:prefLabel` and model classes' `rdfs:label`
- [ ] Tree renders with expand/collapse toggle, class label, and source badge
- [ ] Routes: `GET /browser/ontology/tbox` (root tree), `GET /browser/ontology/tbox/children?parent={iri}` (children)
- [ ] ontology_router included in browser router

## Verification

- Start Docker stack → `curl http://localhost:3000/browser/ontology/tbox` returns HTML with gist root classes (Person, Task, FormattedContent, etc.)
- Expand a gist class → children endpoint returns model subclasses (e.g., gist:Task → bpkm:Project, ppv:Project)
- Classes with no subclasses show empty child area on expansion

## Observability Impact

- Signals added/changed: `logger.debug("TBox root: %d classes from %d graphs")`, `logger.debug("TBox children of %s: %d subclasses")`
- How a future agent inspects this: curl the endpoints directly; check SPARQL query in logs at DEBUG level
- Failure state exposed: HTTP 500 with error message on SPARQL failures; empty tree with "No classes found" message if no ontology graphs loaded

## Inputs

- `backend/app/ontology/service.py` — from T01, has OntologyService with gist loading, constants
- `backend/app/inference/service.py:_load_ontology_graphs()` — FROM clause aggregation pattern
- `backend/app/templates/browser/hierarchy_tree.html` — htmx tree node template pattern
- `backend/app/browser/router.py` — router coordinator for include order
- `backend/app/models/registry.py` — MODELS_GRAPH, ModelGraphs for graph IRI conventions

## Expected Output

- `backend/app/ontology/service.py` — extended with `get_ontology_graph_iris()`, `get_root_classes()`, `get_subclasses()`
- `backend/app/ontology/router.py` — new router with TBox endpoints
- `backend/app/browser/router.py` — modified to include ontology_router
- `backend/app/templates/browser/ontology/tbox_tree.html` — new TBox root tree template
- `backend/app/templates/browser/ontology/tbox_children.html` — new TBox children template
