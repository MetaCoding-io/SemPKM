# S36: Shacl Af Rules

**Goal:** Extend the Mental Model manifest, loader, and registry to support an optional `rules` entrypoint, and extend the inference pipeline to execute SHACL-AF rules via `pyshacl.
**Demo:** Extend the Mental Model manifest, loader, and registry to support an optional `rules` entrypoint, and extend the inference pipeline to execute SHACL-AF rules via `pyshacl.

## Must-Haves


## Tasks

- [x] **T01: 36-shacl-af-rules 01** `est:2min`
  - Extend the Mental Model manifest, loader, and registry to support an optional `rules` entrypoint, and extend the inference pipeline to execute SHACL-AF rules via `pyshacl.shacl_rules()` after OWL 2 RL closure.

Purpose: Enable Mental Models to declare SHACL-AF rules that produce derived triples beyond what OWL 2 RL can express.
Output: Backend infrastructure that loads rules graphs and executes them during inference runs.
- [x] **T02: 36-shacl-af-rules 02** `est:2min`
  - Create example SHACL-AF rules for basic-pkm, wire the rules entrypoint into the manifest, extend admin config UI with a SHACL Rules toggle, and add sh:rule to inference panel filter chips.

Purpose: Complete the user-facing experience so rule-derived triples are discoverable, configurable, and filterable.
Output: Working SHACL-AF rules in basic-pkm, admin toggle, filter chip.

## Files Likely Touched

- `backend/app/models/manifest.py`
- `backend/app/models/loader.py`
- `backend/app/models/registry.py`
- `backend/app/inference/entailments.py`
- `backend/app/inference/service.py`
- `models/basic-pkm/rules/basic-pkm.ttl`
- `models/basic-pkm/manifest.yaml`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `backend/app/admin/router.py`
- `backend/app/templates/admin/model_entailment_config.html`
- `backend/app/inference/router.py`
