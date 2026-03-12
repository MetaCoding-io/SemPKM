# S15: Settings System And Node Type Icons

**Goal:** Build the settings infrastructure layer: database model, service, FastAPI endpoints, client JS module, and workspace keyboard/tab integration.
**Demo:** Build the settings infrastructure layer: database model, service, FastAPI endpoints, client JS module, and workspace keyboard/tab integration.

## Must-Haves


## Tasks

- [x] **T01: 15-settings-system-and-node-type-icons 01**
  - Build the settings infrastructure layer: database model, service, FastAPI endpoints, client JS module, and workspace keyboard/tab integration. This plan establishes the full settings pipeline — from layered resolution to DOM event dispatch — with dark mode as the sole initial registered setting.

Purpose: Every other settings consumer (Phase 17 LLM config, future features) depends on this infrastructure. Phase 15-02 builds the UI on top of this foundation.
Output: Working settings API, client settings cache, Ctrl+, shortcut that opens a settings tab, and manifest schema extended for model-contributed settings and icons.
- [x] **T02: 15-settings-system-and-node-type-icons 02** `est:~3min`
  - Build the full Settings page UI with a two-column VS Code-style layout, in-place search filter, all four input types, Modified indicators, per-setting and per-category reset, and wire dark mode as the first real settings consumer.

Purpose: SETT-01 requires a working settings UI with search and current values. SETT-03 requires that changes dispatch the sempkm:setting-changed event. This plan delivers the complete visual and behavioral layer on top of the infrastructure from Plan 15-01.
Output: A fully functional Settings page that users can navigate, change settings, and see immediate effect (dark mode toggle), plus the settings.css stylesheet.
- [x] **T03: 15-settings-system-and-node-type-icons 03**
  - Build the node type icon system: an IconService that reads manifest icon/color declarations, a /browser/icons JSON endpoint, and updated rendering in the explorer tree, editor tab bar, and graph view. Mental Models (basic-pkm) contribute icon and color declarations in their manifest.yaml.

Purpose: ICON-01/02/03 require type-specific visual identity throughout the workspace. The manifest extension from Plan 15-01 enables model-contributed declarations; this plan wires them into the three render paths.
Output: Explorer tree shows Lucide icons with colors, editor tabs show type icons, graph nodes use type-appropriate shapes/colors, basic-pkm manifest declares icons for its types.

## Files Likely Touched

- `backend/app/auth/models.py`
- `backend/migrations/versions/002_user_settings.py`
- `backend/app/services/settings.py`
- `backend/app/models/manifest.py`
- `backend/app/browser/router.py`
- `frontend/static/js/settings.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/components/_sidebar.html`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_setting_input.html`
- `frontend/static/css/settings.css`
- `backend/app/templates/base.html`
- `frontend/static/js/theme.js`
- `backend/app/services/icons.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/nav_tree.html`
- `backend/app/templates/browser/tree_children.html`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
- `models/basic-pkm/manifest.yaml`
