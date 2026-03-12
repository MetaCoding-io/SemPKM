---
id: S36
parent: M001
milestone: M001
provides:
  - SHACL-AF rules loading infrastructure (manifest, loader, registry)
  - SHACL-AF rule execution step in inference pipeline via pyshacl.shacl_rules()
  - [object Object]
  - "basic-pkm SHACL-AF SPARQLRule (hasRelatedNote inverse derivation)"
  - "Rules entrypoint in manifest.yaml"
  - "SHACL Rules toggle in admin entailment config"
  - "sh:rule filter chip in inference panel"
requires: []
affects: []
key_files: []
key_decisions:
  - "Format detection by file extension in load_rdf_file (.ttl for Turtle, .jsonld for JSON-LD)"
  - "Rule-derived triples tagged as sh:rule directly, bypassing classify_entailment heuristics"
  - "TypeError fallback for iterate_rules parameter in pyshacl compatibility"
  - "hasRelatedNote derived via SHACL rule, NOT owl:inverseOf, to demonstrate SHACL-AF value"
  - "Single-label example display in template (conditional arrow rendering)"
patterns_established:
  - "load_rdf_file: multi-format RDF loading with extension-based dispatch"
  - "Rule triple tracking: pre/post set diff to identify SHACL-derived triples"
  - "SHACL-AF rules file pattern: models/{modelId}/rules/{modelId}.ttl with sh:SPARQLRule"
  - "Rules examples queried from model rules named graph via SPARQL"
observability_surfaces: []
drill_down_paths: []
duration: 2min
verification_result: passed
completed_at: 2026-03-05
blocker_discovered: false
---
# S36: Shacl Af Rules

**# Phase 36 Plan 01: SHACL-AF Rules Infrastructure Summary**

## What Happened

# Phase 36 Plan 01: SHACL-AF Rules Infrastructure Summary

**SHACL-AF rules loading via manifest/loader/registry and execution via pyshacl.shacl_rules() in inference pipeline with sh:rule entailment tagging**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-04T23:57:15Z
- **Completed:** 2026-03-04T23:59:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended ManifestEntrypoints with optional rules field and placeholder resolution
- Added load_rdf_file() supporting Turtle and JSON-LD format detection by extension
- Added rules named graph to ModelGraphs (included in all_graphs for cleanup)
- Added sh:rule entailment type and shacl_rules manifest key mapping
- Inserted SHACL-AF rules execution step (4b) in inference pipeline after OWL 2 RL closure
- Rule-derived triples tagged as sh:rule directly, avoiding classify_entailment None drops

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend manifest, loader, and registry for rules entrypoint** - `45a0d91` (feat)
2. **Task 2: Add sh:rule entailment type and SHACL rules execution** - `3b33399` (feat)

## Files Created/Modified
- `backend/app/models/manifest.py` - Added optional rules field to ManifestEntrypoints with placeholder resolution
- `backend/app/models/loader.py` - Added load_rdf_file() and rules field to ModelArchive
- `backend/app/models/registry.py` - Added rules property to ModelGraphs, included in all_graphs
- `backend/app/inference/entailments.py` - Added sh:rule to ENTAILMENT_TYPES and shacl_rules mapping
- `backend/app/inference/service.py` - Added _load_rules_graphs() and SHACL-AF rules step in run_inference

## Decisions Made
- Format detection by file extension in load_rdf_file: .ttl/.turtle for Turtle (no remote context check needed), .jsonld/.json delegates to load_jsonld_file
- Rule-derived triples are tagged as sh:rule directly in classification step, bypassing classify_entailment heuristics which would return None for them
- TypeError fallback for iterate_rules parameter provides compatibility across pyshacl versions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rules infrastructure ready for 36-02 (test rules with a Mental Model)
- No blockers

---
*Phase: 36-shacl-af-rules*
*Completed: 2026-03-04*

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
