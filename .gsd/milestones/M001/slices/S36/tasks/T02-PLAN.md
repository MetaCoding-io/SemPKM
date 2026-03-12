# T02: 36-shacl-af-rules 02

**Slice:** S36 — **Milestone:** M001

## Description

Create example SHACL-AF rules for basic-pkm, wire the rules entrypoint into the manifest, extend admin config UI with a SHACL Rules toggle, and add sh:rule to inference panel filter chips.

Purpose: Complete the user-facing experience so rule-derived triples are discoverable, configurable, and filterable.
Output: Working SHACL-AF rules in basic-pkm, admin toggle, filter chip.

## Must-Haves

- [ ] "basic-pkm model ships at least one SHACL-AF rule"
- [ ] "basic-pkm manifest declares rules entrypoint and shacl_rules entailment default"
- [ ] "Admin entailment config shows SHACL Rules toggle for models that have rules"
- [ ] "Inference panel filter chips include sh:rule option"
- [ ] "Rule-derived triples appear in inference run results"

## Files

- `models/basic-pkm/rules/basic-pkm.ttl`
- `models/basic-pkm/manifest.yaml`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `backend/app/admin/router.py`
- `backend/app/templates/admin/model_entailment_config.html`
- `backend/app/inference/router.py`
