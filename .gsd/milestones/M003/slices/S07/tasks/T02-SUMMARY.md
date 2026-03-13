---
id: T02
parent: S07
milestone: M003
provides:
  - TBox Explorer with cross-graph class hierarchy SPARQL and htmx tree
  - OntologyService TBox query methods (get_root_classes, get_subclasses, get_ontology_graph_iris)
  - ontology_router with GET /browser/ontology/tbox and GET /browser/ontology/tbox/children
key_files:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/ontology/tbox_tree.html
  - backend/app/templates/browser/ontology/tbox_children.html
  - backend/app/dependencies.py
  - frontend/static/css/workspace.css
key_decisions:
  - Label resolution done inline in SPARQL via COALESCE(skos:prefLabel, rdfs:label, local-name-regex) rather than via LabelService — ontology class labels live in ontology graphs, not in current/inferred graphs where LabelService queries
  - Batch has_subclasses check via VALUES + FILTER EXISTS in a single SPARQL query rather than N+1 ASK queries per class
patterns_established:
  - FROM clause aggregation for TBox queries across gist + model ontology + user-types graphs, built dynamically from model registry
  - htmx tree pattern for ontology classes reuses existing tree-node/tree-children CSS classes from hierarchy_tree.html
  - Source badge pattern (badge-gist, badge-bpkm, badge-ppv, badge-user) for disambiguating class provenance in tree
observability_surfaces:
  - logger.debug("TBox root: %d classes from %d graphs") on root class query
  - logger.debug("TBox children of %s: %d subclasses") on subclass query
  - logger.error on SPARQL failures with exc_info=True
  - curl /browser/ontology/tbox returns HTML tree; curl /browser/ontology/tbox/children?parent={iri} returns children
duration: 30min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Build TBox Explorer with cross-graph class hierarchy SPARQL and htmx tree

**Added TBox Explorer with cross-graph FROM clause aggregation SPARQL, htmx lazy-loading tree, and ontology router with source badges.**

## What Happened

Extended OntologyService with three TBox query methods:
- `get_ontology_graph_iris()` — queries model registry, returns list of all ontology graph IRIs (gist + model ontologies + user-types)
- `get_root_classes()` — SPARQL with dynamic FROM clauses, finds owl:Class with no rdfs:subClassOf parent (excluding owl:Thing), resolves labels via COALESCE, batch-checks has_subclasses
- `get_subclasses(parent_iri)` — same FROM clause pattern for direct subclasses of a given parent

Created `ontology_router` with two endpoints mounted on the browser router:
- `GET /browser/ontology/tbox` — renders root class tree
- `GET /browser/ontology/tbox/children?parent={iri}` — renders subclasses for htmx lazy expansion

Created two Jinja2 templates (`tbox_tree.html`, `tbox_children.html`) following the existing hierarchy_tree.html pattern with htmx `hx-get`/`hx-trigger="click once"` for lazy child loading.

Added CSS for TBox source badges (gist, basic-pkm, ppv, user) and tree-toggle-leaf styling.

Added `get_ontology_service()` DI function to dependencies.py.

## Verification

- **Root tree endpoint:** `curl http://localhost:3000/browser/ontology/tbox` → returns HTML with 66 gist root classes (Account, Agreement, Aspect, Category, etc.) plus model classes (Concept basic-pkm, Note basic-pkm, Person basic-pkm, Project basic-pkm)
- **Children endpoint:** `GET /browser/ontology/tbox/children?parent=gist:Category` → returns 13 gist subclasses (AddressUsageType, Behavior, DegreeOfCommitment, etc.)
- **Leaf node endpoint:** `GET /browser/ontology/tbox/children?parent=gist:Account` → returns "No subclasses" empty state
- **Cross-graph aggregation:** FROM clauses include gist + basic-pkm:ontology + user-types; model classes (Concept, Note, Person, Project from basic-pkm) appear as root nodes
- **Existing tests pass:** `cd backend && .venv/bin/pytest tests/test_ontology_service.py -v` → 16 passed
- **No SPARQL errors:** API logs show all ontology requests returning 200

## Diagnostics

- **Check TBox root:** `curl http://localhost:3000/browser/ontology/tbox` (requires auth session)
- **Check children:** `curl http://localhost:3000/browser/ontology/tbox/children?parent=<url-encoded-iri>`
- **Debug SPARQL:** set `LOG_LEVEL=DEBUG` → TBox queries log class counts and graph counts
- **Failure mode:** SPARQL errors → logged with traceback, endpoint returns empty tree with "No classes found" message

## Deviations

- SPARQL FROM clauses must go between SELECT and WHERE (not inside WHERE block) — initial placement was wrong, caused 400 from RDF4J. Fixed by moving FROM clauses to the correct position.
- Label resolution uses inline SPARQL COALESCE rather than LabelService.resolve_batch() — LabelService only queries urn:sempkm:current and urn:sempkm:inferred, but ontology class labels (skos:prefLabel, rdfs:label) live in ontology graphs. Inline resolution is correct for this use case.
- Model alignment triples (rdfs:subClassOf gist:X) from T01 are in the JSON-LD files but not yet loaded into the triplestore because the model was already installed when T01 ran. Model classes (basic-pkm:Project, etc.) appear as root nodes for now; they'll nest under gist parents after model reinstall.

## Known Issues

- basic-pkm/ppv alignment triples (rdfs:subClassOf gist classes) not yet in triplestore — requires model reinstall to pick up the JSON-LD changes from T01. Not a bug, just deployment state.

## Files Created/Modified

- `backend/app/ontology/service.py` — extended with get_ontology_graph_iris(), get_root_classes(), get_subclasses(), _batch_has_subclasses(), _build_from_clauses()
- `backend/app/ontology/router.py` — new router with tbox_tree and tbox_children endpoints
- `backend/app/browser/router.py` — modified to include ontology_router before objects_router
- `backend/app/dependencies.py` — added get_ontology_service() DI function
- `backend/app/templates/browser/ontology/tbox_tree.html` — new root tree template
- `backend/app/templates/browser/ontology/tbox_children.html` — new children template
- `frontend/static/css/workspace.css` — added TBox source badge and tree styling
