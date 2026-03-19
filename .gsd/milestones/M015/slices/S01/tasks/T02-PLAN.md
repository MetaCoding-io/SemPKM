---
estimated_steps: 8
estimated_files: 2
---

# T02: Build service worker context pipeline with debounce, cache, and badge

**Slice:** S01 — Context queries, badge count, and sidebar with grouped results
**Milestone:** M015

## Description

The core data pipeline: when a user navigates to a page, the service worker debounces for 2 seconds, queries the context-query API with page URL + title, ranks and caches the results, and sets the badge count. Also handles messaging to the sidebar and opens the sidebar on Alt+K.

Two files: `extension/shared/context-utils.js` (new — pure functions for ranking, grouping, and LRU cache) and `extension/background/service-worker.js` (extended — tab listener, debounce, badge, messaging).

The pure functions in `context-utils.js` are extracted specifically so T04 can unit-test them without mocking browser APIs.

**Important:** The extension uses vanilla JS with no bundler (D169). The service worker cannot use ES module `import` (Firefox doesn't support `"type": "module"` for background scripts). `context-utils.js` must use a pattern that works in both contexts:
- For the service worker: `importScripts()` (the classic way to load scripts in service workers)
- For the sidebar: ES module `import` (sidebar.html can use `<script type="module">`)
- For Node.js tests: `require()` or dynamic `import()`

Best approach: write `context-utils.js` as a self-executing script that assigns to `globalThis.SemPKMContextUtils = { rankResults, groupByType, LRUCache }`. The service worker uses `importScripts('../shared/context-utils.js')` and accesses via `SemPKMContextUtils.*`. Sidebar can import it via a thin ES module wrapper. Node.js tests can `require()` it since `globalThis` is available in Node.

## Steps

1. **Create `extension/shared/context-utils.js` with pure functions:**
   - `rankResults(results)`:
     - Input: array of `{iri, label, type_iri, type_label, match_type, snippet}`
     - Ranking: `match_type === 'url'` first, then `'title'`, then `'keyword'` (any other value)
     - Within same match_type, preserve original order
     - Truncate to top 10
     - Return new sorted array (don't mutate input)
   - `groupByType(results)`:
     - Input: array of ranked results
     - Group by `type_label` — results with same `type_label` go into the same group
     - Null/undefined `type_label` grouped as `"Other"`
     - Return array of `{typeLabel, typeIri, results: [...]}` preserving first-seen order of type groups
   - `LRUCache` class:
     - Constructor takes `maxSize` (default 100)
     - `get(key)` — returns value or undefined, promotes key to most recent
     - `set(key, value)` — adds/updates entry, evicts oldest if at max
     - `has(key)` — returns boolean
     - `clear()` — removes all entries
     - Implementation: use a `Map` (which preserves insertion order). On `get()`, delete and re-set to move to end. On `set()` at max size, delete the first key (`map.keys().next().value`).
   - Module pattern: assign all exports to `globalThis.SemPKMContextUtils` so it works via `importScripts()`, and also support `module.exports` for Node.js testing:
     ```javascript
     const SemPKMContextUtils = { rankResults, groupByType, LRUCache };
     if (typeof globalThis !== 'undefined') globalThis.SemPKMContextUtils = SemPKMContextUtils;
     if (typeof module !== 'undefined' && module.exports) module.exports = SemPKMContextUtils;
     ```

2. **Add `importScripts` for shared modules in service worker:**
   - At the top of `service-worker.js`, add:
     ```javascript
     importScripts('../shared/context-utils.js');
     ```
   - Note: The service worker CANNOT use `importScripts` for `api-client.js` (it uses ES module `export`). Instead, inline the API call using `fetch()` directly with settings from `chrome.storage`. This avoids the ES module / classic script conflict.
   - Helper function `_getApiConfig()`: reads `instanceUrl` and `apiKey` from `chrome.storage.sync` (or `.local` fallback). Returns `{instanceUrl, apiKey}` or null.
   - Helper function `_queryContext(url, title, keywords)`: calls `POST /api/context-query` using `fetch()` with Bearer auth from stored settings. Returns `{results, total}` or throws. Applies `contextTimeout` from settings as `AbortController` timeout.

3. **Implement tab navigation listener with debounce:**
   - `chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {...})` 
   - Filter: only act when `changeInfo.status === 'complete'` and `tab.url` exists and starts with `http`
   - Check `autoCheckContext` setting — if false, skip
   - Clear any pending debounce timer for this tab: `_debounceTimers.delete(tabId)`
   - Set new timer: `setTimeout(() => _handleTabReady(tabId, tab.url, tab.title), delay)` where `delay` comes from `contextCheckDelay` setting
   - Store timers in `Map<tabId, timerId>` for cleanup

4. **Implement `_handleTabReady(tabId, url, title)`:**
   - Check LRU cache first: `if (contextCache.has(url))` → set badge from cached data, return
   - Extract keywords from title: split by common separators (`- | — · /`), take unique words ≥3 chars, join with space
   - Call `_queryContext(url, title, keywords)`
   - On success: rank results via `SemPKMContextUtils.rankResults()`, cache as `contextCache.set(url, {results: ranked, timestamp: Date.now()})`, set badge
   - On error: log with `[SemPKM]` prefix, set badge to `"!"` to indicate error
   - Set badge: `chrome.action.setBadgeText({text: count > 0 ? String(count) : '', tabId})` 
   - Set badge color: `chrome.action.setBadgeBackgroundColor({color: '#0d9488', tabId})`

5. **Add `chrome.runtime.onMessage` handler for sidebar communication:**
   - Handle `{type: 'getContextResults'}`:
     - Get active tab via `chrome.tabs.query({active: true, currentWindow: true})`
     - Look up cached results for tab's URL
     - Respond with `{results, url, cached: true/false}` or `{results: [], url, error: 'No results cached'}`
   - Handle `{type: 'refreshContextResults'}`:
     - Force re-query for active tab (bypass cache)
     - After query completes, send `{type: 'contextResultsUpdated', results}` to sidebar

6. **Handle Alt+K command to open sidebar:**
   - `chrome.commands.onCommand.addListener((command) => {...})`
   - When `command === 'open-context-sidebar'`:
     - Chrome: `chrome.sidePanel.open({windowId})` (get windowId from `chrome.windows.getCurrent()`)
     - Firefox: `browser.sidebarAction.open()` (if available)
     - Wrap in try/catch — log error if Side Panel API not available

7. **Clean up debounce timers on tab removal:**
   - `chrome.tabs.onRemoved.addListener((tabId) => { ... })` — clear debounce timer for closed tab

8. **Add `[SemPKM]` console logging for all lifecycle events:**
   - Tab detected: `[SemPKM] Tab ${tabId} loaded: ${url}`
   - Cache hit: `[SemPKM] Cache hit for ${url}: ${count} results`
   - Query start: `[SemPKM] Querying context for ${url}`
   - Query success: `[SemPKM] Context query: ${count} results for ${url}`
   - Query error: `[SemPKM] Context query error: ${err.message}`
   - Sidebar open: `[SemPKM] Opening context sidebar`

## Must-Haves

- [ ] `context-utils.js` exports `rankResults`, `groupByType`, `LRUCache` via `globalThis.SemPKMContextUtils`
- [ ] `rankResults` sorts URL > title > keyword and truncates to 10
- [ ] `LRUCache` evicts oldest at max 100 entries
- [ ] Service worker listens on `chrome.tabs.onUpdated` with 2s debounce
- [ ] Badge text shows per-tab result count (empty when 0, "!" on error)
- [ ] `getContextResults` message handler returns cached results for active tab
- [ ] Alt+K command opens the sidebar via `chrome.sidePanel.open()`
- [ ] All console logs prefixed with `[SemPKM]`

## Verification

- `node --check extension/shared/context-utils.js` exits 0
- `node --check extension/background/service-worker.js` exits 0
- `node -e "require('./extension/shared/context-utils.js'); const c = new SemPKMContextUtils.LRUCache(3); c.set('a',1); c.set('b',2); c.set('c',3); c.set('d',4); console.assert(!c.has('a')); console.assert(c.has('d')); console.log('LRU smoke test OK')"` — passes
- `node -e "require('./extension/shared/context-utils.js'); const r = SemPKMContextUtils.rankResults([{match_type:'keyword',label:'K'},{match_type:'url',label:'U'}]); console.assert(r[0].label === 'U'); console.log('Rank smoke test OK')"` — passes

## Observability Impact

- Signals added: `[SemPKM]` prefixed console logs for tab detection, cache hits/misses, query start/success/error, sidebar open
- How a future agent inspects this: Open `chrome://extensions` → service worker DevTools → Console tab
- Failure state exposed: Badge "!" indicates query failure; console logs show specific error

## Inputs

- `extension/shared/api-client.js` — T01 added `contextQuery()` method (but service worker can't import ES modules, so we inline the fetch call using the same endpoint/auth pattern)
- `extension/shared/storage.js` — T01 added `autoCheckContext`, `contextCheckDelay`, `contextTimeout` to DEFAULTS
- `extension/manifest.json` — T01 added `sidePanel`, `tabs` permissions, `open-context-sidebar` command
- Service worker current content: context menu registration + click handler (preserve this)

## Expected Output

- `extension/shared/context-utils.js` — new file with `rankResults()`, `groupByType()`, `LRUCache` class
- `extension/background/service-worker.js` — extended with tab listener, debounce, context query, cache, badge, message handlers, Alt+K sidebar open command
