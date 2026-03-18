---
id: T02
parent: S03
milestone: M014
provides:
  - Popup content script injection via chrome.scripting.executeScript with page data extraction
  - Schema.org type suggestion and form auto-fill via applySchemaOrgToForm()
  - Context menu handler storing selection data in chrome.storage.session and opening popup
  - Manifest scripting permission
key_files:
  - extension/manifest.json
  - extension/popup/popup.js
  - extension/background/service-worker.js
  - extension/content/extractor.js
key_decisions:
  - Used chrome.scripting.executeScript({func}) with imported extractPageData reference rather than {files:} approach — cleaner, single return value, no message-passing needed
  - Schema.org data stored in module-level pendingPageData and re-applied on every type change via applySchemaOrgToForm() at end of handleTypeChange()
  - Context menu data flows through chrome.storage.session as bridge between service worker and popup contexts
patterns_established:
  - Content script → session storage → popup init pattern for context menu pre-fill
  - applySchemaOrgToForm() called from handleTypeChange() ensures schema.org values survive type switches
observability_surfaces:
  - "[SemPKM] Extracted page data:" in popup console with title/url/selectedText length/schemaOrg count
  - "[SemPKM] Schema.org type suggestion:" when auto-selecting a type from JSON-LD
  - "[SemPKM] Applied N schema.org values to form" after filling data-path inputs
  - "[SemPKM] Content script injection failed:" with error and fallback note
  - "[SemPKM] Context menu: stored selection data" in service worker console
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Popup integration, manifest update, and context menu wiring

**Wired content script extractor and schema.org mapper into popup lifecycle, implemented context menu handler with session storage bridge, and added scripting permission to manifest**

## What Happened

Integrated the T01 modules (extractor.js, schema-mapper.js) into the popup's init flow and added the real context menu handler to the service worker.

**Manifest:** Added `"scripting"` to permissions array (required for `chrome.scripting.executeScript`).

**Popup init() rewrite:** Replaced the simple `chrome.tabs.query` URL/title extraction with a three-path data acquisition flow:
1. Check `chrome.storage.session` for context menu pre-fill data (consumed and cleared on read)
2. If no context menu data, inject `extractPageData` into the active tab via `chrome.scripting.executeScript({func})`
3. On injection failure (restricted pages), fall back to `tab.title` / `tab.url`

After extraction, basic fields (title, URL, notes) are filled respecting the `autoFillTitle`, `autoFillUrl`, `includeSelection` settings. Schema.org type suggestion runs after type selector population — if `suggestType()` finds a match in the available types, it auto-selects the type and triggers `handleTypeChange()`.

**applySchemaOrgToForm():** New function called at the end of `handleTypeChange()`. Maps the pending schema.org entity to `[data-path]` form inputs via `mapSchemaOrgToFormValues()`. Also injects page title into `dcterms:title` and page URL into `schema:url` paths if the shape has those properties and they weren't already mapped. Only fills empty inputs (doesn't overwrite user edits).

**Service worker:** Replaced the shell handler with a real implementation that stores `{selectionText, pageUrl, pageTitle}` in `chrome.storage.session` and calls `chrome.action.openPopup()` with a `chrome.windows.create()` fallback.

**Extractor export:** Added `export { extractPageData }` to extractor.js so the popup can import the function reference for `executeScript({func})`. The function body remains fully self-contained.

## Verification

All task-level and slice-level verification checks pass:
- All modified JS files pass `node --check` syntax validation
- Manifest contains `"scripting"` in permissions
- `chrome.scripting.executeScript` present in popup.js
- `chrome.storage.session` present in both popup.js and service-worker.js
- `chrome.action.openPopup` present in service-worker.js
- `applySchemaOrgToForm` appears 2 times in popup.js (definition + call)
- `pendingPageData` appears 27 times in popup.js
- Zero inline event handlers in any modified file
- No imports/requires in extractor.js body (export line only)
- T01 schema-mapper tests still pass (suggestType, mapSchemaOrgToFormValues, normalizeSchemaType)
- Extractor export verified as self-contained function

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/popup/popup.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 3 | `node --check extension/content/extractor.js` | 0 | ✅ pass | <1s |
| 4 | `node --check extension/shared/schema-mapper.js` | 0 | ✅ pass | <1s |
| 5 | `node -e JSON.parse(manifest.json)` | 0 | ✅ pass | <1s |
| 6 | `grep -c '"scripting"' extension/manifest.json` → 1 | 0 | ✅ pass | <1s |
| 7 | `grep -c 'chrome.scripting.executeScript' extension/popup/popup.js` → 1 | 0 | ✅ pass | <1s |
| 8 | `grep -c 'chrome.storage.session' extension/background/service-worker.js` → 1 | 0 | ✅ pass | <1s |
| 9 | `grep -c 'chrome.storage.session' extension/popup/popup.js` → 2 | 0 | ✅ pass | <1s |
| 10 | `grep -c 'chrome.action.openPopup' extension/background/service-worker.js` → 1 | 0 | ✅ pass | <1s |
| 11 | `grep -c 'applySchemaOrgToForm' extension/popup/popup.js` → 2 | 0 | ✅ pass | <1s |
| 12 | `grep -rn 'onclick=\|onchange=' (all files)` → 0 lines | 0 | ✅ pass | <1s |
| 13 | `node -e` schema-mapper tests | 0 | ✅ pass | <1s |
| 14 | `node -e` extractor export self-contained check | 0 | ✅ pass | <1s |

## Diagnostics

- **Console signals:** Filter Chrome DevTools for `[SemPKM]` to see extraction results, type suggestions, and form fill counts
- **Context menu data:** Run `chrome.storage.session.get('contextMenuData')` in service worker DevTools to inspect pending pre-fill data
- **Injection failures:** Show as `[SemPKM] Content script injection failed: {error}` — expected on `chrome://` and Web Store pages
- **Schema.org miss:** No log when `suggestType()` returns null (silent degradation to manual type selection)
- **Failure shape:** When extraction fails entirely, popup still works with basic tab title/URL fallback

## Deviations

- Added `export { extractPageData }` to extractor.js (wasn't in plan but necessary for the popup to import the function reference for `executeScript({func})`). The function body remains fully self-contained — the export is a module-level statement that doesn't affect serialization.
- Updated service-worker.js JSDoc to remove "shell" wording (cosmetic).

## Known Issues

None.

## Files Created/Modified

- `extension/manifest.json` — added `"scripting"` to permissions array
- `extension/popup/popup.js` — rewrote init() with content script injection, added schema.org type suggestion, added applySchemaOrgToForm() called from handleTypeChange(), added context menu pre-fill check via chrome.storage.session, imported suggestType/mapSchemaOrgToFormValues/extractPageData
- `extension/background/service-worker.js` — replaced shell context menu handler with real implementation (session storage + openPopup with fallback)
- `extension/content/extractor.js` — added `export { extractPageData }` for popup import
- `.gsd/milestones/M014/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
