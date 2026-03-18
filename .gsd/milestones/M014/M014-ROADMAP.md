# M014: Browser Extension Phase 1 — Smart Structured Capture

**Vision:** Chrome/Firefox browser extension that captures typed, schema-validated objects from any web page — with dynamic SHACL-driven forms, auto-population from page metadata and schema.org JSON-LD, relationship creation, and context menu integration.

## Success Criteria

- User installs the extension in Chrome, configures localhost:3000 and an API key, and sees a green connection indicator
- Clicking the extension icon (or pressing Alt+S) opens a popup with a type selector populated from all installed Mental Models
- Selecting a type renders a dynamic form matching the web app's SHACL forms (string, date, boolean, enum, object reference, multi-value fields, groups, helptext)
- Title, URL, and selected text auto-populate from the current page's metadata
- Schema.org JSON-LD from the page (Person, Article, Organization) auto-fills matching fields
- User can search existing objects and create typed relationships at capture time
- Right-click selected text → "Save to SemPKM" opens the popup with the text pre-filled
- After saving, the object appears in the SemPKM workspace with all properties and relationships intact
- Extension works in both Chrome (MV3) and Firefox (WebExtension)

## Key Risks / Unknowns

- **Backend auth gap** — `POST /api/commands` uses `require_role` which chains to cookie-only `get_current_user`. Bearer tokens are silently rejected with 401. Without fixing this, the extension cannot create objects. This is the single blocking dependency.
- **SHACL form renderer in vanilla JS** — Translating the 205-line Jinja2 `_field.html` macro into imperative DOM manipulation for ~10 property types. Risk is in edge cases (multi-value, enum, object reference) rather than the common path.
- **Chrome MV3 service worker constraints** — No DOM access, no persistent state in globals, ephemeral lifecycle. Must use `chrome.storage` and `fetch()` exclusively. Content Security Policy forbids inline scripts and `eval()`.

## Proof Strategy

- **Backend auth gap** → retire in S01 by proving `POST /api/commands` accepts Bearer token and creates an object (backend unit test + extension popup creating a real Note against running instance)
- **SHACL form renderer** → retire in S02 by rendering all standard property types (string, date, boolean, enum, object reference, multi-value, groups) for the CRM Contact type, which exercises the widest variety of field types
- **MV3 service worker** → retire in S01 by proving the service worker can register context menu items and handle API calls without DOM access

## Verification Classes

- Contract verification: Backend unit tests for `require_role_or_api`, extension JS renderer unit tests (JSON → HTML)
- Integration verification: Extension popup → API call → object created in triplestore, verified via workspace UI
- Operational verification: Extension installs from sideload in Chrome and Firefox, survives browser restart, settings persist
- UAT / human verification: Manual walkthrough of final acceptance scenarios (Note capture, CRM Contact with schema.org, relationship creation)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All five slices complete with individual summaries
- `POST /api/commands` accepts Bearer token auth (backend unit tests pass)
- Extension installs in Chrome and Firefox from unpacked/sideloaded directory
- Popup renders SHACL forms correctly for all standard property types across all installed Mental Models
- Auto-population works for title, URL, selected text, and schema.org JSON-LD
- Relationship picker searches existing objects and creates edges
- Context menu "Save to SemPKM" captures selected text
- Settings page configures instance URL, API key, and default type with connection test
- Captured objects appear in SemPKM workspace with all properties and relationships
- E2E tests exercise the capture flow against Docker stack
- User guide chapter documents extension install, configuration, and usage
- Final integrated acceptance scenarios pass (the 6 scenarios from M014-CONTEXT.md)

## Requirement Coverage

- Covers: EXT-01 (popup capture), EXT-02 (SHACL forms), EXT-03 (auto-population), EXT-04 (relationship picker), EXT-05 (context menu), EXT-06 (schema.org), EXT-07 (settings), EXT-08 (keyboard shortcut), EXT-09 (success/error feedback), EXT-10 (cross-browser), EXT-11 (backend auth), EXT-12 (user guide), EXT-13 (E2E tests)
- Partially covers: none
- Leaves for later: none — all 13 EXT requirements are mapped
- Orphan risks: none — no Active requirements are left unmapped

| Requirement | Primary Owner | Supporting |
|---|---|---|
| EXT-01 (popup capture) | S01 | S02 |
| EXT-02 (SHACL forms) | S02 | — |
| EXT-03 (auto-population) | S03 | — |
| EXT-04 (relationship picker) | S04 | — |
| EXT-05 (context menu) | S03 | — |
| EXT-06 (schema.org) | S03 | — |
| EXT-07 (settings) | S01 | S05 |
| EXT-08 (keyboard shortcut) | S05 | — |
| EXT-09 (success/error feedback) | S01 | S05 |
| EXT-10 (cross-browser) | S05 | — |
| EXT-11 (backend auth) | S01 | — |
| EXT-12 (user guide) | S05 | — |
| EXT-13 (E2E tests) | S05 | — |

## Slices

- [x] **S01: Backend auth fix + extension scaffold with working capture** `risk:high` `depends:[]`
  > After this: User installs the extension in Chrome, configures localhost + API key in the options page, sees a green connection indicator, opens the popup, selects "Note" from a type dropdown, fills in a title, clicks Save, and the object is created in SemPKM (verified by checking the workspace). Service worker registers context menu shell. This proves the full round-trip: extension → Bearer auth → API → triplestore.

- [x] **S02: SHACL form renderer + type selector** `risk:high` `depends:[S01]`
  > After this: Popup type selector shows all types from all installed Mental Models with icons. Selecting a type renders a dynamic SHACL-driven form with grouped fields, helptext, validation indicators, and all standard property types (string, date, boolean, enum, object reference placeholder, multi-value). Selecting "Contact" (CRM) renders CRM-specific fields. Forms are compact and usable in the ~400px popup viewport.

- [ ] **S03: Content scripts + context menu + schema.org** `risk:medium` `depends:[S01]`
  > After this: Opening the popup on any page auto-fills title and URL from page metadata. Selecting text before opening the popup pre-fills the body field. Right-click selected text → "Save to SemPKM" opens the popup with the text pre-filled. Visiting a page with schema.org JSON-LD (e.g., Person, Article) auto-fills matching fields when the corresponding type is selected.

- [ ] **S04: Relationship picker + edge creation** `risk:medium` `depends:[S01,S02]`
  > After this: Object reference fields in the SHACL form show a search-as-you-type input. Typing queries the context-query API and shows matching objects with labels and types. Selecting a result populates the hidden IRI input. After saving, the object is created with edges linking to the selected related objects. Two-step creation: object.create first, then edge.create with the returned IRI.

- [ ] **S05: Cross-browser, keyboard shortcut, E2E tests + user guide** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: Extension works in Firefox via separate manifest. Alt+S keyboard shortcut opens the popup. Success/error toast notifications are polished. E2E tests verify the capture flow against Docker stack. User guide chapter documents installation (sideload), configuration, and usage for both browsers. All 13 EXT requirements validated.

## Boundary Map

### S01 → S02

Produces:
- `extension/` directory structure with Chrome MV3 manifest, popup shell (HTML/CSS/JS), service worker, options page, shared API client module
- `extension/shared/api-client.js` — `SemPKMClient` class with `connect()`, `getTypes()`, `getShape(typeIri)`, `createObject(params)`, `createEdge(params)`, `searchObjects(query)` methods using `fetch()` with Bearer auth
- `extension/shared/storage.js` — Settings persistence via `chrome.storage.sync` (instanceUrl, apiKey, defaultType, preferences)
- `extension/popup/popup.html` — Popup shell with type `<select>`, form container `<div>`, and save button
- `extension/popup/popup.js` — Popup initialization, type selector wiring, save handler calling `api-client.createObject()`
- Backend `require_role_or_api(*roles)` dependency in `backend/app/auth/dependencies.py`
- `POST /api/commands` accepting Bearer token auth

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- `extension/shared/api-client.js` — API client for fetching types and creating objects
- `extension/shared/storage.js` — Settings access for instance URL and API key
- `extension/background/service-worker.js` — Service worker with context menu registration shell
- `extension/popup/popup.js` — Popup with `populateFromPageData(data)` function that accepts extracted metadata

Consumes:
- nothing (first slice)

### S01 → S04

Produces:
- `extension/shared/api-client.js` — `searchObjects(query)` method calling `/api/context-query`
- `extension/shared/api-client.js` — `createEdge(params)` method calling `/api/commands` with `edge.create`

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- `extension/shared/shacl-renderer.js` — SHACL form renderer that produces `<input>` elements with `data-path` attributes, including object reference fields with `data-target-class` attribute marking them for search-as-you-type enhancement
- Form field value extraction via `getFormValues()` that returns `{path: value}` pairs

Consumes:
- S01: API client, popup shell, type selector

### S03 → S05

Produces:
- `extension/content/extractor.js` — Content script that extracts page metadata (title, URL, author, selected text, schema.org JSON-LD)
- Context menu "Save to SemPKM" handler in service worker

Consumes:
- S01: Service worker shell, API client, popup

### S04 → S05

Produces:
- Relationship picker UI integrated into SHACL form reference fields
- Edge creation flow (object.create → get IRI → edge.create)

Consumes:
- S01: API client (searchObjects, createEdge)
- S02: SHACL renderer (reference field markup)
