---
id: S03
parent: M014
milestone: M014
provides:
  - Content script page data extractor (title, URL, selected text, author, description, schema.org JSON-LD)
  - Schema.org to SemPKM type suggestion and SHACL form property mapping
  - Popup auto-fill from page metadata and schema.org JSON-LD on open and on type change
  - Context menu "Save to SemPKM" with session storage bridge to popup pre-fill
  - Manifest scripting permission for on-demand content script injection
requires:
  - slice: S01
    provides: Extension scaffold (popup, service worker, api-client, storage, manifest)
  - slice: S02
    provides: SHACL form renderer with data-path inputs, type selector, handleTypeChange()
affects:
  - S05
key_files:
  - extension/content/extractor.js
  - extension/shared/schema-mapper.js
  - extension/manifest.json
  - extension/popup/popup.js
  - extension/background/service-worker.js
key_decisions:
  - D190 — chrome.scripting.executeScript({func}) injection (no persistent content script, no message-passing)
  - D191 — chrome.storage.session bridge for context menu → popup data flow (consume-and-clear pattern)
  - D192 — Cross-namespace mappings take priority over direct schema.org namespace matches
patterns_established:
  - Self-contained content script pattern — function with var declarations, no closures/imports, serializable by executeScript
  - Content script → session storage → popup init pattern for context menu pre-fill
  - Schema.org type normalization strips three prefix forms (https://, http://, schema:) and handles array @type
  - applySchemaOrgToForm() called from handleTypeChange() ensures schema.org values survive type switches
observability_surfaces:
  - "[SemPKM] Extracted page data:" in popup console with title/url/selectedText length/schemaOrg count
  - "[SemPKM] Schema.org type suggestion:" when auto-selecting a type from JSON-LD
  - "[SemPKM] Applied N schema.org values to form" after filling data-path inputs
  - "[SemPKM] Content script injection failed:" with error and fallback note
  - "[SemPKM] Context menu: stored selection data" in service worker console
drill_down_paths:
  - .gsd/milestones/M014/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S03/tasks/T02-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Content scripts + context menu + schema.org

**Page data extraction, schema.org auto-fill, and context menu capture wired into the extension popup — completing the three auto-population requirements (EXT-03, EXT-05, EXT-06).**

## What Happened

Built two pure-function modules and wired them into the extension's popup lifecycle and service worker.

**T01 — Extractor and mapper modules.** Created `extension/content/extractor.js` as a fully self-contained function (var declarations, no imports, no closures) that Chrome can serialize via `executeScript({func})`. It extracts page title (og:title > twitter:title > document.title), URL, selected text, author, description, and all schema.org JSON-LD entities — handling `@graph` arrays, prefixed `@type` values, nested entities, and invalid JSON gracefully. Created `extension/shared/schema-mapper.js` as an ES module with three exports: `normalizeSchemaType()` (strips three prefix forms), `suggestType()` (maps schema.org types to SemPKM type IRIs — Person→Contact, Organization→Company, Article→Note, ScholarlyArticle→Paper), and `mapSchemaOrgToFormValues()` (maps entity properties to SHACL form `data-path` values via cross-namespace and direct-namespace tables).

**T02 — Integration and wiring.** Rewrote the popup `init()` flow with a three-path data acquisition: (1) check `chrome.storage.session` for context menu pre-fill data, (2) inject extractor via `chrome.scripting.executeScript({func})`, (3) fall back to `tab.title`/`tab.url` on injection failure (restricted pages). After extraction, basic fields are filled respecting settings (`autoFillTitle`, `autoFillUrl`, `includeSelection`). Schema.org type suggestion auto-selects the matching type in the dropdown and triggers form rendering. Added `applySchemaOrgToForm()` called at the end of `handleTypeChange()` — this maps pending schema.org entity properties to `[data-path]` form inputs, plus injects page title/URL into dcterms:title and schema:url paths. Only fills empty inputs (won't overwrite user edits). Replaced the service worker's shell context menu handler with real implementation: stores selection data in session storage and calls `chrome.action.openPopup()` with `chrome.windows.create()` fallback. Added `"scripting"` to manifest permissions.

## Verification

All 14 slice-level checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `node --check extension/content/extractor.js` | ✅ pass |
| 2 | `node --check extension/shared/schema-mapper.js` | ✅ pass |
| 3 | `node --check extension/popup/popup.js` | ✅ pass |
| 4 | `node --check extension/background/service-worker.js` | ✅ pass |
| 5 | `"scripting"` in manifest.json permissions | ✅ 1 match |
| 6 | `chrome.scripting.executeScript` in popup.js | ✅ 1 match |
| 7 | `chrome.storage.session` in service-worker.js | ✅ 1 match |
| 8 | `chrome.storage.session` in popup.js | ✅ 2 matches |
| 9 | `chrome.action.openPopup` in service-worker.js | ✅ 1 match |
| 10 | `applySchemaOrgToForm` in popup.js | ✅ 2 matches (def + call) |
| 11 | `pendingPageData` in popup.js | ✅ 27 matches |
| 12 | Zero inline event handlers (onclick/onchange) in all modified files | ✅ 0 found |
| 13 | normalizeSchemaType tests (6 cases) + suggestType tests (5 cases) + mapSchemaOrgToFormValues tests (8 cases) | ✅ 19/19 pass |
| 14 | Extractor self-containment (no imports in function body) | ✅ pass |

No E2E tests or user guide docs for this slice — the extension isn't testable via Playwright against Docker (requires actual Chrome sideloading). E2E and docs are planned for S05.

## Requirements Advanced

- EXT-03 (auto-population) — Popup auto-fills title, URL, and selected text from page metadata on open. Settings toggles respected.
- EXT-05 (context menu) — Right-click "Save to SemPKM" stores selection in session storage and opens popup with text pre-filled.
- EXT-06 (schema.org) — JSON-LD entities parsed from page, type suggestion auto-selects matching type, property values mapped to SHACL form fields via cross-namespace and direct-namespace tables.

## Requirements Validated

None — these three requirements need live Chrome testing (S05 UAT) to be fully validated. The code is structurally complete and unit-tested, but runtime integration proof requires sideloading.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- Added `export { extractPageData }` to extractor.js — not in the original plan but necessary for the popup to import the function reference for `executeScript({func})`. The function body remains fully self-contained; the export is a module-level statement that doesn't affect serialization.

## Known Limitations

- Schema.org type mapping covers Person, Organization, Article, NewsArticle, BlogPosting, ScholarlyArticle. Other types (Event, Product, Recipe, etc.) are not mapped — they'll fall through silently and the user manually selects a type.
- Cross-namespace property mapping is hardcoded for CRM model paths (crm:firstName, crm:lastName, etc.). Other models with different namespace patterns won't get cross-namespace mappings, only direct schema.org namespace matches.
- `chrome.action.openPopup()` may not be available in all Chrome versions — the fallback creates a new window, which is slightly different UX.

## Follow-ups

None.

## Files Created/Modified

- `extension/content/extractor.js` — Self-contained page data extraction function (105 lines), plus export statement
- `extension/shared/schema-mapper.js` — Schema.org → SemPKM type/property mapper ES module (167 lines)
- `extension/manifest.json` — Added `"scripting"` to permissions array
- `extension/popup/popup.js` — Rewrote init() with content script injection, added schema.org type suggestion and applySchemaOrgToForm(), added context menu pre-fill check via chrome.storage.session
- `extension/background/service-worker.js` — Replaced shell context menu handler with real implementation (session storage + openPopup with fallback)

## Forward Intelligence

### What the next slice should know
- The popup stores extracted page data in a module-level `pendingPageData` variable that persists across type changes within a single popup session. `applySchemaOrgToForm()` is called at the end of `handleTypeChange()`, so any new form rendering triggers re-application of schema.org values.
- The `[data-path]` attribute contract from the SHACL renderer (S02) is the integration point — schema.org values are applied by finding inputs with matching data-path attributes and setting their `.value`.
- Object reference fields have `data-target-class` attributes — S04's relationship picker should enhance these without breaking the data-path value extraction that `getFormValues()` depends on.

### What's fragile
- The extractor function must remain fully self-contained — any use of `let`/`const`/arrow functions/`for...of` could break in older page contexts where strict mode isn't enabled. The `var` + traditional loop pattern is deliberate.
- The cross-namespace mapping table (`CROSS_NS_MAP`) is static. If new Mental Models are added with different namespace patterns, the mapper won't know about them. This is acceptable for Phase 1 but would need a dynamic approach for Phase 2.

### Authoritative diagnostics
- Filter Chrome DevTools console for `[SemPKM]` — all extraction, suggestion, and fill operations are logged with structured data
- `chrome.storage.session.get('contextMenuData')` in service worker DevTools shows pending context menu pre-fill data

### What assumptions changed
- None — the S01 boundary map accurately described the consumed surfaces (api-client, storage, popup shell, service worker shell) and the S02 boundary map accurately described the SHACL renderer's data-path contract.
