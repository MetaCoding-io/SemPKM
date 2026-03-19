# M015 — Research: Browser Extension Phase 2 — Knowledge Context Overlay

**Date:** 2026-03-18

## Summary

M015 adds a sidebar panel showing related knowledge objects while browsing, a badge count on the extension icon, and in-context actions (Open, Link to page, Add Evidence). The backend infrastructure is already complete — the `POST /api/context-query` endpoint (M013) handles URL matching via SPARQL and keyword matching via LuceneSail FTS, returning deduplicated results with labels and types. The extension already has `SemPKMClient.searchObjects()` wired to this endpoint. The work is primarily extension-side: adding the sidebar UI, wiring auto-context queries from the service worker, managing badge state, and building the in-context action flows.

The critical architectural decision is **sidebar implementation strategy**. Two options exist: Chrome's native Side Panel API (`chrome.sidePanel`, available since Chrome 114) or content-script-injected UI with Shadow DOM isolation. The Side Panel API is strongly recommended — it's a dedicated browser surface that doesn't interfere with page CSS, persists across tab navigation, and has full access to Chrome extension APIs. Firefox uses a different but functionally equivalent `sidebar_action` manifest key. The cross-browser gap is manageable with the existing dual-manifest pattern (M014).

The highest risk is **false positives from keyword matching**. Common words in page titles will match too many objects. The context-query endpoint already limits to 20 results, but ranking/relevance scoring on the extension side (URL matches first, then title, then keyword) is needed to make the sidebar useful.

## Recommendation

Use Chrome's native Side Panel API for Chrome and `sidebar_action` for Firefox. Start with the service worker context-query integration and badge — this proves the query pipeline works end-to-end before building UI. Then build the sidebar HTML/JS (shared between Chrome and Firefox), then add in-context actions.

**Build order:** Badge + auto-context query → Sidebar UI with grouped results → In-context actions (Open, Link) → Evidence capture → Settings + E2E tests + docs.

## Implementation Landscape

### Key Files

**Existing (to modify):**
- `extension/manifest.json` — Add `"sidePanel"` permission + `"side_panel"` key with `default_path`. Add `"tabs"` permission (needed for `chrome.tabs.onUpdated` listener).
- `extension/manifest.firefox.json` — Add `"sidebar_action"` manifest key pointing to the same sidebar HTML.
- `extension/background/service-worker.js` — Add tab navigation listener, debounced context-query calls, badge text updates, per-URL result caching, and sidebar communication via `chrome.runtime.sendMessage`.
- `extension/shared/api-client.js` — Already has `searchObjects(query)`. May need a richer version accepting `{url, title, keywords}` separately (current impl passes the same string to both title and keywords).
- `extension/shared/storage.js` — Add new settings keys: `autoCheckContext` (bool, default true), `contextCheckDelay` (number ms, default 2000), `contextTimeout` (number ms, default 500).
- `extension/options/options.html` + `options.js` — Add "Context Overlay" settings section.
- `extension/content/extractor.js` — Already extracts title, URL, description, meta keywords, schema.org. Reuse for context signal extraction.

**New files:**
- `extension/sidebar/sidebar.html` — Side panel HTML shell (header, grouped results, quick capture button).
- `extension/sidebar/sidebar.js` — Receives results from service worker via messaging, renders grouped results, handles in-context actions.
- `extension/sidebar/sidebar.css` — Sidebar styling (shared between Chrome and Firefox, self-contained).

### Architecture: Chrome Side Panel API

```
Tab navigation event (chrome.tabs.onUpdated, status=complete)
    │
    ▼
Service worker: debounce 2s → extract page signals → POST /api/context-query
    │
    ▼
Service worker: cache results per URL → chrome.action.setBadgeText({text: count})
    │
    ▼
User clicks badge → Side Panel opens (chrome.sidePanel.open or sidebar_action.open)
    │
    ▼
sidebar.js: chrome.runtime.sendMessage({type: 'getContextResults'})
    │
    ▼
Service worker: returns cached results for active tab's URL
    │
    ▼
sidebar.js: renders grouped results (Notes, Concepts, Claims, etc.)
```

**Badge behavior:**
- `chrome.action.setBadgeText({text: String(count), tabId})` — per-tab badge count
- `chrome.action.setBadgeBackgroundColor({color: '#0d9488'})` — teal accent matching SemPKM theme
- Badge clears when navigating to a new URL (before new results arrive)
- Badge shows "" (empty) when no results, avoiding "0" clutter

**Result caching:**
- In-memory Map keyed by URL → `{results, timestamp}` in service worker
- Cache entries valid for session (no TTL — page content doesn't change within a session)
- Cache cleared on service worker restart (natural MV3 lifecycle)
- Maximum 100 cached URLs (LRU eviction)

### Cross-Browser Sidebar Strategy

| Feature | Chrome | Firefox |
|---------|--------|---------|
| Manifest key | `"side_panel": {"default_path": "sidebar/sidebar.html"}` | `"sidebar_action": {"default_panel": "sidebar/sidebar.html", "default_title": "SemPKM Context"}` |
| Permission | `"sidePanel"` | None needed (sidebar_action is a manifest key, not a permission) |
| Open programmatically | `chrome.sidePanel.open({windowId})` | `browser.sidebarAction.open()` |
| Badge text | `chrome.action.setBadgeText()` | `browser.action.setBadgeText()` (same API) |
| Persists across tabs | Yes (global side panel) | Yes (sidebar is per-window) |

**Shared code:** `sidebar.html`, `sidebar.js`, `sidebar.css` are identical for both browsers. The service worker uses a small abstraction to call the correct open API.

### In-Context Actions

1. **Open** — `window.open(instanceUrl + '/browser/objects/' + encodeURIComponent(iri))` — opens in new tab.
2. **Link to this page** — Creates a `schema:url` edge from the object to the current page URL. Calls `client.createEdge({source: objectIri, target: pageIri, predicate: 'schema:url'})`. Requires minting a "web page" object first or linking directly to the URL as a literal value. Simpler approach: `client.createObject({type: 'Note', properties: {'dcterms:title': pageTitle, 'schema:url': pageUrl}})` then `client.createEdge(...)`.
3. **Add Evidence** — For Claim objects with no evidence. Opens a mini capture form pre-configured with: type=Evidence, `evidenceType`=supporting, linked to the Claim. User highlights text → creates Evidence object → edge to Claim. This is the most complex action and should be the last slice.

### Build Order

1. **S01 — Service worker context queries + badge** (highest risk: query pipeline, debounce, caching)
   - Prove: navigate to a page with matching content → badge shows count
   - Unblocks: everything else

2. **S02 — Sidebar UI with grouped results** (medium risk: cross-browser sidebar API differences)
   - Prove: click badge → sidebar opens with grouped results → click Open → object opens in SemPKM
   - Unblocks: in-context actions

3. **S03 — In-context actions: Link to page + Add Evidence** (medium risk: multi-step object+edge creation)
   - Prove: click "Link to this page" → edge appears in SemPKM relations panel
   - Prove: click "Add Evidence" → Evidence object created and linked to Claim

4. **S04 — Settings, E2E tests, user guide docs** (low risk: proven patterns from M014)
   - Settings: auto-context toggle, delay, timeout in options page
   - E2E: Playwright tests with persistent context fixture (Chromium-only, matching M014 pattern)
   - Docs: user guide chapter

### Verification Approach

- **Unit verification:** Service worker context query logic testable via Node.js (mock chrome APIs)
- **Integration verification:** Sideload extension, navigate to a page whose URL exists as `schema:url` on a Note in SemPKM → badge shows "1" → open sidebar → Note visible
- **E2E verification:** Playwright persistent context fixture from M014 (`e2e/fixtures/extension.ts`), exercise badge + sidebar + link action against Docker test stack
- **Cross-browser:** Manual Firefox verification with `manifest.firefox.json` (Playwright can't load Firefox extensions)

## Constraints

- **No build step** — Extension is vanilla JS (D169). All new files must be plain JS/HTML/CSS, no imports from npm packages, no bundler.
- **MV3 service worker lifecycle** — Service worker can be terminated at any time. Context cache lives in memory and is lost on termination. This is acceptable — cache is a performance optimization, not correctness requirement.
- **`chrome.sidePanel` requires Chrome 114+** — This is fine; Chrome auto-updates and 114 shipped May 2023.
- **Content script extraction** — `chrome.scripting.executeScript` requires `activeTab` permission (already granted) and a user gesture OR `tabs` permission for background queries. Need to add `tabs` permission to manifest for `chrome.tabs.onUpdated` listener.
- **Badge per-tab** — `setBadgeText` accepts `tabId` for per-tab badges. Without `tabId`, badge is global. Per-tab is correct for this feature.
- **Existing popup must coexist** — Side Panel and popup can coexist. By default, clicking the icon opens the popup. Can use `sidePanel.setPanelBehavior({openPanelOnActionClick: true})` to switch, but this replaces the popup. Better approach: keep popup for capture (Alt+S), use a separate keyboard shortcut (Alt+K) or badge click behavior for sidebar.

## Common Pitfalls

- **Popup vs Side Panel conflict** — `setPanelBehavior({openPanelOnActionClick: true})` replaces the popup action. Do NOT use this. Instead, open the side panel programmatically via context menu, keyboard shortcut (Alt+K via commands), or from within the popup via a "Show Context" button.
- **Service worker termination losing cache** — MV3 service workers shut down after ~30s of inactivity. Cache is ephemeral. Don't try to persist cache to storage (too large, too slow). Accept cache misses — re-query is cheap against a local instance.
- **Firefox sidebar_action auto-opens on install** — Firefox shows the sidebar immediately when the extension is installed. Need to handle the "no results yet" empty state gracefully.
- **CORS on context-query** — Already handled by M013 (nginx CORS headers on `/api/`). No new CORS work needed.
- **`SemPKMClient.searchObjects()` sends same string as both title and keywords** — This works but is suboptimal. For richer context matching, split signals: URL as `url` field, page title as `title` field, meta keywords/description as `keywords` field. Requires a new method or updating `searchObjects()`.
- **Rate limiting on context-query** — The endpoint has no rate limiting currently. Debounce on the client side (2s delay) is sufficient for v1. If needed, add server-side rate limiting later.

## Open Risks

- **False positive noise** — Keyword matching against common words (e.g., "the", "about", "project") may return too many irrelevant results. Mitigation: client-side ranking (URL match > title match > keyword match), truncate to top 10, and show match confidence.
- **Large graph query performance** — Context-query against a graph with 10k+ objects may exceed 500ms timeout. The endpoint already uses LuceneSail FTS (fast) and simple SPARQL FILTER for URL matching (fast). Should be fine for typical personal knowledge bases (<5k objects). Monitor in E2E tests.
- **Evidence capture UX complexity** — The "Add Evidence" flow requires text highlighting + object creation + edge creation, all from the sidebar. This is the most complex action. May need to defer part of it (e.g., highlight-then-capture) to a follow-up if it proves too complex for the sidebar UI.

## Candidate Requirements

Based on M015-CONTEXT.md and the design doc, these should be tracked:

| ID | Description | Notes |
|----|-------------|-------|
| EXT-14 | Context badge shows related object count per tab | Badge updates 2s after page load, cached per URL |
| EXT-15 | Sidebar shows related objects grouped by type | Chrome Side Panel + Firefox sidebar_action |
| EXT-16 | "Open" action opens object in SemPKM tab | Simple navigation link |
| EXT-17 | "Link to this page" creates typed relationship | edge.create via API |
| EXT-18 | "Add Evidence" creates Evidence object linked to Claim | Multi-step: highlight text → create Evidence → edge to Claim |
| EXT-19 | Auto-context configurable (on/off, delay, timeout) | Settings in options page |
| EXT-20 | Per-URL result caching for session | In-memory cache in service worker |
| EXT-21 | Sidebar works in both Chrome and Firefox | Side Panel API + sidebar_action |

EXT-14 through EXT-17 and EXT-19-21 are table stakes for the milestone. EXT-18 (Add Evidence) is the stretch goal — it's valuable but complex. Could be deferred to a follow-up slice if the sidebar + basic actions ship cleanly.

## Sources

- Chrome Side Panel API: `chrome.sidePanel` (developer.chrome.com/docs/extensions/reference/api/sidePanel)
- Firefox sidebar_action: MDN (developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/sidebarAction)
- Shadow DOM for content script isolation: WXT docs, crxjs discussions (not needed if using Side Panel API)
- Existing design: `.gsd/design/BROWSER-EXTENSION-DESIGN.md` Phase 2 section
- Existing API: `backend/app/api/router.py` — context-query endpoint (M013)
- Existing extension: `extension/` directory — 3.7k LOC, vanilla JS, dual manifests
