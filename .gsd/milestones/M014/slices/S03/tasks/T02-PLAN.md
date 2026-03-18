---
estimated_steps: 8
estimated_files: 3
---

# T02: Popup integration, manifest update, and context menu wiring

**Slice:** S03 — Content scripts + context menu + schema.org
**Milestone:** M014

## Description

Wire the content script extractor and schema.org mapper (from T01) into the popup lifecycle, implement the service worker context menu handler, and update the manifest. This is the integration task that connects all S03 pieces and completes EXT-03 (auto-population), EXT-05 (context menu), and EXT-06 (schema.org integration).

The key timing challenge: the content script extraction returns page data before the type selector + shape fetch completes. The extracted schema.org data must be stored and re-applied whenever `handleTypeChange()` finishes rendering a new form. A module-level `pendingPageData` variable holds the extracted data for this purpose.

## Steps

1. **Update `extension/manifest.json`:**
   - Add `"scripting"` to the `permissions` array (needed for `chrome.scripting.executeScript`)
   - Final permissions list: `["storage", "activeTab", "contextMenus", "scripting"]`

2. **Update `extension/popup/popup.js` — content script injection:**
   - Import `suggestType`, `mapSchemaOrgToFormValues` from `'../shared/schema-mapper.js'`
   - Import `extractPageData` from `'../content/extractor.js'` (only to reference the function — it's passed to `chrome.scripting.executeScript({func})`)
   - Add module-level variable: `let pendingPageData = null`
   - Replace the existing `chrome.tabs.query` URL/title extraction block in `init()` with:
     ```
     a. Check chrome.storage.session for contextMenuData (context menu pre-fill path)
        - If found: clear it, set pendingPageData with the stored data, pre-fill notes/URL
     b. If no context menu data: inject extractor via chrome.scripting.executeScript
        - Get active tab via chrome.tabs.query
        - Call chrome.scripting.executeScript({target: {tabId}, func: extractPageData})
        - Store result in pendingPageData
        - Log: [SemPKM] Extracted page data: {title, url, selectedText:len, schemaOrg:count}
     c. Handle injection failure gracefully (restricted pages)
        - Catch errors, fall back to tab.title / tab.url from chrome.tabs.query
        - Log: [SemPKM] Content script injection failed: {error} — falling back to tab data
     ```
   - After extraction (regardless of source), apply basic fields:
     - If `settings.autoFillTitle` and `pendingPageData.title`: fill `$fallbackTitle`
     - If `settings.autoFillUrl` and `pendingPageData.url`: fill `$urlInput`
     - If `settings.includeSelection` and `pendingPageData.selectedText`: fill `$notesInput`

3. **Update `extension/popup/popup.js` — schema.org type suggestion:**
   - After extraction and type selector population, call `suggestType(pendingPageData.schemaOrg, loadedTypes)`
   - If a type is suggested and it exists in the selector:
     - Auto-select it in `$typeSelect`
     - Log: `[SemPKM] Schema.org type suggestion: {schemaType} → {sempkmType}`
     - Trigger `handleTypeChange()` to load the shape and render the form

4. **Update `extension/popup/popup.js` — schema.org form filling:**
   - Create `applySchemaOrgToForm()` function:
     - Reads `pendingPageData.schemaOrg` and the currently rendered form
     - If no schema.org data or no current shape, return early
     - Find the matching schema.org entity for the current type (check `suggestType` result or iterate entities)
     - Call `mapSchemaOrgToFormValues(entity, currentShape.properties)` to get `{path: value}` pairs
     - Iterate results, find `[data-path="<path>"]` inputs in `$dynamicForm`, set `.value`
     - Also apply basic page data to any matching form fields (e.g., page title → dcterms:title path, page URL → schema:url path)
     - Log: `[SemPKM] Applied N schema.org values to form`
   - Call `applySchemaOrgToForm()` at the end of `handleTypeChange()` (after form rendering completes)
   - This ensures schema.org values re-apply when the user changes types

5. **Update `extension/background/service-worker.js` — context menu handler:**
   - Replace the shell handler with the real implementation:
     ```js
     chrome.contextMenus.onClicked.addListener(async (info, tab) => {
       if (info.menuItemId === 'save-to-sempkm') {
         await chrome.storage.session.set({
           contextMenuData: {
             selectionText: info.selectionText || '',
             pageUrl: info.pageUrl || '',
             pageTitle: tab?.title || '',
           }
         });
         console.log('[SemPKM] Context menu: stored selection data');
         try {
           await chrome.action.openPopup();
         } catch (err) {
           console.warn('[SemPKM] Could not open popup:', err.message);
           // Fallback: open popup.html as a new window
           chrome.windows.create({
             url: chrome.runtime.getURL('popup/popup.html'),
             type: 'popup',
             width: 420,
             height: 520,
           });
         }
       }
     });
     ```

6. **Handle the `extractPageData` import for `executeScript`:**
   - `chrome.scripting.executeScript({func})` requires a function reference. Since `extractPageData` is self-contained, it can be imported from `extractor.js` as an ES module export and passed directly. The Chrome API serializes just the function body.
   - Alternative: if the import causes issues (since extractor.js is in `/content/` not `/shared/`), define the function inline or use `chrome.scripting.executeScript({files: ['content/extractor.js']})` instead. The `files` approach injects the script file directly into the page — the function must then communicate its result back via the `executeScript` return value mechanism. The `func` approach is cleaner.
   - The extractor function must return its result — `executeScript` captures the return value in `results[0].result`.

7. **Settings respect:**
   - Read `settings.autoFillTitle`, `settings.autoFillUrl`, `settings.includeSelection` from `getSettings()`
   - Only fill the corresponding fields when the setting is enabled
   - These settings are already declared in `storage.js` DEFAULTS

8. **Verify:**
   - `node --check extension/popup/popup.js extension/background/service-worker.js extension/manifest.json`
   - Grep: `"scripting"` in manifest permissions
   - Grep: `chrome.scripting.executeScript` in popup.js
   - Grep: `chrome.storage.session` in service-worker.js and popup.js
   - Grep: `chrome.action.openPopup` in service-worker.js
   - Grep: `applySchemaOrgToForm` in popup.js
   - Grep: `pendingPageData` in popup.js
   - Zero inline handlers: grep for `onclick=|onchange=` in all modified files → empty

## Must-Haves

- [ ] Manifest has `"scripting"` in permissions
- [ ] Popup injects content script via `chrome.scripting.executeScript` and receives page data
- [ ] Popup checks `chrome.storage.session` for context menu pre-fill data on init
- [ ] Context menu handler stores selection data in `chrome.storage.session` and opens popup
- [ ] `applySchemaOrgToForm()` fills `[data-path]` inputs from schema.org mapped values
- [ ] `applySchemaOrgToForm()` called at end of `handleTypeChange()` for re-application on type change
- [ ] Schema.org type suggestion auto-selects type in dropdown
- [ ] Auto-fill respects `autoFillTitle`, `autoFillUrl`, `includeSelection` settings
- [ ] Graceful fallback when content script injection fails (restricted pages)
- [ ] All modified files pass `node --check`

## Verification

- `node --check extension/popup/popup.js` — exits 0
- `node --check extension/background/service-worker.js` — exits 0
- `grep -c '"scripting"' extension/manifest.json` — returns 1
- `grep -c 'chrome.scripting.executeScript' extension/popup/popup.js` — returns ≥1
- `grep -c 'chrome.storage.session' extension/background/service-worker.js` — returns ≥1
- `grep -c 'chrome.storage.session' extension/popup/popup.js` — returns ≥1
- `grep -c 'chrome.action.openPopup' extension/background/service-worker.js` — returns ≥1
- `grep -c 'applySchemaOrgToForm' extension/popup/popup.js` — returns ≥2 (definition + call)
- `grep -rn 'onclick=\|onchange=' extension/popup/popup.js extension/background/service-worker.js` — empty
- Full grep check: no `import` or `require` in extractor.js (self-contained, verified in T01 but worth re-checking after integration)

## Inputs

- `extension/content/extractor.js` (T01) — `extractPageData` function for injection via `chrome.scripting.executeScript`
- `extension/shared/schema-mapper.js` (T01) — `suggestType()` and `mapSchemaOrgToFormValues()` for type suggestion and form filling
- `extension/popup/popup.js` — current popup with `populateFromPageData()`, `handleTypeChange()`, `$dynamicForm`, `$typeSelect`, fallback fields, `loadedTypes`, `currentShape`
- `extension/background/service-worker.js` — current shell context menu handler to be replaced
- `extension/shared/storage.js` — `getSettings()` returns `{autoFillTitle, autoFillUrl, includeSelection}` booleans
- `extension/shared/shacl-renderer.js` — form inputs have `data-path` attributes with full IRI paths; `getFormValues()` reads them back

## Expected Output

- `extension/manifest.json` — `"scripting"` added to permissions array
- `extension/popup/popup.js` — rewritten `init()` with content script injection, schema.org type suggestion, `applySchemaOrgToForm()` function called from `handleTypeChange()`, context menu pre-fill check
- `extension/background/service-worker.js` — context menu handler stores data in `chrome.storage.session` and opens popup via `chrome.action.openPopup()` with fallback

## Observability Impact

**New console signals (all prefixed `[SemPKM]`):**
- `Extracted page data: {title, url, selectedText:len, schemaOrg:count}` — popup, on content script injection result
- `Content script injection failed: {error} — falling back to tab data` — popup, when injection is blocked (restricted pages)
- `Schema.org type suggestion: {schemaType} → {sempkmType}` — popup, when auto-selecting a type from JSON-LD
- `Applied N schema.org values to form` — popup, after filling data-path inputs from mapped entity
- `Context menu: stored selection data` — service worker, on context menu click before opening popup

**Inspectable state:**
- `chrome.storage.session.get('contextMenuData')` in service worker DevTools — shows pending pre-fill data (or absent if popup consumed it)
- `pendingPageData` module variable in popup scope — holds raw extraction result for the session

**Failure visibility:**
- Injection failure degrades to tab title/URL only — logged but not surfaced to user
- Schema.org suggestion miss (no matching type) produces no log — silent, form stays on default/blank
- `chrome.action.openPopup()` failure in service worker falls back to `chrome.windows.create()` — logged as warning
