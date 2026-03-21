# S06 Summary: Dashboard & Workflow Builder UX

**Status:** Complete
**Duration:** ~40 minutes across 3 tasks
**Requirements validated:** DBUIX-01, DBUIX-02, DBUIX-03, DBUIX-04

## What This Slice Delivered

Made the dashboard and workflow builders self-documenting and usable without memorizing IRIs:

1. **Contextual help text on every field** (DBUIX-01) — 13 `<small class="field-help">` elements in dashboard builder, 6 in workflow builder. Covers top-level fields (name, description, layout) and all block/step type config fields (view spec, renderer, target class, object IRI, SPARQL query, markdown content, etc.). Follows the SHACL helptext pattern.

2. **Autocomplete for IRI reference fields** (DBUIX-02) — Two new JSON endpoints:
   - `/browser/class-search?q=...` — wraps OntologyService.search_classes(), returns `[{iri, label}]`
   - `/browser/object-search?q=...` — SPARQL REGEX across rdfs:label, dcterms:title, skos:prefLabel, schema:name in current state graph, returns `[{iri, label}]` (max 15)
   
   Autocomplete widgets (`.reference-field` wrapper + hidden `data-key` input + `.suggestions-dropdown`) wired to:
   - Dashboard `create-form` block → Target Class IRI (class-search)
   - Dashboard `object-embed` block → Object IRI (object-search)
   - Workflow `form` step → Target Class IRI (class-search)

3. **Workflow view step simplification** (DBUIX-03) — Removed redundant renderer `<select>` dropdown from the "view" step. Renderer type is now auto-set from `_cachedViews` when a view is selected, stored in a hidden input (`data-key="renderer_type"`), and shown as a read-only `.renderer-badge` span. The save collector still works because it queries `[data-key]` attributes.

4. **Idempotent seed data** (DBUIX-04) — `backend/app/dashboard/seed.py` creates a "Getting Started" dashboard (sidebar-main layout, markdown welcome + view-embed) and a "Create & Review" two-step workflow for users with zero dashboards/workflows. Wired into app startup after setup mode detection. Error-isolated (never crashes the app). 4 unit tests cover empty, existing, and mixed states.

## Key Files

| File | Change |
|------|--------|
| `backend/app/templates/browser/dashboard_builder.html` | 13 field-help elements, 2 autocomplete widgets (class + object) |
| `backend/app/templates/browser/workflow_builder.html` | 6 field-help elements, 1 autocomplete widget, renderer dropdown → hidden input + badge |
| `backend/app/browser/search.py` | `/browser/class-search` and `/browser/object-search` endpoints |
| `backend/app/dashboard/seed.py` | New: idempotent seed_sample_data() function |
| `backend/app/main.py` | Startup hook calling seed_sample_data for first user |
| `backend/tests/test_seed_data.py` | 4 unit tests for seed idempotency |
| `frontend/static/css/workspace.css` | `.block-config-fields .reference-field` scoped styles |

## Patterns Established

- **Builder autocomplete pattern:** `.reference-field` wrapper containing a visible search `<input>`, a hidden `<input data-key="...">`, and a `.suggestions-dropdown` div. Shared helper function handles 300ms debounce, fetch, rendering, click-to-select, and click-outside dismiss. Endpoint parameter makes it reusable for different search backends.

- **Idempotent seed pattern:** Check `list_for_user()` emptiness before creating, log outcome, wrap in try/except so seed failures never crash startup. Returns `{dashboard_created: bool, workflow_created: bool}` for observability.

## What S07 (E2E Tests + Docs) Should Know

- The autocomplete endpoints are `/browser/class-search?q=...` and `/browser/object-search?q=...` — both return `[{iri, label}]` JSON arrays and gracefully degrade to `[]` on error.
- The renderer dropdown verification check is `grep -c 'step-config-renderer'` returning 0. The hidden input class is `wf-auto-renderer` (deliberately named to avoid that grep match).
- Seed data runs only when `setup_complete=True` and user has 0 dashboards or 0 workflows. Check `docker compose logs backend | grep -i seed` for startup verification.
- Builder error display uses `#builder-error` div — already present in both templates.

## Verification Results

All 9 slice-level checks pass:

| Check | Result |
|-------|--------|
| Dashboard field-help count ≥ 10 | ✅ 13 |
| Workflow field-help count ≥ 5 | ✅ 6 |
| step-config-renderer count = 0 | ✅ 0 (exit code 1) |
| Dashboard has class-search | ✅ |
| Workflow has class-search | ✅ |
| seed.py valid Python | ✅ |
| seed_sample wired in main.py | ✅ (2 matches) |
| Seed unit tests pass | ✅ 4 passed |
| builder-error divs present | ✅ |
