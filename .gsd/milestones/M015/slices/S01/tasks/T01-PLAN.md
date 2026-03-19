---
estimated_steps: 6
estimated_files: 4
---

# T01: Extend API client, storage keys, and manifests for context overlay

**Slice:** S01 — Context queries, badge count, and sidebar with grouped results
**Milestone:** M015

## Description

Foundation task: adds the `contextQuery()` API method, new settings keys for context overlay behavior, and manifest entries for Chrome Side Panel / Firefox sidebar_action. Everything in T02–T04 depends on these additions.

The key API change is adding `contextQuery({url, title, keywords})` to `SemPKMClient`. The existing `searchObjects(query)` method sends the same string as both `title` and `keywords` — per D196, the new method sends each field separately to `POST /api/context-query`. Keep `searchObjects()` for backward compatibility (the popup reference picker uses it).

## Steps

1. **Add `contextQuery()` to `extension/shared/api-client.js`:**
   - New method signature: `async contextQuery({url, title, keywords})`
   - Sends `POST /api/context-query` with `{url, title, keywords}` — only non-empty fields included
   - Returns `{results: Array, total: number}` (the full response, not just results — let callers decide what to use)
   - Backend endpoint schema (`ContextQueryRequest`): `url: str | None`, `title: str | None`, `keywords: str | None` — at least one required
   - Backend response schema (`ContextQueryResponse`): `{results: [{iri, label, type_iri, type_label, match_type, snippet}], total: int}`
   - Do NOT modify `searchObjects()` — it's used by the reference picker (M014/S04)

2. **Add context overlay settings to `extension/shared/storage.js`:**
   - Add to `DEFAULTS` object:
     - `autoCheckContext: true` (bool — whether to auto-query on page navigation)
     - `contextCheckDelay: 2000` (number ms — debounce delay after page load)
     - `contextTimeout: 5000` (number ms — fetch timeout for context query)
   - `SETTINGS_KEYS` is derived from `Object.keys(DEFAULTS)` so it auto-includes new keys

3. **Update `extension/manifest.json` (Chrome):**
   - Add `"sidePanel"` to `permissions` array
   - Add `"tabs"` to `permissions` array (needed for `chrome.tabs.onUpdated` listener)
   - Add top-level `"side_panel"` key: `{"default_path": "sidebar/sidebar.html"}`
   - Add named command for Alt+K in `commands` object:
     ```json
     "open-context-sidebar": {
       "suggested_key": { "default": "Alt+K", "mac": "Alt+K" },
       "description": "Open SemPKM Context Sidebar"
     }
     ```
   - Keep `_execute_action` (Alt+S) unchanged — popup and sidebar coexist (D195)

4. **Update `extension/manifest.firefox.json` (Firefox):**
   - Add `"tabs"` to `permissions` array
   - Add top-level `"sidebar_action"` key:
     ```json
     "sidebar_action": {
       "default_panel": "sidebar/sidebar.html",
       "default_title": "SemPKM Context",
       "default_icon": {
         "16": "assets/icon-16.png",
         "32": "assets/icon-32.png"
       },
       "open_at_install": false
     }
     ```
   - Add the same `"open-context-sidebar"` command entry as Chrome manifest
   - Note: Firefox does NOT have `sidePanel` permission — `sidebar_action` is a manifest key, not a permission

5. **Verify both manifests are valid JSON:**
   - `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json'))"` — no errors
   - Same for `manifest.firefox.json`

6. **Verify all modified JS files pass syntax check:**
   - `node --check extension/shared/api-client.js`
   - `node --check extension/shared/storage.js`

## Must-Haves

- [ ] `contextQuery({url, title, keywords})` exists on SemPKMClient and sends separate fields
- [ ] `searchObjects()` is unchanged (backward compat for reference picker)
- [ ] `DEFAULTS` in storage.js includes `autoCheckContext`, `contextCheckDelay`, `contextTimeout`
- [ ] Chrome manifest has `sidePanel` + `tabs` permissions, `side_panel.default_path`, and Alt+K command
- [ ] Firefox manifest has `tabs` permission, `sidebar_action` with `open_at_install: false`, and Alt+K command
- [ ] Both manifests remain valid JSON

## Verification

- `node --check extension/shared/api-client.js` exits 0
- `node --check extension/shared/storage.js` exits 0
- `node -e "const m = JSON.parse(require('fs').readFileSync('extension/manifest.json','utf8')); console.assert(m.permissions.includes('sidePanel')); console.assert(m.permissions.includes('tabs')); console.assert(m.side_panel); console.assert(m.commands['open-context-sidebar']); console.log('Chrome manifest OK')"` — no errors
- `node -e "const m = JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json','utf8')); console.assert(m.permissions.includes('tabs')); console.assert(m.sidebar_action); console.assert(m.commands['open-context-sidebar']); console.log('Firefox manifest OK')"` — no errors

## Inputs

- `extension/shared/api-client.js` — existing `SemPKMClient` class with `searchObjects()`, `createObject()`, `createEdge()`, `getTypes()`, `getShape()`, `connect()`, and `_request()` helper
- `extension/shared/storage.js` — existing `DEFAULTS` object with 6 keys, `getSettings()`, `saveSettings()`, `getClient()` functions
- `extension/manifest.json` — Chrome MV3 manifest with `permissions: ["storage", "activeTab", "contextMenus", "scripting"]`, `commands._execute_action` (Alt+S), `action.default_popup`, `background.service_worker`
- `extension/manifest.firefox.json` — Firefox manifest with same permissions, `background.scripts` array, `browser_specific_settings.gecko`
- D194 (Side Panel API), D195 (popup/sidebar coexistence), D196 (separate query fields)

## Expected Output

- `extension/shared/api-client.js` — gains `contextQuery({url, title, keywords})` method
- `extension/shared/storage.js` — `DEFAULTS` gains 3 new keys
- `extension/manifest.json` — has `sidePanel`/`tabs` permissions, `side_panel` key, `open-context-sidebar` command
- `extension/manifest.firefox.json` — has `tabs` permission, `sidebar_action` key, `open-context-sidebar` command
