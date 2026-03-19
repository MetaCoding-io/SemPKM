---
id: T01
parent: S05
milestone: M014
provides:
  - Firefox-compatible manifest (manifest.firefox.json)
  - Alt+S keyboard shortcut in both Chrome and Firefox manifests
  - Classic-script service worker (no ES module imports)
key_files:
  - extension/manifest.json
  - extension/manifest.firefox.json
  - extension/background/service-worker.js
key_decisions:
  - Firefox gecko ID set to sempkm@sempkm.org with strict_min_version 109.0
patterns_established:
  - Dual-manifest approach: manifest.json for Chrome, manifest.firefox.json for Firefox
observability_surfaces:
  - node --check on service-worker.js catches parse errors; JSON.parse on manifests catches structural errors
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Firefox manifest + keyboard shortcut + service-worker cleanup

**Created Firefox manifest, added Alt+S keyboard shortcut to both manifests, removed dead ES module import from service-worker.js**

## What Happened

Three changes, all manifest-level and file-cleanup:

1. Removed the dead `import { getClient, getSettings } from '../shared/storage.js'` line from `service-worker.js`. Neither function was called anywhere in the file — the service worker only uses `chrome.*` APIs directly. This makes the service worker a classic script compatible with Firefox's MV3 background scripts.

2. Updated Chrome `manifest.json`: removed `"type": "module"` from the `background` section (no longer needed without imports) and added the `commands._execute_action` block with `Alt+S` keyboard shortcut. The `_execute_action` command is a special browser command that opens the extension popup — no JS handler needed.

3. Created `manifest.firefox.json` mirroring the Chrome manifest but with Firefox-specific differences: `background.scripts` array format instead of `service_worker` string, `browser_specific_settings.gecko` with addon ID and minimum version, and the same `commands._execute_action` keyboard shortcut.

## Verification

All 6 task-level checks and the slice diagnostic check pass:
- Both manifests parse as valid JSON
- `node --check` passes on service-worker.js
- No `import` statements in service-worker.js (rg exits 1)
- Chrome manifest has `commands._execute_action` with `Alt+S` and no `background.type`
- Firefox manifest has `background.scripts` array, `browser_specific_settings.gecko.id`, and `commands._execute_action` with `Alt+S`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json', 'utf8'))"` | 0 | ✅ pass | <1s |
| 2 | `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json', 'utf8'))"` | 0 | ✅ pass | <1s |
| 3 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 4 | `rg "^import " extension/background/service-worker.js` | 1 | ✅ pass (no matches) | <1s |
| 5 | Chrome assertions (commands, no type) | 0 | ✅ pass | <1s |
| 6 | Firefox assertions (scripts array, gecko id, commands) | 0 | ✅ pass | <1s |

### Slice-level checks (T01 scope)

| # | Check | Status |
|---|-------|--------|
| 1 | Both manifests parse as valid JSON | ✅ pass |
| 2 | `node --check` on service-worker.js | ✅ pass |
| 3 | No imports in service-worker.js | ✅ pass |
| 4 | Chrome manifest has `commands._execute_action` with `Alt+S` | ✅ pass |
| 5 | Chrome manifest background has no `"type": "module"` | ✅ pass |
| 6 | Firefox manifest has `background.scripts`, gecko id, commands | ✅ pass |
| 7 | E2E extension tests pass | ⬜ T02 |
| 8 | User guide chapter exists | ⬜ T03 |
| 9 | README TOC updated | ⬜ T03 |
| 10 | Glossary entries | ⬜ T03 |
| 11 | Diagnostic: `node --check` catches parse errors | ✅ pass |

## Diagnostics

- Run `node --check extension/background/service-worker.js` to verify the service worker parses correctly
- Run `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json','utf8'))"` (and same for `.firefox.json`) to validate manifests
- Both manifests can be diffed to see the Chrome vs Firefox structural differences

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/manifest.json` — Removed `"type": "module"` from background, added `commands._execute_action` with Alt+S shortcut
- `extension/manifest.firefox.json` — New Firefox-compatible manifest with `background.scripts` array, `browser_specific_settings.gecko`, and `commands._execute_action`
- `extension/background/service-worker.js` — Removed dead `import { getClient, getSettings }` line
