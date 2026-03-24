---
slice: S05
milestone: M038
title: "Context-Driven Adaptation + Mobile"
status: done
tasks_completed: 3
tasks_total: 3
test_count: 395
verification: passed
completed_at: 2026-03-23
duration_total: 43m
---

# S05: Context-Driven Adaptation + Mobile — Summary

## What This Slice Delivered

The media scheduler app now subscribes to the platform's M037 context SSE stream and re-evaluates schedule rules on context changes. Users can mark plan entries as completed/skipped/saved from the today view. The mobile React Native app displays the current media suggestion with deep-link playback buttons.

Three capabilities assembled:

1. **Context SSE subscription** (`context_service.py`, ~260 lines) — Persistent background task connects to `GET /api/context/stream` via the SDK's platform httpx client. Debounce: 120s default, immediate for `location_zone` changes (D349). Exponential backoff reconnect (min 2^n, max 300s). `asyncio.Lock` serializes plan regeneration calls. Inspection via `get_context_subscription_status()`.

2. **App wiring + entry status** — `on_startup` spawns the SSE listener as an asyncio task; `on_shutdown` cancels it. `POST /_fragments/entry/{entry_iri}/status` patches entry status via `object.patch`. `GET /_fragments/current-suggestion/json` returns structured JSON for mobile consumption. Today view gains complete/skip/save action buttons per entry with htmx POST wiring.

3. **Mobile Now Playing card** — `MediaSuggestion` interface + `getMediaSuggestion()` API method on `SemPKMClient`. `MediaSuggestionCard` component (~190 lines) with source-type emoji, status badge, time slot display, and `Linking.openURL()` deep-link Play button. Self-contained data fetching — returns null on error/empty for graceful degradation.

## Architecture Patterns Established

- **SSE client pattern for App SDK apps:** `ctx._get_platform_client()` → `client.stream("GET", url)` → `aiter_lines()` → `parse_sse_lines()`. First app to use persistent SSE subscription from inside the SDK.
- **Debounce-with-immediate-override:** asyncio task for debounce timer, cancel+direct-call for priority triggers (location_zone). Reusable for any context-sensitive app feature.
- **Self-contained mobile component pattern:** Component takes `instanceUrl`+`apiKey` props, creates its own `SemPKMClient`, manages loading/error/data states internally, renders nothing on failure.

## What S06 Needs to Know

- Context service uses module-level state (consistent with plan_service, rules_service) — import and call functions directly, no instantiation needed.
- Entry status route returns minimal HTML fragments for htmx `outerHTML` swap — status badge + `ms-entry-done` class.
- JSON suggestion endpoint reuses `TODAY_PLAN_SPARQL` — any changes to plan SPARQL must be reflected there.
- `_prev_context` tracks previous context for location_zone diff detection — no external state store needed.
- The `entryStatus` values `completed`, `skipped`, `saved`, `replaced` are all terminal states excluded from the today view SPARQL.

## Files Changed

| File | Change |
|------|--------|
| `apps/media-scheduler/services/context_service.py` | New — SSE client, debounce, reconnect, lifecycle, inspection |
| `apps/media-scheduler/app.py` | Added context_service import, async lifecycle hooks, entry status route, JSON suggestion endpoint |
| `apps/media-scheduler/frontend/templates/today.html` | Added action buttons (complete/skip/save) with htmx wiring |
| `apps/media-scheduler/frontend/static/styles.css` | Added `.ms-entry-actions`, `.ms-action-btn`, `.ms-entry-done`, `.ms-status-saved` |
| `mobile/src/api/client.ts` | Added `MediaSuggestion` interface + `getMediaSuggestion()` method |
| `mobile/src/components/MediaSuggestion.tsx` | New — Now Playing card component (~190 lines) |
| `mobile/src/app/(app)/(tabs)/index.tsx` | Added `MediaSuggestionCard` to dashboard |
| `backend/tests/test_media_scheduler.py` | Added 74 tests (T01: 45, T02: 29) — 395 total |

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_media_scheduler.py -v` — 395 passed | ✅ |
| 2 | `grep -c "def test_"` ≥ 380 | ✅ 395 |
| 3 | `app.py` AST parse | ✅ |
| 4 | `context_service.py` AST parse | ✅ |
| 5 | JSON endpoint in app.py | ✅ |
| 6 | Entry status route in app.py | ✅ |
| 7 | `getMediaSuggestion` in client.ts | ✅ |
| 8 | `MediaSuggestion` in dashboard index.tsx | ✅ |

## Key Decisions

- Module-level state for context_service (consistent with existing service modules)
- JSONResponse from starlette for the JSON endpoint (cleaner content-type handling)
- Entry status route returns minimal HTML fragment for htmx swap, not full entry re-render
- Mobile component returns null on error — no dashboard clutter when scheduler inactive
- `_prev_context` tracking for location_zone diff detection without external state
