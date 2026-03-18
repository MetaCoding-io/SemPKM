---
estimated_steps: 5
estimated_files: 3
---

# T03: Options page with connection test and settings persistence

**Slice:** S01 — Backend auth fix + extension scaffold with working capture
**Milestone:** M014

## Description

Build the extension options page where users configure their SemPKM instance URL, API key, and default capture type. The connection test — a green checkmark or red X with version string — is the first visible proof the extension can communicate with the backend. Settings are persisted via `chrome.storage.sync` (from T02's `storage.js`). The default type selector is populated from `/api/types` after a successful connection test.

This delivers EXT-07 (settings) for this slice.

## Steps

1. Build `extension/options/options.html`:
   - Clean form layout with SemPKM branding
   - Fields:
     - "Instance URL" — `<input type="url" id="instance-url">` with placeholder "http://localhost:3000"
     - "API Key" — `<input type="password" id="api-key">` with placeholder "Your API key"
     - "Test Connection" button — triggers connection test
     - Connection status area: icon (✅ or ❌) + message (version string or error)
     - "Default Type" — `<select id="default-type">` disabled until connection succeeds, populated from `/api/types` response
     - "Save Settings" button
   - Use `<script type="module" src="options.js"></script>` to import shared modules
   - Include `<link rel="stylesheet" href="options.css">`

2. Build `extension/options/options.js`:
   - On page load: call `getSettings()` from storage.js, populate form fields with saved values
   - "Test Connection" click handler:
     - Read instanceUrl and apiKey from form inputs
     - Create a temporary `SemPKMClient(instanceUrl, apiKey)` 
     - Call `client.connect()` — on success:
       - Show green checkmark + `"Connected — SemPKM v${version}"`
       - Call `client.getTypes()` — populate the default-type `<select>` with options (value=IRI, text=label)
       - Enable the default-type selector
     - On failure:
       - Show red X + error message (connection refused → "Cannot reach instance", 401 → "Invalid API key", other → error text)
       - Disable default-type selector
   - "Save Settings" click handler:
     - Gather all form values into settings object
     - Call `saveSettings(settings)` from storage.js
     - Show brief "Settings saved ✓" confirmation
   - Auto-test connection on page load if instanceUrl and apiKey are already saved (convenience for returning users)

3. Build `extension/options/options.css`:
   - Clean, readable layout — max-width ~500px, centered
   - Form field styling: labeled inputs with consistent spacing
   - Connection status: green/red color coding, icon + text inline
   - Button styling matching SemPKM's design language (indigo accent `#4f46e5`)
   - "Settings saved" confirmation: subtle green text or toast
   - Responsive for the options page viewport

4. Wire imports: `options.js` must import from `../shared/api-client.js` and `../shared/storage.js`. Verify the import paths work in the extension context (Chrome allows ES module imports in options pages with `type="module"`).

5. Test the options page:
   - Open extension options (right-click extension icon → "Options" or `chrome://extensions` → extension → "Extension options")
   - Enter `http://localhost:3000` and a valid API key
   - Click "Test Connection" → should show green "Connected — SemPKM v..." and populate type selector
   - Enter invalid URL → should show red "Cannot reach instance"
   - Enter valid URL but bad API key → should show red "Invalid API key"
   - Save settings → reload page → settings persist
   - Default type selector shows types from installed Mental Models

## Must-Haves

- [ ] Options page loads without errors
- [ ] Instance URL and API Key fields save and restore from `chrome.storage.sync`
- [ ] "Test Connection" shows green checkmark + version for valid credentials
- [ ] "Test Connection" shows red X + descriptive error for invalid credentials or unreachable instance
- [ ] Default Type selector populates from `/api/types` after successful connection
- [ ] "Save Settings" persists all form values
- [ ] Auto-test on load if settings already saved

## Verification

- Open options page → fields show saved values from previous session
- Test Connection with valid localhost + API key → green "Connected — SemPKM v0.x.x"
- Test Connection with bad API key → red "Invalid API key"  
- Test Connection with wrong URL → red "Cannot reach instance"
- Save settings → close and reopen options page → all values preserved
- Type selector shows installed model types after successful connection

## Inputs

- `extension/shared/api-client.js` — `SemPKMClient` class with `connect()` and `getTypes()` methods (from T02)
- `extension/shared/storage.js` — `getSettings()`, `saveSettings()` functions (from T02)
- `extension/options/options.html` — Minimal stub from T02 (will be replaced with full implementation)
- `extension/options/options.js` — Minimal stub from T02 (will be replaced)
- `extension/options/options.css` — Empty from T02 (will be replaced)

## Observability Impact

- **Console logging:** `options.js` emits `[SemPKM] Options page loaded` on init, `[SemPKM] Connection test passed: {version, endpoints}` on success, `[SemPKM] Loaded N types` after type fetch, `[SemPKM] Settings saved` on save, and `[SemPKM] Connection test failed: <msg>` on error — all visible in the options page DevTools console.
- **Visual status:** Connection test result is rendered as a green ✅ or red ❌ status banner with descriptive message (version string or error cause). This is the primary user-facing diagnostic.
- **Error differentiation:** `connectionErrorMessage()` maps HTTP status codes to specific user messages: 401 → "Invalid API key", 403 → "API key lacks required permissions", TypeError → "Cannot reach instance", other → server detail string.
- **Inspection:** `chrome.storage.sync.get(null, console.log)` in extension DevTools reveals all persisted settings (instanceUrl, apiKey, defaultType, autoFillTitle, autoFillUrl, includeSelection).
- **Failure state:** If settings are blank or invalid, the type selector stays disabled with "— Connect to load types —" placeholder. The options page never shows a false-positive green status.

## Expected Output

- `extension/options/options.html` — Complete options page with form, connection test area, and type selector
- `extension/options/options.js` — Full options logic: load settings, test connection, save settings, auto-test
- `extension/options/options.css` — Clean styling for the options page
