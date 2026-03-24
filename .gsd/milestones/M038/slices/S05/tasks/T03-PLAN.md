---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T03: Mobile Now Playing card with deep links

**Slice:** S05 — Context-Driven Adaptation + Mobile
**Milestone:** M038

## Description

Add a "Now Playing" card to the mobile dashboard that fetches the current media suggestion from the platform and lets users tap to play in their native app (Spotify, YouTube, or podcast app). This completes the mobile integration pillar of S05.

The mobile app uses Expo (React Native) with `expo-linking` already installed. The `SemPKMClient` class in `mobile/src/api/client.ts` has a clean `request<T>()` generic method. The dashboard is at `mobile/src/app/(app)/(tabs)/index.tsx`.

The JSON endpoint from T02 is at `GET /app/media-scheduler/_fragments/current-suggestion/json` and returns:
```json
{
  "title": "Episode Title",
  "slot_start": "14:00",
  "slot_end": "14:30",
  "status": "now" | "next" | "none",
  "source_type": "podcast" | "youtube" | "spotify",
  "source_title": "Source Name",
  "enclosure_url": "https://...",
  "duration_seconds": 1800
}
```

Per D350, all media types open via deep links — no embedded player.

## Steps

1. **Add types and API method to `mobile/src/api/client.ts`:**
   - Add `MediaSuggestion` interface matching the JSON endpoint shape: `title: string`, `slot_start: string`, `slot_end: string`, `status: 'now' | 'next' | 'none'`, `source_type: 'podcast' | 'youtube' | 'spotify' | null`, `source_title: string | null`, `enclosure_url: string | null`, `duration_seconds: number | null`.
   - Export `MediaSuggestion` from the module.
   - Add `getMediaSuggestion()` method to `SemPKMClient`: calls `this.request<MediaSuggestion>('/app/media-scheduler/_fragments/current-suggestion/json')`. Returns the `MediaSuggestion` object.

2. **Create `mobile/src/components/MediaSuggestion.tsx`:**
   - Props: `instanceUrl: string`, `apiKey: string`.
   - State: `suggestion: MediaSuggestion | null`, `loading: boolean`, `error: string | null`.
   - On mount: create `SemPKMClient`, call `getMediaSuggestion()`, update state. Catch errors gracefully (network failures, 404 if app not installed — show nothing, don't crash).
   - Render:
     - If loading: small inline spinner.
     - If error or suggestion is null or `suggestion.status === 'none'`: render nothing (return null — don't clutter dashboard if no plan exists).
     - Otherwise: a card with:
       - Source type emoji (🎙️ podcast, 🎬 youtube, 🎵 spotify) + source title
       - Entry title (main text)
       - Time slot: `slot_start – slot_end`
       - Status label: "Now playing" (green) or "Up next" (blue)
       - "Play" button: calls `Linking.openURL(suggestion.enclosure_url)`. Disabled/hidden if `enclosure_url` is null.
   - Import `Linking` from `expo-linking`.
   - Style: match existing field card pattern from dashboard (white card, 10px border radius, hairline border, same font sizes).

3. **Integrate into dashboard at `mobile/src/app/(app)/(tabs)/index.tsx`:**
   - Import `MediaSuggestionCard` from `@/components/MediaSuggestion`.
   - Extract `instanceUrl` and `apiKey` from session using `parseSession(session)`.
   - Render `<MediaSuggestionCard instanceUrl={creds.instanceUrl} apiKey={creds.apiKey} />` between the monitoring status row and the "Server Context" section header.
   - The component handles its own loading/error/empty states, so no conditional wrapper needed in the dashboard.

4. **Verify all files parse and contain expected patterns:**
   - `grep -q "getMediaSuggestion" mobile/src/api/client.ts`
   - `grep -q "MediaSuggestion" mobile/src/components/MediaSuggestion.tsx`
   - `grep -q "Linking.openURL" mobile/src/components/MediaSuggestion.tsx`
   - `grep -q "MediaSuggestion" mobile/src/app/\(app\)/\(tabs\)/index.tsx`

## Must-Haves

- [ ] `MediaSuggestion` interface exported from `client.ts`
- [ ] `getMediaSuggestion()` method on `SemPKMClient` class
- [ ] `MediaSuggestion.tsx` component handles loading, error, empty, and active states
- [ ] Deep link via `Linking.openURL(enclosure_url)` for play action
- [ ] Source-type-specific emoji/icon (podcast, youtube, spotify)
- [ ] Component renders on dashboard between monitoring row and server context
- [ ] Graceful degradation: returns null when no suggestion, doesn't crash on network error

## Verification

- `grep -q "getMediaSuggestion" mobile/src/api/client.ts` — API method exists
- `grep -q "export interface MediaSuggestion" mobile/src/api/client.ts` — type exported
- `grep -q "Linking.openURL" mobile/src/components/MediaSuggestion.tsx` — deep link wired
- `grep -q "MediaSuggestion" mobile/src/app/\(app\)/\(tabs\)/index.tsx` — integrated in dashboard

## Inputs

- `mobile/src/api/client.ts` — existing SemPKMClient with `request<T>()` pattern, ~300 lines
- `mobile/src/app/(app)/(tabs)/index.tsx` — existing dashboard with context display, ~310 lines
- `apps/media-scheduler/app.py` — T02 output: JSON endpoint shape at `/_fragments/current-suggestion/json`

## Expected Output

- `mobile/src/api/client.ts` — modified: `MediaSuggestion` interface + `getMediaSuggestion()` method (~25 lines added)
- `mobile/src/components/MediaSuggestion.tsx` — new file (~130 lines) with Now Playing card component
- `mobile/src/app/(app)/(tabs)/index.tsx` — modified: import + render MediaSuggestionCard (~5 lines added)
