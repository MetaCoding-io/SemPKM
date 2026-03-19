---
estimated_steps: 7
estimated_files: 3
---

# T01: Wire "Link to this page" action through service worker

**Slice:** S02 — In-context actions — Link to page and Add Evidence
**Milestone:** M015

## Description

Replace the stub "Link to this page" button in the sidebar with a real `edge.create` API call relayed through the service worker. This is the simpler of the two actions — one API call creates a `schema:url` edge from the sidebar result object to the current page URL.

The service worker already has `_getApiConfig()` for reading API credentials and an inline `fetch()` pattern for calling the context-query endpoint. The new `linkToPage` message handler follows the same pattern. The sidebar sends `{type: 'linkToPage', objectIri, pageUrl}`, the service worker makes the API call, and responds with `{success: true}` or `{error: message}`.

## Steps

1. **Service worker — add `linkToPage` message handler** in `extension/background/service-worker.js`:
   - In the `chrome.runtime.onMessage.addListener` callback, add a new `if (message.type === 'linkToPage')` block
   - Handler receives `{objectIri, pageUrl}` from the message
   - Reads config via `_getApiConfig()` — if null, `sendResponse({error: 'SemPKM not configured'})`
   - POSTs to `${config.instanceUrl}/api/commands` with body: `{command: 'edge.create', params: {source: message.objectIri, target: message.pageUrl, predicate: 'schema:url'}}`
   - Headers: `Authorization: Bearer ${config.apiKey}`, `Content-Type: application/json`, `Accept: application/json`
   - On success (response.ok): `sendResponse({success: true})`
   - On failure: parse error detail from response body, `sendResponse({error: detail})`
   - Console log `[SemPKM] linkToPage: success/error` for diagnostics
   - Return `true` from the outer listener for async sendResponse

2. **Sidebar — track current tab URL** in `extension/sidebar/sidebar.js`:
   - Add module-level variables: `let _currentTabUrl = '';` and `let _currentTabTitle = '';`
   - In the `init()` function, after reading instanceUrl from storage, query `chrome.tabs.query({active: true, currentWindow: true})` to set `_currentTabUrl` and `_currentTabTitle`
   - In the `contextResultsUpdated` message listener, also re-query `chrome.tabs.query` to refresh `_currentTabUrl` and `_currentTabTitle` (handles navigation while sidebar is open)

3. **Sidebar — replace stub link handler** in `extension/sidebar/sidebar.js`:
   - In `_renderCard()`, find the `linkBtn` creation. Change its CSS class from `'action-stub'` to `'action-link'`
   - Replace the stub click handler with a new function `_linkToPage(objectIri, btn)`:
     - If `!_currentTabUrl`: `showToast('Navigate to a page first', 'error'); return;`
     - Disable the button: `btn.disabled = true; btn.textContent = 'Linking…';`
     - Call `chrome.runtime.sendMessage({type: 'linkToPage', objectIri: objectIri, pageUrl: _currentTabUrl})`
     - In the callback: if `response.success` → `showToast('✓ Linked to this page')`, else → `showToast(response.error || 'Failed to link', 'error')`
     - Re-enable button: `btn.disabled = false; btn.textContent = 'Link to page';`
     - Handle `chrome.runtime.lastError` — show error toast and re-enable button
   - Wire the handler: `linkBtn.addEventListener('click', function() { _linkToPage(item.iri, linkBtn); });`

4. **CSS — replace `.action-stub` for link button** in `extension/sidebar/sidebar.css`:
   - Add new `.action-link` rule (solid style, not dashed border):
     ```css
     .action-link {
       color: var(--text-secondary);
       background: transparent;
       border: 1px solid var(--border-light);
     }
     .action-link:hover {
       color: var(--accent);
       border-color: var(--accent);
       background: var(--accent-subtle);
     }
     .action-link:disabled {
       opacity: 0.5;
       cursor: not-allowed;
     }
     ```
   - Keep `.action-stub` for the Evidence button (it stays as a stub until T02)

5. **Syntax validation**: Run `node --check extension/background/service-worker.js` and `node --check extension/sidebar/sidebar.js`

6. **Regression check**: Run `node --test extension/tests/test-context-utils.js` — all 23 tests must pass

7. **Visual inspection**: Confirm the link button uses `.action-link` class (not `.action-stub`) by reading the final `_renderCard()` function

## Must-Haves

- [ ] Service worker handles `linkToPage` message type and calls `edge.create` API
- [ ] Sidebar tracks `_currentTabUrl` and refreshes on tab navigation
- [ ] Link button shows loading state ("Linking…") and disables during API call
- [ ] Success toast: "✓ Linked to this page"
- [ ] Error toast shows API error detail
- [ ] Link button has `.action-link` CSS class (solid border, not dashed)
- [ ] `node --check` passes on both modified JS files
- [ ] 23 existing unit tests still pass

## Verification

- `node --check extension/background/service-worker.js` — no syntax errors
- `node --check extension/sidebar/sidebar.js` — no syntax errors
- `node --test extension/tests/test-context-utils.js` — 23/23 pass
- `rg 'action-link' extension/sidebar/sidebar.js` — confirms link button uses new class
- `rg "type === 'linkToPage'" extension/background/service-worker.js` — confirms handler exists
- `rg '_currentTabUrl' extension/sidebar/sidebar.js` — confirms tab URL tracking exists

## Inputs

- `extension/background/service-worker.js` — existing service worker with `_getApiConfig()`, inline fetch pattern, message listener structure (from S01)
- `extension/sidebar/sidebar.js` — existing sidebar with stub `linkBtn` handler, `showToast()`, `_renderCard()` (from S01)
- `extension/sidebar/sidebar.css` — existing CSS with `.action-stub` styles (from S01)
- S01 summary: "Link to this page" and "Add Evidence" buttons are stubs showing "coming soon" toasts. The `_getApiConfig()` pattern reads `{instanceUrl, apiKey}` from chrome.storage.sync. The service worker uses inline fetch — can't import ES modules. Messages follow `{type: string, ...params}` shape.

## Expected Output

- `extension/background/service-worker.js` — extended with `linkToPage` message handler that calls `edge.create` API
- `extension/sidebar/sidebar.js` — stub link handler replaced with `_linkToPage()`, `_currentTabUrl`/`_currentTabTitle` tracked
- `extension/sidebar/sidebar.css` — `.action-link` styles added (solid border replacing dashed stub)
