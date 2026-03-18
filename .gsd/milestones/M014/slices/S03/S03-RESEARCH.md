# S03: Content Scripts + Context Menu + Schema.org — Research

**Date:** 2026-03-18
**Status:** Complete

## Summary

S03 wires the popup to the actual web page. Three capabilities: (1) a content script that extracts page metadata and sends it to the popup via `chrome.runtime` messaging, (2) the context menu "Save to SemPKM" handler in the service worker that opens the popup with selected text pre-filled, and (3) schema.org JSON-LD parsing that maps structured data on the page to SHACL form fields.

All the infrastructure is in place from S01/S02. The popup already exports `populateFromPageData({title, url, selectedText, author})` and has `#dynamic-form` with `data-path` attributes on every input. The service worker already registers the context menu item with a shell handler. The manifest already has `activeTab` permission. What's missing is the content script itself (`extension/content/extractor.js`), the messaging glue, the manifest `content_scripts` entry, and the schema.org-to-SHACL field mapping logic.

The schema.org mapping is cleaner than expected: several model properties already use the `schema:` namespace (expanding to `https://schema.org/`), so `schema:url` on a page's JSON-LD maps directly to the `https://schema.org/url` property path in the SHACL form. For properties using model-specific namespaces (`crm:firstName`, `crm:email`), S03 needs a lightweight mapping table: `schema:givenName → crm:firstName`, `schema:familyName → crm:lastName`, etc.

## Recommendation

Build the content script as a single `extractor.js` module injected via `chrome.scripting.executeScript` from the popup (not a persistent content script). This approach:
- Avoids running on every page load (battery/memory)
- Uses `activeTab` permission (already declared) — no broad `<all_urls>` content script injection
- Executes only when the user opens the popup or clicks context menu
- Returns results synchronously via the `executeScript` return value

For the context menu flow: Chrome MV3 supports `chrome.action.openPopup()` from the service worker's context menu handler. Store the selection data in `chrome.storage.session`, then open the popup. The popup checks `chrome.storage.session` on init for pre-filled data. Firefox doesn't support `chrome.action.openPopup()`, so the cross-browser fallback (S05) will need a different approach — but S03 targets Chrome only.

## Implementation Landscape

### Key Files

**New files:**
- `extension/content/extractor.js` — Page metadata extraction function. Runs in page context via `chrome.scripting.executeScript`. Returns `{title, url, selectedText, author, description, schemaOrg: [...]}`. Parses `<script type="application/ld+json">` elements, extracts `document.title`/`og:title`/`twitter:title`, meta tags, and `window.getSelection()`.
- `extension/shared/schema-mapper.js` — Maps schema.org JSON-LD data to SHACL form field paths. Contains: (a) schema.org type → SemPKM type IRI mapping, (b) schema.org property → SHACL path mapping, (c) a `mapSchemaOrgToFormValues(schemaData, shapeProperties)` function that returns `{path: value}` pairs.

**Modified files:**
- `extension/manifest.json` — Add `"permissions": ["scripting"]` to support `chrome.scripting.executeScript`. No `content_scripts` section needed (on-demand injection).
- `extension/popup/popup.js` — Replace the bare `chrome.tabs.query` URL/title extraction with content script injection. Enhance `populateFromPageData` to handle both fallback fields AND dynamic SHACL form fields. Check `chrome.storage.session` on init for context menu pre-fill data.
- `extension/background/service-worker.js` — Fill in the context menu click handler: store `{selectionText, pageUrl, pageTitle}` in `chrome.storage.session`, then call `chrome.action.openPopup()`.

**Unchanged files (consume only):**
- `extension/shared/shacl-renderer.js` — Form inputs use `data-path` attributes with full IRI paths (e.g., `https://schema.org/url`, `urn:sempkm:model:crm:firstName`). `getFormValues()` reads these back.
- `extension/shared/api-client.js` — No changes needed.
- `extension/shared/storage.js` — Settings `autoFillTitle`, `autoFillUrl`, `includeSelection` already exist and control auto-fill behavior.

### Content Script — extractor.js

The extractor runs in the page's DOM context. It must be a plain function (not ES module) since `chrome.scripting.executeScript` with `func` parameter serializes/deserializes. Returns a plain object:

```js
{
  title: "Page Title",           // Priority: og:title > twitter:title > document.title
  url: "https://example.com",    // window.location.href
  selectedText: "...",           // window.getSelection().toString()
  author: "Jane Doe",           // meta[name=author] > meta[property=article:author]
  description: "...",            // meta[name=description] > og:description
  schemaOrg: [                   // Parsed <script type="application/ld+json"> elements
    { "@type": "Person", "name": "Jane Doe", "email": "jane@example.com", ... }
  ]
}
```

Schema.org JSON-LD parsing needs to be defensive:
- Multiple `<script type="application/ld+json">` elements per page
- JSON-LD can have `@graph` arrays containing multiple entities
- `@type` can be a string or array
- Nested objects (e.g., `author: { "@type": "Person", "name": "..." }`)
- Missing `@context` (some pages just use the raw schema.org property names)
- Invalid JSON in script tags (catch and skip)

### Schema.org → SHACL Mapping

Two levels of mapping:

**1. Type suggestion:** When the page has a schema.org type, suggest the corresponding SemPKM type in the type selector.

| schema.org @type | SemPKM Type IRI | Model |
|---|---|---|
| `Person` | `urn:sempkm:model:crm:Contact` | CRM |
| `Organization` | `urn:sempkm:model:crm:Company` | CRM |
| `Article`, `NewsArticle`, `BlogPosting` | `urn:sempkm:model:basic-pkm:Note` | basic-pkm |
| `ScholarlyArticle` | `urn:sempkm:model:research:Paper` | Research |

Only suggest types that are actually available (check against loaded types list). Fall through to Note if no specific match.

**2. Property mapping:** When a type is selected and schema.org data is available, fill matching form fields.

Direct namespace matches (schema.org property → SHACL path, same namespace):
- `schema:url` → `https://schema.org/url` (used by PersonShape, ConceptShape, SourceShape)
- `schema:jobTitle` → `https://schema.org/jobTitle` (PersonShape)
- `schema:datePublished` → `https://schema.org/datePublished` (SourceShape)

Cross-namespace mappings (schema.org property → model-specific SHACL path):
- `schema:givenName` → `urn:sempkm:model:crm:firstName`
- `schema:familyName` → `urn:sempkm:model:crm:lastName`
- `schema:email` → `urn:sempkm:model:crm:email`
- `schema:name` → `http://purl.org/dc/terms/title` (fallback for title-like fields)
- `schema:headline` → `http://purl.org/dc/terms/title`
- `schema:description` → body field (if body path available)
- `schema:author` → extract name string if nested object

The `mapSchemaOrgToFormValues()` function takes the schema.org entity data and the current shape's property list, and returns values keyed by full IRI path. The popup then iterates `data-path` inputs and fills matching values.

### Popup Integration — Auto-fill Flow

Current popup `init()` flow:
1. Load settings → check connection → populate types → render shape
2. Get active tab URL/title via `chrome.tabs.query`

New flow with content script:
1. Load settings → check connection → populate types
2. Check `chrome.storage.session` for context menu pre-fill data → if found, clear it and use
3. If no pre-fill: inject `extractor.js` via `chrome.scripting.executeScript` into active tab → get page data
4. Use extracted data for: (a) basic fields (title → fallback title or dynamic title field, URL → source URL, selectedText → notes), (b) schema.org type suggestion (auto-select type in dropdown), (c) after shape loads, fill matching SHACL fields
5. Store the extracted schema.org data so it can be re-applied when the user changes types

The `populateFromPageData` function needs enhancement: it currently only fills fallback fields (simple title/URL/notes). It must also fill `data-path` inputs in the dynamic form when a shape is loaded.

New function: `applySchemaOrgToForm(schemaData, shapeProperties, formContainer)`:
- Called after `handleTypeChange()` renders the SHACL form
- Iterates the mapping table
- For each mapped property, finds the `[data-path="..."]` input in the form and sets its value
- Handles both direct namespace matches and cross-namespace mappings

### Context Menu — Service Worker Handler

The existing shell handler becomes:

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
    // Chrome MV3: open popup programmatically
    await chrome.action.openPopup();
  }
});
```

The popup's init checks `chrome.storage.session.get('contextMenuData')` and if present:
1. Clears the stored data
2. Pre-fills the notes field with `selectionText`
3. Pre-fills the URL field with `pageUrl`
4. Proceeds with the normal flow (type selection, shape loading)

### Manifest Changes

Add `"scripting"` to permissions:
```json
"permissions": ["storage", "activeTab", "contextMenus", "scripting"]
```

No `content_scripts` section — `extractor.js` is injected on-demand via `chrome.scripting.executeScript`, which works under the `activeTab` permission when the user interacts (clicks extension icon or context menu).

### Build Order

1. **T01 — Content script extractor:** Create `extension/content/extractor.js` with page metadata + schema.org JSON-LD extraction. Write as a plain function compatible with `chrome.scripting.executeScript`. Test with `node --check` for syntax. Covers EXT-03 (auto-population extraction) and EXT-06 (schema.org extraction).

2. **T02 — Schema.org mapper:** Create `extension/shared/schema-mapper.js` with type suggestion mapping and property-to-path mapping. Pure functions, testable without Chrome APIs. Covers EXT-06 (schema.org form filling).

3. **T03 — Popup integration + context menu wiring:** Update `manifest.json` (add `scripting` permission), update `popup.js` to inject content script and apply extracted data to both fallback and dynamic form fields, update `service-worker.js` context menu handler. Covers EXT-03 (auto-population), EXT-05 (context menu), EXT-06 (schema.org integration).

### Verification Approach

- `node --check` on all new/modified JS files (syntax, no inline handlers)
- Content script extractor tested by loading the extension in Chrome, opening popup on various pages, checking DevTools console for `[SemPKM]` extraction logs
- Schema.org: visit a page with JSON-LD (e.g., a Wikipedia article, LinkedIn profile) and verify type suggestion and field auto-fill
- Context menu: select text on a page → right-click → "Save to SemPKM" → popup opens with text in Notes field
- Auto-fill settings: toggle `autoFillTitle`/`autoFillUrl`/`includeSelection` in options and verify they're respected
- Full round-trip: extract + auto-fill + save → object appears in SemPKM with correct properties

## Constraints

- `chrome.scripting.executeScript` requires `scripting` permission and only works on tabs where `activeTab` is granted (user interaction trigger)
- Content script function passed to `executeScript({func})` must be self-contained — cannot reference outer scope variables or import modules
- `chrome.action.openPopup()` works in Chrome MV3 but NOT in Firefox — S05 will need a cross-browser alternative for context menu
- `chrome.storage.session` is Chrome MV3 only and not synced — suitable for ephemeral context menu data
- Schema.org JSON-LD parsing must be best-effort — real-world JSON-LD is messy (arrays, missing context, nested objects, invalid JSON)

## Common Pitfalls

- **`executeScript` function serialization** — The function runs in the page's content script world. It cannot use closures, imports, or references to extension code. Must be completely self-contained with all logic inline.
- **Multiple schema.org entities per page** — Pages often have multiple `<script type="application/ld+json">` blocks (e.g., Article + Organization + WebSite). The extractor should return all of them; the mapper picks the most relevant one based on the selected type.
- **`chrome.storage.session` not available in Firefox** — Firefox doesn't support `chrome.storage.session`. For S05 cross-browser, use `chrome.storage.local` with a cleanup-on-read pattern. S03 targets Chrome only.
- **Dynamic form not yet rendered when page data arrives** — The content script extraction returns before the type selector + shape fetch completes. Must store the extracted data and re-apply when `handleTypeChange()` finishes rendering. Use a module-level variable (e.g., `let pendingPageData = null`) and check it at the end of `handleTypeChange()`.
- **Schema.org `@type` normalization** — JSON-LD `@type` can be: `"Person"`, `"schema:Person"`, `"https://schema.org/Person"`, or `["Person", "Thing"]`. Normalize all forms to the bare type name before matching.

## Open Risks

- **`chrome.action.openPopup()` reliability** — Documented as working from service worker in Chrome MV3, but some Chrome versions may restrict it. If it doesn't work reliably, fallback is `chrome.windows.create()` opening `popup.html` as a popup window (slightly different UX but functional).
- **Content script injection on restricted pages** — `chrome.scripting.executeScript` fails on `chrome://`, `chrome-extension://`, and Chrome Web Store pages. The popup should handle this gracefully (fall back to tab title/URL only).
