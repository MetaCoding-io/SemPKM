# T04: 35-owl2-rl-inference 04

**Slice:** S35 — **Milestone:** M001

## Description

Build the admin UI for per-model entailment configuration with concrete ontology examples, and wire model uninstall to clean up inferred triples.

Purpose: Users need to understand and control what inference does. Abstract "owl:inverseOf" means nothing to most users — showing "hasParticipant <-> participatesIn" makes it concrete. Model uninstall must be clean.
Output: Admin entailment config section with toggles and examples, clean model uninstall.

## Must-Haves

- [ ] "Admin model management section shows entailment configuration per installed Mental Model"
- [ ] "User can check/uncheck which OWL RL entailment types to enable for each model"
- [ ] "Available toggles: owl:inverseOf, rdfs:subClassOf, rdfs:subPropertyOf, owl:TransitiveProperty, rdfs:domain/rdfs:range"
- [ ] "Admin UI shows concrete examples from the model's actual ontology for each entailment type"
- [ ] "Defaults come from the model's manifest entailment_defaults; user overrides persist in settings"
- [ ] "Mental Model uninstall cleans up inferred triples"

## Files

- `backend/app/templates/admin/model_entailment_config.html`
- `backend/app/admin/router.py`
- `backend/app/models/registry.py`
- `frontend/static/css/workspace.css`
