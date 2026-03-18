# S03: Reader UI (split-pane layout) — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven unit tests + live-runtime Docker verification)
- Why this mode is sufficient: Unit tests verify route logic and SPARQL query construction; Docker stack needed for visual layout, markdown rendering, and htmx fragment loading.

## Preconditions

- Docker stack running (`docker compose up -d` from worktree root)
- `rss-feeds` model installed (Admin > Mental Models > Install)
- `rss-reader` app installed (Admin > Applications > Install)
- At least 1 feed subscription created (or use subscribe dialog)
- At least 1 poll cycle completed (articles exist in triplestore)

## Smoke Test

Navigate to the RSS Reader page (Apps > RSS Reader in sidebar). The page should show a three-panel layout: feed sidebar on the left, article list in the center, and a "Select an article to read" placeholder in the reading pane on the right.

## Test Cases

### 1. Feed sidebar loads with subscriptions

1. Navigate to Apps > RSS Reader
2. Observe the left sidebar panel
3. **Expected:** Feed sidebar shows subscribed feeds with titles. Each feed with unread articles shows an unread count badge (e.g. "12" in a small pill). The "Subscribe" button is visible at the bottom.

### 2. Article list loads and filters by feed

1. Click "All Feeds" in the feed sidebar
2. Observe the center panel
3. **Expected:** Article list shows articles from all feeds with title, date ("Mar 17, 2026" format), source name, and read/unread visual distinction (unread articles have bolder text or different opacity).
4. Click a specific feed in the sidebar
5. **Expected:** Article list updates to show only articles from that feed. The URL in DevTools Network tab shows `/_fragments/article-list?feed_iri=<iri>`.

### 3. Filter tabs (All / Unread / Starred)

1. Click the "Unread" filter tab above the article list
2. **Expected:** Only unread articles are shown. The "Unread" tab has active styling.
3. Click the "Starred" filter tab
4. **Expected:** Only starred articles are shown. If none are starred, an empty state message appears.
5. Click "All" to return to the full list
6. **Expected:** All articles visible again.

### 4. Reading pane displays article content

1. Click an article in the article list
2. **Expected:** Reading pane shows article title, author, date, and a link to the original article. The body is rendered as formatted markdown (headings, bold, links rendered). If no body exists, the description or "No content available" with a link to the original is shown.

### 5. Star toggle persists

1. Click the star button on an article in the reading pane
2. **Expected:** Star icon changes from outline to filled (or vice versa). The `HX-Trigger: articleStateChanged` header is present in Network tab response.
3. Reload the page
4. Navigate back to the same article
5. **Expected:** Star state persists — the article shows the state you set.

### 6. Mark-as-read on article open

1. Note an unread article in the list (bolder styling)
2. Click the unread article to open it
3. **Expected:** The article's visual state in the list changes to "read" (lighter styling). In Network tab, a POST to `/_fragments/toggle-read` fires automatically with `hx-trigger="load"`.
4. Check the feed sidebar — the unread count should decrease by 1.

### 7. Mark all read for a feed

1. Navigate to a feed with multiple unread articles
2. Click "Mark all read" (if visible in the feed item's context menu or UI)
3. **Expected:** All articles in that feed switch to read state. The unread count badge on the feed drops to 0. The feed sidebar refreshes.

### 8. Unsubscribe from a feed

1. Click the unsubscribe button/action on a feed
2. **Expected:** The feed disappears from the sidebar. `HX-Trigger: feedsChanged` header present in response. Articles from that feed may still appear in "All" view (they aren't deleted).

### 9. Workspace views — Unread Articles

1. Navigate to Views > Unread Articles (workspace sidebar)
2. **Expected:** Shows a list of all unread articles across all feeds, using the same article list format as the reader.

### 10. Workspace views — Starred Articles

1. Navigate to Views > Starred Articles (workspace sidebar)
2. **Expected:** Shows only starred articles. If none are starred, shows an appropriate empty state.

### 11. Proxy query-string forwarding

1. Open DevTools Network tab
2. Click a feed in the sidebar
3. **Expected:** The request to `/_fragments/article-list` includes `?feed_iri=<iri>` in the URL. The response is not empty/error (query string was forwarded to the app process).

## Edge Cases

### No feeds subscribed

1. Install the RSS Reader with no feed subscriptions
2. Navigate to RSS Reader page
3. **Expected:** Feed sidebar shows "No feeds yet — subscribe to get started" empty state. Article list shows "Subscribe to a feed to see articles here". Reading pane shows "Select an article to read".

### Feed with errors

1. Subscribe to an invalid/broken feed URL
2. After a poll cycle, check the feed sidebar
3. **Expected:** The feed shows a small error indicator (red dot or warning icon) next to its name. The feed still appears in the list (not hidden).

### Article with no body or description

1. If a feed provides entries with no body/summary
2. Click such an article
3. **Expected:** Reading pane shows the article title/metadata and "No content available" with a link to the original URL.

### Keyboard navigation (j/k)

1. Focus the article list (click on any article item)
2. Press `j` key
3. **Expected:** Selection moves to the next article
4. Press `k` key
5. **Expected:** Selection moves to the previous article

## Failure Signals

- 404/502 responses in Network tab for `/_fragments/*` endpoints — routes not wired or proxy broken
- Raw markdown visible in reading pane instead of rendered HTML — reader.js not loaded or renderMarkdownBody() failed
- Unread counts not updating after mark-read/mark-all-read — HX-Trigger headers missing or feedsChanged event not dispatched
- "rss-error" class divs appearing — SPARQL query failures (check backend logs)
- All articles showing as read on initial load — isRead default value issue
- Star state not persisting across reload — object.patch not executing or SPARQL query returning stale data

## Requirements Proved By This UAT

- **RSS-02** — Reader UI with split-pane layout, clean typography, star toggle, mark read/unread controls

## Not Proven By This UAT

- **RSS-03** — Custom Article renderer in object browser (S04 scope)
- **RSS-06** — Command palette entries and right-pane contributions (S04 scope)
- **RSS-05** — OPML import (S05 scope)
- End-to-end install → subscribe → poll → read lifecycle (S06 E2E tests)

## Notes for Tester

- The reader UI is an app fragment — it loads inside the platform's page shell. If the app isn't running, you'll see a 502 error.
- Star button uses inline SVG, not Lucide icons — it won't be affected by Lucide loading issues.
- Mark-as-read fires automatically on article open via a hidden htmx element. You won't see a visible button for this — check Network tab for the POST request.
- The `j/k` keyboard navigation only works when the article list area has focus.
- Filter tab state is preserved via query params, not localStorage — refreshing the page resets to "All".
