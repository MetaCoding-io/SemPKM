---
id: T01
parent: S05
milestone: M037
provides:
  - calendar.ts service with requestCalendarPermission() and getCurrentCalendarEvent()
  - expo-calendar and expo-sensors installed as mobile dependencies
  - expo-calendar plugin configured in app.json with permission string
key_files:
  - mobile/src/services/calendar.ts
  - mobile/package.json
  - mobile/app.json
key_decisions:
  - Treat tentative and unspecified availability as busy (conservative default for context detection)
  - Cache permission status in module-level variable to avoid repeated OS prompts
  - Added resetPermissionCache() for settings-return flow
patterns_established:
  - Calendar service follows geofencing.ts pattern: module-scope state, console.log diagnostic keys, typed return values
  - Domain-prefixed log keys (calendar.permission_granted, calendar.events_fetched, etc.) for Expo dev tools filtering
observability_surfaces:
  - console.log calendar.permission_granted / calendar.permission_denied — permission lifecycle
  - console.log calendar.events_fetched { count } — event query success with count
  - console.log calendar.no_calendars — no readable calendars on device
  - console.error calendar.error { phase, error } — unexpected failures with context
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Calendar service with expo-calendar integration

**Installed expo-calendar and expo-sensors, configured calendar plugin in app.json, and implemented calendar service that reads current/upcoming events with busy status and graceful permission-denied handling.**

## What Happened

Installed `expo-calendar` (~55.0.10) and `expo-sensors` (~55.0.9) via `npx expo install`. Added the `expo-calendar` plugin entry to `app.json` with a user-facing permission string explaining why calendar access is needed. Note: `expo-sensors` does not require a plugin entry since 1Hz sampling is below Android's HIGH_SAMPLING_RATE_SENSORS threshold.

Created `mobile/src/services/calendar.ts` following the geofencing.ts service pattern. The service exports:
- `requestCalendarPermission()` — checks/requests calendar read permission, caches the result in a module-level variable, checks `canAskAgain` before re-prompting on previously denied permissions.
- `getCurrentCalendarEvent()` — queries all device calendars for events in a `now → now+5min` window, prefers a currently-running event over an upcoming one, returns `{ title, busy }`. Treats `tentative` and unspecified availability as busy (conservative default).
- `resetPermissionCache()` — allows rechecking after user returns from OS settings.

All three edge cases handled: no calendars found, no events in window, event with empty/whitespace title. Every failure path returns `{ title: null, busy: false }` with structured console logging.

## Verification

All task and applicable slice verification checks pass:
- `npx tsc --noEmit` — zero TypeScript errors
- `expo-calendar` and `expo-sensors` present in `package.json` dependencies
- `expo-calendar` plugin configured in `app.json`
- `calendar.ts` exists and exports both `requestCalendarPermission` and `getCurrentCalendarEvent`
- Graceful degradation path confirmed: `{ title: null, busy: false }` returned for permission denied

Slice checks not yet applicable (T02/T03 outputs): `activity.ts`, `time-period.ts`, `useContextServices.ts` don't exist yet — expected.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | 6.3s |
| 2 | `grep -q '"expo-calendar"' mobile/package.json` | 0 | ✅ pass | <1s |
| 3 | `grep -q '"expo-sensors"' mobile/package.json` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'expo-calendar' mobile/app.json` | 0 | ✅ pass | <1s |
| 5 | `test -f mobile/src/services/calendar.ts` | 0 | ✅ pass | <1s |

## Diagnostics

- **Permission state:** Call `requestCalendarPermission()` — returns cached boolean. Reset with `resetPermissionCache()` to force re-check.
- **Event query:** `getCurrentCalendarEvent()` logs `calendar.events_fetched { count: N }` on each successful query. Filter Expo dev tools by `calendar.` prefix.
- **Failure diagnosis:** `calendar.error { phase, error }` captures both permission-request and event-query failures with the phase name for attribution.

## Deviations

- Added `resetPermissionCache()` export not in the task plan — needed for the settings-return flow where users change permissions in OS settings and come back to the app. Small addition, no plan impact.
- Used `Calendar.EntityTypes.EVENT` parameter in `getCalendarsAsync()` to filter out reminder calendars — the plan didn't specify this but it avoids fetching irrelevant calendar types.
- Check `canAskAgain` before re-prompting on denied permissions — prevents futile OS prompt that would be immediately auto-declined.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/services/calendar.ts` — New calendar service with permission lifecycle, event querying, and diagnostic logging
- `mobile/package.json` — Added expo-calendar (~55.0.10) and expo-sensors (~55.0.9) dependencies
- `mobile/app.json` — Added expo-calendar plugin with calendar permission string
- `.gsd/milestones/M037/slices/S05/S05-PLAN.md` — Added Observability / Diagnostics section (pre-flight fix)
- `.gsd/milestones/M037/slices/S05/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
