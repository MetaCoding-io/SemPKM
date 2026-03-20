---
estimated_steps: 7
estimated_files: 4
---

# T01: MappingConfig models, router endpoints, and unit tests

**Slice:** S02 — Type, Property & Relation Mapping + Preview
**Milestone:** M027

## Description

Add the complete backend layer for the Notion mapping wizard: 4 new dataclasses (`TypeMapping`, `PropertyMapping`, `RelationMapping`, `MappingConfig`) with JSON serialization, 7 new router endpoints (4 GET step pages + 3 POST auto-save), persistence helpers, and unit tests. Also enable the "Continue to Type Mapping" button from S01's scan_results.html. This task does NOT create templates — endpoints will reference template paths that T02 creates.

## Steps

1. **Add mapping dataclasses to `backend/app/notion/models.py`:**
   - `TypeMapping` — `target_type_iri: str`, `target_type_label: str`
   - `PropertyMapping` — `target_property_iri: str`, `target_property_label: str`, `source: str` (values: "shacl" or "custom")
   - `RelationMapping` — `target_predicate_iri: str`, `target_predicate_label: str`, `target_type_iri: str`, `target_type_label: str`
   - `MappingConfig` — `version: int = 1`, `type_mappings: dict[str, TypeMapping | None]` (key = database name), `property_mappings: dict[str, dict[str, PropertyMapping | None]]` (outer key = target_type_iri, inner key = column_name), `relation_mappings: dict[str, RelationMapping | None]` (key = "source_db|source_column"), `standalone_page_type_iri: str | None = None`, `standalone_page_type_label: str | None = None`
   - Implement `to_dict()` and `from_dict()` on `MappingConfig` following the Obsidian `MappingConfig` pattern in `backend/app/obsidian/models.py` (lines 44–118). Key difference: add `relation_mappings` dict and `standalone_page_type_*` fields.

2. **Add `_load_mapping()` and `_save_mapping()` helpers to `backend/app/notion/router.py`:**
   - `_load_mapping(import_dir: Path) -> MappingConfig` — reads `mapping_config.json`, returns empty `MappingConfig()` if missing
   - `_save_mapping(import_dir: Path, config: MappingConfig) -> None` — writes `mapping_config.json`
   - Follow the Obsidian router pattern exactly (lines 322–331 of `backend/app/obsidian/router.py`)

3. **Add 4 GET step endpoints to `router.py`:**
   - Add new imports at top: `from fastapi import Form`, `from app.dependencies import get_shapes_service`, `from app.services.shapes import ShapesService`
   - `GET /{import_id}/step/type-mapping` (current_step=3): Load scan_result + mapping_config + `ShapesService.get_types()`. Pass `scan_result`, `mapping_config`, `available_types`, `import_id`, `current_step=3` to template `notion/partials/type_mapping.html`
   - `GET /{import_id}/step/property-mapping` (current_step=4): Load scan_result + mapping_config. Build `type_sections` dict: for each mapped type, merge columns from ALL databases mapped to that type (dedup by column name, keep highest `non_empty_count`). EXCLUDE columns where `col.inferred_type == 'relation'`. For each type, get SHACL properties via `shapes_service.get_form_for_type(type_iri)`. Pass `type_sections`, `mapping_config`, `import_id`, `current_step=4` to template.
   - `GET /{import_id}/step/relation-mapping` (current_step=5): Load scan_result + mapping_config. Build `relation_entries` list from `scan_result.detected_relations`. For each relation, look up the target DB's mapped type IRI from mapping_config to get available edge predicates from `shapes_service.get_form_for_type()` (filter to properties where `target_class` is not None — these are object properties suitable for edges). If target DB isn't mapped, include an empty predicate list and a `warning: true` flag. Pass `relation_entries`, `mapping_config`, `import_id`, `current_step=5` to template.
   - `GET /{import_id}/step/preview` (current_step=6): Load scan_result + mapping_config. Build `previews` list: for each mapped database, take up to 3 `sample_rows`. For each row, apply property mapping (column_name → mapped property label + value) and relation mapping (relation column → edge label + value). Also build standalone_pages preview if `standalone_page_type_iri` is set. Pass `previews`, `import_id`, `current_step=6` to template.

4. **Add 3 POST auto-save endpoints to `router.py`:**
   - `POST /{import_id}/mapping/type` — Form params: `db_name`, `target_type` (IRI or empty for skip), `target_label`. Saves to `config.type_mappings[db_name]`. Return `HTMLResponse("")`.
   - `POST /{import_id}/mapping/property` — Form params: `type_iri`, `column_name`, `target_property` (IRI, "__custom__", or empty for skip), `property_label`, `source` (default "shacl"). If `target_property == "__custom__"`, also read `custom_iri` form field. Saves to `config.property_mappings[type_iri][column_name]`. Return `HTMLResponse("")`.
   - `POST /{import_id}/mapping/relation` — Form params: `relation_key` ("source_db|source_column" format), `target_predicate` (IRI or empty for skip), `predicate_label`, `target_type_iri`, `target_type_label`. Saves to `config.relation_mappings[relation_key]`. Return `HTMLResponse("")`.
   - Also add `POST /{import_id}/mapping/standalone-type` for standalone page type mapping — Form params: `target_type`, `target_label`. Saves to `config.standalone_page_type_iri` and `config.standalone_page_type_label`.

5. **Enable "Continue to Type Mapping" button in `backend/app/templates/notion/partials/scan_results.html`:**
   - Change the disabled button to:
     ```html
     <button class="btn btn-primary"
             hx-get="/browser/notion/{{ import_id }}/step/type-mapping"
             hx-target="#import-content"
             hx-swap="innerHTML">
         <i data-lucide="arrow-right"></i>
         Continue to Type Mapping
     </button>
     ```
   - Remove `disabled` attribute and `title="Available in the next step"`

6. **Write unit tests in `backend/tests/test_notion_mapping.py`:**
   - Test `MappingConfig.to_dict()` → `MappingConfig.from_dict()` round-trip with:
     - Empty config (all defaults)
     - Full config with type_mappings, property_mappings, relation_mappings, standalone_page_type
     - Partial config (some mappings, some None/skip entries)
     - Config with multiple databases mapped to same type
     - Config with relation_mappings including None (skip) entries
     - Verify `version` field preserved
   - Test `TypeMapping`, `PropertyMapping`, `RelationMapping` individual serialization edge cases

7. **Verify no regressions:**
   - Run `cd backend && uv run python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v`
   - Syntax-check all modified files: `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"`

## Must-Haves

- [ ] `MappingConfig` with `type_mappings`, `property_mappings`, `relation_mappings`, `standalone_page_type_*` fields
- [ ] `to_dict()` / `from_dict()` round-trip works for all field combinations including None entries
- [ ] 7 new endpoints on `/browser/notion/` router
- [ ] Property mapping step merges columns from multiple databases mapped to same type
- [ ] Property mapping step excludes columns with `inferred_type == 'relation'`
- [ ] Relation mapping step uses target type's shape properties for predicate suggestions
- [ ] "Continue to Type Mapping" button enabled with `hx-get`
- [ ] All unit tests pass
- [ ] Existing 31 scanner tests still pass

## Verification

- `cd backend && uv run python -m pytest tests/test_notion_mapping.py -v` — all MappingConfig tests pass
- `cd backend && uv run python -m pytest tests/test_notion_scanner.py -v` — all 31 scanner tests still pass
- `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` — no syntax errors

## Inputs

- `backend/app/notion/models.py` — existing S01 dataclasses (NotionScanResult, NotionDatabase, etc.)
- `backend/app/notion/router.py` — existing S01 router with 6 endpoints
- `backend/app/obsidian/models.py` — reference implementation for MappingConfig (lines 44–118)
- `backend/app/obsidian/router.py` — reference implementation for step endpoints and auto-save (lines 322–700)
- `backend/app/services/shapes.py` — `ShapesService.get_types()` returns `[{iri, label}]`, `get_form_for_type(type_iri)` returns `NodeShapeForm` with `.properties` list (each has `.path`, `.name`, `.target_class`, `.order`)
- `backend/app/dependencies.py` — `get_shapes_service` FastAPI dependency (line 78)
- `backend/app/templates/notion/partials/scan_results.html` — has disabled "Continue to Type Mapping" button to enable

## Expected Output

- `backend/app/notion/models.py` — extended with 4 new dataclasses (`TypeMapping`, `PropertyMapping`, `RelationMapping`, `MappingConfig`) and serialization methods
- `backend/app/notion/router.py` — extended with `_load_mapping`, `_save_mapping`, 4 GET step endpoints, 4 POST auto-save endpoints (3 mapping + 1 standalone type)
- `backend/tests/test_notion_mapping.py` — ~8-12 unit tests for MappingConfig serialization round-trip
- `backend/app/templates/notion/partials/scan_results.html` — "Continue to Type Mapping" button enabled with `hx-get`
