---
id: T03
parent: S05
milestone: M037
provides:
  - time-period.ts service with TimePeriod type and getTimePeriod() function
  - useContextServices.ts orchestrator hook coordinating calendar, activity, and time-period into batched context updates
  - Dashboard wiring showing monitoring status, server context, and device-detected values side by side
key_files:
  - mobile/src/services/time-period.ts
  - mobile/src/hooks/useContextServices.ts
  - mobile/src/app/(app)/(tabs)/index.tsx
key_decisions:
  - Request calendar permission inside orchestrator hook on mount rather than in dashboard screen — centralises permission lifecycle in the hook that actually needs it
  - 30-second minimum push gap (not per-field, global) balances freshness vs rate-limit headroom at 2 pushes/min worst case against 12/min backend limit
  - Dashboard shows both server-reported and device-detected sections to make update propagation discrepancies immediately visible
patterns_established:
  - Orchestrator batching pattern — collect changed fields from multiple services, compare against last-pushed ref, push single API call only on change with rate-limit guard
  - AppState foreground listener pattern for immediate re-poll when app returns from background
  - mountedRef guard pattern to prevent React state updates after unmount in async flows
observability_surfaces:
  - console.log context.update_sent { calendarEvent, calendarBusy, activity, timePeriod } — successful push
  - console.log context.update_skipped { reason } — no_changes / rate_limited / no_session
  - console.error context.api_error { status, message } — push failure
  - console.log context.services_started { pollIntervalMs, minPushGapMs } — init confirmation
  - console.log context.services_stopped — cleanup confirmation
  - console.log context.foreground_refresh — AppState re-poll trigger
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Time-period service, context orchestrator hook, and dashboard wiring

**Built time-period classifier, orchestrator hook that batches calendar/activity/time-period into rate-limited context pushes, and wired both server and device-detected values into the dashboard.**

## What Happened

Created three deliverables:

**1. `time-period.ts`** — Pure function `getTimePeriod(date?)` classifying local hour into morning (5–8), work_hours (9–16), evening (17–20), night (21–4). Exported `TimePeriod` type alias. All 24 hours covered with no gaps.

**2. `useContextServices.ts`** — Orchestrator hook that:
- Requests calendar permission on mount (one-time OS prompt via `requestCalendarPermission()`)
- Starts continuous activity monitoring via `startActivityMonitoring()`
- Polls calendar every 60 seconds and recomputes time-period each cycle
- Listens for `AppState` changes — immediately re-polls calendar and time-period when app returns to foreground
- Tracks previous pushed values in a `useRef`. Compares all four fields (calendarEvent, calendarBusy, activity, timePeriod) and only calls `updateContext()` when at least one changed.
- Enforces 30-second minimum gap between pushes via timestamp ref
- Returns current detected state `{ calendarEvent, calendarBusy, activity, timePeriod, isMonitoring }` for rendering
- Cleans up interval, AppState listener, and activity monitoring on unmount

**3. Dashboard wiring** — Modified `index.tsx` to import and call `useContextServices()`. Added a monitoring status indicator (green dot + "📡 Monitoring" text below the staleness banner). Split context fields into "Server Context" and "Device Detected" sections with section headers, showing both server-reported values and locally-detected values side by side. Added calendar busy field to both sections.

## Verification

All slice-level and task-level verification checks pass:
- TypeScript compiles with zero errors
- All four service files exist (calendar.ts, activity.ts, time-period.ts, useContextServices.ts)
- expo-calendar plugin configured in app.json
- Both expo-calendar and expo-sensors present in package.json
- useContextServices imported in dashboard
- getTimePeriod exported from time-period.ts
- updateContext called in orchestrator hook
- Rate limiting (MIN_PUSH_GAP_MS), change dedup (no_changes), AppState listener, cleanup (clearInterval + stopActivityMonitoring), and 60s poll interval all verified via grep

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | 3.7s |
| 2 | `ls mobile/src/services/calendar.ts mobile/src/services/activity.ts mobile/src/services/time-period.ts mobile/src/hooks/useContextServices.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'expo-calendar' mobile/app.json` | 0 | ✅ pass | <1s |
| 4 | `grep -q '"expo-calendar"' mobile/package.json && grep -q '"expo-sensors"' mobile/package.json` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'useContextServices' mobile/src/app/\(app\)/\(tabs\)/index.tsx` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'getTimePeriod' mobile/src/services/time-period.ts` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'updateContext' mobile/src/hooks/useContextServices.ts` | 0 | ✅ pass | <1s |

## Diagnostics

- **Push monitoring:** Filter Expo dev tools by `context.update_sent` to see each successful batched push with all field values. `context.update_skipped` shows when dedup or rate limiting kicked in.
- **Push failures:** `context.api_error` logged with HTTP status and message. Network errors show status 0.
- **Orchestrator lifecycle:** `context.services_started` on mount confirms poll and push intervals. `context.services_stopped` on unmount confirms cleanup.
- **Foreground re-poll:** `context.foreground_refresh` logged each time AppState triggers an immediate cycle.
- **React DevTools:** The hook's returned state (`calendarEvent`, `calendarBusy`, `activity`, `timePeriod`, `isMonitoring`) is visible in component inspection.
- **Dashboard dual display:** "Server Context" shows what the backend reports; "Device Detected" shows what the phone detects locally. Any discrepancy indicates a push hasn't propagated yet.

## Deviations

- Added `calendarBusy` field display to both server and device sections — the original dashboard only showed calendar event title but not busy status. Small UI addition for completeness.
- Section headers ("Server Context", "Device Detected") added to visually separate the two value sources — not specified in plan but necessary for clarity when both server and device values are shown.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/services/time-period.ts` — New time-of-day classification service with TimePeriod type and getTimePeriod() function
- `mobile/src/hooks/useContextServices.ts` — New orchestrator hook coordinating calendar, activity, and time-period into batched rate-limited context updates
- `mobile/src/app/(app)/(tabs)/index.tsx` — Added useContextServices hook, monitoring status indicator, and dual server/device context display
- `.gsd/milestones/M037/slices/S05/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
