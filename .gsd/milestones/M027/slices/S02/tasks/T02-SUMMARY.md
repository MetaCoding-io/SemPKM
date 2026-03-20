---
id: T02
parent: S02
milestone: M027
provides:
  - type_mapping.html partial — wizard step 3, database → type mapping with auto-save
  - property_mapping.html partial — wizard step 4, CSV columns → RDF properties with auto-suggest and custom IRI
  - relation_mapping.html partial — wizard step 5, cross-database relation → edge predicate mapping
  - preview.html partial — wizard step 6, mapping summary and sample object cards with disabled Import button
key_files:
  - backend/app/templates/notion/partials/type_mapping.html
  - backend/app/templates/notion/partials/property_mapping.html
  - backend/app/templates/notion/partials/relation_mapping.html
  - backend/app/templates/notion/partials/preview.html
key_decisions:
  - Property mapping auto-suggest matches column name to SHACL property label case-insensitively and pre-selects the dropdown
  - Relation mapping custom IRI detection checks if the saved predicate IRI exists in the available_predicates list
patterns_established:
  - All 4 partials follow the same structure: step bar include + OOB swap script + content + mapping-nav + Lucide re-init
  - Auto-save uses hx-post with hx-swap="none" and hx-trigger="change" on select elements, with sibling hidden input for label via onchange handler
observability_surfaces:
  - Template render errors surface as HTTP 500 with TemplateError traceback in docker compose logs
  - Auto-save POST returns empty 200 on success; mapping_config.json in import directory shows current state
  - Lucide re-init script at end of every partial; failed icons visible as unparsed <i> elements in DOM
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Mapping and preview template partials

**Created 4 Jinja2 template partials for Notion import wizard steps 3–6: type mapping, property mapping, relation mapping, and preview — all with step bar OOB swap, auto-save, and back/next navigation**

## What Happened

Created all four mapping wizard template partials adapting the Obsidian importer's patterns for Notion's data model:

**type_mapping.html** (step 3): Renders one table row per database with name (expandable column list), row count, column count badge, and type select dropdown. Includes standalone pages section when present. Auto-save fires on select change via htmx POST with the database name and selected type label forwarded through a sibling hidden input and onchange handler.

**property_mapping.html** (step 4): Groups columns by mapped type, excluding relation-type columns. Auto-suggest pre-selects SHACL properties that match column names case-insensitively. Custom IRI option shows a text input via `toggleCustomIri()` function. Body mapping note per type section explains CSV/md relationship.

**relation_mapping.html** (step 5): New step with no Obsidian equivalent. Shows detected cross-database relations with source/target DB names, column name, match percentage badge, and edge predicate dropdown. Includes "Target not mapped" warning badge when the target DB hasn't been mapped to a type. Custom IRI option for edge predicates.

**preview.html** (step 6): Mapping summary table with per-type row counts, property count, and edge count. Sample object cards per type showing title, mapped property key-value pairs, and relation edge indicators. Standalone pages section when mapped. Import button is present but disabled with "Coming in next update" tooltip — S03 will enable it.

All templates follow the established pattern: step bar include with OOB swap script, Lucide icon re-initialization, and mapping-nav with Back/Next buttons.

## Verification

- All 4 template files parsed without Jinja2 errors via `jinja2.Environment.get_template()`
- Browser flow verified: upload ZIP → scan → "Continue to Type Mapping" → type mapping (databases with type dropdowns) → property mapping (per-type column sections with auto-suggest) → relation mapping (detected relation with match %) → preview (summary table + sample cards + disabled Import) → back navigation all the way to type mapping with mappings preserved
- Auto-save confirmed: set Projects → Project Shape and Tasks → Task Shape, then docker exec cat mapping_config.json showed both mappings persisted
- Step bar showed correct active step at each wizard page (3, 4, 5, 6)
- 18 mapping tests + 31 scanner tests = 49/49 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_notion_mapping.py -v` | 0 | ✅ pass | 13.7s |
| 2 | `uv run python -m pytest tests/test_notion_scanner.py -v` | 0 | ✅ pass | 7.2s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` | 0 | ✅ pass | <1s |
| 5 | Jinja2 template syntax check (all 4 partials) | 0 | ✅ pass | <1s |
| 6 | Browser: full wizard navigation circuit | — | ✅ pass | manual |
| 7 | Browser: auto-save type mapping → mapping_config.json verified | — | ✅ pass | manual |
| 8 | Browser: step bar shows correct active step at each page | — | ✅ pass | manual |
| 9 | Browser: back navigation preserves saved mappings | — | ✅ pass | manual |

## Diagnostics

- **Template render errors:** `docker compose logs api | grep TemplateError` shows Jinja2 failures with full traceback
- **Mapping state:** `docker exec sempkm-api-1 cat /app/data/imports/notion/{user_id}/{timestamp}/mapping_config.json` shows wizard progress
- **Step endpoint failures:** HTTP 404 when scan_result.json missing, HTTP 403 on ownership mismatch
- **Client-side:** Unparsed `<i data-lucide="...">` elements indicate Lucide re-init failure

## Deviations

None — all 4 templates created as specified in the plan.

## Known Issues

- Property auto-suggest pre-selects the dropdown but doesn't fire the auto-save POST, so the pre-suggestion isn't persisted until the user manually changes the dropdown. This is consistent with the Obsidian importer behavior and is a UX enhancement opportunity for a future task.
- The preview shows "0 Properties Mapped" and "0 Edges Detected" when no property/relation auto-save POSTs have been fired — this accurately reflects the persisted mapping state.

## Files Created/Modified

- `backend/app/templates/notion/partials/type_mapping.html` — Type mapping wizard step (step 3) with database rows, type dropdowns, standalone pages section, and auto-save
- `backend/app/templates/notion/partials/property_mapping.html` — Property mapping wizard step (step 4) with per-type column tables, auto-suggest, custom IRI, and auto-save
- `backend/app/templates/notion/partials/relation_mapping.html` — Relation mapping wizard step (step 5) with detected relations, warning badges, edge predicate dropdowns, and auto-save
- `backend/app/templates/notion/partials/preview.html` — Preview wizard step (step 6) with mapping summary, sample object cards, standalone pages section, and disabled Import button
- `.gsd/milestones/M027/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
