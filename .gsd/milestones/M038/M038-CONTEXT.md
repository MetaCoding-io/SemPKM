---
depends_on: [M037]
---

# M038: Personal Media Scheduler App

**Gathered:** 2026-03-22
**Status:** Queued — pending auto-mode execution

## Project Description

A SemPKM platform app that manages a personalized daily media queue — automatically scheduling podcasts, YouTube videos, Spotify playlists, and other media based on user context (time-of-day, location, activity) and configurable rules. While commuting, hear that podcast episode you saved. At work during news hours, catch up on daily briefings from YouTube subscriptions. When the system detects deep focus, switch to ambient lo-fi music. At 4:30pm, wind down with your evening Spotify playlist.

## Why This Milestone

Media consumption is fragmented across 5+ apps with zero coordination. Users manually open Spotify for music, switch to a podcast app during commute, browse YouTube randomly during breaks. There's no system that understands "I want podcasts during commute, news videos at lunch, focus music during deep work, and my wind-down playlist at 4:30."

SemPKM's unique advantage: it already has the User Context system (M037) providing real-time signals about what the user is doing, and the App Platform (M009) for background task scheduling. The media scheduler connects context signals to media sources, generating a daily plan that adapts in real-time.

The structured RDF data model means the AI copilot (M035) can reason about media habits: "you listened to 3 machine learning podcasts this week — here's a related Paper in your Research model."

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open the Media Scheduler app from the [Apps] sidebar and see today's media plan
- Add media sources: podcast RSS feeds, YouTube channels/playlists, Spotify playlists
- Create schedule rules: "when commuting, play podcast queue" / "at 12pm-1pm, play YouTube news" / "when focus-mode, play lo-fi playlist" / "at 4:30pm, play wind-down playlist"
- See the daily media plan auto-generated each morning with time slots mapped to media items
- See the plan adapt in real-time when context changes (unexpected focus block → switches to focus music)
- See the current suggestion on the mobile app (M037) with playback controls or deep links
- Mark items as completed, skipped, or save-for-later
- See media consumption stats: hours per category, most-played sources, weekly trends

### Entry point / environment

- Entry point: `http://localhost:3000/app/media-scheduler/` (web UI), mobile app (M037) for current suggestion
- Environment: Docker Compose (api + triplestore + frontend/nginx) + mobile app providing context
- Live dependencies involved: RDF4J triplestore, YouTube Data API v3, Spotify Web API, podcast RSS feeds, M037 Context API

## Completion Class

- Contract complete means: media source sync discovers new episodes/videos, schedule rules evaluate against context, daily plan generates with correct time slots, media item status tracking works
- Integration complete means: context changes from M037 trigger real-time plan adaptation, YouTube/Spotify/podcast integrations return real media data, mobile app displays current suggestion
- Operational complete means: daily plan regenerates each morning via scheduled task, podcast polling discovers new episodes on interval, plan survives Docker restart, handles API errors gracefully

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User adds a podcast feed and a Spotify playlist as media sources
- User creates rule: "when commuting, play podcast queue"
- User's mobile app detects commute start (M037 context) → media scheduler activates podcast queue → mobile app shows current episode with play button
- User creates rule: "at 12:00-13:00, play YouTube news playlist" → at noon, daily plan shows YouTube videos for that slot
- User's context changes to "focus mode" mid-afternoon → plan adapts to show lo-fi music instead of scheduled content
- Daily plan regenerates at midnight with new podcast episodes and YouTube videos discovered since yesterday

## Risks and Unknowns

- **Spotify playback control** — Spotify Web API requires Premium for playback control. Free tier can browse playlists and tracks but cannot start/pause/skip playback. Need graceful degradation: Premium users get inline playback, free users get deep links to the Spotify app. This is a dealbreaker for some users — document prominently.
- **YouTube API quota** — YouTube Data API has a 10,000 unit/day quota. list operations cost 1 unit each. With 20 subscriptions × daily polling, that's ~100 units/day — well within budget. But video search or channel listing costs more. Need to track usage.
- **Real-time plan adaptation** — The schedule isn't a static daily plan — it reacts to context changes. This means the rules engine needs to re-evaluate on every context update, not just once at plan generation. If context changes every 5 minutes (frequent geofence transitions), this could be chatty.
- **Media playback surface** — Where does media actually play? Options: (a) deep link to native app (Spotify/YouTube/podcast app), (b) embedded web player in mobile app, (c) audio-only player in mobile app for podcasts. For v1, deep links + audio player for podcasts is the pragmatic approach.
- **Podcast episode deduplication** — RSS feeds can update items (corrected titles, updated enclosure URLs). Need stable episode ID (GUID from feed or SHA-256 of enclosure URL) for dedup, same pattern as M010 RSS Reader.

## Existing Codebase / Prior Art

- `apps/rss-reader/` — RSS feed polling, feedparser integration, article dedup, conditional GET (M010). Podcast episode discovery can reuse the same feed polling pattern.
- `apps/rss-reader/services/feed_service.py` — FeedService with subscribe, parse, conditional GET. Reference for podcast feed polling.
- `backend/app/apps/scheduler.py` — AppScheduler for background tasks. Media source polling and daily plan generation run as scheduled tasks.
- `backend/sdk/` — App SDK with CommandClient, HttpClient, StateClient. Media scheduler app follows the same pattern as all sync apps.
- M037 Context API — `GET /api/context/current` provides location, activity, time-of-day, calendar context. The media scheduler consumes this.
- `models/rss-feeds/` — rss-feeds Mental Model. The media-scheduler model may extend or complement it for podcast types.
- `backend/app/views/registry.py` — register_renderer() for custom view types. Media plan could have a custom timeline/agenda renderer.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New requirements: MEDIA-01 through MEDIA-10+ covering media sources, schedule rules, daily plan, context-driven adaptation, mobile integration, API integrations

## Scope

### In Scope

**Mental Model — `media-scheduler`:**
- MediaSource — podcast feed URL, YouTube channel/playlist ID, Spotify playlist URI, sync settings, source type enum
- MediaItem — individual episode/video/track with title, duration, source link, thumbnail, status (queued/playing/completed/skipped/saved)
- MediaScheduleRule — context-triggered rule with conditions (location, activity, timeOfDay, timeRange) and action (play source, play category, play specific playlist)
- DailyMediaPlan — generated daily schedule with ordered time-slot entries
- MediaCategory — user-defined grouping (news, podcasts, music, learning) for rules and stats

**Media Source Integrations:**
- Podcast — RSS feed polling (reuses feedparser from M010), episode metadata extraction, enclosure URL for audio
- YouTube — YouTube Data API v3: subscription feed listing, playlist items, video metadata (title, duration, thumbnail, URL)
- Spotify — Spotify Web API: playlist listing, track metadata, playback control (Premium only), OAuth 2.0 with PKCE

**Schedule Rules Engine:**
- Rules model: conditions (location zone, activity, timeOfDay period, specific time range, calendar event type) → action (play media from source/category/playlist)
- Priority ordering: specific time rules > context rules > default rules
- Rule evaluation on context update (from M037 SSE stream or polling)
- Real-time plan adaptation: re-evaluate when context changes, update current slot

**Daily Plan Generation:**
- Scheduled task runs at configurable time (default midnight)
- Discovers new content from all active media sources
- Applies rules to generate ordered time-slot plan for the day
- Fills time slots with specific media items based on rules and content availability
- Handles conflicts: if two rules match the same time, higher-priority wins

**Mobile Integration (via M037 app):**
- Current media suggestion endpoint: `GET /app/media-scheduler/_fragments/current-suggestion`
- Deep links to native apps (Spotify://track/..., YouTube://video/..., podcast app)
- Audio player for podcast episodes (HTML5 audio in mobile webview)
- "Next", "Skip", "Save for later" actions from mobile

**Workspace UI:**
- Media Scheduler standalone page in [Apps] sidebar
- Today's plan view (timeline/agenda layout with media items)
- Media source management (add/remove/configure sources)
- Rule builder UI (condition builder + action selector)
- Playback history and stats dashboard

### Out of Scope / Non-Goals

- Video playback within SemPKM (use YouTube app/browser)
- Music streaming (use Spotify app — SemPKM controls the queue, not the player)
- AI-generated media recommendations (M035 could suggest, but not in this milestone)
- Social features (sharing playlists, collaborative queues)
- Offline media download/caching
- Apple Music / Amazon Music / other streaming services (Spotify only for v1)
- Live radio or TV streaming
- Custom podcast player with chapter markers, speed control (use native podcast app)

## Technical Constraints

- Built on M009 App Platform SDK (CommandClient, HttpClient, StateClient)
- YouTube Data API v3 requires API key (no OAuth needed for public playlist/channel data)
- Spotify Web API requires OAuth 2.0 with PKCE for user playlist access
- Podcast feeds are standard RSS/Atom — reuse feedparser from M010
- Media items are RDF objects in urn:sempkm:current — queryable, linkable, AI-readable
- Mobile integration via M037 mobile app — the media scheduler doesn't build its own mobile surface
- Schedule rules stored in StateClient (JSON) — not RDF (rules are configuration, not knowledge)
- Daily plan stored as RDF (queryable by copilot: "what did I listen to this week?")

## Integration Points

- **M037 User Context** — `GET /api/context/current` for rule evaluation, SSE stream for real-time adaptation
- **M037 Mobile App** — displays current suggestion, playback controls, deep links
- **M010 RSS Reader** — feedparser pattern reused for podcast RSS polling
- **App Platform (M009)** — scheduled tasks for polling and plan generation
- **M035 AI Copilot** — queries media consumption data ("what podcasts covered topic X this week?")
- **YouTube Data API v3** — subscription feeds, video metadata
- **Spotify Web API** — playlist access, playback control (Premium), OAuth 2.0
- **Dashboard system (M032)** — media stats embeddable as dashboard blocks

## Open Questions

- **Spotify OAuth scope** — Need `user-read-playback-state`, `user-modify-playback-state` (Premium), `playlist-read-private`. The OAuth flow routes through the App Platform's proxy callback pattern (proven in M018 Google Calendar). Can the App SDK's HttpClient handle OAuth token refresh? The sync apps (M016-M024) all implement their own refresh — may need to extract a shared OAuth helper.
- **Podcast playback** — Should the mobile app have an inline audio player for podcasts, or always deep link to the user's preferred podcast app? Inline is simpler (HTML5 audio tag, enclosure URL from RSS) but loses features (speed control, chapter markers). Deep link requires knowing which podcast app to open.
- **YouTube content selection** — Should the app sync ALL videos from subscribed channels, or let users curate (select specific channels/playlists)? Curated is better UX — automatic "everything from subscriptions" produces too much content. Let users pick channels/playlists to include.
- **Plan granularity** — Hourly slots? 30-minute slots? Variable-length slots based on content duration? Variable-length is most natural (a 45-minute podcast episode gets a 45-minute slot) but complicates the timeline renderer.
- **Context change debounce** — How quickly should the plan react to context changes? Immediate (< 5 seconds) for geofence transitions, but debounced (> 2 minutes) for activity changes to avoid thrashing between "walking" and "stationary" during a meeting.
