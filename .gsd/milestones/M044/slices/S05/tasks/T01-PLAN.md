---
estimated_steps: 2
estimated_files: 18
skills_used: []
---

# T01: Move template .append() and namespace() hacks to Python views

Eliminate all Jinja2 `.append()` hacks (8 template files) and `namespace()` hacks (5 template files) by computing the needed data structures in the Python view functions. Each fix is a small, independent change: add pre-computation lines to the Python view, pass the result in the template context, and simplify the Jinja2 template to consume the pre-computed value instead of building it inline.

**Key constraint:** The `get_object()` function in `backend/app/browser/objects.py` (at route `GET /object/{object_iri:path}`) serves `object_tab.html`, `object_read.html`, and `object_embed.html`. All three templates' pre-computation should be consolidated in one block at the end of that function before the template is rendered.

## Inputs

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

## Expected Output

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

## Verification

rg '\.append\(' backend/app/templates/ -g '*.html' | wc -l  # must be 0
rg 'namespace\(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l  # must be 0
cd backend && python -m pytest tests/ -x -q  # all pass
