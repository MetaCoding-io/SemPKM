---
estimated_steps: 11
estimated_files: 19
skills_used: []
---

# T02: Deduplicate Notion/Obsidian importer templates into shared partials

Create shared importer partials at `backend/app/templates/importer/partials/` for near-identical templates between Notion and Obsidian importers. Each shared template uses context variables (`importer_name`, `url_prefix`, `steps`, `file_input_id`, `upload_hint`, etc.) passed from the Python view routers.

**Templates to share** (currently duplicated with only label/URL/ID differences):
- `step_bar.html` — differs in step count (7 vs 6) and step labels. Parametrize via `steps` list of tuples.
- `upload_form.html` — differs in labels, input IDs, URL prefix. Parametrize via `url_prefix`, `file_input_id`, `upload_title`, `upload_hint`.
- `scan_trigger.html` — differs in labels, URL prefix, one Notion-only script block. Parametrize via `url_prefix`, `importer_name`. Use `{% if %}` for Notion-only section.
- `import_progress.html` — differs in step number and step_bar include. Parametrize via `progress_step`, re-include shared step_bar.
- `import_summary.html` — mostly similar, Notion has extra relation_mapping stats. Parametrize, use `{% if %}` for Notion-only block.

**Templates staying importer-specific:** scan_results.html, preview.html, type_mapping.html, property_mapping.html (too structurally different). Notion's relation_mapping.html stays Notion-only.

**Python router changes:** Each view function that renders an importer template must add the shared context variables to its template context dict. Notion router uses `url_prefix="/browser/notion"`, Obsidian uses `url_prefix="/browser/import"`.

**import.html changes:** Both `notion/import.html` and `obsidian/import.html` switch their `{% include %}` paths from importer-specific to shared for the 5 deduplicated partials. The old importer-specific copies of deduplicated partials can be deleted.

**Important:** T01 will have already fixed the `.append()` hack in scan_results.html for both importers. Those scan_results templates remain importer-specific in this task.

## Inputs

- `backend/app/templates/notion/import.html`
- `backend/app/templates/notion/partials/step_bar.html`
- `backend/app/templates/notion/partials/upload_form.html`
- `backend/app/templates/notion/partials/scan_trigger.html`
- `backend/app/templates/notion/partials/import_progress.html`
- `backend/app/templates/notion/partials/import_summary.html`
- `backend/app/templates/obsidian/import.html`
- `backend/app/templates/obsidian/partials/step_bar.html`
- `backend/app/templates/obsidian/partials/upload_form.html`
- `backend/app/templates/obsidian/partials/scan_trigger.html`
- `backend/app/templates/obsidian/partials/import_progress.html`
- `backend/app/templates/obsidian/partials/import_summary.html`
- `backend/app/notion/router.py`
- `backend/app/obsidian/router.py`

## Expected Output

- `backend/app/templates/importer/partials/step_bar.html`
- `backend/app/templates/importer/partials/upload_form.html`
- `backend/app/templates/importer/partials/scan_trigger.html`
- `backend/app/templates/importer/partials/import_progress.html`
- `backend/app/templates/importer/partials/import_summary.html`
- `backend/app/templates/notion/import.html`
- `backend/app/templates/obsidian/import.html`
- `backend/app/notion/router.py`
- `backend/app/obsidian/router.py`

## Verification

test -d backend/app/templates/importer/partials  # shared dir exists
ls backend/app/templates/importer/partials/*.html | wc -l  # >= 5 shared partials
cd backend && python -m pytest tests/ -x -q  # all pass
rg 'importer/partials/' backend/app/templates/notion/ -l | wc -l  # >= 1
rg 'importer/partials/' backend/app/templates/obsidian/ -l | wc -l  # >= 1
