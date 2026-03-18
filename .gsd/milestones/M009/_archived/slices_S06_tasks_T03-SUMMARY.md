---
id: T03
parent: S06
milestone: M009
provides:
  - Object renderer override dispatch in get_object() — apps can replace default SHACL form for specific types
  - AppRegistry.get_renderer() and get_renderer_for_app() methods for type-based renderer lookup
  - _get_renderer_override() helper with AppRendererPref conflict resolution
  - object_tab_app.html template with htmx fragment loading + toolbar chrome + flip card mechanism
  - .app-renderer-content CSS styles for app fragment containers
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/objects.py
  - backend/app/templates/browser/object_tab_app.html
  - frontend/static/css/workspace.css
  - backend/tests/test_renderer_overrides.py
key_decisions:
  - none (implementation followed plan — full IRI matching for v1, first-match-wins in registry, AppRendererPref for conflict override)
patterns_established:
  - Renderer override dispatch pattern: registry lookup → pref table override → fallback to default template. Wrapped in try/except so any failure degrades to standard SHACL form.
  - App template mirrors platform toolbar chrome (label, type badge, favorite, mode toggle) but replaces read/edit face content with htmx-loaded app fragments
observability_surfaces:
  - Logger app.browser.objects at DEBUG logs renderer override details (app_id, type, fragment URLs) when active
  - Logger app.browser.objects at WARNING logs stale AppRendererPref entries and override lookup failures
  - HTML inspection: presence of .app-renderer-content and hx-get="/app/{app_id}/_fragments/..." indicates active override
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Object renderer override dispatch and app renderer template

**Implemented app renderer override dispatch in get_object() with AppRendererPref conflict resolution and object_tab_app.html template for htmx fragment loading**

## What Happened

All implementation was already in place from prior work within this slice. Verified the complete implementation:

1. **AppRegistry.get_renderer()** and **get_renderer_for_app()** methods iterate registered app manifests checking `ui.objectRenderers` for type IRI matches. Returns dict with app_id, app_name, read/edit fragment paths, and renderer label.

2. **_get_renderer_override() helper** in objects.py iterates type_iris, calls registry, then queries AppRendererPref table for conflict resolution. Handles stale pref rows (preferred app no longer has renderer) by falling back to registry default.

3. **get_object() dispatch** — after type resolution, calls _get_renderer_override wrapped in try/except. On match, adds renderer context vars and renders object_tab_app.html. On no match or error, renders object_tab.html unchanged.

4. **object_tab_app.html** — mirrors object_tab.html toolbar (label, type badge, favorite star, mode toggle), replaces read face with htmx `hx-get` to app fragment URL, edit face conditionally uses app edit fragment or falls back to SHACL form + body editor. Includes app badge showing renderer label with puzzle icon. CSS 3D flip card mechanism identical to platform template.

5. **CSS** — `.app-renderer-content` styles (full width/height, overflow auto, padding) and `.app-renderer-loading` skeleton animation added to workspace.css.

6. **Tests** — 19 tests in test_renderer_overrides.py covering: registry get_renderer match/no-match/no-renderers/multi-app/edit-fragment/app-specific/unknown-app, helper with pref override/stale-pref/first-type-wins/no-match, and endpoint dispatch to app template/default template/toolbar preservation/edit fallback/custom edit/embed mode/registry error fallback.

## Verification

- `pytest backend/tests/test_renderer_overrides.py -v` → **19/19 passed**
- `pytest backend/tests/ -x --ignore=backend/tests/test_sdk_integration.py` → **1201 passed**, zero regressions
- `grep -c "object_tab_app" backend/app/browser/objects.py` → 1 ✓
- `grep -c "get_renderer" backend/app/apps/registry.py` → 2 ✓
- Python AST syntax check on all modified files → OK
- Slice-level checks:
  - `test_right_pane_sections.py` → 16/16 passed ✓
  - `test_app_views_commands.py` → 13/13 passed ✓
  - `test_renderer_overrides.py` → 19/19 passed ✓
  - `test_admin_renderers.py` → 13/13 passed ✓
- Pre-existing failure: `test_sdk_integration.py` fails due to missing `sempkm_app_sdk` module (not related to this task)

## Diagnostics

- **Renderer override active?** Check GET `/browser/object/<iri>` response HTML for `.app-renderer-content` class and `hx-get="/app/<app_id>/_fragments/<fragment>"` attributes
- **Logger**: `app.browser.objects` at DEBUG shows `Renderer override for <iri>: app=<id> type=<type> read=<url> edit=<url>`
- **Stale pref warning**: Logger WARNING when AppRendererPref points to app without renderer for that type
- **Graceful degradation**: Any exception in override lookup logged WARNING, falls back silently to object_tab.html

## Deviations

None — all implementation matched the plan. Steps 1-5 were already implemented; this execution verified completeness and ran all tests.

## Known Issues

- `test_sdk_integration.py` has pre-existing failure (missing `sempkm_app_sdk` module) — unrelated to this task

## Files Created/Modified

- `backend/app/apps/registry.py` — `get_renderer()` and `get_renderer_for_app()` methods on AppRegistry
- `backend/app/browser/objects.py` — `_get_renderer_override()` helper + dispatch branch in `get_object()`
- `backend/app/templates/browser/object_tab_app.html` — new template with app fragment htmx loading + toolbar + flip card
- `frontend/static/css/workspace.css` — `.app-renderer-content` and `.app-renderer-loading` styles
- `backend/tests/test_renderer_overrides.py` — 19 tests covering registry, helper, and endpoint dispatch
- `.gsd/milestones/M009/slices/S06/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
