# S05: Template Hygiene & Deduplication

**Goal:** Template computation logic lives in Python views (testable); Notion/Obsidian importers share base templates; guide/docs page uses loop instead of 55 copy-pasted buttons.
**Demo:** After this: template computation logic lives in Python views (testable); Notion/Obsidian importers share base templates; guide/docs pages use loops instead of 81 copy-pasted buttons

## Must-Haves

- `rg '\.append\(' backend/app/templates/ -g '*.html'` returns 0 results
- `rg 'namespace\(' backend/app/templates/ -g '*.html'` returns only `base_namespace` or `info.namespace` (non-hack references)
- Shared importer partials exist at `backend/app/templates/importer/partials/`
- `wc -l backend/app/templates/guide.html` < 80 lines
- `grep -c 'docs-chapter-item' backend/app/templates/guide.html` returns 0
- `cd backend && python -m pytest tests/ -x -q` passes (no import or runtime errors from refactoring)
- All refactored templates render identical HTML output (no functional changes)

## Proof Level

- This slice proves: Contract — pure refactoring verified by grep counts and test suite pass. No runtime behavior changes.

## Integration Closure

- Upstream surfaces consumed: existing template rendering pipeline (Jinja2 + view functions), importer routers (notion/router.py, obsidian/router.py), shell router (guide page)
- New wiring: shared importer partial templates at `backend/app/templates/importer/partials/`; `GUIDE_CHAPTERS` data structure in shell/router.py passed to guide.html context
- What remains: S06 (console cleanup) and S07 (E2E regression) complete the milestone

## Verification

- None — pure template refactoring with no runtime behavior changes.

## Tasks

- [ ] **T01: Move template .append() and namespace() hacks to Python views** `est:2h`
  Eliminate all Jinja2 `.append()` hacks (8 files) and `namespace()` hacks (5 files) by computing the needed data structures in the Python view functions that serve these templates. Each fix is independent: add a few lines to the Python view to pre-compute the list/dict/bool/count, pass it in the template context, and simplify the template to use the pre-computed value.

Key constraint: `object_detail()` in browser/objects.py serves object_tab.html, object_read.html, and object_embed.html — consolidate all three templates' pre-computation in one block at the end of that function.
  - Files: `backend/app/browser/objects.py`, `backend/app/views/router.py`, `backend/app/dashboard/router.py`, `backend/app/admin/router.py`, `backend/app/browser/settings.py`, `backend/app/notion/router.py`, `backend/app/obsidian/router.py`, `backend/app/templates/browser/saved_queries_explorer.html`, `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/admin/models.html`, `backend/app/templates/browser/object_read.html`, `backend/app/templates/browser/object_embed.html`, `backend/app/templates/browser/object_tab.html`, `backend/app/templates/browser/_context_rules.html`, `backend/app/templates/notion/partials/scan_results.html`, `backend/app/templates/obsidian/partials/scan_results.html`, `backend/app/templates/forms/object_form.html`, `backend/app/templates/notion/partials/property_mapping.html`
  - Verify: rg '\.append\(' backend/app/templates/ -g '*.html' | wc -l  # must be 0
rg 'namespace\(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l  # must be 0
cd backend && python -m pytest tests/ -x -q  # all pass

- [ ] **T02: Deduplicate Notion/Obsidian importer templates into shared partials** `est:2h`
  Create shared importer partials at `backend/app/templates/importer/partials/` for the near-identical templates (import.html, step_bar, upload_form, scan_trigger, import_progress, import_summary). Each shared template uses variables (`importer_name`, `url_prefix`, `steps`, `file_input_id`, etc.) passed from the importer-specific Python views. Structurally different templates (scan_results, preview, type_mapping, property_mapping) stay importer-specific. Notion's relation_mapping.html stays Notion-only.

The Python view routers (notion/router.py, obsidian/router.py) need to pass the new context variables (`importer_name`, `url_prefix`, `steps` list). The importer-specific import.html files become thin wrappers that set variables and include shared partials.

URL paths differ: Notion uses `/browser/notion/`, Obsidian uses `/browser/import/`. Shared templates must use `{{ url_prefix }}` everywhere, never hardcoded paths.
  - Files: `backend/app/templates/importer/partials/step_bar.html`, `backend/app/templates/importer/partials/upload_form.html`, `backend/app/templates/importer/partials/scan_trigger.html`, `backend/app/templates/importer/partials/import_progress.html`, `backend/app/templates/importer/partials/import_summary.html`, `backend/app/templates/notion/import.html`, `backend/app/templates/obsidian/import.html`, `backend/app/templates/notion/partials/step_bar.html`, `backend/app/templates/notion/partials/upload_form.html`, `backend/app/templates/notion/partials/scan_trigger.html`, `backend/app/templates/notion/partials/import_progress.html`, `backend/app/templates/notion/partials/import_summary.html`, `backend/app/templates/obsidian/partials/step_bar.html`, `backend/app/templates/obsidian/partials/upload_form.html`, `backend/app/templates/obsidian/partials/scan_trigger.html`, `backend/app/templates/obsidian/partials/import_progress.html`, `backend/app/templates/obsidian/partials/import_summary.html`, `backend/app/notion/router.py`, `backend/app/obsidian/router.py`
  - Verify: test -d backend/app/templates/importer/partials  # shared dir exists
ls backend/app/templates/importer/partials/*.html | wc -l  # >= 5 shared partials
cd backend && python -m pytest tests/ -x -q  # all pass
# Verify importer-specific templates now include shared partials:
rg 'importer/partials/' backend/app/templates/notion/ -l | wc -l  # >= 1
rg 'importer/partials/' backend/app/templates/obsidian/ -l | wc -l  # >= 1

- [ ] **T03: Replace guide.html copy-pasted buttons with data-driven chapter loop** `est:1h`
  Define a `GUIDE_CHAPTERS` list-of-dicts in `backend/app/shell/router.py` containing all 55 chapter entries (section groupings, filenames, titles, icons, optional tour URLs). Pass this data structure in the template context from `guide_page()`. Replace the 55 hardcoded `<button>` blocks in `guide.html` with a Jinja2 `{% for %}` loop over the sections and chapters.

The guide has three section types: Interactive Tutorials (tour links with special URL pattern), User Guide chapters (standard filename-based), and External References (different rendering with external URLs). The data structure must handle all three.

Per KNOWLEDGE.md three-file-sync rule: this only fixes guide.html. README.md and index.html remain manual (but the `GUIDE_CHAPTERS` data structure could be used to generate them in a future task).
  - Files: `backend/app/shell/router.py`, `backend/app/templates/guide.html`
  - Verify: grep -c 'docs-chapter-item' backend/app/templates/guide.html  # must be 0 (no hardcoded buttons)
wc -l backend/app/templates/guide.html | awk '{print ($1 < 80) ? "PASS" : "FAIL: " $1 " lines"}'  # < 80 lines
cd backend && python -m pytest tests/ -x -q  # all pass

## Files Likely Touched

- backend/app/browser/objects.py
- backend/app/views/router.py
- backend/app/dashboard/router.py
- backend/app/admin/router.py
- backend/app/browser/settings.py
- backend/app/notion/router.py
- backend/app/obsidian/router.py
- backend/app/templates/browser/saved_queries_explorer.html
- backend/app/templates/browser/dashboard_builder.html
- backend/app/templates/admin/models.html
- backend/app/templates/browser/object_read.html
- backend/app/templates/browser/object_embed.html
- backend/app/templates/browser/object_tab.html
- backend/app/templates/browser/_context_rules.html
- backend/app/templates/notion/partials/scan_results.html
- backend/app/templates/obsidian/partials/scan_results.html
- backend/app/templates/forms/object_form.html
- backend/app/templates/notion/partials/property_mapping.html
- backend/app/templates/importer/partials/step_bar.html
- backend/app/templates/importer/partials/upload_form.html
- backend/app/templates/importer/partials/scan_trigger.html
- backend/app/templates/importer/partials/import_progress.html
- backend/app/templates/importer/partials/import_summary.html
- backend/app/templates/notion/import.html
- backend/app/templates/obsidian/import.html
- backend/app/templates/notion/partials/step_bar.html
- backend/app/templates/notion/partials/upload_form.html
- backend/app/templates/notion/partials/scan_trigger.html
- backend/app/templates/notion/partials/import_progress.html
- backend/app/templates/notion/partials/import_summary.html
- backend/app/templates/obsidian/partials/step_bar.html
- backend/app/templates/obsidian/partials/upload_form.html
- backend/app/templates/obsidian/partials/scan_trigger.html
- backend/app/templates/obsidian/partials/import_progress.html
- backend/app/templates/obsidian/partials/import_summary.html
- backend/app/shell/router.py
- backend/app/templates/guide.html
