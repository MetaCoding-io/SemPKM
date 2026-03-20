---
id: S02
parent: M027
milestone: M027
provides:
  - MappingConfig, TypeMapping, PropertyMapping, RelationMapping dataclasses with to_dict/from_dict serialization
  - 8 new router endpoints (4 GET wizard steps + 4 POST auto-save) for type, property, relation, and standalone-type mapping
  - _load_mapping / _save_mapping persistence helpers writing mapping_config.json alongside scan_result.json
  - 4 Jinja2 template partials (type_mapping, property_mapping, relation_mapping, preview) with step bar OOB swap and Lucide re-init
  - "Continue to Type Mapping" button enabled in scan_results.html
  - Property mapping auto-suggest from ShapesService with case-insensitive label matching
  - Relation mapping with edge predicate selection from SHACL shapes
  - Preview showing mapping summary, sample object cards, and disabled Import button (ready for S03)
  - 18 unit tests for MappingConfig serialization round-trip
requires:
  - slice: S01
    provides: NotionScanResult (databases, columns, relations), scan_result.json persistence, upload/scan/results UI
affects:
  - S03
key_files:
  - backend/app/notion/models.py
  - backend/app/notion/router.py
  - backend/tests/test_notion_mapping.py
  - backend/app/templates/notion/partials/scan_results.html
  - backend/app/templates/notion/partials/type_mapping.html
  - backend/app/templates/notion/partials/property_mapping.html
  - backend/app/templates/notion/partials/relation_mapping.html
  - backend/app/templates/notion/partials/preview.html
key_decisions:
  - MappingConfig follows Obsidian pattern but adds relation_mappings dict and standalone_page_type_iri/label fields
  - Property mapping merges columns from all databases mapped to same type, excluding relation-type columns
  - Relation mapping checks both source AND target DB shapes for available edge predicates
  - Property auto-suggest pre-selects dropdown by case-insensitive column name to SHACL property label match
patterns_established:
  - Notion mapping persistence as mapping_config.json alongside scan_result.json in per-import directory
  - All wizard partials follow the same structure: step bar include + OOB swap script + content + mapping-nav + Lucide re-init
  - Auto-save via hx-post with hx-swap="none" and hx-trigger="change" on select elements
observability_surfaces:
  - mapping_config.json persisted on each auto-save POST — inspectable via cat on import directory
  - logger.debug messages on each save with mapping key and target
  - HTTP 404 from step endpoints when scan_result.json missing, HTTP 403 on ownership mismatch
  - Template render errors surface as HTTP 500 with TemplateError traceback in docker compose logs
  - Unparsed <i data-lucide="..."> elements indicate Lucide re-init failure
drill_down_paths:
  - .gsd/milestones/M027/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M027/slices/S02/tasks/T02-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Type, Property & Relation Mapping + Preview

**Added the complete 4-step mapping wizard (type → property → relation → preview) with auto-save, SHACL-driven suggestions, and stored MappingConfig ready for S03's import executor**

## What Happened

**T01 (backend):** Added 4 mapping dataclasses (`TypeMapping`, `PropertyMapping`, `RelationMapping`, `MappingConfig`) to `models.py` following the Obsidian importer's pattern but extended with `relation_mappings` dict and `standalone_page_type_iri/label` fields for Notion's richer data model. Both `to_dict()` and `from_dict()` handle None (skip) entries for all mapping types. Added `_load_mapping()` and `_save_mapping()` helpers to `router.py`, then implemented 4 GET step endpoints (type-mapping at step 3, property-mapping at step 4, relation-mapping at step 5, preview at step 6) and 4 POST auto-save endpoints (type, property, relation, standalone-type). The property mapping step merges columns from all databases mapped to the same type (deduplicating by name, keeping highest non_empty_count) and excludes relation-type columns. The relation mapping step looks up both source and target DB shapes for edge predicates. Enabled the "Continue to Type Mapping" button in `scan_results.html`. Wrote 18 unit tests covering empty, full, partial, multi-db-same-type, all-None, and minimal-data configurations.

**T02 (templates):** Created all 4 Jinja2 template partials. `type_mapping.html` renders one row per database with name, expandable column list, row count, type select dropdown, and a standalone pages section. `property_mapping.html` groups columns by mapped type with auto-suggest pre-selecting SHACL properties matching column names case-insensitively, plus custom IRI option. `relation_mapping.html` is a new step with no Obsidian equivalent — shows detected cross-database relations with match percentage badges, "target not mapped" warnings, and edge predicate dropdowns. `preview.html` shows mapping summary table, sample object cards per type, and a disabled Import button ("Coming in next update" — S03 enables it). All templates follow the established pattern: step bar include with OOB swap script, Lucide re-init, and mapping-nav with Back/Next buttons.

## Verification

- **Unit tests:** 49/49 passed — 18 MappingConfig serialization tests + 31 existing scanner tests (zero regressions)
- **AST parse:** `models.py` and `router.py` both parse cleanly
- **Template syntax:** All 4 Jinja2 templates parse without errors
- **No conflict markers:** grep across all Notion backend and template files — zero results
- **Browser flow (T02):** Upload ZIP → scan → "Continue to Type Mapping" → type mapping (databases with type dropdowns) → property mapping (per-type column sections with auto-suggest) → relation mapping (detected relations with match %) → preview (summary table + sample cards + disabled Import) → back navigation all the way to type mapping with mappings preserved
- **Auto-save (T02):** Set type mappings, then verified mapping_config.json was persisted via docker exec cat
- **Step bar (T02):** Correct active step indicator at each wizard page (3, 4, 5, 6)

## Requirements Advanced

- NOTION-01 — ZIP import wizard now has complete mapping UI (steps 3–6); missing only the executor (S03) and E2E tests (S04)
- NOTION-02 — Database→type mapping with auto-suggestions from ShapesService fully implemented and browser-verified

## Requirements Validated

- None — NOTION-02 requires end-to-end import execution to validate (S03 dependency)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Added a 4th POST endpoint (`/{import_id}/mapping/standalone-type`) not counted in the original "3 POST" description — the plan specified it as a sub-item but it's a separate route
- Relation mapping checks both source AND target DB shapes for edge predicates — plan only mentioned target DB. This is more useful since the relation predicate may be defined on either side's shape.

## Known Limitations

- Property auto-suggest pre-selects the dropdown but doesn't fire the auto-save POST, so pre-suggestions aren't persisted until the user manually changes the dropdown. Consistent with Obsidian importer behavior — UX enhancement opportunity for a future iteration.
- Preview shows "0 Properties Mapped" and "0 Edges Detected" when no property/relation auto-save POSTs have been fired — accurately reflects the persisted mapping state.
- Import button on preview page is disabled — S03 will enable it and wire the executor.

## Follow-ups

- S03 must consume `mapping_config.json` to execute the two-pass import (objects + relations)
- S03 must enable the Import button on the preview page and connect it to the executor endpoint

## Files Created/Modified

- `backend/app/notion/models.py` — Added TypeMapping, PropertyMapping, RelationMapping, MappingConfig dataclasses with to_dict/from_dict
- `backend/app/notion/router.py` — Added _load_mapping/_save_mapping helpers, 4 GET step endpoints, 4 POST auto-save endpoints
- `backend/tests/test_notion_mapping.py` — 18 unit tests for MappingConfig serialization round-trip
- `backend/app/templates/notion/partials/scan_results.html` — Enabled "Continue to Type Mapping" button with hx-get
- `backend/app/templates/notion/partials/type_mapping.html` — Type mapping wizard step (step 3)
- `backend/app/templates/notion/partials/property_mapping.html` — Property mapping wizard step (step 4) with auto-suggest
- `backend/app/templates/notion/partials/relation_mapping.html` — Relation mapping wizard step (step 5)
- `backend/app/templates/notion/partials/preview.html` — Preview wizard step (step 6) with disabled Import button

## Forward Intelligence

### What the next slice should know
- `MappingConfig` is loaded from `mapping_config.json` via `_load_mapping(import_dir)` — the executor should use this same helper
- The preview page has a disabled Import button (`#start-import-btn`) — S03 needs to remove the `disabled` attribute and add `hx-post` to the executor endpoint
- Sample rows are stored in `scan_result.json` under each database's `sample_rows` field — the executor reads actual CSV data, not samples
- Standalone pages are mapped separately via `standalone_page_type_iri/label` on MappingConfig — the executor must handle them as a distinct pass

### What's fragile
- Auto-save relies on `onchange` firing JavaScript that sets sibling hidden inputs for labels — if template structure changes (e.g., wrapper elements added), the `previousElementSibling` / `nextElementSibling` selectors break
- Property auto-suggest pre-selection uses `Array.from(select.options).find(o => o.text.toLowerCase() === name.toLowerCase())` — any whitespace or encoding differences in SHACL labels vs column names will miss

### Authoritative diagnostics
- `cat /app/data/imports/notion/{user_id}/{timestamp}/mapping_config.json` — shows exact mapping state as persisted by auto-save
- `docker compose logs api | grep "Saved .* mapping"` — shows debug-level auto-save events with keys and targets
- `docker compose logs api | grep TemplateError` — catches any Jinja2 rendering failures

### What assumptions changed
- The plan described "3 POST auto-save endpoints" but 4 were needed (standalone-type is a separate route)
- Relation mapping benefits from checking both source AND target DB shapes, not just target — this was discovered during implementation
