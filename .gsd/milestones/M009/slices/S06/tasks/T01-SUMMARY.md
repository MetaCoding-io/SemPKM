---
id: T01
parent: S06
milestone: M009
provides:
  - AppRegistry.get_right_pane_contributions() method for type-filtered app section collection
  - GET /browser/apps/right-pane-sections endpoint merging platform + app sections
  - Dynamic right pane container in workspace.html replacing hardcoded <details> blocks
  - loadRightPane() JS function with AbortController request cancellation
  - right_pane_sections.html template rendering platform + app contribution sections
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/apps.py
  - backend/app/templates/browser/right_pane_sections.html
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - backend/tests/test_right_pane_sections.py
key_decisions:
  - Used request.app.state.triplestore_client pattern (not Depends) since apps router has no DI for triplestore
  - Running-app filtering done in endpoint (async status check) rather than in registry method (sync) — registry returns all registered contributions, endpoint filters by running status
  - Platform sections use hx-trigger="load" for immediate content fetch on swap (not "toggle once" which would require user click)
  - Used new TemplateResponse(request, name) signature for new endpoint to avoid deprecation warning
patterns_established:
  - Dynamic right pane pattern: endpoint returns full section HTML → JS swaps into #right-pane-dynamic → htmx.process() on container for nested htmx attributes
  - AbortController cancellation pattern for rapid tab switching — stored on window._rightPaneAbort
observability_surfaces:
  - Logger app.browser.apps: DEBUG with type count + app section count per request, WARNING on triplestore/registry failures
  - GET /browser/apps/right-pane-sections?iri=<IRI> inspectable directly — returns platform + app section HTML
  - window._rightPaneAbort in devtools for cancellation state inspection
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Dynamic right pane sections endpoint and JS refactor

**Replaced 3 hardcoded right pane `<details>` blocks with a dynamic endpoint that merges platform sections + app contributions, filtered by object type.**

## What Happened

Added `get_right_pane_contributions(type_iris)` to `AppRegistry` — iterates registered app manifests, collects `ui.contributions.rightPane` entries matching the object's type IRIs (wildcard `["*"]` matches all), returns sorted by priority ascending.

Created `GET /browser/apps/right-pane-sections?iri=` endpoint in `apps.py` that: queries the triplestore for the object's rdf:type IRIs, filters contributions to running apps only, and renders the `right_pane_sections.html` template with platform sections (relations, lint, comments) always present plus any matching app contributions.

The template renders platform `<details>` blocks with `hx-get` URLs for lazy content loading (same pattern as the old hardcoded blocks, but now with `hx-trigger="load"` since they're swapped in dynamically), followed by app contribution `<details>` blocks loading fragments from `/app/{app_id}/_fragments/{fragment}`.

In `workspace.html`, replaced the three hardcoded `<details>` blocks with a single `<div id="right-pane-dynamic">`. Inbox and collaboration panels remain as static `{% include %}` directives below the dynamic container.

In `workspace.js`, replaced `loadRightPaneSection(iri, section)` (called 3x per tab switch) with `loadRightPane(objectIri)` — a single fetch to the new endpoint with AbortController for request cancellation on rapid tab switching. Updated all 5 call sites: initial object load, objectSaved event, relation delete, lint-after-save refresh, and trigger-validation handler. The `setContextualPanelActive(false)` handler now clears the dynamic container and cancels any in-flight request.

## Verification

- `python -m pytest backend/tests/test_right_pane_sections.py -v` — 16/16 passed (6 registry unit tests + 10 endpoint tests)
- `python -m pytest backend/tests/ -x -v` — 1156/1156 passed, zero regressions
- `grep -c "right-pane-dynamic" workspace.html` → 1 ✓
- `grep -c "loadRightPane" workspace.js` → 8 ✓
- `grep -c "loadRightPaneSection" workspace.js` → 0 ✓
- All modified .py files pass `ast.parse()` ✓

## Diagnostics

- `GET /browser/apps/right-pane-sections?iri=<IRI>` — curl directly to inspect rendered HTML for any object
- Logger `app.browser.apps` at DEBUG level logs type count and app section count per request
- Logger `app.browser.apps` at WARNING level logs triplestore query failures and registry errors (with graceful fallback to platform-only sections)
- `window._rightPaneAbort` in browser devtools — check `.signal.aborted` to verify cancellation behavior

## Deviations

- Platform sections use `hx-trigger="load"` instead of `hx-trigger="toggle once"` — since sections are swapped in dynamically (already visible), "toggle once" would require user to close/reopen each `<details>`. "load" triggers immediately on swap, matching the old behavior where JS fetched content on tab activation.
- Used `request.app.state.triplestore_client` directly instead of `Depends(get_triplestore_client)` — the apps router doesn't have triplestore DI set up, and adding it would require changing all existing endpoint signatures. This is consistent with how workspace.py endpoints access the client.

## Known Issues

- Pre-existing DeprecationWarning on the existing `apps_explorer` and `app_page` endpoints (old TemplateResponse signature) — not addressed since those are S04 code and not in scope for this task.

## Files Created/Modified

- `backend/app/apps/registry.py` — added `get_right_pane_contributions(type_iris)` method, TYPE_CHECKING import for AppManager
- `backend/app/browser/apps.py` — added `right_pane_sections` endpoint with triplestore type query and running-app filtering
- `backend/app/templates/browser/right_pane_sections.html` — new template with platform sections + app contribution loop
- `backend/app/templates/browser/workspace.html` — replaced 3 hardcoded `<details>` blocks with `<div id="right-pane-dynamic">`
- `frontend/static/js/workspace.js` — replaced `loadRightPaneSection()` with `loadRightPane()` + AbortController, updated all call sites
- `backend/tests/test_right_pane_sections.py` — 16 tests covering registry method and endpoint (no apps, matching/non-matching types, wildcard, priority ordering, stopped apps excluded, triplestore error graceful degradation)
