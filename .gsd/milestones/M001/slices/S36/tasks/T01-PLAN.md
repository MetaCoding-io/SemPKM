# T01: 36-shacl-af-rules 01

**Slice:** S36 — **Milestone:** M001

## Description

Extend the Mental Model manifest, loader, and registry to support an optional `rules` entrypoint, and extend the inference pipeline to execute SHACL-AF rules via `pyshacl.shacl_rules()` after OWL 2 RL closure.

Purpose: Enable Mental Models to declare SHACL-AF rules that produce derived triples beyond what OWL 2 RL can express.
Output: Backend infrastructure that loads rules graphs and executes them during inference runs.

## Must-Haves

- [ ] "ManifestEntrypoints accepts an optional rules field"
- [ ] "ModelArchive loads a rules graph (Turtle or JSON-LD) when declared"
- [ ] "ModelGraphs has a rules named graph IRI"
- [ ] "InferenceService runs SHACL-AF rules after OWL 2 RL closure"
- [ ] "Rule-derived triples are tagged as sh:rule entailment type"
- [ ] "Rule-derived triples are stored in urn:sempkm:inferred"

## Files

- `backend/app/models/manifest.py`
- `backend/app/models/loader.py`
- `backend/app/models/registry.py`
- `backend/app/inference/entailments.py`
- `backend/app/inference/service.py`
