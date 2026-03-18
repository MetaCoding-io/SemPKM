---
estimated_steps: 6
estimated_files: 3
---

# T04: Popup capture flow with type selector, save, and success/error feedback

**Slice:** S01 — Backend auth fix + extension scaffold with working capture
**Milestone:** M014

## Description

Build the popup capture UI — the core extension interaction surface. When the user clicks the extension icon, the popup opens with a type selector (populated from `/api/types`), a title input, a body textarea, and a Save button. Saving calls `POST /api/commands` with `object.create` via the `SemPKMClient` from T02. Success shows a green toast; failure shows a red toast with the error message.

This completes the full round-trip demo: popup → Bearer auth (T01) → API → triplestore. Combined with T02 (shared modules) and T03 (settings), this proves the extension can create real objects in SemPKM.

This delivers EXT-01 (popup capture) and EXT-09 (success/error feedback) for this slice.

**Skill note:** The `frontend-design` skill is relevant for popup CSS styling if the executor wants polish guidance.

## Steps

1. Build `extension/popup/popup.html`:
   - Compact layout (popup viewport is ~400px wide, ~600px tall max)
   - Header bar with SemPKM branding + connection status dot (green/red)
   - Unconfigured state: if no settings saved, show "⚙️ Configure SemPKM in extension settings" with a link/button that opens the options page (`chrome.runtime.openOptionsPage()`)
   - Configured state (main form):
     - Type selector: `<select id="type-select">` populated from `getTypes()`. Show type label. Pre-select the default type from settings (if set). Group by model_name if available.
     - Title: `<input type="text" id="title-input" placeholder="Title">` — required field
     - Body: `<textarea id="body-input" placeholder="Notes..." rows="4"></textarea>` — optional, will be pre-filled by content scripts in S03
     - Source URL: `<input type="url" id="url-input" readonly>` — display-only, auto-filled from active tab URL
     - Save button: `<button id="save-btn">Save</button>` — primary action
   - Toast container for success/error messages (positioned at bottom of popup)
   - Use `<script type="module" src="popup.js"></script>`

2. Build `extension/popup/popup.js`:
   - On popup open (DOMContentLoaded):
     - Load settings via `getSettings()`
     - If no instanceUrl or apiKey: show unconfigured state, hide form
     - If configured: create `SemPKMClient`, show form
     - Call `client.getTypes()` → populate type `<select>` with `<option value="${iri}">${label}</option>`
     - Pre-select default type from settings
     - Get active tab URL: `chrome.tabs.query({active: true, currentWindow: true})` → set url-input value
     - Show green connection dot if types loaded; red if API call fails
   - Save button click handler:
     - Validate: title is required (show inline error if empty)
     - Gather form values: type IRI, title, body (if not empty), URL
     - Build properties object: `{"dcterms:title": title}`. If body is not empty, include it (but NOT as a property — body is set via a separate `body.set` command; for now in this slice, include body as `sempkm:body` property in the create command to keep it simple — the full body.set pattern can be refined in later slices)
     - If URL is present, add `schema:url` to properties
     - Call `client.createObject({type: typeIri, properties})`
     - On success: show green toast "✓ Object created!", disable save button briefly to prevent double-submit
     - On error: show red toast with error message, re-enable save button
   - Toast system:
     - `showToast(message, type)` where type is 'success' or 'error'
     - Toast appears at bottom of popup, auto-dismisses after 3s
     - Green background for success, red for error
   - Export `populateFromPageData(data)` function that accepts `{title, url, selectedText, author}` and fills form fields. This function will be called by S03's content script messaging. For now it just exists as an exported function on the popup module.
   - Loading states: show spinner/disabled state on Save button during API call; show loading text while types are being fetched

3. Build `extension/popup/popup.css`:
   - Popup dimensions: `width: 380px; min-height: 200px;` (Chrome constrains popup width)
   - Header: small bar with "SemPKM" text + connection dot (8px green/red circle)
   - Form layout: stacked fields with labels, consistent 12px spacing
   - Type selector: full-width `<select>` with appropriate font size
   - Title input: full-width, slightly larger font (this is the primary field)
   - Body textarea: full-width, 4 rows, resizable vertically
   - URL input: full-width, muted appearance (read-only display)
   - Save button: full-width, indigo accent (`#4f46e5`), white text, hover/active states
   - Toast: fixed bottom, full-width, padding, green (#22c55e) or red (#ef4444) background, white text, fade-out animation
   - Unconfigured state: centered message with settings icon, muted text
   - Loading state: spinner or pulsing animation on save button
   - Typography: system-ui font stack, readable sizes for the compact popup viewport
   - Follow CLAUDE.md rules: no inline styles on SVGs, CSS handles all sizing

4. Wire the "open options page" link in the unconfigured state:
   ```javascript
   document.getElementById('open-settings').addEventListener('click', () => {
     chrome.runtime.openOptionsPage();
   });
   ```

5. Test the complete flow against the running Docker stack:
   - Ensure Docker stack is running on localhost:3000
   - Ensure an API key exists (check via admin UI or database)
   - Configure extension settings (T03 options page)
   - Open popup → verify type selector shows types from installed models
   - Enter a title → click Save → verify success toast
   - Open SemPKM workspace → verify the new object appears in the nav tree with the correct title and type
   - Test error cases: disconnect Docker → click Save → verify error toast

6. Test edge cases:
   - Empty title → Save should show inline validation error, NOT call API
   - No API key configured → popup shows "Configure in Settings" message
   - API returns 401 (invalid key) → popup shows error toast with "Invalid API key"
   - API returns 500 → popup shows error toast with server error message
   - Rapid double-click Save → only one object created (debounce/disable pattern)

## Must-Haves

- [ ] Popup opens with type selector populated from `/api/types`
- [ ] Type selector pre-selects default type from settings
- [ ] Active tab URL auto-fills the URL field
- [ ] Save creates an object via `POST /api/commands` with correct payload
- [ ] Success toast appears after successful save
- [ ] Error toast appears with descriptive message on failure
- [ ] Unconfigured state shows "Configure in Settings" with link to options page
- [ ] Title field validation (required, show error if empty)
- [ ] Loading state on Save button during API call
- [ ] `populateFromPageData()` function exported for S03 integration

## Verification

- Open popup → type selector shows Note, Concept, Person, Project (from basic-pkm model)
- Enter title "Test from extension" → Save → green toast "✓ Object created!"
- Open SemPKM workspace → "Test from extension" object visible in nav tree
- Remove API key from settings → open popup → shows "Configure in Settings"
- Enter empty title → Save → shows "Title is required" error (no API call made)
- Stop Docker → Save → red error toast with network error message

## Inputs

- `extension/shared/api-client.js` — `SemPKMClient.createObject()` and `getTypes()` (from T02)
- `extension/shared/storage.js` — `getSettings()`, `getClient()` (from T02)
- `extension/options/` — Options page where user configures settings (from T03)
- `backend/app/commands/router.py` — Commands endpoint now accepts Bearer auth (from T01)
- `backend/app/commands/schemas.py` — `ObjectCreateParams`: `{type, slug?, properties}`. The `type` field accepts full IRI (e.g., `urn:sempkm:model:basic-pkm:Note`). The `properties` dict maps predicate IRIs or compact forms (e.g., `dcterms:title`) to values.

## Expected Output

- `extension/popup/popup.html` — Complete popup UI with type selector, title, body, URL, save button, toast area
- `extension/popup/popup.js` — Full popup logic: load types, save object, toast notifications, loading states, unconfigured state
- `extension/popup/popup.css` — Polished popup styling for the compact extension viewport
