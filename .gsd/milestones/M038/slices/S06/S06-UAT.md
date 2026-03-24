# S06 UAT — Stats Dashboard + Polish

## Preconditions

- Media Scheduler app installed and running in Docker
- At least one media source (podcast, YouTube, or Spotify) subscribed
- At least 3 MediaItems with `entryStatus: "completed"` across different source types
- At least 1 MediaItem with `entryStatus: "skipped"` and 1 with `entryStatus: "saved"`
- basic-pkm and media-scheduler Mental Models installed

---

## Test Cases

### TC-01: Stats Tab Navigation

1. Open the Media Scheduler app from the Apps sidebar section
2. Verify the navigation bar shows tabs: Today, Sources, Rules, **Stats**
3. Click the **Stats** tab
4. **Expected:** The stats dashboard loads with three chart sections visible
5. **Expected:** The Stats tab button shows the `bar-chart-3` Lucide icon
6. **Expected:** No JavaScript errors in browser console

### TC-02: Hours by Source Type Chart

1. Navigate to the Stats tab
2. Locate the "Hours by Source Type" chart card
3. **Expected:** A horizontal bar chart displays with bars for each source type that has completed items (e.g., "podcast", "youtube", "spotify")
4. **Expected:** Bar values represent hours (decimal), not raw duration counts
5. **Expected:** Source types with zero completed items do not appear

### TC-03: Top Sources Chart

1. Navigate to the Stats tab
2. Locate the "Top Sources" chart card
3. **Expected:** A horizontal bar chart displays the top 10 most-played sources by title
4. **Expected:** Sources are ordered by play count descending
5. **Expected:** Each bar label shows the source title, not an IRI

### TC-04: Weekly Activity Trend Chart

1. Navigate to the Stats tab
2. Locate the "Weekly Activity" chart card
3. **Expected:** A line chart with filled area displays 7 data points (one per day)
4. **Expected:** Days with no completed items show as 0 (continuous line, no gaps)
5. **Expected:** X-axis labels are dates in chronological order (oldest → newest)

### TC-05: Empty Stats State

1. Install the media-scheduler model fresh (no completed items)
2. Navigate to the Stats tab
3. **Expected:** All three chart areas render without errors
4. **Expected:** Charts show "No data" or empty visualization (no blank white space, no JS errors)

### TC-06: Stats Resilience on Query Failure

1. Navigate to the Stats tab while the triplestore is temporarily unreachable
2. **Expected:** The page renders (HTTP 200, not 500)
3. **Expected:** Charts show empty states
4. **Expected:** App container logs show `stats.<function_name> query failed:` warnings

### TC-07: Status Badge Visual Polish — Completed

1. Open the Today tab with a completed media item visible
2. **Expected:** The "completed" badge has a green background with border
3. **Expected:** Badge text is readable with sufficient contrast

### TC-08: Status Badge Visual Polish — Skipped

1. Open the Today tab with a skipped media item visible
2. **Expected:** The "skipped" badge has an amber/orange background with border
3. **Expected:** Visually distinct from the completed (green) badge

### TC-09: Status Badge Visual Polish — Saved

1. Open the Today tab with a saved media item visible
2. **Expected:** The "saved" badge has a blue background with border
3. **Expected:** Visually distinct from both completed (green) and skipped (amber) badges

### TC-10: Action Button Hover Effect

1. Hover over any action button (complete, skip, save) on a media item in the Today view
2. **Expected:** Button scales up slightly (1.08×) with a subtle box-shadow
3. **Expected:** Transition is smooth (not instant snap)

### TC-11: User Guide Chapter 49 Exists and Is Linked

1. Navigate to `/guide` in the app (Docs & Tutorials page)
2. Scroll to the Media Scheduler entry in the sidebar/list
3. **Expected:** "Media Scheduler" chapter appears in the guide navigation
4. Click it
5. **Expected:** Chapter loads with sections covering: prerequisites, installation, adding sources, schedule rules, today's plan, stats dashboard, mobile integration, troubleshooting

### TC-12: User Guide Covers All Source Types

1. Open chapter 49 of the user guide
2. **Expected:** Podcast source setup documented (RSS feed URL)
3. **Expected:** YouTube source setup documented (API key + channel/playlist URL)
4. **Expected:** Spotify source setup documented (OAuth PKCE flow)

### TC-13: Stats Data Inspection

1. Open browser DevTools Network tab
2. Navigate to the Stats tab
3. Inspect the response for `/_fragments/stats`
4. **Expected:** Response contains embedded JSON with `hours_by_type`, `top_sources`, and `weekly_trends` keys
5. **Expected:** JSON values are arrays of objects with expected fields (e.g., `source_type`, `hours` for hours_by_type)

---

## Edge Cases

### EC-01: Stats with Single Source Type Only
- Add only podcast sources, complete several episodes
- **Expected:** Hours chart shows one bar (podcast), Top Sources shows podcast names only, Weekly chart shows podcast completion counts

### EC-02: Stats After Bulk Completions
- Mark 15+ items as completed in rapid succession
- Navigate to Stats tab
- **Expected:** Charts reflect all completions accurately, no truncation besides top-10 limit on sources

### EC-03: Chart.js CDN Unavailable
- Block `cdn.jsdelivr.net` in browser devtools or network settings
- Navigate to Stats tab
- **Expected:** Charts fail to render but page does not crash — the template's lazy-load pattern logs an error
