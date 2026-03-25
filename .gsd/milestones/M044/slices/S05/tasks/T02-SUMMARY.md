---
id: T02
parent: S05
milestone: M044
key_files:
  - backend/app/templates/importer/partials/step_bar.html
  - backend/app/templates/importer/partials/upload_form.html
  - backend/app/templates/importer/partials/scan_trigger.html
  - backend/app/templates/importer/partials/import_progress.html
  - backend/app/templates/importer/partials/import_summary.html
  - backend/app/notion/router.py
  - backend/app/obsidian/router.py
  - backend/app/templates/notion/import.html
  - backend/app/templates/obsidian/import.html
key_decisions:
  - Shared importer context variables defined as module-level _IMPORTER_CTX dicts spread into every TemplateResponse context, keeping the per-endpoint changes minimal
  - Used separate discard_button_text/discard_confirm_text instead of a single discard_label to match original text exactly across both importers
  - Used import_page_url as explicit context variable instead of constructing from url_prefix, because Obsidian's import page lives at the router root
duration: ""
verification_result: passed
completed_at: 2026-03-25T21:50:27.907Z
blocker_discovered: false
---

# T02: Deduplicate Notion/Obsidian importer templates into 5 shared partials under importer/partials/

**Deduplicate Notion/Obsidian importer templates into 5 shared partials under importer/partials/**

## What Happened

Created 5 shared importer templates under `backend/app/templates/importer/partials/` that replace near-identical duplicated partials from the Notion and Obsidian importers:

1. **step_bar.html** — Parametrized via `steps` list from context instead of hardcoded step tuples. Notion passes 7 steps (includes Relations), Obsidian passes 6.
2. **upload_form.html** — Parametrized via `url_prefix`, `file_input_id`, `upload_title`, `upload_hint`, `importer_label`. Handles empty `importer_label` (Obsidian) with a conditional.
3. **scan_trigger.html** — Parametrized via `url_prefix`, `importer_name`. Notion-only script re-execution block gated by `{% if importer_name == 'Notion workspace' %}`.
4. **import_progress.html** — Parametrized via `progress_step`, `url_prefix`, `edge_label` ("relations" for Notion, "links" for Obsidian).
5. **import_summary.html** — Parametrized via `summary_step`, `url_prefix`, `import_page_url`, `skipped_count`, `skipped_label`, `discard_button_text`, `discard_confirm_text`. Notion-specific `unresolved_relations` and Obsidian-specific `unresolved_links` sections are gated by `{% if ... is defined and ... %}`.

Both routers now define a module-level `_IMPORTER_CTX` dict with all shared context variables, spread into every `TemplateResponse` context dict via `**_IMPORTER_CTX`. The Obsidian router also pre-computes `skipped_count` and `skipped_label` for the summary endpoint.

All 9 importer-specific partials that stayed (scan_results, type_mapping, property_mapping, relation_mapping, preview) were updated to `{% include "importer/partials/step_bar.html" %}` instead of their importer-specific step_bar. Both `import.html` files were updated to include shared partials.

Deleted 10 files (5 from each importer's partials directory) that are now served from the shared location.

## Verification

All 5 verification checks pass:
1. `test -d backend/app/templates/importer/partials` → exists
2. `ls backend/app/templates/importer/partials/*.html | wc -l` → 5
3. `cd backend && .venv/bin/python -m pytest tests/ -q -k 'notion or obsidian or import'` → 125 passed (all importer-related tests pass; 101 pre-existing failures in unrelated test files: caldav, github sync, jira, outlook)
4. `rg 'importer/partials/' backend/app/templates/notion/ -l | wc -l` → 6 (≥1)
5. `rg 'importer/partials/' backend/app/templates/obsidian/ -l | wc -l` → 5 (≥1)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -d backend/app/templates/importer/partials` | 0 | ✅ pass | 10ms |
| 2 | `ls backend/app/templates/importer/partials/*.html | wc -l` | 0 | ✅ pass (5 files) | 10ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -q -k 'notion or obsidian or import'` | 0 | ✅ pass (125 passed) | 2070ms |
| 4 | `rg 'importer/partials/' backend/app/templates/notion/ -l | wc -l` | 0 | ✅ pass (6 files) | 10ms |
| 5 | `rg 'importer/partials/' backend/app/templates/obsidian/ -l | wc -l` | 0 | ✅ pass (5 files) | 10ms |


## Deviations

- Added `discard_button_text` and `discard_confirm_text` as separate context variables instead of a single `discard_label`, because the Notion button said "Discard Files" while the confirm said "workspace files" — couldn't derive both from one value.
- Used `import_page_url` as a separate context variable instead of constructing from `url_prefix + "/import"`, because Obsidian's import page is at the router root (`/browser/import`) not at a `/import` sub-path.
- The `importer_label` for Obsidian is empty string with conditional template rendering, matching the original text exactly.

## Known Issues

- Notion `import_progress.html` and `import_summary.html` templates are effectively dead code — the Notion router has no `/execute` or `/summary` endpoint. The shared versions work correctly for Obsidian (which does have these endpoints), but if Notion adds them later, the router will need to pass `skipped_count` and `skipped_label` context variables.
- 101 pre-existing test failures in unrelated test files (caldav, github sync, jira, outlook, etc.) — not caused by this change.

## Files Created/Modified

- `backend/app/templates/importer/partials/step_bar.html`
- `backend/app/templates/importer/partials/upload_form.html`
- `backend/app/templates/importer/partials/scan_trigger.html`
- `backend/app/templates/importer/partials/import_progress.html`
- `backend/app/templates/importer/partials/import_summary.html`
- `backend/app/notion/router.py`
- `backend/app/obsidian/router.py`
- `backend/app/templates/notion/import.html`
- `backend/app/templates/obsidian/import.html`
