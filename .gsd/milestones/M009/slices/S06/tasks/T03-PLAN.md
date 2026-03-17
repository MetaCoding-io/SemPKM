---
estimated_steps: 7
estimated_files: 5
---

# T03: Object renderer override dispatch and app renderer template

**Slice:** S06 — Frontend Level 2+3 — Workspace Contributions & Renderer Overrides
**Milestone:** M009

## Description

Implement Level 3 frontend integration (APP-09): apps can replace the default SHACL form for specific types with custom read/edit renderers. Modifies `get_object()` with a conditional branch that checks `AppRegistry` for a renderer matching the object's type, with conflict resolution via the `AppRendererPref` table. Creates `object_tab_app.html` template that loads app fragments while preserving platform toolbar chrome.

## Steps

1. **Add `get_renderer()` method to `AppRegistry`** (`backend/app/apps/registry.py`):
   - Signature: `get_renderer(self, type_iri: str) -> dict | None`
   - Iterate `self._manifests` for all registered apps. For each, check `ui.objectRenderers` list for entries where `type` matches `type_iri` (full IRI comparison — no prefix expansion for v1).
   - If match found, return `{ "app_id": app_id, "read_fragment": renderer.modes.read, "edit_fragment": renderer.modes.edit or None, "label": renderer.label }`.
   - If multiple apps match, return the first found. (Conflict resolution via `AppRendererPref` happens in the calling code, not here.)
   - If no match, return `None`.
   - Check the manifest schema for the exact field names: the `AppObjectRenderer` model should have `type`, `label`, `modes` (with `read` and optional `edit` fragment paths).

2. **Add renderer preference lookup helper** in `backend/app/browser/objects.py`:
   - Create `async def _get_renderer_override(db, registry, type_iris)` helper:
     - For each `type_iri` in `type_iris`, call `registry.get_renderer(type_iri)`.
     - If a match is found, query `AppRendererPref` table for a row with `(type_iri=type_iri, mode='read')`:
       - If a pref row exists AND its `app_id` differs from registry result → use the pref row's app_id. Call `registry.get_renderer()` on that app's manifest directly (or look up by app_id in manifests).
       - If no pref row or pref matches registry result → use registry result as-is.
     - Return the first match found (iterate types in order, first match wins).
     - Return `None` if no renderers match any type.
   - Import `AppRendererPref` from `backend/app/apps/models.py`. Use `db.execute(select(AppRendererPref).where(...))` pattern.

3. **Modify `get_object()` to dispatch to app renderer** (`backend/app/browser/objects.py`):
   - After the existing `type_iris` resolution (around line 107), call `_get_renderer_override(db, registry, type_iris)`.
   - `registry` is `request.app.state.app_registry` — check if this is already accessible in the function scope. If not, add it.
   - `db` is the database session — check how the function gets its DB session (dependency injection via FastAPI).
   - If override found:
     - Set template to `"browser/object_tab_app.html"` instead of `"browser/object_tab.html"`.
     - Add to template context: `renderer_app_id`, `read_fragment` (URL: `/app/{app_id}/_fragments/{read_fragment}?iri={object_iri}`), `edit_fragment` (URL or None), `has_custom_edit` (bool), `renderer_label`.
   - If no override: render as usual with `"browser/object_tab.html"`. No changes to existing flow.
   - Important: preserve all existing context variables (object data, type info, favorite status, etc.) — the app template needs the toolbar context.

4. **Create `object_tab_app.html` template** at `backend/app/templates/browser/object_tab_app.html`:
   - Start from the existing `object_tab.html` structure for reference. The template needs:
     - **Toolbar**: identical to `object_tab.html` — label, type badge/icon, favorite star toggle, read/edit mode toggle button. All using the same template variables.
     - **Read face** (flip card front): Instead of the SHACL form, render `<div hx-get="{{ read_fragment }}" hx-trigger="load" hx-swap="innerHTML" class="app-renderer-content"></div>`. This loads the app's custom read view.
     - **Edit face** (flip card back): Two cases controlled by `has_custom_edit`:
       - If `has_custom_edit`: `<div hx-get="{{ edit_fragment }}" hx-trigger="load" hx-swap="innerHTML" class="app-renderer-content"></div>`
       - If not: fall back to the standard SHACL edit form (include the same form partial used in `object_tab.html`).
     - The CSS 3D flip card mechanism must work identically — `backface-visibility: hidden`, `display: none` defense, `toggleObjectMode()` JS function. Reference CLAUDE.md rules on flip card animation.
   - The template extends the same base/block structure as `object_tab.html`. Check what blocks/base template `object_tab.html` uses.

5. **Add CSS for app renderer content** (if needed):
   - Add `.app-renderer-content` styles to `frontend/static/css/workspace.css` — full width/height, proper overflow handling.
   - App fragments should inherit platform theme variables (colors, fonts) since they're rendered in the platform DOM, not an iframe.

6. **Write tests** in `backend/tests/test_renderer_overrides.py`:
   - Test: `AppRegistry.get_renderer()` returns correct dict for matching type
   - Test: `get_renderer()` returns None for non-matching type
   - Test: `get_renderer()` skips apps with no objectRenderers declared
   - Test: `get_object()` renders `object_tab_app.html` when renderer override exists
   - Test: `get_object()` renders `object_tab.html` when no override (default behavior preserved)
   - Test: `AppRendererPref` preference overrides registry default — if pref says app-B for a type, but app-A is first in registry, pref wins
   - Test: edit fallback — when app renderer has no edit mode, template gets `has_custom_edit=False`
   - Test: toolbar variables (label, type, favorite) preserved in app renderer template context
   - Mock setup: mock `app_registry` with manifests declaring objectRenderers, mock triplestore for object data and types, mock DB session with AppRendererPref rows.

7. **Verify no regressions**: `python -m pytest backend/tests/ -x --timeout=30`

## Must-Haves

- [ ] `AppRegistry.get_renderer(type_iri)` correctly finds renderer from running app manifests
- [ ] `get_object()` dispatches to `object_tab_app.html` when a renderer override matches the object's type
- [ ] `get_object()` falls back to `object_tab.html` when no override exists (zero behavior change for existing objects)
- [ ] `AppRendererPref` table lookup overrides registry default for conflict resolution
- [ ] `object_tab_app.html` preserves toolbar chrome (label, type badge, favorite, mode toggle)
- [ ] Read face loads app fragment via htmx; edit face falls back to SHACL form when no custom edit renderer
- [ ] Tests covering: match, no-match, preference override, edit fallback, toolbar context preservation

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_renderer_overrides.py -v` — all tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/ -x --timeout=30` — zero regressions
- `grep -c "object_tab_app" backend/app/browser/objects.py` → ≥1
- `grep -c "get_renderer" backend/app/apps/registry.py` → ≥1

## Inputs

- `backend/app/browser/objects.py` — `get_object()` function at line 54. After type resolution (~line 107), the dispatch check goes here. Uses `request.app.state.templates` for rendering. Check how DB session and triplestore client are accessed.
- `backend/app/apps/registry.py` — `AppRegistry` class. T01 added `get_right_pane_contributions()`. Now add `get_renderer()`.
- `backend/app/templates/browser/object_tab.html` — reference for toolbar structure and flip card mechanism. The app template mirrors this.
- `backend/app/apps/models.py` — `AppRendererPref` SQLAlchemy model with composite PK `(type_iri, mode)` and `app_id` column.
- `backend/app/apps/manifest.py` or `backend/app/models/manifest.py` — `AppObjectRenderer` model with `type`, `label`, `modes` (containing `read` and optional `edit` fragment paths).
- S05 forward intelligence: `AppRegistry` renderer/contribution metadata is available via manifests.

## Expected Output

- `backend/app/apps/registry.py` — new `get_renderer()` method
- `backend/app/browser/objects.py` — renderer override dispatch in `get_object()`, helper `_get_renderer_override()`
- `backend/app/templates/browser/object_tab_app.html` — new template with app fragment loading + toolbar + flip card
- `frontend/static/css/workspace.css` — `.app-renderer-content` styles (if needed)
- `backend/tests/test_renderer_overrides.py` — ≥8 tests covering dispatch, preference, fallback

## Observability Impact

- **New runtime signal:** Logger `app.browser.objects` at DEBUG level logs when renderer override dispatches to `object_tab_app.html` (app_id, type_iri, fragment URLs). At WARNING level logs failures during renderer lookup (with graceful fallback to default SHACL form).
- **Inspection surface:** `GET /object/<iri>` response — inspect response HTML for `app-renderer-content` class presence to confirm renderer override is active. `SELECT * FROM app_renderer_prefs` shows active renderer preference overrides.
- **Failure visibility:** If `AppRegistry.get_renderer()` raises or returns invalid data, `get_object()` falls back silently to the default `object_tab.html` — logged at WARNING. If the app fragment URL returns 404/500, the htmx div shows an error state in the browser (visible in devtools Network tab).
- **Redaction constraints:** None.
