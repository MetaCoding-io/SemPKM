---
estimated_steps: 5
estimated_files: 3
---

# T01: Firefox manifest + keyboard shortcut + service-worker cleanup

**Slice:** S05 — Cross-browser, keyboard shortcut, E2E tests + user guide
**Milestone:** M014

## Description

Create the Firefox-compatible manifest, add the Alt+S keyboard shortcut to both manifests, and remove dead ES module imports from service-worker.js so it works as a classic script in both browsers. This is all manifest-level and file-cleanup work — no runtime behavior changes.

The Chrome manifest currently has `"type": "module"` in the `background` section and the service worker has `import { getClient, getSettings } from '../shared/storage.js'` — but those imported functions are **never called** in the service worker body. Firefox MV3 background scripts don't support ES module imports, so removing the dead imports and the `"type": "module"` makes the service worker compatible with both browsers without any functional change.

The `_execute_action` command is a special Chrome/Firefox command that automatically opens the extension popup — no JS handler needed. Both manifests get the same `commands` block.

## Steps

1. **Remove dead imports from service-worker.js.** Delete the `import { getClient, getSettings } from '../shared/storage.js';` line. The file already uses only `chrome.*` APIs directly — the import was never consumed. Verify the file still parses with `node --check`.

2. **Update Chrome manifest.json.** Remove `"type": "module"` from the `background` section (no longer needed without imports). Add `commands` key with `_execute_action`:
   ```json
   "commands": {
     "_execute_action": {
       "suggested_key": {
         "default": "Alt+S",
         "mac": "Alt+S"
       },
       "description": "Open SemPKM Capture"
     }
   }
   ```

3. **Create Firefox manifest.firefox.json.** Copy Chrome manifest structure but with these differences:
   - `background`: use `{ "scripts": ["background/service-worker.js"] }` (array format, NO `service_worker` key, NO `type`)
   - Add `browser_specific_settings`: `{ "gecko": { "id": "sempkm@sempkm.org", "strict_min_version": "109.0" } }`
   - Include the same `commands._execute_action` block
   - Everything else (permissions, host_permissions, action, icons, options_page) stays the same

4. **Validate both manifests.** Parse as JSON with `node -e`. Verify structural correctness: Chrome has `background.service_worker` (string), Firefox has `background.scripts` (array). Neither has `"type": "module"`. Both have `commands._execute_action` with `Alt+S`.

5. **Verify service-worker.js has no imports.** `rg "^import " extension/background/service-worker.js` must return empty.

## Must-Haves

- [ ] `extension/manifest.firefox.json` exists with `background.scripts` array, `browser_specific_settings.gecko.id`, and `commands._execute_action`
- [ ] Chrome `extension/manifest.json` has `commands._execute_action` with `suggested_key.default: "Alt+S"`
- [ ] Chrome manifest background section has no `"type": "module"`
- [ ] `extension/background/service-worker.js` has zero `import` statements
- [ ] Both manifests parse as valid JSON
- [ ] `node --check extension/background/service-worker.js` passes

## Verification

- `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json', 'utf8'))"` exits 0
- `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json', 'utf8'))"` exits 0
- `node --check extension/background/service-worker.js` exits 0
- `rg "^import " extension/background/service-worker.js` returns empty (exit code 1)
- `node -e "const m=JSON.parse(require('fs').readFileSync('extension/manifest.json','utf8')); console.assert(m.commands._execute_action.suggested_key.default==='Alt+S'); console.assert(!m.background.type); console.log('Chrome OK')"` prints "Chrome OK"
- `node -e "const m=JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json','utf8')); console.assert(Array.isArray(m.background.scripts)); console.assert(m.browser_specific_settings.gecko.id==='sempkm@sempkm.org'); console.assert(m.commands._execute_action.suggested_key.default==='Alt+S'); console.log('Firefox OK')"` prints "Firefox OK"

## Observability Impact

This task is manifest-level and file-cleanup only — no runtime behavior changes. The observable signals are:
- **Structural validation:** Both manifests parse as valid JSON and pass structural assertions (background format, commands, gecko settings). A future agent can re-run the verification commands to confirm correctness.
- **Syntax check:** `node --check` on service-worker.js confirms the file is valid JavaScript after import removal.
- **Failure visibility:** If the import removal breaks the service worker, `node --check` will report a parse error with line number. If a manifest is malformed, `JSON.parse` will throw with the character offset.

## Inputs

- `extension/manifest.json` — Current Chrome MV3 manifest with `background.service_worker` and `"type": "module"`
- `extension/background/service-worker.js` — Service worker with dead `import { getClient, getSettings }` line that is never called

## Expected Output

- `extension/manifest.json` — Updated: `commands._execute_action` added, `"type": "module"` removed from background
- `extension/manifest.firefox.json` — New: Firefox-compatible manifest with `background.scripts` array, gecko settings, commands
- `extension/background/service-worker.js` — Updated: dead import line removed
