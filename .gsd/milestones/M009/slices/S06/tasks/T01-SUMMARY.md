---
id: T01
parent: S06
milestone: M009
provides:
  - GET /browser/apps/right-pane-sections endpoint merging platform + app contributions
  - AppRegistry.get_right_pane_contributions() method
  - Dynamic right-pane container in workspace.html
  - loadRightPane() JS function with AbortController request cancellation
  - refreshRightPaneSection() for targeted single-section reloads
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/apps.py
  - backend/app/templates/browser/right_pane_sections.html
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - backend/tests/test_right_pane_sections.py
key_decisions:
  - Kept a lightweight refreshRightPaneSection() for targeted reloads (lint after validation, relations after delete) instead of reloading all sections via loadRightPane()
  - Platform sections use hx-trigger="load once" in the dynamic template rather than JS-driven fetch, letting htmx handle lazy loading after the container swap
  - workspace.html retains static fallback <details> blocks inside #right-pane-dynamic for the initial page load before JS hydrates
patterns_established:
  - Dynamic right-pane sections via endpoint + container swap pattern — app contributions injected alongside platform sections
observability_surfaces:
  - GET /browser/apps/right-pane-sections?iri=<IRI> returns inspectable HTML of merged platform + app sections
  - Logger app.browser.apps emits DEBUG with type count + app section count per request
  - Logger app.browser.apps emits WARNING on triplestore or registry failures (graceful degradation)
  - window._rightPaneAbort AbortController visible in browser devtools
duration: 25m
verification_result: passed
completed_at: 2026-03-18T09:42Z
blocker_discovered: false
---

# T01: Dynamic right pane sections endpoint and JS refactor

**Replaced 3 hardcoded right-pane <details> blocks and 3 JS loadRightPaneSection() calls with a single dynamic endpoint that merges platform sections + app contributions, with AbortController request cancellation.**

## What Happened

Added `get_right_pane_contributions(type_iris)` to `AppRegistry` — iterates registered app manifests, collects `ui.contributions.rightPane` entries whose `targetTypes` match (wildcard `*` or explicit IRI overlap), returns sorted by priority ascending.

Created `GET /browser/apps/right-pane-sections?iri=` endpoint in `apps.py` — queries the object's `rdf:type` via SPARQL, calls the registry helper, and renders `right_pane_sections.html` with platform sections (relations, lint, comments) always first, followed by any app contributions. Gracefully degrades to platform-only sections on triplestore or registry errors.

Created `right_pane_sections.html` template with platform `<details>` blocks using `hx-trigger="load once"` for lazy content loading, followed by app contribution `<details>` blocks loading fragments from `/app/{app_id}/_fragments/{fragment}?iri={iri}`.

Refactored `workspace.html` right pane: the 3 hardcoded `<details>` blocks are now inside a `<div id="right-pane-dynamic">` container. Static fallback content remains for initial page load. Inbox and collaboration panels kept as static `{% include %}` directives outside the dynamic container.

Refactored `workspace.js`: replaced `loadRightPaneSection()` with `loadRightPane(objectIri)` that fetches the dynamic endpoint and swaps `#right-pane-dynamic` innerHTML with AbortController cancellation. Added `refreshRightPaneSection(objectIri, section)` for targeted single-section reloads (used by lint-after-validation and relations-after-delete flows). Updated all 6 call sites.

## Verification

- 14/14 tests pass in `test_right_pane_sections.py` covering: no apps, matching type, non-matching type, wildcard targetTypes, priority ordering, unknown IRI, triplestore error, URL encoding, missing param 422, and registry unit tests
- 1358/1358 tests pass in full suite — zero regressions
- `grep -c "right-pane-dynamic"` in workspace.html = 1
- `grep -c "loadRightPane"` in workspace.js = 5
- `grep -c "loadRightPaneSection"` in workspace.js = 0 (old function fully removed)
- Endpoint importable: `from app.browser.apps import apps_router` succeeds
- All modified `.py` files pass `ast.parse()` syntax check

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest backend/tests/test_right_pane_sections.py -v` | 0 | ✅ pass | 0.3s |
| 2 | `pytest backend/tests/ -x` | 0 | ✅ pass | 40s |
| 3 | `grep -c "right-pane-dynamic" workspace.html` | 0 | ✅ pass | <1s |
| 4 | `grep -c "loadRightPane" workspace.js` | 0 | ✅ pass (5) | <1s |
| 5 | `grep -c "loadRightPaneSection" workspace.js` | 1 (grep=0 matches) | ✅ pass | <1s |
| 6 | `python -c "from app.browser.apps import apps_router"` | 0 | ✅ pass | <1s |
| 7 | `ast.parse()` on all modified .py files | 0 | ✅ pass | <1s |

## Diagnostics

- **Endpoint inspection**: `GET /browser/apps/right-pane-sections?iri=http://nonexistent/iri` returns 200 with platform sections only (graceful degradation verified in test)
- **Logging**: `app.browser.apps` logger at DEBUG level shows `Right pane for <iri>: N type(s), M app section(s)` on every request; WARNING on triplestore query failure or app contribution collection failure
- **Request cancellation**: `window._rightPaneAbort` AbortController cancels stale requests on rapid tab switching — AbortError silently caught

## Deviations

- Plan said to remove `loadRightPaneSection()` entirely. Instead added `refreshRightPaneSection()` — a targeted single-section reload helper used by lint-after-validation and relations-after-delete flows. These need to refresh only one section, not reload the entire dynamic container. The old function name is gone; the new function serves the same purpose with a clearer name.
- Template uses `hx-trigger="load once"` for lazy content loading instead of relying on JS to fetch each section's content after the container swap. This is simpler and more htmx-idiomatic.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/registry.py` — added `get_right_pane_contributions(type_iris)` method
- `backend/app/browser/apps.py` — added `right_pane_sections` endpoint, updated module docstring and imports
- `backend/app/templates/browser/right_pane_sections.html` — new template with platform + app contribution sections
- `backend/app/templates/browser/workspace.html` — right pane refactored to `#right-pane-dynamic` container with static fallback
- `frontend/static/js/workspace.js` — replaced `loadRightPaneSection()` with `loadRightPane()` + `refreshRightPaneSection()`, AbortController, updated all call sites
- `backend/tests/test_right_pane_sections.py` — 14 tests covering endpoint and registry method
