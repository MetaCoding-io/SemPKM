---
id: T02
parent: S01
milestone: M055
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - Capture ?tab= before initWorkspaceLayout because replaceState overwrites URL param
  - Route tab IDs through type-detection dispatch supporting all 9 tab ID formats
duration: 
verification_result: passed
completed_at: 2026-04-06T06:25:50.476Z
blocker_discovered: false
---

# T02: Added deep-link handler that opens and focuses the correct tab type from ?tab= query parameter on initial page load

**Added deep-link handler that opens and focuses the correct tab type from ?tab= query parameter on initial page load**

## What Happened

Added a deep-link handler in workspace.js that reads the ?tab= query parameter and opens the corresponding tab after dockview layout initialization. The key challenge was that initWorkspaceLayout() includes a replaceState that overwrites ?tab= with the restored layout's active panel, so the value must be captured before calling initWorkspaceLayout(). The handler supports all tab ID formats: object IRIs, special:*, view:*, generic-view:*, dashboard:*, workflow:*, catalog:*, app-page:*, app-view:*. If the panel is already open from layout restore, it calls setActive() instead of opening a duplicate.

## Verification

Tested 4 scenarios in browser: (1) deep-link to object IRI — Concept tab opens and is active, (2) refresh preserves the tab, (3) deep-link to special:docs — docs tab opens, (4) no ?tab= parameter — normal behavior with no errors. All tests pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `Browser: navigate ?tab=Concept IRI → tab opens and is active` | 0 | ✅ pass | 2000ms |
| 2 | `Browser: reload → same tab active, URL preserved` | 0 | ✅ pass | 3000ms |
| 3 | `Browser: navigate ?tab=special:docs → docs tab opens` | 0 | ✅ pass | 2000ms |
| 4 | `Browser: navigate /browser/ without ?tab= → no errors` | 0 | ✅ pass | 2000ms |
| 5 | `Browser: URL assert contains correct tab ID` | 0 | ✅ pass | 100ms |

## Deviations

Had to capture ?tab= BEFORE initWorkspaceLayout() instead of after, because replaceState inside init overwrites the URL parameter. Required frontend asset rebuild and Docker volume deployment.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js`
