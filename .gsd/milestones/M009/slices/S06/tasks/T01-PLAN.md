---
estimated_steps: 8
estimated_files: 6
---

# T01: Dynamic right pane sections endpoint and JS refactor

**Slice:** S06 — Frontend Level 2+3 — Workspace Contributions & Renderer Overrides
**Milestone:** M009

## Description

Replace the 3 hardcoded `<details>` blocks (relations, lint, comments) in the workspace right pane with a dynamic htmx endpoint that merges platform sections + app contributions. This is the biggest structural change in S06 — it touches `workspace.html` layout, `workspace.js` section loading, and introduces a new endpoint + template. D153 directs this approach. The inbox and collaboration panels stay as static `{% include %}` directives (they don't depend on the current object).

## Steps

1. **Add `get_right_pane_contributions()` to `AppRegistry`** (`backend/app/apps/registry.py`):
   - Method signature: `get_right_pane_contributions(self, type_iris: list[str]) -> list[dict]`
   - Iterate `self._manifests` for running apps (check `self._manager.get_status(app_id).status == 'running'` or just iterate registered apps — the manifest is only registered for installed apps).
   - For each app manifest, check `ui.rightPane` contributions. If `targetTypes` is empty/None, include for all objects. If `targetTypes` is set, include only when any of `type_iris` matches.
   - Return list of dicts: `{app_id, label, icon, fragment, priority, app_name}` sorted by `priority` (ascending).
   - Note: `AppRegistry` is at `backend/app/apps/registry.py`. Check its current API — it has `get_manifest(app_id)`, `list_apps()`. The method needs access to manifests' `ui.rightPane` field. Check the manifest schema at `backend/app/apps/manifest.py` (or `backend/app/models/manifest.py`) for the `AppRightPaneContribution` model — it should have `label`, `icon`, `fragment`, `priority`, `targetTypes`.

2. **Create `GET /browser/apps/right-pane-sections` endpoint** in `backend/app/browser/apps.py`:
   - Accepts query param `iri` (the object IRI).
   - Query the object's `rdf:type` via a lightweight SPARQL query: `SELECT ?type WHERE { <{iri}> a ?type }` using the existing triplestore client pattern in browser endpoints.
   - Call `registry.get_right_pane_contributions(type_iris)` to get app sections.
   - Build template context with: platform sections list (relations, lint, comments — always present), app sections list (from registry), and the object `iri`.
   - Render `right_pane_sections.html`.
   - Use the existing pattern from `apps.py` endpoints: `request.app.state.app_registry`, `request.app.state.templates`, triplestore client from `request.app.state.triplestore` or the helper pattern used in objects.py.

3. **Create `right_pane_sections.html` template** at `backend/app/templates/browser/right_pane_sections.html`:
   - Platform sections first — 3 `<details>` blocks matching the current structure in `workspace.html`:
     - Relations: `<details>` with `hx-get="/browser/objects/{iri}/relations-content"` `hx-trigger="toggle once"` (copy exact attributes from current workspace.html lines ~175-195)
     - Lint: `<details>` with `hx-get="/browser/objects/{iri}/lint-content"` `hx-trigger="toggle once"`
     - Comments: `<details>` with `hx-get="/browser/objects/{iri}/comments-content"` `hx-trigger="toggle once"`
   - App contribution sections next — for each app section: `<details>` with `hx-get="/app/{app_id}/_fragments/{fragment}?iri={iri}"` `hx-trigger="toggle once"`. Use Lucide icon if specified. Include app name in a subtle badge/label.
   - Important: Use the `iri` variable passed from the endpoint. The hx-get URLs must be properly URL-encoded.

4. **Modify `workspace.html` right pane** (`backend/app/templates/browser/workspace.html`):
   - Find the right pane area (lines ~175-215) containing the 3 hardcoded `<details>` blocks for relations, lint, comments.
   - Replace those 3 `<details>` blocks with a single `<div id="right-pane-dynamic"></div>` container.
   - Keep `{% include "browser/partials/inbox_panel.html" %}` and `{% include "browser/partials/collaboration_panel.html" %}` as static elements below (or above) the dynamic container — they are self-loading via their own `hx-trigger="load"`.
   - The dynamic container will be populated by JS calling the new endpoint.

5. **Refactor `workspace.js` right pane loading**:
   - Find the current `loadRightPaneSection(iri, section)` function (~line 262) and the 3 hardcoded calls at ~lines 254-256 and ~2446-2448.
   - Replace with a single `loadRightPane(objectIri)` function that:
     - Creates or reuses an `AbortController` stored as `window._rightPaneAbort`
     - Cancels any pending request: `if (window._rightPaneAbort) window._rightPaneAbort.abort()`
     - Creates new AbortController
     - Fetches `/browser/apps/right-pane-sections?iri={encodeURIComponent(objectIri)}`
     - On success, swaps innerHTML of `#right-pane-dynamic`
     - After swap, calls `lucide.createIcons()` on the container (app sections may use Lucide icons)
   - Update all call sites that currently call `loadRightPaneSection()` to call `loadRightPane(objectIri)` instead.
   - The old `loadRightPaneSection()` function can be removed entirely.
   - Check `sempkm:tab-activated` event handler and any other places that trigger right pane loading.

6. **Handle edge cases**:
   - When no object tab is active (e.g., dashboard tab), the right pane should either be empty or show only static panels. The `loadRightPane()` should handle this — only call when `isObjectTab` is true in the tab-activated event.
   - When the endpoint returns an error, the right pane should show platform sections only (graceful degradation). The endpoint itself should catch registry errors and fall back.

7. **Write tests** in `backend/tests/test_right_pane_sections.py`:
   - Test: no apps registered → returns only platform sections (relations, lint, comments)
   - Test: app with rightPane contribution matching object type → returns platform + app section
   - Test: app with rightPane contribution NOT matching object type → returns platform only
   - Test: app with empty targetTypes (all objects) → always included
   - Test: multiple app sections sorted by priority
   - Test: stopped app contributions excluded
   - Test: unknown object IRI (no types) → returns platform sections only
   - Use the test pattern from `test_app_browser.py`: FastAPI TestClient + Jinja2Blocks + mock app_registry/app_manager on app.state. Mock the triplestore client to return type IRIs for the SPARQL query.

8. **Verify no regressions**: `python -m pytest backend/tests/ -x --timeout=30`

## Must-Haves

- [ ] `AppRegistry.get_right_pane_contributions(type_iris)` returns correct sections filtered by targetTypes and sorted by priority
- [ ] `GET /browser/apps/right-pane-sections?iri=` endpoint returns merged platform + app sections HTML
- [ ] `workspace.html` right pane uses dynamic container instead of hardcoded `<details>` blocks
- [ ] `workspace.js` uses single `loadRightPane()` with AbortController for request cancellation
- [ ] Inbox and collaboration panels remain as static `{% include %}` directives (not in dynamic container)
- [ ] Platform sections (relations, lint, comments) always appear even when no apps are registered
- [ ] Tests covering: no apps, matching type, non-matching type, empty targetTypes, priority ordering, stopped apps excluded

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_right_pane_sections.py -v` — all tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/ -x --timeout=30` — zero regressions
- `grep -c "right-pane-dynamic" backend/app/templates/browser/workspace.html` → ≥1
- `grep -c "loadRightPane" frontend/static/js/workspace.js` → ≥1
- `grep -c "loadRightPaneSection" frontend/static/js/workspace.js` → 0 (old function removed)

## Inputs

- `backend/app/browser/apps.py` — existing app browser endpoints from S04 (explorer, page). New endpoint goes here.
- `backend/app/templates/browser/workspace.html` — current right pane structure at lines ~175-215. Three hardcoded `<details>` blocks for relations, lint, comments. Below them: `{% include "browser/partials/inbox_panel.html" %}` and `{% include "browser/partials/collaboration_panel.html" %}`.
- `frontend/static/js/workspace.js` — `loadRightPaneSection(iri, section)` at ~line 262. Three hardcoded calls at ~lines 254-256 and ~2446-2448 in the tab-activated event handler.
- `backend/app/apps/registry.py` — `AppRegistry` with `get_manifest(app_id)`, `list_apps()`. Manifest schema has `AppRightPaneContribution` with fields: `label`, `icon`, `fragment`, `priority`, `targetTypes`.
- `backend/tests/test_app_browser.py` — reference test pattern for app browser endpoints.
- S04 summary: endpoints use `request.app.state.templates` (shared Jinja2Blocks instance), `request.app.state.app_registry`, and `request.app.state.app_manager`.

## Expected Output

- `backend/app/apps/registry.py` — new `get_right_pane_contributions()` method
- `backend/app/browser/apps.py` — new `right_pane_sections` endpoint
- `backend/app/templates/browser/right_pane_sections.html` — new template with platform + app sections
- `backend/app/templates/browser/workspace.html` — right pane refactored to dynamic container
- `frontend/static/js/workspace.js` — `loadRightPane()` replaces `loadRightPaneSection()`, AbortController added
- `backend/tests/test_right_pane_sections.py` — ≥7 tests covering all scenarios
