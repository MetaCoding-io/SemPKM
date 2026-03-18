---
id: T03
parent: S06
milestone: M009
provides:
  - AppRegistry.get_renderer(type_iri) method for renderer lookup from manifests
  - _get_renderer_override() helper with AppRendererPref conflict resolution
  - get_object() dispatch branch to object_tab_app.html for overridden types
  - object_tab_app.html template with app fragment loading and SHACL edit fallback
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/objects.py
  - backend/app/templates/browser/object_tab_app.html
  - frontend/static/css/workspace.css
  - backend/tests/test_renderer_overrides.py
key_decisions:
  - AppObjectRenderer has no label field — use app name as renderer label
  - Renderer badge in toolbar shows which app is providing the custom view
patterns_established:
  - Renderer override dispatch in get_object() — check AppRegistry first, fall through to default SHACL template
  - AppRendererPref table as tie-breaker when multiple apps claim the same type
observability_surfaces:
  - Logger app.browser.objects at DEBUG logs renderer override dispatch (app_id, matched type, fragment URLs)
  - Logger app.browser.objects at WARNING logs stale AppRendererPref or failed override lookup
  - data-renderer-app attribute on .object-tab DOM element identifies which app is active
  - app-renderer-content class in HTML marks app-served content regions
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Object renderer override dispatch and app renderer template

**Added AppRegistry.get_renderer() method, _get_renderer_override() helper with AppRendererPref conflict resolution, and get_object() dispatch to object_tab_app.html for app-overridden types**

## What Happened

Added `get_renderer(type_iri)` to `AppRegistry` — iterates registered app manifests checking `ui.objectRenderers` for an exact IRI match, returning a dict with `app_id`, `app_name`, `read_fragment`, `edit_fragment`, and `label`.

Created `_get_renderer_override()` async helper in `objects.py` that iterates an object's type IRIs, queries the registry for a renderer match, then checks `AppRendererPref` for a user preference override. Stale preferences (pointing to an app without a renderer) fall back to the registry default with a WARNING log.

Modified `get_object()` to call the override helper after type resolution. When an override is found, the template switches to `object_tab_app.html` and extra context variables are added (`renderer_app_id`, `read_fragment`, `edit_fragment`, `has_custom_edit`, `renderer_label`). When no override exists, the existing `object_tab.html` path is untouched — zero behavior change for existing objects.

Created `object_tab_app.html` template that preserves the full platform toolbar (label, type badge, favorite star, mode toggle) and adds a renderer badge showing which app is providing the view. The read face loads the app's fragment via htmx; the edit face either loads a custom app edit fragment or falls back to the standard SHACL form with CodeMirror body editor.

Added `.app-renderer-content` and `.object-toolbar-renderer-badge` CSS styles to workspace.css.

## Verification

- 13 tests in `test_renderer_overrides.py` all pass — covering get_renderer match/no-match/skip, _get_renderer_override preference override and stale pref fallback, get_object dispatch to both templates, edit fallback, and toolbar preservation
- Full test suite: 1386 passed in 40s, zero regressions
- Syntax check passed on all modified `.py` files
- `grep -c "object_tab_app" objects.py` → 1
- `grep -c "get_renderer" registry.py` → 1
- Slice-level checks: test_right_pane_sections (14 passed), test_app_views_commands (15 passed), test_renderer_overrides (13 passed), endpoint importable confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_renderer_overrides.py -v` | 0 | ✅ pass | 0.64s |
| 2 | `pytest tests/ -x` | 0 | ✅ pass | 40.29s |
| 3 | `python3 -c "import ast; ..."` (syntax) | 0 | ✅ pass | 3.8s |
| 4 | `grep -c "object_tab_app" objects.py` | 0 | ✅ pass | <1s |
| 5 | `grep -c "get_renderer" registry.py` | 0 | ✅ pass | <1s |
| 6 | `pytest tests/test_right_pane_sections.py -v` | 0 | ✅ pass | 0.31s |
| 7 | `pytest tests/test_app_views_commands.py -v` | 0 | ✅ pass | 0.32s |
| 8 | `python -c "from fastapi.testclient import TestClient; ..."` | 0 | ✅ pass | <1s |

## Diagnostics

- **Renderer override active?** Check the response HTML for `GET /browser/object/<iri>` — if `app-renderer-content` class is present with `hx-get` pointing to `/app/<app_id>/_fragments/<fragment>`, the override is active. If absent, default SHACL form is in use.
- **Which app?** The `data-renderer-app` attribute on the `.object-tab` div identifies the rendering app. The toolbar renderer badge also shows it visually.
- **Logger**: `app.browser.objects` at DEBUG logs renderer dispatch details; WARNING logs stale preferences or failed lookups.
- **Override lookup failure**: Any exception in `_get_renderer_override()` is caught and logged; the object falls back to the default SHACL form — never an error page.

## Deviations

- `AppObjectRenderer` model has no `label` field (plan assumed it would). Used app name (`manifest.name`) as the renderer label instead.
- The existing flip card uses opacity/pointer-events (not CSS 3D transforms), so the template follows the same opacity pattern rather than the backface-visibility pattern described in CLAUDE.md for card flips.

## Known Issues

- `test_admin_renderers.py` does not yet exist — it's T04's responsibility.

## Files Created/Modified

- `backend/app/apps/registry.py` — added `get_renderer(type_iri)` method
- `backend/app/browser/objects.py` — added `_get_renderer_override()` helper and renderer dispatch in `get_object()`
- `backend/app/templates/browser/object_tab_app.html` — new template with app fragment loading + toolbar + flip card
- `frontend/static/css/workspace.css` — added `.app-renderer-content` and `.object-toolbar-renderer-badge` styles
- `backend/tests/test_renderer_overrides.py` — 13 tests covering dispatch, preference, fallback, toolbar
