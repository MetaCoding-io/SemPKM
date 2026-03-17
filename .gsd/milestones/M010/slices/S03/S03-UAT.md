# S03: Reader UI (split-pane layout) — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for structure, live-runtime for interactivity)
- Why this mode is sufficient: The reader UI is htmx fragment-driven — static artifact checks confirm template/CSS/JS structure, but star/read toggles and markdown rendering require a live Docker stack to validate end-to-end.

## Preconditions

- Docker stack running (`docker compose up -d`)
- `rss-feeds` Mental Model installed (Admin > Mental Models)
- `rss-reader` app installed and running (Admin > Applications, status: running)
- At least 1 feed subscribed with ≥3 articles ingested (use Subscribe dialog or S02's subscribe endpoint)
- Browser open to the RSS Reader page (via [Apps] sidebar section)

## Smoke Test

Navigate to the RSS Reader page. Verify a three-panel layout appears: feed sidebar on the left, article list in the center, and a reading pane (or placeholder) on the right.

## Test Cases

### 1. Feed sidebar loads with subscriptions

1. Open the RSS Reader page
2. Observe the left sidebar panel
3. **Expected:** Feed sidebar shows at least one feed subscription with its title. Each feed shows an unread count badge (may be 0). A "Subscribe" button appears at the bottom.

### 2. Feed sidebar unread counts are accurate

1. Note the unread count displayed next to a feed in the sidebar
2. Click that feed to filter the article list
3. Switch to the "Unread" filter tab in the article list
4. Count the listed articles
5. **Expected:** The count of articles in the unread list matches the unread badge in the sidebar.

### 3. Article list loads and filters by feed

1. In the sidebar, click "All Feeds" (top item)
2. Observe the article list in the center panel
3. **Expected:** All articles from all feeds appear, sorted newest first. Each article shows title, source name, and date.
4. Click a specific feed in the sidebar
5. **Expected:** Article list updates to show only articles from that feed.

### 4. Filter tabs work (All / Unread / Starred)

1. Click the "All" filter tab above the article list
2. **Expected:** All articles for the current feed (or all feeds) are shown.
3. Click the "Unread" tab
4. **Expected:** Only unread articles appear (bold/prominent styling).
5. Click the "Starred" tab
6. **Expected:** Only starred articles appear (or empty state if none starred).

### 5. Reading pane displays article content

1. Click any article in the article list
2. Observe the right reading pane
3. **Expected:** Article title, author (if available), publication date, and a link to the original article appear in the header. Below, the article body renders as formatted markdown (paragraphs, headings, code blocks, blockquotes styled properly). No raw markdown syntax visible.

### 6. Star toggle works

1. Open an article in the reading pane
2. Find the star button (star icon near the article header)
3. Click the star button
4. **Expected:** Star icon changes to filled/active state. No page reload — the button replaces itself inline.
5. Click the star button again
6. **Expected:** Star icon returns to outline/inactive state.
7. Reload the page and navigate back to the same article
8. **Expected:** Star state persists — if you left it starred, it's still starred.

### 7. Mark-as-read fires on article open

1. Find an unread article in the article list (bold title or visible unread indicator)
2. Click it to open in the reading pane
3. **Expected:** After a moment, the article's unread indicator in the list disappears — it's now marked as read. The unread count in the sidebar decreases by 1.

### 8. Mark-all-read for a feed

1. Select a feed in the sidebar that has unread articles (badge > 0)
2. Find and click the "Mark all read" action for that feed
3. **Expected:** Sidebar refreshes with unread count for that feed at 0. All articles in the list for that feed now show as read.

### 9. Unsubscribe from a feed

1. Select a feed in the sidebar
2. Find and click the "Unsubscribe" action
3. **Expected:** The feed disappears from the sidebar. Sidebar refreshes. Articles from that feed are no longer listed.

### 10. Unread Articles workspace view

1. Navigate to the workspace Views section
2. Open "Unread Articles" view
3. **Expected:** A list of unread articles appears, equivalent to the reader's article list with the "Unread" filter active.

### 11. Starred Articles workspace view

1. Star at least one article in the reader
2. Navigate to the workspace Views section
3. Open "Starred Articles" view
4. **Expected:** A list of starred articles appears, matching what the "Starred" filter tab shows.

### 12. Reading pane body fallback

1. If available, find an article where the feed only provided a summary (no full content extraction)
2. Open it in the reading pane
3. **Expected:** The description/summary text appears. If no content at all, a message like "No content available" with a link to the original article is shown.

## Edge Cases

### No subscriptions

1. If no feeds are subscribed, open the RSS Reader page
2. **Expected:** Feed sidebar shows an empty state message (e.g., "No feeds yet") with the Subscribe button still visible. Article list shows an empty state. Reading pane shows a placeholder.

### Feed with errors

1. Subscribe to a feed URL that returns 404 or invalid XML
2. Wait for a poll cycle
3. **Expected:** Feed appears in sidebar with an error indicator (red dot or warning icon). Hovering shows error text. The app does not crash.

### Keyboard navigation

1. With the article list focused, press `j`
2. **Expected:** Selection moves to the next article in the list
3. Press `k`
4. **Expected:** Selection moves to the previous article
5. At the last article, press `j`
6. **Expected:** Selection wraps to the first article

### Query-string preservation through proxy

1. In browser DevTools Network tab, observe requests when clicking feeds
2. **Expected:** Fragment requests like `/_fragments/article-list?feed_iri=...&filter=unread` include query parameters (not stripped). Response contains filtered content.

## Failure Signals

- Three-panel layout collapses to single column or panels overlap — CSS Grid issue
- Clicking a feed doesn't filter the article list — query-string forwarding bug or missing hx-get params
- Article body shows raw markdown syntax instead of formatted text — reader.js not loaded or renderMarkdownBody() not firing
- Star click produces no visual change — HX-Trigger not emitting or star-button.html not swapping
- Unread count in sidebar doesn't change after reading articles — articleStateChanged event not triggering sidebar refresh
- Browser console shows `renderMarkdownBody is not defined` — platform markdown-render.js not loaded
- 404 or 500 errors in Network tab for `/_fragments/*` requests — route handlers missing or SPARQL query failure

## Requirements Proved By This UAT

- **RSS-02** — Reader UI with split-pane layout: full layout, star toggle, mark read/unread
- **RSS-01** (partial) — Unsubscribe handler, error indicators per feed
- **RSS-06** (partial) — Unread Articles and Starred Articles workspace views

## Not Proven By This UAT

- **RSS-03** — Custom object renderer for Article (opening article from object browser) — S04
- **RSS-04** — Hypothesis sync — deferred to M011
- **RSS-05** — OPML import — S05
- **RSS-06** (remainder) — Command palette entries, Related Articles right pane — S04
- **RSS-08** — Feed discovery from website URLs — S02 (already complete)
- Automated E2E test coverage — S06

## Notes for Tester

- The proxy query-string fix is platform-wide — if you notice other apps' parametrized requests working better after this, that's expected.
- The reading pane markdown rendering relies on the platform's `markdown-render.js` being loaded. If you see raw markdown, check the browser console for errors related to `renderMarkdownBody`.
- Unread/starred workspace views are thin htmx wrappers — they load the same fragment endpoint as the reader's filter tabs but outside the reader's three-panel layout.
- The star button uses inline SVG (not Lucide icons) to avoid flash-of-unstyled-content during htmx swap.
- j/k keyboard navigation only works when no text input is focused (search fields, etc.).
