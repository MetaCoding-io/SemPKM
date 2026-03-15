# S04: Dashboard Builder UI & Explorer Integration — Research

**Date:** 2026-03-15

## Summary

S04 adds two things: (1) a form-based UI for creating and editing dashboards, and (2) a DASHBOARDS section in the explorer sidebar. The codebase already has everything this slice needs — the `DashboardService` CRUD (S03), the explorer section pattern (FAVORITES, VIEWS, SHARED), the htmx form pattern (class creation form, mount creation form), and the `openDashboardTab()` JS function. No new libraries, no new infrastructure.

The builder is a form rendered inside a workspace tab (same pattern as the ontology viewer or VFS browser). It collects: dashboard name, description, layout selection (visual picker from 5 predefined layouts), and a repeating block editor where each block row configures type + type-specific fields. The existing `PATCH /api/dashboard/{id}` endpoint handles saves; `POST /api/dashboard` handles creation. Both already validate layouts and block types.

The explorer integration is a new `<div class="explorer-section">` in `workspace.html` between MY VIEWS and SHARED, lazy-loaded via htmx from a new endpoint. Each dashboard appears as a clickable leaf node calling `openDashboardTab()`.

## Recommendation

**Two new routes + one template + one explorer section.**

1. **`GET /browser/dashboard/new`** — renders the builder form template in "create" mode (empty fields). Opens in a workspace tab via a new `openDashboardBuilderTab()` JS function.
2. **`GET /browser/dashboard/{id}/edit`** — renders the same builder form template in "edit" mode (pre-populated from `DashboardService.get()`).
3. **`dashboard_builder.html`** — single Jinja2 template handling both create and edit modes. Uses the mount-form/class-creation-form pattern: `form-field` + `form-actions` CSS classes, htmx submit, dynamic block rows via JS.
4. **Explorer section** — new `dashboard_explorer.html` partial, loaded via `GET /browser/dashboard/explorer`. Lists dashboards with click-to-open. Include between MY VIEWS and SHARED in `workspace.html`.

The builder form submits to the existing JSON API endpoints (`POST /api/dashboard` for create, `PATCH /api/dashboard/{id}` for edit) via `fetch()` (not htmx), since the API expects JSON body, not form-encoded data. On success, open the dashboard tab and close the builder tab.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Dashboard CRUD | `DashboardService` (S03) | Already validates layouts and block types, handles ownership |
| View spec picker for view-embed blocks | `GET /browser/views/available` | Returns all ViewSpecs as JSON with spec_iri, label, renderer_type, target_class |
| Type picker for create-form blocks | `ShapesService.get_types()` | Returns `[{iri, label}]` for all types with SHACL shapes |
| Layout definitions | `LAYOUT_DEFINITIONS` in `dashboard/router.py` | Slot names, CSS classes, grid templates already defined |
| Dashboard tab opening | `openDashboardTab(id, name)` in `workspace.js` | Already wired to dockview special-panel routing |
| Explorer section pattern | FAVORITES/VIEWS/SHARED sections in `workspace.html` | Same `explorer-section` + `explorer-section-header` + htmx lazy-load |
| Form CSS | `.form-field`, `.form-actions`, `.mount-form-row` in `workspace.css` | Established input/select/button styling |
| Dynamic form rows | Property editor in `create_class_form.html` | `addPropertyRow()` pattern for repeating form sections |

## Existing Code and Patterns

- `backend/app/dashboard/router.py` — All rendering and API routes. Has `LAYOUT_DEFINITIONS` dict mapping layout names to CSS classes, slot names, and grid templates. New builder routes go here.
- `backend/app/dashboard/service.py` — `DashboardService` with `create()`, `get()`, `list_for_user()`, `update()`, `delete()`. All async, all tested (19 tests).
- `backend/app/dashboard/models.py` — `VALID_LAYOUTS` and `VALID_BLOCK_TYPES` sets for validation. Block config schema documented in docstring.
- `backend/app/templates/browser/ontology/create_class_form.html` — Best reference for complex form UIs. Sections, icon picker, parent class picker, dynamic property rows. Uses `hx-on::config-request` for serializing dynamic JS state into form params (D063).
- `backend/app/templates/browser/_vfs_settings.html` — Mount creation form with strategy-dependent dynamic fields shown/hidden by JS. Good reference for conditional block config fields.
- `backend/app/templates/browser/views_explorer.html` — Explorer tree with model folders, type leaf nodes, `openViewTab()` onclick. Dashboard explorer follows same leaf pattern but simpler (flat list, no grouping).
- `backend/app/templates/browser/partials/favorites_section.html` — Simplest explorer section. htmx lazy-load on `load`, event-driven refresh. Dashboard section follows this pattern.
- `backend/app/views/router.py` lines 49-66 — `available_views()` returns JSON list of all ViewSpecs. Builder fetches this to populate the view-embed block config dropdown.
- `frontend/static/js/workspace.js` lines 713-731 — `openDashboardTab()` already registered on `window`. Builder calls this after successful create/save.
- `frontend/static/js/workspace-layout.js` lines 206-214 — `special-panel` handler routes dashboard tabs to `/browser/dashboard/{id}`. Builder tab needs its own `specialType: 'dashboard-builder'`.

## Constraints

- **JSON API, not form-encoded**: `POST /api/dashboard` and `PATCH /api/dashboard/{id}` expect JSON bodies. The builder form must submit via `fetch()` with `Content-Type: application/json`, not htmx form submission. This matches the mount form pattern in `_vfs_settings.html`.
- **Block config varies by type**: Each block type has different config fields (view-embed needs spec_iri + renderer_type; markdown needs content; create-form needs target_class; object-embed needs object_iri). The form must show/hide config fields based on the selected block type — same pattern as mount strategy fields.
- **Slot assignment**: Blocks must be assigned to named slots that match the selected layout. The layout picker must update available slot options when the layout changes. `LAYOUT_DEFINITIONS[layout]["slots"]` provides the valid slot names.
- **No drag-and-drop**: Builder is form-based only (roadmap explicitly excludes freeform drag-and-drop). Blocks are a vertical list of configuration rows, not a visual grid.
- **Explorer section ordering**: Dashboard section should go between MY VIEWS and SHARED. This positions it with other "user-created content" sections, below system views but above federation content.

## Common Pitfalls

- **D063: htmx form serialization timing** — If using htmx form submission, dynamic JS state (like block configurations) must be serialized in `hx-on::config-request`, not `htmx:beforeRequest`. But since we're using `fetch()` for the JSON API, this doesn't apply. Just build the JSON payload from DOM state in the submit handler.
- **Lucide icons in flex containers** — Any Lucide icons in the builder form's buttons need `flex-shrink: 0` on the SVG (CLAUDE.md rule). Call `lucide.createIcons()` after dynamic DOM insertion (block rows).
- **`select#explorer-mode-select` click targeting** — Per CLAUDE.md browser testing rules, the explorer dropdown is a frequent false-positive target. When verifying the dashboard explorer section, scope browser_find to `#section-dashboards` to avoid mis-targeting.
- **Tab key collision** — The dashboard builder opens as a new special-panel tab. Make sure the tab key is unique (e.g., `dashboard-builder:{id}` for edit, `dashboard-builder:new` for create) to avoid clobbering other tabs.
- **Layout slot mismatch** — If the user changes the layout after assigning blocks to slots, previously valid slot names may become invalid. The builder should either reset slot assignments when layout changes, or auto-map to the new layout's slots.

## Open Risks

- **View spec availability at build time**: The builder fetches `/browser/views/available` to populate the view-embed dropdown. If no models are installed (empty triplestore), this returns `[]` and the view-embed block type is useless. Not a bug — just an edge case to handle gracefully with a "No views available" message.
- **Object IRI input for object-embed blocks**: The object-embed block config needs an `object_iri`. There's no existing IRI picker component. For v1, a text input with the raw IRI is sufficient. A proper search/picker is a nice-to-have but not required for S04.
- **Explorer refresh after create/delete**: After creating or deleting a dashboard, the explorer section should refresh. The favorites pattern uses `HX-Trigger: favoritesRefreshed` → `hx-trigger="load, favoritesRefreshed from:body"`. Dashboard explorer should use the same pattern with a `dashboardsRefreshed` event.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | mindrally/skills@htmx | available (205 installs) — not needed, htmx patterns well-established in codebase |
| FastAPI | wshobson/agents@fastapi-templates | available (6.4K installs) — not needed, existing patterns sufficient |

## Sources

- Block config schemas from `DashboardSpec` model docstring (`backend/app/dashboard/models.py`)
- Layout definitions from `LAYOUT_DEFINITIONS` dict (`backend/app/dashboard/router.py`)
- Form patterns from class creation form (`create_class_form.html`) and mount form (`_vfs_settings.html`)
- Explorer section patterns from `workspace.html` sidebar structure
