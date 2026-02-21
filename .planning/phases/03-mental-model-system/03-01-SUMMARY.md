---
phase: 03-mental-model-system
plan: 01
subsystem: api
tags: [pydantic, pyyaml, rdflib, json-ld, shacl, sparql, manifest, validation, model-registry]

# Dependency graph
requires:
  - phase: 01-core-data-foundation
    provides: TriplestoreClient, rdflib namespaces, SPARQL query/update
  - phase: 02-semantic-services
    provides: pyshacl dependency, validation patterns, rdflib usage patterns
provides:
  - ManifestSchema Pydantic model with YAML parsing and field validation
  - load_jsonld_file and load_archive for JSON-LD to rdflib Graph loading with remote context detection
  - validate_archive with IRI namespace checking and cross-file reference integrity
  - ModelGraphs named graph IRI generation for model artifacts
  - Registry SPARQL operations (register, unregister, list, write graphs, clear graphs, check user data)
affects: [03-02-basic-pkm, 03-03-model-service, 04-admin-shell]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: [manifest YAML schema validation, JSON-LD archive loading, IRI namespace enforcement, triple-by-triple SPARQL serialization, model registry as named graph]

key-files:
  created:
    - backend/app/models/__init__.py
    - backend/app/models/manifest.py
    - backend/app/models/loader.py
    - backend/app/models/validator.py
    - backend/app/models/registry.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Copied _rdf_term_to_sparql helper into registry.py rather than importing from validation.py to avoid cross-module coupling"
  - "Remote @context URL detection reads raw JSON before rdflib parsing to prevent Docker-environment fetch failures"
  - "Triple-by-triple SPARQL INSERT DATA serialization (not N-Triples) per Research Pitfall 2"

patterns-established:
  - "ManifestSchema: Pydantic model_validator(mode='after') for cross-field validation and placeholder resolution"
  - "ModelGraphs: dataclass with properties for deterministic named graph IRI generation"
  - "ALLOWED_EXTERNAL_NAMESPACES: whitelist pattern for IRI namespace enforcement"

requirements-completed: [MODL-04, MODL-05]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 3 Plan 01: Model Domain Module Summary

**Manifest schema, JSON-LD archive loader, IRI/reference validators, and SPARQL model registry for Mental Model management**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T17:30:00Z
- **Completed:** 2026-02-21T17:34:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ManifestSchema validates YAML manifests with modelId pattern, semantic versioning, namespace enforcement, and entrypoint placeholder resolution
- load_archive loads JSON-LD model files into rdflib Graphs with remote @context URL detection preventing Docker fetch failures
- validate_archive performs IRI namespace checking (with external namespace whitelist) and cross-file reference integrity for ontology-shapes-views-seed consistency
- Model registry provides full CRUD SPARQL operations for installed models with proper literal escaping and named graph management

## Task Commits

Each task was committed atomically:

1. **Task 1: Manifest schema, JSON-LD loader, and archive validators** - `86b1198` (feat)
2. **Task 2: Model registry SPARQL operations** - `611d3d2` (feat)

## Files Created/Modified
- `backend/pyproject.toml` - Added pyyaml>=6.0 dependency
- `backend/app/models/__init__.py` - Package init
- `backend/app/models/manifest.py` - ManifestSchema Pydantic model with YAML parsing, field validation, namespace checking, entrypoint placeholder resolution
- `backend/app/models/loader.py` - JSON-LD file loading, ModelArchive dataclass, remote @context detection
- `backend/app/models/validator.py` - IRI namespace validation, reference integrity checking, ArchiveValidationReport with error/warning separation
- `backend/app/models/registry.py` - ModelGraphs IRI generation, InstalledModel dataclass, register/unregister/list/write/clear/check SPARQL operations

## Decisions Made
- Copied `_rdf_term_to_sparql` helper into registry.py rather than importing from validation.py to avoid cross-module coupling between models and services packages
- Remote @context URL detection implemented by reading raw JSON before rdflib parsing, preventing Docker-environment remote fetch failures (Research Pitfall 1)
- Triple-by-triple SPARQL INSERT DATA serialization used instead of N-Triples bulk format to avoid RDF4J parsing edge cases (Research Pitfall 2)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Model domain module complete with all types, validation, and data access ready for ModelService orchestration (Plan 03)
- Basic PKM starter model (Plan 02) can now be validated against ManifestSchema and ArchiveValidationReport
- Registry SPARQL operations ready for install/remove/list pipelines

## Self-Check: PASSED

- All 5 created files verified on disk
- Commit 86b1198 (Task 1) verified in git log
- Commit 611d3d2 (Task 2) verified in git log

---
*Phase: 03-mental-model-system*
*Completed: 2026-02-21*
