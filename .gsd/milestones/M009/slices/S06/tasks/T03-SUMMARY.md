---
id: T03
parent: S06
milestone: M009
provides:
  - AppRegistry.get_renderer(type_iri) method returning renderer info dict or None
  - AppRegistry.get_renderer_for_app(app_id, type_iri) for pref-override lookups
  - _get_renderer_override(db, registry, type_iris) async helper with AppRendererPref conflict resolution
  - get_object() dispatch to object_tab_app.html when renderer override matches
  - object_tab_app.html template with htmx fragment loading + toolbar chrome + flip card
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/objects.py
  - backend/app/templates/browser/object_tab_app.html
  - frontend/static/css/workspace.css
  - backend/tests/test_renderer_overrides.py
key_decisions:
  - Used app name as renderer_label since AppObjectRenderer model has no label field (only type + modes)
  - Added get_renderer_for_app() as separate method for pref-override lookups to avoid re-iterating all manifests
  - Renderer override check wrapped in try/except with WARNING log — any failure silently falls back to default SHACL form
  - Embed mode (embed=1) is unaffected by renderer overrides — embeds always use object_embed.html
patterns_established:
  - Renderer override dispatch pattern: registry lookup → pref table check → template swap with context augmentation
  - App renderer template pattern: platform toolbar chrome preserved, content area replaced with htmx fragment div
  - Edit fallback pattern: has_custom_edit=False → standard SHACL form + body editor on edit face
observability_surfaces:
  - Logger app.browser.objects at DEBUG logs renderer override dispatch (app_id, type, fragment URLs)
  - Logger app.browser.objects at WARNING logs renderer lookup failures with traceback
  - HTML response contains app-renderer-content class when override active (inspectable)
  - SELECT * FROM app_renderer_prefs shows active preference overrides
duration: 25min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Object renderer override dispatch and app renderer template

**Added renderer override dispatch in get_object() — apps can replace default SHACL form for specific types with custom read/edit renderers loaded via htmx fragments.**

## What Happened

Implemented Level 3 frontend integration (APP-09) in three layers:

1. **Registry methods** (`registry.py`): Added `get_renderer(type_iri)` that iterates registered app manifests checking `ui.objectRenderers` for type match, returning `{app_id, app_name, read_fragment, edit_fragment, renderer_label}` or None. Added `get_renderer_for_app(app_id, type_iri)` for targeted lookup when AppRendererPref overrides the default.

2. **Endpoint dispatch** (`objects.py`): Added `_get_renderer_override()` async helper that iterates type_iris, checks registry for match, then consults `AppRendererPref` table for user preference overrides. In `get_object()`, after type resolution and before template rendering, calls the helper and dispatches to `object_tab_app.html` if override found. The dispatch adds `renderer_app_id`, `read_fragment` (URL), `edit_fragment` (URL or None), `has_custom_edit`, and `renderer_label` to the template context while preserving all existing context variables.

3. **App renderer template** (`object_tab_app.html`): Mirrors `object_tab.html` toolbar (label, type badge, favorite star, mode toggle) plus an app badge showing which app is rendering. Read face loads app fragment via `hx-get` with skeleton loading state. Edit face: if `has_custom_edit`, loads app edit fragment; otherwise falls back to standard SHACL form + body editor identical to `object_tab.html`.

4. **CSS** (`workspace.css`): Added `.app-renderer-content` (full width/height, overflow auto, padding), `.app-renderer-loading` with skeleton pulse animation, and `.object-toolbar-app-badge` for the renderer label badge in toolbar.

## Verification

- `python -m pytest backend/tests/test_renderer_overrides.py -v` — 19/19 passed (7 registry unit tests, 5 helper tests, 7 endpoint dispatch tests)
- `python -m pytest backend/tests/ -x --ignore=backend/tests/test_sdk_integration.py -q` — 1181 passed, zero regressions (SDK integration test excluded: pre-existing module install issue)
- `python -m pytest backend/tests/test_right_pane_sections.py -v` — 16/16 passed
- `python -m pytest backend/tests/test_app_views_commands.py -v` — 13/13 passed
- `grep -c "object_tab_app" backend/app/browser/objects.py` → 1
- `grep -c "get_renderer" backend/app/apps/registry.py` → 2
- All modified .py files pass `ast.parse()` syntax check
- `from app.browser.apps import apps_router` — importable without errors

## Diagnostics

- **Renderer dispatch logging:** Logger `app.browser.objects` at DEBUG logs app_id, type, and fragment URLs when dispatch occurs
- **Failure fallback:** If `_get_renderer_override()` raises, WARNING logged with traceback, request silently falls back to standard `object_tab.html`
- **HTML inspection:** `app-renderer-content` class present in response HTML indicates renderer override is active
- **Pref table:** `SELECT * FROM app_renderer_prefs` shows which types have user-set renderer preferences

## Deviations

- Plan referenced `renderer.label` from manifest, but `AppObjectRenderer` model has no `label` field (only `type` + `modes`). Used `manifest.name` (app name) as `renderer_label` instead.
- Added `get_renderer_for_app()` as a separate method (not in plan) — needed for efficient pref-override lookup.
- Tests use 19 tests instead of the plan's ≥8 — expanded coverage.
- `test_sdk_integration.py` excluded from full regression run due to pre-existing `sempkm_app_sdk` install failure.

## Known Issues

- `test_sdk_integration.py` fails to collect due to missing `sempkm_app_sdk` module — pre-existing, not introduced by this task.

## Files Created/Modified

- `backend/app/apps/registry.py` — added `get_renderer()` and `get_renderer_for_app()` methods
- `backend/app/browser/objects.py` — added `AppRendererPref` import, `_get_renderer_override()` helper, renderer dispatch in `get_object()`
- `backend/app/templates/browser/object_tab_app.html` — new template with app fragment loading, platform toolbar chrome, flip card mechanism
- `frontend/static/css/workspace.css` — added `.app-renderer-content`, `.app-renderer-loading`, `.object-toolbar-app-badge` styles
- `backend/tests/test_renderer_overrides.py` — 19 tests covering registry, helper, and endpoint dispatch
- `.gsd/milestones/M009/slices/S06/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
