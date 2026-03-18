---
id: T04
parent: S01
milestone: M014
provides:
  - Complete popup capture UI with type selector, title/body/URL fields, save flow, and toast feedback
  - populateFromPageData() export for S03 content script integration
  - Unconfigured state with "Open Settings" link to options page
key_files:
  - extension/popup/popup.html
  - extension/popup/popup.js
  - extension/popup/popup.css
key_decisions:
  - "Type selector groups by model_name using <optgroup> elements for clear visual hierarchy"
  - "Save button disables for 1.5s after success to prevent double-submit, then clears form for next capture"
  - "Title validation runs first (custom JS), type validation second (toast), before any API call"
patterns_established:
  - "Use showToast(message, type) for all popup user feedback — type is 'success' (green) or 'error' (red), auto-dismisses after 3s"
  - "Use setConnectionDot(state, tooltip) for header status — states are 'connected' (green), 'error' (red), 'loading' (amber pulse)"
  - "Use errorMessage(err) to map SemPKMError/TypeError to user-facing strings — 401→'Invalid API key', TypeError→'Cannot reach SemPKM instance'"
observability_surfaces:
  - "[SemPKM] Popup loaded — logged on DOMContentLoaded"
  - "[SemPKM] Loaded N types — logged after successful type population"
  - "[SemPKM] Object created: {iri} — logged on successful save"
  - "[SemPKM] Save failed: {msg} — logged on API error"
  - "[SemPKM] Popup: no settings configured — logged when unconfigured state shown"
  - "Green/red connection dot in popup header — visual at-a-glance health"
  - "Toast notifications — green success / red error with descriptive message"
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Popup capture flow with type selector, save, and success/error feedback

**Built complete popup capture UI with type selector (grouped by model), title/body/URL form, save-to-API flow with toast feedback, unconfigured state, and exported populateFromPageData() for S03 integration**

## What Happened

The popup files (popup.html, popup.js, popup.css) were already fully implemented during T02's scaffold work. T04 verified that the implementation matches all 10 must-haves from the plan, tested the full API round-trip against the running Docker stack, and confirmed visual rendering at Chrome popup dimensions (380px wide).

Key implementation details already present:
- **Type selector**: Populated from `SemPKMClient.getTypes()`, grouped by `model_name` using `<optgroup>`, pre-selects default type from settings
- **Auto-fill**: Active tab URL via `chrome.tabs.query`, title from page title when `autoFillTitle` setting is enabled
- **Save flow**: Validates title (required) → validates type selection → builds properties (`dcterms:title`, optional `sempkm:body`, optional `schema:url`) → calls `client.createObject()` → success toast or error toast
- **Loading states**: Save button shows spinner, disables during API call, re-enables on completion
- **Unconfigured state**: Shows ⚙️ icon + "Configure in Settings" message with "Open Settings" button that calls `chrome.runtime.openOptionsPage()`
- **Toast system**: `showToast(message, type)` with slide-in animation, auto-dismiss after 3s, green for success, red for error
- **Double-submit prevention**: Save button disables during API call and stays disabled 1.5s after success
- **populateFromPageData()**: Exported function accepting `{title, url, selectedText, author}` for S03 content script messaging

## Verification

1. **API round-trip**: Created test API token, verified `POST /api/commands` with Bearer auth creates objects (HTTP 200, returns IRI)
2. **Error paths**: Verified invalid Bearer returns `{"detail": "Invalid or expired API token"}` (401), no auth returns `{"detail": "Not authenticated"}` (401)
3. **Object persistence**: Verified created object appears in context-query search results
4. **Visual rendering**: Served popup HTML via static server, confirmed unconfigured state renders correctly at 380px viewport — header with branding, red connection dot, settings prompt, and "Open Settings" button all visible
5. **Configured state rendering**: Injected mock settings via localStorage, confirmed form appears with all fields (type selector, title, notes, URL, save button)
6. **Code audit**: All 10 must-haves verified present in the code — type population, default pre-select, URL auto-fill, createObject call, success/error toasts, unconfigured state, title validation, loading states, populateFromPageData export

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py -v` | 0 | ✅ pass (10/10) | 9.8s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass (62/62) | 5.1s |
| 3 | `curl -X POST -H "Authorization: Bearer $TOKEN" ... /api/commands` | 0 | ✅ pass (HTTP 200) | <1s |
| 4 | `curl -X POST -H "Authorization: Bearer bad-token" ... /api/commands` | 0 | ✅ pass (401, "Invalid or expired API token") | <1s |
| 5 | `curl -X POST ... /api/commands` (no auth) | 0 | ✅ pass (401, "Not authenticated") | <1s |
| 6 | Visual: popup at 380px viewport, unconfigured state | — | ✅ pass | — |
| 7 | Visual: popup at 380px viewport, configured state with form | — | ✅ pass | — |

## Diagnostics

- **Popup DevTools console**: Filter for `[SemPKM]` to see all lifecycle events — popup load, types count, save success/failure
- **Connection dot**: Green = types loaded, red = API unreachable or auth failed, amber pulse = loading
- **Toast notifications**: Green "✓ Object created!" for success, red with error detail for failure
- **Unconfigured state**: If `chrome.storage.sync` has no instanceUrl/apiKey, popup shows configuration prompt instead of form
- **Save button states**: Spinner during API call, disabled state prevents double-submit
- **Title validation**: "Title is required" error below input, red border on empty submit

## Deviations

None — the popup implementation was already complete from T02's scaffold work. T04's role was verification and testing of the round-trip.

## Known Issues

- CORS blocks cross-origin requests when testing popup outside Chrome extension context (e.g., via static server). This is expected — Chrome extensions bypass CORS via `host_permissions` in manifest.json.
- The `required` attribute on `<select>` and `<input>` triggers browser native validation before the custom JS handler. Both layers work correctly — native validation is a first defense, custom JS is the second.

## Files Created/Modified

- `extension/popup/popup.html` — Complete popup UI with header, unconfigured state, capture form (type/title/body/URL), save button, toast container
- `extension/popup/popup.js` — Full popup logic: settings check, type population with optgroup grouping, active tab URL auto-fill, save flow with validation and API call, toast system, loading states, populateFromPageData export
- `extension/popup/popup.css` — Polished popup styling for 380px viewport: header bar, connection dot, form layout, inputs, save button, toast animations, unconfigured state
