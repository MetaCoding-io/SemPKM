---
estimated_steps: 17
estimated_files: 32
skills_used: []
---

# T02: Migrate template onclick handlers and inline script globals to SemPKM namespace

Update all Jinja2 template files that reference custom workspace globals. Three categories of changes:

1. **onclick handlers calling bare globals**: `onclick="openTab(...)"` → `onclick="SemPKM.openTab(...)"`. This is the most common pattern (~67 occurrences across ~21 templates).

2. **Inline `<script>` blocks that export to window**: `window.X = function(...)` → `window.SemPKM.X = function(...)`. Found in object_form.html (~5 exports), object_tab_app.html (~4 exports), dashboard_builder.html, workflow_builder.html, workflow_runner.html, _llm_settings.html, admin/models.html.

3. **typeof guards in inline scripts**: `typeof window.X === 'function'` → `typeof SemPKM.X === 'function'`. Found in _field.html, guide_article.html, object_embed.html, object_tab_app.html.

**DO NOT migrate:**
- Debug/admin templates that use page-local functions from `app.js` (switchTab, executeCommand, runSparqlQuery in debug/commands.html, debug/event_console.html, debug/sparql.html) — those are NOT workspace globals
- Browser builtins: `window.location`, `window.confirm`, `window.open`, `window.localStorage`, `window.setTimeout`, `window.matchMedia`, etc.
- Third-party: `window.htmx`, `window.lucide`, `window.posthog`, `window.DockviewCore`, etc.
- Existing `SemPKMSettings`, `SemPKMLayouts`, `SemPKMCanvas` references — already namespaced
- Template variables that happen to be in onclick handlers but are Jinja2 expressions, not JS globals

**Key templates by edit volume:**
- object_tab.html: ~10 editorAction + toggleObjectMode + saveCurrentObject onclick calls
- object_tab_app.html: ~8 onclick calls + ~6 window.X references in inline script
- okr_view.html: ~4 openTab onclick calls
- object_form.html: ~5 window.X = function exports
- workspace.html: onclick handlers for workspace-level UI
- saved_queries_explorer.html / tag_tree_objects.html: ondragstart with window.__canvasDragPayload

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/object_tab_app.html`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/event_log.html`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/workflow_builder.html`

## Expected Output

- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/object_tab_app.html`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/browser/object_embed.html`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/okr_view.html`
- `backend/app/templates/browser/bmc_view.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/kanban_view.html`
- `backend/app/templates/browser/quadrant_view.html`
- `backend/app/templates/browser/decision_matrix_view.html`
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/lint_dashboard.html`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/event_log.html`
- `backend/app/templates/browser/ref_tooltip.html`
- `backend/app/templates/browser/partials/shared_nav_content.html`
- `backend/app/templates/browser/saved_queries_explorer.html`
- `backend/app/templates/browser/tag_tree_objects.html`
- `backend/app/templates/browser/_llm_settings.html`
- `backend/app/templates/browser/workflow_runner.html`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/workflow_builder.html`
- `backend/app/templates/browser/docs_viewer.html`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/guide_article.html`
- `backend/app/templates/components/_tabs.html`
- `backend/app/templates/components/_sidebar.html`
- `backend/app/templates/admin/sparql.html`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/browser/ontology/abox_instances.html`

## Verification

1. No custom window.X onclick handlers remain: `rg 'onclick=.*window\.\w+' backend/app/templates/ | grep -v 'window\.(location|confirm|prompt|open|matchMedia|lucide|htmx|posthog|close|print|getComputedStyle|innerWidth|scrollTo|addEventListener|removeEventListener|setTimeout|clearTimeout|setInterval|clearInterval|requestAnimationFrame|getSelection|DOMParser|MutationObserver|IntersectionObserver|ResizeObserver|URL|fetch|history|navigator|performance|CustomEvent|dispatchEvent|Event|localStorage|sessionStorage|SemPKM)'` — zero lines.
2. Bare workspace globals in onclick migrated: `rg 'onclick="(openTab|closeTab|editorAction|toggleObjectMode|saveCurrentObject|showToast|showCreateFormForType|switchTab|markDirty|markClean|refreshNavTree|showConfirmDialog|showTypePicker|toggleBottomPanel|filterGraph|initGraph|showSettingsCategory|filterSettings|renderMarkdownBody)\b' backend/app/templates/ | grep -v 'SemPKM\.' | grep -v 'debug/' | grep -v 'admin/federation'` — zero lines (excluding debug pages with local app.js functions).
3. Inline script window exports migrated: `rg 'window\.[a-z]\w+ = function' backend/app/templates/ | grep -v 'window\.SemPKM'` — zero lines.
4. typeof guards in templates migrated: `rg 'typeof window\.\w+ ==' backend/app/templates/ | grep -v 'typeof window\.SemPKM' | grep -v 'typeof SemPKM'` — zero lines.
