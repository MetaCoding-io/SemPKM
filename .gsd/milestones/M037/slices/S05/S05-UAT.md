# S05: Mobile Calendar & Activity Detection — UAT

**Milestone:** M037
**Written:** 2026-03-23

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: Calendar, activity detection, and time-period are device-level features that require a running Expo dev build on a phone or simulator. TypeScript compilation proves API contract correctness; live runtime proves real device integration.

## Preconditions

- Expo dev build running on iOS simulator or physical device (`cd mobile && npx expo start --dev-client`)
- Backend running with Context API (S01) — `POST /api/context/update` and `GET /api/context/current` operational
- Mobile app configured with valid instance URL and API key (S03 onboarding completed)
- Device has at least one calendar with events (simulator: add events via Calendar app)
- Device/simulator has accelerometer hardware (physical device preferred; iOS simulator has limited sensor support)

## Smoke Test

Open the mobile app dashboard tab. Verify "📡 Monitoring" indicator appears below the staleness banner. Both "Server Context" and "Device Detected" sections should be visible with fields for calendar event, calendar busy, activity, and time period.

## Test Cases

### 1. Calendar Event Detection — Current Event

1. Create a calendar event on the device that starts 10 minutes ago and ends 30 minutes from now (title: "Team Standup")
2. Open the mobile app dashboard
3. Wait up to 60 seconds for the next calendar poll cycle
4. **Expected:** "Device Detected" section shows calendar event = "Team Standup", calendar busy = Yes
5. Check backend: `GET /api/context/current` should include `calendar_event: "Team Standup"` and `calendar_busy: true`

### 2. Calendar Event Detection — Upcoming Event (5-minute lookahead)

1. Create a calendar event starting 3 minutes from now (title: "Design Review")
2. Open the mobile app dashboard
3. Wait for the next poll cycle (up to 60 seconds)
4. **Expected:** "Device Detected" section shows calendar event = "Design Review"
5. **Expected:** Event with start time more than 5 minutes away does NOT appear

### 3. Calendar Permission Denied

1. Revoke calendar permission in device Settings > Privacy > Calendars > SemPKM
2. Return to the mobile app
3. **Expected:** Calendar event shows as empty/null, calendar busy = No (graceful degradation)
4. Check Expo dev tools console: `calendar.permission_denied` log entry should appear
5. **Expected:** Activity detection and time-period continue working independently

### 4. Activity Detection — Stationary

1. Place the device on a stable surface
2. Open the mobile app dashboard and wait 15 seconds (10 accelerometer samples at 1Hz + classification)
3. **Expected:** "Device Detected" section shows activity = "stationary"
4. Check Expo dev tools: `activity.classified { activity: "stationary", variance: <0.01, ... }` should appear

### 5. Activity Detection — Walking

1. Hold the device and walk normally for 15+ seconds
2. Observe dashboard
3. **Expected:** Activity changes to "walking"
4. Verify via `activity.classified` log: either variance 0.01–0.15 or `stepsIncreasing: true` overriding to walking

### 6. Time-of-Day Period

1. Note the current local time
2. Open the mobile app dashboard
3. **Expected:** "Device Detected" section shows time period matching:
   - 5:00–8:59 → "morning"
   - 9:00–16:59 → "work_hours"
   - 17:00–20:59 → "evening"
   - 21:00–4:59 → "night"

### 7. Batched Context Update — Change Deduplication

1. Open dashboard with monitoring active
2. Wait for an initial `context.update_sent` log
3. Without changing anything (no new calendar event, device stationary, same hour), wait 2+ minutes
4. **Expected:** `context.update_skipped { reason: "no_changes" }` appears in console — no redundant API calls
5. Now create a new calendar event starting now
6. **Expected:** Within 60 seconds, `context.update_sent` fires with the new calendar event field

### 8. Rate Limiting — 30-Second Minimum Push Gap

1. Trigger a context change (e.g., create a calendar event)
2. Observe `context.update_sent` log with timestamp
3. Immediately trigger another change (e.g., start walking)
4. **Expected:** Second change is buffered — next `context.update_sent` fires no sooner than 30 seconds after the first
5. If within the 30-second window: `context.update_skipped { reason: "rate_limited" }` should appear

### 9. AppState Foreground Refresh

1. Open the mobile app dashboard (monitoring running)
2. Switch to another app (home screen or another app) for 10+ seconds
3. Return to the mobile app
4. **Expected:** `context.foreground_refresh` appears in Expo dev tools
5. Calendar and time-period are re-polled immediately (check for `calendar.events_fetched` log shortly after)

### 10. Dashboard Dual Display — Server vs Device

1. Open dashboard with monitoring active
2. Wait for at least one `context.update_sent` log
3. **Expected:** "Server Context" values match "Device Detected" values for all four fields
4. Disable network (airplane mode)
5. Create a new calendar event
6. **Expected:** "Device Detected" shows new event, "Server Context" still shows previous value (propagation discrepancy visible)

## Edge Cases

### No Calendars on Device

1. Delete all calendars from the device (or use a fresh simulator with no accounts)
2. Open the mobile app dashboard
3. **Expected:** Calendar event = null, busy = false. Console shows `calendar.no_calendars`
4. **Expected:** Activity and time-period services unaffected

### Accelerometer Unavailable (Simulator)

1. Run on iOS simulator (limited accelerometer support)
2. Open dashboard
3. **Expected:** Console shows `activity.hardware_unavailable`. Activity field shows "unknown"
4. **Expected:** Calendar and time-period services unaffected

### Calendar Event with Empty Title

1. Create a calendar event with no title (just a time block)
2. Wait for poll cycle
3. **Expected:** Calendar event shows as null or empty — no crash, no "undefined" string

### App Backgrounded for Extended Period

1. Open dashboard, confirm monitoring is active
2. Background the app for 5+ minutes
3. Return to the app
4. **Expected:** `context.foreground_refresh` fires, all services re-poll, monitoring continues without restart

## Failure Signals

- "📡 Monitoring" indicator does not appear → orchestrator hook failed to initialize
- "Device Detected" section missing → `useContextServices()` not wired into dashboard
- Activity stuck on "unknown" on a physical device → accelerometer subscription failed
- Calendar always null despite events → calendar permission not requested or permanently denied
- Server Context never updates → `updateContext()` API calls failing (check `context.api_error`)
- TypeScript compilation errors → service interfaces broken

## Requirements Proved By This UAT

- CTX-12 (device calendar reading) — Test cases 1, 2, 3 prove calendar event detection with title and busy status
- CTX-13 (activity detection) — Test cases 4, 5 prove accelerometer + pedometer classification

## Not Proven By This UAT

- Full end-to-end chain (calendar event → context update → rule evaluation → persona switch) — deferred to S07 integration
- Push notification suppression based on calendar_busy — deferred to S06
- Offline queue and retry for failed context pushes — deferred per roadmap (CTX-15)
- Activity classification accuracy across diverse device placements — requires extended field testing

## Notes for Tester

- iOS simulator has limited sensor support — activity detection tests (4, 5) are best run on a physical device. On simulator, expect "unknown" activity with `activity.hardware_unavailable` log.
- Calendar poll interval is 60 seconds. Wait at least one full cycle after creating events before concluding the test failed.
- The 30-second push gap means rapid changes are batched, not lost. If a test seems to "miss" a change, wait 30 seconds for the next push window.
- Console log filtering in Expo dev tools: use `calendar.`, `activity.`, or `context.` prefixes to isolate specific service output.
