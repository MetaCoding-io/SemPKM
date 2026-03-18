---
id: T01
parent: S03
milestone: M014
provides:
  - extension/content/extractor.js — self-contained page data extraction function for chrome.scripting.executeScript
  - extension/shared/schema-mapper.js — ES module mapping schema.org JSON-LD to SemPKM types and SHACL form paths
key_files:
  - extension/content/extractor.js
  - extension/shared/schema-mapper.js
key_decisions:
  - Extractor uses var declarations and for-loops (no let/const/for-of) for maximum compatibility in page contexts
  - Cross-namespace mappings take priority over direct namespace matches in mapSchemaOrgToFormValues (first-write-wins)
patterns_established:
  - Self-contained content script pattern — function with nested helpers, no closures, no imports, serializable by chrome.scripting.executeScript
  - Schema.org type normalization strips three prefix forms (https://, http://, schema:) and handles array @type
observability_surfaces:
  - Both modules are pure functions testable with node -e at any time
  - Extractor returns structured defaults (null/empty) for missing metadata — no exceptions
  - Mapper returns null from suggestType for unrecognized/unavailable types
  - Mapper returns {} from mapSchemaOrgToFormValues when no properties match
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Content script extractor and schema.org mapper modules

**Built self-contained page data extractor and schema.org-to-SemPKM mapper with full edge case handling and passing tests.**

## What Happened

Created two pure-function modules that T02 (popup integration) depends on:

1. **`extension/content/extractor.js`** — A single `extractPageData()` function that runs in the page's DOM context via `chrome.scripting.executeScript`. Extracts title (og:title > twitter:title > document.title), URL, selected text, author, description, and all schema.org JSON-LD entities. Handles `@graph` arrays, prefixed `@type` values, nested entities (e.g. author objects), array `@type`, and invalid JSON (try/catch per script element). Returns a flat `{ title, url, selectedText, author, description, schemaOrg: [...] }` object. Uses `var` and traditional loops for broadest compatibility in injected page contexts.

2. **`extension/shared/schema-mapper.js`** — ES module exporting three functions:
   - `normalizeSchemaType(rawType)` — strips `https://schema.org/`, `http://schema.org/`, `schema:` prefixes; handles array `@type`
   - `suggestType(schemaOrgEntities, availableTypes)` — maps schema.org types to SemPKM IRIs (Person→Contact, Organization→Company, Article/NewsArticle/BlogPosting→Note, ScholarlyArticle→Paper); only returns types present in `availableTypes`
   - `mapSchemaOrgToFormValues(schemaEntity, shapeProperties)` — maps entity properties to SHACL form `data-path` values via direct namespace and cross-namespace tables; handles nested author objects; skips arrays/objects/nulls

## Verification

- `node --check` passes for both files
- Self-containment: grep for `import`/`require` in extractor.js returns only comments
- normalizeSchemaType: 9 test cases pass (bare, prefixed, URL, array, null, empty)
- suggestType: 7 test cases pass (Person→Contact, Organization→Company, Article→Note, unknown→null, unavailable→null, ScholarlyArticle→Paper, edge cases)
- mapSchemaOrgToFormValues: 5 test groups pass (Person→CRM fields, Article→Note fields with nested author, limited shapeProperties filtering, skip arrays/objects/nulls, edge cases)
- extractPageData: 6 test groups pass (return shape, basic values, entity extraction from @graph/nested/prefixed/array, invalid JSON skip, 7 entities extracted)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/content/extractor.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/shared/schema-mapper.js` | 0 | ✅ pass | <1s |
| 3 | `grep -n 'import\|require' extension/content/extractor.js` (only comments) | 0 | ✅ pass | <1s |
| 4 | `node -e` normalizeSchemaType tests (9 cases) | 0 | ✅ pass | <1s |
| 5 | `node -e` suggestType tests (7 cases) | 0 | ✅ pass | <1s |
| 6 | `node -e` mapSchemaOrgToFormValues tests (5 groups) | 0 | ✅ pass | <1s |
| 7 | `node -e` extractPageData mock DOM tests (6 groups) | 0 | ✅ pass | <1s |
| 8 | `node -e` diagnostic failure-path tests | 0 | ✅ pass | <1s |

## Diagnostics

- **Test either module**: `node -e 'import { suggestType } from "./extension/shared/schema-mapper.js"; console.log(suggestType([{"@type":"Person"}], [{iri:"urn:sempkm:model:crm:Contact"}]));' --input-type=module`
- **Test extractor**: eval the file contents in Node with a mock `document`/`window`, call `extractPageData()`
- **Failure shapes**: extractor returns `{ title: null, url: "", selectedText: "", author: null, description: null, schemaOrg: [] }` on empty pages; mapper returns `null`/`{}` for unrecognized inputs

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/content/extractor.js` — Self-contained page data extraction function (105 lines)
- `extension/shared/schema-mapper.js` — Schema.org → SemPKM type/property mapper ES module (167 lines)
