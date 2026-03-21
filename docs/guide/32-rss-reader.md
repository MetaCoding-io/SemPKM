# Chapter 32: RSS Reader

The **RSS Reader** is a first-party SemPKM application that brings external web content into your knowledge base. Subscribe to RSS, Atom, or JSON feeds, and the reader automatically polls them for new articles, ingests the content as typed objects in the knowledge graph, and presents them in a clean three-pane reading interface. Because articles are stored as `rss:Article` objects, they participate in the full SemPKM experience — search, tagging, edges, views, and SPARQL queries all work on feed content just like any other object.

This chapter covers installing the reader, subscribing to feeds, reading articles, and managing settings.

---

## Prerequisites

The RSS Reader requires two components to be installed:

1. **rss-feeds Mental Model** — defines the `Article` and `Subscription` types, their SHACL shapes, and views.
2. **RSS Reader application** — the running app that polls feeds, serves the reader UI, and contributes workspace integrations.

If you have not yet installed the App Platform itself, see [Chapter 29: App Platform](29-app-platform.md) first.

## Installing the Mental Model

1. Navigate to **Admin > Mental Models**.
2. Click **Install Model**.
3. Enter the archive path: `rss-feeds` (the bundled model ships with SemPKM).
4. Click **Install**. The model registers the `rss:Article` and `rss:Subscription` types, their SHACL shapes for form generation, and default views for browsing articles.

> **Tip:** You can verify the model is loaded by checking the Types list in the Explorer — `Article` and `Subscription` should now appear.

## Installing the RSS Reader App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the path: `/app/apps/rss-reader`.
3. Click **Install**. The platform validates the manifest, creates the app's virtual environment, and starts the process.
4. Wait for the status badge to turn **green (Running)**. This typically takes a few seconds.

Once running, an **RSS Reader** entry appears in the **APPS** section of the workspace sidebar. Click it to open the reader.

## The Reader Interface

The RSS Reader uses a three-pane layout:

```
┌──────────────┬────────────────────┬──────────────────────────┐
│  Feed        │  Article List      │  Reading Pane            │
│  Sidebar     │                    │                          │
│              │  ┌──────────────┐  │  Article title           │
│  All Feeds   │  │ Filter tabs  │  │  Author · Date · Source  │
│  ─────────── │  │ All|Unread|★ │  │                          │
│  Feed A  (3) │  ├──────────────┤  │  Rendered markdown body  │
│  Feed B  (1) │  │ Article 1    │  │                          │
│  Feed C  (0) │  │ Article 2    │  │  ┌────┐                  │
│              │  │ Article 3    │  │  │ ★  │  Star / Unstar   │
│              │  └──────────────┘  │  └────┘                  │
└──────────────┴────────────────────┴──────────────────────────┘
```

### Feed Sidebar

The left pane lists all subscribed feeds. Each entry shows:

| Element | Description |
|---------|-------------|
| Feed name | The feed's title, fetched from the feed metadata |
| Unread badge | A count of unread articles for that feed (hidden when 0) |
| Error indicator | A red icon shown when the last poll for that feed failed |

Click **All Feeds** at the top to show articles from every subscription. Click a specific feed to filter the article list to that feed only.

At the bottom of the sidebar:

- **Subscribe** button — opens the subscribe dialog (see below)
- **Import OPML** button — imports feeds from an OPML file

### Article List

The center pane shows articles matching the current feed selection. Three **filter tabs** at the top control which articles appear:

| Tab | Shows |
|-----|-------|
| **All** | Every article from the selected feed(s) |
| **Unread** | Only articles not yet marked as read |
| **Starred** | Only articles you have starred |

Each article item displays the title, published date, and source feed name. Unread articles appear with a visual indicator (bolder text) to distinguish them from read articles.

### Reading Pane

The right pane displays the selected article's content:

- **Title** — the article's headline
- **Metadata line** — author, published date, and source feed name
- **Body** — the article content rendered as clean markdown with proper typography
- **Star button** — toggle to star/unstar the article (persists across sessions)

If an article has no extracted body content, the reading pane falls back to showing the feed-provided description.

---

## Subscribing to Feeds

### Adding a Feed by URL

1. Click the **Subscribe** button in the feed sidebar (or use the command palette: `Ctrl+K` → "Subscribe to Feed...").
2. Enter the feed URL (RSS, Atom, or JSON Feed) in the dialog.
3. Click **Subscribe**.

The reader validates the URL, fetches the feed metadata, and creates a subscription. New articles are ingested immediately, and the feed appears in the sidebar.

### Feed Discovery

You don't need to know the exact feed URL. Paste a **website URL** (e.g., `https://example.com/blog`) and the reader will attempt to discover the feed automatically by checking:

- `<link rel="alternate" type="application/rss+xml">` tags in the page HTML
- Common feed paths (`/feed`, `/rss`, `/atom.xml`)

If a feed is found, it subscribes to the discovered URL.

### Importing Feeds from OPML

If you're migrating from another RSS reader, you can import all your subscriptions at once using an OPML file:

1. Click the **Import OPML** button in the feed sidebar.
2. Select your `.opml` or `.xml` file.
3. The reader parses the file, creates a subscription for each feed entry, and reports results.

The import result shows:

| Field | Meaning |
|-------|---------|
| **Created** | Number of new subscriptions added |
| **Duplicates** | Feeds you were already subscribed to (skipped) |
| **Errors** | Feeds that could not be parsed or subscribed |

> **Tip:** OPML folder categories are preserved as tags on each subscription. If your OPML file organizes feeds into folders like "Tech" and "News", those become `bpkm:tags` values on the subscription objects — searchable and filterable throughout SemPKM.

---

## Reading Articles

### Opening an Article

Click any article in the article list to load it in the reading pane. If the **Mark read on open** setting is enabled (default: on), the article is automatically marked as read when you open it.

### Starring and Unstarring

Click the **star button** (★) in the reading pane to star an article. Starred articles persist across sessions and can be filtered using the **Starred** tab in the article list. Click again to remove the star.

Stars are stored as `rss:isStarred` properties on the article object — they survive app restarts and are visible in SPARQL queries.

### Mark as Read / Unread

Articles are marked as read automatically when opened (if the setting is enabled). You can also:

- **Mark All as Read** — available in the command palette (`Ctrl+K` → "Mark All as Read") or via the reader UI. This marks every unread article in the current feed selection as read.

Read state is tracked via the `rss:isRead` property on each article object.

### Keyboard Navigation

The reader supports keyboard shortcuts for efficient reading:

| Key | Action |
|-----|--------|
| `j` | Select next article in the list |
| `k` | Select previous article in the list |

These shortcuts work when the reader pane is focused.

---

## Workspace Integration

The RSS Reader contributes several integration points to the main SemPKM workspace, extending the reader experience beyond its standalone page.

### Views in the Explorer

Two views appear in the **Views** section of the Explorer panel:

- **Unread Articles** — shows all unread articles across all feeds, filterable and sortable
- **Starred Articles** — shows all starred articles across all feeds

These views use the standard SemPKM view infrastructure, so they support the same table/card display options as any other view.

### Related Articles (Right Pane)

When you select any object in the workspace, the right pane's **Related Articles** tab shows articles that share a connection with the focused object. The relationship is determined by:

- **Same feed source** — articles from the same feed as a selected article
- **Shared tags** — articles whose tags overlap with the focused object's tags

Up to 10 related articles are shown, each clickable to open in the object browser.

### Command Palette

The RSS Reader adds three entries to the command palette (`Ctrl+K`):

| Command | Action |
|---------|--------|
| **Subscribe to Feed...** | Opens the subscribe dialog |
| **Mark All as Read** | Marks all unread articles as read |
| **Open RSS Reader** | Switches to the RSS Reader tab |

### Custom Article Renderer

When you open an `rss:Article` object from the object browser or a view, it renders using the RSS Reader's custom layout — showing the article title, metadata, markdown body, and star button — instead of the default SHACL form editor. This provides a consistent reading experience regardless of how you navigate to the article.

---

## Managing Feeds

### Unsubscribing from a Feed

To remove a feed subscription:

1. Click on the feed in the sidebar to select it.
2. Click the **Unsubscribe** button that appears.
3. The subscription is soft-deleted — the feed no longer appears in the sidebar and polling stops.

> **Note:** Unsubscribing does not delete articles already ingested from that feed. They remain in your knowledge base and are findable via search and SPARQL.

### Feed Error Indicators

When a feed poll fails (network error, invalid feed format, server timeout), the feed sidebar shows a **red error indicator** next to the affected feed. The error clears automatically when the next poll succeeds.

Common causes of feed errors:

- The feed URL is no longer valid (site moved or shut down)
- The server is temporarily unreachable
- The feed format changed and can no longer be parsed

### Re-subscribing

If you unsubscribe from a feed and later want it back, simply subscribe again with the same URL. The reader detects duplicates and will not create a second subscription.

---

## Settings

The RSS Reader has configurable settings accessible from the reader's settings panel. Navigate to the reader and click the settings icon, or go to **Admin > Applications > RSS Reader**.

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Articles per page** | Number of articles shown in the article list at once | 50 | 10–200 |
| **Mark read on open** | Automatically mark articles as read when opened in the reading pane | Enabled | On/Off |

### Poll Interval

The frequency at which the reader checks feeds for new articles is configured at the app level:

1. Go to **Admin > Applications**.
2. Click **RSS Reader** to open the detail page.
3. In the **Task Configuration** section, find the `poll-feeds` task.
4. Adjust the interval (default: **5 minutes**).

The poll task uses conditional GET (ETag and Last-Modified headers) to avoid re-downloading unchanged feeds, so frequent polling has minimal bandwidth impact.

---

## Admin Monitoring

Administrators can monitor the RSS Reader from the **Admin > Applications > RSS Reader** detail page.

### App Status and Lifecycle

The detail page shows the current status badge:

| Status | Meaning |
|--------|---------|
| **Running** (green) | App is alive and processing feed polls |
| **Stopped** (gray) | App is installed but not active |
| **Error** (red) | App crashed — check the error message |

Use the **Start**, **Stop**, and **Restart** buttons to control the app lifecycle. If the app crashes, the platform automatically restarts it with exponential backoff.

### Task History

The **Task History** section shows recent executions of the `poll-feeds` background task:

- **Start time** — when the poll ran
- **Status** — success or error
- **Duration** — how long the poll took in milliseconds
- **Error** — any error message (if the poll failed)

This history is useful for diagnosing feed ingestion problems. If polls are consistently failing, check the feed URLs and network connectivity.

### Permissions

The RSS Reader declares these permissions in its manifest:

| Permission | What It Enables |
|------------|-----------------|
| `object.create` | Creating Article and Subscription objects in the knowledge graph |
| `sparql.read` | Querying the knowledge graph for subscriptions, articles, and related objects |
| `backgroundTasks` | Running the scheduled `poll-feeds` task |
| `network: ["*"]` | Fetching external feed URLs (all domains allowed) |
| `settings` | Reading and writing app-scoped settings |

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — how the app platform manages apps, lifecycle, and permissions
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing and managing the `rss-feeds` model

---

**Previous:** [Chapter 31: API Surface](31-api-surface.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
