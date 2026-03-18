---
id: S01
parent: M014
milestone: M014
provides:
  - require_role_or_api(*roles) factory in backend/app/auth/dependencies.py enabling Bearer token auth on POST /api/commands
  - Complete extension/ directory with Chrome MV3 manifest, popup, options page, service worker, shared modules
  - SemPKMClient class (6 API methods with Bearer auth) in extension/shared/api-client.js
  - Storage wrapper (getSettings, saveSettings, getClient) in extension/shared/storage.js
  - Service worker with "Save to SemPKM" context menu registration (shell — handler wired in S03)
  - Options page with connection test (green/red indicator), type selector population, settings persistence
  - Popup capture UI with type selector (grouped by model), title/body/URL form, save flow, toast feedback
  - populateFromPageData() export for S03 content script integration
  - Admin API key management page at /admin/api-keys (create, list, delete with one-time plaintext display)
requires:
  - slice: M013/S01
    provides: get_current_user_or_api dual-auth dependency, CORS headers, nginx Authorization forwarding
  - slice: M013/S02
    provides: GET /api/types and GET /api/shapes/{type_iri} endpoints
  - slice: M013/S03
    provides: POST /api/context-query endpoint
affects:
  - S02 (consumes api-client.js, storage.js, popup shell, type selector)
  - S03 (consumes api-client.js, storage.js, service worker, populateFromPageData)
  - S04 (consumes api-client.js searchObjects/createEdge methods)
  - S05 (consumes all extension infrastructure)
key_files:
  - backend/app/auth/dependencies.py
  - backend/app/commands/router.py
  - backend/tests/test_commands_bearer_auth.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/api_tokens.html
  - extension/manifest.json
  - extension/shared/api-client.js
  - extension/shared/storage.js
  - extension/background/service-worker.js
  - extension/options/options.html
  - extension/options/options.js
  - extension/options/options.css
  - extension/popup/popup.html
  - extension/popup/popup.js
  - extension/popup/popup.css
key_decisions:
  - D165: require_role_or_api factory parallels require_role but chains to dual-auth — htmx routes untouched
  - ES modules throughout extension — manifest type:module, popup/options use script type=module, no bundler
  - SemPKMClient._request() attaches Bearer auth uniformly; SemPKMError carries HTTP status + detail
  - storage.js getClient() returns null when unconfigured rather than constructing a broken client
  - Admin API keys use request.app.state.auth_service (not Depends(get_db_session)) since AuthService requires async_sessionmaker
patterns_established:
  - "Use require_role_or_api for API endpoints needing Bearer token support; keep require_role for cookie-only htmx routes"
  - "All extension API calls go through SemPKMClient._request() with Bearer auth and uniform error handling"
  - "Use ES module import/export for all extension JS — no global scripts, no bundler needed"
  - "showToast(message, type) for all popup user feedback — green success, red error, auto-dismiss"
  - "setConnectionDot(state, tooltip) for connection health — green/red/amber states"
  - "Admin pages follow webhooks.html template pattern — card layout, htmx POST, sparql-results table, hx-confirm delete"
observability_surfaces:
  - "get_current_user_or_api logs 'dual-auth resolved via Bearer token' / 'session cookie' at DEBUG level"
  - "401 responses carry distinct detail messages: 'Not authenticated' / 'Invalid or expired API token' / 'Invalid or expired session'"
  - "Extension popup DevTools: [SemPKM] Popup loaded, [SemPKM] Loaded N types, [SemPKM] Object created: {iri}"
  - "Extension options DevTools: [SemPKM] Connection test passed: {version, endpoints}"
  - "Service worker console: [SemPKM] Context menu 'Save to SemPKM' registered"
  - "Admin /admin/api-keys page: full token lifecycle visible"
drill_down_paths:
  - .gsd/milestones/M014/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T04-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T05-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-18
---

# S01: Backend auth fix + extension scaffold with working capture

**Fixed `POST /api/commands` to accept Bearer token auth, built the Chrome MV3 extension with options page, popup capture, and admin API key management — proving the full round-trip: extension → Bearer auth → API → triplestore.**

## What Happened

**T01 (Backend auth fix):** Added `require_role_or_api(*roles)` factory in `dependencies.py` that mirrors `require_role` but chains to `get_current_user_or_api` (dual-auth) instead of `get_current_user` (cookie-only). Switched `POST /api/commands` to use it. Wrote 10 unit tests covering Bearer acceptance, cookie acceptance, wrong role (403), no credentials (401), and invalid Bearer (401). All existing `require_role` usages unchanged — zero regression risk.

**T02 (Extension scaffold):** Created the complete `extension/` directory with Chrome MV3 manifest (`"type": "module"` for ES module service worker), `SemPKMClient` class in `shared/api-client.js` with 6 API methods (`connect`, `getTypes`, `getShape`, `createObject`, `createEdge`, `searchObjects`) using `fetch()` with `Authorization: Bearer` header through a shared `_request()` method. Storage wrapper in `shared/storage.js` with `getSettings`/`saveSettings`/`getClient`. Service worker registers "Save to SemPKM" context menu item on install. Generated indigo placeholder icons (16/32/48/128px).

**T03 (Options page):** Built options page with Instance URL and API Key fields (with password visibility toggle), Test Connection button that calls `SemPKMClient.connect()` then `getTypes()`, green ✅/red ❌ status banner with error differentiation (401 → "Invalid API key", TypeError → "Cannot reach instance"), Default Type selector populated from `/api/types`, three capture behavior checkboxes, and Save button persisting to `chrome.storage.sync`. Auto-tests connection on load when settings are already saved.

**T04 (Popup capture):** Popup (380px) with connection status dot, type selector grouped by model via `<optgroup>`, title/body/URL form fields, and save flow calling `client.createObject()`. Save builds properties (`dcterms:title`, optional `sempkm:body`, optional `schema:url`) and shows green success toast or red error toast. Handles unconfigured state ("Open Settings" prompt), loading states (spinner), double-submit prevention, and title validation. Exports `populateFromPageData(data)` for S03 content script integration.

**T05 (Admin API keys page):** Added `/admin/api-keys` with three routes (GET list, POST create, DELETE revoke) using `request.app.state.auth_service`. Template shows create form, one-time plaintext token display with Copy button and "shown once" warning, token list table, and confirmation-guarded delete. Added sidebar nav link and admin index card.

## Verification

- `backend/tests/test_commands_bearer_auth.py` — 10/10 passed (Bearer acceptance, cookie acceptance, role rejection, no-auth rejection, invalid-Bearer rejection, commands endpoint integration)
- `backend/tests/test_api_surface.py` — 62/62 passed (no regression in existing dual-auth, types, shapes, context-query endpoints)
- All 5 extension JS files pass `node --check` syntax validation
- Extension manifest validates as Chrome MV3 (all referenced files exist on disk)
- All 4 icon sizes verified as valid PNG at correct dimensions
- Full API round-trip verified against running Docker stack: `POST /api/commands` with Bearer token returns 200 + IRI; invalid token returns 401; no auth returns 401
- Options page connection test verified: valid credentials → green + version string; invalid key → red "Invalid API key"; unreachable → red "Cannot reach instance"
- Admin API keys page verified: create → plaintext shown → copy → use in extension → green checkmark → delete → extension gets 401

## Requirements Advanced

- EXT-01 (popup capture) — Popup type selector + title + save flow working against real API
- EXT-07 (settings) — Options page with connection test, type selector, settings persistence
- EXT-09 (success/error feedback) — Toast notifications in popup (green success, red error with detail)
- EXT-11 (backend auth) — `require_role_or_api` factory, `POST /api/commands` accepts Bearer tokens

## Requirements Validated

- EXT-11 — `POST /api/commands` accepts Bearer token (10 unit tests proving all auth paths); existing cookie auth unchanged (62 regression tests pass)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T03: Added API key visibility toggle (eye icon), capture behavior checkboxes (auto-fill title/URL, include selection), and Enter key shortcut — minor UX additions not in original plan
- T04: Popup was fully implemented during T02 scaffold work. T04 became a verification task rather than implementation
- T05: Used `request.app.state.auth_service` instead of `Depends(get_db_session)` — AuthService requires `async_sessionmaker`, not `AsyncSession`. Matches auth router's own `_get_auth_service(request)` pattern

## Known Limitations

- Extension sideload verification is manual (Chrome DevTools) — no automated Chrome extension E2E yet (planned for S05)
- CORS double-header issue when testing via static server against nginx-proxied backend (both nginx and FastAPI add `Access-Control-Allow-Origin: *`). Does not affect the real extension — Chrome extensions bypass CORS via `host_permissions`
- `pytest` not available inside Docker container (not volume-mounted) — tests run from host filesystem only
- Context menu "Save to SemPKM" registers but has no handler yet (shell — wired in S03)

## Follow-ups

- S02 will consume `api-client.js` (`getTypes`, `getShape`) and the popup type selector to build the SHACL form renderer
- S03 will wire the context menu click handler in service-worker.js and implement `populateFromPageData()` content script messaging
- S05 needs to add E2E tests for the full extension flow and Firefox manifest compatibility

## Files Created/Modified

- `backend/app/auth/dependencies.py` — Added `require_role_or_api(*roles)` factory function (~20 lines)
- `backend/app/commands/router.py` — Changed import and dependency to `require_role_or_api("owner", "member")`
- `backend/tests/test_commands_bearer_auth.py` — 10 tests covering factory unit tests and commands endpoint integration
- `backend/app/admin/router.py` — Added 3 API key management routes (GET, POST, DELETE) + helper
- `backend/app/templates/admin/api_tokens.html` — Token management page with create/list/delete UI
- `backend/app/templates/admin/index.html` — Added API Keys card to admin dashboard
- `backend/app/templates/components/_sidebar.html` — Added API Keys nav link with key-round icon
- `extension/manifest.json` — Chrome MV3 manifest with permissions, host_permissions, action, background, icons, options
- `extension/shared/api-client.js` — SemPKMClient class with 6 API methods + SemPKMError class
- `extension/shared/storage.js` — Settings persistence wrapper (getSettings, saveSettings, getClient)
- `extension/background/service-worker.js` — Context menu registration + click listener shell
- `extension/assets/icon-{16,32,48,128}.png` — Placeholder extension icons
- `extension/options/options.html` — Options page with connection form, type selector, capture defaults
- `extension/options/options.js` — Options logic: load/save settings, test connection, populate types
- `extension/options/options.css` — Options styling: centered 520px layout, indigo accent, animated status
- `extension/popup/popup.html` — Popup UI with header, unconfigured state, capture form, toast container
- `extension/popup/popup.js` — Popup logic: type population, save flow, toast system, loading states
- `extension/popup/popup.css` — Popup styling for 380px viewport

## Forward Intelligence

### What the next slice should know
- `api-client.js` exports `SemPKMClient` and `SemPKMError` as ES modules. Import via relative path: `import { SemPKMClient, SemPKMError } from '../shared/api-client.js'`
- `storage.js` exports `getSettings()`, `saveSettings(settings)`, and `getClient()`. `getClient()` returns null when unconfigured — always null-check before use
- The popup already has `populateFromPageData({title, url, selectedText, author})` exported — S03 just needs to send a message from the content script
- The service worker's context menu click handler is a TODO comment at line ~20 — S03 fills it in
- Type selector uses `<optgroup>` elements grouped by `model_name` from `/api/types` response

### What's fragile
- The popup implementation assumed all types have `model_name` for optgroup grouping — types without `model_name` go into an "Other" group. If a model returns null `model_name`, the optgroup label will be "Other"
- CORS double-header (nginx + FastAPI CORSMiddleware both adding `Access-Control-Allow-Origin: *`) — doesn't affect extension but blocks web-based testing

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py -v` — 10 tests proving all Bearer auth paths
- `node --check extension/**/*.js` — syntax validation for all extension JS
- Extension popup DevTools console filtered for `[SemPKM]` — shows lifecycle events
- Admin `/admin/api-keys` — visible token CRUD with one-time plaintext display

### What assumptions changed
- T04 assumed popup implementation was a separate task — it was already done in T02's scaffold. T04 became verification-only
- T05 assumed `AuthService(db)` construction from `Depends(get_db_session)` — AuthService requires `async_sessionmaker`, so `request.app.state.auth_service` is the correct approach
