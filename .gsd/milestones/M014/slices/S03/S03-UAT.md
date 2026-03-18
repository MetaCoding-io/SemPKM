# S03: Content scripts + context menu + schema.org — UAT

**Milestone:** M014
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: These features require a real Chrome browser with the extension sideloaded on actual web pages — can't be tested via Playwright or Node.js alone. The pure-function modules have node -e unit tests; UAT covers the runtime integration.

## Preconditions

- Chrome browser with extension sideloaded from `extension/` directory (chrome://extensions → Load unpacked)
- SemPKM instance running at configured URL (docker compose up)
- At least one Mental Model installed (basic-pkm at minimum; CRM recommended for schema.org testing)
- API key configured in extension options page with green connection indicator
- Extension permissions granted (scripting permission should be requested on install)

## Smoke Test

Open the extension popup on any web page (e.g. Wikipedia). The title and URL fields should auto-fill from the page. If they do, the content script injection pipeline works.

## Test Cases

### 1. Auto-fill title and URL from page metadata

1. Navigate to any webpage with a `<title>` tag (e.g. `https://en.wikipedia.org/wiki/Knowledge_graph`)
2. Click the extension icon to open the popup
3. **Expected:** Title field shows the page title, URL field shows the current page URL
4. Check DevTools console for `[SemPKM] Extracted page data:` log with non-null title and url

### 2. Auto-fill from og:title meta tag

1. Navigate to a page with OpenGraph meta tags (e.g. most news articles, blog posts)
2. Open the extension popup
3. **Expected:** Title uses og:title value (not document.title) — visible if og:title differs from the `<title>` tag

### 3. Selected text pre-fill

1. Navigate to any page
2. Select a paragraph of text on the page
3. Open the extension popup
4. **Expected:** The notes/body field contains the selected text

### 4. Context menu "Save to SemPKM"

1. Navigate to any page
2. Select some text on the page
3. Right-click the selection → choose "Save to SemPKM" from the context menu
4. **Expected:** The extension popup opens with the selected text pre-filled in the notes/body field, plus the page title and URL filled in
5. Check service worker console (chrome://extensions → service worker "Inspect") for `[SemPKM] Context menu: stored selection data`

### 5. Schema.org Person → CRM Contact auto-fill

1. Navigate to a page with schema.org Person JSON-LD (e.g. a personal website with structured data, or use the test page below)
2. Open the extension popup
3. **Expected:** Type selector auto-switches to "Contact" (if CRM model is installed)
4. **Expected:** CRM form fields populate — givenName→firstName, familyName→lastName, email→email
5. Check console for `[SemPKM] Schema.org type suggestion: Person → urn:sempkm:model:crm:Contact`
6. Check console for `[SemPKM] Applied N schema.org values to form` with N > 0

Test page HTML (save locally and open in Chrome):
```html
<!DOCTYPE html>
<html><head><title>Test Person</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","givenName":"Alice","familyName":"Smith","email":"alice@example.com","jobTitle":"Engineer","name":"Alice Smith"}
</script></head><body><h1>Alice Smith</h1></body></html>
```

### 6. Schema.org Article → Note auto-fill

1. Navigate to a page with schema.org Article JSON-LD (most news sites have this)
2. Open the extension popup
3. **Expected:** Type selector auto-switches to "Note" (basic-pkm)
4. **Expected:** dcterms:title field gets the headline, author field populated if present
5. Check console for schema.org type suggestion log

### 7. Schema.org values re-apply on type change

1. Open popup on a page with schema.org Person data
2. Type auto-selects "Contact" and fields fill
3. Manually change the type selector to "Note"
4. **Expected:** Form re-renders for Note type; any matching schema.org fields (e.g. name→title) are applied
5. Change back to "Contact"
6. **Expected:** CRM fields re-populate from the stored schema.org data

### 8. Settings respect (toggle auto-fill off)

1. Open extension options page
2. Disable "Auto-fill title" toggle
3. Open popup on any page
4. **Expected:** URL field fills, but title field is empty
5. Re-enable "Auto-fill title", disable "Include selection"
6. Select text, open popup
7. **Expected:** Title fills, but notes/body field is empty

## Edge Cases

### Restricted page fallback (chrome:// pages)

1. Navigate to `chrome://extensions` or `chrome://settings`
2. Open the extension popup
3. **Expected:** Content script injection fails gracefully. Title falls back to tab title, URL to tab URL. Console shows `[SemPKM] Content script injection failed:` with error details. No crash, no empty popup.

### Page with no schema.org data

1. Navigate to a simple page with no JSON-LD script tags (e.g. a plain HTML file)
2. Open the extension popup
3. **Expected:** Title and URL auto-fill normally. No type auto-selection occurs. Console log shows `schemaOrg:0` in the extracted data summary.

### Page with invalid JSON-LD

1. Create a test page with a malformed `<script type="application/ld+json">` (e.g. `{invalid json}`)
2. Open the extension popup
3. **Expected:** Extractor skips the invalid JSON-LD block silently. Other metadata (title, URL) still extracts. No error thrown.

### Page with @graph array

1. Create a test page with JSON-LD containing `"@graph": [...]` with multiple entities
2. Open the extension popup
3. **Expected:** All entities in the @graph are extracted. Type suggestion uses the first matching entity.

### Context menu with no selection

1. Right-click on a page without selecting any text
2. **Expected:** The context menu item "Save to SemPKM" should not appear (it only shows when text is selected via the `contexts: ["selection"]` manifest setting)

## Failure Signals

- Popup opens with blank title and URL fields → content script injection broken
- "Save to SemPKM" missing from context menu → service worker not registering the context menu item
- Type selector doesn't auto-switch on schema.org pages → suggestType() returning null or import broken
- Form fields empty after type auto-select on schema.org page → applySchemaOrgToForm() not called or data-path mismatch
- Console error `Uncaught TypeError` in popup → likely a missing import or undefined variable in the wiring
- Context menu click does nothing → chrome.storage.session write or chrome.action.openPopup() failing

## Requirements Proved By This UAT

- EXT-03 (auto-population) — tests 1-3, 8 prove title/URL/selection auto-fill with settings respect
- EXT-05 (context menu) — test 4 proves right-click "Save to SemPKM" captures selected text
- EXT-06 (schema.org) — tests 5-7 prove JSON-LD type suggestion and property mapping

## Not Proven By This UAT

- EXT-04 (relationship picker) — S04 scope
- EXT-08 (keyboard shortcut) — S05 scope
- EXT-10 (cross-browser Firefox) — S05 scope
- EXT-13 (E2E automated tests) — S05 scope
- Schema.org mapping for types beyond Person/Organization/Article/ScholarlyArticle — only the mapped types are tested
- Performance under pages with very large JSON-LD (10+ entities) — not explicitly tested

## Notes for Tester

- The schema.org test cases work best with locally-created HTML test pages (see test case 5) because real websites vary in their JSON-LD quality.
- DevTools console filtering for `[SemPKM]` is the best diagnostic tool — every extraction, suggestion, and fill operation is logged.
- The service worker console is separate from the popup console — access it via chrome://extensions → "Inspect views: service worker" link.
- If the CRM model isn't installed, schema.org Person test will silently fall through (suggestType returns null when the target type isn't available).
