---
id: T01
parent: S01
milestone: M015
provides:
  - contextQuery() API method on SemPKMClient
  - autoCheckContext/contextCheckDelay/contextTimeout settings keys
  - Chrome sidePanel + tabs permissions and side_panel manifest key
  - Firefox tabs permission and sidebar_action manifest key
  - Alt+K keyboard command in both manifests
key_files:
  - extension/shared/api-client.js
  - extension/shared/storage.js
  - extension/manifest.json
  - extension/manifest.firefox.json
key_decisions: []
patterns_established:
  - contextQuery() returns full response {results, total} — callers decide what to use
  - searchObjects() left unchanged for backward compat (reference picker uses it)
observability_surfaces:
  - Chrome extensions page shows sidePanel + tabs permissions
  - Firefox about:debugging shows sidebar_action registration
  - contextQuery() throws SemPKMError with status/detail on API failures
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Extend API client, storage keys, and manifests for context overlay

**Added contextQuery() method, context overlay settings keys, and sidePanel/sidebar_action manifest entries for Chrome and Firefox**

## What Happened

Four files modified per plan. `contextQuery({url, title, keywords})` added to `SemPKMClient` — sends only non-empty fields to `POST /api/context-query` and returns the full `{results, total}` response. Existing `searchObjects()` left untouched for reference picker backward compat. Three new settings keys added to `DEFAULTS` in storage.js (`autoCheckContext`, `contextCheckDelay`, `contextTimeout`) — `SETTINGS_KEYS` auto-includes them via `Object.keys(DEFAULTS)`. Chrome manifest gained `sidePanel` + `tabs` permissions, `side_panel.default_path` pointing to `sidebar/sidebar.html`, and the `open-context-sidebar` Alt+K command. Firefox manifest gained `tabs` permission, `sidebar_action` with `open_at_install: false`, and the same Alt+K command.

## Verification

All four task-level verification checks pass: both JS files pass `node --check`, both manifests are valid JSON with the required keys, permissions, and commands.

Slice-level checks for files not yet created (context-utils.js, sidebar.js, test-context-utils.js) are expected to fail — those are T02–T04 deliverables.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/shared/storage.js` | 0 | ✅ pass | <1s |
| 3 | Chrome manifest JSON parse + assertions (sidePanel, tabs, side_panel, open-context-sidebar) | 0 | ✅ pass | <1s |
| 4 | Firefox manifest JSON parse + assertions (tabs, sidebar_action, open-context-sidebar) | 0 | ✅ pass | <1s |

## Diagnostics

- `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json','utf8')).permissions"` — shows Chrome permissions including sidePanel/tabs
- `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json','utf8')).sidebar_action"` — shows Firefox sidebar config
- API client method inspection: import and check `SemPKMClient.prototype.contextQuery` exists

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/shared/api-client.js` — added `contextQuery({url, title, keywords})` method
- `extension/shared/storage.js` — added `autoCheckContext`, `contextCheckDelay`, `contextTimeout` to DEFAULTS
- `extension/manifest.json` — added sidePanel/tabs permissions, side_panel key, open-context-sidebar command
- `extension/manifest.firefox.json` — added tabs permission, sidebar_action key, open-context-sidebar command
- `.gsd/milestones/M015/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
