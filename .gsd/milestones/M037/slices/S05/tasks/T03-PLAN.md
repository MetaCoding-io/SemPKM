---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T03: Time-period service, context orchestrator hook, and dashboard wiring

**Slice:** S05 — Mobile Calendar & Activity Detection
**Milestone:** M037

## Description

Build the time-of-day classification service, the context orchestrator hook that coordinates all three enrichment services (calendar, activity, time-period) into rate-limit-aware batched context updates, and wire everything into the dashboard screen.

The orchestrator is the critical piece — it prevents three independent services from each calling `updateContext()` separately (which would hit the backend's 12/min rate limit). Instead, it collects all changed fields and pushes a single batched update at most once every 30 seconds, only when at least one field has changed.

## Steps

1. Create `mobile/src/services/time-period.ts` with:
   - `TimePeriod` type alias: `'morning' | 'work_hours' | 'evening' | 'night'`
   - `getTimePeriod(date?: Date)` — returns `TimePeriod` based on the current hour. Defaults: 5:00–8:59 → morning, 9:00–16:59 → work_hours, 17:00–20:59 → evening, 21:00–4:59 → night. Uses `date.getHours()` (local time). Must cover all 24 hours with no gaps.

2. Create `mobile/src/hooks/useContextServices.ts` with `useContextServices()` hook returning `{ calendarEvent: string | null, calendarBusy: boolean, activity: string, timePeriod: string, isMonitoring: boolean }`. The hook:
   - Calls `startActivityMonitoring()` on mount (from `activity.ts`)
   - Sets up a 60-second `setInterval` for calendar polling (calls `getCurrentCalendarEvent()` from `calendar.ts`)
   - Computes `getTimePeriod()` on each polling cycle
   - Listens for `AppState` changes via React Native's `AppState.addEventListener('change', ...)` — when app comes to foreground, immediately re-polls calendar and recomputes time-period
   - Tracks previous values in a `useRef`. On each cycle, compares current vs previous. Only calls `updateContext()` (via `SemPKMClient` from session credentials) when at least one field changed.
   - Enforces minimum 30-second gap between `updateContext()` calls (tracks last push timestamp in a ref)
   - Returns current detected state for dashboard display
   - Cleans up all intervals, AppState listener, and activity monitoring on unmount via `useEffect` cleanup

3. Modify `mobile/src/app/(app)/(tabs)/index.tsx` to:
   - Import and call `useContextServices()` hook
   - Show a small monitoring status indicator below the staleness banner (e.g., "📡 Monitoring" with a green dot when `isMonitoring` is true)
   - Display the locally-detected values alongside the server-reported values (the hook's returned state shows what the phone detects; the fetched context shows what the server has)

4. Request calendar permission at an appropriate point — either in the orchestrator on first mount, or in the dashboard screen. Use `requestCalendarPermission()` from `calendar.ts`. This is a one-time OS prompt.

5. Verify the full slice: `cd mobile && npx tsc --noEmit`, check all service files exist, check dashboard imports the hook.

## Must-Haves

- [ ] `time-period.ts` exports `TimePeriod` and `getTimePeriod()` covering all 24 hours
- [ ] `useContextServices.ts` hook coordinates calendar (60s poll), activity (continuous), and time-period
- [ ] Orchestrator batches updates — single `updateContext()` call with all changed fields
- [ ] Minimum 30-second gap between pushes (rate limit protection)
- [ ] Change deduplication — no push if no field changed
- [ ] AppState listener re-checks calendar on app foreground
- [ ] Dashboard screen imports and uses `useContextServices` hook
- [ ] All subscriptions and intervals cleaned up on unmount
- [ ] TypeScript compiles with zero errors

## Verification

- `cd mobile && npx tsc --noEmit` — zero errors
- `test -f mobile/src/services/time-period.ts` — file exists
- `test -f mobile/src/hooks/useContextServices.ts` — file exists
- `grep -q 'useContextServices' mobile/src/app/\(app\)/\(tabs\)/index.tsx` — hook wired in dashboard
- `grep -q 'getTimePeriod' mobile/src/services/time-period.ts` — function exported
- `grep -q 'updateContext' mobile/src/hooks/useContextServices.ts` — orchestrator pushes to API

## Inputs

- `mobile/src/services/calendar.ts` — from T01, provides `requestCalendarPermission` and `getCurrentCalendarEvent`
- `mobile/src/services/activity.ts` — from T02, provides `startActivityMonitoring`, `stopActivityMonitoring`, `getCurrentActivity`
- `mobile/src/api/client.ts` — existing API client with `updateContext()` method
- `mobile/src/ctx.tsx` — `parseSession()` and `useSession()` for credentials
- `mobile/src/app/(app)/(tabs)/index.tsx` — existing dashboard screen to modify

## Expected Output

- `mobile/src/services/time-period.ts` — new file with time-of-day classification
- `mobile/src/hooks/useContextServices.ts` — new file with context orchestrator hook
- `mobile/src/app/(app)/(tabs)/index.tsx` — modified to wire orchestrator hook and show monitoring status

## Observability Impact

**New diagnostic signals:**
- `context.update_sent` — logged on each successful batched push, includes all field values. Confirms the orchestrator is pushing to the server.
- `context.update_skipped` — logged with `reason` (no_changes, rate_limited, no_session). Confirms dedup and rate limiting are working.
- `context.api_error` — logged with HTTP status and message on push failure. Critical for diagnosing backend connectivity.
- `context.services_started` — logged once on mount with poll and push intervals.
- `context.services_stopped` — logged on unmount, confirms cleanup happened.
- `context.foreground_refresh` — logged when AppState triggers a re-poll.
- `timePeriod.classified` — not logged per-call since it's pure computation, but visible via React DevTools on the hook's returned state.

**Inspection surface:** The `useContextServices()` hook returns `{ calendarEvent, calendarBusy, activity, timePeriod, isMonitoring }` — all visible in React DevTools. The dashboard renders both server-reported and device-detected values side by side, making discrepancies immediately visible.

**Failure visibility:** Push failures are logged as `context.api_error` with status code. Missing hardware degrades gracefully (activity → "unknown"). Calendar permission denial flows through existing `calendar.permission_denied` diagnostic.
