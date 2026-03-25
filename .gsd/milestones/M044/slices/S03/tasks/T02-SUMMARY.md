---
id: T02
parent: S03
milestone: M044
key_files:
  - backend/app/templates/browser/object_tab.html
  - backend/app/templates/browser/object_tab_app.html
  - backend/app/templates/browser/settings_page.html
  - backend/app/templates/browser/event_log.html
  - backend/app/templates/forms/object_form.html
  - backend/app/templates/forms/_field.html
  - backend/app/templates/browser/_context_rules.html
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/templates/browser/workflow_builder.html
  - backend/app/templates/browser/_setting_input.html
  - backend/app/templates/components/_sidebar.html
  - backend/app/templates/browser/workflow_runner.html
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/canvas.js
  - frontend/static/js/kanban.js
key_decisions:
  - Migrated __canvasDragPayload to SemPKM namespace (reversing T01 decision to leave double-underscore globals unmigrated) — templates writing to it must be consistent with JS readers
  - Internal state vars (_tabMeta, _dockview, _sempkmRefreshTimer, _sempkmCmdListener, _viewFilterRefocusBound) moved into SemPKM namespace alongside public APIs for consistency
duration: ""
verification_result: passed
completed_at: 2026-03-25T19:35:35.467Z
blocker_discovered: false
---

# T02: Migrate all template onclick handlers, inline script exports, and typeof guards to SemPKM namespace

**Migrate all template onclick handlers, inline script exports, and typeof guards to SemPKM namespace**

## What Happened

Migrated all Jinja2 templates from bare window.X references to SemPKM.X namespace. Three categories of changes:

1. **onclick/onchange/oninput/onsubmit handlers** (~70+ occurrences across ~30 templates): `onclick="openTab(...)"` → `onclick="SemPKM.openTab(...)"`. Covered all view templates (quadrant, okr, bmc, cards, kanban, decision_matrix, table, lint_dashboard), object templates (object_tab, object_tab_app, object_read, object_embed), form templates (object_form, _field, search_suggestions), settings templates (settings_page, _setting_input, _context_rules, _llm_settings), builder templates (dashboard_builder, workflow_builder), explorer templates (workflow_explorer, dashboard_explorer), and misc templates (ref_tooltip, shared_nav_content, type_picker, _tabs, abox_instances, graph_view, workspace, docs_page, workflow_runner, dashboard_form_group).

2. **Inline `<script>` window.X exports** (~50 function definitions): `window.X = function` → `window.SemPKM.X = function`. Found in object_tab.html (4 props functions), object_form.html (5 form functions), settings_page.html (5 settings functions), event_log.html (2 event functions), _context_rules.html (6 functions), _llm_settings.html (1), _webid_settings.html (7), _notification_preferences.html (4), workflow_runner.html (1), workflow_explorer.html (1), dashboard_explorer.html (1), dashboard_builder.html (7), workflow_builder.html (7), my_views.html (2), view_toolbar.html (1), admin/models.html (2), ontology/edit_class_form.html (5), ontology/create_property_form.html (2), ontology/edit_property_form.html (1).

3. **typeof guards** (~20 occurrences): `typeof window.X === 'function'` → `typeof SemPKM.X === 'function'`. Updated in _field.html, guide_article.html, docs_viewer.html, object_embed.html, object_read.html, object_tab.html, object_tab_app.html, type_picker.html, workspace.html, graph_view.html, my_views.html, view_toolbar.html, docs_page.html.

4. **Internal state references**: `window._tabMeta` → `window.SemPKM._tabMeta`, `window._dockview` → `SemPKM._dockview`, `window.__canvasDragPayload` → `window.SemPKM.__canvasDragPayload` (in 6 drag templates + 2 JS files), `window._sempkmSkipLayoutSave` → `window.SemPKM._sempkmSkipLayoutSave` (sidebar template + workspace-layout.js reader), `window._sempkmRefreshTimer` → `window.SemPKM._sempkmRefreshTimer`, `window._sempkmCmdListener` → `window.SemPKM._sempkmCmdListener`.

Also fixed T01 leftover: updated workspace-layout.js to read `_sempkmSkipLayoutSave` from SemPKM namespace (T01 deferred this to T02), and migrated `__canvasDragPayload` in canvas.js and kanban.js (T01 had left double-underscore globals unmigrated).

## Verification

All four slice-level verification checks pass with zero lines of output (exit code 1 = no matches = correct):
1. No custom window.X onclick handlers remain (excludes browser builtins and SemPKM namespace)
2. Bare workspace globals in onclick fully migrated (excludes debug pages)
3. Inline script window exports fully migrated (all use window.SemPKM.X)
4. typeof guards fully migrated (all use SemPKM.X or window.SemPKM)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'onclick=.*window\.\w+' templates/ | grep -v exclusions (Check 1: no custom window.X onclick handlers)` | 1 | ✅ pass | 80ms |
| 2 | `rg bare workspace globals in onclick (Check 2)` | 1 | ✅ pass | 70ms |
| 3 | `rg 'window\.[a-z]\w+ = function' templates/ | grep -v window.SemPKM (Check 3: inline exports)` | 1 | ✅ pass | 60ms |
| 4 | `rg 'typeof window\.\w+ ==' templates/ | grep -v SemPKM (Check 4: typeof guards)` | 1 | ✅ pass | 60ms |


## Deviations

1. Migrated __canvasDragPayload in JS files (canvas.js, kanban.js) and all drag templates — T01 had left double-underscore globals unmigrated but templates writing to them needed consistent namespace. 2. Updated workspace-layout.js _sempkmSkipLayoutSave reader — T01 deferred this to T02. 3. Migrated additional templates not in the plan's Expected Output: _setting_input.html, _context_rules.html, _webid_settings.html, _notification_preferences.html, search_suggestions.html, tree_children.html, views_explorer.html, mount_tree_objects.html, tag_tree_folder.html, dashboard_form_group.html, dashboard_explorer.html, workflow_explorer.html, type_picker.html, docs_page.html, docs_viewer.html, view_toolbar.html, my_views.html, graph_view.html, ontology/edit_class_form.html, ontology/create_property_form.html, ontology/edit_property_form.html.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/object_tab_app.html`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/event_log.html`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/browser/_context_rules.html`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/workflow_builder.html`
- `backend/app/templates/browser/_setting_input.html`
- `backend/app/templates/components/_sidebar.html`
- `backend/app/templates/browser/workflow_runner.html`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/kanban.js`
