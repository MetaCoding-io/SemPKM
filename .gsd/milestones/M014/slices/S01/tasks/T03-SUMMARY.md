---
id: T03
parent: S01
milestone: M014
provides:
  - Complete extension options page with connection test, type selector population, and settings persistence via chrome.storage.sync
key_files:
  - extension/options/options.html
  - extension/options/options.js
  - extension/options/options.css
key_decisions:
  - API key visibility toggle with eye icon for UX — users can show/hide the key during entry
  - Auto-test connection on page load when settings are already saved — returns users skip the manual click
  - Connection error mapping in connectionErrorMessage() provides user-friendly messages for each failure type
patterns_established:
  - "Use setVisible(el, visible) helper for toggling .hidden class on elements — avoids scattered classList.toggle calls"
  - "Use data-savedValue on select elements to stash the persisted value for restoration after async population"
observability_surfaces:
  - Console log: "[SemPKM] Options page loaded" on init
  - Console log: "[SemPKM] Connection test passed: {version, endpoints}" on successful connection test
  - Console log: "[SemPKM] Loaded N types" after type selector population
  - Console log: "[SemPKM] Settings saved" on save
  - Console warn: "[SemPKM] Connection test failed: <msg>" on connection failure
  - Visual: green ✅ / red ❌ status banner with descriptive message
  - Inspection: chrome.storage.sync.get(null, console.log) shows all persisted settings
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Options page with connection test and settings persistence

**Built extension options page with connection test (green/red status), type selector population from /api/types, settings persistence via chrome.storage.sync, and auto-test on load**

## What Happened

Replaced the three stub files (options.html, options.js, options.css) with a complete settings page. The HTML has a clean form layout with SemPKM branding (inline SVG icon), two sections (Connection and Capture Defaults), labeled inputs for Instance URL and API Key (with password visibility toggle), Test Connection button with loading spinner, connection status banner, Default Type select (disabled until connection succeeds), three capture-behavior checkboxes, and a Save Settings button with auto-dismissing confirmation text.

The JS module imports `SemPKMClient` and `getSettings`/`saveSettings` from the shared modules. On page load it populates form fields from saved settings and auto-triggers a connection test if both URL and key are present. The Test Connection handler creates a temporary client, calls `connect()` then `getTypes()`, and shows green ✅ + version string on success or red ❌ + error message on failure. Error mapping differentiates 401 ("Invalid API key"), 403 ("API key lacks required permissions"), TypeError ("Cannot reach instance"), and generic server errors. The type selector is populated with options (value=IRI, text=label) from the `/api/types` response.

The CSS provides a centered 520px layout with indigo (#4f46e5) accent, consistent input/button styling, animated status banner (slideIn), and fade-in/fade-out save confirmation.

## Verification

Tested against the running SemPKM Docker stack:

1. **Page loads without errors** — served via python HTTP server on port 8765, all JS modules loaded, console shows `[SemPKM] Options page loaded`
2. **Valid connection test** — entered `http://localhost:8901` + valid API key → green ✅ "Connected — SemPKM v2.6.0" → type selector enabled with 6 types (Project, Note, Person, Concept, Task, Milestone)
3. **Invalid API key** — entered bad key → red ❌ "Invalid API key" → type selector disabled
4. **Unreachable instance** — entered `http://localhost:9999` → red ❌ "Cannot reach instance"
5. **Empty field validation** — clicked Test Connection with empty URL → red ❌ "Enter an instance URL first"
6. **Save confirmation** — clicked Save Settings → "Settings saved ✓" appeared and auto-dismissed after 2s
7. **API key toggle** — clicked eye icon → field type toggled between password/text
8. **Backend tests pass** — 10/10 bearer auth tests, 62/62 API surface tests (no regression)

Note: Cross-origin fetch from the test HTTP server to the nginx-proxied backend (port 3901) fails due to duplicate `Access-Control-Allow-Origin: *` headers from both nginx and FastAPI CORSMiddleware. This is a pre-existing configuration issue that does **not** affect the real extension — Chrome extension pages bypass CORS via `host_permissions` in the manifest. Direct-to-API testing (port 8901) works correctly.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/options/options.js` | 0 | ✅ pass | <1s |
| 2 | `cd backend && .venv/bin/pytest tests/test_commands_bearer_auth.py -v` | 0 | ✅ pass | 0.69s |
| 3 | `cd backend && .venv/bin/pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 1.47s |
| 4 | Browser: Test Connection (valid credentials, port 8901) | — | ✅ pass | — |
| 5 | Browser: Test Connection (invalid API key) | — | ✅ pass | — |
| 6 | Browser: Test Connection (unreachable URL) | — | ✅ pass | — |
| 7 | Browser: Save Settings confirmation appears | — | ✅ pass | — |

## Diagnostics

- **Options page DevTools console:** Shows `[SemPKM] Options page loaded`, connection test results, type count, and save confirmations
- **Connection status banner:** Visual green ✅ or red ❌ with specific error message — the primary user-facing diagnostic
- **Error differentiation:** `connectionErrorMessage()` maps: 401 → "Invalid API key", 403 → "API key lacks required permissions", TypeError → "Cannot reach instance", other → server detail string
- **Storage inspection:** `chrome.storage.sync.get(null, console.log)` in extension DevTools shows all persisted settings (instanceUrl, apiKey, defaultType, autoFillTitle, autoFillUrl, includeSelection)
- **Type selector:** After successful connection, inspect `#default-type` options to verify type IRIs and labels match installed Mental Models

## Deviations

- Added API key visibility toggle (eye icon) — not in the original plan but standard UX for password fields
- Added three capture-behavior checkboxes (auto-fill title, auto-fill URL, include selection) — these were already in `storage.js` DEFAULTS from T02 and needed form controls
- Added empty-field validation before connection test — prevents unnecessary network requests
- Added Enter key shortcut on URL/key fields to trigger connection test

## Known Issues

- **Double CORS header on nginx-proxied backend:** Both nginx and FastAPI CORSMiddleware add `Access-Control-Allow-Origin: *`, which causes browsers to reject cross-origin requests to port 3901. Does not affect the Chrome extension (which bypasses CORS) but would affect any web-based client using the proxied endpoint. Pre-existing issue, not introduced by this task.

## Files Created/Modified

- `extension/options/options.html` — Complete options page with connection form, type selector, capture defaults, and save button
- `extension/options/options.js` — Full options logic: load/save settings, test connection, populate types, auto-test on load
- `extension/options/options.css` — Clean styling: centered 520px layout, indigo accent, animated status banner, fade confirmation
- `.gsd/milestones/M014/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
