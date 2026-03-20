# S02: Type, Property & Relation Mapping + Preview — Research

**Date:** 2026-03-20

## Summary

This slice adds the mapping wizard steps (3–6) to the Notion import flow: type mapping (database → RDF type), property mapping (CSV column → RDF predicate per type), relation mapping (relation columns → edge predicates), and a preview of sample mapped objects. The pattern is directly mirrored from the Obsidian import wizard — same endpoint structure, same htmx partial-swap navigation, same auto-save-on-change approach. The one novel element is the **relation mapping step** (step 5), which doesn't exist in Obsidian and needs a new template + backend dataclass.

The work is straightforward: extend `models.py` with `MappingConfig`/`TypeMapping`/`PropertyMapping`/`RelationMapping` dataclasses, add ~6 new endpoints to `router.py`, create 4 template partials, and enable the disabled "Continue to Type Mapping" button from S01. No unfamiliar technology.

## Recommendation

Follow the Obsidian mapping pattern exactly. Build in this order:

1. **Models first** — `MappingConfig` with type/property/relation mapping dataclasses + to_dict/from_dict serialization. This is a pure data layer with no dependencies.
2. **Router endpoints** — 4 GET step endpoints + 3 POST auto-save endpoints, using the same `_load_mapping` / `_save_mapping` helper pattern as Obsidian.
3. **Templates** — 4 new partials (type_mapping, property_mapping, relation_mapping, preview), adapted from Obsidian templates with Notion-specific data binding.
4. **Wire scan_results.html** — Enable the "Continue to Type Mapping" button.
5. **Unit tests** — Test MappingConfig serialization round-trip and any mapping logic (e.g. auto-suggest matching).

## Implementation Landscape

### Key Files

**Existing (S01 outputs — modify):**

- `backend/app/notion/models.py` — Add `MappingConfig`, `TypeMapping`, `PropertyMapping`, `RelationMapping` dataclasses with `to_dict()`/`from_dict()` serialization. Follow Obsidian's `models.py` pattern (lines 44–118) but add `relation_mappings` dict keyed by `source_db|source_column`.
- `backend/app/notion/router.py` — Add 7 new endpoints:
  - `GET /{import_id}/step/type-mapping` — step 3, serves type mapping table
  - `GET /{import_id}/step/property-mapping` — step 4, per-type property mapping
  - `GET /{import_id}/step/relation-mapping` — step 5, relation column → edge predicate mapping
  - `GET /{import_id}/step/preview` — step 6, sample mapped objects with properties and edges
  - `POST /{import_id}/mapping/type` — auto-save single type mapping
  - `POST /{import_id}/mapping/property` — auto-save single property mapping
  - `POST /{import_id}/mapping/relation` — auto-save single relation mapping
  - Also needs `_load_mapping()` and `_save_mapping()` helper functions (copy from Obsidian router pattern, lines 270–283).
- `backend/app/templates/notion/partials/scan_results.html` — Change the disabled "Continue to Type Mapping" button to an enabled `hx-get` pointing to the type mapping step endpoint.

**New (create):**

- `backend/app/templates/notion/partials/type_mapping.html` — Table with databases as rows, count/columns summary, select dropdown for target type from `ShapesService.get_types()`. Auto-saves via `hx-post`. Obsidian's `type_mapping.html` is the reference. Key difference: Notion rows are `scan_result.databases` (not `type_groups`), group key is the database name.
- `backend/app/templates/notion/partials/property_mapping.html` — Per-mapped-type sections with CSV columns as rows, select dropdown for target property from `ShapesService.get_form_for_type()`. Reference: Obsidian `property_mapping.html`. Key difference: source data is `db.columns` (not frontmatter keys), and relation-type columns should be excluded here (they're handled in the relation mapping step).
- `backend/app/templates/notion/partials/relation_mapping.html` — New template (no Obsidian equivalent). Table of detected relations with source DB, source column, target DB, and a select for the edge predicate. Predicate options come from installed model shapes (object properties with ranges matching the target type). Also include a "Skip" option and display the match ratio from `DetectedRelation`.
- `backend/app/templates/notion/partials/preview.html` — Per-type sections showing sample rows with mapped property key→value pairs and detected edges. Reference: Obsidian `preview.html`. Key difference: preview reads CSV data from `scan_result.databases[].sample_rows`, not frontmatter from markdown files. Edges shown from relation columns. Standalone pages shown as a separate "Notes" section.

**Dependencies (read-only):**

- `backend/app/services/shapes.py` — `ShapesService.get_types()` returns `[{iri, label}]` for type dropdown. `ShapesService.get_form_for_type(type_iri)` returns `NodeShapeForm` with `.properties` list (each has `.path`, `.name`, `.order`) for property dropdown.
- `backend/app/dependencies.py` — `get_shapes_service` FastAPI dependency.

### Data Model Design

**MappingConfig** structure for Notion (parallels Obsidian but adds relations):

```python
@dataclass
class TypeMapping:
    target_type_iri: str
    target_type_label: str

@dataclass
class PropertyMapping:
    target_property_iri: str
    target_property_label: str
    source: str  # "shacl" or "custom"

@dataclass
class RelationMapping:
    target_predicate_iri: str
    target_predicate_label: str
    target_type_iri: str   # the type of the target objects
    target_type_label: str

@dataclass
class MappingConfig:
    version: int = 1
    type_mappings: dict[str, TypeMapping | None] = field(default_factory=dict)
    # key: database name, value: TypeMapping or None (skip)
    property_mappings: dict[str, dict[str, PropertyMapping | None]] = field(default_factory=dict)
    # key: target_type_iri, value: {column_name: PropertyMapping or None}
    relation_mappings: dict[str, RelationMapping | None] = field(default_factory=dict)
    # key: "source_db|source_column", value: RelationMapping or None (skip)
    standalone_page_type_iri: str | None = None
    standalone_page_type_label: str | None = None
```

The `standalone_page_type_iri` field allows mapping standalone pages to a type (default: Note). This is distinct from database type mappings.

### Type Mapping Logic

The type mapping step shows each database from `scan_result.databases` as a row. Unlike Obsidian (which has type groups from different detection signals), Notion has one row per database — simpler. The group key is just `db.name`.

Additionally, if standalone pages exist, show a separate row for "Standalone Pages" with a type selector (default suggest: Note if available).

### Property Mapping Logic

After type mapping saves, the property mapping step iterates over each mapped type. For each type, it shows the columns from databases mapped to that type. Multiple databases can map to the same type — columns should be merged (union of column names across all databases mapped to that type, same as Obsidian merges frontmatter keys from multiple groups mapped to the same type — see Obsidian `property_mapping_step()` lines 294–330).

**Important:** Columns with `inferred_type == 'relation'` should be excluded from property mapping — they go to the relation mapping step instead.

Auto-suggest: For each column, present SHACL properties from the target type's shape. If a column name matches a property label (case-insensitive), pre-select it.

### Relation Mapping Logic

This is the novel step. Shows each entry from `scan_result.detected_relations` plus any columns with `inferred_type == 'relation'` that weren't caught by the >80% heuristic. For each:

- Source database name + column name (read-only)
- Target database name (from DetectedRelation, read-only)
- Edge predicate selector — populated from object properties in the target type's shape (properties where `sh:class` or `sh:nodeKind sh:IRI` indicates an object reference). Include a "Custom IRI..." option.
- If the target database isn't mapped to a type, show a warning.

### Preview Logic

The preview step reads CSV data directly from `scan_result.databases[].sample_rows` (up to 3–5 per type). For each sample row:
- Show mapped property key→value pairs (apply property mapping to CSV columns)
- Show relation edges (apply relation mapping to relation columns)
- Note whether the row has a matching .md body file

Also preview standalone pages if they're mapped to a type.

### Build Order

1. **T01: Models + router endpoints + scan_results button** — All backend code. Models with MappingConfig dataclasses. 7 new router endpoints. Helper functions. Enable the scan_results button. Unit tests for MappingConfig serialization round-trip.
2. **T02: Templates** — 4 new partials (type_mapping, property_mapping, relation_mapping, preview). Step bar OOB swap pattern. Navigation wiring. This depends on T01's endpoints existing.

Alternatively, this can be a single task since the backend and templates are tightly coupled and both are moderate in size.

### Verification Approach

1. **Unit tests** — MappingConfig to_dict/from_dict round-trip, including relation_mappings. Test with empty mappings, partial mappings, null (skipped) entries.
2. **Syntax check** — All new Python files pass `python -c "import ast; ast.parse(open(f).read())"`.
3. **Template syntax** — All new Jinja2 templates parse without errors (render with mock data).
4. **Browser flow verification** — Upload a Notion ZIP → scan → see results → click "Continue to Type Mapping" → map databases to types → proceed to property mapping → map columns → proceed to relation mapping → configure edges → preview shows sample objects with properties and edges → back/forward navigation works between all steps.
5. **Existing tests pass** — `cd backend && python -m pytest tests/test_notion_scanner.py -v` still passes (no regressions).

## Constraints

- The `scan_trigger.html` uses `fetch()` + `innerHTML` + manual script extraction. Any new partial that injects step bar updates must follow the same OOB swap pattern (include step_bar, then script to move it).
- `ShapesService.get_types()` and `get_form_for_type()` are async and require the `get_shapes_service` FastAPI dependency — all step GET endpoints that need type/property data must accept it as a `Depends()` parameter.
- Mapping config persists as `mapping_config.json` in the import directory (same as Obsidian's pattern). Re-scanning should delete stale mapping config.

## Common Pitfalls

- **Multiple databases mapped to same type** — Property mapping must merge columns from all databases mapped to the same type, deduplicating column names (keep highest non_empty_count). Obsidian handles this for frontmatter keys at lines 294–330 of its router.
- **Relation columns in property mapping** — Must be excluded from property mapping step to avoid double-mapping. Filter by `col.inferred_type == 'relation'` when building property sections.
- **Step bar OOB swap** — Every partial must include the step_bar.html and the inline script to move it from `#import-content` to `#import-container`. Missing this causes step bar duplication (S01 fixed this bug in scan_trigger.html).
- **Lucide icon initialization** — Every partial must end with `<script>if (typeof lucide !== 'undefined') { lucide.createIcons(); }</script>` since partials load via htmx and icons need re-initialization.
