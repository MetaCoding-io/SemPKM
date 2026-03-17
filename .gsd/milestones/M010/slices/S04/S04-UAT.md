# S04: Workspace contributions + custom renderer — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for contract verification + live-runtime for integration)
- Why this mode is sufficient: Unit tests verify SPARQL structure, template args, and response branching. Live runtime needed to confirm right pane rendering, custom renderer dispatch, command palette behavior, and dockview tab opening — all deferred to S06 E2E.

## Preconditions

- Docker stack running (`docker compose up -d`)
- `rss-feeds` Mental Model installed (from S01)
- `rss-reader` app installed and running (from S01)
- At least one feed subscribed with articles present (from S02/S03)
- At least one article exists in the triplestore

## Smoke Test

Open the workspace, press Ctrl+K, type "Mark All as Read" — the command should appear. Execute it and see a confirmation message (not a sidebar HTML fragment).

## Test Cases

### 1. Related Articles in Right Pane

1. Open any object in the object browser (e.g., a Note or Concept)
2. Look at the right pane sections
3. **Expected:** A "RELATED ARTICLES" section appears (may show "No related articles found" if the object shares no tags or feed source with any article)

### 2. Related Articles with Matching Tags

1. Create or find an object that shares a `bpkm:tags` value with at least one article
2. Open that object in the object browser
3. Look at the "RELATED ARTICLES" section in the right pane
4. **Expected:** Articles with matching tags appear as clickable items with title, date, and feed source. Maximum 10 articles shown. The focused object itself does NOT appear in the list.

### 3. Custom Article Read Renderer

1. Navigate to the object browser
2. Find an `rss:Article` object (e.g., via Table View filtered to Article type, or via Ctrl+K search)
3. Click to open the article
4. **Expected:** The article displays in a clean reader layout with title, author, date, body (markdown-rendered), and a star button. It does NOT show the default SHACL form with raw property fields.

### 4. Star Button in Custom Renderer

1. Open an article via the object browser (custom renderer)
2. Click the star button
3. Reload the page
4. **Expected:** Star state persists — the star button shows the correct filled/unfilled state matching the toggled value.

### 5. Mark All as Read via Command Palette

1. Press Ctrl+K to open the command palette
2. Type "Mark All as Read"
3. Select the command
4. **Expected:** A confirmation message appears showing "Marked N articles as read" (with the actual count). The message has a green success style (not a sidebar HTML fragment). Unread counts in the reader sidebar update.

### 6. Open RSS Reader via Command Palette (Dockview Tab)

1. Press Ctrl+K to open the command palette
2. Type "Open RSS Reader"
3. Select the command
4. **Expected:** The RSS Reader opens as a new dockview tab within the workspace. The URL bar does NOT change to `/app/rss-reader/reader`. The workspace SPA remains intact with all other tabs still accessible.

### 7. Navigate Command JSON Enrichment

1. Open browser DevTools → Network tab
2. Trigger the command palette (Ctrl+K)
3. Find the `/api/apps/commands` request
4. Inspect the JSON response
5. **Expected:** The "Open RSS Reader" entry includes `appId: "rss-reader"` and `pageId: "reader"` fields alongside the existing `actionType: "navigate"` and `actionUrl`.

## Edge Cases

### Empty Right Pane (No Related Articles)

1. Open an object that shares no tags and no feed source with any article
2. Look at the "RELATED ARTICLES" section
3. **Expected:** Shows "No related articles found" empty state (not an error)

### Missing Article IRI in Renderer

1. Manually navigate to the article renderer fragment endpoint without an IRI parameter (e.g., `GET /app/rss-reader/_fragments/article-read-renderer`)
2. **Expected:** Returns an error message "Missing article IRI" — not a server crash

### Mark All as Read with Zero Unread

1. Mark all articles as read first
2. Then use Ctrl+K → "Mark All as Read" again
3. **Expected:** Shows "Marked 0 articles as read" — no error, no crash

### SPARQL Error in Related Articles

1. If triplestore is temporarily unavailable, open an object
2. **Expected:** The right pane shows "Failed to load related articles: ..." error message with `rss-error` styling — not a page crash

## Failure Signals

- Right pane shows no "RELATED ARTICLES" section → manifest `rightPane` contribution not being read by platform
- Article opens with SHACL form instead of reader layout → `objectRenderers` not being dispatched by `_get_renderer_override()`
- "Open RSS Reader" navigates away from workspace (URL changes) → JS `openAppPageTab()` dispatch not firing, falling through to `window.location.href`
- "Mark All as Read" from command palette returns sidebar HTML → HX-Target detection failing (target changed or header not forwarded)
- Related articles shows articles including the focused object itself → self-exclusion FILTER not working

## Requirements Proved By This UAT

- RSS-03 (partial) — Custom Article read renderer replaces default SHACL form when opening an article from the object browser
- RSS-06 (partial) — "Related Articles" in right pane, "Mark All as Read" and "Open RSS Reader" command palette entries functional

## Not Proven By This UAT

- RSS-03 (oa:Annotation renderer) — deferred to M011 with RSS-04
- RSS-06 ("Subscribe to Feed..." command palette entry) — already verified in S03
- Full E2E automation — deferred to S06
- Performance under load (many articles in related-articles query)

## Notes for Tester

- The custom renderer is only triggered when opening an `rss:Article` type object. Other types still show the default SHACL form — this is correct behavior.
- The "Related Articles" section queries by both feedSource and tags (UNION). If your test articles share neither with the focused object, the section will correctly show empty state.
- The navigate fix (dockview tab) is a platform-wide change — it affects ALL apps with navigate commands, not just RSS Reader. If another app is installed with navigate commands, verify those also open as tabs.
- Mark-all-read returns different responses based on context: from command palette → confirmation div; from reader UI sidebar → refreshed sidebar HTML. Test both paths.
