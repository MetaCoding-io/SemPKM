---
estimated_steps: 7
estimated_files: 8
---

# T02: Extension directory scaffold with manifest, shared modules, and service worker

**Slice:** S01 — Backend auth fix + extension scaffold with working capture
**Milestone:** M014

## Description

Create the complete `extension/` directory structure with Chrome MV3 manifest, shared API client module, storage wrapper, and service worker. This establishes the directory layout and boundary contracts consumed by all subsequent slices (S02-S05). The `api-client.js` (`SemPKMClient` class) is the single point of contact between the extension and the SemPKM backend. The `storage.js` module wraps `chrome.storage.sync` for settings persistence. The service worker registers the context menu item shell.

No UI in this task — that comes in T03 (options) and T04 (popup). This task is pure infrastructure.

## Steps

1. Create `extension/manifest.json` — Chrome MV3 manifest:
   ```json
   {
     "manifest_version": 3,
     "name": "SemPKM Capture",
     "version": "0.1.0",
     "description": "Capture typed, schema-validated objects from any web page to your SemPKM knowledge graph.",
     "permissions": ["storage", "activeTab", "contextMenus"],
     "host_permissions": ["http://localhost:*/*", "https://*/*"],
     "action": {
       "default_popup": "popup/popup.html",
       "default_icon": {
         "16": "assets/icon-16.png",
         "32": "assets/icon-32.png",
         "48": "assets/icon-48.png",
         "128": "assets/icon-128.png"
       }
     },
     "icons": {
       "16": "assets/icon-16.png",
       "32": "assets/icon-32.png",
       "48": "assets/icon-48.png",
       "128": "assets/icon-128.png"
     },
     "background": {
       "service_worker": "background/service-worker.js"
     },
     "options_page": "options/options.html"
   }
   ```

2. Create `extension/shared/api-client.js` — the `SemPKMClient` class:
   - Constructor takes `instanceUrl` and `apiKey`
   - All methods use `fetch()` with `Authorization: Bearer ${apiKey}` header
   - Methods (all return Promises):
     - `connect()` → GET `/.well-known/sempkm` → returns `{version, endpoints, capabilities}` or throws
     - `getTypes()` → GET `/api/types` → returns array of `{iri, label, icon, icon_color, model_id, model_name}`
     - `getShape(typeIri)` → GET `/api/shapes/${encodeURIComponent(typeIri)}` → returns shape object with properties/groups
     - `createObject(params)` → POST `/api/commands` with `{command: "object.create", params}` → returns `{results, event_iri, timestamp}`
     - `createEdge(params)` → POST `/api/commands` with `{command: "edge.create", params}` → returns response
     - `searchObjects(query)` → POST `/api/context-query` with `{title: query, keywords: query}` → returns array of results
   - Error handling: check `response.ok`, parse error JSON, throw descriptive errors
   - Export the class for use by popup, options, and service worker via ES module or global assignment (since MV3 CSP forbids eval, use `globalThis` or import in service worker context)
   
   **Important:** Chrome MV3 popup and options pages can use ES module `<script type="module">` with `import`. Service workers can also use `type: "module"` in the manifest. Use ES module exports consistently.

3. Create `extension/shared/storage.js` — settings persistence wrapper:
   - `getSettings()` → returns Promise resolving to `{instanceUrl, apiKey, defaultType, autoFillTitle, autoFillUrl, includeSelection}` with defaults
   - `saveSettings(settings)` → saves to `chrome.storage.sync`
   - `getClient()` → creates and returns a `SemPKMClient` instance from stored settings; returns `null` if instanceUrl or apiKey not configured
   - Use `chrome.storage.sync` with fallback to `chrome.storage.local`
   - Default values: `instanceUrl: ""`, `apiKey: ""`, `defaultType: ""`, `autoFillTitle: true`, `autoFillUrl: true`, `includeSelection: true`

4. Create `extension/background/service-worker.js`:
   - Import storage module
   - Register context menu on install:
     ```javascript
     chrome.runtime.onInstalled.addListener(() => {
       chrome.contextMenus.create({
         id: 'save-to-sempkm',
         title: 'Save to SemPKM',
         contexts: ['selection']
       });
     });
     ```
   - Add click listener shell (handler implementation in S03):
     ```javascript
     chrome.contextMenus.onClicked.addListener((info, tab) => {
       if (info.menuItemId === 'save-to-sempkm') {
         // S03 will implement: open popup with selected text pre-filled
         console.log('Save to SemPKM clicked:', info.selectionText);
       }
     });
     ```
   - If using ES modules in service worker, set `"type": "module"` in manifest background section

5. Generate extension icon PNGs. Create simple placeholder icons — colored square with "S" letter or SemPKM branding. Use a canvas-based approach or create minimal SVG → PNG:
   - `extension/assets/icon-16.png` (16×16)
   - `extension/assets/icon-32.png` (32×32)
   - `extension/assets/icon-48.png` (48×48)
   - `extension/assets/icon-128.png` (128×128)
   
   Use Python with Pillow, or ImageMagick `convert`, or create from an SVG. The icons should be a solid color square (SemPKM accent color `#4f46e5` indigo) with a white "S" letter. Placeholder quality is fine — these can be polished later.

6. Create minimal stub files for popup and options (so manifest references don't break):
   - `extension/popup/popup.html` — minimal HTML shell with `<!DOCTYPE html>`, charset, viewport, link to popup.css, script to popup.js
   - `extension/popup/popup.js` — empty or `console.log('popup loaded')`
   - `extension/popup/popup.css` — empty
   - `extension/options/options.html` — minimal HTML shell
   - `extension/options/options.js` — empty or `console.log('options loaded')`
   - `extension/options/options.css` — empty

7. Test: Load `extension/` as unpacked extension in Chrome (`chrome://extensions` → Developer mode → Load unpacked). Verify:
   - Extension loads without manifest errors
   - Service worker shows "active" in extension details
   - Right-click on any page → "Save to SemPKM" appears in context menu
   - Clicking extension icon opens a blank popup (stub)
   - Options page opens (stub)

## Must-Haves

- [ ] `extension/manifest.json` is valid Chrome MV3 manifest with correct permissions and file references
- [ ] `SemPKMClient` class has all 6 methods: `connect`, `getTypes`, `getShape`, `createObject`, `createEdge`, `searchObjects`
- [ ] All API calls include `Authorization: Bearer` header
- [ ] `storage.js` wraps `chrome.storage.sync` with `getSettings`, `saveSettings`, `getClient`
- [ ] Service worker registers "Save to SemPKM" context menu item on install
- [ ] All icon sizes exist (16, 32, 48, 128)
- [ ] Extension loads in Chrome without errors

## Verification

- Load `extension/` as unpacked extension in Chrome → no errors in `chrome://extensions`
- Service worker console shows no errors (`chrome://extensions` → extension → "Inspect views: service worker")
- Right-click selected text on any page → "Save to SemPKM" context menu item visible
- Open browser DevTools console in popup/options → modules load without import errors

## Inputs

- M014 research doc — Manifest structure, cross-browser notes, API client requirements
- `backend/app/api/router.py` — Response schemas for types, shapes, context-query, well-known endpoints
- `backend/app/commands/schemas.py` — Command payload structure for object.create, edge.create
- D165 — `require_role_or_api` (from T01) ensures commands endpoint accepts Bearer auth
- D166 — Client-side SHACL rendering via shapes JSON
- D167 — Use context-query for object search (not SPARQL)
- D169 — Vanilla JS, no build step

## Expected Output

- `extension/manifest.json` — Complete Chrome MV3 manifest
- `extension/shared/api-client.js` — SemPKMClient class with 6 API methods
- `extension/shared/storage.js` — Settings persistence wrapper
- `extension/background/service-worker.js` — Context menu registration + click listener shell
- `extension/assets/icon-{16,32,48,128}.png` — Extension icons
- `extension/popup/popup.html`, `popup.js`, `popup.css` — Minimal stubs
- `extension/options/options.html`, `options.js`, `options.css` — Minimal stubs
