# S05: Context-Driven Adaptation + Mobile

**Goal:** Context changes from M037 trigger real-time plan re-evaluation with debounced re-generation, entry status updates work from the UI, and the mobile app displays the current media suggestion with deep links.
**Demo:** A context change event causes the media scheduler to re-evaluate rules and regenerate the daily plan after a 2-minute debounce (immediate for location zone changes). Users mark entries as completed/skipped/saved from the today view. The mobile dashboard shows the current or next media suggestion with a tap-to-play deep link.

## Must-Haves

- Context SSE subscription client that connects to `/api/context/stream` via the platform httpx client
- 2-minute debounce on context changes; immediate re-evaluation for `location_zone` changes (D349)
- Reconnect-with-backoff on SSE connection loss
- `asyncio.Lock` around `generate_plan()` to prevent concurrent plan generation
- `on_startup` spawns SSE listener as `asyncio.create_task`, `on_shutdown` cancels it
- `POST /_fragments/entry/{entry_iri}/status` route updating `entryStatus` via `object.patch`
- `GET /_fragments/current-suggestion/json` returning structured JSON for mobile consumption
- Today view entry action buttons (complete, skip, save) that htmx-POST to the status route
- Mobile `getMediaSuggestion()` API method and `MediaSuggestion` component on dashboard
- Deep links via `Linking.openURL()` for Spotify, YouTube, and podcast URLs

## Proof Level

- This slice proves: integration (context SSE → rules → plan re-generation pipeline, mobile → JSON API)
- Real runtime required: yes (SSE stream, asyncio lifecycle)
- Human/UAT required: yes (deep links open native apps — can't verify programmatically)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — 380+ tests pass
- `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` returns ≥ 380
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — clean parse
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/context_service.py').read())"` — clean parse
- `grep -q "/_fragments/current-suggestion/json" apps/media-scheduler/app.py` — JSON endpoint exists
- `grep -q "/_fragments/entry/" apps/media-scheduler/app.py` — status route exists
- `grep -q "getMediaSuggestion" mobile/src/api/client.ts` — mobile API method exists
- `grep -q "MediaSuggestion" mobile/src/app/\(app\)/\(tabs\)/index.tsx` — component integrated

## Observability / Diagnostics

- Runtime signals: `context_service` logger (SSE connect/disconnect/reconnect, debounce fire/cancel, plan generation trigger); plan generation summary dict logged on completion
- Inspection surfaces: `get_context_subscription_status()` function returning `{connected, last_event_at, debounce_pending, reconnect_count}`; entry status visible in today SPARQL
- Failure visibility: SSE reconnect count + last error logged; plan generation lock contention logged as warning
- Redaction constraints: none (context data is not secret)

## Integration Closure

- Upstream surfaces consumed: `evaluate_rules()` from `services/rules_service.py`, `generate_plan()` from `services/plan_service.py`, `_get_platform_client()` from SDK `AppContext`, SSE stream at `GET /api/context/stream` from `backend/app/context/router.py`
- New wiring introduced: background asyncio task in app lifecycle, SSE client connection to platform API, JSON API endpoint for mobile consumption
- What remains before milestone is truly usable end-to-end: S06 (stats dashboard + polish), S07 (integration verification)

## Tasks

- [ ] **T01: Context subscription service with SSE client, debounce, and reconnect** `est:1h`
  - Why: Core new capability — the media scheduler must subscribe to the platform's context SSE stream and trigger plan re-generation on context changes. This is the first app to use a persistent SSE subscription from inside the App SDK.
  - Files: `apps/media-scheduler/services/context_service.py`, `backend/tests/test_media_scheduler.py`
  - Do: Create `context_service.py` with: SSE line parser (`parse_sse_line`), debounce manager (2min default, immediate for location_zone per D349), reconnect-with-exponential-backoff, `start_context_listener(ctx)` that spawns asyncio task using `ctx._get_platform_client()` to stream `/api/context/stream`, `stop_context_listener()` that cancels the task, `get_context_subscription_status()` for inspection. Use `asyncio.Lock` around `generate_plan()` calls. Add ~45 tests covering SSE parsing, debounce logic, reconnect behavior, plan trigger, status inspection.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "context" -v` — all context service tests pass
  - Done when: `context_service.py` exists with all functions, 45+ new tests pass, AST parse clean

- [ ] **T02: App wiring — lifecycle hooks, entry status route, JSON suggestion endpoint, today UI buttons** `est:1h`
  - Why: Wires the context service into the app lifecycle, adds the missing entry status mutation route, provides the JSON endpoint the mobile app needs, and gives users UI controls to mark entries complete/skipped/saved.
  - Files: `apps/media-scheduler/app.py`, `apps/media-scheduler/frontend/templates/today.html`, `apps/media-scheduler/frontend/static/styles.css`, `backend/tests/test_media_scheduler.py`
  - Do: (1) Make `on_startup` async, call `start_context_listener(ctx)` from context_service, store task ref. Make `on_shutdown` async, call `stop_context_listener()`. (2) Add `POST /_fragments/entry/{entry_iri}/status` route accepting `status` form field (completed/skipped/saved), calling `object.patch` to update `entryStatus`. (3) Add `GET /_fragments/current-suggestion/json` returning `{title, slot_start, slot_end, status, source_type, source_title, enclosure_url, duration_seconds}`. (4) Add action buttons to each plan entry in today.html: complete (✓), skip (→), save (♡) — each htmx-POSTs to status route and swaps the entry. (5) Add ~25 tests for new routes, lifecycle wiring, and template content.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "status or suggestion_json or lifecycle" -v` — all new tests pass
  - Done when: lifecycle hooks spawn/cancel context listener, status route works, JSON endpoint returns valid JSON, today.html has action buttons, 25+ new tests pass

- [ ] **T03: Mobile Now Playing card with deep links** `est:45m`
  - Why: The mobile dashboard needs to show the current media suggestion so users can tap-to-play from their phone. This completes the mobile integration pillar of S05.
  - Files: `mobile/src/api/client.ts`, `mobile/src/components/MediaSuggestion.tsx`, `mobile/src/app/(app)/(tabs)/index.tsx`
  - Do: (1) Add `MediaSuggestion` interface to client.ts matching the JSON endpoint shape. Add `getMediaSuggestion()` method calling `GET /app/media-scheduler/_fragments/current-suggestion/json`. (2) Create `MediaSuggestion.tsx` component: fetches suggestion on mount, shows card with title/time/source, "Play" button calls `Linking.openURL(enclosure_url)`, handles empty/error states, uses source-type-specific icons (🎙️ podcast, 🎬 youtube, 🎵 spotify). (3) Import and render `MediaSuggestionCard` in dashboard index.tsx between the monitoring status row and the "Server Context" section header. (4) Add ~10 verification assertions (grep checks for key patterns since these are React Native components without a test runner in the current setup).
  - Verify: `grep -q "getMediaSuggestion" mobile/src/api/client.ts && grep -q "MediaSuggestion" mobile/src/components/MediaSuggestion.tsx && grep -q "MediaSuggestion" mobile/src/app/\(app\)/\(tabs\)/index.tsx`
  - Done when: API client has `getMediaSuggestion()`, component file exists with deep link handling, dashboard renders the component, all 3 grep checks pass

## Files Likely Touched

- `apps/media-scheduler/services/context_service.py` (new)
- `apps/media-scheduler/app.py`
- `apps/media-scheduler/frontend/templates/today.html`
- `apps/media-scheduler/frontend/static/styles.css`
- `mobile/src/api/client.ts`
- `mobile/src/components/MediaSuggestion.tsx` (new)
- `mobile/src/app/(app)/(tabs)/index.tsx`
- `backend/tests/test_media_scheduler.py`
