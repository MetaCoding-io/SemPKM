# S03: YouTube Integration — UAT Script

**Milestone:** M038  
**Slice:** S03  
**Written:** 2026-03-23  

## Preconditions

- Media Scheduler app installed (from S01) — `media-scheduler` model present, app running
- At least one podcast source already subscribed (from S01) — proves baseline works
- YouTube Data API v3 key available (Google Cloud Console → APIs & Services → Credentials)
- Docker stack running (`docker compose up`)

## Test Cases

### 1. Add YouTube channel by @handle URL

1. Open Media Scheduler app from sidebar → Sources tab
2. Locate the **YouTube** section in the Add Source form
3. Enter URL: `https://www.youtube.com/@3blue1brown`
4. Enter a valid YouTube Data API v3 key
5. Click "Add YouTube Source"
6. **Expected:** Success message appears. Sources list refreshes and shows a new entry with:
   - Title containing the channel name
   - "youtube" source type badge
   - External ID = the resolved uploads playlist ID (starts with `UU`)

### 2. Add YouTube playlist by URL

1. In the YouTube section of Add Source
2. Enter URL: `https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab` (3Blue1Brown Essence of Linear Algebra)
3. Enter the same API key
4. Click "Add YouTube Source"
5. **Expected:** Success message. New source appears in list with playlist title and "youtube" badge.

### 3. Poll discovers videos

1. Wait for the `poll-youtube` task to run (15m interval) — or trigger via admin Task History "Run Now" if available
2. Navigate to the Episodes/Items tab
3. **Expected:** YouTube videos appear as MediaItem objects with:
   - Title matching the video title
   - Duration in seconds (not "PT..." ISO format)
   - Thumbnail URL present
   - YouTube watch link (e.g., `https://www.youtube.com/watch?v=...`)
   - Source type = "youtube"

### 4. YouTube videos appear in daily plan

1. Ensure at least one schedule rule exists that matches YouTube sources (e.g., rule with `source_type: "youtube"`)
2. Trigger daily plan generation
3. **Expected:** Today's plan includes time slots with YouTube video entries alongside any podcast episodes.

### 5. Invalid URL rejected

1. In the YouTube section, enter an invalid URL: `https://www.example.com/not-youtube`
2. Enter a valid API key
3. Click "Add YouTube Source"
4. **Expected:** Error message: URL format not recognized. No source created.

### 6. Invalid API key rejected

1. Enter a valid YouTube URL: `https://www.youtube.com/@TED`
2. Enter an invalid API key: `invalid-key-12345`
3. Click "Add YouTube Source"
4. **Expected:** Error message indicating API key validation failed (403 from YouTube). No source created.

### 7. Duplicate source prevented

1. Add the same YouTube channel URL that was already added in Test Case 1
2. **Expected:** Error message indicating this source already exists. No duplicate created.

### 8. Quota tracking visible

1. After poll-youtube has run at least once
2. Check app state (via admin or logs) for `youtube_quota_used` and `youtube_quota_reset_date`
3. **Expected:** `youtube_quota_used` shows a positive integer reflecting API calls made. `youtube_quota_reset_date` shows today's date.

### 9. Podcast sources unaffected

1. Check that existing podcast sources still appear in the sources list
2. Verify podcast episodes still appear in the Items tab
3. Trigger `poll-sources` (podcast poll) if possible
4. **Expected:** Podcast functionality unchanged. Both podcast and YouTube items coexist.

## Edge Cases

### API key not configured
1. Remove or never set a YouTube API key
2. Wait for `poll-youtube` to trigger
3. **Expected:** Task logs "No YouTube API key configured" and skips gracefully. No errors. Podcast polling unaffected.

### Quota exhaustion
1. (Simulated) If daily quota approaches 10,000 units
2. **Expected:** `poll-youtube` stops querying remaining sources when quota check fails. Logs "Quota exceeded" at WARNING. Next day, counter resets and polling resumes.

### Channel with no videos
1. Add a YouTube channel that has zero public videos
2. Wait for poll
3. **Expected:** Poll completes without error. Source state updated with zero new items. No crash.

## Failure Signals

- "youtube" badge missing from source list entries → `sourceType` not set on MediaSource creation
- Videos show "PT4M30S" instead of "270" → `parse_iso8601_duration()` not called during conversion
- `poll-youtube` errors in task history → check API key validity and quota state in StateClient
- YouTube form section missing from Add Source page → template not updated or htmx swap broken
- `405 Method Not Allowed` on form submit → htmx URL missing `/app/media-scheduler/` proxy prefix

## Notes for Tester

- The YouTube Data API v3 key requires enabling the "YouTube Data API v3" in Google Cloud Console
- Free tier provides 10,000 quota units/day — each `search.list` costs 100 units, `playlistItems.list` costs 1 unit, `videos.list` costs 1 unit per video
- Channel resolution (`@handle` → channel ID → uploads playlist ID) costs ~3 units total
- The poll task respects the quota tracker — it won't exceed the configured threshold
