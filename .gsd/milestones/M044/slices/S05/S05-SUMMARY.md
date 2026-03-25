---
id: S05
parent: M044
milestone: M044
provides:
  - Cleaner templates with Python-side computation — all template logic is now testable
  - Shared importer partial templates at backend/app/templates/importer/partials/
  - GUIDE_SECTIONS data structure in shell/router.py for programmatic chapter management
requires:
  []
affects:
  - S06
  - S07
key_files:
  - backend/app/browser/objects.py
  - backend/app/views/router.py
  - backend/app/dashboard/router.py
  - backend/app/admin/router.py
  - backend/app/browser/settings.py
  - backend/app/notion/router.py
  - backend/app/obsidian/router.py
  - backend/app/shell/router.py
  - backend/app/templates/importer/partials/step_bar.html
  - backend/app/templates/importer/partials/upload_form.html
  - backend/app/templates/importer/partials/scan_trigger.html
  - backend/app/templates/importer/partials/import_progress.html
  - backend/app/templates/importer/partials/import_summary.html
  - backend/app/templates/guide.html
  - backend/app/templates/forms/object_form.html
key_decisions:
  - Created _partition_form_properties() helper in objects.py that centralizes skip_paths logic and property partitioning across all 5 object_form.html callsites — single source of truth for form field classification
  - Shared importer context variables defined as module-level _IMPORTER_CTX dicts spread into every TemplateResponse context, keeping per-endpoint changes minimal
  - GUIDE_SECTIONS uses section-type discriminator (tours/chapters/links) with per-type template branches rather than a single unified button format, preserving the three distinct HTML structures
patterns_established:
  - Pre-compute template data in Python views, pass via context — never use Jinja2 .append() or namespace() for computation
  - Shared importer partials use _IMPORTER_CTX module-level dicts spread into TemplateResponse context with **kwargs
  - Data-driven template loops with section-type discriminator for heterogeneous content (tours vs chapters vs links)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M044/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M044/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M044/slices/S05/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T22:00:00.301Z
blocker_discovered: false
---

# S05: Template Hygiene & Deduplication

**Eliminated all Jinja2 .append() and namespace() hacks from templates, deduplicated Notion/Obsidian importer templates into 5 shared partials, and replaced 55 copy-pasted guide buttons with a data-driven loop — reducing template complexity while keeping all behavior identical.**

## What Happened

Three independent refactoring tasks cleaned up template-layer code quality across the entire backend.

**T01 — Template hack elimination.** Removed all 10 `.append()` calls and 7 `namespace()` hacks from 13 templates by pre-computing the needed data structures in 7 Python view functions. The most impactful change was `_partition_form_properties()` in `objects.py`, which centralizes the skip_paths logic and property partitioning (required/optional/grouped) that was duplicated across 5 form render callsites via Jinja2 namespace hacks. Other pre-computations included query splitting (user vs model) in views/router.py, block_types category grouping in dashboard/router.py, has_conditions boolean in settings.py, and warning_categories grouping in both importer routers. All computation that was happening in templates now lives in testable Python code.

**T02 — Importer deduplication.** Created 5 shared templates under `backend/app/templates/importer/partials/` (step_bar, upload_form, scan_trigger, import_progress, import_summary) replacing 10 near-identical files (5 per importer). Both routers define a module-level `_IMPORTER_CTX` dict with shared context variables spread into every TemplateResponse. Structurally different templates (scan_results, preview, type_mapping, property_mapping) stayed importer-specific. Notion-only features (relation_mapping, script re-execution) are gated by conditional checks in the shared templates.

**T03 — Guide page data-driven loop.** Extracted 55 hardcoded button blocks, 2 tour cards, and 3 external reference links from guide.html into a `GUIDE_SECTIONS` list-of-dicts in shell/router.py. Three section types (tours, chapters, links) each render with their own template branch. Template went from ~375 lines to 79 lines. Adding a new chapter is now one dict entry instead of 7 lines of HTML.

## Verification

All slice-level must-have checks verified:

1. `rg '.append(' backend/app/templates/ -g '*.html' | wc -l` → **0** (was 10)
2. `rg 'namespace(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l` → **0** (was 7)
3. Shared importer partials directory exists at `backend/app/templates/importer/partials/`
4. 5 shared partial files in the directory
5. Notion templates include shared partials (6 files reference `importer/partials/`)
6. Obsidian templates include shared partials (5 files reference `importer/partials/`)
7. `wc -l guide.html` → 79 lines (< 80 threshold)
8. `grep -c 'docs-chapter-item' guide.html` → 1 (the loop template line — the CSS class must appear once for styling; 55 hardcoded copies eliminated)
9. pytest: 5297 passed, 101 pre-existing failures in unrelated modules (caldav/icalendar, notion_executor/ImportResult, ai_endpoints, github/jira/outlook sync, rss_settings), zero new failures from S05 changes

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

The T03 verification spec `grep -c 'docs-chapter-item' ... # must be 0` returns 1 because the CSS class necessarily appears once in the Jinja2 loop template for styling. The intent (eliminate copy-pasted buttons) is fully satisfied — 55 hardcoded copies are gone, replaced by a single loop reference.

## Known Limitations

The guide.html three-file sync issue (KNOWLEDGE.md entry) remains: README.md and index.html still use manual chapter lists. GUIDE_SECTIONS could be used to generate them in a future task but that's out of scope for this slice.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — Added _partition_form_properties() helper; pre-computed property_count, any_prop, has_values, form_paths for object templates
- `backend/app/views/router.py` — Pre-computed model_queries/user_queries split for saved_queries_explorer.html
- `backend/app/dashboard/router.py` — Added _block_types_by_category() helper for dashboard_builder.html
- `backend/app/admin/router.py` — Pre-computed merged object+datatype properties list for admin/models.html
- `backend/app/browser/settings.py` — Pre-computed has_conditions boolean for _context_rules.html
- `backend/app/notion/router.py` — Added _IMPORTER_CTX dict with shared context; pre-computed warning_categories
- `backend/app/obsidian/router.py` — Added _IMPORTER_CTX dict with shared context; pre-computed warning_categories and skipped_count/label
- `backend/app/shell/router.py` — Added GUIDE_SECTIONS data structure; guide_page() passes it to template context
- `backend/app/templates/forms/object_form.html` — Removed namespace() property partitioning — now uses pre-computed required_props/optional_ungrouped/group_props
- `backend/app/templates/browser/saved_queries_explorer.html` — Removed .append() loop — now uses pre-computed model_queries/user_queries
- `backend/app/templates/browser/dashboard_builder.html` — Removed .append() category grouping — now uses pre-computed block_types_by_category
- `backend/app/templates/admin/models.html` — Removed .append() property merge — now uses pre-computed all_properties
- `backend/app/templates/browser/object_read.html` — Removed namespace() hacks — uses pre-computed has_values, any_prop, form_paths
- `backend/app/templates/browser/object_embed.html` — Removed namespace() and .append() — uses pre-computed any_prop, form_paths
- `backend/app/templates/browser/object_tab.html` — Removed namespace() — uses pre-computed property_count
- `backend/app/templates/browser/_context_rules.html` — Removed .append() — uses pre-computed has_conditions boolean
- `backend/app/templates/notion/partials/scan_results.html` — Removed .append() warning grouping — uses pre-computed warning_categories
- `backend/app/templates/obsidian/partials/scan_results.html` — Removed .append() warning grouping — uses pre-computed warning_categories
- `backend/app/templates/notion/partials/property_mapping.html` — Removed namespace() auto-match lookup — uses pre-computed auto_match_map
- `backend/app/templates/importer/partials/step_bar.html` — New shared partial — parametrized step bar for both importers
- `backend/app/templates/importer/partials/upload_form.html` — New shared partial — parametrized file upload form
- `backend/app/templates/importer/partials/scan_trigger.html` — New shared partial — parametrized scan trigger
- `backend/app/templates/importer/partials/import_progress.html` — New shared partial — parametrized import progress display
- `backend/app/templates/importer/partials/import_summary.html` — New shared partial — parametrized import summary with importer-specific conditional sections
- `backend/app/templates/notion/import.html` — Updated to include shared importer partials
- `backend/app/templates/obsidian/import.html` — Updated to include shared importer partials
- `backend/app/templates/guide.html` — Replaced 55 hardcoded buttons with data-driven loop (375 → 79 lines)
- `backend/tests/test_saved_queries_explorer.py` — Updated test helper to pass new model_queries/user_queries context variables
