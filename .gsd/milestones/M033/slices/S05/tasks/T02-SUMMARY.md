---
id: T02
parent: S05
milestone: M033
provides:
  - SERVICE endpoint URL autocomplete inside SERVICE <...> patterns in SPARQL console
  - Debounced info banner below editor showing per-endpoint allowlist status (✓/⚠)
  - Allowlist cache warm-up at console init (was previously only fetched post-execution)
  - Updated isEndpointAllowed() to handle object format {url, source, removable} from T01
key_files:
  - frontend/static/js/sparql-console.js
  - frontend/static/css/workspace.css
key_decisions:
  - Updated isEndpointAllowed() with _allowlistEntryUrl() helper to handle both old string format and new T01 object format {url, source, removable}
  - Skipped admin link in info banner since no user-role data attribute exists on body element — no client-side mechanism to detect owner role
patterns_established:
  - _allowlistEntryUrl(entry) normalizes allowlist cache entries to URL strings regardless of format (string or object)
  - _updateServiceInfoBanner() uses detectServiceEndpoints() + isEndpointAllowed() for per-endpoint status, triggered by EditorView.updateListener with 500ms debounce
observability_surfaces:
  - SERVICE info banner is a live diagnostic surface showing detected endpoints and their allowlist status
  - Autocomplete dropdown shows allowlisted endpoints with type 'url' and detail '⛓' chain emoji
  - fetchMirrorAllowlist() now called at init — check network logs for GET /api/sparql/mirror/endpoints on console open
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: SERVICE endpoint autocomplete and info banner

**Added SERVICE URI autocomplete with allowlisted endpoint suggestions and debounced info banner showing per-endpoint allowlist status in the SPARQL console**

## What Happened

Extended the SPARQL console with two pre-execution assistance features:

1. **Allowlist cache warm-up:** Added `fetchMirrorAllowlist()` call in `initSparqlConsole()` after `fetchVocabulary()`. Previously the allowlist was only fetched post-execution when the mirror button appeared.

2. **SERVICE URI autocomplete:** Added a new detection branch at the top of `sparqlCompletions()` that checks if the cursor is inside a `SERVICE <...>` or `SERVICE SILENT <...>` pattern. When matched, it filters the `mirrorAllowlistCache` entries whose URL starts with the partial text typed so far and returns completions with type `'url'` and detail `'⛓'`. The branch returns early — it doesn't mix endpoint URLs with keyword suggestions.

3. **Debounced info banner:** Added an `EditorView.updateListener` extension in `createEditor()` that fires on content changes with a 500ms debounce. The listener calls `_updateServiceInfoBanner()` which runs `detectServiceEndpoints()` on the current document text and renders a `div.sparql-service-info` bar showing each endpoint with ✓ (allowed) or ⚠ (blocked) status. The banner is created dynamically in `initSparqlConsole()` and appended to `.sparql-editor-wrap`.

4. **isEndpointAllowed fix:** The T01 changes made the GET endpoint return objects `{url, source, removable}` instead of plain strings. Updated `isEndpointAllowed()` to use a new `_allowlistEntryUrl()` helper that normalizes both formats to URL strings. This also fixes the autocomplete and mirror button to work with the new cache format.

5. **CSS:** Added `.sparql-service-info` styles with light/dark theme support, flex-wrap layout, and `.endpoint-allowed` / `.endpoint-blocked` status classes using the same color palette as the mirror button states.

## Verification

- **Unit tests:** Both `test_federation_config.py` (18 tests) and `test_federation_endpoints_api.py` (6 tests) pass.
- **Browser verification:** 
  - Added two endpoints via admin federation page (dbpedia.org/sparql, query.wikidata.org/sparql)
  - Opened SPARQL console → typed `SERVICE <` → autocomplete dropdown shows both endpoints with ⛓ indicator
  - Typed `SERVICE <https://d` → dropdown filters to just dbpedia endpoint
  - Typed `SERVICE SILENT <` → both endpoints appear (SILENT variant works)
  - Typed full query with `SERVICE <https://dbpedia.org/sparql>` → info banner appears with ✓
  - Typed query with `SERVICE <https://unknown.org/sparql>` → info banner shows ⚠
  - Query with both endpoints → banner shows ✓ for dbpedia and ⚠ for unknown
  - Removed SERVICE clause → banner disappears (display: none)
  - Dark theme renders correctly — banner and editor use appropriate dark colors
  - No JS console errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py -v` | 0 | ✅ pass | 0.6s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_federation_endpoints_api.py -v` | 0 | ✅ pass | 0.6s |
| 3 | Browser: SERVICE `<` autocomplete shows allowlisted endpoints | — | ✅ pass | — |
| 4 | Browser: info banner shows ✓ for allowed, ⚠ for blocked | — | ✅ pass | — |
| 5 | Browser: banner hides when no SERVICE endpoints in query | — | ✅ pass | — |
| 6 | Browser: dark/light themes render correctly | — | ✅ pass | — |

## Diagnostics

- **Info banner:** The `#sparql-service-info` element shows detected SERVICE endpoints and their allowlist status. Check `display` style — `none` when no endpoints, `flex` when endpoints detected.
- **Autocomplete:** SERVICE URI completions use type `url` and detail `⛓` (chain emoji) — distinguishable in the CodeMirror dropdown from keywords (K), classes (C), and variables (V).
- **Cache state:** The `mirrorAllowlistCache` variable holds the fetched allowlist. If the fetch failed, it's an empty array and all endpoints show ⚠.
- **Network:** `GET /api/sparql/mirror/endpoints` is now fetched at console init, visible in the network tab.

## Deviations

- Skipped the admin link in the info banner. The plan suggested showing a link to `/admin/federation` for owner-role users, but there's no `data-user-role` or similar attribute on the body element — no client-side mechanism exists to detect the user's role. This is a minor nice-to-have that would require a template change outside scope.

## Known Issues

- When the SPARQL panel is docked at the bottom with minimal height, the info banner may be below the viewport fold. It becomes visible when the panel is expanded. This is inherent to the panel's flex layout — the banner has `flex-shrink: 0` so it takes priority after the editor content.

## Files Created/Modified

- `frontend/static/js/sparql-console.js` — Added SERVICE URI autocomplete branch, debounced info banner, allowlist cache warm-up at init, updated isEndpointAllowed() for object format
- `frontend/static/css/workspace.css` — Added `.sparql-service-info` banner styles with light/dark theme support
- `.gsd/milestones/M033/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section
