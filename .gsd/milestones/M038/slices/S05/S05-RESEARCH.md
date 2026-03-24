# S05 Research: Context-Driven Adaptation + Mobile

## Summary

This slice wires two things: (1) the media-scheduler app subscribes to M037's context SSE stream and re-evaluates schedule rules on context changes, triggering plan re-generation with debounce, and (2) the mobile app gets a "Now Playing" section on its dashboard that fetches the current media suggestion with deep links.

The work is medium complexity. The rules engine and plan generator are fully built (S02). The SSE broadcast infrastructure is proven (context-indicator.js, ContextBroadcast). The mobile app is Expo/React Native with `expo-linking` already installed. No new libraries needed. The main challenge is async background task management in the App SDK — no app has done a persistent SSE subscription from inside the SDK before.

## Recommendation

Three tasks:

1. **Context subscription service + app wiring** — New `context_service.py` that opens an SSE stream to `/api/context/stream` via the platform client (`ctx._get_platform_client()` or `ctx.platform_url`), parses events, debounces, and calls `generate_plan()` with `context_override`. Wire into `on_startup`/`on_shutdown` lifecycle hooks. Add media item status update routes (completed/skipped/saved). Tests for debounce logic, SSE parsing, status updates.

2. **Mobile "Now Playing" card** — Add `getMediaSuggestion()` to the mobile API client and a `MediaSuggestion` component on the dashboard tab. Uses `expo-linking` for deep links to Spotify/YouTube/podcast apps. Polls the current-suggestion endpoint (needs a JSON variant, not HTML). Tests for the component and API method.

3. **Current-suggestion JSON endpoint + enhanced template** — Add a `/_fragments/current-suggestion/json` route returning structured JSON (title, slot times, enclosure URL, source type, source title, duration). Enhance the HTML current-suggestion template with source type badges and deep link buttons. Wire the plan re-evaluation to emit an SSE event or update the current-suggestion cache. Tests for JSON endpoint, status update propagation.

## Implementation Landscape

### Files to Create

| File | Purpose |
|------|---------|
| `apps/media-scheduler/services/context_service.py` | SSE subscription client, debounced re-evaluation, event parsing |
| `mobile/src/components/MediaSuggestion.tsx` | Now Playing card component with deep links |

### Files to Modify

| File | Change |
|------|--------|
| `apps/media-scheduler/app.py` | Add `on_startup` SSE subscription, `on_shutdown` teardown, status update routes, JSON current-suggestion endpoint |
| `apps/media-scheduler/manifest.yaml` | No task changes needed (SSE is persistent connection, not scheduled task) |
| `mobile/src/api/client.ts` | Add `getMediaSuggestion()` method + `MediaSuggestion` type |
| `mobile/src/app/(app)/(tabs)/index.tsx` | Add MediaSuggestion card to dashboard |
| `backend/tests/test_media_scheduler.py` | ~80 new tests for context service, status updates, JSON endpoint, mobile API |

### Existing Code to Reuse

| What | Where | How |
|------|-------|-----|
| `evaluate_rules(rules, context)` | `services/rules_service.py` | Pure function — call directly on each SSE event |
| `generate_plan(ctx, context_override=...)` | `services/plan_service.py` | Pass context from SSE event as `context_override` |
| `ContextBroadcast` + SSE protocol | `backend/app/context/broadcast.py` + `router.py` | Reference for SSE event format (`event: context_update\ndata: {json}\n\n`) |
| `context-indicator.js` SSE pattern | `frontend/static/js/context-indicator.js` | Reference for client-side SSE parsing (EventSource) |
| `current_suggestion_fragment()` | `app.py` lines 1730-1775 | Existing SPARQL + logic, adapt for JSON output |
| App SDK lifecycle hooks | `sdk/sempkm_app_sdk/app.py` | `@app.on_startup` / `@app.on_shutdown` decorators |
| `expo-linking` | `mobile/package.json` | Already installed — `Linking.openURL()` for deep links |

## Key Technical Findings

### 1. SSE Subscription Architecture

No app has subscribed to the context SSE stream before — this is a new pattern. The SSE endpoint at `GET /api/context/stream` requires authentication (`Bearer` token) and emits `context_update` events with JSON payloads matching the context model fields (`location_zone`, `activity`, `time_period`, `calendar_event`, `calendar_busy`, `device_id`, `is_stale`, `updated_at`).

**Approach:** Use `httpx` directly (not the SDK's HttpClient, which is for external domains only). The platform client from `ctx._get_platform_client()` has the correct `base_url` and auth headers. Open a streaming GET to `/api/context/stream` in an `asyncio.Task` spawned from `on_startup`. Parse SSE text format line-by-line (`event:`, `data:`, blank line = dispatch).

**Lifecycle:** The background task must be cancelled on `on_shutdown`. Store the task reference on the app module or in the ctx. The runner calls the shutdown lifecycle handler on SIGTERM.

**Critical detail:** The `on_startup` handler in the SDK (`app.py` line 63) calls `handler(ctx)` — if it's async and returns a coroutine, the runner awaits it. But we need to spawn a *background* task, not block startup. Solution: call `asyncio.create_task()` inside `on_startup` and store the task reference.

### 2. Debounce Strategy (per D349 planning)

Context changes can be frequent (location ping every few seconds during movement). The roadmap specifies 2-minute debounce for plan re-evaluation.

**Approach:** When an SSE event arrives, record the timestamp and the new context dict. If a debounce timer is already running, cancel it and restart. After 2 minutes of no new events, execute `generate_plan(ctx, context_override=last_context)`. This is a standard asyncio debounce pattern:

```python
_debounce_task: asyncio.Task | None = None
_last_context: dict = {}

async def _on_context_event(ctx, context_data):
    global _debounce_task, _last_context
    _last_context = context_data
    if _debounce_task and not _debounce_task.done():
        _debounce_task.cancel()
    _debounce_task = asyncio.create_task(_debounce_regenerate(ctx))

async def _debounce_regenerate(ctx):
    await asyncio.sleep(120)  # 2 minutes
    await generate_plan(ctx, context_override=_last_context)
```

### 3. `fetch_context()` Uses External HttpClient — Bug or Feature?

`plan_service.py:337` calls `fetch_context(ctx.http)` where `ctx.http` is the external HttpClient (no base URL, domain-gated). The URL `/api/context/current` is relative. In production this likely fails silently (returns `{}` due to the try/except in `fetch_context`), and plan generation proceeds with an empty context (no rules match → empty plan).

**S05 approach:** Use `context_override` parameter in `generate_plan()` to bypass `fetch_context()` entirely. The SSE event already contains the full context data — no need for an extra HTTP call.

### 4. Media Item Status Updates

The plan entries have `entryStatus` (pending/completed/skipped/replaced) but there's no route to update an individual entry's status from the UI. S05 needs:

- `POST /_fragments/entry/{entry_iri}/status` — accepts `status` form field, calls `object.patch` to update `entryStatus`
- Status values: `completed`, `skipped`, `saved` (new — for "save for later")
- The today.html template needs action buttons per entry (mark complete, skip, save)

### 5. Mobile Integration — JSON Endpoint

The existing `/_fragments/current-suggestion` returns HTML. The mobile app needs JSON. Two options:

- **Option A:** New route `/_fragments/current-suggestion/json` returning structured JSON
- **Option B:** Accept header content negotiation on the existing route

Option A is cleaner — the mobile client calls a dedicated JSON endpoint. The response shape:

```json
{
  "title": "Episode Title",
  "slot_start": "14:00",
  "slot_end": "14:30",
  "status": "now",
  "source_type": "podcast",
  "source_title": "Podcast Name",
  "enclosure_url": "https://...",
  "duration_seconds": 1800
}
```

### 6. Mobile Deep Links

`expo-linking` is already in `package.json`. The `enclosureUrl` field on MediaItems stores:
- Podcasts: direct audio URL (e.g. `https://cdn.example.com/episode.mp3`)
- YouTube: watch URL (e.g. `https://www.youtube.com/watch?v=abc123`)
- Spotify: web URL (e.g. `https://open.spotify.com/track/abc123`)

For deep linking on mobile:
- YouTube URLs open the YouTube app on both iOS and Android (universal links)
- Spotify web URLs open the Spotify app (universal links)
- Podcast audio URLs — open in browser or a basic audio player. The roadmap suggests HTML5 audio for podcast playback in the mobile WebView, but deep linking to a podcast app requires knowing the podcast's iTunes ID or overcast URL. For v1, open the audio URL in the browser.

`Linking.openURL(enclosureUrl)` handles all three — the OS resolves YouTube/Spotify URLs to their native apps.

### 7. App SDK `on_startup` Async Limitation

The SDK runner at `runner.py:119-127` dispatches lifecycle hooks through the FastAPI `/_lifecycle/{hook}` endpoint. The handler runs `handler(ctx)` and if it's a coroutine, awaits it. This means `on_startup` can be async, but it runs *synchronously* in the request handler — we can't block it with a long-running SSE subscription.

**Solution:** In `on_startup`, spawn the SSE listener as an `asyncio.create_task()`. Return immediately. Store the task reference for cancellation in `on_shutdown`.

### 8. Test Count Target

321 existing tests. S05 should add ~60-80 new tests covering:
- SSE event parsing (text→dict) — ~5 tests
- Debounce logic (cancel/restart/fire) — ~10 tests  
- Plan re-generation on context change — ~10 tests
- Media item status update route — ~10 tests
- JSON current-suggestion endpoint — ~10 tests
- Mobile API client method — ~5 tests (in TS, or as Python equivalents)
- Entry status button template — ~5 tests
- Error handling (SSE disconnect/reconnect, stale context) — ~10 tests

Target: 380+ total tests.

## Constraints

- The App SDK has no built-in SSE client — must use `httpx` streaming directly or raw `asyncio` with the platform client
- The `on_startup` lifecycle hook is called via an HTTP POST from the platform, not during app process initialization — there's no event loop available at module import time
- The 2-minute debounce must survive rapid context changes without accumulating stale tasks
- Deep link URLs vary by source type — no uniform URI scheme across podcast/YouTube/Spotify
- Mobile app is Expo (React Native) — no direct access to the app's internal SSE stream (goes through the platform API, not the app proxy)

## Risks

- **SSE connection lifecycle:** If the SSE connection to `/api/context/stream` drops (server restart, network hiccup), the app needs reconnection logic. The `context-indicator.js` relies on EventSource auto-reconnect, but the Python httpx streaming client does not. Need explicit reconnect-with-backoff.
- **Concurrent plan generation:** If the debounce fires while a plan generation is already running (from the scheduled `generate-plan` task), both could create overlapping plan entries. Need a simple lock (asyncio.Lock) around `generate_plan()`.
