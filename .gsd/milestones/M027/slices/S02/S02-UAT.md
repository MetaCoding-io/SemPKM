# S02: Type, Property & Relation Mapping + Preview — UAT

**Milestone:** M027
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for serialization + live-runtime for browser flow)
- Why this mode is sufficient: Unit tests prove data model correctness; browser verification proves template rendering and wizard navigation. No human judgment required beyond these.

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d` from worktree)
- At least one Mental Model installed (basic-pkm provides type suggestions)
- A Notion-format test ZIP file available (use the synthetic fixture from S01's test suite or create one with a CSV database + standalone .md files)

## Smoke Test

Upload a Notion ZIP → scan → click "Continue to Type Mapping" → type mapping page renders with database rows and type dropdowns. If this works, the full pipeline (S01 scan → S02 mapping) is connected.

## Test Cases

### 1. MappingConfig serialization round-trip (automated)

1. Run `cd backend && uv run python -m pytest tests/test_notion_mapping.py -v`
2. **Expected:** 18/18 tests pass — covering empty config, full config with all mapping types, partial configs, multi-db-same-type merging, all-None entries, standalone page type, individual dataclass field access, from_dict with missing optional fields, and default version

### 2. Existing scanner tests unbroken (automated)

1. Run `cd backend && uv run python -m pytest tests/test_notion_scanner.py -v`
2. **Expected:** 31/31 tests pass — no regressions from S02 changes to models.py or router.py

### 3. Type mapping step renders correctly

1. Upload a Notion ZIP containing at least 2 databases (e.g., "Projects" and "Tasks")
2. Complete scan and wait for results
3. Click "Continue to Type Mapping" button
4. **Expected:** Type mapping page shows:
   - Step bar with step 3 highlighted
   - One row per database with database name, row count, column count badge
   - Type dropdown populated from installed Mental Models (e.g., "Project", "Person", "Note")
   - Standalone pages section (if ZIP contained standalone .md files)

### 4. Type mapping auto-save persists

1. On the type mapping page, select a type for a database (e.g., "Projects" → "Project")
2. Run: `docker exec sempkm-api-1 cat /app/data/imports/notion/*/mapping_config.json`
3. **Expected:** JSON file contains `type_mappings` with the selected database name as key, and the chosen type IRI + label as values

### 5. Property mapping with auto-suggest

1. Map at least one database to a type that has SHACL properties (e.g., map "Tasks" to "Task" from basic-pkm)
2. Click "Next: Property Mapping"
3. **Expected:** Property mapping page shows:
   - Section for each mapped type
   - Column rows with property dropdown pre-selecting matching SHACL properties (e.g., "Status" column pre-selects "Task Status" property)
   - Relation-type columns excluded from display
   - "Custom IRI" option in each dropdown
   - Body mapping note explaining CSV/markdown relationship

### 6. Relation mapping with detected relations

1. Use a ZIP fixture with cross-database relations (e.g., "Tasks" has a column referencing "Projects" titles)
2. Complete type mapping for both databases
3. Navigate to property mapping, then to relation mapping
4. **Expected:** Relation mapping page shows:
   - Detected relations with source DB → target DB names
   - Match percentage badge
   - Edge predicate dropdown populated from target type's SHACL shape properties
   - "Target not mapped" warning badge if target DB wasn't mapped to a type
   - "Skip" option in predicate dropdown

### 7. Preview shows mapping summary

1. Complete type and property mapping
2. Navigate to preview step
3. **Expected:** Preview page shows:
   - Mapping summary table: type name, row count, properties mapped count, edges detected count
   - Sample object cards per type with title and mapped property key-value pairs
   - Standalone pages section (if mapped)
   - Import button present but **disabled** with "Coming in next update" tooltip

### 8. Back/forward navigation preserves state

1. Navigate from type mapping → property mapping → relation mapping → preview
2. Click "Back" on the preview page
3. Continue clicking "Back" through relation mapping → property mapping → type mapping
4. **Expected:** Each step restores previously saved mappings — dropdowns show previously selected values, step bar shows correct active step at each page

### 9. Standalone page type mapping

1. Use a ZIP with standalone .md files (not inside any database folder)
2. On type mapping, select a type for standalone pages (e.g., "Note")
3. **Expected:** Standalone pages row appears separately from database rows, auto-save persists `standalone_page_type_iri` and `standalone_page_type_label` in mapping_config.json

## Edge Cases

### Invalid import_id returns 403

1. Send `GET /browser/notion/FAKE-ID/mapping/type` (manually via curl or browser)
2. **Expected:** HTTP 403 response (import directory doesn't belong to current user or doesn't exist)

### Missing scan_result.json returns 404

1. Create an import directory without running a scan (or delete scan_result.json)
2. Navigate to a mapping step endpoint
3. **Expected:** HTTP 404 response ("Scan results not found")

### Database with no columns

1. Upload a ZIP with an empty CSV database (header row only, no data rows)
2. Navigate through mapping steps
3. **Expected:** Database appears in type mapping with 0 row count. Property mapping for that type shows no columns. Preview shows 0 sample objects for that type.

### All databases skipped

1. On type mapping, leave all databases un-mapped (select "— skip —" or leave default)
2. Navigate to property mapping
3. **Expected:** Property mapping shows "No types mapped yet" message. Relation mapping shows no relations. Preview shows empty summary.

## Failure Signals

- **Template-not-found error (HTTP 500):** One of the 4 partials is missing from `backend/app/templates/notion/partials/`
- **Step bar not updating:** OOB swap script not executing — check for JavaScript errors in browser console
- **Lucide icons not rendering:** `<i data-lucide="...">` elements visible as empty — Lucide re-init script at end of partial not firing
- **Auto-save not persisting:** Check `mapping_config.json` in import directory — if missing, POST endpoint is failing silently
- **Type dropdown empty:** ShapesService.get_types() returning empty — check if Mental Models are installed
- **Property auto-suggest not matching:** Case-sensitivity issue or whitespace in SHACL labels vs column names

## Requirements Proved By This UAT

- NOTION-02 (database→type mapping) — Test cases 3, 4, 5, 6, 7, 9 together prove the full mapping workflow from databases to types to properties to relations to preview
- NOTION-01 (partial) — Mapping wizard is a required step in the ZIP import flow; proven to work but executor not yet connected

## Not Proven By This UAT

- Import execution (NOTION-01 completion) — Import button is disabled; S03 connects the executor
- Relation resolution by title matching (NOTION-03) — Only the mapping configuration UI is proven; actual edge creation happens in S03
- 500+ page import performance — Not testable until S03 executor exists
- E2E Playwright automation — Manual browser verification only; S04 adds automated E2E tests

## Notes for Tester

- The "Continue to Type Mapping" button in scan results is an `hx-get` — it loads the type mapping partial into the wizard area without a full page reload
- Auto-save fires on every dropdown `change` event — you don't need to click a Save button
- Property auto-suggest only pre-selects the dropdown visually; it doesn't fire the auto-save. To persist a pre-suggested mapping, manually change the dropdown away and back.
- The fixture ZIP from S01's test suite (`backend/tests/` area) can be used for manual testing — it has databases with cross-DB relations
