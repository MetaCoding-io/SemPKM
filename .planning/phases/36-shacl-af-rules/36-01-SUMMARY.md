---
phase: 36-shacl-af-rules
plan: 01
subsystem: inference
tags: [shacl, pyshacl, rdflib, owl2rl, rules-engine]

requires:
  - phase: 35-owl2-rl-inference
    provides: OWL 2 RL inference pipeline with entailment classification
provides:
  - SHACL-AF rules loading infrastructure (manifest, loader, registry)
  - SHACL-AF rule execution step in inference pipeline via pyshacl.shacl_rules()
  - sh:rule entailment type for rule-derived triple classification
affects: [36-02, inference-ui, model-authoring]

tech-stack:
  added: [pyshacl.shacl_rules]
  patterns: [load_rdf_file format detection by extension, rule-derived triple tagging]

key-files:
  created: []
  modified:
    - backend/app/models/manifest.py
    - backend/app/models/loader.py
    - backend/app/models/registry.py
    - backend/app/inference/entailments.py
    - backend/app/inference/service.py

key-decisions:
  - "Format detection by file extension in load_rdf_file (.ttl for Turtle, .jsonld for JSON-LD)"
  - "Rule-derived triples tagged as sh:rule directly, bypassing classify_entailment heuristics"
  - "TypeError fallback for iterate_rules parameter in pyshacl compatibility"

patterns-established:
  - "load_rdf_file: multi-format RDF loading with extension-based dispatch"
  - "Rule triple tracking: pre/post set diff to identify SHACL-derived triples"

requirements-completed: [INF-02]

duration: 2min
completed: 2026-03-04
---

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
