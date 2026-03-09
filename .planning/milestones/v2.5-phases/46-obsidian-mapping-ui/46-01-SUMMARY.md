---
phase: 46-obsidian-mapping-ui
plan: 01
subsystem: obsidian-import
tags: [backend, models, router, mapping-wizard]
dependency_graph:
  requires: []
  provides: [MappingConfig-model, per-group-frontmatter-keys, mapping-wizard-endpoints]
  affects: [obsidian-scanner, obsidian-router]
tech_stack:
  added: []
  patterns: [dataclass-serialization, htmx-partial-endpoints, auto-save-pattern]
key_files:
  created: []
  modified:
    - backend/app/obsidian/models.py
    - backend/app/obsidian/scanner.py
    - backend/app/obsidian/router.py
decisions:
  - MappingConfig uses pipe-delimited group keys (type_name|signal_source) for type_mappings dict
  - Property mappings keyed by target_type_iri to support many-to-one group merging
  - Preview step re-reads frontmatter from disk for accurate sample transformations
metrics:
  duration_minutes: 4
  completed: "2026-03-08"
---

# Phase 46 Plan 01: Backend Models and Mapping Endpoints Summary

MappingConfig/TypeMapping/PropertyMapping dataclasses with full round-trip serialization, per-group frontmatter key tracking in scanner, and 5 wizard step + auto-save router endpoints.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Add MappingConfig model and per-group frontmatter keys | 821554d | TypeMapping/PropertyMapping/MappingConfig dataclasses, NoteTypeGroup.frontmatter_keys field, scanner per-group key tracking, stale mapping deletion on re-scan |
| 2 | Add wizard step and auto-save router endpoints | 20cd801 | 3 GET step endpoints (type-mapping, property-mapping, preview), 2 POST auto-save endpoints, ShapesService injection, helper functions |

## Verification Results

- MappingConfig round-trip serialization: PASSED (None values, nested dicts)
- NoteTypeGroup per-group frontmatter_keys: PASSED
- All 5 router endpoints defined with correct paths: PASSED
- ShapesService injected for mapping endpoints: PASSED
- AST parse of router.py: PASSED (no syntax errors)

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Pipe-delimited group keys**: Type mappings use `type_name|signal_source` as dict key for unique identification of note type groups
2. **Many-to-one merging**: Property mapping step merges frontmatter keys from all groups mapped to the same RDF type (union keys, sum counts, combine samples)
3. **Preview re-reads from disk**: Preview step loads actual note files via python-frontmatter for accurate sample output rather than relying on cached data

## Self-Check: PASSED
