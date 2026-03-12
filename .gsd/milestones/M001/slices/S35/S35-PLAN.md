# S35: Owl2 Rl Inference

**Goal:** Build the complete backend inference engine: owlrl dependency, InferenceService with selective entailment filtering, API endpoints for triggering inference and managing inferred triples (list, dismiss, promote), SQLite metadata table for per-triple state, and event log integration.
**Demo:** Build the complete backend inference engine: owlrl dependency, InferenceService with selective entailment filtering, API endpoints for triggering inference and managing inferred triples (list, dismiss, promote), SQLite metadata table for per-triple state, and event log integration.

## Must-Haves


## Tasks

- [x] **T01: 35-owl2-rl-inference 01** `est:8min`
  - Build the complete backend inference engine: owlrl dependency, InferenceService with selective entailment filtering, API endpoints for triggering inference and managing inferred triples (list, dismiss, promote), SQLite metadata table for per-triple state, and event log integration.

Purpose: This is the core backend that makes OWL 2 RL inference work. Without it, no inferred triples exist. All other plans depend on data this produces.
Output: Working `/api/inference/run` endpoint that materializes owl:inverseOf (and other enabled entailment) triples into `urn:sempkm:inferred`, plus CRUD endpoints for triple management.
- [x] **T02: 35-owl2-rl-inference 02** `est:6min`
  - Modify all SPARQL queries and UI templates to display inferred triples alongside user-created data. Relations panel shows inferred badge, object read view uses two-column layout, graph view uses dashed lines for inferred edges.

Purpose: Without this, inferred triples exist in the triplestore but are invisible to users. This plan makes inference results visible everywhere users look at their data.
Output: Modified SPARQL queries, updated templates with inferred badges, two-column object read layout, dashed graph edges.
- [x] **T03: 35-owl2-rl-inference 03** `est:3min`
  - Build the Inference bottom panel tab — the user's control center for inference. Contains a Refresh button to trigger inference, a global list of all inferred triples, filters (object type, date range), grouping options, and per-triple dismiss/promote actions.

Purpose: This is the primary user interface for interacting with inference. Users trigger inference here, review results, and manage individual triples.
Output: New Inference tab in bottom panel with full interactive triple management via htmx.
- [x] **T04: 35-owl2-rl-inference 04** `est:4min`
  - Build the admin UI for per-model entailment configuration with concrete ontology examples, and wire model uninstall to clean up inferred triples.

Purpose: Users need to understand and control what inference does. Abstract "owl:inverseOf" means nothing to most users — showing "hasParticipant <-> participatesIn" makes it concrete. Model uninstall must be clean.
Output: Admin entailment config section with toggles and examples, clean model uninstall.
- [x] **T05: 35-owl2-rl-inference 05** `est:3min`
  - Close 4 verification gaps from Phase 35 verification: (1) wire admin-saved entailment config into inference run, (2) add object_type and date range filters, (3) add group_by functionality, (4) populate last-run timestamp via OOB swap.

Purpose: The core inference engine works, but user control over entailment types is disconnected from the admin UI, the inference panel lacks filters specified in CONTEXT.md, and the last-run timestamp is never displayed.
Output: Fully wired entailment config, complete filter/group controls in inference panel, visible last-run timestamp.

## Files Likely Touched

- `backend/pyproject.toml`
- `backend/app/inference/__init__.py`
- `backend/app/inference/service.py`
- `backend/app/inference/entailments.py`
- `backend/app/inference/models.py`
- `backend/app/inference/router.py`
- `backend/app/main.py`
- `backend/app/db/base.py`
- `models/basic-pkm/manifest.yaml`
- `backend/app/sparql/client.py`
- `backend/app/browser/router.py`
- `backend/app/views/service.py`
- `backend/app/services/labels.py`
- `backend/app/templates/browser/properties.html`
- `backend/app/templates/browser/object_read.html`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/inference_panel.html`
- `backend/app/templates/browser/inference_triple_row.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/admin/model_entailment_config.html`
- `backend/app/admin/router.py`
- `backend/app/models/registry.py`
- `frontend/static/css/workspace.css`
- `backend/app/inference/service.py`
- `backend/app/inference/router.py`
- `backend/app/templates/browser/inference_panel.html`
