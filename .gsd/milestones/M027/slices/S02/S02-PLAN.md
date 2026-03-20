# S02: Type, Property & Relation Mapping + Preview

**Goal:** User can map Notion databases to Mental Model types, map CSV columns to RDF predicates, configure relation columns as typed edges, and preview sample mapped objects — all persisted as `mapping_config.json` ready for S03's executor.
**Demo:** After scanning a Notion ZIP, click "Continue to Type Mapping" → map each database to a type → proceed to property mapping → map columns to SHACL properties → proceed to relation mapping → configure edge predicates → preview shows sample objects with properties and edges → back/forward navigation works between all steps.

## Must-Haves

- `MappingConfig`, `TypeMapping`, `PropertyMapping`, `RelationMapping` dataclasses with `to_dict()`/`from_dict()` round-trip serialization
- 7 new router endpoints: 4 GET step endpoints (type-mapping, property-mapping, relation-mapping, preview) + 3 POST auto-save endpoints (type, property, relation)
- `_load_mapping()` / `_save_mapping()` helper functions persisting `mapping_config.json` alongside `scan_result.json`
- 4 new Jinja2 template partials (type_mapping, property_mapping, relation_mapping, preview) with step bar OOB swap and Lucide icon re-init
- Type mapping: one row per database + optional standalone pages row, dropdown from `ShapesService.get_types()`
- Property mapping: per-mapped-type sections with merged columns from all databases mapped to that type, relation-type columns excluded, auto-suggest from `ShapesService.get_form_for_type()`
- Relation mapping: detected relations with source/target DB, edge predicate selector from target type's shape properties
- Preview: sample rows with mapped property key→value pairs and detected edges
- "Continue to Type Mapping" button in scan_results.html enabled with `hx-get`
- Standalone page type mapping (separate row in type mapping, default suggest: Note)
- Unit tests for MappingConfig serialization round-trip (empty, partial, full, null/skip entries, relation mappings)
- All existing `test_notion_scanner.py` tests still pass

## Proof Level

- This slice proves: integration (mapping UI connected to scan results and ShapesService)
- Real runtime required: yes (browser verification against running Docker stack)
- Human/UAT required: no

## Verification

- `cd backend && uv run python -m pytest tests/test_notion_mapping.py -v` — MappingConfig serialization round-trip tests pass
- `cd backend && uv run python -m pytest tests/test_notion_scanner.py -v` — existing 31 scanner tests still pass
- All new Python files pass `python3 -c "import ast; ast.parse(open(f).read())"`
- Browser flow: upload ZIP → scan → click "Continue to Type Mapping" → type mapping renders with database rows and type dropdowns → save a mapping → proceed to property mapping → columns shown per type → proceed to relation mapping → relation rows shown → proceed to preview → sample objects displayed → back navigation returns to previous steps
- Failure-path: POST to `/browser/notion/{import_id}/mapping/type` with invalid `import_id` returns HTTP 403; GET step endpoint with missing `scan_result.json` returns HTTP 404

## Observability / Diagnostics

- Runtime signals: `mapping_config.json` written to import directory on each auto-save
- Inspection surfaces: `cat /app/data/imports/notion/{user_id}/{timestamp}/mapping_config.json` shows current mapping state
- Failure visibility: HTTP 404 if scan results not found, HTTP 403 if import_id ownership mismatch

## Integration Closure

- Upstream surfaces consumed: `NotionScanResult` from S01 (via `scan_result.json`), `ShapesService.get_types()` and `get_form_for_type()` from platform
- New wiring introduced in this slice: 7 new endpoints on existing `/browser/notion/` router, `mapping_config.json` persistence
- What remains before the milestone is truly usable end-to-end: S03 (two-pass executor consuming `MappingConfig`), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: MappingConfig models, router endpoints, and unit tests** `est:45m`
  - Why: All backend logic for the mapping wizard — dataclasses, endpoint handlers, persistence helpers, auto-save endpoints, and serialization tests. Templates can't work without these.
  - Files: `backend/app/notion/models.py`, `backend/app/notion/router.py`, `backend/tests/test_notion_mapping.py`, `backend/app/templates/notion/partials/scan_results.html`
  - Do: (1) Add `TypeMapping`, `PropertyMapping`, `RelationMapping`, `MappingConfig` dataclasses to `models.py` with `to_dict()`/`from_dict()` following the Obsidian pattern but adding `relation_mappings` and `standalone_page_type_*` fields. (2) Add `_load_mapping()` and `_save_mapping()` helpers to `router.py`. (3) Add 4 GET step endpoints and 3 POST auto-save endpoints. Type mapping merges databases mapped to same type in property mapping step. Property mapping excludes `inferred_type == 'relation'` columns. Relation mapping reads `scan_result.detected_relations`. Preview reads `sample_rows` from scan result. (4) Enable the "Continue to Type Mapping" button in `scan_results.html`. (5) Write unit tests for MappingConfig round-trip serialization.
  - Verify: `cd backend && uv run python -m pytest tests/test_notion_mapping.py tests/test_notion_scanner.py -v` — all pass
  - Done when: 7 new endpoints exist, MappingConfig serializes/deserializes correctly (including edge cases: empty, partial, null entries, relation mappings), scan_results button is enabled

- [ ] **T02: Mapping and preview template partials** `est:45m`
  - Why: The 4 Jinja2 templates that render the mapping wizard steps. Without these, the GET endpoints return template-not-found errors. This is the user-facing piece.
  - Files: `backend/app/templates/notion/partials/type_mapping.html`, `backend/app/templates/notion/partials/property_mapping.html`, `backend/app/templates/notion/partials/relation_mapping.html`, `backend/app/templates/notion/partials/preview.html`
  - Do: (1) Create `type_mapping.html` — table with databases as rows, type dropdown from `available_types`, standalone pages row, auto-save via `hx-post`, step bar OOB swap. (2) Create `property_mapping.html` — per-mapped-type sections with column rows (relation columns excluded), SHACL property dropdown with auto-suggest (case-insensitive name match), Custom IRI option. (3) Create `relation_mapping.html` — detected relations table with source/target DB, edge predicate dropdown from target type shape properties, skip option, match ratio display. (4) Create `preview.html` — per-type sample cards with mapped property k/v pairs and detected edge indicators, standalone pages section. All partials must include step bar OOB swap script and Lucide re-init. Back/Next navigation buttons on every partial.
  - Verify: Browser flow against running Docker stack — full wizard navigation from scan results through all 4 mapping steps and back
  - Done when: All 4 templates render without errors, step bar updates correctly on each step, auto-save persists mappings, navigation works forward and backward

## Files Likely Touched

- `backend/app/notion/models.py`
- `backend/app/notion/router.py`
- `backend/tests/test_notion_mapping.py`
- `backend/app/templates/notion/partials/scan_results.html`
- `backend/app/templates/notion/partials/type_mapping.html`
- `backend/app/templates/notion/partials/property_mapping.html`
- `backend/app/templates/notion/partials/relation_mapping.html`
- `backend/app/templates/notion/partials/preview.html`
