# M014: Browser Extension Phase 1 — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

M014 builds a Chrome/Firefox browser extension for structured knowledge capture from any web page. The extension is primarily a **frontend project** — the vast majority of backend API surface already exists from M013 (types, shapes, context-query, well-known discovery). Two critical backend gaps remain: (1) the `POST /api/commands` endpoint uses session-cookie-only auth via `require_role("owner", "member")` → `get_current_user`, which rejects Bearer tokens; (2) the SPARQL endpoint (`/api/sparql`) has the same cookie-only auth, blocking the relationship picker.

The extension's core technical challenge is the **SHACL form renderer in vanilla JS** — translating the structured JSON from `GET /api/shapes/{type_iri}` into dynamic HTML forms that handle string, date, boolean, enum, object reference, multi-value, and grouped fields. The existing Jinja2 template (`_field.html`) is the reference implementation with ~200 lines covering all property types. The JS renderer will be a simpler but faithful port.

Cross-browser compatibility requires a dual-manifest approach: Chrome demands `background.service_worker` (MV3), while Firefox (as of mid-2025) only supports `background.scripts`. Both share the same codebase for popup, content scripts, and shared modules. The `browser` namespace polyfill or conditional API calls bridge the `chrome.*` vs `browser.*` API differences.

## Recommendation

**Prove auth first, then build UI.** The single highest-risk item is that the extension cannot create objects via the existing API — `require_role` chains to cookie-only auth. Fix this backend gap in the first slice (small, surgical change), then build all extension UI on a proven API contract. This mirrors the M013 pattern where `get_current_user_or_api` was created for the API surface.

**Client-side SHACL rendering (Option A from design doc).** The extension fetches shape JSON and renders forms in JS. This avoids a network round-trip for form HTML, enables offline-ish form rendering from cached shapes, and keeps the extension self-contained. The JS renderer handles the common SHACL property types used in standard Mental Models — not every edge case.

**Sideload-only distribution** for Phase 1. Chrome Web Store review adds latency and constraints (code review, privacy disclosures). Sideloading is sufficient for early adopters and development iteration.

## Implementation Landscape

### Key Files

**Backend (auth gap — small changes):**
- `backend/app/auth/dependencies.py` — Contains `get_current_user_or_api` (dual-auth) and `require_role` (cookie-only). Need a `require_role_or_api` that chains to `get_current_user_or_api` instead of `get_current_user`.
- `backend/app/commands/router.py` — `POST /api/commands` uses `Depends(require_role("owner", "member"))`. Must switch to `require_role_or_api("owner", "member")` so the extension can create objects with Bearer tokens.
- `backend/app/sparql/router.py` — All 18+ endpoints use `Depends(get_current_user)`. The extension's relationship picker needs Bearer auth on at least the query execution endpoint.

**Backend (existing, no changes needed):**
- `backend/app/api/router.py` — All M013 endpoints already use `get_current_user_or_api`. Types, shapes, context-query, and well-known all work with Bearer tokens.
- `backend/app/services/shapes.py` — `ShapesService` returns `NodeShapeForm` dataclasses with `PropertyShape` entries. The `/api/shapes/{type_iri}` endpoint serializes these to JSON. Extension consumes this JSON directly.
- `backend/app/commands/schemas.py` — `ObjectCreateParams` (type, slug, properties), `EdgeCreateParams` (source, target, predicate, properties). Extension must construct these payloads.
- `backend/app/commands/handlers/object_create.py` — Shows how type IRIs resolve (full IRI or local name), how `_resolve_predicate` handles compact IRIs and full IRIs, and how `_to_rdf_value` converts strings/numbers/booleans to RDF literals.

**Frontend reference (form rendering patterns):**
- `backend/app/templates/forms/_field.html` — The Jinja2 macro that the JS SHACL renderer must replicate. Covers: string, date, datetime, boolean, integer, decimal/float, URI, enum (sh:in), object reference (sh:class), tags, multi-value lists.
- `backend/app/templates/forms/object_form.html` — Shows how groups are rendered as fieldsets with form structure.

**Extension (new files):**
- `extension/` — New top-level directory alongside `backend/`, `frontend/`, `models/`, `e2e/`
- `extension/manifest.json` — Chrome MV3 manifest
- `extension/manifest.firefox.json` — Firefox-specific manifest overrides (background.scripts instead of service_worker)
- `extension/popup/` — Capture popup HTML/JS/CSS
- `extension/background/` — Service worker (Chrome) / background script (Firefox)
- `extension/content/` — Content scripts for page metadata extraction and context menu
- `extension/shared/` — SHACL renderer, API client, auth module, storage
- `extension/options/` — Settings page
- `extension/assets/` — Icons (16, 32, 48, 128px)

### Critical Backend Auth Gap

**Problem:** The extension sends `Authorization: Bearer <token>` headers. The `/api/commands` endpoint uses `require_role("owner", "member")` which internally calls `get_current_user` — a cookie-only dependency. Bearer tokens are silently ignored, resulting in 401.

**The `require_role` chain:**
```
require_role("owner", "member")
  → _check_role(current_user = Depends(get_current_user))
    → get_current_user(token = Depends(get_session_token))
      → get_session_token(sempkm_session = Cookie(None))
        → Raises 401 if no cookie
```

**Fix:** Create `require_role_or_api(*roles)` in `dependencies.py` that chains to `get_current_user_or_api` instead of `get_current_user`. Then update `commands/router.py` to use it. Same pattern for SPARQL endpoints that the relationship picker needs.

This is a ~20-line change in `dependencies.py` + 2-line change in `commands/router.py` + selective changes in `sparql/router.py`. Low risk, high value.

### SHACL Form Renderer (JS)

The renderer translates `GET /api/shapes/{type_iri}` JSON into HTML form elements. The shape response structure:

```json
{
  "shape_iri": "...",
  "target_class": "urn:sempkm:model:crm:Contact",
  "label": "Contact Shape",
  "helptext": "...",
  "groups": [
    {"iri": "crm:ContactBasicInfoGroup", "label": "Basic Info", "order": 1}
  ],
  "properties": [
    {
      "path": "crm:firstName",
      "name": "First Name",
      "datatype": "http://www.w3.org/2001/XMLSchema#string",
      "min_count": 1, "max_count": 1,
      "order": 1,
      "group": "crm:ContactBasicInfoGroup",
      "helptext": "The contact's first name."
    }
  ]
}
```

**Property type → HTML input mapping (from `_field.html`):**

| SHACL Property | HTML Widget | Notes |
|---|---|---|
| `xsd:string` (default) | `<input type="text">` | Fallback for unknown datatypes |
| `xsd:date` | `<input type="date">` | |
| `xsd:dateTime` | `<input type="datetime-local">` | Strip timezone for input value |
| `xsd:boolean` | `<select>` Yes/No | Not checkbox — matches backend |
| `xsd:integer` | `<input type="number" step="1">` | |
| `xsd:decimal/float/double` | `<input type="number" step="0.01">` | |
| `xsd:anyURI` | `<input type="url">` | |
| `sh:in [list]` | `<select>` with options | Enum constraint |
| `sh:class` (target_class) | Search input + hidden IRI | Object reference picker |
| tags (`tags`/`keywords` in path) | Text input | Tag autocomplete (simplified) |
| `max_count` null or > 1 | Multi-value list + Add button | Clone pattern from _field.html |

**Scope limitation:** The extension renderer does NOT need: regex patterns (sh:pattern), complex cardinality beyond min/max, nested shapes, conditional shapes, custom validators. These don't appear in any of the 5 standard Mental Models.

### Object Creation Payload

The extension constructs a `POST /api/commands` payload:

```json
{
  "command": "object.create",
  "params": {
    "type": "urn:sempkm:model:basic-pkm:Note",
    "properties": {
      "dcterms:title": "Page Title",
      "schema:url": "https://example.com/article",
      "bpkm:noteType": "reference"
    }
  }
}
```

For relationships, a second command creates an edge:
```json
{
  "command": "edge.create",
  "params": {
    "source": "<newly-created-object-iri>",
    "target": "urn:sempkm:...:concept-123",
    "predicate": "bpkm:isAbout"
  }
}
```

The commands endpoint supports batch (array) payloads. The extension can send both object.create and edge.create in one atomic request, provided it mints the object IRI client-side or uses the returned IRI from the first command result.

**Issue:** The commands endpoint returns the created IRI in the response. But batch commands are atomic — all share one event graph. The extension can send `[object.create, edge.create]` as a batch IF the object.create doesn't need a slug (UUID-minted). For relationship creation, the extension must either:
1. Send object.create first, get the IRI from the response, then send edge.create separately, OR
2. Use a client-minted IRI (construct the IRI following the `mint_object_iri` pattern) and include both in a single batch

Option 1 is simpler and sufficient for v1.

### Page Metadata Extraction (Content Script)

The content script extracts:
1. **Title:** `document.title`, `og:title`, `twitter:title` (first available)
2. **URL:** `window.location.href`
3. **Author:** `meta[name=author]`, `meta[property=article:author]`, `og:author`
4. **Description:** `meta[name=description]`, `og:description`
5. **Selected text:** `window.getSelection().toString()`
6. **Schema.org JSON-LD:** Parse all `<script type="application/ld+json">` elements

Schema.org type mapping:
- `schema:Person` → CRM Contact (if crm model installed)
- `schema:Article` / `ScholarlyArticle` → Note or Paper
- `schema:Organization` → CRM Company
- Other types → Note with auto-populated properties

### Cross-Browser Compatibility

**Chrome (MV3):**
```json
{
  "manifest_version": 3,
  "background": { "service_worker": "background/service-worker.js" },
  "action": { "default_popup": "popup/popup.html" },
  "permissions": ["storage", "activeTab", "contextMenus"],
  "host_permissions": ["http://localhost:*/*", "https://*/*"]
}
```

**Firefox (MV3 with scripts fallback):**
```json
{
  "manifest_version": 3,
  "background": { "scripts": ["background/service-worker.js"] },
  "action": { "default_popup": "popup/popup.html" },
  "permissions": ["storage", "activeTab", "contextMenus"],
  "host_permissions": ["http://localhost:*/*", "https://*/*"],
  "browser_specific_settings": {
    "gecko": { "id": "sempkm@example.com", "strict_min_version": "109.0" }
  }
}
```

**Key difference:** Chrome requires `service_worker` (single file), Firefox uses `scripts` (array). Both share the same JS — the background/service-worker.js must work in both contexts. This means:
- No DOM/`window` access in background (service worker limitation)
- Use `chrome.storage` (not localStorage) for settings persistence
- All event listeners registered at top level (not in callbacks)
- Use `fetch()` for API calls (not XMLHttpRequest)

**API namespace:** Chrome uses `chrome.*`, Firefox uses `browser.*` (promise-based). Simple polyfill: `const api = typeof browser !== 'undefined' ? browser : chrome;`

### Context Menu Integration

Right-click "Save to SemPKM" on selected text:
1. Service worker registers context menu item via `chrome.contextMenus.create()`
2. On click: captures `selectionText` and `pageUrl` from the event info
3. Opens popup with pre-filled body (selected text) and source URL
4. Default type: Note (configurable in settings)

### Relationship Picker (Object Search)

The extension needs to search existing objects for relationship creation. Two approaches:

**Option A: Use context-query endpoint** — `POST /api/context-query` with title/keywords. Already works with Bearer auth. Returns objects with IRIs, labels, and types. Sufficient for basic search.

**Option B: Use SPARQL endpoint** — More flexible queries, type filtering. But `GET /api/sparql` currently uses cookie-only auth. Requires the auth gap fix.

**Recommendation:** Use Option A (context-query) for v1 relationship search. It's already Bearer-auth-ready and returns the right data shape. If users need more precise search, add SPARQL auth in a follow-up. This reduces the auth-gap fix scope to just the commands endpoint.

**However**: The design doc's reference field uses `hx-get="/browser/search?type={class}"` for type-filtered object search. The extension should have a similar search API. The context-query endpoint doesn't support type filtering. Options:
1. Add a `type_filter` parameter to context-query (small backend addition)
2. Create a dedicated `GET /api/objects/search?q=...&type=...` endpoint
3. Use context-query as-is with client-side type filtering

Option 1 is the lightest touch. Option 3 works for v1 with small result sets.

### Settings & Connection

Extension options page stores:
- `instanceUrl` — SemPKM instance URL (e.g., `http://localhost:3000`)
- `apiKey` — Bearer token string
- `defaultType` — Default capture type IRI
- `autoFillTitle` / `autoFillUrl` / `includeSelection` — Auto-fill preferences

Connection test: `GET /.well-known/sempkm` with Bearer token. Success = JSON response with version. Failure = connection refused or 401.

All settings stored via `chrome.storage.sync` (synced across devices) with fallback to `chrome.storage.local`.

### Build Order

1. **S01: Backend auth gap + extension scaffold** — Create `require_role_or_api`, update commands router. Set up `extension/` directory with manifest, popup shell, background script, options page. Prove end-to-end: extension popup → API call → object created. This is the critical proof-of-concept.

2. **S02: SHACL form renderer + type selector** — Implement `shacl-renderer.js` covering all standard property types. Type selector populated from `/api/types`. Dynamic form rendering on type change. Auto-population from page metadata.

3. **S03: Content scripts + context menu + schema.org** — Page metadata extraction, selected text capture, right-click "Save to SemPKM", schema.org JSON-LD parsing and type mapping.

4. **S04: Relationship picker + edge creation** — Object search via context-query, predicate selection from available properties on the current type, edge.create after object.create.

5. **S05: Settings, polish, cross-browser + E2E tests + docs** — Options page with connection test, keyboard shortcut (Alt+S), Firefox manifest, success/error toasts, loading states. E2E tests (extension integration tests against Docker stack). User guide chapter.

### Verification Approach

**Unit testing:** The SHACL renderer is a pure function (JSON → HTML) testable in Node.js or browser context. API client can be tested with mocked responses.

**Integration testing:** Playwright can load Chrome extensions via `--load-extension` flag. Test flow: install extension → configure localhost → capture Note → verify object created in SemPKM. However, Playwright extension testing has limitations (popup interaction is tricky).

**Manual verification checkpoints:**
1. Extension installs in Chrome, popup opens
2. Options page: configure localhost:3000, API key, test connection shows ✅
3. Click extension icon → type selector shows types from installed models
4. Select "Contact" (CRM) → form shows CRM-specific fields
5. Auto-fill: title and URL from current page
6. Save → success toast → object visible in SemPKM workspace
7. Right-click selected text → "Save to SemPKM" → popup with text pre-filled
8. Schema.org: visit a page with JSON-LD → fields auto-populated
9. Relationship picker: search for existing Concept → create link

**Docker stack verification:** Extension tests run against the same Docker Compose stack used for E2E tests (`docker-compose.test.yml`). The extension connects to `http://localhost:3901` (test stack frontend port).

## Constraints

- **Vanilla JS only** — No React, Vue, or build step. Plain HTML/CSS/JS in the extension. This constrains form rendering to imperative DOM manipulation.
- **Popup viewport ~400px wide** — Forms must be compact. Groups should be collapsible. Multi-value fields need careful layout.
- **Service worker lifecycle** — Chrome MV3 service workers are ephemeral (terminate after ~30s idle). Cannot hold state in global variables. Must use `chrome.storage` for any persistent state.
- **No localhost in host_permissions for Chrome Web Store** — Web Store review may reject `http://localhost:*/*`. For sideloading this is fine; for Store distribution would need to use `<all_urls>` or specific patterns.
- **Content Security Policy** — MV3 extensions cannot use `eval()` or inline scripts. All JS must be in separate files referenced by `<script src="...">`.
- **Commands router auth uses `require_role` which chains to cookie-only auth** — Must fix before extension can create objects. This is the single blocking backend dependency.

## Common Pitfalls

- **`require_role` vs `require_role_or_api`** — The existing `require_role` factory creates a dependency that chains to `get_current_user` (cookie-only). Creating a parallel `require_role_or_api` that chains to `get_current_user_or_api` avoids breaking existing htmx routes while enabling Bearer auth on commands.

- **Service worker death during API calls** — If the extension makes a long-running API call from the service worker and Chrome terminates it, the response is lost. Popup-initiated `fetch()` calls are safe (popup context stays alive while open). Only background context-query calls (Phase 2 badge updates) need resilience patterns.

- **Property IRI resolution in command payload** — The `object.create` handler's `_resolve_predicate()` accepts both compact IRIs (`dcterms:title`) and full IRIs (`http://purl.org/dc/terms/title`). The extension should send compact IRIs from the SHACL shape's `path` field. But shape paths are full IRIs (e.g., `http://purl.org/dc/terms/title`). The handler also accepts full IRIs, so passing the `path` value directly works.

- **Object reference (sh:class) search in popup** — The form's reference field currently uses htmx to call `/browser/search?type=<class>`. The extension can't use htmx. It must implement its own search-as-you-type with `fetch()` calls to `/api/context-query` (or a new search endpoint). The search results must include IRI + label for hidden input + display input pattern.

- **Cross-origin cookie issues** — Extensions making `fetch()` requests to `http://localhost:3000` won't automatically include cookies from the browser's session. This is expected — the extension uses Bearer tokens, not cookies. But if a user tries to use the extension without an API key (relying on their browser session), it won't work. The settings page must make API key configuration mandatory.

- **Firefox `browser_specific_settings.gecko.id`** — Firefox requires a fixed extension ID for persistent storage. Without it, `chrome.storage.local` data is lost on reload. Always include `gecko.id` in the Firefox manifest.

## Open Risks

- **Playwright extension testing limitations** — Playwright can load extensions in Chrome but popup interaction is limited. May need to test via the extension's internal pages (popup.html opened as a tab) rather than through the actual popup trigger. If this proves too fragile, fall back to manual verification for the E2E acceptance.

- **Schema.org JSON-LD variety** — Real-world JSON-LD is messy (arrays of types, nested objects, missing `@context`). The schema.org extractor needs defensive parsing. Scope it to the 3-4 most common types (Person, Article, Organization) and treat everything else as "extract what we can."

- **Multi-value property handling in popup** — The Jinja2 template's `addMultiValue()` clones DOM nodes. The JS equivalent must rebuild form state correctly. Tag fields with autocomplete add extra complexity. Consider deferring tag autocomplete to a polish pass.

- **Edge creation sequencing** — Creating an object and then an edge requires two API calls (since the first call returns the new IRI needed by the second). If the first succeeds but the second fails, the user has an object without the intended relationship. Show a clear error message and let the user retry the edge creation. Not a data corruption risk — just a UX concern.

## Candidate Requirements

The following should be tracked as explicit requirements for M014. They map to the design doc's Phase 1 scope:

| ID | Requirement | Notes |
|---|---|---|
| EXT-01 | Popup capture: type selector, dynamic form, save to SemPKM | Core flow |
| EXT-02 | SHACL-driven forms in popup (string, date, boolean, enum, reference, multi-value, groups) | JS renderer |
| EXT-03 | Auto-population from page metadata (title, URL, selected text, author) | Content script extraction |
| EXT-04 | Relationship picker: search existing objects, create typed edges | Object search + edge.create |
| EXT-05 | Context menu "Save to SemPKM" for selected text | Right-click integration |
| EXT-06 | Schema.org JSON-LD extraction and form auto-fill | Person, Article, Organization mapping |
| EXT-07 | Settings page: instance URL, API key, connection test, default type | Options page |
| EXT-08 | Keyboard shortcut (Alt+S configurable) for capture | Chrome commands API |
| EXT-09 | Success/error feedback after save | Toast notifications in popup |
| EXT-10 | Chrome MV3 and Firefox WebExtension compatibility | Cross-browser manifests |
| EXT-11 | Backend: commands endpoint accepts Bearer token auth | Auth gap fix |
| EXT-12 | User guide documenting extension install, config, and usage | Standing requirement |
| EXT-13 | E2E/integration tests for extension capture flow | Standing requirement |

**EXT-11 is the only backend requirement.** All others are extension-side.

The context mentions "EXT-01 through EXT-06" as relevant requirements. EXT-07 through EXT-13 are additions discovered during research — they're either explicit in the design doc or implied by standing requirements (docs, tests).

## Sources

- `.gsd/design/BROWSER-EXTENSION-DESIGN.md` — Full architecture, Phase 1 flow, SHACL renderer spec
- `backend/app/api/router.py` — M013 API endpoints (types, shapes, context-query, well-known)
- `backend/app/auth/dependencies.py` — Auth dependency chain (`get_current_user` vs `get_current_user_or_api`)
- `backend/app/commands/router.py` — Commands endpoint auth pattern (`require_role`)
- `backend/app/templates/forms/_field.html` — Jinja2 SHACL form macro (reference for JS renderer)
- `backend/app/services/shapes.py` — ShapesService dataclasses (PropertyShape, NodeShapeForm)
- Chrome Manifest V3 migration docs (source: [developer.chrome.com](https://developer.chrome.com/docs/extensions/develop/migrate/to-service-workers))
- Firefox WebExtension background scripts compatibility (source: [MDN](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background))
