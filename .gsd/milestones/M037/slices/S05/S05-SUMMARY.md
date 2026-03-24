---
id: S05
parent: M037
milestone: M037
provides:
  - Calendar service reading device events via expo-calendar with busy status detection
  - Activity detection service classifying stationary/walking/driving via accelerometer variance + pedometer
  - Time-of-day classification service (morning/work_hours/evening/night)
  - Orchestrator hook batching all three services into rate-limited context updates
  - Dashboard wiring showing both server-reported and device-detected context values
requires:
  - slice: S03
    provides: API client, updateContext() dispatch function, navigation scaffold
affects:
  - S07
key_files:
  - mobile/src/services/calendar.ts
  - mobile/src/services/activity.ts
  - mobile/src/services/time-period.ts
  - mobile/src/hooks/useContextServices.ts
  - mobile/src/app/(app)/(tabs)/index.tsx
key_decisions:
  - Treat tentative and unspecified calendar availability as busy (conservative default for context detection)
  - 30-second minimum push gap between context updates — balances freshness vs backend rate limit (12/min)
  - Dashboard shows server-reported and device-detected sections side by side for update propagation visibility
  - Calendar permission requested inside orchestrator hook on mount, not in dashboard screen — centralises permission lifecycle
patterns_established:
  - Orchestrator batching — collect changed fields from multiple services, compare against last-pushed ref, push single API call only on change with rate-limit guard
  - AppState foreground listener for immediate re-poll when app returns from background
  - mountedRef guard to prevent React state updates after unmount in async flows
  - Domain-prefixed console.log keys per service (calendar.*, activity.*, context.*) for Expo dev tools filtering
  - Sliding window with population variance for sensor signal smoothing
observability_surfaces:
  - console.log context.update_sent { fields } — successful batched push
  - console.log context.update_skipped { reason } — no_changes / rate_limited / no_session
  - console.error context.api_error { status, message } — push failure
  - console.log activity.classified { activity, variance, windowSize, stepsIncreasing } — classification detail
  - console.log calendar.events_fetched { count } — event query result
  - Dashboard dual display — server vs device values show propagation discrepancies
drill_down_paths:
  - .gsd/milestones/M037/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M037/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M037/slices/S05/tasks/T03-SUMMARY.md
duration: 35m
verification_result: passed
completed_at: 2026-03-23
---

# S05: Mobile Calendar & Activity Detection

**Mobile app reads device calendar events, classifies activity via accelerometer/pedometer, computes time-of-day period, and pushes all three as batched context updates to the backend.**

## What Happened

Three services and one orchestrator hook, built across three tasks:

**Calendar service (T01)** — Installed `expo-calendar` (~55.0.10) and `expo-sensors` (~55.0.9). Configured the expo-calendar plugin in `app.json` with a user-facing permission string. The service requests calendar read permission (with `canAskAgain` check to avoid futile re-prompts on permanent denials), queries device calendars for events in a `now → now+5min` window, prefers currently-running events over upcoming ones, and returns `{ title, busy }`. Tentative and unspecified availability are treated as busy (conservative default). Permission status is cached in a module-level variable with `resetPermissionCache()` for the settings-return flow.

**Activity detection service (T02)** — Subscribes to `Accelerometer` at 1Hz, maintains a 10-sample sliding window of magnitude values, computes population variance for classification: `<0.01` → stationary, `0.01–0.15` → walking, `≥0.15` → driving. Supplemented by `Pedometer.watchStepCount()` — if step count increased in the last 3 seconds, classification is overridden to "walking" regardless of variance (handles steady-pace walking that produces low variance). Degrades to "unknown" if accelerometer hardware is unavailable.

**Time-period service + orchestrator hook + dashboard wiring (T03)** — Pure function `getTimePeriod()` classifying local hour into morning (5–8), work_hours (9–16), evening (17–20), night (21–4). The `useContextServices()` hook coordinates all three: requests calendar permission on mount, starts activity monitoring, polls calendar every 60 seconds, recomputes time-period each cycle, listens for AppState changes to re-poll on foreground return, and batches changed fields into a single `updateContext()` call with 30-second minimum push gap and change deduplication. Dashboard now shows monitoring status indicator and splits context into "Server Context" and "Device Detected" sections.

## Verification

All five slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `cd mobile && npx tsc --noEmit` — zero TypeScript errors | ✅ pass |
| 2 | All four service files exist (calendar.ts, activity.ts, time-period.ts, useContextServices.ts) | ✅ pass |
| 3 | `expo-calendar` plugin configured in `app.json` | ✅ pass |
| 4 | `expo-calendar` and `expo-sensors` in `package.json` | ✅ pass |
| 5 | `useContextServices` imported in dashboard `index.tsx` | ✅ pass |

Observability verified: all domain-prefixed log keys present across calendar (8 logs), activity (6 logs), and orchestrator (8 logs) services. Time-period service is a pure function with no side effects — no logs needed.

## Deviations

- **`resetPermissionCache()` added to calendar service** — Not in the task plan. Needed for the settings-return flow where users grant calendar permission in OS Settings and return to the app.
- **Calendar busy status added to dashboard** — The original dashboard only showed event title. Added busy status display to both server and device sections for completeness.
- **"Server Context" / "Device Detected" section headers** — Not specified in plan but necessary for clarity when showing both server-reported values and locally-detected values side by side.

None of these deviate from the slice goal — they're additive completeness improvements.

## Known Limitations

- **Activity thresholds are best-guess** — The variance boundaries (0.01 / 0.15) are reasonable heuristics but not calibrated against real-world device diversity. Different phone placements (pocket vs bag vs hand) produce different magnitude distributions.
- **Calendar event title only** — No event description, location, or attendee info is transmitted. This is intentional (privacy) but means context rules can only match on event title and busy status.
- **Time-period boundaries are hardcoded** — Morning/work_hours/evening/night hour ranges are fixed in code. The plan mentions "configurable boundaries" but this slice deferred configuration to a settings screen (no settings UI for time boundaries exists yet).
- **No offline queue** — If the phone has no network when a context change occurs, the update is lost. CTX-15 (offline queue with retry) is deferred per the roadmap.

## Follow-ups

- S06 (Push Notifications) can now receive calendar_busy and time_period fields in context for notification suppression logic.
- S07 (Integration) needs to verify the full chain: calendar event starts → orchestrator detects it → pushes to backend → rules engine evaluates → persona switches.
- Time-period configuration UI could be added to the mobile Settings tab — currently hardcoded.

## Files Created/Modified

- `mobile/src/services/calendar.ts` — Calendar service with permission lifecycle, event querying, busy detection
- `mobile/src/services/activity.ts` — Activity detection with accelerometer sliding window, variance classification, pedometer override
- `mobile/src/services/time-period.ts` — Time-of-day classification (morning/work_hours/evening/night)
- `mobile/src/hooks/useContextServices.ts` — Orchestrator hook batching calendar/activity/time-period into rate-limited context pushes
- `mobile/src/app/(app)/(tabs)/index.tsx` — Dashboard wiring with monitoring status and dual server/device display
- `mobile/package.json` — Added expo-calendar and expo-sensors dependencies
- `mobile/app.json` — Added expo-calendar plugin with permission string

## Forward Intelligence

### What the next slice should know
- S05 services are fully wired through `useContextServices()` — the dashboard imports and renders the hook's return values. S06 (push notifications) doesn't need to touch the mobile context services, only the backend notification dispatch.
- The `updateContext()` call from S03's API client is the single integration point. All three services funnel through the orchestrator hook which calls `updateContext()` with a flat dict of fields.

### What's fragile
- Activity variance thresholds (0.01 / 0.15) — tuned by hand, not calibrated against device diversity. If activity misclassification becomes an issue, these need per-device calibration or a configurable sensitivity setting.
- Pedometer 3-second snapshot window — too short may miss slow walking, too long adds latency. Current value is a compromise.

### Authoritative diagnostics
- `context.update_sent` in Expo dev tools — shows exactly what fields were pushed and when. If the backend shows stale context, check whether this log fires.
- `activity.classified` — shows raw variance and classification decision on every 10-sample cycle. First place to look if activity type seems wrong.
- Dashboard dual display (server vs device) — any discrepancy between the two sections means the push hasn't propagated. Check `context.update_skipped` and `context.api_error`.

### What assumptions changed
- expo-sensors doesn't require an app.json plugin entry — the plan expected it might, but 1Hz sampling is below Android's HIGH_SAMPLING_RATE_SENSORS threshold.
