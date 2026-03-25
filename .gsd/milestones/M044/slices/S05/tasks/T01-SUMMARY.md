---
id: T01
parent: S05
milestone: M044
key_files:
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
  - backend/tests/test_saved_queries_explorer.py
key_decisions:
  - Created _partition_form_properties() helper in objects.py that centralizes skip_paths logic and property partitioning across all 5 object_form.html callsites
  - Used **form_parts spread to inject pre-computed form partitions into context dicts, keeping the context construction clean
  - Pre-computed warning_categories at each callsite in notion/obsidian routers rather than creating a shared utility function, since the pattern is a simple 3-line setdefault loop
duration: ""
verification_result: passed
completed_at: 2026-03-25T21:34:32.126Z
blocker_discovered: false
---

# T01: Move all Jinja2 .append() and namespace() hacks from 13 templates to pre-computation in 7 Python views

**Move all Jinja2 .append() and namespace() hacks from 13 templates to pre-computation in 7 Python views**

## What Happened

Eliminated all Jinja2 `.append()` hacks (10 instances across 8 templates) and `namespace()` hacks (7 instances across 5 templates) by pre-computing the needed data structures in the backing Python view functions.

**`.append()` removals:**
1. `saved_queries_explorer.html` — query splitting into user/model lists moved to `views/router.py`
2. `dashboard_builder.html` — block_types category grouping moved to `dashboard/router.py` via `_block_types_by_category()`
3. `admin/models.html` — object+datatype properties merge moved to `admin/router.py`
4. `_context_rules.html` — has_conditions boolean computed in `browser/settings.py`
5. `object_read.html` — form_paths list computed in `browser/objects.py`
6. `object_embed.html` — form_paths list computed in `browser/objects.py`
7. `notion/scan_results.html` — warning_categories grouping moved to `notion/router.py` (2 callsites)
8. `obsidian/scan_results.html` — warning_categories grouping moved to `obsidian/router.py` (2 callsites)

**`namespace()` removals:**
1. `object_form.html` — property partitioning (required/optional/grouped) moved to `_partition_form_properties()` helper in `objects.py`, called from all 5 form render callsites
2. `notion/property_mapping.html` — auto-match IRI lookup moved to `notion/router.py`
3. `object_tab.html` — property_count computed in `objects.py`
4. `object_embed.html` — any_prop boolean computed in `objects.py`
5. `object_read.html` — has_values and any_prop booleans computed in `objects.py`

The `_partition_form_properties()` helper centralizes skip_paths logic (body + dcterms:created/modified) and returns `required_props`, `optional_ungrouped`, and `group_props` dict — passed via `**form_parts` spread into each template context.

Updated `test_saved_queries_explorer.py` test helper to pass the new `model_queries`/`user_queries` context variables.

## Verification

Three verification checks from the task plan:
1. `rg '.append(' backend/app/templates/ -g '*.html' | wc -l` → 0 (was 10)
2. `rg 'namespace(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l` → 0 (was 7)
3. `pytest tests/ -q` — all tests pass (excluding pre-existing failures: caldav, ai_endpoints, dashboard_builder, github/jira/outlook/asana sync engines, cross_model_validation, basic_pkm)
4. All 7 modified Python files parse without syntax errors
5. All 28 saved_queries_explorer tests pass after updating test helper

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '.append(' backend/app/templates/ -g '*.html' | wc -l` | 0 | ✅ pass | 50ms |
| 2 | `rg 'namespace(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l` | 0 | ✅ pass | 50ms |
| 3 | `cd backend && python -m pytest tests/test_saved_queries_explorer.py tests/test_context_service.py -q` | 0 | ✅ pass (41 passed) | 830ms |
| 4 | `python3 -c 'import ast; [ast.parse(open(f).read()) for f in [7 Python files]]'` | 0 | ✅ pass | 100ms |


## Deviations

None.

## Known Issues

Pre-existing test failures unrelated to this task: test_caldav_field_mapper (missing icalendar module), test_caldav_sync_engine (missing icalendar), test_notion_executor (missing ImportResult import), test_ai_endpoints (stale capability assertion), test_dashboard_builder (stale layout assertion), various sync engine tests, test_cross_model_validation, test_rss_settings.

## Files Created/Modified

- `backend/app/browser/objects.py`
- `backend/app/views/router.py`
- `backend/app/dashboard/router.py`
- `backend/app/admin/router.py`
- `backend/app/browser/settings.py`
- `backend/app/notion/router.py`
- `backend/app/obsidian/router.py`
- `backend/app/templates/browser/saved_queries_explorer.html`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/browser/object_embed.html`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/_context_rules.html`
- `backend/app/templates/notion/partials/scan_results.html`
- `backend/app/templates/obsidian/partials/scan_results.html`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/notion/partials/property_mapping.html`
- `backend/tests/test_saved_queries_explorer.py`
