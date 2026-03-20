---
id: T01
parent: S02
milestone: M027
provides:
  - MappingConfig, TypeMapping, PropertyMapping, RelationMapping dataclasses with to_dict/from_dict
  - _load_mapping / _save_mapping persistence helpers
  - 4 GET wizard step endpoints (type-mapping, property-mapping, relation-mapping, preview)
  - 4 POST auto-save endpoints (type, property, relation, standalone-type)
  - "Continue to Type Mapping" button enabled in scan_results.html
  - 18 unit tests for MappingConfig serialization round-trip
key_files:
  - backend/app/notion/models.py
  - backend/app/notion/router.py
  - backend/tests/test_notion_mapping.py
  - backend/app/templates/notion/partials/scan_results.html
key_decisions:
  - Notion MappingConfig follows Obsidian pattern but adds relation_mappings dict and standalone_page_type_* fields
  - Property mapping step merges columns from all databases mapped to same type, excluding relation-type columns
  - Relation mapping checks both source and target DB shapes for available edge predicates
patterns_established:
  - Notion mapping persistence as mapping_config.json alongside scan_result.json in import directory
observability_surfaces:
  - mapping_config.json persisted on each auto-save POST — inspectable via cat on import directory
  - logger.debug messages on each save with mapping key and target
  - HTTP 404 / 403 from step endpoints on missing scan results or ownership mismatch
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: MappingConfig models, router endpoints, and unit tests

**Added 4 mapping dataclasses, 8 new router endpoints, persistence helpers, and 18 unit tests for the Notion import mapping wizard backend**

## What Happened

Added `TypeMapping`, `PropertyMapping`, `RelationMapping`, and `MappingConfig` dataclasses to `models.py` following the Obsidian `MappingConfig` pattern but extended with `relation_mappings` dict and `standalone_page_type_iri/label` fields. Both `to_dict()` and `from_dict()` handle None (skip) entries for all mapping types.

Added `_load_mapping()` and `_save_mapping()` helpers to `router.py`, then implemented 4 GET step endpoints (type-mapping at step 3, property-mapping at step 4 with column merging and relation exclusion, relation-mapping at step 5 with SHACL predicate lookup, preview at step 6 with sample object construction) and 4 POST auto-save endpoints (type, property with custom IRI support, relation, standalone-type).

The property mapping step merges columns from all databases mapped to the same type (deduplicating by name, keeping highest non_empty_count) and excludes columns with `inferred_type == 'relation'`. The relation mapping step looks up both source and target DB shapes for edge predicates (properties with `target_class`).

Enabled the "Continue to Type Mapping" button in `scan_results.html` with an `hx-get` to the type-mapping step endpoint.

Wrote 18 unit tests covering empty, full, partial, multi-db-same-type, all-None, and minimal-data configurations.

## Verification

- `cd backend && uv run python -m pytest tests/test_notion_mapping.py -v` — 18/18 passed
- `cd backend && uv run python -m pytest tests/test_notion_scanner.py -v` — 31/31 passed (no regressions)
- `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` — OK
- `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` — OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_notion_mapping.py -v` | 0 | ✅ pass | 4.1s |
| 2 | `uv run python -m pytest tests/test_notion_scanner.py -v` | 0 | ✅ pass | 4.1s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Mapping state:** `cat /app/data/imports/notion/{user_id}/{timestamp}/mapping_config.json` shows current wizard progress
- **Failure signals:** HTTP 404 when `scan_result.json` is missing, HTTP 403 on ownership mismatch — both propagated by FastAPI's default exception handler
- **Debug logging:** Each POST auto-save emits `logger.debug("Saved <type> mapping: ...")` with the mapping key and target

## Deviations

- Added a 4th POST endpoint (`/{import_id}/mapping/standalone-type`) not originally counted in the "3 POST" description but specified in step 4 of the plan. The plan listed it as a sub-item of step 4.
- Relation mapping checks both source and target DB shapes for edge predicates (plan only mentioned target DB). This is more useful since the relation predicate may be defined on either side's shape.

## Known Issues

- GET step endpoints reference template paths (`notion/partials/type_mapping.html`, etc.) that don't exist yet — T02 creates them. Hitting these endpoints before T02 will produce TemplateNotFound errors, which is expected.
- Browser flow verification deferred to T02 when templates exist.

## Files Created/Modified

- `backend/app/notion/models.py` — Added TypeMapping, PropertyMapping, RelationMapping, MappingConfig dataclasses with to_dict/from_dict serialization
- `backend/app/notion/router.py` — Added _load_mapping/_save_mapping helpers, 4 GET step endpoints, 4 POST auto-save endpoints, new imports
- `backend/tests/test_notion_mapping.py` — 18 unit tests for MappingConfig serialization round-trip
- `backend/app/templates/notion/partials/scan_results.html` — Enabled "Continue to Type Mapping" button with hx-get
