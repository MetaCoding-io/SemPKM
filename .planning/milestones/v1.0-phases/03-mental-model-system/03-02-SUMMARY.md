---
phase: 03-mental-model-system
plan: 02
subsystem: models
tags: [owl, shacl, json-ld, rdf, skos, foaf, dcterms, schema-org, seed-data, view-specs]

# Dependency graph
requires:
  - phase: 03-mental-model-system
    provides: ManifestSchema validation, load_archive, validate_archive
provides:
  - Basic PKM starter model with 4 OWL types (Project, Person, Note, Concept)
  - SHACL NodeShapes with form generation hints (sh:order, sh:group, sh:in, sh:defaultValue)
  - View specs for table, card, and graph renderers per type
  - Interconnected seed data with 11 example objects
affects: [03-03-model-service, 05-renderers]

# Tech tracking
tech-stack:
  added: []
  patterns: [JSON-LD with inline @context, OWL ontology with standard vocabularies, SHACL sh:PropertyGroup for form layout, sempkm:ViewSpec for renderer config, SPARQL queries in view spec literals]

key-files:
  created:
    - models/basic-pkm/manifest.yaml
    - models/basic-pkm/ontology/basic-pkm.jsonld
    - models/basic-pkm/shapes/basic-pkm.jsonld
    - models/basic-pkm/views/basic-pkm.jsonld
    - models/basic-pkm/seed/basic-pkm.jsonld
  modified: []

key-decisions:
  - "All JSON-LD uses inline @context only — no remote URLs to avoid Docker fetch failures"
  - "Standard vocabularies (FOAF, Dublin Core, Schema.org, SKOS) used for well-known property semantics, bpkm: namespace for model-specific terms"
  - "SPARQL queries in view specs use full IRIs since they are stored as string literals"
  - "Seed data uses bpkm:seed- prefixed IRIs to distinguish from user-created data"

patterns-established:
  - "Model archive structure: manifest.yaml + ontology/ + shapes/ + views/ + seed/ directories"
  - "sh:PropertyGroup for form section grouping with sh:order for layout"
  - "sempkm:ViewSpec with rendererType, sparqlQuery, columns for renderer configuration"

requirements-completed: [MODL-06]

# Metrics
duration: 8min
completed: 2026-02-21
---

# Phase 3 Plan 02: Basic PKM Starter Model Summary

**OWL ontology with 4 types and 40+ properties, SHACL shapes with form hints, 12 view specs, and 11 interconnected seed objects**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-21T17:30:00Z
- **Completed:** 2026-02-21T17:38:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Manifest YAML with modelId, version, namespace, prefixes, and entrypoint paths
- OWL ontology defining Project, Person, Note, Concept with 40+ properties across standard vocabularies (FOAF, Dublin Core, Schema.org, SKOS) plus model-specific object properties for inter-type relationships
- 4 SHACL NodeShapes (365 triples) with sh:property, sh:order, sh:group, sh:name, sh:datatype/sh:class, sh:in, sh:defaultValue for form generation
- 12 ViewSpecs (76 triples) covering table, card, and graph renderers for each type with SPARQL queries
- 11 seed objects (90 triples): 2 Projects, 3 People, 3 Notes, 3 Concepts with cross-type relationships wired

## Task Commits

Each task was committed atomically:

1. **Task 1: Manifest and ontology with four types** - `5d8e6a1` (feat)
2. **Task 2: SHACL shapes, view specs, and seed data** - `bfad26b` (feat)

## Files Created/Modified
- `models/basic-pkm/manifest.yaml` - Model metadata with basic-pkm identity, namespace, and entrypoints
- `models/basic-pkm/ontology/basic-pkm.jsonld` - 4 OWL classes with 65 triples defining types and properties
- `models/basic-pkm/shapes/basic-pkm.jsonld` - 4 NodeShapes with 365 triples, property groups, constraints, and defaults
- `models/basic-pkm/views/basic-pkm.jsonld` - 12 ViewSpecs with 76 triples for table/card/graph rendering
- `models/basic-pkm/seed/basic-pkm.jsonld` - 11 seed objects with 90 triples demonstrating linked data

## Decisions Made
- All JSON-LD files use inline @context only — no remote context URLs to prevent Docker network fetch failures
- Standard vocabularies (FOAF, Dublin Core, Schema.org, SKOS) used for well-known property semantics; bpkm: namespace for model-specific properties
- SPARQL queries in view specs use full IRIs (`<urn:sempkm:model:basic-pkm:Project>`) since queries are stored as string literals
- Seed data IRIs use `bpkm:seed-` prefix to be distinguishable from user-created data

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete model archive ready for ModelService install pipeline (Plan 03)
- Manifest validates against ManifestSchema from Plan 01
- All RDF files verified to parse cleanly via rdflib with correct namespace and reference integrity
- docker-compose.yml updated to mount models/ directory into api container

## Self-Check: PASSED

- All 5 model files verified on disk
- All JSON-LD files parse without errors (365 + 76 + 90 + 65 triples)
- Shapes target valid ontology classes (4/4)
- Seed data uses valid ontology types (4/4)
- Inline @context only — no remote URLs
- Commit 5d8e6a1 (Task 1) verified in git log
- Commit bfad26b (Task 2) verified in git log

---
*Phase: 03-mental-model-system*
*Completed: 2026-02-21*
