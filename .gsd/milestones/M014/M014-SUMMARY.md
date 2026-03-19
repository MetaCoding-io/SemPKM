---
id: M014
provides:
  - Chrome MV3 browser extension (extension/ directory) with popup capture UI, options page, service worker
  - Firefox WebExtension via manifest.firefox.json (95% shared codebase)
  - SemPKMClient API client (6 methods) with Bearer auth for external client access
  - SHACL form renderer (shacl-renderer.js — 10 property types, groups, multi-value, validation indicators)
  - Content script page data extractor (title, URL, selection, schema.org JSON-LD)
  - Schema.org → SemPKM type suggestion and property mapping (schema-mapper.js)
  - Reference picker with search-as-you-type via context-query API (reference-picker.js)
  - Two-step save flow (object.create → edge.create) with per-edge error isolation
  - Context menu "Save to SemPKM" with session storage bridge to popup
  - Alt+S keyboard shortcut opening popup in both Chrome and Firefox
  - require_role_or_api(*roles) factory enabling Bearer token auth on POST /api/commands
  - Admin API key management page at /admin/api-keys (create, list, delete)
  - Playwright E2E test suite for extension capture flow (3 tests, persistent context fixture)
  - User guide Chapter 32 (12 sections, 25 headings) + 2 glossary entries
key_decisions:
  - D165: require_role_or_api factory parallels require_role but chains to dual-auth
  - D166: Client-side JS SHACL renderer (no server-rendered partials for extension)
  - D167: context-query endpoint for relationship search (skip SPARQL Bearer auth for Phase 1)
  - D168: Sideload-only distribution for Phase 1 (no Web Store submission)
  - D169: Vanilla JS only — no React/Vue/bundler
  - D170: Two-step sequential object + edge creation (no client-side IRI minting)
  - D189: 4-priority title extraction cascade for varying Mental Model conventions
  - D190: chrome.scripting.executeScript({func}) injection — no persistent content script
  - D191: chrome.storage.session bridge for context menu → popup data flow
  - D192: Cross-namespace schema.org mappings take priority over direct namespace matches
  - D193: Per-edge error isolation — edge failures never block object creation success
patterns_established:
  - "ES module imports throughout extension — no global scripts, no bundler"
  - "SemPKMClient._request() with Bearer auth for all API calls"
  - "el() helper for CSP-compliant imperative DOM creation (zero inline handlers)"
  - "extractTitle() cascade for handling varying title conventions across Mental Models"
  - "Content script → session storage → popup init pattern for context menu pre-fill"
  - "Custom event bridge (sempkm:reference-field-added) for cross-module DOM initialization"
  - "Dual-manifest approach: manifest.json (Chrome) + manifest.firefox.json (Firefox)"
  - "Extension E2E via chromium.launchPersistentContext with --load-extension"
  - "chrome.storage.local injection for reliable cross-page settings in test environments"
observability_surfaces:
  - "[SemPKM] Popup loaded / Loaded N types / Object created: {iri} — popup DevTools console"
  - "[SemPKM] Connection test passed: {version, endpoints} — options DevTools console"
  - "[SemPKM] Shape loaded for {typeIri}: N properties, M groups — popup DevTools console"
  - "[SemPKM] Extracted page data: — popup console with title/url/selectedText/schemaOrg"
  - "[SemPKM] Schema.org type suggestion: — popup console when auto-selecting type"
  - "[SemPKM] Applied N schema.org values to form — popup console after fill"
  - "[SemPKM] Reference picker initialized: N fields / Search / Selected / Edge created — popup console"
  - "[SemPKM] Context menu: stored selection data — service worker console"
  - "get_current_user_or_api logs dual-auth resolution path at DEBUG level"
  - "401 responses carry distinct detail messages for each auth failure mode"
  - "Admin /admin/api-keys page: visible token lifecycle"
requirement_outcomes:
  - id: EXT-01
    from_status: active
    to_status: validated
    proof: "Popup type selector + title/body/URL form + save flow working against real API. E2E test 3 proves full round-trip."
  - id: EXT-02
    from_status: active
    to_status: validated
    proof: "shacl-renderer.js handles all 10 standard property types with groups, multi-value, validation. Node.js rendering tests verified 4 types (Contact, Deal, Note, Task). E2E test 2 proves SHACL form rendering."
  - id: EXT-03
    from_status: active
    to_status: validated
    proof: "Popup auto-fills title, URL, selected text from page metadata via chrome.scripting.executeScript. Settings toggles respected. S03 unit tests (19/19) + S03 integration checks (14/14)."
  - id: EXT-04
    from_status: active
    to_status: validated
    proof: "reference-picker.js provides search-as-you-type with type filtering, selection, clear, two-step save with edge creation. S04 verification checks all pass."
  - id: EXT-05
    from_status: active
    to_status: validated
    proof: "service-worker.js registers context menu item and stores selection in chrome.storage.session. Popup checks session storage on init and consumes data. Handler implementation verified via code inspection."
  - id: EXT-06
    from_status: active
    to_status: validated
    proof: "schema-mapper.js maps Person→Contact, Organization→Company, Article→Note, ScholarlyArticle→Paper. Cross-namespace property mapping. 19/19 unit tests pass."
  - id: EXT-07
    from_status: active
    to_status: validated
    proof: "Options page with connection test (green/red indicator), type selector, API key with visibility toggle, capture behavior checkboxes, settings persistence via chrome.storage.sync. E2E test 1 proves configuration round-trip."
  - id: EXT-08
    from_status: active
    to_status: validated
    proof: "Alt+S keyboard shortcut in both Chrome manifest (commands._execute_action) and Firefox manifest. Uses browser-native _execute_action which opens popup without JS handler."
  - id: EXT-09
    from_status: active
    to_status: validated
    proof: "showToast(message, type) for green success and red error with auto-dismiss. Connection status dot (green/red/amber). Loading spinners during save. E2E test 3 waits for success toast."
  - id: EXT-10
    from_status: active
    to_status: validated
    proof: "manifest.firefox.json with background.scripts array, browser_specific_settings.gecko, same commands block. All extension JS files pass node --check. No ES module imports in service worker (Firefox compat)."
  - id: EXT-11
    from_status: active
    to_status: validated
    proof: "require_role_or_api factory in dependencies.py. POST /api/commands accepts Bearer token. 10 unit tests (test_commands_bearer_auth.py) proving Bearer acceptance, cookie acceptance, role rejection, invalid-Bearer rejection."
  - id: EXT-12
    from_status: active
    to_status: validated
    proof: "docs/guide/32-browser-extension.md — 12 sections, 25 headings covering installation, configuration, capture workflow, auto-population, schema.org, context menu, relationship picker, keyboard shortcut, troubleshooting. README TOC updated, 2 glossary entries."
  - id: EXT-13
    from_status: active
    to_status: validated
    proof: "e2e/tests/25-extension/extension-capture.spec.ts — 3 serial tests: options config + connection test, popup type loading + SHACL form rendering, Note capture + SPARQL-verified persistence. Custom persistent context fixture in e2e/fixtures/extension.ts."
duration: ~5h
verification_result: passed
completed_at: 2026-03-18
---

# M014: Browser Extension Phase 1 — Smart Structured Capture

**Chrome/Firefox browser extension delivering typed, schema-validated object capture from any web page — with dynamic SHACL-driven forms, auto-population from page metadata and schema.org JSON-LD, relationship creation via search-as-you-type picker, context menu integration, and Alt+S keyboard shortcut.**

## What Happened

Five slices built the extension from the ground up, each retiring a key risk and producing a demoable increment.

**S01 (Backend auth + scaffold)** fixed the blocking dependency: `POST /api/commands` only accepted session cookies, not Bearer tokens. Added `require_role_or_api(*roles)` factory in `dependencies.py` that chains to `get_current_user_or_api` (dual-auth) — 10 unit tests proving all auth paths. Built the complete `extension/` directory with Chrome MV3 manifest, `SemPKMClient` class (6 API methods with Bearer auth), storage wrapper, service worker with context menu registration, options page with connection test, and popup capture UI with type selector grouped by model. Added admin API key management page at `/admin/api-keys`.

**S02 (SHACL form renderer)** retired the second key risk: translating the 205-line Jinja2 `_field.html` macro into imperative JS DOM manipulation. Built `shacl-renderer.js` (588 lines) handling all 10 standard property types — enum, object reference, date, dateTime, boolean, integer, decimal, anyURI, tags, and default text — with groups as collapsible `<details>`, multi-value add/remove, skip paths, required markers, and helptext. Wired into popup via `handleTypeChange()` orchestrator. Patched backend `object_create.py` to iterate list values for multi-value fields. All rendering is CSP-compliant (zero inline handlers).

**S03 (Content scripts + context menu + schema.org)** built page data extraction and auto-population. Created `extractor.js` as a fully self-contained function (serializable by `chrome.scripting.executeScript({func})`) extracting title, URL, selected text, author, and schema.org JSON-LD from any page. Created `schema-mapper.js` mapping schema.org types to SemPKM types (Person→Contact, Article→Note) with cross-namespace property mapping. Wired the context menu handler: stores selection in `chrome.storage.session`, opens popup, popup checks session on init and consumes data.

**S04 (Relationship picker)** built `reference-picker.js` enhancing object reference fields with debounced search (300ms), type filtering via `data-target-class`, dropdown with label + type badge, selection management, and outside-click dismissal. Wired two-step save in popup: `createObject()` first, then `createEdge()` for each selected reference, with per-edge error isolation (failures warn but never block object success). Custom event bridge (`sempkm:reference-field-added`) handles multi-value reference field initialization.

**S05 (Cross-browser + E2E + docs)** polished the final deliverables. Created `manifest.firefox.json` with `background.scripts` array format and `browser_specific_settings.gecko`. Added Alt+S keyboard shortcut in both manifests via `_execute_action` command. Removed dead ES module import from service worker for Firefox compatibility. Built Playwright E2E test suite (3 tests) with custom persistent context fixture proving the full capture round-trip: API key creation, options configuration, popup type loading with SHACL form rendering, object save, and SPARQL-verified persistence. Wrote user guide Chapter 32 (12 sections covering installation, configuration, and all features) with glossary entries and navigation chain.

## Cross-Slice Verification

Each success criterion from the roadmap, verified:

| Criterion | Evidence |
|-----------|----------|
| User installs extension, configures localhost + API key, sees green connection indicator | E2E test 1: configures options, waits for green status banner, saves, reloads, verifies persistence |
| Extension icon opens popup with type selector from all installed Mental Models | E2E test 2: popup loads, type selector populates from API, types grouped by model |
| Selecting a type renders dynamic SHACL form (string, date, boolean, enum, object ref, multi-value, groups, helptext) | E2E test 2: selects type, waits for `[data-path]` inputs; S02 Node.js test verified all 4 types (Contact 12 fields/6 groups, Deal, Note, Task 18 fields/4 groups) |
| Title, URL, selected text auto-populate from page metadata | S03: 14/14 integration checks, extractor.js tested via node --check + unit tests |
| Schema.org JSON-LD auto-fills matching fields | S03: 19/19 mapper unit tests (normalizeSchemaType 6 cases, suggestType 5 cases, mapSchemaOrgToFormValues 8 cases) |
| Relationship picker searches existing objects and creates typed edges | S04: reference-picker.js verified (3 exports, picker init, search, select flow); POST /api/context-query returns results against Docker stack |
| Right-click "Save to SemPKM" opens popup with text pre-filled | service-worker.js has contextMenus.create + onClicked.addListener + chrome.storage.session.set; popup.js checks session storage on init |
| Settings page configures URL, API key, default type with connection test | Options page verified in S01 with connection test (green ✅ / red ❌), type selector population, settings persistence |
| Captured objects appear in SemPKM workspace | E2E test 3: creates Note via popup save, verifies via SPARQL API query |
| E2E tests exercise capture flow against Docker stack | 3 tests in extension-capture.spec.ts, all passing consistently (4 consecutive runs) |
| User guide documents extension | Chapter 32 (25 headings, 12 sections), README TOC updated, 2 glossary entries |
| POST /api/commands accepts Bearer token auth | 10 unit tests in test_commands_bearer_auth.py, all passing |
| Extension installs in Chrome and Firefox | Chrome: E2E proven via Playwright persistent context; Firefox: manifest.firefox.json structurally valid (JSON parse + correct format) |
| Alt+S keyboard shortcut opens popup | Both manifests have `commands._execute_action` with `suggested_key.default: "Alt+S"` |

All 9 extension JS files pass `node --check` syntax validation. Zero inline event handlers across the entire extension (CSP-compliant).

## Requirement Changes

- EXT-01 (popup capture): active → validated — Popup type selector + save flow proven via E2E test 3
- EXT-02 (SHACL forms): active → validated — 10 property types rendered, Node.js rendering tests for 4 types, E2E test 2
- EXT-03 (auto-population): active → validated — Title/URL/selection auto-fill from page metadata, S03 unit tests 19/19
- EXT-04 (relationship picker): active → validated — Search-as-you-type with type filtering, two-step save, S04 verification
- EXT-05 (context menu): active → validated — Context menu registered and handled in service worker, session storage bridge
- EXT-06 (schema.org): active → validated — JSON-LD parsing, type suggestion, cross-namespace property mapping, 19/19 unit tests
- EXT-07 (settings): active → validated — Options page with connection test, type selector, capture behavior, E2E test 1
- EXT-08 (keyboard shortcut): active → validated — Alt+S in both Chrome and Firefox manifests via _execute_action
- EXT-09 (success/error feedback): active → validated — Toast notifications, connection dot, loading spinners, E2E test 3
- EXT-10 (cross-browser): active → validated — manifest.firefox.json with gecko settings, classic service worker (no ES modules)
- EXT-11 (backend auth): active → validated — require_role_or_api factory, 10 unit tests in test_commands_bearer_auth.py
- EXT-12 (user guide): active → validated — Chapter 32 (12 sections), README TOC, 2 glossary entries
- EXT-13 (E2E tests): active → validated — 3 Playwright tests with custom persistent context fixture

## Forward Intelligence

### What the next milestone should know
- The extension is vanilla JS with no build step — all ES module imports use relative paths. Adding a bundler would change the import pattern across every file.
- `SemPKMClient` in `api-client.js` is the canonical API client for the extension. It has 6 methods: `connect`, `getTypes`, `getShape`, `createObject`, `createEdge`, `searchObjects`. Phase 2 (context overlay) should extend this class rather than creating a new one.
- The SHACL renderer (`shacl-renderer.js`) handles the common property types but does NOT support regex patterns, complex cardinality, nested shapes, or conditional constraints. Mental Models that use exotic SHACL features will render with fallback text inputs.
- Schema.org type mapping covers Person, Organization, Article, NewsArticle, BlogPosting, ScholarlyArticle. Other types (Event, Product, Recipe) fall through silently — the user must manually select a type.
- Cross-namespace property mapping is hardcoded for CRM model paths. Other models with different namespaces only get direct schema.org namespace matches.
- The extension E2E tests are Chromium-only — Firefox doesn't support `--load-extension` in Playwright persistent context.

### What's fragile
- `extractTitle()` cascade relies on string matching ("title" in path, "name" in path) — new Mental Models with unconventional title fields may fall through to the "first required field" heuristic.
- The content script extractor function must remain fully self-contained (var declarations, no closures, no imports) for `chrome.scripting.executeScript({func})` serialization. Any use of let/const/arrow functions/for...of could break in strict mode contexts.
- `chrome.action.openPopup()` in the context menu handler may not be available in all Chrome versions — the fallback creates a new window (different UX).
- The popup assumes 380px viewport width. Deeply nested multi-value reference fields with long labels may overflow horizontally.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py -v` — 10 tests proving Bearer auth paths
- `cd e2e && npx playwright test --project=extension` — 3 tests proving capture round-trip (requires Docker test stack on port 3901)
- `node --check extension/**/*.js` — syntax validation for all extension JS
- Filter Chrome DevTools console for `[SemPKM]` — all extension lifecycle events are logged

### What assumptions changed
- S02 assumed `object_create` handler already supported list values — it didn't, requiring a backend patch.
- S02 assumed all types have `dcterms:title` — CRM Contact doesn't, requiring the extractTitle cascade.
- S05/T02 discovered `chrome.storage.sync` is unreliable in Playwright persistent context — used `chrome.storage.local` injection instead.
- S05/T02 discovered persistent context hangs when navigating non-extension pages — substituted SPARQL API verification.
- S05/T03 noted context menu as a declared capability only, but the handler IS implemented in service-worker.js (T03 docs note was inaccurate).

## Files Created/Modified

### Extension (new directory)
- `extension/manifest.json` — Chrome MV3 manifest with permissions, host_permissions, action, background, icons, commands
- `extension/manifest.firefox.json` — Firefox WebExtension manifest with background.scripts, gecko settings
- `extension/shared/api-client.js` — SemPKMClient class (6 API methods + SemPKMError)
- `extension/shared/storage.js` — Settings persistence (getSettings, saveSettings, getClient)
- `extension/shared/shacl-renderer.js` — SHACL form renderer (renderForm, renderField, getFormValues — 588 lines)
- `extension/shared/schema-mapper.js` — Schema.org → SemPKM type/property mapper (167 lines)
- `extension/shared/reference-picker.js` — Search-as-you-type reference picker (~190 lines)
- `extension/background/service-worker.js` — Context menu registration + handler
- `extension/content/extractor.js` — Self-contained page data extraction function
- `extension/popup/popup.html` — Popup UI (type selector, dynamic form container, toast)
- `extension/popup/popup.js` — Popup logic (type loading, SHACL rendering, save flow, auto-fill)
- `extension/popup/popup.css` — Popup styling for 380px viewport (groups, multi-value, reference picker)
- `extension/options/options.html` — Options page (connection form, type selector, capture defaults)
- `extension/options/options.js` — Options logic (load/save settings, connection test, type population)
- `extension/options/options.css` — Options styling (520px centered layout, indigo accent)
- `extension/assets/icon-{16,32,48,128}.png` — Placeholder extension icons

### Backend
- `backend/app/auth/dependencies.py` — Added require_role_or_api(*roles) factory
- `backend/app/commands/router.py` — Switched to require_role_or_api("owner", "member")
- `backend/app/commands/handlers/object_create.py` — Patched list-value iteration for multi-value properties
- `backend/tests/test_commands_bearer_auth.py` — 10 Bearer auth tests
- `backend/app/admin/router.py` — Added 3 API key management routes
- `backend/app/templates/admin/api_tokens.html` — Token management page
- `backend/app/templates/admin/index.html` — Added API Keys card
- `backend/app/templates/components/_sidebar.html` — Added API Keys nav link

### E2E Tests
- `e2e/fixtures/extension.ts` — Persistent context fixture for extension testing
- `e2e/tests/25-extension/extension-capture.spec.ts` — 3 E2E tests for capture flow
- `e2e/playwright.config.ts` — Added extension project entry

### Documentation
- `docs/guide/32-browser-extension.md` — Chapter 32 (12 sections, 25 headings)
- `docs/guide/README.md` — Updated TOC with Chapter 32
- `docs/guide/appendix-d-glossary.md` — Added "API Token" and "Browser Extension" entries
- `docs/guide/31-api-surface.md` — Updated navigation chain to Chapter 32
