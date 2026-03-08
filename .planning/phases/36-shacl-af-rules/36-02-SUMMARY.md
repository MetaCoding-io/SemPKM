---
phase: 36-shacl-af-rules
plan: 02
subsystem: inference
tags: [shacl-af, sparql-rule, admin-ui, inference-filter]

requires:
  - phase: 36-01
    provides: "SHACL-AF rule execution engine, rules graph loading, sh:rule entailment type"
provides:
  - "basic-pkm SHACL-AF SPARQLRule (hasRelatedNote inverse derivation)"
  - "Rules entrypoint in manifest.yaml"
  - "SHACL Rules toggle in admin entailment config"
  - "sh:rule filter chip in inference panel"
affects: [inference, admin, basic-pkm-model]

tech-stack:
  added: []
  patterns: ["SHACL-AF SPARQLRule for inverse derivation beyond OWL 2 RL"]

key-files:
  created:
    - "models/basic-pkm/rules/basic-pkm.ttl"
  modified:
    - "models/basic-pkm/manifest.yaml"
    - "models/basic-pkm/ontology/basic-pkm.jsonld"
    - "backend/app/admin/router.py"
    - "backend/app/templates/admin/model_entailment_config.html"
    - "backend/app/templates/browser/inference_panel.html"

key-decisions:
  - "hasRelatedNote derived via SHACL rule, NOT owl:inverseOf, to demonstrate SHACL-AF value"
  - "Single-label example display in template (conditional arrow rendering)"

patterns-established:
  - "SHACL-AF rules file pattern: models/{modelId}/rules/{modelId}.ttl with sh:SPARQLRule"
  - "Rules examples queried from model rules named graph via SPARQL"

requirements-completed: [INF-02]

duration: 2min
completed: 2026-03-05
---

# Phase 36 Plan 02: SHACL-AF Rules Content & UI Integration Summary

**basic-pkm ships SHACL-AF SPARQLRule deriving hasRelatedNote, with admin toggle and inference panel filter chip for sh:rule**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T00:02:17Z
- **Completed:** 2026-03-05T00:03:58Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created SHACL-AF SPARQLRule in basic-pkm deriving bpkm:hasRelatedNote from bpkm:relatedProject
- Added bpkm:hasRelatedNote ObjectProperty to ontology with label for UI display
- Added SHACL Rules toggle to admin entailment config with rule label examples from rules graph
- Added sh:rule filter option to inference panel dropdown

## Task Commits

Each task was committed atomically:

1. **Task 1: Create basic-pkm SHACL-AF rules file and update manifest** - `9412e72` (feat)
2. **Task 2: Add SHACL Rules toggle to admin config and sh:rule filter chip** - `8960324` (feat)

## Files Created/Modified
- `models/basic-pkm/rules/basic-pkm.ttl` - SHACL-AF SPARQLRule deriving hasRelatedNote inverse
- `models/basic-pkm/manifest.yaml` - Added rules entrypoint and shacl_rules entailment default
- `models/basic-pkm/ontology/basic-pkm.jsonld` - Added bpkm:hasRelatedNote ObjectProperty
- `backend/app/admin/router.py` - SHACL Rules in ENTAILMENT_DISPLAY, rules examples SPARQL query
- `backend/app/templates/admin/model_entailment_config.html` - Conditional arrow for single-label examples
- `backend/app/templates/browser/inference_panel.html` - sh:rule filter option, fixed filter values

## Decisions Made
- hasRelatedNote uses SHACL-AF rule derivation (not owl:inverseOf) to demonstrate SHACL-AF value beyond OWL 2 RL
- Template conditionally renders arrow only when label_b is non-empty, supporting single-label SHACL rule examples

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed inference panel filter option values**
- **Found during:** Task 2
- **Issue:** Filter dropdown had `rdfs:domain` and `rdfs:range` as separate options which don't match the entailment type `rdfs:domain/rdfs:range`, and was missing `owl:TransitiveProperty`
- **Fix:** Updated filter options to match actual ENTAILMENT_TYPES values
- **Files modified:** backend/app/templates/browser/inference_panel.html
- **Committed in:** 8960324

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix ensures filter dropdown values match backend entailment types. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 36 complete: SHACL-AF rules infrastructure + content fully integrated
- Model reinstall + inference run needed for rule-derived triples to appear in live system

---
*Phase: 36-shacl-af-rules*
*Completed: 2026-03-05*
