---
id: T04
parent: S01
milestone: M033
provides:
  - detectServiceEndpoints() function for SERVICE clause URL extraction
  - Mirror Results button in SPARQL console results info bar
  - handleMirrorClick() with full POST /api/sparql/mirror integration
  - Lazy-loaded mirror endpoint allowlist cache with warning indicator
  - .sparql-mirror-btn CSS with teal accent, warning, success, error, and dark theme states
key_files:
  - frontend/static/js/sparql-console.js
  - frontend/static/css/workspace.css
key_decisions:
  - SERVICE detection strips string literals before regex matching to avoid false positives inside quoted SPARQL strings
  - Allowlist is fetched lazily on first SERVICE query result, not on page load — avoids unnecessary API call for users who never use SERVICE
  - Mirror button shows first detected endpoint only (data-endpoint attribute) — multi-endpoint queries use the first SERVICE URL
patterns_established:
  - Button state machine pattern — sparql-mirror-btn cycles through default → mirror-warning/mirror-success/mirror-error via classList, with title attribute carrying error detail
  - Lucide icon re-rendering after innerHTML mutation — call window.lucide.createIcons() after setting button innerHTML with <i data-lucide="...">
observability_surfaces:
  - console.warn on allowlist fetch failure
  - Button DOM state (classList + title) carries error detail for all failure modes
  - Network request POST /api/sparql/mirror visible in DevTools with structured JSON response
  - Module-level mirrorAllowlistCache inspectable via console
duration: 8min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T04: SPARQL console Mirror button and endpoint picker

**Added Mirror Results button to SPARQL console that detects SERVICE clauses, checks endpoint allowlist, and mirrors federated query results into local triplestore with full success/error feedback**

## What Happened

Added `detectServiceEndpoints(queryText)` function that strips string literals then applies a regex for `SERVICE [SILENT] <url>` patterns, returning deduplicated endpoint URLs. Added `fetchMirrorAllowlist()` with module-level caching and `isEndpointAllowed()` helper.

In the `executeQuery()` result rendering block, after the existing "Save as View" button conditional, added logic that calls `detectServiceEndpoints()` on the executed query text. When SERVICE endpoints are found, a teal-accented "Mirror Results" button with a Lucide `database` icon is appended to the results info bar. The button stores the first endpoint URL in `data-endpoint`.

The allowlist is fetched lazily via `fetchMirrorAllowlist()` — if the detected endpoint is not in the allowlist, the button gets `mirror-warning` class with amber styling and a tooltip explaining the situation.

Implemented `handleMirrorClick()` as the click handler: disables the button and shows "Mirroring…" text, POSTs to `/api/sparql/mirror`, then transitions to success state ("✓ Mirrored N triples" with green check icon), 403 state ("Not allowed" with shield icon and admin guidance in tooltip), or generic error state with the detail message in tooltip.

Added comprehensive CSS in `workspace.css` — `.sparql-mirror-btn` base styles match the teal mirrored-badge color scheme, with `svg` flex-shrink-0 per project convention, hover/disabled/warning/success/error variants, and full dark theme overrides.

## Verification

- `rg "detectServiceEndpoints|sparql-mirror-btn|mirror" frontend/static/js/sparql-console.js` — SERVICE detection, button class, and mirror handlers present ✅
- `rg "sparql-mirror-btn" frontend/static/css/workspace.css` — 13 CSS rules for all button states ✅
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` — 78/78 passed ✅
- `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` — constant exists ✅
- `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` — mirrored graph queried in object detail ✅
- `rg "mirror" frontend/static/js/sparql-console.js` — mirror button code present ✅
- `rg "mirrored-badge|mirrored-edge" frontend/static/css/workspace.css` — provenance styling exists ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` | 0 | ✅ pass | 0.57s |
| 2 | `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` | 0 | ✅ pass | <0.1s |
| 3 | `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` | 0 | ✅ pass | <0.1s |
| 4 | `rg "mirror" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <0.1s |
| 5 | `rg "mirrored-badge\|mirrored-edge" frontend/static/css/workspace.css` | 0 | ✅ pass | <0.1s |
| 6 | `rg "detectServiceEndpoints\|sparql-mirror-btn\|mirror" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <0.1s |
| 7 | `rg "sparql-mirror-btn" frontend/static/css/workspace.css` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Allowlist fetch failure**: `console.warn('Failed to fetch mirror allowlist:', e)` in browser console
- **Button state inspection**: Check `document.querySelector('.sparql-mirror-btn').classList` for current state (mirror-warning, mirror-success, mirror-error). Check `.title` attribute for error detail.
- **Network**: POST `/api/sparql/mirror` visible in DevTools with `{query, endpoint_url}` payload; responses include `mirrored_count` on success, `detail` on error
- **Allowlist cache**: `mirrorAllowlistCache` holds the cached allowlist after first fetch; null before first SERVICE query result

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/sparql-console.js` — added detectServiceEndpoints(), fetchMirrorAllowlist(), isEndpointAllowed(), handleMirrorClick(), mirror button rendering in executeQuery result info bar, mirrorAllowlistCache module state
- `frontend/static/css/workspace.css` — added .sparql-mirror-btn with base/hover/disabled/warning/success/error states, SVG sizing, and dark theme overrides
- `.gsd/milestones/M033/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section per pre-flight requirement
