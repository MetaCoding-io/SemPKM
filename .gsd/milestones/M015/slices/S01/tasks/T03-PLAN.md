---
estimated_steps: 7
estimated_files: 3
---

# T03: Build sidebar UI with grouped results and Open action

**Slice:** S01 — Context queries, badge count, and sidebar with grouped results
**Milestone:** M015

## Description

The user-facing sidebar that renders context results grouped by type. Opens via Alt+K (or Firefox sidebar toggle). Communicates with the service worker via `chrome.runtime.sendMessage` to get cached results, then renders them using `groupByType()` from `context-utils.js`.

Three new files: `sidebar.html` (shell), `sidebar.js` (logic), `sidebar.css` (styling). These are self-contained — loaded by Chrome's Side Panel API or Firefox's sidebar_action, both pointing to `sidebar/sidebar.html`.

The sidebar must work without ES module imports in the service worker context. `sidebar.html` CAN use `<script type="module">` since it's a regular HTML page loaded by the browser. But `context-utils.js` uses `globalThis` assignment pattern, so import it via a plain `<script>` tag before the module script, or use `importScripts` indirectly.

**Simplest approach:** Use `<script src="../shared/context-utils.js"></script>` (sets `globalThis.SemPKMContextUtils`) then `<script src="sidebar.js"></script>` (accesses `SemPKMContextUtils` from global scope). No ES modules needed in the sidebar — keeps it consistent with the service worker pattern.

## Steps

1. **Create `extension/sidebar/sidebar.html`:**
   - Standard HTML5 document with `<meta charset="utf-8">`
   - Link to `sidebar.css`
   - SemPKM header bar with logo/title: "SemPKM Context"
   - Main content area with:
     - Loading state: `<div id="loading">` with spinner text "Checking for related objects..."
     - Error state: `<div id="error" hidden>` with error message and "Retry" button
     - Empty state: `<div id="empty" hidden>` with "No related objects found for this page" message
     - Results container: `<div id="results" hidden>` where grouped results render
   - Footer: "Powered by SemPKM" with link to instance
   - Script tags: `<script src="../shared/context-utils.js"></script>` then `<script src="sidebar.js"></script>`

2. **Create `extension/sidebar/sidebar.js`:**
   - On `DOMContentLoaded`, call `init()`
   - `init()`:
     - Send `chrome.runtime.sendMessage({type: 'getContextResults'})` 
     - On response: if `results.length > 0`, call `renderResults(results)`; else show empty state
     - On error: show error state with message
   - `renderResults(results)`:
     - Call `SemPKMContextUtils.groupByType(results)` to get type groups
     - For each group, create a section: type label heading with count badge + result items
     - Each result item is a card with:
       - Object label (clickable — same as "Open" action)
       - Match type badge: small colored pill — "URL" (green), "Title" (blue), "Keyword" (gray)
       - Snippet text (if present, truncated to 120 chars)
       - Action bar with 3 buttons:
         - "Open" — `chrome.tabs.create({url: instanceUrl + '/browser/objects/' + encodeURIComponent(iri)})` (need to read `instanceUrl` from `chrome.storage`)
         - "Link to page" — shows toast "Coming in next update" (stub for S02)
         - "Add Evidence" — shows toast "Coming in next update" (stub for S02)
     - Type group sections are collapsible (click header to toggle)
   - `showToast(message)` — simple toast notification, auto-dismiss after 3s
   - Listen for `chrome.runtime.onMessage` with `{type: 'contextResultsUpdated'}` → re-render results
   - Read `instanceUrl` from `chrome.storage` on init (needed for "Open" links)

3. **Implement "Open" action:**
   - On click: `chrome.tabs.create({url: instanceUrl + '/browser/objects/' + encodeURIComponent(result.iri)})`
   - If `instanceUrl` is not configured, show error toast "Configure SemPKM instance in extension settings"

4. **Implement stub actions:**
   - "Link to page" button: `showToast('Link to page — coming in next update')`
   - "Add Evidence" button: `showToast('Add Evidence — coming in next update')`
   - Both buttons styled but with subtle "coming soon" indicator (slightly muted color or dashed border)

5. **Create `extension/sidebar/sidebar.css`:**
   - CSS variables matching SemPKM theme: `--accent: #0d9488` (teal), `--bg: #1a1a2e` (dark), `--surface: #252540`, `--text: #e2e8f0`, `--text-muted: #94a3b8`
   - Header bar: accent gradient background, white text, compact (40px height)
   - Type group sections: collapsible with chevron rotation animation
   - Result cards: surface background, 1px border, rounded, compact padding (8px 12px)
   - Match type badges: small pills — URL green, Title blue, Keyword gray
   - Action buttons: icon-only or compact text, flex row, no border, hover reveals
   - Empty/error states: centered, muted text, icon
   - Toast: fixed bottom-right, accent background, white text, fade out
   - Loading spinner: simple CSS animation (pulsing dot or rotating ring)
   - Responsive: sidebar width varies (250-400px), ensure content wraps gracefully
   - Scrollable results area with `overflow-y: auto`

6. **Handle edge cases:**
   - Sidebar opened before any navigation → show empty state with "Navigate to a page to see related objects"
   - Service worker not responding (terminated) → show error with "Retry" button that re-sends message
   - Very long labels → truncate with ellipsis via CSS `text-overflow: ellipsis`
   - Large result counts (10 items max from ranking, but type groups may have 1-10 items each)

7. **Verify syntax:**
   - `node --check extension/sidebar/sidebar.js` passes

## Must-Haves

- [ ] `sidebar.html` loads correctly as Chrome Side Panel and Firefox sidebar
- [ ] Results render grouped by type with count in section header
- [ ] Each result shows label, match type badge, snippet (if present), and 3 action buttons
- [ ] "Open" navigates to the object in SemPKM in a new tab
- [ ] "Link to page" and "Add Evidence" show "coming soon" toast (stubs for S02)
- [ ] Loading, empty, and error states all handled
- [ ] Auto-refreshes when service worker sends `contextResultsUpdated`

## Verification

- `node --check extension/sidebar/sidebar.js` exits 0
- Sideload extension against Docker test stack → navigate to page with matching URL → Alt+K opens sidebar → results render grouped by type → match type badges visible → click "Open" → object opens in new SemPKM tab
- Click "Link to page" → toast appears → no errors

## Inputs

- `extension/shared/context-utils.js` — T02's `groupByType()` function (accessed via `SemPKMContextUtils.groupByType`)
- `extension/background/service-worker.js` — T02's message handler responding to `{type: 'getContextResults'}` with `{results, url}`
- `extension/shared/storage.js` — `getSettings()` for reading `instanceUrl`
- SemPKM teal accent color: `#0d9488`. Dark theme colors from existing popup.css for reference.

## Expected Output

- `extension/sidebar/sidebar.html` — self-contained sidebar shell
- `extension/sidebar/sidebar.js` — result rendering, messaging, "Open" action, stub actions
- `extension/sidebar/sidebar.css` — dark theme styling matching SemPKM brand
