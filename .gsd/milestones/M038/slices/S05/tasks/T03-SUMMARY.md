---
id: T03
parent: S05
milestone: M038
provides:
  - MediaSuggestion interface and getMediaSuggestion() API method on SemPKMClient
  - MediaSuggestionCard React Native component with deep-link playback
  - Dashboard integration showing current/next media suggestion
key_files:
  - mobile/src/api/client.ts
  - mobile/src/components/MediaSuggestion.tsx
  - mobile/src/app/(app)/(tabs)/index.tsx
key_decisions:
  - Compute creds via parseSession() once in component body and reuse in JSX for MediaSuggestionCard props — avoids IIFE in JSX or duplicate parsing
  - Component returns null for error/empty/none states — no dashboard clutter when media scheduler isn't installed or has no plan
patterns_established:
  - Self-contained data-fetching component pattern: component takes instanceUrl+apiKey props, creates its own SemPKMClient, manages loading/error/data states internally, renders nothing on failure
observability_surfaces:
  - console.warn on API fetch failure with status code and detail
  - console.warn on Linking.openURL failure for deep links
  - Component renders null on error — absence is the visual indicator
duration: 10m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Mobile Now Playing card with deep links

**Added MediaSuggestion interface, getMediaSuggestion() API method, and Now Playing card component with source-type emoji, time slots, status badges, and deep-link Play button to the mobile dashboard.**

## What Happened

1. **API layer** (`client.ts`) — Added `MediaSuggestion` interface with all 8 fields matching the T02 JSON endpoint shape (title, slot_start, slot_end, status union, source_type, source_title, enclosure_url, duration_seconds). Added `getMediaSuggestion()` method to `SemPKMClient` calling the `/app/media-scheduler/_fragments/current-suggestion/json` endpoint.

2. **Component** (`MediaSuggestion.tsx`, ~190 lines) — Self-contained card that fetches on mount, shows an inline spinner during load, returns null for error/empty/none states (graceful degradation), and renders a card with: status badge ("▶ Now playing" green / "⏭ Up next" blue), source emoji (🎙️/🎬/🎵) + source title, entry title, time slot, duration, and a "Play in {source}" button that calls `Linking.openURL(enclosure_url)`. Both fetch and deep-link errors are caught and logged via console.warn.

3. **Dashboard integration** (`index.tsx`) — Imported `MediaSuggestionCard`, computed `creds` once via `parseSession(session)` at component body level, rendered the card between the monitoring status row and "Server Context" section header. Conditional on `creds` being non-null.

## Verification

- All 4 task-level grep checks pass (getMediaSuggestion, export interface, Linking.openURL, dashboard integration)
- 395 backend tests pass (no regressions from prior T01/T02 work)
- All slice-level checks pass: app.py clean parse, context_service.py clean parse, JSON endpoint exists, entry status route exists, test count ≥ 380

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "getMediaSuggestion" mobile/src/api/client.ts` | 0 | ✅ pass | <0.1s |
| 2 | `grep -q "export interface MediaSuggestion" mobile/src/api/client.ts` | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "Linking.openURL" mobile/src/components/MediaSuggestion.tsx` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "MediaSuggestion" mobile/src/app/\(app\)/\(tabs\)/index.tsx` | 0 | ✅ pass | <0.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass (395) | 1.21s |
| 6 | `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` → 395 | 0 | ✅ pass | <0.1s |
| 7 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <0.1s |
| 8 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/context_service.py').read())"` | 0 | ✅ pass | <0.1s |
| 9 | `grep -q "/_fragments/current-suggestion/json" apps/media-scheduler/app.py` | 0 | ✅ pass | <0.1s |
| 10 | `grep -q "/_fragments/entry/" apps/media-scheduler/app.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Fetch failures:** `console.warn('Media suggestion fetch failed: {status} {detail}')` in MediaSuggestionCard — visible in Expo dev console
- **Deep link failures:** `console.warn('Failed to open media URL:', err)` when Linking.openURL throws
- **Visual indicator:** Component absence on dashboard = endpoint unreachable or no plan active
- **Runtime:** Card re-fetches on `instanceUrl`/`apiKey` prop change via useEffect dependency array

## Deviations

- Extracted `creds = parseSession(session)` to the component body level in `index.tsx` instead of using an IIFE in JSX — cleaner, same behavior.
- Component is ~190 lines instead of the planned ~130 — the extra is from accessibility props (`accessibilityRole`, `accessibilityLabel`), the `formatDuration` helper, and the `sourceLabel` helper.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/api/client.ts` — Added `MediaSuggestion` interface (8 fields) and `getMediaSuggestion()` method on SemPKMClient (~30 lines added)
- `mobile/src/components/MediaSuggestion.tsx` — New file (~190 lines): self-contained Now Playing card with fetch, error handling, deep-link Play button, source-type emoji, status badges
- `mobile/src/app/(app)/(tabs)/index.tsx` — Added MediaSuggestionCard import, top-level creds parsing, card rendered between monitoring row and Server Context section (~10 lines added)
- `.gsd/milestones/M038/slices/S05/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
