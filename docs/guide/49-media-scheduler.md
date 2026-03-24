# Chapter 49: Media Scheduler

The **Media Scheduler** is a first-party SemPKM application for managing podcast episodes, YouTube videos, and Spotify tracks. It polls your subscribed sources for new content, stores episodes as typed objects in the knowledge graph, generates a daily listening plan based on schedule rules and your current context, and tracks your consumption stats over time.

Because all media items are stored as knowledge graph objects, they participate in the full SemPKM experience — search, tagging, edges, views, and SPARQL queries all work on media content just like any other object.

This chapter covers installing the app, subscribing to sources, configuring schedule rules, using the daily plan, reading stats, and troubleshooting common issues.

---

## Prerequisites

The Media Scheduler requires two components:

1. **media-scheduler Mental Model** — defines the `MediaSource`, `MediaItem`, `DailyMediaPlan`, `PlanEntry`, and `ScheduleRule` types, their SHACL shapes, and default views.
2. **Media Scheduler application** — the running app that polls sources, generates plans, serves the UI, and contributes workspace integrations.

If you have not yet installed the App Platform itself, see [Chapter 29: App Platform](29-app-platform.md) first.

## Installing the Mental Model

1. Navigate to **Admin > Mental Models**.
2. Click **Install Model**.
3. Enter the archive path: `media-scheduler` (the bundled model ships with SemPKM).
4. Click **Install**. The model registers the media types, their SHACL shapes for form generation, and default views.

> **Tip:** Verify the model is loaded by checking the Types list in the Explorer — `MediaSource`, `MediaItem`, and `ScheduleRule` should now appear.

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the path: `/app/apps/media-scheduler`.
3. Click **Install**. The platform validates the manifest, creates the app's virtual environment, and starts the process.
4. Wait for the status badge to turn **green (Running)**. This typically takes a few seconds.

Once running, a **Media Scheduler** entry appears in the **APPS** section of the workspace sidebar. Click it to open the scheduler.

---

## The Scheduler Interface

The Media Scheduler uses a sidebar-plus-tabs layout:

```
┌──────────────┬───────────────────────────────────────────┐
│  Sources     │  Tab Bar                                  │
│  Sidebar     │  [Today] [Episodes] [Rules] [Stats]       │
│              ├───────────────────────────────────────────┤
│  + Add       │                                           │
│  ─────────── │  Tab Content Area                         │
│  Podcast A   │                                           │
│  YouTube B   │  (varies by selected tab)                 │
│  Spotify C   │                                           │
│              │                                           │
└──────────────┴───────────────────────────────────────────┘
```

### Sources Sidebar

The left pane lists all subscribed media sources. Each entry shows:

| Element | Description |
|---------|-------------|
| Source title | The source's name (feed title or channel/playlist name) |
| Source type | Icon indicating podcast, YouTube, or Spotify |
| Error indicator | A red badge shown when the last poll for that source failed |

Click the **+** button at the top to reveal the add-source form. Click a source to filter the Episodes tab to that source's items.

### Tab Bar

Four tabs control the main content area:

| Tab | Description |
|-----|-------------|
| **Today** | Today's generated media plan with time slots and action buttons |
| **Episodes** | All discovered media items across sources |
| **Rules** | Schedule rules that control plan generation |
| **Stats** | Listening statistics with interactive charts |

---

## Adding Media Sources

The Media Scheduler supports three source types. Click the **+** button in the sources sidebar to open the add-source form, then select the appropriate tab.

### Podcasts (RSS Feeds)

1. Select the **Podcast** tab in the add-source form.
2. Enter the podcast's RSS feed URL (e.g., `https://example.com/feed.xml`).
3. Optionally enter a custom title (otherwise the feed's title is used).
4. Click **Subscribe**.

The scheduler validates the URL, fetches the feed metadata, and creates a `MediaSource` subscription. New episodes are ingested immediately (up to 50 most recent), and the source appears in the sidebar.

> **Tip:** Most podcast apps and directories show the RSS feed URL in the podcast's details or sharing options. If you only have the podcast's website URL, check the page source for `<link rel="alternate" type="application/rss+xml">` tags.

### YouTube Channels and Playlists

1. Select the **YouTube** tab in the add-source form.
2. Enter a YouTube channel or playlist URL (e.g., `https://www.youtube.com/c/ChannelName` or `https://www.youtube.com/playlist?list=PLxxxxxxx`).
3. Enter your **YouTube Data API v3 key**. The scheduler uses this to fetch video metadata and durations.
4. Click **Subscribe**.

The scheduler parses the URL, resolves channels to their uploads playlist, validates the API key with a test call, and creates the subscription. Recent videos are fetched immediately.

**Supported URL formats:**

- `https://www.youtube.com/c/ChannelName`
- `https://www.youtube.com/channel/UCxxxxxxx`
- `https://www.youtube.com/@HandleName`
- `https://www.youtube.com/playlist?list=PLxxxxxxx`

> **Note:** YouTube polling consumes API quota (roughly 2 units per source per poll). The scheduler tracks daily quota usage to avoid exceeding limits. If the daily quota is exhausted, polling pauses until the next day.

### Spotify Playlists

Spotify integration requires an OAuth connection before subscribing to playlists.

#### Connecting to Spotify

1. Select the **Spotify** tab in the add-source form.
2. Enter your **Spotify Client ID**, **Client Secret**, and **Redirect URI**. These come from a Spotify Developer Application you create at [developer.spotify.com](https://developer.spotify.com).
3. Click **Connect**. You are redirected to Spotify's authorization page.
4. Approve the requested permissions. Spotify redirects you back to SemPKM with a success message.

> **Setting up a Spotify Developer App:**
> 1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a new app.
> 2. Set the Redirect URI to match your SemPKM instance (e.g., `https://your-instance.example/app/media-scheduler/_fragments/spotify/callback`).
> 3. Copy the Client ID and Client Secret from the app settings.

#### Subscribing to a Playlist

Once connected, the add-source form shows your Spotify playlists in a dropdown:

1. Select a playlist from the dropdown (shows playlist name and track count).
2. Click **Subscribe**.

The scheduler creates a `MediaSource` for the playlist and ingests its tracks immediately.

#### Disconnecting

To disconnect from Spotify, click the **Disconnect** button in the Spotify section of the add-source form. This clears all stored OAuth tokens and credentials.

---

## Schedule Rules

Schedule rules control how the daily media plan is generated. They match conditions against your current context (time of day, activity, location) and select appropriate content.

### Creating a Rule

1. Switch to the **Rules** tab.
2. Fill in the rule form:
   - **Name** — a descriptive label (e.g., "Morning commute podcasts")
   - **Conditions** — when this rule applies:
     - **Time period** — morning, afternoon, evening, or any
     - **Activity** — commuting, exercising, working, relaxing, or any
     - **Location** — home, office, transit, gym, or any
   - **Actions** — what content to select:
     - **Source type** — podcast, youtube, spotify, or any
     - **Category** — optional category filter
   - **Priority** — numeric priority (higher = matched first)
3. Click **Add Rule**.

### How Rules Are Evaluated

When a daily plan is generated, the plan service:

1. Fetches your current context (time, activity, location) from the context service.
2. Evaluates all enabled rules against the current context, ordered by priority.
3. For each matching rule, selects unlistened media items that match the rule's source type and category filters.
4. Allocates time slots in the plan based on item durations.

### Enabling and Disabling Rules

Each rule has a toggle to enable or disable it. Disabled rules are skipped during plan generation but preserved for future use.

### Deleting a Rule

Click the delete button next to a rule to permanently remove it.

---

## Today's Plan

The **Today** tab shows your generated daily media plan — a schedule of media items selected by your rules and fitted into time slots.

### Generating a Plan

Plans are generated automatically by the `generate-plan` background task (runs every 6 hours by default). You can also trigger manual generation from the Today tab.

Each plan entry shows:

| Element | Description |
|---------|-------------|
| Time slot | Suggested listening time |
| Title | The media item's title |
| Source | Which source the item comes from |
| Duration | Estimated listening/watching time |
| Status | Current status (pending, completed, skipped, saved) |

### Action Buttons

Each plan entry has three action buttons:

| Button | Action |
|--------|--------|
| **Complete** ✓ | Mark the item as completed — it won't appear in future plans |
| **Skip** ✕ | Skip this item for today — it may appear in future plans |
| **Save** ♡ | Save the item for later — bookmarks it for future listening |

### Context-Driven Re-evaluation

If your context changes during the day (e.g., you switch from commuting to working), the next plan generation cycle re-evaluates rules against the new context. Items already marked as completed or skipped retain their status.

---

## Stats Dashboard

The **Stats** tab displays three interactive Chart.js charts summarizing your listening activity. All charts are based on completed items only.

### Hours by Category

A horizontal bar chart showing total listening hours grouped by source type (podcast, YouTube, Spotify). Helps you see which content type dominates your consumption.

### Top Sources

A horizontal bar chart showing the 10 most-played sources ranked by number of completed items. Useful for identifying your favorite feeds and channels.

### Weekly Activity

A line chart showing daily completion counts over the past week. Days with zero activity are included for a continuous trend line. Helps you track listening consistency.

> **Tip:** If no items have been completed yet, the charts show "No data" empty states. Start completing items from your daily plan to populate the stats.

---

## Managing Sources

### Removing a Source

To unsubscribe from a source:

1. Find the source in the sidebar.
2. Click the **remove** button (trash icon) next to the source.
3. The source is removed and polling stops.

> **Note:** Removing a source does not delete media items already ingested from that source. They remain in your knowledge graph and are findable via search and SPARQL.

### Poll Settings

The frequency at which the scheduler checks sources for new content is configured per task type:

1. Go to **Admin > Applications**.
2. Click **Media Scheduler** to open the detail page.
3. In the **Task Configuration** section, find the poll tasks:

| Task | Default Interval | Description |
|------|-----------------|-------------|
| `poll-sources` | 15 minutes | Polls podcast RSS feeds |
| `poll-youtube` | 15 minutes | Polls YouTube channels and playlists |
| `poll-spotify` | 15 minutes | Polls Spotify playlists |
| `generate-plan` | 6 hours | Generates or regenerates the daily media plan |

Podcast polling uses conditional GET (ETag and Last-Modified headers) to avoid re-downloading unchanged feeds, so frequent polling has minimal bandwidth impact.

### Error Handling

When a source poll fails (network error, invalid feed, API quota exceeded), the source shows an error indicator in the sidebar. The error count increments with each failure and resets on the next successful poll.

Sources with persistent errors continue to be polled — the error indicator helps you identify and fix the underlying issue (expired API key, changed feed URL, etc.).

---

## Mobile Integration

The Media Scheduler integrates with the SemPKM mobile context system (see [Chapter 48: Mobile App & Context](48-mobile-app-context.md)) to provide context-aware suggestions.

### How It Works

The context service subscribes to context updates from the mobile app (location, activity, time). When your context changes, the scheduler can re-evaluate rules to suggest content that matches your current situation — for example, switching to podcast recommendations when you start commuting.

### Context Subscription

The context listener starts automatically when the app launches and stops when the app shuts down. You can check the connection status in the app's admin detail page.

---

## Admin Monitoring

Administrators can monitor the Media Scheduler from the **Admin > Applications > Media Scheduler** detail page.

### App Status

The detail page shows the current status badge:

| Status | Meaning |
|--------|---------|
| **Running** (green) | App is alive and processing polls |
| **Stopped** (gray) | App is installed but not active |
| **Error** (red) | App crashed — check the error message |

Use the **Start**, **Stop**, and **Restart** buttons to control the app lifecycle.

### Task History

The **Task History** section shows recent executions of each background task (`poll-sources`, `poll-youtube`, `poll-spotify`, `generate-plan`):

- **Start time** — when the task ran
- **Status** — success or error
- **Duration** — how long the task took
- **Error** — any error message (if the task failed)

### Permissions

The Media Scheduler declares these permissions in its manifest:

| Permission | What It Enables |
|------------|-----------------|
| `object.create` | Creating MediaSource, MediaItem, and plan objects |
| `object.patch` | Updating item status (complete, skip, save) |
| `edge.create` | Creating relationships between objects |
| `sparql.read` | Querying the knowledge graph for sources, items, rules, and stats |
| `backgroundTasks` | Running scheduled poll and plan-generation tasks |
| `network: ["*"]` | Fetching external feeds, YouTube API, and Spotify API |
| `settings` | Reading and writing app-scoped settings |

---

## Troubleshooting

### No episodes appearing after subscribing

- **Check the source's error indicator.** If it shows errors, the feed URL may be invalid or unreachable.
- **Verify the feed URL** by opening it directly in a browser — it should return XML (RSS/Atom) content.
- **For YouTube sources,** confirm the API key is valid and has YouTube Data API v3 enabled in the Google Cloud Console.
- **Check task history** in the admin page to see if poll tasks are running and whether they report errors.

### YouTube API quota exceeded

The YouTube Data API has a daily quota limit (typically 10,000 units). Each poll cycle uses roughly 2 units per source (1 for playlist items, 1 for video durations).

- The scheduler tracks quota usage and automatically stops polling when the limit is reached.
- Quota resets daily at midnight Pacific Time.
- Reduce poll frequency or number of YouTube sources if you consistently hit the limit.

### Spotify connection issues

- **"Not connected" after authorizing:** The OAuth callback may have failed. Check that the Redirect URI in your Spotify Developer App matches exactly (including trailing slashes).
- **Token refresh failures:** If the refresh token expires, you need to reconnect by clicking **Disconnect** and then **Connect** again.
- **No playlists showing:** Ensure your Spotify app has the `playlist-read-private` scope. The scheduler requests this during OAuth.

### Today's plan is empty

- **No rules configured:** Create at least one schedule rule in the Rules tab.
- **Rules don't match current context:** Check that your rule conditions match your current time, activity, and location context.
- **No unlistened items:** If all items from matching sources are already completed or skipped, there's nothing to schedule. Subscribe to more sources or wait for new content.
- **Plan generation hasn't run:** The `generate-plan` task runs every 6 hours by default. Check the task history to see when it last ran.

### Context not updating

- **Mobile app not connected:** Check the context subscription status in the admin detail page.
- **Context service not running:** The context listener starts with the app — try restarting the app from the admin page.
- See [Chapter 48: Mobile App & Context](48-mobile-app-context.md) for mobile-side troubleshooting.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — how the app platform manages apps, lifecycle, and permissions
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing and managing the `media-scheduler` model
- [Chapter 48: Mobile App & Context](48-mobile-app-context.md) — mobile context integration

---

**Previous:** [Chapter 48: Mobile App & Context](48-mobile-app-context.md) | **Next:** [Chapter 38: Hosted Demo](38-hosted-demo.md)
