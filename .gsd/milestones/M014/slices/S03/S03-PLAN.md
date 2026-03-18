# S03: Content scripts + context menu + schema.org

**Goal:** Wire the extension popup to the actual web page — extracting metadata, pre-filling SHACL forms from page data and schema.org JSON-LD, and enabling context menu capture.
**Demo:** Opening the popup on any page auto-fills title and URL from page metadata. Selecting text before opening the popup pre-fills the body field. Right-click selected text → "Save to SemPKM" opens the popup with the text pre-filled. Visiting a page with schema.org JSON-LD (e.g., Person, Article) auto-fills matching fields when the corresponding type is selected.

## Must-Haves

- Content script (`extension/content/extractor.js`) extracts page title (og:title > twitter:title > document.title), URL, selected text, author, description, and all schema.org JSON-LD entities
- Schema.org mapper (`extension/shared/schema-mapper.js`) maps JSON-LD types to SemPKM type IRIs and schema.org properties to SHACL form field paths (both direct namespace and cross-namespace)
- Popup injects content script via `chrome.scripting.executeScript` on open (no persistent content script)
- Popup auto-fills both fallback fields (title/URL/notes) AND dynamic SHACL form `[data-path]` inputs from extracted data
- Schema.org type suggestion auto-selects the matching type in the type dropdown
- Schema.org property values re-apply when user changes type (stored in module-level variable)
- Context menu "Save to SemPKM" stores selection data in `chrome.storage.session` and opens popup via `chrome.action.openPopup()`
- Popup checks `chrome.storage.session` on init for context menu pre-fill data
- Manifest gains `"scripting"` permission
- Auto-fill respects settings (`autoFillTitle`, `autoFillUrl`, `includeSelection`)
- Graceful fallback when content script injection fails (restricted pages — `chrome://`, Web Store)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Chrome sideloaded extension on real web pages)
- Human/UAT required: no (Node.js tests for pure functions; Chrome DevTools console for integration)

## Verification

- `node --check extension/content/extractor.js extension/shared/schema-mapper.js` — syntax valid
- `node -e` test script exercises extractor function with mock DOM (jsdom or inline assertions on return shape)
- `node -e` test script exercises schema-mapper with sample JSON-LD data, verifying type suggestion and property mapping
- `node --check extension/popup/popup.js extension/background/service-worker.js` — syntax valid after modifications
- Grep checks: `"scripting"` in manifest permissions, `chrome.scripting.executeScript` in popup.js, `chrome.storage.session` in service-worker.js and popup.js, `chrome.action.openPopup` in service-worker.js
- No inline event handlers in any modified file (grep for `onclick=` / `onchange=` returns empty)

## Observability / Diagnostics

- Runtime signals: `[SemPKM] Extracted page data: {title, url, selectedText:len, schemaOrg:count}` in popup console; `[SemPKM] Schema.org type suggestion: {schemaType} → {sempkmType}` when a type is auto-selected; `[SemPKM] Applied N schema.org values to form` after form fill; `[SemPKM] Context menu: stored selection data` in service worker console
- Inspection surfaces: Chrome DevTools console filtered for `[SemPKM]`; `chrome.storage.session.get('contextMenuData')` in service worker DevTools
- Failure visibility: Content script injection failure logged as `[SemPKM] Content script injection failed: {error}` with fallback to tab title/URL; invalid JSON-LD logged as `[SemPKM] Skipping invalid JSON-LD: {error}`
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `extension/shared/api-client.js` (SemPKMClient), `extension/shared/storage.js` (getSettings), `extension/shared/shacl-renderer.js` (renderForm, getFormValues — `data-path` attribute contract), `extension/popup/popup.js` (populateFromPageData, handleTypeChange, type selector), `extension/background/service-worker.js` (context menu shell handler)
- New wiring introduced in this slice: content script injection from popup via `chrome.scripting.executeScript`, `chrome.storage.session` bridge between service worker and popup for context menu data, schema-mapper module imported by popup.js
- What remains before the milestone is truly usable end-to-end: S04 (relationship picker), S05 (cross-browser, E2E tests, keyboard shortcut, user guide)

## Tasks

- [ ] **T01: Content script extractor and schema.org mapper modules** `est:45m`
  - Why: Creates the two pure-function modules that all popup integration depends on — the content script that runs in the page DOM context and the schema.org-to-SHACL mapping logic. Both are testable without Chrome APIs.
  - Files: `extension/content/extractor.js`, `extension/shared/schema-mapper.js`
  - Do: Build extractor as a self-contained function (no imports/closures — `chrome.scripting.executeScript` serializes it). Parse `<script type="application/ld+json">`, meta tags, `og:title`, `window.getSelection()`. Build mapper with type suggestion table (Person→Contact, Organization→Company, Article→Note, ScholarlyArticle→Paper) and property mapping table (direct namespace matches + cross-namespace like `schema:givenName→crm:firstName`). Normalize `@type` variants. Handle `@graph` arrays, nested objects, missing `@context`, invalid JSON.
  - Verify: `node --check` on both files; `node -e` test scripts exercising extractor return shape and mapper with sample JSON-LD
  - Done when: Both modules export well-documented functions, handle edge cases defensively, and pass syntax + functional tests

- [ ] **T02: Popup integration, manifest update, and context menu wiring** `est:45m`
  - Why: Wires extractor and mapper into the popup lifecycle, fills in the service worker context menu handler, and updates the manifest — completing all three requirements (EXT-03, EXT-05, EXT-06).
  - Files: `extension/manifest.json`, `extension/popup/popup.js`, `extension/background/service-worker.js`
  - Do: Add `"scripting"` to manifest permissions. In popup.js: replace bare `chrome.tabs.query` with `chrome.scripting.executeScript` injecting the extractor function, store extracted data in module-level `pendingPageData`, use mapper for type suggestion (auto-select in dropdown), enhance `handleTypeChange()` to call `applySchemaOrgToForm()` after rendering, fill both fallback fields and `[data-path]` dynamic form inputs, check `chrome.storage.session` on init for context menu pre-fill. In service-worker.js: store `{selectionText, pageUrl, pageTitle}` in `chrome.storage.session`, call `chrome.action.openPopup()`. Handle restricted-page fallback gracefully.
  - Verify: `node --check` on all modified files; grep for `"scripting"` in manifest, `chrome.scripting.executeScript` in popup.js, `chrome.storage.session` in both files, `chrome.action.openPopup` in service-worker.js; zero inline handlers
  - Done when: Popup injects content script and fills form fields from page data, context menu opens popup with selected text pre-filled, schema.org auto-selects type and fills matching fields, settings toggles respected

## Files Likely Touched

- `extension/content/extractor.js` (new)
- `extension/shared/schema-mapper.js` (new)
- `extension/manifest.json` (add scripting permission)
- `extension/popup/popup.js` (content script injection, schema.org integration, context menu pre-fill)
- `extension/background/service-worker.js` (context menu handler implementation)
