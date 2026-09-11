<!-- GENERATED FILE. Do not edit. Source: models/media-scheduler/README.md. Regenerate with: python3 scripts/sync-model-docs.py -->
> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the `media-scheduler` Mental Model archive. The same text is available in the app under **Admin > Models > Media Scheduler > Documentation** and at `/api/models/media-scheduler/docs`. To change it, edit `models/media-scheduler/README.md` and run `scripts/sync-model-docs.py`.

# Media Scheduler

**Model ID:** `media-scheduler` · **Namespace:** `urn:sempkm:model:media-scheduler:` · **Prefix:** `ms:`

The Media Scheduler model defines the types behind the **Media Scheduler** app, which polls
podcast feeds, YouTube channels, and Spotify playlists, stores what it finds as typed objects,
and builds a daily listening plan from schedule rules and your current context. The model ships
no seed data — the app populates it.

## Types

### MediaSource

A content source such as a podcast feed, YouTube channel, or Spotify playlist.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Display name of the source |
| Source Type | enum | ✓ | `podcast`, `youtube`, `spotify` |
| Feed URL | URI | ✓ | URL of the RSS/Atom feed or channel/playlist |
| Category | → MediaCategory | | Category this source belongs to |
| Last Polled | dateTime | | When this source was last polled |
| Error Count | integer | | Consecutive polling errors |
| Last Error | string | | Most recent polling error |
| ETag / Last-Modified Header | string | | HTTP caching headers for conditional GET |

### MediaItem

An individual episode, video, or track discovered from a media source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Title of the episode, video, or track |
| Enclosure URL | URI | | URL of the audio or video file |
| External ID | string | | Identifier from the source (episode GUID, video ID) |
| Duration | integer | | Duration in seconds |
| Thumbnail URL | URI | | Episode or video thumbnail |
| Published | dateTime | | Publication date |
| Description | string | | Episode or video description |
| Media Source | → MediaSource | ✓ | The source this item was discovered from |
| Status | enum | ✓ | `queued`, `playing`, `completed`, `skipped`, `saved` (default: `queued`) |

### MediaCategory

A user-defined grouping for media sources (e.g. news, podcasts, music, learning).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Name of the category |
| Description | string | | Description of the category |
| Color | string | | Display color (hex code) |

### DailyMediaPlan

A generated daily schedule of media items assigned to time slots based on context rules.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Date | date | ✓ | The date this plan covers |
| Created | dateTime | | When this plan was generated |
| Plan Status | enum | | `active`, `completed`, `regenerating` (default: `active`) |

### PlanEntry

A single time-slotted media item within a daily plan.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Plan | → DailyMediaPlan | ✓ | The daily plan this entry belongs to |
| Media Item | → MediaItem | ✓ | The media item scheduled in this slot |
| Slot Start / Slot End | string | | Slot times in `HH:MM` |
| Slot Order | integer | | Ordinal position within the plan |
| Entry Status | enum | | `pending`, `active`, `completed`, `skipped`, `replaced` (default: `pending`) |
| Rule ID | string | | UUID of the schedule rule that generated this entry |

Schedule rules themselves live in the app's own store, not in the knowledge graph; the Rule ID
on a plan entry is the link back.

## Relationships

```
MediaSource ──category──▸ MediaCategory
MediaItem ──mediaSource──▸ MediaSource
PlanEntry ──plan──▸ DailyMediaPlan
PlanEntry ──mediaItem──▸ MediaItem
```

## Views

| View | Description |
|------|-------------|
| Media Items Table / Cards | All discovered episodes, videos, and tracks |
| Media Sources Table | Subscribed sources with polling status |

## Validation rules

None. Field constraints come from the SHACL shapes only.

## Installation

Install this model **before** the Media Scheduler app: go to **Admin > Models**, pick **Media
Scheduler** from the bundled catalog (or enter `/app/models/media-scheduler`) and click
**Install**. Then install the app from **Admin > Applications** with the path
`/app/apps/media-scheduler`. See the user guide chapter *Media Scheduler* for sources, schedule
rules, the daily plan, and stats.

---

**Back:** [Chapter 11: Mental Model Catalog](11-mental-model-catalog.md)
