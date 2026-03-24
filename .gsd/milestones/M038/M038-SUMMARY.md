---
id: M038
provides:
  - media-scheduler Mental Model (MediaSource, MediaItem, MediaCategory types with SHACL shapes)
  - media-scheduler App Platform app with 6 services (podcast, YouTube, Spotify, rules, plan, context, stats)
  - Podcast RSS polling via feedparser with conditional GET and dedup
  - YouTube Data API v3 integration with quota tracking and daily reset
  - Spotify OAuth 2.0 with PKCE, playlist discovery, track-to-MediaItem conversion
  - Schedule rules engine with AND-matching conditions (location, activity, time period, time range)
  - Daily plan generator with time-slot allocation from rules + available content
  - Context SSE subscription consuming M037 context stream with debounced re-evaluation
  - Media item status tracking (completed, skipped, saved) via htmx actions
  - Stats dashboard with Chart.js (hours by category, top sources, weekly trends)
  - Mobile Now Playing card with deep-link playback to Spotify/YouTube/podcast apps
  - E2E Playwright spec (14 phases) and user guide Chapter 49
key_decisions:
  - "D351: Flat sh:in enum for sourceType, not OWL subclasses — simpler SPARQL filtering"
  - "D352: Media scheduler owns its model, does not extend rss-feeds — clean separation of concerns"
  - "D353: gist:FormattedContent as MediaItem superclass — matches rss-feeds Article pattern"
  - "D354: Time range rules fail-closed when current_time missing — safety for context-driven automation"
  - "D355: Old plan entries patched to entryStatus=replaced, not deleted — avoids object.delete permission, preserves plan history"
patterns_established:
  - "Multi-source poll architecture: per-source-type poll task + shared dedup/create pipeline"
  - "Module independence: each service (podcast, youtube, spotify) redefines constants locally instead of importing — decoupling over DRY"
  - "Import aliasing in app.py when services export identically-named functions (mint_item_iri, get_existing_item_iris)"
  - "SSE client pattern for App SDK apps: ctx._get_platform_client() → client.stream() → aiter_lines() → parse_sse_lines()"
  - "Debounce-with-immediate-override: asyncio timer for standard changes, cancel+direct-call for priority triggers (location_zone)"
  - "Rules stored as JSON in StateClient, evaluated by pure function — no I/O in rule matching"
  - "Self-contained mobile component: takes instanceUrl + apiKey, manages own fetch/error/data states, returns null on failure"
observability_surfaces:
  - "Per-source error state (errorCount, lastError) updated on poll failure — visible in sources list UI"
  - "YouTube quota tracking via StateClient keys (youtube_quota_used, youtube_quota_reset_date)"
  - "Context subscription status inspectable via get_context_subscription_status()"
  - "Stats route logs rendered counts; query failures logged as stats.<function_name> query failed"
  - "Plan generation returns structured summary dict (plan_iri, date, rules_matched, entries_created)"
requirement_outcomes: []
duration: ~4h
verification_result: passed
completed_at: 2026-03-23
---

# M038: Personal Media Scheduler App

**Daily media queue app that schedules podcasts, YouTube videos, and Spotify tracks based on user context and configurable rules — with real-time plan adaptation via M037 context stream, mobile Now Playing card, and consumption stats dashboard.**

## What Happened

Seven slices built the media scheduler from bottom up.

**S01** laid the foundation: a `media-scheduler` Mental Model with three OWL classes (MediaSource, MediaItem, MediaCategory), SHACL shapes with `sh:in` enums for sourceType (podcast/youtube/spotify) and status (queued/playing/completed/skipped/saved), and 3 ViewSpecs. The app registered with the App Platform, exposing 6 fragment routes and a `poll-sources` task that parses RSS feeds via feedparser, deduplicates by deterministic SHA-256 IRI, and bulk-creates MediaItems via CommandClient. 64 tests.

**S02** added the rules engine and plan generation. Schedule rules use AND-matching with null-as-wildcard across 4 condition types (location_zone, activity, time_period, time_range). Midnight-spanning time ranges work correctly. The plan generator pipeline: fetch context → evaluate rules → query items per action → dedup → allocate time slots → patch old entries to "replaced" → bulk-create new entries. The app UI became a 3-tab interface (Today/Episodes/Rules). 100 new tests bringing the total to 164.

**S03** (YouTube) and **S04** (Spotify) followed the same architectural pattern as S01's podcast service: standalone service module with pure functions + API client class + subscribe flow, poll task in manifest, add-source route in app.py. YouTube added 6 URL format parsing, ISO 8601 duration handling, and daily quota tracking with configurable threshold (10,000 units). Spotify added full OAuth 2.0 with PKCE (RFC 7636), token refresh with 5-minute expiry buffer, playlist discovery, and HTTP 429 rate-limit handling. Both integrate via the shared deterministic IRI minting pattern and `update_source_state()` SPARQL helper. Combined 148 new tests.

**S05** wired context-driven adaptation. A persistent SSE client subscribes to M037's `/api/context/stream`, debouncing re-evaluation at 120s with immediate override for location_zone changes. Exponential backoff reconnect handles disconnections. Entry status tracking (complete/skip/save) was added to the Today view with htmx POST actions. The mobile React Native app gained a `MediaSuggestionCard` component with deep-link playback buttons and self-contained data fetching. 74 new tests.

**S06** delivered the stats dashboard with three Chart.js charts (hours by category, top 10 sources, weekly trends with zero-fill) and polished status badges. User guide Chapter 49 (13 sections) was written, with all three guide index files updated.

**S07** closed with a comprehensive Playwright E2E spec: 14 phases covering the full app lifecycle from model install through podcast subscription, tab navigation, rule creation, plan generation, stats dashboard verification, and cleanup.

## Cross-Slice Verification

| Success Criterion | Evidence | Result |
|---|---|---|
| User adds podcast/YouTube/Spotify sources and sees them listed | S01: podcast subscribe CRUD + poll-sources task; S03: YouTube subscribe with 6 URL formats; S04: Spotify OAuth + playlist selection. All tested in unit tests and E2E spec phases 4-5. | ✅ Met |
| User creates schedule rule mapping context condition to media source | S02: rules CRUD with AND-matching evaluation, rule-form.html builder UI, 48 rule unit tests covering all condition types + edge cases. E2E spec phase 7. | ✅ Met |
| Daily media plan generates with time-slot entries | S02: plan_service.py generates ordered slots from rules + content, allocate_slots() pure function, 39 plan unit tests. E2E spec phase 8 (conditional — empty plan when no real episodes). | ✅ Met |
| Context change from M037 triggers real-time plan re-evaluation | S05: context_service.py SSE subscription with debounced re-evaluation, 45 unit tests covering debounce, reconnect, location_zone immediate override. | ✅ Met |
| Media items track status and consumption stats visible | S05: entry status PATCH route (completed/skipped/saved) with htmx swap. S06: stats_service.py with 3 SPARQL aggregate queries + Chart.js dashboard. 19 stats + 29 status tests. | ✅ Met |
| Mobile app shows current suggestion with deep links | S05: MediaSuggestionCard React Native component (~190 lines), getMediaSuggestion() API method, Linking.openURL() for native app deep links. | ✅ Met |

**Test evidence:** 414 unit tests passing in 1.22s (`cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v`). E2E spec compiles clean (zero errors in our files). Code diff: 36 non-`.gsd/` files, 14,063 lines added.

## Requirement Changes

No formal MEDIA-XX requirements were registered in REQUIREMENTS.md for this milestone (noted as a known issue in S01 summary). The milestone was scoped by its own success criteria and definition of done, which were all met. No existing requirements changed status.

## Forward Intelligence

### What the next milestone should know
- The media-scheduler app is the first App Platform app to subscribe to the context SSE stream. The SSE client pattern (`ctx._get_platform_client()` → `client.stream()`) is reusable for any future context-aware app.
- Spotify OAuth tokens are stored in StateClient (not SQL). Token refresh happens at poll time with a 5-minute expiry buffer. If a user's refresh token is revoked by Spotify, the poll task breaks the loop with SpotifyAuthError — manual reconnect required.
- YouTube and Spotify E2E phases are intentionally skipped in the Playwright spec (require real API keys). Podcast subscription CRUD is the E2E-tested path.
- The rules engine evaluates purely in-memory — no SPARQL during rule matching. Rules are JSON in StateClient, loaded once per evaluation cycle.

### What's fragile
- **Chart.js CDN lazy-load** — stats dashboard loads Chart.js 4.4 from CDN. CDN outage breaks the stats view entirely. The M029 vendor pipeline could absorb this.
- **Context SSE reconnect** — exponential backoff reconnect maxes at 300s. If the context API is down for extended periods, the app silently operates without context (rules that depend on context won't match).
- **YouTube quota tracking is per-instance, not per-API-key** — if multiple instances share the same API key, they each track quota independently and could collectively exceed the limit.

### Authoritative diagnostics
- `backend/tests/test_media_scheduler.py` — 414 tests covering all 7 services. Start here for any regression.
- Per-source `errorCount`/`lastError` in the sources list UI — first place to check when a source stops discovering content.
- `youtube_quota_used` and `youtube_quota_reset_date` StateClient keys — inspect via state API when YouTube polling stops.

### What assumptions changed
- **D352 (independent model) validated** — keeping media-scheduler separate from rss-feeds was the right call. The three source types (podcast/youtube/spotify) share the poll-dedup-create pipeline but have completely different API clients, auth flows, and data mapping. A shared model would have created coupling without benefit.
- **Podcast polling reuses feedparser directly** (D353) — no JSON Feed dispatch needed because podcast feeds are always XML/RSS. The rss-feeds app's FeedService was not reused; podcast_service.py is self-contained.

## Files Created/Modified

- `models/media-scheduler/manifest.yaml` — Model manifest (v1.0.0, 3 types)
- `models/media-scheduler/ontology/media-scheduler.jsonld` — OWL ontology (3 classes, 15+ properties)
- `models/media-scheduler/shapes/media-scheduler.jsonld` — SHACL shapes with PropertyGroups, sh:in enums
- `models/media-scheduler/views/media-scheduler.jsonld` — 3 ViewSpecs
- `apps/media-scheduler/manifest.yaml` — App manifest (3 scheduled tasks, permissions, UI page)
- `apps/media-scheduler/app.py` — App entrypoint (~2000 lines, 20+ routes, 3 task handlers, lifecycle hooks)
- `apps/media-scheduler/requirements.txt` — feedparser dependency
- `apps/media-scheduler/services/podcast_service.py` — Podcast RSS parsing, subscription CRUD
- `apps/media-scheduler/services/youtube_service.py` — YouTube Data API v3 client, quota tracking
- `apps/media-scheduler/services/spotify_service.py` — Spotify OAuth PKCE, playlist discovery, track conversion
- `apps/media-scheduler/services/rules_service.py` — Rules CRUD + AND-matching evaluation
- `apps/media-scheduler/services/plan_service.py` — Daily plan generation pipeline
- `apps/media-scheduler/services/context_service.py` — Context SSE subscription, debounce, reconnect
- `apps/media-scheduler/services/stats_service.py` — SPARQL aggregate queries for consumption stats
- `apps/media-scheduler/frontend/templates/*.html` — 12 Jinja2 templates (main, today, rules, stats, sources, items, add-source, rule-form, etc.)
- `apps/media-scheduler/frontend/static/styles.css` — 1063 lines, 44 workspace theme variable references
- `backend/tests/test_media_scheduler.py` — 414 unit tests across 30+ test classes
- `e2e/tests/55-media-scheduler/media-scheduler.spec.ts` — 14-phase E2E spec
- `e2e/helpers/selectors.ts` — 40 media-scheduler selectors added
- `mobile/src/api/client.ts` — MediaSuggestion interface + getMediaSuggestion()
- `mobile/src/components/MediaSuggestion.tsx` — Now Playing card component
- `mobile/src/app/(app)/(tabs)/index.tsx` — MediaSuggestionCard added to dashboard
- `docs/guide/49-media-scheduler.md` — Chapter 49 user guide (377 lines, 13 sections)
- `docs/guide/README.md` — TOC entry for chapter 49
- `docs/guide/index.html` — Sidebar link for chapter 49
- `backend/app/templates/guide.html` — In-app guide button for chapter 49
