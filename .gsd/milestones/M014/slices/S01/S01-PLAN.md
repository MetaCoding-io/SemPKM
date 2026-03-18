# S01: Backend auth fix + extension scaffold with working capture

**Goal:** Fix the commands endpoint to accept Bearer token auth, then build the Chrome extension scaffold with options page, popup capture, and service worker — proving the full round-trip: extension → Bearer auth → API → triplestore.

**Demo:** User installs the extension in Chrome, configures localhost + API key in the options page, sees a green connection indicator, opens the popup, selects "Note" from a type dropdown, fills in a title, clicks Save, and the object is created in SemPKM (verified by checking the workspace). Service worker registers context menu shell.

## Must-Haves

- `require_role_or_api(*roles)` factory in `backend/app/auth/dependencies.py` that chains to `get_current_user_or_api`
- `POST /api/commands` accepts Bearer token auth (switched from `require_role` to `require_role_or_api`)
- Existing htmx routes using `require_role` unchanged
- `extension/` directory with Chrome MV3 manifest, popup, options page, service worker, shared modules
- `extension/shared/api-client.js` — `SemPKMClient` class with `connect()`, `getTypes()`, `getShape(typeIri)`, `createObject(params)`, `createEdge(params)`, `searchObjects(query)` methods
- `extension/shared/storage.js` — Settings persistence via `chrome.storage.sync`
- Options page: instance URL, API key, connection test with green/red indicator
- Popup: type selector populated from `/api/types`, title field, save button calling `object.create`
- Success/error toast notifications in popup after save
- Service worker registers "Save to SemPKM" context menu item (shell — handler wired in S03)

## Proof Level

- This slice proves: integration (extension → backend → triplestore round-trip)
- Real runtime required: yes (Docker stack + Chrome with sideloaded extension)
- Human/UAT required: yes (manual sideload and capture test)

## Verification

- `cd backend && python -m pytest tests/test_commands_bearer_auth.py -v` — Backend unit tests for `require_role_or_api` factory and commands endpoint Bearer auth acceptance
- Manual: load `extension/` as unpacked extension in Chrome → options page → configure `http://localhost:3000` + API key → green checkmark → popup → select Note → enter title → Save → success toast → verify object in SemPKM workspace
- `cd backend && python -m pytest tests/test_api_surface.py -v` — Existing dual-auth tests still pass (no regression)
- Diagnostic: `POST /api/commands` with invalid/missing Bearer token returns structured JSON error `{"detail": "Invalid or expired API token"}` (401) or `{"detail": "Not authenticated"}` (401) — verify distinct error messages for each failure path in test output

## Observability / Diagnostics

- Runtime signals: `logger.debug("dual-auth resolved via Bearer token")` in `get_current_user_or_api` (already exists), `logger.debug("command executed via require_role_or_api")` in new factory
- Inspection surfaces: Chrome extension service worker console (`chrome://extensions` → Inspect), popup DevTools, options page DevTools
- Failure visibility: API errors surface as JSON `{"error": "..."}` in popup toast notifications; 401 responses include distinct detail messages (`"Not authenticated"` vs `"Invalid or expired API token"`)
- Redaction constraints: API key stored in `chrome.storage.sync`, never logged or displayed in full

## Integration Closure

- Upstream surfaces consumed: M013 API endpoints (`/.well-known/sempkm`, `/api/types`, `/api/shapes/{type}`, `/api/commands`) — all already shipped and tested
- New wiring introduced: `require_role_or_api` factory in `dependencies.py`, `commands/router.py` switched to use it, entire `extension/` directory tree
- What remains before the milestone is truly usable end-to-end: S02 (SHACL form renderer for all property types), S03 (content scripts + context menu handler + schema.org), S04 (relationship picker), S05 (Firefox, keyboard shortcut, E2E tests, user guide)

## Tasks

- [x] **T01: Create `require_role_or_api` factory and wire commands endpoint to dual-auth** `est:30m`
  - Why: The commands endpoint (`POST /api/commands`) uses `require_role("owner", "member")` which chains to cookie-only `get_current_user`. Bearer tokens are silently rejected with 401. This is the single blocking dependency for the extension — without it, no object creation is possible from the extension.
  - Files: `backend/app/auth/dependencies.py`, `backend/app/commands/router.py`, `backend/tests/test_commands_bearer_auth.py`
  - Do: Create `require_role_or_api(*roles)` factory that mirrors `require_role` but chains to `get_current_user_or_api` instead of `get_current_user`. Update `commands/router.py` to import and use `require_role_or_api("owner", "member")` instead of `require_role("owner", "member")`. Write unit tests proving Bearer token creates objects and cookie auth still works. Leave all other `require_role` usages unchanged.
  - Verify: `cd backend && python -m pytest tests/test_commands_bearer_auth.py -v` passes; `python -m pytest tests/test_api_surface.py -v` passes (no regression)
  - Done when: `POST /api/commands` with `Authorization: Bearer <valid-token>` returns 200 with created object IRI; same request with invalid token returns 401; existing cookie-based commands still work

- [x] **T02: Extension directory scaffold with manifest, shared modules, and service worker** `est:1h`
  - Why: Establishes the directory structure, Chrome MV3 manifest, API client, storage wrapper, and service worker that all subsequent slices (S02-S05) depend on. The shared modules (`api-client.js`, `storage.js`) are boundary contracts consumed by popup, options, content scripts, and service worker.
  - Files: `extension/manifest.json`, `extension/shared/api-client.js`, `extension/shared/storage.js`, `extension/background/service-worker.js`, `extension/assets/icon-16.png`, `extension/assets/icon-32.png`, `extension/assets/icon-48.png`, `extension/assets/icon-128.png`
  - Do: Create Chrome MV3 manifest with permissions (storage, activeTab, contextMenus), host_permissions (localhost, https), popup action, service worker background, options page. Implement `SemPKMClient` class in api-client.js with methods: `connect()` (GET /.well-known/sempkm), `getTypes()` (GET /api/types), `getShape(typeIri)` (GET /api/shapes/{typeIri}), `createObject(params)` (POST /api/commands with object.create), `createEdge(params)` (POST /api/commands with edge.create), `searchObjects(query)` (POST /api/context-query). Implement storage.js with `getSettings()`, `saveSettings()`, `getClient()` using chrome.storage.sync. Create service-worker.js that registers "Save to SemPKM" context menu item on install. Generate simple extension icons (colored squares with "S" letter).
  - Verify: `chrome://extensions` → Load unpacked → extension loads without errors; service worker active in extension details; context menu item appears on right-click
  - Done when: Extension loads in Chrome without manifest errors, service worker is registered, right-click shows "Save to SemPKM" menu item (clicking it does nothing yet — handler wired in S03)

- [x] **T03: Options page with connection test and settings persistence** `est:45m`
  - Why: The user needs to configure the SemPKM instance URL and API key before the popup can make authenticated API calls. The connection test (green/red indicator) is the first visible proof the extension talks to the backend. This task delivers EXT-07 (settings) for this slice.
  - Files: `extension/options/options.html`, `extension/options/options.js`, `extension/options/options.css`
  - Do: Build options page with form fields: Instance URL (text input, default "http://localhost:3000"), API Key (password input), Default Type (select, populated after successful connection test). "Test Connection" button calls `SemPKMClient.connect()` — success shows green checkmark + version string, failure shows red X + error message. Save button persists settings via storage.js. Auto-load saved settings on page open. Style with clean, simple CSS matching SemPKM's design language.
  - Verify: Open options page → enter localhost:3000 + valid API key → click Test Connection → green indicator with version → Save → reload page → settings persisted
  - Done when: Options page saves/loads settings, connection test shows green for valid instance + API key and red for invalid

- [x] **T04: Popup capture flow with type selector, save, and success/error feedback** `est:1h`
  - Why: This is the core capture UI — the popup where users select a type, fill in a title, and save an object. Combined with T01 (auth fix) and T02/T03 (extension infrastructure), this completes the full round-trip demo proving extension → Bearer auth → API → triplestore. Delivers EXT-01 (popup capture) and EXT-09 (success/error feedback) for this slice.
  - Files: `extension/popup/popup.html`, `extension/popup/popup.js`, `extension/popup/popup.css`
  - Do: Build popup (400px wide) with: connection status indicator (green/red dot in header), type selector `<select>` populated from `SemPKMClient.getTypes()`, title `<input>` field, body `<textarea>` (for selected text — pre-fill wired in S03), Save button. On Save: construct `object.create` command with type IRI + properties (dcterms:title, sempkm:body if provided), call `createObject()`, show success toast (green, "Object created!" with link text) or error toast (red, error message). Handle loading states (spinner on save button). Handle unconfigured state (show "Configure in Settings" message if no instanceUrl/apiKey). Export `populateFromPageData(data)` function for S03 content script integration.
  - Verify: Open popup → type selector shows Note, Concept, etc. → enter title "Test from extension" → click Save → success toast → open SemPKM workspace → object "Test from extension" visible in nav tree
  - Done when: Full round-trip works: popup → type select → title → Save → object created in SemPKM and visible in workspace; error cases show appropriate toast messages

- [ ] **T05: Admin API key management page** `est:1h`
  - Why: Users have no way to generate API keys through the UI — the auth router has `POST /auth/tokens` and `GET /auth/tokens` and `DELETE /auth/tokens/{id}` endpoints but no admin page exposes them. Without this, users can't configure the extension without shell access to the database.
  - Files: `backend/app/templates/admin/api_tokens.html`, `backend/app/admin/router.py`, `frontend/static/css/style.css` (minor)
  - Do: Add an "API Keys" page to the admin section. List existing tokens (name, created date — no plaintext shown). "Create Token" form (name input + create button) that calls `POST /auth/tokens` and displays the plaintext token exactly once with a copy button and warning that it won't be shown again. Delete button per token. Link from admin nav. Use the existing admin template patterns (card layout, table).
  - Verify: Navigate to admin → API Keys → create token → plaintext shown once → copy it → use in extension options page → green checkmark → delete token → extension returns 401
  - Done when: Users can create, list, and delete API keys entirely through the admin UI without shell access

## Files Likely Touched

- `backend/app/auth/dependencies.py`
- `backend/app/commands/router.py`
- `backend/tests/test_commands_bearer_auth.py`
- `extension/manifest.json`
- `extension/shared/api-client.js`
- `extension/shared/storage.js`
- `extension/background/service-worker.js`
- `extension/options/options.html`
- `extension/options/options.js`
- `extension/options/options.css`
- `extension/popup/popup.html`
- `extension/popup/popup.js`
- `extension/popup/popup.css`
- `extension/assets/icon-16.png`
- `extension/assets/icon-32.png`
- `extension/assets/icon-48.png`
- `extension/assets/icon-128.png`
