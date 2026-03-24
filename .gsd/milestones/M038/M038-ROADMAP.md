# M038: Personal Media Scheduler App

**Vision:** A SemPKM platform app that generates a personalized daily media queue — scheduling podcasts, YouTube videos, and Spotify playlists based on user context (location, activity, time-of-day) and configurable rules. Context changes from M037 trigger real-time plan adaptation.

## Success Criteria

- User adds a podcast RSS feed, YouTube channel, and Spotify playlist as media sources and sees them listed in the Media Scheduler app
- User creates a schedule rule mapping a context condition (e.g. "commuting") to a media source and the rule evaluates correctly on context change
- Daily media plan generates with time-slot entries drawn from media source content
- Context change from M037 triggers real-time plan re-evaluation and the current suggestion updates
- Media items track status (queued, completed, skipped, saved) and consumption stats are visible
- Mobile app (M037) shows current media suggestion with deep links to native apps

## Key Risks / Unknowns

- **Spotify OAuth 2.0 with PKCE through App SDK** — The app needs user-level OAuth with token refresh. The Google Calendar OAuth pattern is proven but Spotify has its own quirks (token expiry, scope requirements, Premium vs Free tier detection). If this fails, the entire Spotify integration is blocked.
- **Context-driven plan adaptation** — The rules engine must subscribe to M037 context SSE stream and re-evaluate on every change. This is a new pattern (no existing app subscribes to the context stream). If context changes are too frequent, the re-evaluation could be expensive or cause UI thrashing.
- **YouTube Data API v3 quota** — 10,000 units/day is adequate for polling, but getting the API key provisioned and testing against real data requires the key early. If quota management is wrong, the app silently stops discovering new content.

## Proof Strategy

- Spotify OAuth 2.0 → retire in S04 by proving token exchange, playlist listing, and Premium detection with real Spotify API
- Context-driven plan adaptation → retire in S05 by proving rule evaluation against live context SSE events with debounced re-evaluation
- YouTube API quota → retire in S03 by proving video listing against real YouTube Data API with quota tracking

## Verification Classes

- Contract verification: pytest unit tests for rules engine, plan generation, media item CRUD, feed parsing, API clients
- Integration verification: scheduled task execution (poll-sources, generate-plan), context SSE subscription, SPARQL queries for media data
- Operational verification: daily plan regeneration survives Docker restart, API errors for individual sources don't block other sources, stale context detection
- UAT / human verification: today's plan view shows correct time slots, mobile app displays current suggestion, deep links open correct native app

## Milestone Definition of Done

This milestone is complete only when all are true:

- Media sources (podcast, YouTube, Spotify) can be added and poll for new content
- Schedule rules map context conditions to media sources and evaluate correctly
- Daily plan generates with ordered time-slot entries drawn from discovered content
- Context changes from M037 trigger plan re-evaluation and current suggestion updates
- Media item status tracking (completed, skipped, saved) works through the UI
- Mobile app shows current suggestion with playback controls or deep links
- Success criteria are verified against live Docker environment with real API data

## Requirement Coverage

- Covers: new MEDIA-01 through MEDIA-10 (defined by this milestone's scope)
- Partially covers: CTX-05 (auto-persona switch — media scheduler consumes context events, extends the context ecosystem)
- Leaves for later: AI-powered media recommendations (M035 copilot integration), additional streaming services, offline caching
- Orphan risks: none — all Active requirements mapped to slices

## Slices

- [x] **S01: Mental Model + Podcast Sources** `risk:high` `depends:[]`
  > After this: user installs the media-scheduler model, opens the Media Scheduler app from the sidebar, subscribes to a podcast RSS feed, and sees discovered episodes listed as MediaItem objects in the triplestore. Podcast polling runs as a scheduled task.

- [x] **S02: Schedule Rules Engine + Daily Plan Generation** `risk:high` `depends:[S01]`
  > After this: user creates schedule rules (e.g. "when commuting, play podcasts") via a rule builder UI, triggers daily plan generation, and sees an ordered time-slot plan for today. Plan is stored as RDF and visible in the app's Today view.

- [x] **S03: YouTube Integration** `risk:medium` `depends:[S01]`
  > After this: user adds a YouTube channel or playlist as a media source, the app polls YouTube Data API for new videos, and discovered videos appear as MediaItems in the daily plan alongside podcast episodes.

- [x] **S04: Spotify Integration** `risk:high` `depends:[S01]`
  > After this: user connects their Spotify account via OAuth, selects playlists as media sources, and Spotify tracks appear as MediaItems. Premium users see playback control hints; Free users see deep links.

- [x] **S05: Context-Driven Adaptation + Mobile** `risk:medium` `depends:[S02,S04]`
  > After this: context changes from M037 trigger real-time plan re-evaluation. The daily plan adapts when the user starts commuting or enters focus mode. The mobile app displays the current media suggestion with deep links to Spotify/YouTube/podcast apps.

- [x] **S06: Stats Dashboard + Polish** `risk:low` `depends:[S05]`
  > After this: user sees media consumption stats (hours per category, most-played sources, weekly trends) in a stats view. Media item status tracking (completed, skipped, saved) is polished. The full app is documented in the user guide.

- [ ] **S07: Integration Verification** `risk:low` `depends:[S06]`
  > After this: E2E tests prove the assembled system works end-to-end — podcast polling discovers episodes, YouTube/Spotify sources sync, rules evaluate against context, daily plan generates and adapts, mobile app displays suggestion. All verification classes pass.

## Boundary Map

### S01 → S02

Produces:
- `media-scheduler` Mental Model installed with MediaSource, MediaItem, MediaCategory, MediaScheduleRule, DailyMediaPlan types and SHACL shapes
- `media-scheduler` app registered with App Platform: manifest, SDK entry point, scheduled task `poll-sources`
- Podcast subscription CRUD routes: `/_fragments/sources` (GET list), `/_fragments/sources/add-podcast` (POST)
- MediaItem creation via CommandClient with deterministic IRI minting (SHA-256 of source + episode ID)
- SPARQL queries for media source listing and media item listing by source
- FeedService reuse from RSS Reader: feedparser, conditional GET, enclosure URL extraction for audio

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- MediaSource type with `sourceType` enum field (podcast, youtube, spotify)
- Deterministic IRI minting pattern for media items (`urn:sempkm:app:media-scheduler:item-{hash}`)
- SPARQL query patterns for source listing and item dedup

Consumes:
- nothing (first slice)

### S01 → S04

Produces:
- Same as S01 → S03

Consumes:
- nothing (first slice)

### S02 → S05

Produces:
- Schedule rules CRUD stored in StateClient (JSON): conditions (location_zone, activity, time_period, time_range), action (source_type, source_iri, category)
- RulesEngine.evaluate(context) → list of matching rules with priority ordering
- DailyPlanGenerator that builds time-slot entries from rules + available content
- Today's plan view UI fragment
- `GET /_fragments/current-suggestion` endpoint returning the current best media item

Consumes:
- S01: MediaSource and MediaItem types in triplestore, `poll-sources` task populating items

### S04 → S05

Produces:
- Spotify OAuth tokens in StateClient (access_token, refresh_token, token_expiry)
- Spotify playlist track listing via SpotifyClient
- Spotify deep link format (`spotify:track:{id}`)

Consumes:
- S01: MediaSource type, deterministic IRI minting

### S05 → S06

Produces:
- Context SSE subscription in app startup hook
- Real-time plan re-evaluation on context change with 2-minute debounce
- Mobile-facing `/_fragments/current-suggestion` with deep links
- Media item status updates (completed, skipped, saved) via `object.patch`

Consumes:
- S02: RulesEngine, DailyPlanGenerator, Today view
- S04: Spotify tokens and deep links

### S06 → S07

Produces:
- Stats SPARQL queries: hours per category, most-played sources, weekly trends
- Stats view fragment with Chart.js
- User guide chapter
- Polished media item status toggle UI

Consumes:
- S05: Full media lifecycle (sources, rules, plan, adaptation, status tracking)
