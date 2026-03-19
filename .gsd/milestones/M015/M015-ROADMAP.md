# M015: Browser Extension Phase 2 — Knowledge Context Overlay

**Vision:** While browsing any web page, the user sees how many related objects exist in their SemPKM knowledge graph (badge count), opens a sidebar showing those objects grouped by type, and takes in-context actions — open, link, or add evidence — without leaving the page.

## Success Criteria

- User navigates to a page whose URL matches a `schema:url` property on a Note — badge shows "1", sidebar shows the Note under its type group
- User navigates to a page whose title keywords match a Concept label — sidebar shows the Concept and any linked objects
- User clicks "Open" on a sidebar result — object opens in a new SemPKM tab
- User clicks "Link to this page" on a sidebar result — a `schema:url` edge is created, visible in SemPKM's relations panel
- User clicks "Add Evidence" on a Claim in the sidebar — highlight text on page, Evidence object created and linked to the Claim
- Badge count appears 2 seconds after page load, cached per URL for the session
- User disables auto-context in settings — badge only appears on manual check (Alt+K or sidebar button)
- Sidebar works in both Chrome (Side Panel API) and Firefox (sidebar_action)

## Key Risks / Unknowns

- **Chrome Side Panel API integration** — First use of `chrome.sidePanel` in the extension. Popup and Side Panel must coexist (clicking icon opens popup; Alt+K opens sidebar). Risk: `setPanelBehavior({openPanelOnActionClick: true})` replaces the popup, which we must NOT do.
- **False positive noise from keyword matching** — Common page title words matching too many objects makes the sidebar useless. Need client-side ranking (URL match > title match > keyword match) and truncation.
- **Service worker lifecycle vs. cache** — MV3 service workers shut down after ~30s of inactivity. In-memory URL→results cache is ephemeral. Acceptable (re-query is cheap) but needs graceful handling.
- **Evidence capture UX complexity** — Highlighting text + creating Evidence object + linking to Claim is a multi-step flow from the sidebar. May require content script injection for text selection capture.

## Proof Strategy

- Side Panel API coexistence → retire in S01 by shipping a working sidebar alongside the existing popup, opened via Alt+K, with badge count from real context queries
- False positive ranking → retire in S01 by implementing client-side result ranking and verifying against real graph data in Docker
- Evidence capture complexity → retire in S02 by building the full highlight → create → link flow

## Verification Classes

- Contract verification: Node.js unit tests for result ranking/grouping logic, service worker cache management
- Integration verification: Sideload extension against Docker test stack — badge + sidebar + actions against real graph data
- Operational verification: Cache lifecycle (populate, hit, evict), debounce timing, timeout handling
- UAT / human verification: Sidebar renders correctly on real-world pages, evidence highlight UX is usable

## Milestone Definition of Done

This milestone is complete only when all are true:

- Badge shows correct count after page load, cached per URL
- Sidebar opens via Alt+K showing grouped results from real graph data
- All three in-context actions work (Open, Link, Add Evidence)
- Auto-context toggle in settings controls badge behavior
- E2E Playwright tests exercise badge + sidebar + link action against Docker stack
- User guide documents the context overlay feature
- Extension works in both Chrome and Firefox

## Requirement Coverage

- Covers: EXT-14 (badge), EXT-15 (sidebar), EXT-16 (open action), EXT-17 (link action), EXT-18 (evidence capture), EXT-19 (auto-context settings), EXT-20 (URL caching), EXT-21 (cross-browser)
- New requirements to register: EXT-14 through EXT-21
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [x] **S01: Context queries, badge count, and sidebar with grouped results** `risk:high` `depends:[]`
  > After this: user navigates to a page, sees badge count after 2s, opens sidebar via Alt+K showing related objects grouped by type, can click "Open" to view any object in SemPKM

- [x] **S02: In-context actions — Link to page and Add Evidence** `risk:medium` `depends:[S01]`
  > After this: user can click "Link to this page" to create an edge (visible in SemPKM relations panel), and click "Add Evidence" on a Claim to highlight text and create a linked Evidence object

- [ ] **S03: Settings, E2E tests, and user guide** `risk:low` `depends:[S01,S02]`
  > After this: auto-context configurable in options page, Playwright E2E tests prove badge + sidebar + link action against Docker stack, user guide Chapter 33 documents the full feature

## Boundary Map

### S01 → S02

Produces:
- `extension/sidebar/sidebar.js` with `renderResults(results)` function and action button click handlers (Open wired, Link/Evidence as stubs)
- `extension/background/service-worker.js` with `getContextResults` message handler returning cached `{results, tabUrl}` for active tab
- `extension/shared/api-client.js` with `contextQuery({url, title, keywords})` method accepting separate fields
- Result ranking logic: URL match results first, then title, then keyword — applied before rendering
- In-memory URL→results cache in service worker with LRU eviction (max 100)

### S01 → S03

Produces:
- Settings keys in `extension/shared/storage.js`: `autoCheckContext` (bool), `contextCheckDelay` (number), `contextTimeout` (number)
- `extension/sidebar/sidebar.html` + `sidebar.css` as self-contained sidebar UI

### S02 → S03

Produces:
- "Link to this page" action calling `client.createEdge()` via service worker relay
- "Add Evidence" action with content script text selection + `client.createObject()` + `client.createEdge()`
- Both actions produce visible toast feedback in sidebar

## Standing Requirements Check

- E2E tests: covered by S03 (Playwright tests against Docker stack)
- User guide docs: covered by S03 (Chapter 33)
