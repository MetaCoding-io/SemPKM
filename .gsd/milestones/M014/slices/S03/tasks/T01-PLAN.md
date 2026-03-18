---
estimated_steps: 8
estimated_files: 2
---

# T01: Content script extractor and schema.org mapper modules

**Slice:** S03 — Content scripts + context menu + schema.org
**Milestone:** M014

## Description

Create two pure-function modules that the popup integration (T02) depends on:

1. **`extension/content/extractor.js`** — A self-contained function that runs in the page's DOM context via `chrome.scripting.executeScript`. It must be completely self-contained (no imports, no closures, no references to extension code) because `executeScript` serializes/deserializes the function. Returns a plain object with page metadata and parsed schema.org JSON-LD.

2. **`extension/shared/schema-mapper.js`** — An ES module that maps schema.org JSON-LD entities to SemPKM type IRIs and SHACL form field paths. This runs in the popup context (normal ES module), not in the page context.

Both modules are testable with Node.js — no Chrome APIs needed.

## Steps

1. **Create `extension/content/extractor.js`:**
   - Export a single function `extractPageData()` that will be passed to `chrome.scripting.executeScript({func: extractPageData})`
   - Title extraction priority: `og:title` meta tag > `twitter:title` meta tag > `document.title`
   - URL: `window.location.href`
   - Selected text: `window.getSelection().toString()` (trimmed)
   - Author: `meta[name="author"]` > `meta[property="article:author"]`
   - Description: `meta[name="description"]` > `meta[property="og:description"]`
   - Schema.org JSON-LD: parse all `<script type="application/ld+json">` elements
     - Handle `@graph` arrays (flatten into individual entities)
     - Handle `@type` as string or array (normalize to bare type name — strip `schema:` prefix and `https://schema.org/` prefix)
     - Catch and skip invalid JSON (try/catch per element)
     - Handle nested objects (e.g., `author: { "@type": "Person", "name": "..." }`) — extract nested entities into the flat list
   - Return shape: `{ title, url, selectedText, author, description, schemaOrg: [...] }`
   - **Critical constraint**: The function body must be completely self-contained. No `import`, no closures over outer variables, no references to other extension files. It runs in the page's content script world.

2. **Create `extension/shared/schema-mapper.js`:**
   - Export `suggestType(schemaOrgEntities, availableTypes)`:
     - Takes the `schemaOrg` array from the extractor and the loaded types list from `/api/types`
     - Checks each entity's `@type` against the mapping table
     - Only suggests types that exist in `availableTypes`
     - Mapping table:
       - `Person` → `urn:sempkm:model:crm:Contact`
       - `Organization` → `urn:sempkm:model:crm:Company`
       - `Article`, `NewsArticle`, `BlogPosting` → `urn:sempkm:model:basic-pkm:Note`
       - `ScholarlyArticle` → `urn:sempkm:model:research:Paper`
     - Falls back to `null` if no match or matched type not available
     - Returns `{ typeIri, schemaEntity }` — the matched type IRI and the specific entity that matched
   - Export `mapSchemaOrgToFormValues(schemaEntity, shapeProperties)`:
     - Takes one schema.org entity and the current shape's `properties` array
     - Builds a `{path: value}` map matching form field `data-path` attributes
     - Two mapping levels:
       - **Direct namespace matches**: schema.org property name matches the SHACL path's local name under `https://schema.org/` namespace (e.g., `schema:url` → the property with path `https://schema.org/url`)
       - **Cross-namespace mappings**: explicit table:
         - `givenName` → `urn:sempkm:model:crm:firstName`
         - `familyName` → `urn:sempkm:model:crm:lastName`
         - `email` → `urn:sempkm:model:crm:email`
         - `telephone` → `urn:sempkm:model:crm:phone`
         - `jobTitle` → `https://schema.org/jobTitle`
         - `name` → `http://purl.org/dc/terms/title` (fallback)
         - `headline` → `http://purl.org/dc/terms/title`
         - `url` → `https://schema.org/url`
         - `datePublished` → `https://schema.org/datePublished`
     - Only include values for paths that actually exist in `shapeProperties`
     - Handle nested `author` objects (extract `name` string)
     - Skip values that are objects/arrays (only map string/number/boolean scalars)
   - Export `normalizeSchemaType(rawType)`:
     - Strips `https://schema.org/`, `http://schema.org/`, `schema:` prefixes
     - Handles array `@type` (returns first recognized type)
     - Returns bare type name string (e.g., `"Person"`)

3. **Verify both files:**
   - `node --check extension/content/extractor.js` — syntax valid
   - `node --check extension/shared/schema-mapper.js` — syntax valid
   - Write inline Node.js test exercising extractor return shape (mock a minimal DOM or just verify the function is parseable and returns correct structure with a JSDOM-free approach)
   - Write inline Node.js test exercising mapper: sample JSON-LD Person entity → `suggestType` returns Contact IRI → `mapSchemaOrgToFormValues` returns `{crm:firstName: "Jane", crm:lastName: "Doe"}`

## Must-Haves

- [ ] `extractPageData()` is self-contained — zero import/require/closure references
- [ ] Extractor handles `@graph` arrays, string and array `@type`, missing `@context`, invalid JSON
- [ ] Extractor returns `{ title, url, selectedText, author, description, schemaOrg: [...] }`
- [ ] Schema.org `@type` normalization strips all prefix forms (`schema:`, `https://schema.org/`, arrays)
- [ ] `suggestType()` only returns types that exist in the `availableTypes` list
- [ ] `mapSchemaOrgToFormValues()` handles both direct namespace and cross-namespace property mappings
- [ ] `mapSchemaOrgToFormValues()` only returns values for paths present in `shapeProperties`
- [ ] Both files pass `node --check`
- [ ] Node.js functional tests pass for mapper (suggestType + mapSchemaOrgToFormValues)

## Verification

- `node --check extension/content/extractor.js` — exits 0
- `node --check extension/shared/schema-mapper.js` — exits 0
- `node -e` test: import schema-mapper, call `suggestType` with a Person entity and a types list containing Contact → returns Contact IRI
- `node -e` test: import schema-mapper, call `mapSchemaOrgToFormValues` with Person entity and CRM shape properties → returns mapped values for firstName, lastName, email
- `node -e` test: verify `normalizeSchemaType` handles `"Person"`, `"schema:Person"`, `"https://schema.org/Person"`, `["Person", "Thing"]`
- Grep extractor.js for `import` / `require` — must return empty (self-contained constraint)

## Observability Impact

- **Extractor logging**: The extractor itself has no console.log (it runs in the page context — the caller logs). But invalid JSON-LD parsing logs a warning per invalid `<script>` tag: `[SemPKM] Skipping invalid JSON-LD: {error}` — this is emitted by the caller in T02, but the try/catch structure in the extractor enables it.
- **Mapper diagnostic signals**: `suggestType()` returns `null` (not throws) for unmapped types — callers inspect this to decide whether to log `[SemPKM] Schema.org type suggestion: none`. `mapSchemaOrgToFormValues()` silently skips non-scalar values and missing paths — the caller logs the count of applied values.
- **Inspection**: Both modules are pure functions — test with `node -e` at any time by importing and calling with sample data. No runtime state to inspect.
- **Failure shapes**: Extractor returns `{ title: null, url: '', selectedText: '', author: null, description: null, schemaOrg: [] }` when page has no metadata. Mapper returns `null` from `suggestType` when no types match. `mapSchemaOrgToFormValues` returns `{}` when no properties map.

## Inputs

- S03-RESEARCH.md content script and schema.org mapping sections — defines the extraction logic, mapping tables, and edge cases
- S01 Forward Intelligence — `populateFromPageData({title, url, selectedText, author})` is the expected shape; the mapper's output feeds into `[data-path]` form inputs
- S02 Forward Intelligence — SHACL renderer produces `data-path` attributes with full IRI paths (e.g., `https://schema.org/url`, `urn:sempkm:model:crm:firstName`)

## Expected Output

- `extension/content/extractor.js` — Self-contained page metadata + schema.org extraction function (~80-120 lines)
- `extension/shared/schema-mapper.js` — ES module with `suggestType`, `mapSchemaOrgToFormValues`, `normalizeSchemaType` exports (~100-150 lines)
- Both pass syntax checks and functional tests
