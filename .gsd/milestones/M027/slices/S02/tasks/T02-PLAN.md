---
estimated_steps: 6
estimated_files: 4
---

# T02: Mapping and preview template partials

**Slice:** S02 — Type, Property & Relation Mapping + Preview
**Milestone:** M027

## Description

Create the 4 Jinja2 template partials that render the mapping wizard steps 3–6: type mapping, property mapping, relation mapping, and preview. Each partial follows the same structural pattern established by S01's `scan_results.html` and the Obsidian importer's mapping templates: step bar OOB swap at top, content section, navigation buttons at bottom, Lucide icon re-initialization.

The Obsidian templates at `backend/app/templates/obsidian/partials/` are the direct reference — adapt them for Notion's data model (databases instead of type groups, CSV columns instead of frontmatter keys, relation columns as a new step).

## Steps

1. **Create `backend/app/templates/notion/partials/type_mapping.html`** (step 3):
   - Step bar include: `{% set current_step = 3 %}` + `{% include "notion/partials/step_bar.html" %}` + OOB swap script (same pattern as `scan_results.html`)
   - Section heading: "Map Database Types" with `<i data-lucide="layers">` icon
   - Help text explaining the mapping step
   - Table with columns: Database, Rows, Columns, Map To
   - One row per `scan_result.databases`: database name (with expandable details showing column list), row count, column count badge, select dropdown populated from `available_types` (each option `value="{{ t.iri }}"` with label `{{ t.label }}`). Pre-select if `mapping_config.type_mappings.get(db.name)` has a match. Skip option is `<option value="">-- Skip --</option>`.
   - Auto-save: `hx-post="/browser/notion/{{ import_id }}/mapping/type"` with `hx-vals='{"db_name": "{{ db.name }}"}'`, `hx-swap="none"`, `hx-trigger="change"`. The select also needs a hidden `<input>` or `onchange` handler to include the selected option's text as `target_label` — use `onchange="this.nextElementSibling.value = this.options[this.selectedIndex].text"` with a sibling `<input type="hidden" name="target_label">`.
   - If `scan_result.standalone_pages` is non-empty, add a separate row below the table for "Standalone Pages ({{ count }})" with its own type dropdown. Auto-save to `POST /{import_id}/mapping/standalone-type`.
   - Navigation: Back → scan results (`hx-get="/browser/notion/{{ import_id }}/results"`, `hx-target="#import-content"`), Next → property mapping (`hx-get="/browser/notion/{{ import_id }}/step/property-mapping"`)
   - End with Lucide re-init: `<script>if (typeof lucide !== 'undefined') { lucide.createIcons(); }</script>`

2. **Create `backend/app/templates/notion/partials/property_mapping.html`** (step 4):
   - Step bar include with `current_step = 4` + OOB swap script
   - Section heading: "Map Properties" with `<i data-lucide="settings-2">` icon
   - Help text: "For each mapped type, choose which RDF property each CSV column should become."
   - For each `type_iri, type_info in type_sections.items()`:
     - Sub-heading: `{{ type_info.label }}`
     - Note about body content: "CSV row data will be imported as properties. Matching .md files will provide the object body."
     - Table: Column Name, Non-Empty Count, Sample Values, Map To
     - One row per column in `type_info.columns`. Pre-select if `mapping_config.property_mappings.get(type_iri, {}).get(col_name)` matches a SHACL property path. Add auto-suggest: if a column name matches a property label (case-insensitive), pre-select it in the initial render.
     - Select dropdown: Skip option, then SHACL properties from `type_info.properties` (each with `value="{{ prop.path }}"` and label `{{ prop.name }}`), then "Custom IRI..." option
     - Custom IRI input: hidden `<input>` that shows on "Custom IRI..." selection (same pattern as Obsidian's `toggleCustomIri` JS function)
     - Auto-save: `hx-post="/browser/notion/{{ import_id }}/mapping/property"` with `hx-vals='{"type_iri": "{{ type_iri }}", "column_name": "{{ col.name }}"}'`
   - Navigation: Back → type mapping, Next → relation mapping
   - Include `toggleCustomIri` JS function and Lucide re-init

3. **Create `backend/app/templates/notion/partials/relation_mapping.html`** (step 5):
   - Step bar include with `current_step = 5` + OOB swap script
   - Section heading: "Map Relations" with `<i data-lucide="git-branch">` icon
   - Help text: "Configure how detected cross-database relations should become typed edges."
   - If `relation_entries` is empty: show info message "No relations detected between mapped databases."
   - Otherwise, table: Source Database, Column, Target Database, Match %, Edge Predicate
   - One row per relation entry:
     - Source DB name (read-only), column name (read-only), target DB name (read-only)
     - Match ratio as percentage badge
     - If `entry.warning` (target DB not mapped): show amber warning badge "Target not mapped"
     - Select dropdown for edge predicate: Skip option, then object properties from target type's shape (from `entry.available_predicates`, each with `value="{{ pred.path }}"` and label `{{ pred.name }}`), then "Custom IRI..." option with the same `toggleCustomIri` pattern
     - Pre-select if `mapping_config.relation_mappings.get(relation_key)` has a match
     - Auto-save: `hx-post="/browser/notion/{{ import_id }}/mapping/relation"` with `hx-vals` including the `relation_key` ("source_db|source_column" format)
   - Navigation: Back → property mapping, Next → preview
   - Lucide re-init

4. **Create `backend/app/templates/notion/partials/preview.html`** (step 6):
   - Step bar include with `current_step = 6` + OOB swap script
   - If `previews` is empty: show info message "No types are mapped. Go back to type mapping to map at least one database."
   - Otherwise:
     - Mapping summary table: Type, Sample Rows, Properties Mapped, Edges Detected
     - Per-type sample cards: for each preview type, show up to 3 sample rows as cards
       - Card title: first column value (the title/name)
       - Property key-value list: mapped column → value pairs
       - Edge indicators: relation column → target title with edge predicate label
       - Body indicator: "Has .md body" if the row has a matching markdown file
     - If standalone pages are mapped, show a separate "Standalone Pages" section with up to 3 sample page titles
   - Navigation: Back → relation mapping, Next → "Import" button. The Import button should be disabled with `title="Coming in next update"` (S03 will enable it) — `hx-post="/browser/notion/{{ import_id }}/execute"` with `disabled` attribute.
   - Lucide re-init

5. **Verify all templates parse without Jinja2 errors** by checking syntax and ensuring all variable references match what T01's endpoints provide:
   - `type_mapping.html` uses: `scan_result.databases`, `mapping_config`, `available_types`, `import_id`
   - `property_mapping.html` uses: `type_sections` (dict of `{label, properties, columns}`), `mapping_config`, `import_id`
   - `relation_mapping.html` uses: `relation_entries` (list of dicts with `source_db_name`, `source_column`, `target_db_name`, `match_ratio`, `warning`, `available_predicates`, `relation_key`), `mapping_config`, `import_id`
   - `preview.html` uses: `previews` (list of dicts with `type_label`, `rows` each having `title`, `properties`, `edges`, `has_body`), `standalone_previews`, `import_id`

6. **Browser verification** against running Docker stack:
   - Upload a Notion ZIP fixture → scan → verify "Continue to Type Mapping" button is now clickable
   - Click through type mapping → property mapping → relation mapping → preview
   - Verify step bar updates at each step
   - Verify auto-save fires on select change (check `mapping_config.json` via docker exec)
   - Verify back navigation returns to previous steps without losing saved mappings

## Must-Haves

- [ ] All 4 template partials render without Jinja2 errors
- [ ] Step bar OOB swap pattern present in every partial (step bar moves from `#import-content` to `#import-container`)
- [ ] Lucide icon re-initialization at the end of every partial
- [ ] Auto-save on dropdown change works for all 3 mapping types
- [ ] Type mapping shows one row per database + standalone pages row
- [ ] Property mapping excludes relation-type columns and shows per-type sections
- [ ] Relation mapping shows detected relations with target warnings
- [ ] Preview shows sample data with properties and edge indicators
- [ ] Back/Next navigation works between all steps

## Verification

- All 4 template files exist under `backend/app/templates/notion/partials/`
- Browser flow: scan results → type mapping → property mapping → relation mapping → preview → back to type mapping (full navigation circuit)
- Step bar shows correct active step at each wizard page
- Mapping auto-save: change a type dropdown, then navigate away and back — the selection is preserved
- Preview shows sample data reflecting the mappings configured in prior steps

## Inputs

- `backend/app/notion/router.py` — T01's 7 new endpoints define the template context variables
- `backend/app/templates/notion/partials/scan_results.html` — T01 enabled the button; this task's templates are the targets of that button's `hx-get`
- `backend/app/templates/notion/partials/step_bar.html` — S01's step bar partial (7 steps: Upload, Scan, Types, Properties, Relations, Preview, Import)
- `backend/app/templates/obsidian/partials/type_mapping.html` — reference pattern for type mapping UI (adapt for databases instead of type groups)
- `backend/app/templates/obsidian/partials/property_mapping.html` — reference pattern for property mapping UI (adapt for columns instead of frontmatter keys, add relation column exclusion)
- `backend/app/templates/obsidian/partials/preview.html` — reference pattern for preview UI (adapt for CSV sample rows instead of frontmatter-parsed notes)

## Expected Output

- `backend/app/templates/notion/partials/type_mapping.html` — type mapping wizard step (step 3)
- `backend/app/templates/notion/partials/property_mapping.html` — property mapping wizard step (step 4)
- `backend/app/templates/notion/partials/relation_mapping.html` — relation mapping wizard step (step 5, new — no Obsidian equivalent)
- `backend/app/templates/notion/partials/preview.html` — preview wizard step (step 6)
