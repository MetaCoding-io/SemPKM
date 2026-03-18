# S03: Reader UI (split-pane layout) — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for templates/CSS + live-runtime for Docker UI verification)
- Why this mode is sufficient: Route handler logic is proven by 56 unit tests. Live runtime needed for typography, layout, and htmx swap behavior which can't be tested with mocked contexts.

## Preconditions

- Docker stack running (`docker compose -f docker-compose.test.yml up -d`)
- `rss-feeds` Mental Model installed via Admin > Mental Models
- `rss-reader` app installed via Admin > Applications
- At least one feed subscription created (e.g. https://hnrss.org/frontpage or similar)
- `poll-feeds` task has run at least once (articles exist in triplestore)

## Smoke Test

Navigate to the RSS Reader page (sidebar > Apps > RSS Reader). Confirm: three-panel layout visible (feed sidebar left, article list center, reading pane right). At least one feed appears in the sidebar with an unread count badge.

## Test Cases

### 1. Three-panel layout renders correctly

1. Navigate to RSS Reader page
2. Inspect layout: sidebar (left, ~240px), article list (center, ~320px), reading pane (right, fills remaining space)
3. **Expected:** CSS Grid layout with three distinct panels. No overlapping content. Theme colors match workspace (dark/light mode).

### 2. Feed sidebar shows subscriptions with unread counts

1. Look at feed sidebar panel
2. Verify "All Feeds" item appears at top
3. Verify each subscribed feed shows its title
4. **Expected:** Each feed with unread articles shows a badge with the unread count (e.g. "12"). Feeds with zero unread articles show no badge. If a feed has errors, an orange/red error indicator dot appears.

### 3. Click feed to filter article list

1. Click a specific feed in the sidebar
2. Observe the article list panel
3. **Expected:** Article list shows only articles from that feed. Feed item in sidebar gets active highlight. Filter tabs (All/Unread/Starred) appear above article list.

### 4. Click "All Feeds" to show all articles

1. Click "All Feeds" at top of feed sidebar
2. **Expected:** Article list shows articles from all feeds, sorted by date (newest first).

### 5. Article list filter tabs work

1. Click "Unread" filter tab
2. **Expected:** Only unread articles shown
3. Click "Starred" filter tab
4. **Expected:** Only starred articles shown
5. Click "All" filter tab
6. **Expected:** All articles shown regardless of read/starred state

### 6. Click article to open reading pane

1. Click any article in the article list
2. Observe the reading pane (right panel)
3. **Expected:** Reading pane shows article title (large heading), author name, publication date, link to original article, and the article body rendered as formatted HTML (not raw markdown). If no body content available, shows description or "No content available" with link to original.

### 7. Article auto-marks as read on open

1. Note an unread article (bolder text / higher opacity in article list)
2. Click to open it in reading pane
3. **Expected:** After ~1 second, the article's visual state in the list changes to read (lighter/dimmer). Unread count in sidebar decreases by 1.

### 8. Star toggle works

1. Open an article in the reading pane
2. Click the star button (outline star icon)
3. **Expected:** Star icon fills in (solid star). Click again → star unfills (outline). State persists across page reload.

### 9. Mark All Read for a feed

1. Select a feed with multiple unread articles
2. Look for "Mark all read" button/action in the feed sidebar or article list
3. Click it
4. **Expected:** All articles in that feed become read. Unread count in sidebar drops to 0. Article list items change to read visual state.

### 10. Unsubscribe from a feed

1. Right-click or find unsubscribe action for a feed
2. Confirm unsubscribe
3. **Expected:** Feed disappears from sidebar. Its articles may still appear in "All Feeds" but no new articles will be fetched. Sidebar refreshes.

### 11. Unread Articles workspace view

1. Navigate to Views section in workspace sidebar
2. Open "Unread Articles" view
3. **Expected:** Shows all unread articles across all feeds with title, date, source info

### 12. Starred Articles workspace view

1. Navigate to Views section in workspace sidebar
2. Open "Starred Articles" view
3. **Expected:** Shows only articles where star is toggled on

### 13. Empty states render gracefully

1. If you have no feeds, navigate to RSS Reader
2. **Expected:** Feed sidebar shows "No feeds yet" message with subscribe CTA. Article list shows appropriate empty message. Reading pane shows "Select an article to read" placeholder.

### 14. Markdown rendering quality

1. Open an article with rich content (headings, links, code blocks, lists)
2. **Expected:** Markdown renders as formatted HTML with proper typography. Links are clickable. Code blocks have monospace font. Lists are indented properly.

### 15. Keyboard navigation (j/k)

1. Focus the RSS Reader page
2. Press `j` key
3. **Expected:** Next article in list is selected/highlighted
4. Press `k` key
5. **Expected:** Previous article is selected

## Edge Cases

### Feed with errors

1. Subscribe to an invalid feed URL (e.g. https://example.com/nonexistent-feed)
2. Wait for a poll cycle
3. **Expected:** Feed appears in sidebar with error indicator dot. Error does not crash the app or prevent other feeds from loading.

### Very long article body

1. Open an article with extensive content (thousands of words)
2. **Expected:** Reading pane scrolls independently. No layout overflow into adjacent panels.

### Article with no body content

1. If a feed provides summary-only entries (no full content)
2. **Expected:** Reading pane shows the summary/description text with a "Read original" link to the article URL.

### Special characters in article titles

1. Open articles with special characters in titles (ampersands, quotes, unicode)
2. **Expected:** Titles render correctly without HTML entity escaping issues.

## Failure Signals

- **Three panels not visible** → CSS Grid not loading; check that styles.css is served via nginx app-static
- **Feed sidebar empty despite subscriptions existing** → SPARQL query failing; check browser Network tab for `/_fragments/feed-sidebar` response (should be 200 with HTML, not 502/404)
- **Articles list stays empty after clicking feed** → Query string not forwarding; check that `?feed_iri=...` appears in Network tab request to `/_fragments/article-list`
- **Star click does nothing** → Check Network tab for POST to `/_fragments/toggle-star`; check for `HX-Trigger: articleStateChanged` in response headers
- **Raw markdown visible in reading pane** → reader.js not loaded or `renderMarkdownBody()` failing; check browser console for errors
- **Unread count doesn't update after reading** → Fire-and-forget mark-read hidden div not triggering; check Network tab for POST to `/_fragments/toggle-read`

## Requirements Proved By This UAT

- **RSS-02** — Full split-pane reader UI with all controls (if all test cases pass in live Docker)

## Not Proven By This UAT

- **RSS-03** — Custom renderer when opening Article from object browser (S04 scope)
- **RSS-06** — Command palette entries and right-pane related articles (S04 scope)
- **RSS-01** — Feed polling reliability under real conditions (operational, not UI)
- **Performance** under large feed counts (100+ feeds, 10K+ articles)

## Notes for Tester

- The proxy query-string fix is critical — if parametrized fragment requests fail, nothing after the initial page load will work. Verify by watching Network tab.
- Styles are scoped under `.rss-reader` — if they bleed into the workspace, that's a bug.
- reader.js relies on the global `renderMarkdownBody()` function from `markdown-render.js`. If that script isn't loaded in the platform shell, markdown will appear raw.
- Star button uses inline SVG, not Lucide icon replacement — it should render immediately without waiting for `lucide.createIcons()`.
- The `j`/`k` keyboard navigation only works when focus is within the reader container, not when other UI elements are focused.
