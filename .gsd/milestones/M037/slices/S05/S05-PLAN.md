# S05: Mobile Calendar & Activity Detection

**Goal:** Mobile app reads device calendar and detects activity type (stationary/walking/driving), enriching context updates with calendar event name, busy status, activity type, and time-of-day period.
**Demo:** After granting calendar permission in the app, a current/upcoming calendar event's title and busy status appear in the context dashboard. Accelerometer-based activity classification shows as stationary/walking/driving. Time-of-day period (morning/work_hours/evening/night) is computed automatically. All three fields are batched into a single `updateContext()` call to the backend.

## Must-Haves

- `expo-calendar` installed and configured in `app.json` with calendar permission string
- `expo-sensors` installed for Accelerometer and Pedometer access
- Calendar service reads device calendars and detects current/upcoming events with busy status
- Activity service classifies motion via accelerometer magnitude variance + pedometer step counting
- Time-of-day service classifies current hour into morning/work_hours/evening/night
- Context orchestrator hook batches all three services into rate-limit-aware `updateContext()` calls
- All services degrade gracefully when permissions are denied or hardware unavailable
- Dashboard screen wires the orchestrator hook and shows monitoring status
- TypeScript compiles with zero errors

## Verification

- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- `ls mobile/src/services/calendar.ts mobile/src/services/activity.ts mobile/src/services/time-period.ts mobile/src/hooks/useContextServices.ts` — all service files exist
- `grep -q 'expo-calendar' mobile/app.json` — calendar plugin configured
- `grep -q '"expo-calendar"' mobile/package.json && grep -q '"expo-sensors"' mobile/package.json` — dependencies installed
- `grep -q 'useContextServices' mobile/src/app/\(app\)/\(tabs\)/index.tsx` — orchestrator wired into dashboard

## Tasks

- [x] **T01: Calendar service with expo-calendar integration** `est:45m`
  - Why: CTX-12 requires reading device calendar events. This installs `expo-calendar` and `expo-sensors`, configures app.json plugins, and builds the calendar service that reads current/upcoming events with busy status detection and graceful permission-denied handling.
  - Files: `mobile/package.json`, `mobile/app.json`, `mobile/src/services/calendar.ts`
  - Do: Run `npx expo install expo-calendar expo-sensors` in `mobile/`. Add `expo-calendar` plugin to `app.json` with permission string. Implement `calendar.ts` with `requestCalendarPermission()`, `getCurrentCalendarEvent()` returning `{title, busy}`, permission status caching, and a 5-minute lookahead window for upcoming events. Handle permission denied by returning `{title: null, busy: false}`.
  - Verify: `cd mobile && npx tsc --noEmit` passes, `grep -q 'expo-calendar' mobile/app.json` passes
  - Done when: `calendar.ts` exports `requestCalendarPermission` and `getCurrentCalendarEvent`, both `expo-calendar` and `expo-sensors` are in package.json, and TypeScript compiles clean

- [x] **T02: Activity detection service with accelerometer and pedometer** `est:45m`
  - Why: CTX-13 requires detecting stationary/walking/driving activity. This builds the activity service using Accelerometer magnitude variance over a sliding window, supplemented by Pedometer step counting to confirm walking.
  - Files: `mobile/src/services/activity.ts`
  - Do: Implement `activity.ts` with `ActivityService` class (or functional module) that subscribes to Accelerometer at 1Hz, maintains a 10-sample sliding window of magnitude values, computes variance to classify activity (variance < 0.01 → stationary, < 0.15 → walking, ≥ 0.15 → driving). Supplement with `Pedometer.watchStepCount()` — increasing steps override to "walking". Check `Accelerometer.isAvailableAsync()` and degrade to "unknown" if unavailable. Export `startActivityMonitoring()`, `stopActivityMonitoring()`, and `getCurrentActivity()`.
  - Verify: `cd mobile && npx tsc --noEmit` passes, `test -f mobile/src/services/activity.ts`
  - Done when: `activity.ts` exports start/stop/get functions with accelerometer subscription, sliding window variance classification, pedometer supplement, and unavailable-hardware fallback

- [ ] **T03: Time-period service, context orchestrator hook, and dashboard wiring** `est:45m`
  - Why: Ties all three context enrichment services together. The time-period service is pure computation. The orchestrator hook coordinates calendar polling (60s), activity monitoring, and time-period computation into rate-limit-aware batched `updateContext()` calls with change deduplication. Dashboard wiring makes it live.
  - Files: `mobile/src/services/time-period.ts`, `mobile/src/hooks/useContextServices.ts`, `mobile/src/app/(app)/(tabs)/index.tsx`
  - Do: Implement `time-period.ts` with `getTimePeriod()` returning morning/work_hours/evening/night based on current hour (defaults: 5-8 morning, 9-16 work_hours, 17-20 evening, 21-4 night). Build `useContextServices()` hook that starts activity monitoring on mount, polls calendar every 60s, computes time-period on each cycle, listens for AppState changes to re-check on foreground, batches changed fields into a single `updateContext()` call (minimum 30s between pushes to respect rate limit), and returns current detected state `{calendarEvent, calendarBusy, activity, timePeriod, isMonitoring}`. Wire hook into dashboard screen, showing monitoring status indicator. Clean up all subscriptions on unmount.
  - Verify: `cd mobile && npx tsc --noEmit` passes, `grep -q 'useContextServices' mobile/src/app/\(app\)/\(tabs\)/index.tsx` passes
  - Done when: All three services wired through orchestrator, dashboard shows monitoring status, TypeScript compiles clean, context updates batched with deduplication

## Observability / Diagnostics

- **Runtime signals:** Each service logs structured console messages with domain-prefixed keys (`calendar.*`, `activity.*`, `timePeriod.*`) for filtering in Expo dev tools. The orchestrator hook logs `context.update_sent` with field diffs on each successful push and `context.update_skipped` when rate-limited or unchanged.
- **Inspection surfaces:** The `useContextServices()` hook returns current detected state (`calendarEvent`, `calendarBusy`, `activity`, `timePeriod`, `isMonitoring`) — visible in React DevTools and rendered on the dashboard. Permission denial is surfaced as `calendar.permission_denied` log entry.
- **Failure visibility:** Network errors from `updateContext()` are logged as `context.api_error` with status code. Hardware unavailability (no accelerometer/pedometer) is logged once as `activity.hardware_unavailable` and the service degrades to `"unknown"`. Calendar permission denial returns a typed null result — no silent swallowing.
- **Redaction:** No calendar event content beyond title is logged. No PII from calendar descriptions or attendee lists is ever transmitted.

## Files Likely Touched

- `mobile/package.json`
- `mobile/app.json`
- `mobile/src/services/calendar.ts`
- `mobile/src/services/activity.ts`
- `mobile/src/services/time-period.ts`
- `mobile/src/hooks/useContextServices.ts`
- `mobile/src/app/(app)/(tabs)/index.tsx`
