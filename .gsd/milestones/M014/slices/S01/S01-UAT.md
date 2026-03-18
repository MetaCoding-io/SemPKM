# S01: Backend auth fix + extension scaffold with working capture — UAT

**Milestone:** M014
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for backend tests + live-runtime for extension + human-experience for Chrome sideload)
- Why this mode is sufficient: Backend auth is proven by automated unit tests. Extension functionality requires Chrome sideloading which cannot be automated in CI yet. Admin UI round-trip needs a running Docker stack.

## Preconditions

- Docker stack running: `docker compose up -d` from project root
- At least one Mental Model installed (basic-pkm recommended — provides Note type for simplest capture)
- Chrome browser available for extension sideloading
- Backend virtual environment available: `backend/.venv/bin/python` exists

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py tests/test_api_surface.py -v` — should report 72 passed, 0 failed.

## Test Cases

### 1. Bearer token auth on commands endpoint

1. Create an API token via the admin UI or `curl -X POST -H "Cookie: <session>" http://localhost:3000/admin/api-keys -d "name=test-token"`
2. Send `curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" http://localhost:3000/api/commands -d '{"commands": [{"type": "object.create", "params": {"type_iri": "urn:sempkm:model:basic-pkm:Note", "properties": {"dcterms:title": "Bearer test"}}}]}'`
3. **Expected:** HTTP 200, response body contains `"results"` array with created object IRI

### 2. Invalid Bearer token rejected with 401

1. Send `curl -X POST -H "Authorization: Bearer invalid-garbage-token" -H "Content-Type: application/json" http://localhost:3000/api/commands -d '{"commands": [{"type": "object.create", "params": {"type_iri": "urn:sempkm:model:basic-pkm:Note", "properties": {"dcterms:title": "Should fail"}}}]}'`
2. **Expected:** HTTP 401, response body `{"detail": "Invalid or expired API token"}`

### 3. No credentials rejected with 401

1. Send `curl -X POST -H "Content-Type: application/json" http://localhost:3000/api/commands -d '{"commands": [{"type": "object.create", "params": {"type_iri": "urn:sempkm:model:basic-pkm:Note", "properties": {"dcterms:title": "Should fail"}}}]}'`
2. **Expected:** HTTP 401, response body `{"detail": "Not authenticated"}`

### 4. Admin API key management — create and use

1. Log in as owner, navigate to `/admin/api-keys`
2. Enter "Extension Key" in the Name field, click "Create Token"
3. **Expected:** Green banner appears showing the plaintext token with a Copy button and "This key will only be shown once" warning
4. Click Copy to clipboard
5. Reload the page
6. **Expected:** Token listed in table with name "Extension Key" and created timestamp. Plaintext NOT shown again.

### 5. Admin API key management — delete and verify revocation

1. From `/admin/api-keys`, click Delete on the "Extension Key" row
2. **Expected:** Confirmation dialog appears
3. Confirm deletion
4. **Expected:** Token removed from list, success message shown
5. Use the previously copied token: `curl -H "Authorization: Bearer <deleted-token>" http://localhost:3000/api/types`
6. **Expected:** HTTP 401, `{"detail": "Invalid or expired API token"}`

### 6. Extension sideload in Chrome

1. Navigate to `chrome://extensions`
2. Enable "Developer mode" toggle
3. Click "Load unpacked", select the `extension/` directory
4. **Expected:** Extension loads without errors. "SemPKM Capture" appears in the extension list with indigo icon. Service worker status shows "Active".

### 7. Extension options page — connection test

1. Click "Details" on the extension in `chrome://extensions`, then "Extension options" (or right-click extension icon → Options)
2. Enter `http://localhost:3000` in Instance URL
3. Enter a valid API key (created in test case 4)
4. Click "Test Connection"
5. **Expected:** Green ✅ banner with "Connected — SemPKM v2.6.0" (or current version). Default Type selector becomes enabled and shows available types (Note, Project, Person, etc.)
6. Select "Note" as default type, click "Save Settings"
7. **Expected:** "Settings saved ✓" confirmation appears and auto-dismisses

### 8. Extension options page — invalid credentials

1. On the options page, change the API key to "bad-key-12345"
2. Click "Test Connection"
3. **Expected:** Red ❌ banner with "Invalid API key". Default Type selector remains disabled.

### 9. Extension popup — capture object

1. Navigate to any web page in Chrome
2. Click the SemPKM extension icon in the toolbar
3. **Expected:** Popup appears (380px wide) with connection status dot (green if configured), type selector, title field, notes field, URL field
4. Select "Note" from the type dropdown
5. Enter "Test from extension" in the Title field
6. Click "Save"
7. **Expected:** Green toast "✓ Object created!" appears. Save button shows spinner during API call.
8. Open SemPKM workspace at `http://localhost:3000/browser/`
9. **Expected:** "Test from extension" appears in the object navigator

### 10. Extension popup — unconfigured state

1. Clear extension storage (chrome://extensions → Details → Clear data for SemPKM Capture, or `chrome.storage.sync.clear()` in extension DevTools)
2. Click the extension icon
3. **Expected:** Popup shows unconfigured state with ⚙️ icon, "Configure in Settings" message, and "Open Settings" button

### 11. Context menu registration

1. Select text on any web page
2. Right-click the selection
3. **Expected:** "Save to SemPKM" appears in the context menu
4. Click it
5. **Expected:** Nothing happens yet (handler is a shell — wired in S03). No errors in service worker console.

## Edge Cases

### Empty title rejection

1. Open popup, select a type, leave Title empty, click Save
2. **Expected:** Red error message "Title is required" below the title field. No API call made.

### Connection lost after configuration

1. Configure extension with valid settings, verify green dot
2. Stop the Docker stack: `docker compose down`
3. Open the popup, try to save
4. **Expected:** Red toast with "Cannot reach SemPKM instance" or similar network error. Red connection dot.

### Multiple tokens

1. Create 3 API tokens via admin page
2. **Expected:** All 3 listed in the table with different names
3. Delete the middle one
4. **Expected:** Only that token is removed; the other two remain and continue working

## Failure Signals

- Popup shows unconfigured state when settings are already saved → `chrome.storage.sync` not persisting (check for storage permission in manifest)
- Connection test shows red with valid credentials → CORS issue or nginx not forwarding Authorization header (check network tab for preflight failures)
- Type selector is empty after successful connection → `/api/types` returning empty array (check if Mental Models are installed)
- Save returns 401 → Bearer token not reaching backend (check nginx `proxy_set_header Authorization` directive)
- Save returns 403 → Token user role insufficient (token must be for owner or member, not guest)
- Admin API Keys page returns 404 → routes not registered (check admin router import)
- Context menu not appearing → service worker not active (check `chrome://extensions` for errors)

## Requirements Proved By This UAT

- EXT-11 — Backend auth: test cases 1-3 prove Bearer token acceptance/rejection on commands endpoint
- EXT-07 — Settings: test cases 7-8 prove options page connection test, type population, settings persistence
- EXT-01 — Popup capture: test case 9 proves type selector + title + save round-trip
- EXT-09 — Feedback: test cases 8-9 prove green/red indicators and toast notifications

## Not Proven By This UAT

- EXT-02 (SHACL forms) — popup only has title/body/URL fields; dynamic SHACL form rendering is S02
- EXT-03 (auto-population) — title/URL auto-fill from page metadata is S03
- EXT-04 (relationship picker) — not implemented yet (S04)
- EXT-05 (context menu handler) — menu item registered but handler is a shell (S03)
- EXT-06 (schema.org) — not implemented yet (S03)
- EXT-08 (keyboard shortcut) — not implemented yet (S05)
- EXT-10 (cross-browser) — Firefox manifest not created yet (S05)
- EXT-12 (user guide) — not written yet (S05)
- EXT-13 (E2E tests) — no Playwright extension tests yet (S05)

## Notes for Tester

- The extension popup cannot be tested via Playwright — Chrome extension popups require manual interaction. The S05 E2E tests will use a different approach (testing the API round-trip without the extension UI).
- When testing the options page outside Chrome (e.g., via static server), cross-origin requests to localhost:3000 will fail due to CORS. This is expected — Chrome extensions bypass CORS.
- The admin API keys page is only accessible to users with the "owner" role. Guest and member users will see a 403.
- Extension icons are placeholder indigo squares with white "S" — not final branding.
