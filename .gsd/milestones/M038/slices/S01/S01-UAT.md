# S01: Mental Model + Podcast Sources — UAT Script

## Preconditions

- Docker stack running (`docker compose up -d`)
- `media-scheduler` Mental Model installed via Admin > Models (or `POST /admin/models/install` with the `models/media-scheduler/` archive)
- `media-scheduler` app started via Admin > Applications
- User logged in to SemPKM workspace

## Test Cases

### TC-01: Model Installation

**Steps:**
1. Navigate to Admin > Models
2. Install the `media-scheduler` model
3. Navigate to Admin > Models list

**Expected:**
- Model appears in list with ID `media-scheduler`, version `1.0.0`
- Three types visible: MediaSource (radio icon), MediaItem (play-circle icon), MediaCategory (folder icon)

### TC-02: App Registration and Sidebar

**Steps:**
1. Navigate to Admin > Applications
2. Verify `media-scheduler` app is listed
3. Start the app if not running
4. Navigate to the workspace
5. Check the [Apps] sidebar section

**Expected:**
- App shows status "running" in admin
- "Media Scheduler" appears in the [Apps] sidebar section
- Clicking it opens the Media Scheduler app page

### TC-03: App Page Layout

**Steps:**
1. Open the Media Scheduler app from the sidebar

**Expected:**
- Two-column layout: sources sidebar (left) and items area (right)
- Sources panel shows "No sources added yet" message if empty
- Items area shows "No items discovered yet" message if empty
- A "+" button is visible in the sources sidebar header

### TC-04: Subscribe to Podcast Feed

**Steps:**
1. Click the "+" button in the sources sidebar
2. Enter a podcast RSS feed URL (e.g., `https://feeds.simplecast.com/54nAGcIl` — The Changelog)
3. Optionally enter a custom title
4. Click "Subscribe"

**Expected:**
- Success message appears
- New source appears in the sources sidebar with:
  - Title (custom or extracted from feed)
  - "podcast" badge
  - No error indicator
- Sources list refreshes automatically (htmx `sourcesChanged` trigger)

### TC-05: Subscribe to Duplicate Feed

**Steps:**
1. Try to subscribe to the same feed URL used in TC-04

**Expected:**
- Error message: source already exists (duplicate check via SPARQL)
- Sources list unchanged

### TC-06: Poll Sources — Initial Episode Discovery

**Steps:**
1. Wait for the `poll-sources` scheduled task to run (15m interval), OR
2. Trigger manually via Admin > Applications > media-scheduler > Tasks > poll-sources > Run Now

**Expected:**
- Items area populates with discovered episodes (up to 50 per source)
- Each item shows: title, source name, publication date, duration (if available), "queued" status badge
- Items ordered by publication date (most recent first)

### TC-07: Item Deduplication

**Steps:**
1. Trigger `poll-sources` again after TC-06

**Expected:**
- No new items created (all episodes already discovered)
- Task log shows 0 `items_created`
- Source's `lastPolled` timestamp updated

### TC-08: Source Filtering

**Steps:**
1. Subscribe to a second podcast feed
2. Wait for poll to discover items from both sources
3. Click on Source A in the sources sidebar

**Expected:**
- Items area shows only items from Source A
- "Show all items" button appears below sources list
- Clicking "Show all items" restores the full items list

### TC-09: Remove Source

**Steps:**
1. Click the remove (✕) button next to a source in the sidebar

**Expected:**
- Source removed from the list
- Source object's sourceType set to "inactive" (soft-delete)
- Items from that source remain visible (not deleted)
- Source no longer polled on next `poll-sources` run

### TC-10: Feed Error Handling

**Steps:**
1. Subscribe to an invalid feed URL (e.g., `https://example.com/nonexistent-feed`)
2. Trigger `poll-sources`

**Expected:**
- Source shows an error badge with count (1) in the sources sidebar
- Error tooltip shows the failure reason (HTTP 404 or parse error)
- Other sources continue polling normally (per-feed isolation)
- `ms:errorCount` incremented, `ms:lastError` set on the MediaSource object

### TC-11: Conditional GET Efficiency

**Steps:**
1. After a successful poll, inspect the MediaSource object's `ms:etag` or `ms:lastModifiedHeader` properties
2. Trigger `poll-sources` again

**Expected:**
- If the feed server supports conditional GET, the response is 304 Not Modified
- Task log shows feed was polled but 0 items created, 0 bytes transferred
- `lastPolled` updated, `etag`/`lastModifiedHeader` preserved

### TC-12: MediaItem Object Integrity

**Steps:**
1. Navigate to the workspace object browser
2. Find a MediaItem object created by poll-sources
3. Open the object

**Expected:**
- Object has correct RDF type (`ms:MediaItem`)
- Properties populated: `dcterms:title`, `ms:enclosureUrl` (audio link), `dcterms:date` (published), `ms:status` ("queued"), `ms:mediaType` ("audio")
- If feed provided duration: `ms:duration` is an integer (seconds)
- Object IRI follows pattern `urn:sempkm:app:media-scheduler:item-{hash}`

## Edge Cases

### EC-01: Empty Feed
Subscribe to a valid RSS feed that has zero items. After polling, source shows 0 items, no error.

### EC-02: Feed with No Enclosures
Subscribe to a text-only RSS feed (no audio/video enclosures). Items created with `ms:enclosureUrl` set to the article link as fallback.

### EC-03: Very Long Episode Duration
An episode with duration "99:59:59" should parse to 359999 seconds without error.

### EC-04: Missing Duration
Episodes without `<itunes:duration>` should create items without `ms:duration` property (not 0, not null string).

### EC-05: Unicode in Feed Content
Feed with non-ASCII titles/descriptions (e.g., Japanese podcast) should create items with correct UTF-8 content.
